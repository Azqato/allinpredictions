"""One-off: map data/processed/transcripts_speechmatics/<dir> to rewrite episode_ids.

Matches on exact RSS 'published' string first, falls back to published_iso date + title
overlap for anything unmatched. Prints a JSON mapping and a report of unmatched dirs.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed" / "transcripts_speechmatics"
ARCHIVE = ROOT / "rewrite" / "data" / "episodes_full_archive.json"


def normalize_title(t: str) -> set:
    words = re.findall(r"[a-z0-9]+", t.lower())
    return set(w for w in words if len(w) > 2)


def main():
    archive = json.load(open(ARCHIVE, encoding="utf-8"))
    by_published = {}
    for e in archive:
        by_published.setdefault(e["published"], []).append(e)

    mapping = {}
    unmatched = []

    for d in sorted(PROCESSED.iterdir()):
        if not d.is_dir():
            continue
        meta_path = d / "metadata.json"
        if not meta_path.exists():
            unmatched.append((d.name, "no metadata.json"))
            continue
        meta = json.load(open(meta_path, encoding="utf-8"))
        published = meta.get("published")
        title = meta.get("title", "")

        candidates = by_published.get(published, [])
        if len(candidates) == 1:
            mapping[d.name] = candidates[0]["episode_id"]
            continue
        if len(candidates) > 1:
            tset = normalize_title(title)
            best = max(candidates, key=lambda e: len(tset & normalize_title(e["title"])))
            mapping[d.name] = best["episode_id"]
            continue

        # fallback: same date, best title overlap across whole archive
        date_prefix = meta.get("published", "")[:16]  # "Fri, 16 May 2025"
        date_candidates = [e for e in archive if e["published"][:16] == date_prefix]
        if date_candidates:
            tset = normalize_title(title)
            scored = sorted(date_candidates, key=lambda e: -len(tset & normalize_title(e["title"])))
            best = scored[0]
            overlap = len(tset & normalize_title(best["title"]))
            if overlap >= 2:
                mapping[d.name] = best["episode_id"]
                continue

        unmatched.append((d.name, f"no archive match for published={published!r} title={title!r}"))

    print(f"Matched: {len(mapping)}")
    print(f"Unmatched: {len(unmatched)}")
    for name, reason in unmatched:
        print(f"  UNMATCHED {name}: {reason}")

    out_path = ROOT / "rewrite" / "data" / "processed_episode_map.json"
    json.dump(mapping, open(out_path, "w", encoding="utf-8"), indent=2)
    print(f"\nWrote mapping to {out_path}")


if __name__ == "__main__":
    main()
