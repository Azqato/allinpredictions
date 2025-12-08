#!/usr/bin/env python3
"""Assign canonical speaker names to AssemblyAI diarization labels using embeddings."""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import Counter

import numpy as np

from speaker_utils import (
    AUDIO_DIR,
    TRANSCRIPTS_DIR,
    CURRENT_TRANSCRIPTION_SOURCE,
    aggregate_embeddings,
    compute_embedding,
    load_audio_segment,
    load_config,
    load_segments,
    require_ffmpeg,
    select_segments,
    get_transcripts_dir,
    set_transcripts_dir,
)


def load_known_embeddings(
    config: Dict[str, dict], *, strategy: str
) -> Dict[str, np.ndarray]:
    known: Dict[str, np.ndarray] = {}
    for key, info in config.get("speakers", {}).items():
        path = info.get("embedding")
        if not path:
            continue
        embedding_path = Path(path)
        if embedding_path.exists():
            stored_strategy = info.get("embedding_strategy")
            if stored_strategy and stored_strategy != strategy:
                raise SystemExit(
                    f"Embedding for {key} was created with '{stored_strategy}' but '{strategy}' was requested. "
                    "Rebuild profiles with build_speaker_profiles.py using the desired --strategy."
                )
            if stored_strategy is None and strategy != "mfcc":
                raise SystemExit(
                    "Existing embeddings lack strategy metadata and may be incompatible with 'speechbrain'. "
                    "Rebuild profiles with build_speaker_profiles.py --strategy speechbrain."
                )
            known[key] = np.load(embedding_path)
        else:
            print(f"[WARN] Embedding path missing for {key}: {embedding_path}")
    if not known:
        raise SystemExit(
            "No speaker embeddings available. Run build_speaker_profiles.py first."
        )
    return known


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def compute_label_embedding(
    segments: List[Dict[str, float]],
    label: str,
    audio_path: Path,
    *,
    min_duration: float,
    max_segments: int,
    strategy: str,
) -> Optional[np.ndarray]:
    selected = select_segments(
        segments, label, min_duration=min_duration, max_segments=max_segments
    )
    if not selected:
        # fallback: take shortest segments as last resort
        fallback = select_segments(
            segments, label, min_duration=0.5, max_segments=max_segments
        )
        selected = fallback
    vectors: List[np.ndarray] = []
    for start, end in selected:
        waveform = load_audio_segment(audio_path, start, end)
        embedding = compute_embedding(waveform, strategy=strategy)
        if embedding is not None:
            vectors.append(embedding)
    if not vectors:
        return None
    return aggregate_embeddings(vectors)


def assign_speakers_to_episode(
    episode_id: str,
    config: Dict[str, dict],
    known_embeddings: Dict[str, np.ndarray],
    *,
    threshold: float,
    min_duration: float,
    max_segments: int,
    strategy: str,
) -> None:
    segments = load_segments(episode_id)
    print(f"[INFO] Assigning speakers for {episode_id} with {len(segments)} segments")
    audio_path = AUDIO_DIR / f"{episode_id}.mp3"
    if not audio_path.exists():
        raise SystemExit(f"Missing audio file at {audio_path}")

    label_counts = Counter(seg.get("speaker_label") for seg in segments)
    label_results: Dict[str, Dict[str, Any]] = {}
    for label in sorted({seg.get("speaker_label") for seg in segments}):
        embedding = compute_label_embedding(
            segments,
            label,
            audio_path,
            min_duration=min_duration,
            max_segments=max_segments,
            strategy=strategy,
        )
        if embedding is None:
            label_results[label] = {
                "speaker_key": None,
                "display_name": None,
                "score": None,
                "status": "unassigned",
                "scores": {},
                "segment_count": label_counts.get(label, 0),
            }
            continue
        best_key: Optional[str] = None
        best_score = -1.0
        all_scores: Dict[str, float] = {}
        for speaker_key, reference in known_embeddings.items():
            score = cosine_similarity(embedding, reference)
            all_scores[speaker_key] = round(score, 4)
            if score > best_score:
                best_score = score
                best_key = speaker_key
        if best_key and best_score >= threshold:
            info = config["speakers"].get(best_key, {})
            label_results[label] = {
                "speaker_key": best_key,
                "display_name": info.get("display_name", best_key),
                "score": round(best_score, 4),
                "status": "matched",
                "scores": all_scores,
                "segment_count": label_counts.get(label, 0),
            }
        else:
            label_results[label] = {
                "speaker_key": None,
                "display_name": None,
                "score": round(best_score, 4) if best_score >= 0 else None,
                "status": "unmatched",
                "scores": all_scores,
                "segment_count": label_counts.get(label, 0),
            }

    rewrite_transcript_files(episode_id, segments, label_results)
    save_speaker_map(episode_id, label_results)
    print(f"[OK] Updated transcripts for {episode_id}")


