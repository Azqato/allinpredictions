#!/usr/bin/env python3
"""Extract and validate podcast predictions from transcripts."""
from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from openai import OpenAI
from openai.types.responses import (
    Response as OpenAIResponse,
    ResponseOutputMessage,
    ResponseOutputText,
)
from openai.types.responses.response_output_text import Annotation
from pydantic import BaseModel, Field
from speaker_utils import (
    TRANSCRIPTION_DIRS,
    CURRENT_TRANSCRIPTION_SOURCE,
)
from dotenv import load_dotenv


class PredictionWorkerResult(BaseModel):
    episode_id: str
    success: bool
    message: Optional[str]


class PredictionItem(BaseModel):
    id: str = Field(
        ...,
        description="Deterministic ID like speaker-timestamp (e.g., A-00:12:34.500)",
    )
    who: str = Field(
        ..., description="Speaker key (one of chamath|friedberg|jason|sacks|...)"
    )
    quote: str = Field(..., description="Exact quote from the transcript")
    timestamp: str = Field(..., description="Start timestamp hh:mm:ss.mmm of the quote")
    prediction: str = Field(
        ...,
        description="Clean, precise prediction suitable for later validation; include timeframes",
    )


class PredictionExtraction(BaseModel):
    predictions: List[PredictionItem] = Field(
        default_factory=list, description="List of predictions in this chunk"
    )


class PredictionValidation(BaseModel):
    id: str
    result: str
    explanation: str
    sources: List[Annotation]
    grok_result: Optional[str] = None
    grok_explanation: Optional[str] = None


@dataclass
class TranscriptChunk:
    chunk_id: int
    text: str
    start_idx: int
    end_idx: int


def format_timestamp(ms: Optional[int]) -> str:
    if ms is None:
        return "??:??:??.???"
    seconds, ms_part = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{ms_part:03d}"


def load_segments(transcription: str, episode_id: str) -> List[Dict]:
    if transcription not in TRANSCRIPTION_DIRS:
        valid = ", ".join(sorted(TRANSCRIPTION_DIRS))
        raise SystemExit(
            f"Unknown transcription source '{transcription}'. Choose from: {valid}"
        )
    segments_path = TRANSCRIPTION_DIRS[transcription] / episode_id / "segments.json"
    if not segments_path.exists():
        raise SystemExit(
            f"Segments not found at {segments_path}. Transcribe the episode first."
        )
    return json.loads(segments_path.read_text())


def load_metadata(transcription: str, episode_id: str) -> Dict[str, str]:
    meta_path = TRANSCRIPTION_DIRS[transcription] / episode_id / "metadata.json"
    if not meta_path.exists():
        return {}
    try:
        return json.loads(meta_path.read_text())
    except Exception:
        return {}


def load_speaker_map(transcription: str, episode_id: str) -> Dict[str, Dict]:
    map_path = TRANSCRIPTION_DIRS[transcription] / episode_id / "speaker_map.json"
    if not map_path.exists():
        return {}
    try:
        return json.loads(map_path.read_text())
    except Exception:
        return {}


def build_lines(segments: List[Dict]) -> List[str]:
    lines: List[str] = []
    for seg in segments:
        speaker = seg.get("speaker_label") or seg.get("speaker") or "Speaker"
        start_ms = seg.get("start_ms") or int(seg.get("start", 0) * 1000)
        ts = format_timestamp(start_ms)
        text = seg.get("text", "").strip()
        lines.append(f"{speaker} [{ts}]: {text}")
    return lines


def chunk_lines(
    lines: List[str],
    *,
    max_chars: int,
    overlap_lines: int,
) -> List[TranscriptChunk]:
    chunks: List[TranscriptChunk] = []
    buffer: List[str] = []
    start_idx = 0
    chunk_id = 1
    for idx, line in enumerate(lines):
        candidate = "\n".join(buffer + [line])
        if buffer and len(candidate) > max_chars:
            chunk_text = "\n".join(buffer)
            end_idx = start_idx + len(buffer) - 1
            chunks.append(TranscriptChunk(chunk_id, chunk_text, start_idx, end_idx))
            chunk_id += 1
            # start new buffer with overlap
            buffer = buffer[-overlap_lines:] if overlap_lines else []
            start_idx = idx - len(buffer)
        buffer.append(line)
    if buffer:
        end_idx = start_idx + len(buffer) - 1
        chunks.append(TranscriptChunk(chunk_id, "\n".join(buffer), start_idx, end_idx))
    return chunks


