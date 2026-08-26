#!/usr/bin/env python3
"""Transcribe All-In podcast episodes with OpenAI's diarized Whisper endpoint."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI

EPISODES_JSON = Path("data/processed/all_in_episodes.json")
AUDIO_DIR = Path("data/audio/all_in")
OUTPUT_ROOT = Path("data/processed/transcripts_openai")
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


def load_openai_key() -> str:
    key = os.getenv("OPENAI_API_KEY")
    if key:
        return key
    if ENV_PATH.exists():
        env_values = parse_env_file(ENV_PATH)
        key = env_values.get("OPENAI_API_KEY")
        if key:
            return key
    raise SystemExit("Missing OPENAI_API_KEY (set env var or add to .env)")


def load_episode_index(path: Path = EPISODES_JSON) -> Dict[str, Dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"Episode metadata not found at {path}. Run all_in_downloader first.")
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


def ensure_output_dir(episode_id: str) -> Path:
    out_dir = OUTPUT_ROOT / episode_id
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def convert_segments(raw_segments: List[Dict[str, Any]], offset: float = 0.0) -> List[Dict[str, Any]]:
    segments: List[Dict[str, Any]] = []
    for seg in raw_segments:
        start = float(seg.get("start", 0.0))
        end = float(seg.get("end", start))
        start += offset
        end += offset
        segments.append(
            {
                "speaker": seg.get("speaker"),
                "text": seg.get("text", ""),
                "start": start,
                "end": end,
                "start_ms": int(start * 1000),
                "end_ms": int(end * 1000),
            }
        )
    return segments


def write_outputs(episode_id: str, payload: Dict[str, Any], segments: List[Dict[str, Any]]) -> None:
    out_dir = ensure_output_dir(episode_id)
    (out_dir / "openai_raw.json").write_text(json.dumps(payload, indent=2))
    (out_dir / "segments.json").write_text(json.dumps(segments, indent=2))

    lines = [
        f"{seg['speaker']} [{format_timestamp(seg['start_ms'])} - {format_timestamp(seg['end_ms'])}]: {seg['text']}"
        for seg in segments
    ]
    (out_dir / "transcript.txt").write_text("\n".join(lines))


def format_timestamp(ms: int) -> str:
    seconds, ms_part = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{ms_part:03d}"


def normalize_response(data: Any) -> Dict[str, Any]:
    if hasattr(data, "model_dump"):
        return data.model_dump()
    if isinstance(data, str):
        return json.loads(data)
    if isinstance(data, dict):
        return data
    raise TypeError(f"Unsupported response type: {type(data)}")


def convert_to_wav(audio_path: Path) -> Path:
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_path = Path(tmp.name)
    tmp.close()
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(audio_path),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "wav",
        str(tmp_path),
    ]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        tmp_path.unlink(missing_ok=True)
        raise SystemExit(f"ffmpeg conversion failed for {audio_path}: {exc}") from exc
    return tmp_path


def get_audio_duration(audio_path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def split_audio_if_needed(
    audio_path: Path,
    *,
    max_chunk_mb: int,
    chunk_seconds: int,
) -> Tuple[List[Path], Optional[tempfile.TemporaryDirectory]]:
    max_bytes = max_chunk_mb * 1024 * 1024
    if audio_path.stat().st_size <= max_bytes:
        return [audio_path], None

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    temp_dir = tempfile.TemporaryDirectory(dir=OUTPUT_ROOT)
    chunk_dir = Path(temp_dir.name)
    chunk_pattern = chunk_dir / "chunk_%03d.mp3"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(audio_path),
        "-f",
        "segment",
        "-segment_time",
        str(chunk_seconds),
        "-c",
        "copy",
        str(chunk_pattern),
    ]
    subprocess.run(cmd, check=True)
    chunk_paths = sorted(chunk_dir.glob("chunk_*.mp3"))
    if not chunk_paths:
        temp_dir.cleanup()
        raise SystemExit(f"Chunking failed for {audio_path}; ffmpeg produced no segments")
    return chunk_paths, temp_dir


def transcribe_episode(
    episode_id: str,
    metadata: Dict[str, Any],
    client: OpenAI,
    *,
    model: str,
    chunking_strategy: str,
    max_chunk_mb: int,
    chunk_seconds: int,
) -> None:
    audio_filename = metadata.get("audio_filename")
    if not audio_filename:
        print(f"[{episode_id}] Missing audio_filename in metadata, skipping")
        return
    audio_path = AUDIO_DIR / audio_filename
    if not audio_path.exists():
        print(f"[{episode_id}] Audio file not found at {audio_path}, skipping")
        return

    chunk_paths, temp_dir = split_audio_if_needed(
        audio_path,
        max_chunk_mb=max_chunk_mb,
        chunk_seconds=chunk_seconds,
    )

    combined_segments: List[Dict[str, Any]] = []
    chunk_payloads: List[Dict[str, Any]] = []
    offset = 0.0

    try:
        for idx, chunk_path in enumerate(chunk_paths):
            print(f"[{episode_id}] Processing chunk {idx + 1}/{len(chunk_paths)}: {chunk_path.name}")
            wav_path = convert_to_wav(chunk_path)
            try:
                with wav_path.open("rb") as audio_file:
                    response = client.audio.transcriptions.create(
                        model=model,
                        file=audio_file,
                        response_format="diarized_json",
                        chunking_strategy=chunking_strategy,
                        timeout=60,
                    )
            finally:
                wav_path.unlink(missing_ok=True)

            payload = normalize_response(response)
            raw_segments = payload.get("segments") or []
            combined_segments.extend(convert_segments(raw_segments, offset=offset))
            chunk_duration = get_audio_duration(chunk_path)
            chunk_payloads.append(
                {
                    "chunk_index": idx,
                    "offset_start": offset,
                    "duration": chunk_duration,
                    "raw": payload,
                }
            )
            offset += chunk_duration
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()

    combined_payload = {
        "episode_id": episode_id,
        "model": model,
        "chunking_strategy": chunking_strategy,
        "chunks": chunk_payloads,
    }
    write_outputs(episode_id, combined_payload, combined_segments)
    print(f"[{episode_id}] ✅ Saved OpenAI transcript to {OUTPUT_ROOT / episode_id}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episode-id", required=True, help="Episode ID (e.g., ALLIN-E001)")
    parser.add_argument("--model", default="gpt-4o-transcribe-diarize", help="OpenAI transcription model")
    parser.add_argument(
        "--chunking-strategy",
        default="auto",
        choices=["auto", "resample", "none"],
        help="Chunking strategy passed to the API",
    )
    parser.add_argument(
        "--max-chunk-mb",
        type=int,
        default=24,
        help="Maximum chunk size in megabytes before splitting",
    )
    parser.add_argument(
        "--chunk-seconds",
        type=int,
        default=600,
        help="Target chunk duration in seconds when splitting large files",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    api_key = load_openai_key()
    client = OpenAI(api_key=api_key)
    metadata_index = load_episode_index()
    metadata = metadata_index.get(args.episode_id)
    if metadata is None:
        raise SystemExit(f"Episode {args.episode_id} not found in metadata index")
    transcribe_episode(
        args.episode_id,
        metadata,
        client,
        model=args.model,
        chunking_strategy=args.chunking_strategy,
        max_chunk_mb=args.max_chunk_mb,
        chunk_seconds=args.chunk_seconds,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
