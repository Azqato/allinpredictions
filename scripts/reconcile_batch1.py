"""One-off: reconcile already-extracted rewrite predictions (E000-E010) against the
paid-pipeline reference data in data/processed/transcripts_speechmatics, appending any
predictions that were missed during manual extraction. Does not touch existing entries.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed" / "transcripts_speechmatics"
PRED_DIR = ROOT / "rewrite" / "data" / "predictions"

EPISODES = [f"E{i:03d}" for i in range(0, 11)]  # E000-E010
MATCH_WINDOW_SECONDS = 20


def to_seconds(ts: str) -> float:
    ts = ts.strip()
    parts = ts.split(":")
    parts = [float(p) for p in parts]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    h, m, s = parts
    return h * 3600 + m * 60 + s


def to_hhmmss(seconds: float) -> str:
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def main():
    total_added = 0
    for ep in EPISODES:
        pred_path = PRED_DIR / f"{ep}.json"
        ref_path = PROCESSED / f"ALLIN-{ep}" / "predictions.json"
        if not pred_path.exists() or not ref_path.exists():
            print(f"{ep}: skip (missing files)")
            continue

        existing = json.load(open(pred_path, encoding="utf-8"))
        ref = json.load(open(ref_path, encoding="utf-8"))

        existing_times = [
            (p["who"], to_seconds(p["timestamp"])) for p in existing["predictions"]
        ]

        added = []
        for rp in ref["predictions"]:
            rp_sec = to_seconds(rp["timestamp"])
            rp_who = rp["who"]
            matched = any(
                who == rp_who and abs(sec - rp_sec) <= MATCH_WINDOW_SECONDS
                for who, sec in existing_times
            )
            if matched:
                continue

            ts_hhmmss = to_hhmmss(rp_sec)
            new_entry = {
                "id": f"{rp_who}-{ts_hhmmss}",
                "who": rp_who,
                "role": "host",
                "speaker_confidence": "high",
                "quote": rp["quote"],
                "timestamp": ts_hhmmss,
                "prediction": rp["prediction"],
                "tags": rp.get("tags", []),
            }
            added.append(new_entry)

        if added:
            existing["predictions"].extend(added)
            existing["predictions"].sort(key=lambda p: to_seconds(p["timestamp"]))
            counts = {}
            for p in existing["predictions"]:
                counts[p["who"]] = counts.get(p["who"], 0) + 1
            existing["meta"]["count"] = len(existing["predictions"])
            existing["meta"]["count_by_who"] = counts
            json.dump(existing, open(pred_path, "w", encoding="utf-8"), indent=2)
            print(f"{ep}: added {len(added)} -> {[a['id'] for a in added]}")
            total_added += len(added)
        else:
            print(f"{ep}: no additions (already complete)")

    print(f"\nTotal predictions added: {total_added}")


if __name__ == "__main__":
    main()
