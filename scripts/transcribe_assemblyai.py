#!/usr/bin/env python3
"""Transcribe All-In podcast episodes using AssemblyAI with speaker diarization."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

EPISODES_JSON = Path("data/processed/all_in_episodes.json")
AUDIO_DIR = Path("data/audio/all_in")
TRANSCRIPTS_DIR = Path("data/processed/transcripts_assemblyai")
STATUS_PATH = Path("data/processed/transcript_status.json")
ASSEMBLYAI_BASE = "https://api.assemblyai.com/v2"
UPLOAD_CHUNK_BYTES = 5_242_880  # 5 MB chunks per AssemblyAI guidance


class AssemblyAIError(RuntimeError):
    """Raised for API-related failures."""


class AssemblyAIClient:
    def __init__(self, api_key: str) -> None:
        self.session = requests.Session()
        self.session.headers.update({"authorization": api_key})

    def upload_file(self, audio_path: Path) -> str:
        url = f"{ASSEMBLYAI_BASE}/upload"
        with audio_path.open("rb") as source:
            response = self.session.post(url, data=self._read_file(source))
        _raise_for_status(response, f"upload {audio_path.name}")
        upload_url = response.json().get("upload_url")
        if not upload_url:
            raise AssemblyAIError("Upload response missing upload_url")
        return upload_url

    @staticmethod
    def _read_file(source) -> Iterable[bytes]:
        while True:
            data = source.read(UPLOAD_CHUNK_BYTES)
            if not data:
                break
            yield data

    def create_transcript(self, audio_url: str, *, speaker_labels: bool = True) -> str:
        url = f"{ASSEMBLYAI_BASE}/transcript"
        payload = {
            "audio_url": audio_url,
            "speaker_labels": speaker_labels,
            "language_detection": False,
        }
        response = self.session.post(url, json=payload)
        _raise_for_status(response, "create transcript")
        transcript_id = response.json().get("id")
        if not transcript_id:
            raise AssemblyAIError("Transcript creation response missing id")
        return transcript_id

    def wait_for_completion(
        self, transcript_id: str, poll_interval: int = 15
    ) -> Dict[str, Any]:
        url = f"{ASSEMBLYAI_BASE}/transcript/{transcript_id}"
        while True:
            response = self.session.get(url)
            _raise_for_status(response, "fetch transcript status")
            data = response.json()
            status = data.get("status")
            if status in {"completed", "error"}:
                return data
            print(f"  Status: {status}, waiting {poll_interval}s ...")
            time.sleep(poll_interval)


def _raise_for_status(response: requests.Response, context: str) -> None:
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        detail = response.text
        raise AssemblyAIError(
            f"Failed to {context}: {exc}\nResponse: {detail}"
        ) from exc


def load_api_key(env_path: Path = Path(".env")) -> str:
    key = os.getenv("ASSEMBLYAI_API_KEY")
    if key:
        return key
    if env_path.exists():
        env_data = parse_env_file(env_path)
        key = env_data.get("ASSEMBLYAI_API_KEY")
        if key:
            return key
    raise SystemExit("Missing ASSEMBLYAI_API_KEY (set env var or add to .env)")


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


def load_episode_index(path: Path = EPISODES_JSON) -> Dict[str, Dict[str, Any]]:
    if not path.exists():
        raise SystemExit(
            f"Missing episode metadata at {path}. Run all_in_downloader first."
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


def list_available_episode_ids(audio_dir: Path = AUDIO_DIR) -> List[str]:
    if not audio_dir.exists():
        return []
    return sorted(p.stem for p in audio_dir.glob("*.mp3"))


def ensure_output_dirs() -> None:
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)


def ms_to_seconds(value: Optional[int]) -> Optional[float]:
    if value is None:
        return None
    return round(value / 1000.0, 3)


def format_timestamp(ms: Optional[int]) -> str:
    if ms is None:
        return "??:??:??.???"
    seconds, ms_part = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{ms_part:03d}"


def write_transcript_outputs(
    episode_id: str,
    assembly_payload: Dict[str, Any],
    episode_metadata: Dict[str, Any],
) -> None:
    episode_dir = TRANSCRIPTS_DIR / episode_id
    episode_dir.mkdir(parents=True, exist_ok=True)

    raw_path = episode_dir / "assemblyai_raw.json"
    segments_path = episode_dir / "segments.json"
    text_path = episode_dir / "transcript.txt"
    metadata_path = episode_dir / "metadata.json"

    raw_path.write_text(json.dumps(assembly_payload, indent=2))

    utterances = assembly_payload.get("utterances") or []
    segments: List[Dict[str, Any]] = []
    lines: List[str] = []
    for utterance in utterances:
        start_ms = utterance.get("start")
        end_ms = utterance.get("end")
        segment = {
            "speaker_label": utterance.get("speaker"),
            "text": utterance.get("text"),
            "start_ms": start_ms,
            "end_ms": end_ms,
            "start": ms_to_seconds(start_ms),
            "end": ms_to_seconds(end_ms),
            "confidence": utterance.get("confidence"),
        }
        segments.append(segment)
        lines.append(
            f"{segment['speaker_label']} [{format_timestamp(start_ms)} - {format_timestamp(end_ms)}]: {segment['text']}"
        )

    segments_path.write_text(json.dumps(segments, indent=2))
    text_path.write_text("\n".join(lines))

    metadata = {
        "episode_id": episode_id,
        "title": episode_metadata.get("title"),
        "published": episode_metadata.get("published"),
        "transcript_id": assembly_payload.get("id"),
        "audio_duration_sec": assembly_payload.get("audio_duration"),
        "completed_at": assembly_payload.get("completed"),
        "status": assembly_payload.get("status"),
        "audio_url": assembly_payload.get("audio_url"),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2))

    update_status_file(
        episode_id,
        {
            "transcript_id": assembly_payload.get("id"),
            "status": assembly_payload.get("status"),
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "audio_duration_sec": assembly_payload.get("audio_duration"),
            "segments_path": str(segments_path),
        },
    )


def update_status_file(episode_id: str, payload: Dict[str, Any]) -> None:
    status = {}
    if STATUS_PATH.exists():
        status = json.loads(STATUS_PATH.read_text())
    status[episode_id] = payload
    STATUS_PATH.write_text(json.dumps(status, indent=2))


def transcribe_episode(
    episode_id: str,
    episode_metadata: Dict[str, Any],
    client: AssemblyAIClient,
    *,
    force: bool = False,
    poll_interval: int = 15,
) -> None:
    def log(message: str) -> None:
        print(f"[{episode_id}] {message}")

    audio_filename = episode_metadata.get("audio_filename")
    if not audio_filename:
        log("Skipping: missing audio_filename in metadata")
        return
    audio_path = AUDIO_DIR / audio_filename
    if not audio_path.exists():
        log(f"Skipping: audio file not found at {audio_path}")
        return

    episode_dir = TRANSCRIPTS_DIR / episode_id
    segments_path = episode_dir / "segments.json"
    if segments_path.exists() and not force:
        log("Skipping: transcript already exists (use --force to re-run)")
        return

    log(f"Uploading {audio_path} ...")
    upload_url = client.upload_file(audio_path)
    log("Starting transcription job ...")
    transcript_id = client.create_transcript(upload_url)
    log(f"Transcript ID: {transcript_id}")
    result = client.wait_for_completion(transcript_id, poll_interval=poll_interval)
    status = result.get("status")
    if status != "completed":
        error = result.get("error", "Unknown error")
        raise AssemblyAIError(f"Transcription failed: {error}")
    write_transcript_outputs(episode_id, result, episode_metadata)
    log(f"✅ Completed: {segments_path}")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--episode-id",
        action="append",
        help="Episode ID(s) to transcribe (e.g. ALLIN-E012). Can specify multiple times.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Transcribe every episode with a downloaded audio file",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on how many episodes to process",
    )
    parser.add_argument(
        "--force", action="store_true", help="Re-run even if transcript exists"
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=15,
        help="Seconds between AssemblyAI status polls",
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=10,
        help="Maximum number of concurrent transcription jobs",
    )
    return parser.parse_args(argv)


def resolve_targets(
    args: argparse.Namespace, episode_index: Dict[str, Dict[str, Any]]
) -> List[str]:
    if args.episode_id:
        return args.episode_id
    if args.all:
        have_audio = list_available_episode_ids()
        return have_audio
    raise SystemExit("Specify --episode-id or --all to choose episodes to transcribe")


def transcribe_worker(
    api_key: str,
    episode_id: str,
    episode_metadata: Dict[str, Any],
    *,
    force: bool,
    poll_interval: int,
) -> Tuple[bool, Optional[str]]:
    client = AssemblyAIClient(api_key)
    try:
        transcribe_episode(
            episode_id,
            episode_metadata,
            client,
            force=force,
            poll_interval=poll_interval,
        )
        return True, None
    except AssemblyAIError as exc:
        return False, str(exc)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    ensure_output_dirs()
    api_key = load_api_key()
    episode_index = load_episode_index()
    targets = resolve_targets(args, episode_index)
    if args.limit is not None:
        targets = targets[: args.limit]
    if not targets:
        print("No episodes selected.")
        return 0

    with ThreadPoolExecutor(max_workers=max(1, args.max_concurrency)) as executor:
        future_map = {}
        for episode_id in targets:
            metadata = episode_index.get(episode_id)
            if not metadata:
                print(f"[{episode_id}] Skipping: not found in metadata")
                continue
            future = executor.submit(
                transcribe_worker,
                api_key,
                episode_id,
                metadata,
                force=args.force,
                poll_interval=args.poll_interval,
            )
            future_map[future] = episode_id

        for future in as_completed(future_map):
            episode_id = future_map[future]
            try:
                success, message = future.result()
            except Exception as exc:
                print(f"[{episode_id}] ❌ Unexpected error: {exc}")
                continue
            if not success:
                print(f"[{episode_id}] ❌ {message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