def ensure_openai_key(env_path: Path = Path(".env")) -> None:
    if os.getenv("OPENAI_API_KEY"):
        return
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            if key.strip() == "OPENAI_API_KEY" and val.strip():
                os.environ["OPENAI_API_KEY"] = val.strip()
                return
    raise SystemExit("Missing OPENAI_API_KEY (set env var or add to .env)")


def ensure_grok_key(env_path: Path = Path(".env")) -> None:
    if os.getenv("XAI_API_KEY"):
        return
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            if key.strip() == "XAI_API_KEY" and val.strip():
                os.environ["XAI_API_KEY"] = val.strip()
                return
    raise SystemExit("Missing XAI_API_KEY (set env var or add to .env)")


def extract_predictions_from_chunk(
    client: OpenAI,
    model: str,
    chunk: TranscriptChunk,
    *,
    episode_title: Optional[str],
    episode_date: Optional[str],
) -> List[PredictionItem]:
    context_header = ""
    if episode_title or episode_date:
        parts = []
        if episode_title:
            parts.append(f"Title: {episode_title}")
        if episode_date:
            parts.append(f"Release date: {episode_date}")
        context_header = "\n".join(parts) + "\n\n"
    response = client.responses.parse(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "Your goal is to extract explicit predictions from historical podcast transcript. "
                    "Return only statements that are concrete predictions about the future (events, outcomes, metrics), and"
                    " don't waste time with vague predictions that would be difficult to falsify."
                    "A later verification step will check if these predictions were accurate, so it's important to "
                    "be precise, include any relevant details and timeframes."
                ),
            },
            {
                "role": "user",
                "content": f"{context_header}Transcript chunk {chunk.chunk_id}:\n{chunk.text}",
            },
        ],
        text_format=PredictionExtraction,
        reasoning={"effort": "low"},
    )
    ext = response.output_parsed
    if ext is None:
        raise SystemExit("Failed to parse prediction extraction response")
    return ext.predictions


def dedupe_predictions(predictions: List[PredictionItem]) -> List[PredictionItem]:
    seen = {}
    for pred in predictions:
        seen[pred.id] = pred
    return list(seen.values())


def save_predictions(episode_dir: Path, predictions: List[PredictionItem]) -> None:
    out_path = episode_dir / "predictions.json"
    count_by_who: Dict[str, int] = {}
    for p in predictions:
        count_by_who[p.who] = count_by_who.get(p.who, 0) + 1
    payload = {
        "meta": {"count": len(predictions), "count_by_who": count_by_who},
        "predictions": [p.model_dump() for p in predictions],
    }
    out_path.write_text(json.dumps(payload, indent=2))
    print(f"[OK] Saved predictions to {out_path}")


def apply_speaker_map(
    predictions: List[PredictionItem], speaker_map: Dict[str, Dict]
) -> List[PredictionItem]:
    if not speaker_map:
        return predictions
    mapped: List[PredictionItem] = []
    for pred in predictions:
        label = pred.who
        entry = speaker_map.get(label)
        if entry:
            friendly = entry.get("speaker_key") or entry.get("display_name")
            if friendly:
                mapped.append(pred.model_copy(update={"who": friendly}))
                continue
        mapped.append(pred)
    return mapped


