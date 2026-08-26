#!/usr/bin/env python3
"""Normalize raw caption cues into readable timestamped lines and split into
Claude-sized chunks. Pure Python, deterministic, no LLM calls.

Ports the shape of the original repo's build_lines/chunk_lines helpers, but
reads caption cues (no speaker_label -- see PRD.md section 6.4) instead of
diarized ASR segments, and uses smaller chunk sizes tuned for a Claude Code
turn budget rather than an API context window.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List


def format_timestamp(seconds: float) -> str:
    total = int(round(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def merge_cues_to_lines(cues: List[dict], *, gap_seconds: float = 2.5) -> List[str]:
    """Merge consecutive caption cues into readable timestamped lines.

    YouTube auto-captions often arrive as short overlapping fragments; we
    coalesce cues into sentence-ish chunks, starting a new line whenever
    there's a meaningful pause (gap_seconds) or the buffer gets long.
    """
    lines: List[str] = []
    buf: List[str] = []
    buf_start: float | None = None
    last_end: float | None = None

    def flush() -> None:
        nonlocal buf, buf_start
        if buf and buf_start is not None:
            text = " ".join(buf).strip()
            text = re.sub(r"\s+", " ", text)
            if text:
                lines.append(f"[{format_timestamp(buf_start)}] {text}")
        buf, buf_start = [], None

    for cue in cues:
        start = float(cue["start_seconds"])
        end = start + float(cue.get("duration_seconds", 0.0))
        text = (cue.get("text") or "").strip()
        if not text:
            continue
        if buf_start is None:
            buf_start = start
        elif last_end is not None and (start - last_end) > gap_seconds:
            flush()
            buf_start = start
        buf.append(text)
        if sum(len(t) for t in buf) > 400:
            flush()
        last_end = end
    flush()
    return lines


@dataclass
class Chunk:
    chunk_id: int
    text: str


def chunk_lines(lines: List[str], *, max_chars: int, overlap_lines: int) -> List[Chunk]:
    chunks: List[Chunk] = []
    buffer: List[str] = []
    chunk_id = 1
    for line in lines:
        candidate_len = len("\n".join(buffer + [line]))
        if buffer and candidate_len > max_chars:
            chunks.append(Chunk(chunk_id, "\n".join(buffer)))
            chunk_id += 1
            buffer = buffer[-overlap_lines:] if overlap_lines else []
        buffer.append(line)
    if buffer:
        chunks.append(Chunk(chunk_id, "\n".join(buffer)))
    return chunks


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transcripts-dir", type=Path, default=Path("data/transcripts"))
    parser.add_argument("--out-dir", type=Path, default=Path("data/chunks"))
    parser.add_argument("--max-chars", type=int, default=18_000)
    parser.add_argument("--overlap-lines", type=int, default=6)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    transcript_files = sorted(args.transcripts_dir.glob("*.json"))
    transcript_files = [p for p in transcript_files if not p.name.startswith("_")]

    total_chunks = 0
    for path in transcript_files:
        data = json.loads(path.read_text())
        episode_id = data["episode_id"]
        out_dir = args.out_dir / episode_id
        if out_dir.exists() and not args.force and any(out_dir.glob("chunk_*.txt")):
            print(f"[skip] {episode_id} (chunks already exist)")
            continue

        lines = merge_cues_to_lines(data["cues"])
        chunks = chunk_lines(lines, max_chars=args.max_chars, overlap_lines=args.overlap_lines)
        out_dir.mkdir(parents=True, exist_ok=True)
        for old in out_dir.glob("chunk_*.txt"):
            old.unlink()
        for chunk in chunks:
            (out_dir / f"chunk_{chunk.chunk_id:02d}.txt").write_text(chunk.text)
        print(f"[ok] {episode_id}: {len(lines)} lines -> {len(chunks)} chunks")
        total_chunks += len(chunks)

    print(f"\nDone. {total_chunks} total chunks written across {len(transcript_files)} episodes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
