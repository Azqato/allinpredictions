#!/usr/bin/env python3
"""Discover All-In Podcast episodes and resolve each to a YouTube video id.

Free-tooling only: podcast RSS feed (no key) + yt-dlp flat-playlist listing
(metadata only, no video/audio download). See rewrite/PRD.md section 6.1.

Canonical numbering/ordering reference: https://allin.com/episodes, used to
sanity-check episode_code extraction, not scraped as a data source (no public
JSON feed was found behind it).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

DEFAULT_FEED_URL = "https://rss.libsyn.com/shows/254861/destinations/1928300.xml"
DEFAULT_YOUTUBE_PLAYLIST_URL = "https://www.youtube.com/@allin/videos"
USER_AGENT = "allinpredictions-rewrite/0.1 (+https://github.com/)"
NAMESPACES = {
    "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
}


def fetch_feed(feed_url: str) -> bytes:
    req = Request(feed_url, headers={"User-Agent": USER_AGENT})
    with urlopen(req) as resp:
        return resp.read()


def parse_rfc_datetime(value: str) -> Optional[datetime]:
    try:
        return parsedate_to_datetime(value)
    except Exception:
        return None


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", title.lower())


def extract_episode_code(text: str) -> Optional[str]:
    """Pull an episode number like 'E211' out of a title/id string."""
    m = re.search(r"\bE\s?(\d{1,4})\b", text, re.IGNORECASE)
    if not m:
        return None
    try:
        idx = int(m.group(1))
    except ValueError:
        return None
    return f"E{idx:03d}"


def slugify(value: str, fallback: str = "episode") -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug or fallback


def parse_feed(feed_bytes: bytes) -> List[Dict[str, Any]]:
    root = ET.fromstring(feed_bytes)
    episodes: List[Dict[str, Any]] = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        pub_str = (item.findtext("pubDate") or "").strip()
        pub_dt = parse_rfc_datetime(pub_str)
        guid = (item.findtext("guid") or "").strip()
        description = (item.findtext("description") or "").strip()
        code = extract_episode_code(title) or extract_episode_code(guid)
        episode_id = code or slugify(title, "episode")
        episodes.append(
            {
                "episode_id": episode_id,
                "episode_code": code,
                "title": title,
                "published": pub_str,
                "published_iso": pub_dt.isoformat() if pub_dt else None,
                "description": description,
                "guid": guid,
            }
        )
    return episodes


def fetch_ytdlp_playlist(playlist_url: str, ytdlp_path: str = "yt-dlp") -> bytes:
    cmd = [ytdlp_path, "-J", "--flat-playlist", playlist_url]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"yt-dlp failed ({result.returncode}): {result.stderr.strip() or result.stdout}"
        )
    return result.stdout.encode("utf-8")


def parse_ytdlp_entries(raw_bytes: bytes) -> List[Dict[str, Any]]:
    data = json.loads(raw_bytes.decode("utf-8"))
    entries: List[Dict[str, Any]] = []
    for entry in data.get("entries", []):
        title = (entry.get("title") or "").strip()
        vid = entry.get("id") or ""
        if not title or not vid:
            continue
        upload_date = entry.get("upload_date")
        published_dt = None
        if upload_date and len(upload_date) == 8:
            try:
                published_dt = datetime.strptime(upload_date, "%Y%m%d")
            except Exception:
                published_dt = None
        is_short = "/shorts/" in (entry.get("url") or "")
        entries.append(
            {
                "title": title,
                "video_id": vid,
                "title_norm": normalize_title(title),
                "published_dt": published_dt,
                "episode_code": extract_episode_code(title),
                "is_short": is_short,
            }
        )
    return entries


def attach_video_ids(
    episodes: List[Dict[str, Any]],
    yt_entries: List[Dict[str, Any]],
    manual_map: Dict[str, str],
) -> None:
    long_entries = [e for e in yt_entries if not e.get("is_short")]
    by_code = {e["episode_code"]: e for e in long_entries if e.get("episode_code")}
    by_title = {e["title_norm"]: e for e in long_entries if e.get("title_norm")}

    for ep in episodes:
        vid = manual_map.get(ep["episode_id"])
        if vid:
            ep["video_id"] = vid
            ep["youtube_url"] = f"https://www.youtube.com/watch?v={vid}"
            ep["match_method"] = "manual_override"
            continue

        if ep.get("episode_code") and ep["episode_code"] in by_code:
            match = by_code[ep["episode_code"]]
            ep["video_id"] = match["video_id"]
            ep["youtube_url"] = f"https://www.youtube.com/watch?v={match['video_id']}"
            ep["match_method"] = "episode_code"
            continue

        title_norm = normalize_title(ep["title"])
        if title_norm in by_title:
            match = by_title[title_norm]
            ep["video_id"] = match["video_id"]
            ep["youtube_url"] = f"https://www.youtube.com/watch?v={match['video_id']}"
            ep["match_method"] = "title_match"
            continue

        ep_dt = parse_rfc_datetime(ep.get("published", ""))
        best, best_delta = None, None
        if ep_dt:
            for entry in long_entries:
                dt = entry.get("published_dt")
                if not dt:
                    continue
                # Both are naive/aware; normalize by dropping tzinfo for the diff.
                dt_cmp = dt.replace(tzinfo=None)
                ep_cmp = ep_dt.replace(tzinfo=None)
                delta = abs((dt_cmp - ep_cmp).total_seconds())
                if best_delta is None or delta < best_delta:
                    best_delta, best = delta, entry
        if best is not None and best_delta is not None and best_delta <= 30 * 24 * 3600:
            ep["video_id"] = best["video_id"]
            ep["youtube_url"] = f"https://www.youtube.com/watch?v={best['video_id']}"
            ep["match_method"] = "nearest_date"
            continue

        ep["video_id"] = None
        ep["youtube_url"] = None
        ep["match_method"] = "unmatched"


def load_manual_map(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except Exception:
        return {}
    if isinstance(data, dict):
        return {str(k): str(v) for k, v in data.items()}
    return {}


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feed-url", default=DEFAULT_FEED_URL)
    parser.add_argument("--youtube-playlist-url", default=DEFAULT_YOUTUBE_PLAYLIST_URL)
    parser.add_argument("--yt-dlp-path", default="yt-dlp")
    parser.add_argument(
        "--youtube-map",
        type=Path,
        default=Path("config/youtube_urls_override.json"),
        help="Optional manual episode_id -> video_id overrides",
    )
    parser.add_argument("--out", type=Path, default=Path("data/episodes.json"))
    parser.add_argument("--raw-feed-path", type=Path, default=Path("data/raw_feed.xml"))
    parser.add_argument(
        "--skip-youtube",
        action="store_true",
        help="Skip yt-dlp lookup (RSS metadata only, no video_id resolution)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only keep the N most recent episodes (smoke-testing)",
    )
    args = parser.parse_args(argv)

    print(f"Fetching RSS feed from {args.feed_url} ...")
    feed_bytes = fetch_feed(args.feed_url)
    args.raw_feed_path.parent.mkdir(parents=True, exist_ok=True)
    args.raw_feed_path.write_bytes(feed_bytes)

    episodes = parse_feed(feed_bytes)
    # RSS feeds list newest first; keep that order but allow --limit to sample
    # the newest N without needing yt-dlp to churn through the whole channel.
    if args.limit is not None:
        episodes = episodes[: args.limit]
    print(f"Parsed {len(episodes)} episodes from RSS.")

    if not args.skip_youtube:
        try:
            print(f"Listing YouTube uploads via yt-dlp ({args.youtube_playlist_url}) ...")
            yt_raw = fetch_ytdlp_playlist(args.youtube_playlist_url, args.yt_dlp_path)
            yt_entries = parse_ytdlp_entries(yt_raw)
            print(f"Found {len(yt_entries)} YouTube uploads.")
        except Exception as exc:  # noqa: BLE001
            print(f"WARNING: yt-dlp lookup failed, video_ids will be unresolved: {exc}")
            yt_entries = []
        manual_map = load_manual_map(args.youtube_map)
        attach_video_ids(episodes, yt_entries, manual_map)
    else:
        for ep in episodes:
            ep["video_id"] = None
            ep["youtube_url"] = None
            ep["match_method"] = "skipped"

    matched = sum(1 for e in episodes if e.get("video_id"))
    print(f"Resolved YouTube video_id for {matched}/{len(episodes)} episodes.")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(episodes, indent=2))
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
