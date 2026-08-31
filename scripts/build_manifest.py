#!/usr/bin/env python3
"""Build/refresh data/manifest.json: per-episode pipeline status tracking.

Enables incremental, idempotent runs (PRD.md section 6.8): re-running the
pipeline after adding new episodes should only touch what's new.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=Path, default=Path("data/episodes.json"))
    parser.add_argument("--transcripts-dir", type=Path, default=Path("data/transcripts"))
    parser.add_argument("--chunks-dir", type=Path, default=Path("data/chunks"))
    parser.add_argument("--predictions-dir", type=Path, default=Path("data/predictions"))
    parser.add_argument("--checks-dir", type=Path, default=Path("data/checks"))
    parser.add_argument("--out", type=Path, default=Path("data/manifest.json"))
    args = parser.parse_args(argv)

    episodes = json.loads(args.episodes.read_text()) if args.episodes.exists() else []

    existing: Dict[str, Any] = {}
    if args.out.exists():
        try:
            prev = json.loads(args.out.read_text())
            existing = {row["episode_id"]: row for row in prev.get("episodes", [])}
        except Exception:
            existing = {}

    rows: List[Dict[str, Any]] = []
    counts = {
        "captions_fetched": 0,
        "chunked": 0,
        "predictions_extracted": 0,
        "validated": 0,
        "legacy_no_transcript": 0,
    }

    for ep in episodes:
        episode_id = ep["episode_id"]
        prev_row = existing.get(episode_id, {})

        captions_fetched = (args.transcripts_dir / f"{episode_id}.json").exists()
        chunked = (args.chunks_dir / episode_id).exists() and any(
            (args.chunks_dir / episode_id).glob("chunk_*.txt")
        )
        predictions_extracted = (args.predictions_dir / f"{episode_id}.json").exists()
        validated = (args.checks_dir / f"{episode_id}.json").exists()
        # True for episodes processed in an earlier phase of this project where
        # predictions/checks were extracted and retained but the raw transcript/
        # chunk files were not (or have since been pruned). NOT the same as
        # "unprocessed" -- these episodes are fully done, just missing their raw
        # source artifacts. See docs/PRD.md notes on manifest interpretation.
        legacy_no_transcript = predictions_extracted and not (captions_fetched and chunked)

        row = {
            "episode_id": episode_id,
            "title": ep.get("title"),
            "video_id": ep.get("video_id"),
            "captions_fetched": captions_fetched,
            "chunked": chunked,
            "predictions_extracted": predictions_extracted,
            "validated": validated,
            "legacy_no_transcript": legacy_no_transcript,
            "first_seen": prev_row.get("first_seen", now_iso()),
            "last_checked": now_iso(),
        }
        rows.append(row)
        for key in counts:
            if row[key]:
                counts[key] += 1

    manifest = {
        "generated_at": now_iso(),
        "episode_count": len(episodes),
        "status_counts": counts,
        "notes": (
            "captions_fetched/chunked are computed fresh from file existence on every "
            "run, so they are never stale by construction. However, they legitimately "
            "read false for episodes marked legacy_no_transcript=true: these were "
            "processed in an earlier phase of the project, have real predictions_extracted "
            "and validated=true, but their raw transcript/chunk files were never retained. "
            "Do not treat captions_fetched=false/chunked=false as 'unprocessed' without "
            "also checking predictions_extracted -- use predictions_extracted (or the "
            "presence of data/predictions/{id}.json and data/checks/{id}.json) as the "
            "ground truth for pipeline completeness."
        ),
        "episodes": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, indent=2))
    print(
        f"Wrote {args.out}: {len(episodes)} episodes, "
        f"captions={counts['captions_fetched']} chunked={counts['chunked']} "
        f"predictions={counts['predictions_extracted']} validated={counts['validated']} "
        f"(legacy_no_transcript={counts['legacy_no_transcript']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
