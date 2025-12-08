#!/usr/bin/env python3
"""Transcribe All-In episodes with Deepgram's diarization API."""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from deepgram import DeepgramClient

EPISODES_JSON = Path("data/processed/all_in_episodes.json")
AUDIO_DIR = Path("data/audio/all_in")
OUTPUT_DIR = Path("data/processed/transcripts_deepgram")
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
    key = os.getenv("DEEPGRAM_API_KEY")
    if key:
        return key
    if ENV_PATH.exists():
        env_vals = parse_env_file(ENV_PATH)
        key = env_vals.get("DEEPGRAM_API_KEY")
        if key:
            return key
    raise SystemExit("Missing DEEPGRAM_API_KEY (set env var or add to .env)")


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


def list_downloaded_episode_ids() -> List[str]:
    if not AUDIO_DIR.exists():
        return []
    return sorted(p.stem for p in AUDIO_DIR.glob("*.mp3"))


def ensure_episode_dir(episode_id: str) -> Path:
    out_dir = OUTPUT_DIR / episode_id
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def transcript_exists(episode_id: str) -> bool:
    return (OUTPUT_DIR / episode_id / "transcript.txt").exists()


def format_timestamp(ms: int) -> str:
    seconds, ms_part = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{ms_part:03d}"


def speaker_label_from_id(speaker: Any) -> str:
    try:
        idx = int(float(speaker))
    except (ValueError, TypeError):
        return str(speaker)
    if idx < 0:
        return str(speaker)
    letters: List[str] = []
    while True:
        idx, rem = divmod(idx, 26)
        letters.append(chr(ord("A") + rem))
        if idx == 0:
            break
        idx -= 1
    return "".join(reversed(letters))


def build_segment(
    speaker: str,
    text: str,
    start: float,
    end: float,
    confidence: Optional[float],
) -> Dict[str, Any]:
    return {
        "speaker": speaker_label_from_id(speaker),
        "text": text,
        "start": start,
        "end": end,
        "start_ms": int(start * 1000),
        "end_ms": int(end * 1000),
        "confidence": confidence,
    }


