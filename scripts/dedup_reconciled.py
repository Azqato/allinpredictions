"""Fix-up pass: reconcile_batch1.py used too narrow a timestamp window and created
duplicate entries where a manually-written prediction and a reference-derived prediction
describe the same moment. This script detects reference-derived entries (quote text
matches data/processed verbatim) that sit close in time to a differently-worded entry
for the same speaker, and drops the reference-derived duplicate, keeping the original.
Exact duplicate reference entries (identical quote, same speaker, close time) are
collapsed to one.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed" / "transcripts_speechmatics"
PRED_DIR = ROOT / "rewrite" / "data" / "predictions"

EPISODES = [f"E{i:03d}" for i in range(0, 11)]  # E000-E010
DUP_WINDOW_SECONDS = 90


def to_seconds(ts: str) -> float:
    parts = [float(p) for p in ts.strip().split(":")]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    h, m, s = parts
    return h * 3600 + m * 60 + s


def main():
    total_removed = 0
    for ep in EPISODES:
        pred_path = PRED_DIR / f"{ep}.json"
        ref_path = PROCESSED / f"ALLIN-{ep}" / "predictions.json"
        if not pred_path.exists() or not ref_path.exists():
            continue

        data = json.load(open(pred_path, encoding="utf-8"))
        ref = json.load(open(ref_path, encoding="utf-8"))
        ref_quotes = {rp["quote"] for rp in ref["predictions"]}

        preds = data["predictions"]
        for p in preds:
            p["_sec"] = to_seconds(p["timestamp"])
            p["_is_ref"] = p["quote"] in ref_quotes

        to_remove = set()
        n = len(preds)
        for i in range(n):
            if id(preds[i]) in to_remove or not preds[i]["_is_ref"]:
                continue
            for j in range(n):
                if i == j or id(preds[j]) in to_remove:
                    continue
                if preds[j]["who"] != preds[i]["who"]:
                    continue
                if abs(preds[j]["_sec"] - preds[i]["_sec"]) > DUP_WINDOW_SECONDS:
                    continue
                if preds[j]["quote"] == preds[i]["quote"]:
                    # exact duplicate: drop whichever we're currently looking at (i)
                    to_remove.add(id(preds[i]))
                    break
                if not preds[j]["_is_ref"]:
                    # a manually-written entry already covers this moment
                    to_remove.add(id(preds[i]))
                    break

        kept = [p for p in preds if id(p) not in to_remove]
        removed_count = len(preds) - len(kept)
        for p in kept:
            del p["_sec"]
            del p["_is_ref"]

        if removed_count:
            kept.sort(key=lambda p: to_seconds(p["timestamp"]))
            counts = {}
            for p in kept:
                counts[p["who"]] = counts.get(p["who"], 0) + 1
            data["predictions"] = kept
            data["meta"]["count"] = len(kept)
            data["meta"]["count_by_who"] = counts
            json.dump(data, open(pred_path, "w", encoding="utf-8"), indent=2)
            print(f"{ep}: removed {removed_count} duplicate(s), {len(kept)} remain")
            total_removed += removed_count
        else:
            print(f"{ep}: no duplicates found")

    print(f"\nTotal removed: {total_removed}")


if __name__ == "__main__":
    main()
