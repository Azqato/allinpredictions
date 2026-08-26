#!/usr/bin/env python3
"""Cross-check the rewrite's independently-derived episode/YouTube matches
against the old repo's already-resolved data/processed/all_in_episodes.json.

Per PRD.md section 14.4: the rewrite derives its own matching from scratch,
then diffs against the old repo's output purely as a free correctness check
(and as QA evidence for the eventual old-pipeline retirement decision).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (title or "").lower())


def load_json(path: Path) -> Any:
    if not path.exists():
        raise SystemExit(f"Not found: {path}")
    return json.loads(path.read_text())


def extract_video_id(youtube_url: Optional[str]) -> Optional[str]:
    if not youtube_url:
        return None
    m = re.search(r"[?&]v=([\w-]{6,})", youtube_url)
    if m:
        return m.group(1)
    m = re.search(r"youtu\.be/([\w-]{6,})", youtube_url)
    return m.group(1) if m else None


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rewrite-episodes", type=Path, default=Path("data/episodes.json"))
    parser.add_argument(
        "--old-episodes",
        type=Path,
        default=Path("../data/processed/all_in_episodes.json"),
        help="Path to the old repo's resolved episode index",
    )
    parser.add_argument("--out", type=Path, default=Path("data/episode_source_diff.json"))
    args = parser.parse_args(argv)

    rewrite_eps = load_json(args.rewrite_episodes)
    if not args.old_episodes.exists():
        print(f"Old repo episode index not found at {args.old_episodes} -- skipping cross-check.")
        args.out.write_text(json.dumps({"skipped": True, "reason": "old index not found"}, indent=2))
        return 0
    old_eps = load_json(args.old_episodes)

    old_by_title = {normalize_title(e.get("title")): e for e in old_eps}

    matched, agree, disagree, old_missing = [], [], [], []
    for ep in rewrite_eps:
        key = normalize_title(ep.get("title"))
        old = old_by_title.get(key)
        if old is None:
            old_missing.append({"episode_id": ep["episode_id"], "title": ep["title"]})
            continue
        matched.append(ep["episode_id"])
        old_vid = extract_video_id(old.get("youtube_url"))
        new_vid = ep.get("video_id")
        row = {
            "episode_id": ep["episode_id"],
            "title": ep["title"],
            "rewrite_video_id": new_vid,
            "old_video_id": old_vid,
            "rewrite_match_method": ep.get("match_method"),
        }
        if old_vid and new_vid and old_vid == new_vid:
            agree.append(row)
        else:
            disagree.append(row)

    report = {
        "summary": {
            "rewrite_episode_count": len(rewrite_eps),
            "old_episode_count": len(old_eps),
            "matched_by_title": len(matched),
            "agree": len(agree),
            "disagree": len(disagree),
            "in_rewrite_not_in_old": len(old_missing),
        },
        "disagreements": disagree,
        "not_found_in_old_index": old_missing,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2))

    print(
        f"Cross-check: {len(agree)} agree, {len(disagree)} disagree, "
        f"{len(old_missing)} not found in old index (of {len(rewrite_eps)} rewrite episodes)."
    )
    print(f"Wrote {args.out}")
    if disagree:
        print("NOTE: disagreements should be resolved by hand against allin.com/episodes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
