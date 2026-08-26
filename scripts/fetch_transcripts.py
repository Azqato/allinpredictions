#!/usr/bin/env python3
"""Fetch YouTube caption tracks for each episode (free, no API key).

Prefers youtube-transcript-api (direct timedtext access); falls back to
`yt-dlp --write-auto-sub --skip-download` + local SRT parsing if that's
blocked/unavailable for a given video. If both are blocked (e.g. a
cloud/datacenter IP block from YouTube), falls back further to driving a
real, visible Microsoft Edge browser via Playwright against tactiq.io's
free transcript tool -- this only works in headed mode (headless Chromium
does not reliably load the underlying YouTube embed/captions), so a
browser window will pop up on screen for each episode that reaches this
fallback. See PRD.md section 6.2.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional


def fetch_via_transcript_api(video_id: str) -> Optional[List[Dict[str, Any]]]:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        return None
    try:
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id)
        cues = []
        for snippet in fetched:
            cues.append(
                {
                    "text": snippet.text,
                    "start_seconds": round(float(snippet.start), 3),
                    "duration_seconds": round(float(snippet.duration), 3),
                }
            )
        return cues
    except Exception as exc:  # noqa: BLE001
        print(f"  youtube-transcript-api failed: {exc}")
        return None


def srt_timestamp_to_seconds(ts: str) -> float:
    h, m, rest = ts.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def parse_srt(text: str) -> List[Dict[str, Any]]:
    blocks = re.split(r"\r?\n\r?\n", text.strip())
    cues: List[Dict[str, Any]] = []
    for block in blocks:
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        time_line = next((ln for ln in lines if "-->" in ln), None)
        if not time_line:
            continue
        start_str, end_str = [p.strip() for p in time_line.split("-->")]
        try:
            start = srt_timestamp_to_seconds(start_str)
            end = srt_timestamp_to_seconds(end_str.split(" ")[0])
        except Exception:
            continue
        text_lines = lines[lines.index(time_line) + 1 :]
        cue_text = " ".join(text_lines).strip()
        if not cue_text:
            continue
        cues.append(
            {
                "text": cue_text,
                "start_seconds": round(start, 3),
                "duration_seconds": round(max(end - start, 0.0), 3),
            }
        )
    return cues


def fetch_via_ytdlp(video_id: str, ytdlp_path: str = "yt-dlp") -> Optional[List[Dict[str, Any]]]:
    url = f"https://www.youtube.com/watch?v={video_id}"
    with tempfile.TemporaryDirectory() as tmpdir:
        out_tmpl = str(Path(tmpdir) / "%(id)s.%(ext)s")
        cmd = [
            ytdlp_path,
            "--write-auto-sub",
            "--sub-lang",
            "en",
            "--skip-download",
            "--convert-subs",
            "srt",
            "-o",
            out_tmpl,
            url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print(f"  yt-dlp caption fetch failed: {result.stderr.strip()[:300]}")
            return None
        srt_files = list(Path(tmpdir).glob("*.srt"))
        if not srt_files:
            return None
        return parse_srt(srt_files[0].read_text(encoding="utf-8", errors="replace"))


TACTIQ_TIMESTAMP_RE = re.compile(r"^(\d{2}):(\d{2}):(\d{2})\.(\d{3})$")


def parse_tactiq_transcript(body_text: str) -> List[Dict[str, Any]]:
    lines = body_text.splitlines()
    cues: List[Dict[str, Any]] = []
    i = 0
    n = len(lines)
    while i < n:
        m = TACTIQ_TIMESTAMP_RE.match(lines[i].strip())
        if m:
            h, mnt, s, ms = m.groups()
            start = int(h) * 3600 + int(mnt) * 60 + int(s) + int(ms) / 1000.0
            text = lines[i + 1].strip() if i + 1 < n else ""
            if text:
                cues.append({"text": text, "start_seconds": round(start, 3)})
            i += 2
        else:
            i += 1

    for idx, cue in enumerate(cues):
        if idx + 1 < len(cues):
            duration = max(cues[idx + 1]["start_seconds"] - cue["start_seconds"], 0.0)
        else:
            duration = 5.0
        cue["duration_seconds"] = round(duration, 3)
    return cues


def fetch_via_tactiq_playwright(video_id: str) -> Optional[List[Dict[str, Any]]]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  playwright not installed; skipping tactiq fallback")
        return None

    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=False, slow_mo=150)
            page = browser.new_page()
            page.goto("https://tactiq.io/tools/youtube-transcript", wait_until="domcontentloaded")

            input_box = page.locator("input[type='text'], input[type='url']").first
            input_box.fill(url)

            submit_btn = page.get_by_role("button", name="Get Video Transcript")
            if submit_btn.count() == 0:
                submit_btn = page.locator("button:has-text('Transcript')").first
            submit_btn.click()

            page.wait_for_timeout(12000)
            body_text = page.locator("body").inner_text()
            browser.close()
    except Exception as exc:  # noqa: BLE001
        print(f"  tactiq/playwright fetch failed: {exc}")
        return None

    cues = parse_tactiq_transcript(body_text)
    return cues or None


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=Path, default=Path("data/episodes.json"))
    parser.add_argument("--out-dir", type=Path, default=Path("data/transcripts"))
    parser.add_argument("--missing-log", type=Path, default=Path("data/transcripts/_missing.json"))
    parser.add_argument("--yt-dlp-path", default="yt-dlp")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--no-tactiq-fallback",
        action="store_true",
        help="Disable the headed-Edge/Playwright/tactiq.io fallback (pops up a visible browser per episode).",
    )
    args = parser.parse_args(argv)

    episodes = json.loads(args.episodes.read_text())
    if args.limit is not None:
        episodes = episodes[: args.limit]

    args.out_dir.mkdir(parents=True, exist_ok=True)
    missing: List[Dict[str, str]] = []
    if args.missing_log.exists() and not args.force:
        try:
            missing = json.loads(args.missing_log.read_text())
        except Exception:
            missing = []

    fetched, skipped, failed = 0, 0, 0
    for ep in episodes:
        episode_id = ep["episode_id"]
        video_id = ep.get("video_id")
        out_path = args.out_dir / f"{episode_id}.json"

        if out_path.exists() and not args.force:
            print(f"[skip] {episode_id} (already fetched)")
            skipped += 1
            continue
        if not video_id:
            print(f"[skip] {episode_id} (no video_id resolved)")
            missing.append({"episode_id": episode_id, "reason": "no_video_id"})
            continue

        print(f"[fetch] {episode_id} ({video_id})")
        cues = fetch_via_transcript_api(video_id)
        method = "youtube_transcript_api"
        if cues is None:
            print("  falling back to yt-dlp auto-sub ...")
            cues = fetch_via_ytdlp(video_id, args.yt_dlp_path)
            method = "yt_dlp_auto_sub"
        if cues is None and not args.no_tactiq_fallback:
            print("  falling back to headed Edge / tactiq.io (browser window will open) ...")
            cues = fetch_via_tactiq_playwright(video_id)
            method = "tactiq_playwright_edge"

        if not cues:
            print(f"  [FAILED] no captions available for {episode_id}")
            missing.append({"episode_id": episode_id, "reason": "captions_unavailable"})
            failed += 1
            continue

        payload = {
            "episode_id": episode_id,
            "video_id": video_id,
            "source": method,
            "cue_count": len(cues),
            "cues": cues,
        }
        out_path.write_text(json.dumps(payload, indent=2))
        fetched += 1

    args.missing_log.write_text(json.dumps(missing, indent=2))
    print(f"\nDone. fetched={fetched} skipped={skipped} failed={failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