def rewrite_transcript_files(
    episode_id: str,
    segments: List[Dict[str, float]],
    assignments: Dict[str, Dict[str, Optional[str]]],
) -> None:
    episode_dir = TRANSCRIPTS_DIR / episode_id
    transcript_named = episode_dir / "transcript_named.txt"

    lines: List[str] = []
    for seg in segments:
        label = seg.get("speaker_label")
        assignment = assignments.get(label, {})
        speaker_name = assignment.get("display_name") or f"Speaker {label}"
        seg["speaker_key"] = assignment.get("speaker_key")
        seg["canonical_speaker"] = speaker_name
        start_ms = seg.get("start_ms")
        end_ms = seg.get("end_ms")
        lines.append(
            f"{speaker_name} [{format_timestamp(start_ms)} - {format_timestamp(end_ms)}]: {seg.get('text','')}"
        )

    (episode_dir / "segments.json").write_text(json.dumps(segments, indent=2))
    transcript_named.write_text("\n".join(lines))


def save_speaker_map(
    episode_id: str, assignments: Dict[str, Dict[str, Optional[str]]]
) -> None:
    episode_dir = TRANSCRIPTS_DIR / episode_id
    map_path = episode_dir / "speaker_map.json"
    map_path.write_text(json.dumps(assignments, indent=2))


def format_timestamp(ms: Optional[int]) -> str:
    if ms is None:
        return "??:??:??.???"
    seconds, ms_part = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{ms_part:03d}"


def list_available_episode_ids() -> List[str]:
    transcripts_dir = get_transcripts_dir()
    if not transcripts_dir.exists():
        return []
    ids: List[str] = []
    for subdir in sorted(transcripts_dir.iterdir()):
        if not subdir.is_dir():
            continue
        if (subdir / "segments.json").exists():
            ids.append(subdir.name)
    return ids


def episode_has_named_transcript(episode_id: str) -> bool:
    episode_dir = get_transcripts_dir() / episode_id
    return (episode_dir / "transcript_named.txt").exists()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--episode-id",
        action="append",
        help="Episode ID(s) to label (e.g., ALLIN-E000). Can be passed multiple times.",
    )
    parser.add_argument(
        "--all", action="store_true", help="Process every episode with a transcript"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.725,
        help="Cosine similarity required for a match",
    )
    parser.add_argument(
        "--min-duration",
        type=float,
        default=3.0,
        help="Minimum segment length in seconds",
    )
    parser.add_argument(
        "--segments-per-speaker",
        type=int,
        default=6,
        help="Number of top segments to average per diarized label",
    )
    parser.add_argument(
        "--strategy",
        choices=["mfcc", "speechbrain"],
        default="speechbrain",
        help="Embedding strategy for speaker verification",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on how many episodes to process",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run even if transcript_named.txt already exists",
    )
    parser.add_argument(
        "--transcription",
        choices=["assemblyai", "deepgram", "openai", "speechmatics"],
        default=CURRENT_TRANSCRIPTION_SOURCE,
        help="Select which transcripts directory to use",
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=6,
        help="Maximum number of concurrent speaker-assignment jobs",
    )
    return parser.parse_args()


def resolve_targets(args: argparse.Namespace) -> List[str]:
    if args.episode_id:
        return args.episode_id
    if args.all:
        ids = list_available_episode_ids()
        if not ids:
            raise SystemExit("No transcripts found under data/processed/transcripts_*/")
        return ids
    raise SystemExit(
        "Specify --episode-id (one or many) or --all to choose episodes to label."
    )


def assign_worker(
    episode_id: str,
    config: Dict[str, dict],
    known_embeddings: Dict[str, np.ndarray],
    *,
    threshold: float,
    min_duration: float,
    max_segments: int,
    force: bool,
    strategy: str,
) -> Tuple[str, bool, Optional[str]]:
    if not force and episode_has_named_transcript(episode_id):
        return episode_id, True, "skip"
    try:
        assign_speakers_to_episode(
            episode_id,
            config,
            known_embeddings,
            threshold=threshold,
            min_duration=min_duration,
            max_segments=max_segments,
            strategy=strategy,
        )
        return episode_id, True, None
    except SystemExit as exc:  # raised when required files missing
        return episode_id, False, str(exc)
    except Exception as exc:
        return episode_id, False, str(exc)


def main() -> int:
    args = parse_args()
    set_transcripts_dir(args.transcription)
    require_ffmpeg()
    targets = resolve_targets(args)
    if args.limit is not None:
        targets = targets[: args.limit]
    if not targets:
        print("No episodes selected.")
        return 0

    config = load_config()
    known_embeddings = load_known_embeddings(config, strategy=args.strategy)

    with ThreadPoolExecutor(max_workers=max(1, args.max_concurrency)) as executor:
        futures = [
            executor.submit(
                assign_worker,
                episode_id,
                config,
                known_embeddings,
                threshold=args.threshold,
                min_duration=args.min_duration,
                max_segments=args.segments_per_speaker,
                force=args.force,
                strategy=args.strategy,
            )
            for episode_id in targets
        ]

        for future in as_completed(futures):
            episode_id, success, message = future.result()
            if message == "skip":
                print(
                    f"[{episode_id}] Skipping: transcript_named.txt already exists (use --force to re-run)"
                )
                continue
            if not success:
                print(f"[{episode_id}] ❌ {message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
