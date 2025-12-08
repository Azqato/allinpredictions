#!/usr/bin/env python3
"""Add categorical tags to predictions using the OpenAI API."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel

from openai import OpenAI
from openai.types.responses import ResponseOutputMessage, ResponseOutputText

from speaker_utils import CURRENT_TRANSCRIPTION_SOURCE, TRANSCRIPTION_DIRS

# Single source of truth for allowed tags.
ALLOWED_TAGS: List[str] = [
    "politics",
    "government",
    "conflict",
    "venture",
    "tech",
    "ai",
    "markets",
    "economy",
    "health",
    "climate",
    "science",
]


@dataclass
class TaggingResult:
    episode_id: str
    success: bool
    message: str


class TaggingResponseFormat(BaseModel):
    tags: List[str]


def load_predictions(path: Path) -> Dict:
    if not path.exists():
        raise SystemExit(f"predictions file not found: {path}")
    return json.loads(path.read_text())


def save_predictions(path: Path, payload: Dict) -> None:
    path.write_text(json.dumps(payload, indent=2))
    print(f"[OK] wrote tags -> {path}")


def list_episode_ids(transcription: str) -> List[str]:
    root = TRANSCRIPTION_DIRS[transcription]
    if not root.exists():
        return []
    ids: List[str] = []
    for subdir in sorted(root.iterdir()):
        if not subdir.is_dir():
            continue
        if (subdir / "predictions.json").exists():
            ids.append(subdir.name)
    return ids


def build_tag_schema() -> Dict:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "prediction_tags",
            "schema": {
                "type": "object",
                "properties": {
                    "tags": {
                        "type": "array",
                        "items": {"type": "string", "enum": ALLOWED_TAGS},
                        "minItems": 1,
                    }
                },
                "required": ["tags"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    }


def classify_tags(client: OpenAI, model: str, prediction: str, quote: str) -> List[str]:
    response = client.responses.parse(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "You classify predictions into the tag(s) that best describe them.\n"
                    "- Most predicitons should have 1 or 2 tags, in rare cases 3."
                    "- Only select the most relevant (e.g. a prediction about Consumer Price Index should be 'economy' and not 'markets').\n"
                    "- Don't force tags (e.g. a joke about a cohost gaining weight should not be tagged 'health').\n"
                    "- If no tags are relevant, simply emit an empty list."
                    f"- Only emit allowed tags: {', '.join(ALLOWED_TAGS)}"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Normalized prediction: {prediction}\n"
                    f'Original quote: "{quote}"\n'
                    "Respond with a JSON object containing a `tags` array."
                ),
            },
        ],
        text_format=TaggingResponseFormat,
    )
    parsed = response.output_parsed
    if parsed is None:
        raise SystemExit("Failed to parse prediction extraction response")
    unknown_tags = set(parsed.tags) - set(ALLOWED_TAGS) if parsed else None
    if unknown_tags:
        print(f"Found unknown tags: {unknown_tags}")
    valid_tags = [tag for tag in parsed.tags if tag in ALLOWED_TAGS]
    return valid_tags


def tag_episode(
    client: OpenAI,
    model: str,
    transcription: str,
    episode_id: str,
    *,
    force: bool,
) -> TaggingResult:
    root = TRANSCRIPTION_DIRS[transcription]
    predictions_path = root / episode_id / "predictions.json"
    payload = load_predictions(predictions_path)
    predictions = payload.get("predictions") or []
    if not isinstance(predictions, list):
        return TaggingResult(episode_id, False, "predictions payload malformed")

    changed = False
    for item in predictions:
        if not isinstance(item, dict):
            continue
        if item.get("tags") and not force:
            continue
        tags = classify_tags(
            client=client,
            model=model,
            prediction=item.get("prediction") or "",
            quote=item.get("quote") or "",
        )
        item["tags"] = tags
        changed = True

    if changed:
        save_predictions(predictions_path, payload)
        return TaggingResult(episode_id, True, "updated")
    return TaggingResult(episode_id, True, "no changes (existing tags present)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--episode-id",
        action="append",
        help="Episode ID, e.g., ALLIN-E001 (can be repeated)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process every episode that has predictions.json",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on number of episodes when using --all",
    )
    parser.add_argument(
        "--transcription",
        choices=sorted(TRANSCRIPTION_DIRS),
        default=CURRENT_TRANSCRIPTION_SOURCE,
        help="Which transcript source to read",
    )
    parser.add_argument(
        "--model",
        default="gpt-5.1-2025-11-13",
        help="OpenAI model to use for tagging",
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=4,
        help="Maximum parallel tagging jobs",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run tagging even if tags already exist",
    )
    return parser.parse_args()


def resolve_episode_ids(args: argparse.Namespace) -> List[str]:
    if not args.all and not args.episode_id:
        raise SystemExit("Specify --episode-id (repeatable) or --all")
    if args.episode_id and args.all:
        raise SystemExit("Use either --episode-id or --all, not both")

    if args.all:
        ids = list_episode_ids(args.transcription)
        if args.limit is not None:
            ids = ids[: args.limit]
        return ids
    # ensure uniqueness while preserving order
    seen = set()
    out: List[str] = []
    for eid in args.episode_id:
        if eid in seen:
            continue
        seen.add(eid)
        out.append(eid)
    return out


def main() -> None:
    args = parse_args()
    episode_ids = resolve_episode_ids(args)
    if not episode_ids:
        raise SystemExit("No episodes to process.")

    client = OpenAI()

    results: List[TaggingResult] = []
    with ThreadPoolExecutor(max_workers=max(1, args.max_concurrency)) as executor:
        futures = {
            executor.submit(
                tag_episode,
                client,
                args.model,
                args.transcription,
                episode_id,
                force=args.force,
            ): episode_id
            for episode_id in episode_ids
        }
        for future in as_completed(futures):
            episode_id = futures[future]
            try:
                result = future.result()
            except Exception as exc:  # pylint: disable=broad-except
                results.append(
                    TaggingResult(
                        episode_id=episode_id, success=False, message=str(exc)
                    )
                )
                continue
            results.append(result)

    failures = [r for r in results if not r.success]
    for res in results:
        status = "OK" if res.success else "FAIL"
        print(f"[{status}] {res.episode_id}: {res.message}")
    if failures:
        raise SystemExit(f"{len(failures)} episode(s) failed tagging")


if __name__ == "__main__":
    main()
