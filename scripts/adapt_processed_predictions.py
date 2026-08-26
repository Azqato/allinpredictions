"""Adapter: convert data/processed/transcripts_speechmatics/<dir>/predictions.json
(paid-pipeline output from the original repo) into the rewrite's predictions schema.

Only raw predictions are carried over -- NOT predictions_check.json / validation
results, since all predictions will be independently revalidated later.

Speaker normalization:
  - Known host name variants (chamath/sacks/jason/friedberg incl. full names, different
    casing, underscores) collapse to the canonical host key, role="host".
  - Single-letter/unresolved Speechmatics speaker codes are looked up in that episode's
    speaker_map.json; if it resolves to a known name, use that. Otherwise the entry is
    kept with who="unknown-<letter>" and speaker_confidence="low" rather than dropped,
    so it surfaces for manual review instead of silently losing a prediction.
  - Everything else is treated as a guest, role="guest", name lowercased/underscored.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed" / "transcripts_speechmatics"
PRED_DIR = ROOT / "rewrite" / "data" / "predictions"
MAP_PATH = ROOT / "rewrite" / "data" / "processed_episode_map.json"

ALREADY_DONE = {f"E{i:03d}" for i in range(0, 11)}  # E000-E010, manually done + reconciled

HOST_ALIASES = {
    "chamath": "chamath", "chamath palihapitiya": "chamath", "chamath_palihapitiya": "chamath",
    "sacks": "sacks", "david sacks": "sacks", "david_sacks": "sacks", "sachs": "sacks",
    "jason": "jason", "jason calacanis": "jason",
    "friedberg": "friedberg", "david friedberg": "friedberg", "freeberg": "friedberg",
}


def to_seconds(ts: str) -> float:
    parts = [float(p) for p in ts.strip().split(":")]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    h, m, s = parts
    return h * 3600 + m * 60 + s


def to_hhmmss(seconds: float) -> str:
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def resolve_who(raw_who: str, speaker_map: dict) -> tuple:
    """Returns (who, role, speaker_confidence)."""
    key = raw_who.strip().lower()
    if key in HOST_ALIASES:
        return HOST_ALIASES[key], "host", "high"

    # single-letter Speechmatics code -> look up speaker_map.json
    if re.fullmatch(r"[a-z]", key):
        entry = speaker_map.get(raw_who.strip().upper()) or speaker_map.get(raw_who.strip())
        if entry and entry.get("speaker_key"):
            mapped = entry["speaker_key"].strip().lower()
            if mapped in HOST_ALIASES:
                return HOST_ALIASES[mapped], "host", "high"
            return mapped.replace(" ", "_"), "guest", "medium"
        return f"unknown-{key}", "unknown", "low"

    # guest name (may contain trailing notes like "Nassim Taleb (quoted by sacks)")
    name = re.sub(r"\s*\(.*?\)\s*", "", raw_who).strip().lower()
    name = re.sub(r"\s+", "_", name)
    return name, "guest", "medium"


def dedupe_ids(preds):
    seen = {}
    for p in preds:
        if p["id"] in seen:
            seen[p["id"]] += 1
            p["id"] = f"{p['id']}-{seen[p['id']]}"
        else:
            seen[p["id"]] = 1


def main():
    mapping = json.load(open(MAP_PATH, encoding="utf-8"))
    adapted, skipped_done, skipped_no_pred = 0, 0, 0

    for dir_name, episode_id in mapping.items():
        if episode_id in ALREADY_DONE:
            skipped_done += 1
            continue

        ref_path = PROCESSED / dir_name / "predictions.json"
        if not ref_path.exists():
            skipped_no_pred += 1
            continue

        ref = json.load(open(ref_path, encoding="utf-8"))
        speaker_map_path = PROCESSED / dir_name / "speaker_map.json"
        speaker_map = json.load(open(speaker_map_path, encoding="utf-8")) if speaker_map_path.exists() else {}

        out_preds = []
        for rp in ref["predictions"]:
            who, role, conf = resolve_who(rp["who"], speaker_map)
            ts = to_hhmmss(to_seconds(rp["timestamp"]))
            out_preds.append({
                "id": f"{who}-{ts}",
                "who": who,
                "role": role,
                "speaker_confidence": conf,
                "quote": rp["quote"],
                "timestamp": ts,
                "prediction": rp["prediction"],
                "tags": rp.get("tags", []),
            })

        out_preds.sort(key=lambda p: to_seconds(p["timestamp"]))
        dedupe_ids(out_preds)

        counts = {}
        for p in out_preds:
            counts[p["who"]] = counts.get(p["who"], 0) + 1

        out = {
            "meta": {"count": len(out_preds), "count_by_who": counts},
            "predictions": out_preds,
        }
        out_path = PRED_DIR / f"{episode_id}.json"
        json.dump(out, open(out_path, "w", encoding="utf-8"), indent=2)
        adapted += 1

    print(f"Adapted: {adapted}")
    print(f"Skipped (already manually done): {skipped_done}")
    print(f"Skipped (no predictions.json in source): {skipped_no_pred}")


if __name__ == "__main__":
    main()