def validate_prediction(
    client: OpenAI,
    model: str,
    prediction: PredictionItem,
    *,
    episode_title: Optional[str],
    episode_date: Optional[str],
) -> PredictionValidation:
    context_parts = []
    if episode_title:
        context_parts.append(f"Podcast title: {episode_title}")
    if episode_date:
        context_parts.append(f"Podcast release date: {episode_date}")
    header = "\n".join(context_parts)
    response: OpenAIResponse = client.responses.create(
        model=model,
        reasoning={"effort": "medium"},
        tools=[{"type": "web_search"}],
        input=[
            {
                "role": "system",
                "content": (
                    "You should verify whether a prediction from a podcast came true. "
                    "Use current knowledge and web search; be concise.\n\n"
                    # Using strucutred outputs breaks the web_search tool (no annotations
                    # are returned in the response – so instead we'll attempt this manually
                    # and hope for the best)
                    "You should output a single JSON object with the fields:\n"
                    "- result: One of: 'right', 'wrong', 'inconclusive' (too early), 'ambiguous' (cannot be determined even though enough time passed)\n"
                    "- explanation: Rationale for the result, be sure to reference your sources. Can use basic markdown formatting (bold, italic, hyperlinks, lists), no headings though.\n\n"
                    "Do not output *anything* other than the JSON object."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"{header}\n\n"
                    f"Predictor: {prediction.who}\n"
                    f"Prediction (normalized): {prediction.prediction}\n"
                    f'Original quote: "{prediction.quote}"\n'
                ),
            },
        ],
    )
    parsed: PredictionValidation | None = None
    for item in response.output or []:
        if isinstance(item, ResponseOutputMessage):
            for content_item in item.content:
                if isinstance(content_item, ResponseOutputText):
                    parsed_dict = json.loads(content_item.text)
                    parsed = PredictionValidation(
                        id=prediction.id,
                        result=parsed_dict.get("result"),
                        explanation=parsed_dict.get("explanation"),
                        sources=content_item.annotations,
                    )
    if parsed is None:
        raise SystemExit(
            f"Failed to parse prediction extraction response: {response.model_dump_json(indent=2)}"
        )
    return parsed


def validate_prediction_grok(
    prediction: PredictionItem,
    *,
    episode_title: Optional[str],
    episode_date: Optional[str],
    model: str = "grok-4-1-fast",
) -> Tuple[str, str]:
    try:
        from xai_sdk import Client  # type: ignore
        from xai_sdk.chat import user, system  # type: ignore
        from xai_sdk.tools import web_search  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(
            "xai-sdk is required for --grok validation. Install dependencies."
        ) from exc

    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        raise SystemExit("Set XAI_API_KEY to use --grok validation.")

    prompt = (
        "You should verify whether a prediction from a podcast came true. "
        "Use current knowledge and web search; be concise.\n\n"
        "You should output a single JSON object with the fields:\n"
        "- result: One of: 'right', 'wrong', 'inconclusive' (too early), 'ambiguous' (cannot be determined even though enough time passed)\n"
        "- explanation: Rationale for the result, be sure to reference your sources. Can use basic markdown formatting (bold, italic, hyperlinks, lists), no headings though.\n\n"
        "Output only the raw JSON object – do not include any other preamble, formatting, or follow-ups outside of the JSON object."
    )

    header_parts = []
    if episode_title:
        header_parts.append(f"Podcast title: {episode_title}")
    if episode_date:
        header_parts.append(f"Podcast release date: {episode_date}")
    header = "\n".join(header_parts)

    client = Client(api_key=api_key)
    chat = client.chat.create(
        model=model,
        tools=[web_search()],
    )
    chat.append(system(prompt))
    chat.append(
        user(
            f"{header}\n\n"
            f"Predictor: {prediction.who}\n"
            f"Prediction (normalized): {prediction.prediction}\n"
            f'Original quote: "{prediction.quote}"\n'
        )
    )

    response = None
    for response, _chunk in chat.stream():
        pass
    if response is None or not response.content:
        raise SystemExit("No response from Grok validation.")
    text = response.content
    if isinstance(text, list):
        text = "".join(getattr(part, "text", "") for part in text)
    if not isinstance(text, str):
        raise ValueError("Unexpected Grok response content")
    if not text.strip():
        raise ValueError("Empty response text from Grok.")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse Grok JSON: {text}") from exc
    return parsed.get("result"), parsed.get("explanation")


def list_available_episode_ids(transcription: str) -> List[str]:
    root = TRANSCRIPTION_DIRS[transcription]
    if not root.exists():
        return []
    ids: List[str] = []
    for subdir in sorted(root.iterdir()):
        if not subdir.is_dir():
            continue
        if (subdir / "segments.json").exists():
            ids.append(subdir.name)
    return ids


def load_predictions_file(transcription: str, episode_id: str) -> Optional[Dict]:
    path = TRANSCRIPTION_DIRS[transcription] / episode_id / "predictions.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def load_prediction_checks(
    transcription: str, episode_id: str
) -> Dict[str, Dict[str, str]]:
    path = TRANSCRIPTION_DIRS[transcription] / episode_id / "predictions_check.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        items = data.get("predictions", [])
        return {item.get("id"): item for item in items if item.get("id")}
    except Exception:
        return {}