def extract_segments(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    segments: List[Dict[str, Any]] = []
    results = payload.get("results") or {}
    channels = results.get("channels") or []
    if channels:
        alternatives = channels[0].get("alternatives") or []
        if alternatives:
            alt = alternatives[0]
            paragraphs = (alt.get("paragraphs") or {}).get("paragraphs") or []
            if paragraphs:
                for paragraph in paragraphs:
                    speaker = paragraph.get("speaker", "Speaker")
                    para_start = float(paragraph.get("start", 0.0))
                    para_end = float(paragraph.get("end", para_start))
                    sentences = paragraph.get("sentences") or []
                    if sentences:
                        for sentence in sentences:
                            text = sentence.get("text", "")
                            start = float(sentence.get("start", para_start))
                            end = float(sentence.get("end", para_end))
                            confidence = sentence.get("confidence")
                            segments.append(
                                build_segment(speaker, text, start, end, confidence)
                            )
                    else:
                        text = paragraph.get("text", "")
                        segments.append(
                            build_segment(speaker, text, para_start, para_end, None)
                        )
                return segments
            utterances = results.get("utterances") or []
            if utterances:
                for utterance in utterances:
                    speaker = utterance.get("speaker", "Speaker")
                    start = float(utterance.get("start", 0.0))
                    end = float(utterance.get("end", start))
                    text = utterance.get("transcript", "")
                    segments.append(
                        build_segment(
                            speaker, text, start, end, utterance.get("confidence")
                        )
                    )
                return segments
            words = alt.get("words") or []
            if words:
                current_speaker = None
                buffer: List[str] = []
                start = end = 0.0
                for word in words:
                    speaker = word.get("speaker", current_speaker or "Speaker")
                    if current_speaker is None:
                        current_speaker = speaker
                        start = float(word.get("start", 0.0))
                    elif speaker != current_speaker:
                        if buffer:
                            text = " ".join(buffer)
                            segments.append(
                                build_segment(current_speaker, text, start, end, None)
                            )
                        buffer = []
                        current_speaker = speaker
                        start = float(word.get("start", 0.0))
                    buffer.append(word.get("word", ""))
                    end = float(word.get("end", start))
                if buffer and current_speaker is not None:
                    text = " ".join(buffer)
                    segments.append(
                        build_segment(current_speaker, text, start, end, None)
                    )
    return segments


def write_outputs(
    episode_id: str,
    payload: Dict[str, Any],
    segments: List[Dict[str, Any]],
    episode_metadata: Dict[str, Any],
) -> None:
    out_dir = ensure_episode_dir(episode_id)
    (out_dir / "deepgram_raw.json").write_text(
        json.dumps(payload, indent=2, default=str)
    )
    (out_dir / "segments.json").write_text(json.dumps(segments, indent=2))
    lines = [
        f"{seg['speaker']} [{format_timestamp(seg['start_ms'])} - {format_timestamp(seg['end_ms'])}]: {seg['text']}"
        for seg in segments
    ]
    (out_dir / "transcript.txt").write_text("\n".join(lines))
    # Episode metadata snapshot for downstream joins
    metadata_path = out_dir / "metadata.json"
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
    metadata_path.write_text(json.dumps(metadata, indent=2, default=str))


def transcribe_episode(
    episode_id: str,
    metadata: Dict[str, Any],
    client: DeepgramClient,
    *,
    model: str,
    language: str,
) -> None:
    audio_filename = metadata.get("audio_filename")
    if not audio_filename:
        print(f"[{episode_id}] Missing audio_filename in metadata, skipping")
        return
    audio_path = AUDIO_DIR / audio_filename
    if not audio_path.exists():
        print(f"[{episode_id}] Audio file not found at {audio_path}, skipping")
        return

    mimetype = mimetypes.guess_type(audio_path.name)[0] or "audio/mpeg"
    with audio_path.open("rb") as audio_file:
        source = {"buffer": audio_file.read(), "mimetype": mimetype}

    print(f"[{episode_id}] Transcribing with Deepgram ({model}) ...")
    response = client.listen.v1.media.transcribe_file(
        request=source["buffer"],
        model=model,
        smart_format=True,
        diarize=True,
        language=language,
    )
    payload = response.model_dump()
    segments = extract_segments(payload)
    write_outputs(episode_id, payload, segments, metadata)
    print(f"[{episode_id}] ✅ Saved Deepgram transcript to {OUTPUT_DIR / episode_id}")


def parse_args() -> argparse.Namespace:
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
        default=4,
        help="Maximum parallel Deepgram jobs",
    )
    parser.add_argument(
        "--model", default="nova-3", help="Deepgram model (default: nova-3)"
    )
    parser.add_argument(
        "--language", default="en-US", help="Language code (default: en-US)"
    )
    return parser.parse_args()


def resolve_targets(args: argparse.Namespace) -> List[str]:
    if args.episode_id:
        return args.episode_id
    if args.all:
        ids = list_downloaded_episode_ids()
        if not ids:
            raise SystemExit("No audio files found under data/audio/all_in/")
        return ids
    raise SystemExit("Specify --episode-id or --all to select episodes")


def worker(
    episode_id: str,
    metadata: Dict[str, Any],
    client: DeepgramClient,
    *,
    model: str,
    language: str,
    force: bool,
) -> Tuple[str, bool, Optional[str]]:
    if not force and transcript_exists(episode_id):
        return episode_id, True, "skip"
    try:
        transcribe_episode(episode_id, metadata, client, model=model, language=language)
        return episode_id, True, None
    except Exception as exc:
        return episode_id, False, str(exc)


def main() -> int:
    args = parse_args()
    api_key = load_api_key()
    client = DeepgramClient(api_key=api_key)
    metadata_index = load_episode_index()
    targets = resolve_targets(args)
    if args.limit is not None:
        targets = targets[: args.limit]
    if not targets:
        print("No episodes selected.")
        return 0

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with ThreadPoolExecutor(max_workers=max(1, args.max_concurrency)) as executor:
        futures = []
        for episode_id in targets:
            metadata = metadata_index.get(episode_id)
            if metadata is None:
                print(f"[{episode_id}] Skipping: not found in metadata index")
                continue
            futures.append(
                executor.submit(
                    worker,
                    episode_id,
                    metadata,
                    client,
                    model=args.model,
                    language=args.language,
                    force=args.force,
                )
            )

        for future in as_completed(futures):
            episode_id, success, message = future.result()
            if message == "skip":
                print(
                    f"[{episode_id}] Skipping: transcript already exists (use --force to overwrite)"
                )
                continue
            if not success:
                print(f"[{episode_id}] ❌ {message}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
