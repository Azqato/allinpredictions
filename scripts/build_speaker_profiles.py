#!/usr/bin/env python3
"""Generate canonical speaker embeddings from labeled AssemblyAI segments."""
from __future__ import annotations

import argparse
import json
import shutil
import wave
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from speaker_utils import (
    AUDIO_DIR,
    SPEAKER_DIR,
    aggregate_embeddings,
    compute_embedding,
    load_audio_segment,
    load_config,
    load_segments,
    require_ffmpeg,
    save_config,
    select_segments,
    set_transcripts_dir,
    update_embedding_entry,
)

DEFAULT_SAMPLE_RATE = 16000


def parse_assignments(assignments: List[str]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for item in assignments:
        if "=" not in item:
            raise SystemExit(
                f"Invalid --assign value '{item}'. Expected format label=speaker_key."
            )
        label, key = item.split("=", 1)
        mapping[label.strip()] = key.strip()
    return mapping


def save_waveform(path: Path, waveform: np.ndarray, sample_rate: int = DEFAULT_SAMPLE_RATE) -> None:
    clipped = np.clip(waveform, -1.0, 1.0)
    ints = (clipped * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(ints.tobytes())


def build_embeddings_for_episode(
    episode_id: str,
    assignments: Dict[str, str],
    *,
    min_duration: float,
    max_segments: int,
    debug: bool = False,
    debug_dir: Optional[Path] = None,
    strategy: str = "mfcc",
) -> Dict[str, Path]:
    segments = load_segments(episode_id)
    audio_path = AUDIO_DIR / f"{episode_id}.mp3"
    if not audio_path.exists():
        raise SystemExit(f"Audio file not found for {episode_id} at {audio_path}")

    debug_root = None
    if debug:
        target_root = debug_dir or (SPEAKER_DIR / "debug")
        debug_root = target_root / episode_id
        if debug_root.exists():
            shutil.rmtree(debug_root)
        debug_root.mkdir(parents=True, exist_ok=True)

    saved: Dict[str, Path] = {}
    for label, speaker_key in assignments.items():
        selected = select_segments(
            segments, label, min_duration=min_duration, max_segments=max_segments
        )
        if not selected:
            print(f"[WARN] No segments for label {label} meeting duration threshold.")
            continue
        speaker_debug_dir = None
        debug_samples: List[Dict[str, float]] = []
        if debug_root is not None:
            speaker_debug_dir = debug_root / speaker_key
            if speaker_debug_dir.exists():
                shutil.rmtree(speaker_debug_dir)
            speaker_debug_dir.mkdir(parents=True, exist_ok=True)
        vectors: List[np.ndarray] = []
        for idx, (start, end) in enumerate(selected, start=1):
            waveform = load_audio_segment(audio_path, start, end, sample_rate=DEFAULT_SAMPLE_RATE)
            embedding = compute_embedding(waveform, strategy=strategy)
            if embedding is not None:
                vectors.append(embedding)
            if speaker_debug_dir is not None and waveform.size:
                filename = f"{idx:02d}_{start:.2f}-{end:.2f}.wav"
                save_waveform(speaker_debug_dir / filename, waveform, sample_rate=DEFAULT_SAMPLE_RATE)
                debug_samples.append(
                    {
                        "file": filename,
                        "start": round(start, 3),
                        "end": round(end, 3),
                        "duration": round(end - start, 3),
                    }
                )
        if not vectors:
            print(f"[WARN] Unable to compute embeddings for label {label}.")
            continue
        speaker_vector = aggregate_embeddings(vectors)
        SPEAKER_DIR.mkdir(parents=True, exist_ok=True)
        out_path = SPEAKER_DIR / f"{speaker_key}.npy"
        np.save(out_path, speaker_vector)
        saved[speaker_key] = out_path
        print(f"[OK] Stored embedding for {speaker_key} at {out_path}")
        if speaker_debug_dir is not None and debug_samples:
            (speaker_debug_dir / "samples.json").write_text(json.dumps(debug_samples, indent=2))
    return saved


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--episode-id", required=True, help="Episode ID (e.g., ALLIN-E000)"
    )
    parser.add_argument(
        "--assign",
        action="append",
        required=True,
        help="Map diarization label to speaker key, e.g., --assign A=jason",
    )
    parser.add_argument(
        "--min-duration",
        type=float,
        default=3.0,
        help="Minimum segment length (seconds)",
    )
    parser.add_argument(
        "--segments-per-speaker",
        type=int,
        default=5,
        help="Maximum number of segments to average per speaker",
    )
    parser.add_argument(
        "--strategy",
        choices=["mfcc", "speechbrain"],
        default="mfcc",
        help="Embedding strategy to use for profile generation",
    )
    parser.add_argument(
        "--transcription",
        choices=["assemblyai", "deepgram", "openai", "speechmatics"],
        default="assemblyai",
        help="Select which transcripts directory to read from",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Dump the selected audio clips used per speaker for manual review.",
    )
    parser.add_argument(
        "--debug-dir",
        type=Path,
        default=Path("data/speakers/debug"),
        help="Directory to store debug audio samples when --debug is set.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    require_ffmpeg()
    set_transcripts_dir(args.transcription)
    assignments = parse_assignments(args.assign)
    saved = build_embeddings_for_episode(
        args.episode_id,
        assignments,
        min_duration=args.min_duration,
        max_segments=args.segments_per_speaker,
        debug=args.debug,
        debug_dir=args.debug_dir,
        strategy=args.strategy,
    )
    if not saved:
        print("No embeddings were generated.")
        return 1
    config = load_config()
    for speaker_key, path in saved.items():
        update_embedding_entry(config, speaker_key, path, strategy=args.strategy)
    save_config(config)
    print("Speaker configuration updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