def save_prediction_checks(
    transcription: str,
    episode_id: str,
    checks: List[PredictionValidation],
) -> None:
    path = TRANSCRIPTION_DIRS[transcription] / episode_id / "predictions_check.json"
    count_by_result: Dict[str, int] = {}
    for c in checks:
        count_by_result[c.result] = count_by_result.get(c.result, 0) + 1
    payload = {
        "meta": {"count": len(checks), "count_by_result": count_by_result},
        "predictions": [c.model_dump() for c in checks],
    }
    path.write_text(json.dumps(payload, indent=2))
    print(f"[OK] Saved validation to {path}")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--episode-id",
        action="append",
        help="Episode ID, e.g., ALLIN-E001 (can be repeated)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process every episode with a transcript in the chosen source",
    )
    parser.add_argument(
        "--transcription",
        choices=sorted(TRANSCRIPTION_DIRS),
        default=CURRENT_TRANSCRIPTION_SOURCE,
        help="Which transcript source to read",
    )
    parser.add_argument(
        "--model-extract",
        default="gpt-5.1-2025-11-13",
        help="OpenAI model for extraction",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=60_000,
        help="Max characters per chunk when sending to the LLM",
    )
    parser.add_argument(
        "--overlap-lines",
        type=int,
        default=8,
        help="Number of transcript lines to overlap between chunks",
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=4,
        help="Maximum parallel prediction extraction jobs",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on number of episodes when using --all",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run even if predictions.json already exists",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Also validate predictions into predictions_check.json",
    )
    parser.add_argument(
        "--grok",
        action="store_true",
        help="When validating, also run Grok and store grok_result/grok_explanation",
    )
    parser.add_argument(
        "--model-validate",
        default="gpt-5.1-2025-11-13",
        help="OpenAI model for validation",
    )
    parser.add_argument(
        "--validate-limit",
        type=int,
        default=None,
        help="Optional cap on number of predictions to validate per episode",
    )
    parser.add_argument(
        "--validate-concurrency",
        type=int,
        default=10,
        help="Maximum parallel validation calls per episode",
    )
    parser.add_argument(
        "--has-episode-code",
        action="store_true",
        help="Skip episodes missing episode_code in all_in_episodes.json",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    ensure_openai_key()

    if not args.episode_id and not args.all:
        raise SystemExit(
            "Specify --episode-id (one or many) or --all to select episodes"
        )

    if args.all:
        targets = list_available_episode_ids(args.transcription)
    else:
        targets = args.episode_id or []

    if not targets:
        print("No episodes selected.")
        return 0

    # Optional filter: require episode_code in master index
    episodes_index_path = Path("data/processed/all_in_episodes.json")
    if args.has_episode_code and episodes_index_path.exists():
        try:
            master_index = json.loads(episodes_index_path.read_text())
            valid_ids = {
                ep.get("episode_id") or Path(ep.get("audio_filename") or "").stem
                for ep in master_index
                if ep.get("episode_code")
            }
            targets = [tid for tid in targets if tid in valid_ids]
        except Exception:
            pass

    if args.limit is not None:
        targets = targets[: args.limit]

    def worker(episode_id: str) -> PredictionWorkerResult:
        try:
            episode_dir = TRANSCRIPTION_DIRS[args.transcription] / episode_id
            predictions_path = episode_dir / "predictions.json"
            client = OpenAI()
            segments = load_segments(args.transcription, episode_id)
            metadata = load_metadata(args.transcription, episode_id)
            episode_title = metadata.get("title")
            episode_date = metadata.get("published")
            speaker_map = load_speaker_map(args.transcription, episode_id)

            # Extraction (lazy unless forced)
            if predictions_path.exists() and not args.force:
                predictions_data = load_predictions_file(args.transcription, episode_id)
                deduped: List[PredictionItem] = []
                if predictions_data:
                    for item in predictions_data.get("predictions", []):
                        deduped.append(PredictionItem(**item))
            else:
                lines = build_lines(segments)
                chunks = chunk_lines(
                    lines, max_chars=args.max_chars, overlap_lines=args.overlap_lines
                )
                if not chunks:
                    return PredictionWorkerResult(
                        episode_id=episode_id,
                        success=False,
                        message="No transcript content to process",
                    )

                predictions: List[PredictionItem] = []
                for chunk in chunks:
                    try:
                        chunk_preds = extract_predictions_from_chunk(
                            client,
                            args.model_extract,
                            chunk,
                            episode_title=episode_title,
                            episode_date=episode_date,
                        )
                    except Exception as exc:  # noqa: BLE001
                        return PredictionWorkerResult(
                            episode_id=episode_id,
                            success=False,
                            message=f"Chunk {chunk.chunk_id} failed: {exc}",
                        )
                    predictions.extend(chunk_preds)

                if not predictions:
                    return PredictionWorkerResult(
                        episode_id=episode_id,
                        success=True,
                        message="No predictions found",
                    )

                mapped = apply_speaker_map(predictions, speaker_map)
                deduped = dedupe_predictions(mapped)
                save_predictions(episode_dir, deduped)

            if not args.validate:
                return PredictionWorkerResult(
                    episode_id=episode_id, success=True, message=None
                )

            existing_checks = load_prediction_checks(args.transcription, episode_id)
            final_checks: List[PredictionValidation] = []
            validated_count = 0
            preds_to_validate: List[
                Tuple[PredictionItem, Optional[Dict], bool, bool]
            ] = []
            for pred in deduped:
                existing = existing_checks.get(pred.id)
                need_openai = args.force or existing is None
                need_grok = args.grok and (
                    args.force
                    or existing is None
                    or existing.get("grok_result") is None
                    or existing.get("grok_explanation") is None
                )
                if not need_openai and not need_grok and existing:
                    final_checks.append(PredictionValidation(**existing))
                    continue
                if (
                    need_openai
                    and args.validate_limit is not None
                    and validated_count >= args.validate_limit
                ):
                    # respect limit for new OpenAI validations, but still allow Grok if existing
                    if need_grok and existing:
                        preds_to_validate.append((pred, existing, False, True))
                    continue
                preds_to_validate.append((pred, existing, need_openai, need_grok))
                if need_openai:
                    validated_count += 1

            if preds_to_validate:

                def validate_worker(
                    p: PredictionItem,
                    existing: Optional[Dict],
                    do_openai: bool,
                    do_grok: bool,
                ) -> Tuple[
                    PredictionItem, Optional[PredictionValidation], Optional[str]
                ]:
                    try:
                        check: Optional[PredictionValidation] = None
                        if do_openai:
                            client_local = OpenAI()
                            check = validate_prediction(
                                client_local,
                                args.model_validate,
                                p,
                                episode_title=episode_title,
                                episode_date=episode_date,
                            )
                        elif existing:
                            check = PredictionValidation(**existing)
                        if do_grok:
                            ensure_grok_key()
                            grok_result, grok_explanation = validate_prediction_grok(
                                p,
                                episode_title=episode_title,
                                episode_date=episode_date,
                            )
                            if check is None:
                                check = PredictionValidation(
                                    id=p.id,
                                    result="unvalidated",
                                    explanation="",
                                    sources=[],
                                )
                            check.grok_result = grok_result
                            check.grok_explanation = grok_explanation
                        return p, check, None
                    except Exception as exc:  # noqa: BLE001
                        return p, None, str(exc)

                with ThreadPoolExecutor(
                    max_workers=max(1, args.validate_concurrency)
                ) as vexec:
                    vfutures = {
                        vexec.submit(
                            validate_worker, p, existing, do_openai, do_grok
                        ): p
                        for (p, existing, do_openai, do_grok) in preds_to_validate
                    }
                    for vfut in as_completed(vfutures):
                        pred_obj = vfutures[vfut]
                        _, check, err = vfut.result()
                        if err:
                            return PredictionWorkerResult(
                                episode_id=episode_id,
                                success=False,
                                message=f"Validation failed for {pred_obj.id}: {err}",
                            )
                        if check:
                            final_checks.append(check)

            save_prediction_checks(args.transcription, episode_id, final_checks)
            return PredictionWorkerResult(
                episode_id=episode_id, success=True, message=None
            )
        except Exception as exc:  # noqa: BLE001
            return PredictionWorkerResult(
                episode_id=episode_id, success=False, message=str(exc)
            )

    with ThreadPoolExecutor(max_workers=max(1, args.max_concurrency)) as executor:
        futures = {executor.submit(worker, ep): ep for ep in targets}
        for future in as_completed(futures):
            episode_id = futures[future]
            result = future.result()
            if not result.success:
                print(f"[{episode_id}] ❌ {result.message}")
            elif result.message:
                print(f"[{episode_id}] {result.message}")
            else:
                msg = "✅ Predictions saved"
                if args.validate:
                    msg = "✅ Predictions saved and validated"
                print(f"[{episode_id}] {msg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
