#!/usr/bin/env python3
"""Transcribe All-In podcast episodes using Speechmatics Batch."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from speechmatics.batch import AsyncClient, TranscriptionConfig, Transcript

EPISODES_JSON = Path("data/processed/all_in_episodes.json")
AUDIO_DIR = Path("data/audio/all_in")
OUTPUT_DIR = Path("data/processed/transcripts_speechmatics")
ENV_PATH = Path(".env")


def parse_env_file(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def load_api_key() -> str:
    key = os.getenv("SPEECHMATICS_API_KEY")
    if key:
        return key
    if ENV_PATH.exists():
        env_vals = parse_env_file(ENV_PATH)
        key = env_vals.get("SPEECHMATICS_API_KEY")
        if key:
            os.environ["SPEECHMATICS_API_KEY"] = key
            return key
    raise SystemExit("Missing SPEECHMATICS_API_KEY (set env var or add to .env)")


def load_episode_index(path: Path = EPISODES_JSON) -> Dict[str, Dict[str, Any]]:
    if not path.exists():
        raise SystemExit(
            f"Episode metadata not found at {path}. Run all_in_downloader first."
        )
    episodes = json.loads(path.read_text())
    index: Dict[str, Dict[str, Any]] = {}
    for episode in episodes:
        filename = episode.get("audio_filename")
        if not filename:
            continue
        episode_id = Path(filename).stem
        episode["episode_id"] = episode_id
        index[episode_id] = episode
    return index


def list_downloaded_episode_ids(audio_dir: Path = AUDIO_DIR) -> List[str]:
    if not audio_dir.exists():
        return []
    return sorted(p.stem for p in audio_dir.glob("*.mp3"))


def ensure_output_dir(episode_id: str) -> Path:
    out_dir = OUTPUT_DIR / episode_id
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def transcript_exists(episode_id: str) -> bool:
    return (OUTPUT_DIR / episode_id / "transcript.txt").exists()


def normalize_result(result: Any) -> Any:
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if is_dataclass(result):
        return asdict(result)
    if isinstance(result, dict):
        return result
    if hasattr(result, "__dict__"):
        return result.__dict__
    try:
        return json.loads(result)  # type: ignore[arg-type]
    except Exception:
        return str(result)


def ms_to_seconds(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(value, 3)


def format_timestamp(ms: Optional[int]) -> str:
    if ms is None:
        return "??:??:??.???"
    seconds, ms_part = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{ms_part:03d}"


def speaker_label_from_id(raw: Any) -> str:
    text = str(raw) if raw is not None else "Speaker"
    if text.startswith("S") and text[1:].isdigit():
        idx = int(text[1:]) - 1
        if idx >= 0:
            letters: List[str] = []
            while True:
                idx, rem = divmod(idx, 26)
                letters.append(chr(ord("A") + rem))
                if idx == 0:
                    break
                idx -= 1
            return "".join(reversed(letters))
    return text


def build_segments_from_results(results: List[Any]) -> List[Dict[str, Any]]:
    segments: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    punctuation_chars = set(".,!?;:()[]{}\"'-")

    for item in results:
        alternatives = getattr(item, "alternatives", None)
        if not alternatives:
            continue
        alt = alternatives[0]
        content = getattr(alt, "content", "") or ""
        speaker = speaker_label_from_id(getattr(alt, "speaker", None))
        start = getattr(item, "start_time", None)
        end = getattr(item, "end_time", None)
        confidence = getattr(alt, "confidence", None)

        speaker_label = speaker
        is_punctuation = content.strip() in punctuation_chars

        if current is None or speaker_label != current["speaker_label"]:
            if current:
                current["text"] = "".join(current.pop("parts")).strip()
                confidences = current.pop("confidences")
                if confidences:
                    current["confidence"] = sum(confidences) / len(confidences)
                segments.append(current)
            current = {
                "speaker_label": speaker_label,
                "start": start,
                "end": end,
                "parts": [],
                "confidences": [],
            }
        else:
            if end is not None:
                current["end"] = end

        if start is not None and current["start"] is None:
            current["start"] = start
        if confidence is not None:
            current["confidences"].append(confidence)

        parts = current["parts"]
        if parts and not is_punctuation and not parts[-1].endswith(" "):
            parts.append(" ")
        parts.append(content)

    if current:
        current["text"] = "".join(current.pop("parts")).strip()
        confidences = current.pop("confidences")
        if confidences:
            current["confidence"] = sum(confidences) / len(confidences)
        segments.append(current)

    for seg in segments:
        start = seg.get("start")
        end = seg.get("end")
        seg["start_ms"] = int(start * 1000) if start is not None else None
        seg["end_ms"] = int(end * 1000) if end is not None else None
        seg["start"] = ms_to_seconds(start)
        seg["end"] = ms_to_seconds(end)
    return segments


def write_outputs(
    episode_id: str,
    payload: Transcript,
    segments: List[Dict[str, Any]],
    episode_metadata: Dict[str, Any],
) -> None:
    out_dir = ensure_output_dir(episode_id)
    (out_dir / "speechmatics_raw.json").write_text(
        json.dumps(normalize_result(payload), indent=2, default=str)
    )

    segments_path = out_dir / "segments.json"
    segments_path.write_text(json.dumps(segments, indent=2))

    lines = [
        f"{seg['speaker_label']} [{format_timestamp(seg.get('start_ms'))} - {format_timestamp(seg.get('end_ms'))}]: {seg.get('text', '')}"
        for seg in segments
    ]
    (out_dir / "transcript.txt").write_text("\n".join(lines))

    metadata = {
        key: episode_metadata.get(key)
        for key in [
            "episode_id",
            "title",
            "published",
            "description",
            "duration",
            "audio_filename",
        ]
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, default=str))


def resolve_targets(args: argparse.Namespace) -> List[str]:
    if args.episode_id:
        return args.episode_id
    if args.all:
        ids = list_downloaded_episode_ids()
        if not ids:
            raise SystemExit("No audio files found under data/audio/all_in/")
        return ids
    raise SystemExit("Specify --episode-id or --all to select episodes")


async def transcribe_episode(
    episode_id: str,
    metadata: Dict[str, Any],
    client: AsyncClient,
    *,
    force: bool,
) -> None:
    if not force and transcript_exists(episode_id):
        print(
            f"[{episode_id}] Skipping: transcript already exists (use --force to overwrite)"
        )
        return

    audio_filename = metadata.get("audio_filename")
    if not audio_filename:
        print(f"[{episode_id}] Missing audio_filename in metadata, skipping")
        return

    audio_path = AUDIO_DIR / audio_filename
    if not audio_path.exists():
        print(f"[{episode_id}] Audio file not found at {audio_path}, skipping")
        return

    print(f"[{episode_id}] Uploading to Speechmatics ...")
    result = await client.transcribe(
        str(audio_path),
        transcription_config=TranscriptionConfig(
            language="en",
            diarization="speaker",
            operating_point="enhanced",
            enable_entities=True,
        ),
    )
    if isinstance(result, str):
        raise SystemExit("Transcription failed or returned unexpected result type.")

    segments = build_segments_from_results(getattr(result, "results", []))
    write_outputs(episode_id, result, segments, metadata)
    print(
        f"[{episode_id}] ✅ Saved Speechmatics transcript to {OUTPUT_DIR / episode_id}"
    )


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--episode-id",
        action="append",
        help="Episode ID(s) to transcribe (e.g., ALLIN-E001). Can be passed multiple times.",
    )
    parser.add_argument(
        "--all", action="store_true", help="Transcribe every downloaded episode"
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Optional cap on number of episodes"
    )
    parser.add_argument(
        "--force", action="store_true", help="Re-run even if transcript already exists"
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=5,
        help="Maximum parallel Speechmatics jobs",
    )
    return parser.parse_args(argv)


def worker(
    episode_id: str, metadata: Dict[str, Any], *, force: bool
) -> Tuple[str, bool, Optional[str]]:
    async def _run() -> None:
        async with AsyncClient(api_key=load_api_key()) as client:
            await transcribe_episode(
                episode_id,
                metadata,
                client,
                force=force,
            )

    try:
        asyncio.run(_run())
        return episode_id, True, None
    except Exception as exc:  # noqa: BLE001
        return episode_id, False, str(exc)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    load_api_key()
    metadata_index = load_episode_index()
    targets = resolve_targets(args)
    if args.limit is not None:
        targets = targets[: args.limit]
    if not targets:
        print("No episodes selected.")
        return 0

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with ThreadPoolExecutor(max_workers=max(1, args.max_concurrency)) as executor:
        futures = {}
        for episode_id in targets:
            metadata = metadata_index.get(episode_id)
            if metadata is None:
                print(f"[{episode_id}] Skipping: not found in metadata index")
                continue
            futures[executor.submit(worker, episode_id, metadata, force=args.force)] = (
                episode_id
            )

        for future in as_completed(futures):
            episode_id = futures[future]
            try:
                _, success, message = future.result()
            except Exception as exc:  # noqa: BLE001
                print(f"[{episode_id}] ❌ Unexpected error: {exc}")
                continue
            if not success:
                print(f"[{episode_id}] ❌ {message}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
