#!/usr/bin/env python3
"""Fetch, parse, and optionally download the All-In podcast archive."""
from __future__ import annotations

import argparse
import json
import re
import sys
import subprocess
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

DEFAULT_FEED_URL = "https://rss.libsyn.com/shows/254861/destinations/1928300.xml"
DEFAULT_YOUTUBE_PLAYLIST_URL = (
    "https://www.youtube.com/@allin/videos"
)
USER_AGENT = "predict-allin-downloader/0.1 (+https://github.com/)"
NAMESPACES = {
    "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    "podcast": "https://podcastindex.org/namespace/1.0",
    "atom": "http://www.w3.org/2005/Atom",
}


def fetch_feed(feed_url: str) -> bytes:
    req = Request(feed_url, headers={"User-Agent": USER_AGENT})
    with urlopen(req) as resp:
        return resp.read()


def parse_feed(feed_bytes: bytes) -> List[Dict[str, Any]]:
    root = ET.fromstring(feed_bytes)
    episodes: List[Dict[str, Any]] = []
    for item in root.findall("./channel/item"):
        enclosure = item.find("enclosure")
        if enclosure is None:
            continue
        pub_str = (item.findtext("pubDate") or "").strip()
        pub_dt = parse_rfc_datetime(pub_str)
        episodes.append(
            {
                "title": (item.findtext("title") or "").strip(),
                "published": pub_str,
                "published_iso": pub_dt.isoformat() if pub_dt else None,
                "guid": (item.findtext("guid") or "").strip(),
                "description": (item.findtext("description") or "").strip(),
                "duration": (item.findtext("itunes:duration", namespaces=NAMESPACES) or "").strip(),
                "audio_url": enclosure.get("url", ""),
                "audio_length": enclosure.get("length"),
                "audio_type": enclosure.get("type"),
            }
        )
    return episodes


def slugify(value: str, fallback: str = "episode") -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug or fallback


def infer_audio_filename(episode: Dict[str, Any], index: int) -> str:
    url = episode.get("audio_url") or ""
    parsed = urlparse(url)
    candidate = Path(unquote(parsed.path or "")).name
    if candidate.endswith(".mp3"):
        base = candidate
    else:
        base = f"{slugify(episode.get('title', ''), f'episode-{index:03d}')}.mp3"
    safe = re.sub(r"[^a-zA-Z0-9._-]", "-", base)
    safe = re.sub(r"-+", "-", safe)
    if not safe.endswith(".mp3"):
        safe = f"{safe}.mp3"
    return safe


def download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = destination.with_suffix(destination.suffix + ".part")
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req) as resp, open(tmp_path, "wb") as fh:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                fh.write(chunk)
        tmp_path.replace(destination)
    finally:
        if tmp_path.exists() and not destination.exists():
            tmp_path.unlink(missing_ok=True)


def parse_rfc_datetime(value: str) -> datetime | None:
    try:
        return parsedate_to_datetime(value)
    except Exception:
        return None


def parse_iso_datetime(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", title.lower())


def extract_youtube_links(text: str) -> List[str]:
    if not text:
        return []
    pattern = re.compile(
        r"(https?://(?:www\\.)?youtube\\.com/[\\w/?=&%-]+|https?://youtu\\.be/[\\w-]+)",
        re.IGNORECASE,
    )
    return pattern.findall(text)


def extract_episode_code(text: str) -> str | None:
    m = re.search(r"e(?:p)?\s?(\d+)", text.lower())
    if not m:
        return None
    try:
        idx = int(m.group(1))
    except ValueError:
        return None
    return f"E{idx:03d}"


def parse_youtube_feed(feed_bytes: bytes) -> List[Dict[str, Any]]:
    root = ET.fromstring(feed_bytes)
    entries: List[Dict[str, Any]] = []
    for entry in root.findall("atom:entry", namespaces=NAMESPACES):
        title = (entry.findtext("atom:title", namespaces=NAMESPACES) or "").strip()
        link_el = entry.find("atom:link", namespaces=NAMESPACES)
        href = link_el.get("href") if link_el is not None else ""
        published = (entry.findtext("atom:published", namespaces=NAMESPACES) or "").strip()
        media_group = entry.find("{http://search.yahoo.com/mrss/}group")
        media_desc = ""
        if media_group is not None:
            media_desc = (media_group.findtext("{http://search.yahoo.com/mrss/}description") or "").strip()
        is_short = href.startswith("https://www.youtube.com/shorts/")
        entries.append(
            {
                "title": title,
                "published": published,
                "url": href,
                "description": media_desc,
                "is_short": is_short,
                "title_norm": normalize_title(title),
                "published_dt": parse_iso_datetime(published),
            }
        )
    return entries


def attach_youtube_links(
    episodes: List[Dict[str, Any]],
    yt_entries: List[Dict[str, Any]],
    manual_map: Dict[str, str] | None = None,
) -> None:
    manual_map = manual_map or {}
    manual_title_map = {normalize_title(k): v for k, v in manual_map.items() if k}
    long_entries = [e for e in yt_entries if not e.get("is_short")]
    index_by_title = {e["title_norm"]: e for e in long_entries if e.get("title_norm")}
    # Episode code mapping: titles that start with E[number]:
    index_by_episode_code: Dict[str, Dict[str, Any]] = {}
    for entry in long_entries:
        title = entry.get("title") or ""
        m = re.search(r"e(?:p)?\s?(\d+)", title.strip().lower())
        if m:
            idx = int(m.group(1))
            code = f"E{idx:03d}"
            index_by_episode_code[code] = entry
    for ep in episodes:
        title_norm = normalize_title(ep.get("title", ""))
        # Skip if already set via other means
        if ep.get("youtube_url"):
            continue
        if ep.get("episode_id") and ep["episode_id"] in manual_map:
            ep["youtube_url"] = manual_map[ep["episode_id"]]
            continue
        if title_norm in manual_title_map:
            ep["youtube_url"] = manual_title_map[title_norm]
            continue
        ep_id = ep.get("episode_id")
        ep_code = ep.get("episode_code")
        def maybe_match(code: str) -> bool:
            if code in index_by_episode_code:
                ep["youtube_url"] = index_by_episode_code[code].get("url")
                return True
            return False

        if ep_code and maybe_match(ep_code):
            continue
        if ep_code:
            # also try unpadded form
            m_pad = re.match(r"E0*(\d+)", ep_code)
            if m_pad and maybe_match(f"E{int(m_pad.group(1))}"):
                continue
        if ep_id:
            m_id = re.search(r"e0*(\d+)", ep_id.lower())
            if m_id and maybe_match(f"E{int(m_id.group(1))}"):
                continue
            if m_id and maybe_match(f"E{int(m_id.group(1)):03d}"):
                continue
        yt_match = index_by_title.get(title_norm)
        if yt_match is None:
            # fallback: nearest date
            ep_dt = parse_rfc_datetime(ep.get("published", ""))
            if ep_dt:
                best = None
                best_delta = None
                for entry in long_entries:
                    dt = entry.get("published_dt")
                    if not dt:
                        continue
                    delta = abs((dt - ep_dt).total_seconds())
                    if best_delta is None or delta < best_delta:
                        best_delta = delta
                        best = entry
                # accept if within ~30 days
                if best is not None and best_delta is not None and best_delta <= 30 * 24 * 3600:
                    yt_match = best
        if yt_match:
            ep["youtube_url"] = yt_match.get("url")
        else:
            # Try to extract from description
            desc_links = extract_youtube_links(ep.get("description", ""))
            if desc_links:
                ep["youtube_url"] = desc_links[0]


def fetch_ytdlp_playlist(playlist_url: str, ytdlp_path: str = "yt-dlp") -> bytes:
    cmd = [ytdlp_path, "-J", "--flat-playlist", playlist_url]
    result = subprocess.run(
        cmd, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"yt-dlp failed ({result.returncode}): {result.stderr.strip() or result.stdout}"
        )
    return result.stdout.encode("utf-8")


def parse_ytdlp_entries(raw_bytes: bytes) -> List[Dict[str, Any]]:
    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Failed to parse yt-dlp JSON: {exc}") from exc
    entries: List[Dict[str, Any]] = []
    for entry in data.get("entries", []):
        title = (entry.get("title") or "").strip()
        vid = entry.get("id") or entry.get("url") or ""
        if not title or not vid:
            continue
        url = vid if vid.startswith("http") else f"https://www.youtube.com/watch?v={vid}"
        upload_date = entry.get("upload_date")
        published_dt = None
        if upload_date and len(upload_date) == 8:
            try:
                published_dt = datetime.strptime(upload_date, "%Y%m%d")
            except Exception:
                published_dt = None
        entries.append(
            {
                "title": title,
                "published": upload_date or "",
                "url": url,
                "title_norm": normalize_title(title),
                "published_dt": published_dt,
                "is_short": url.startswith("https://www.youtube.com/shorts/"),
            }
        )
    return entries

def download_audio_archive(
    episodes: List[Dict[str, Any]],
    audio_dir: Path,
    limit: int | None = None,
) -> int:
    downloaded = 0
    audio_dir.mkdir(parents=True, exist_ok=True)
    for idx, episode in enumerate(reversed(episodes), start=1):
        if limit is not None and downloaded >= limit:
            break
        url = episode.get("audio_url") or ""
        if not url:
            continue
        fname = episode.get("audio_filename") or infer_audio_filename(episode, idx)
        destination = audio_dir / fname
        if destination.exists() and destination.stat().st_size > 0:
            print(f"Skip existing {destination}")
            continue
        print(f"Downloading {episode.get('title', 'Unknown')} -> {destination}")
        download_file(url, destination)
        downloaded += 1
    return downloaded


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feed-url", default=DEFAULT_FEED_URL, help="RSS feed URL to fetch")
    parser.add_argument(
        "--youtube-playlist-url",
        default=DEFAULT_YOUTUBE_PLAYLIST_URL,
        help="YouTube uploads playlist URL (used with yt-dlp)",
    )
    parser.add_argument(
        "--raw-feed-path",
        type=Path,
        default=Path("data/raw/all_in_feed.xml"),
        help="Where to store the raw XML feed",
    )
    parser.add_argument(
        "--raw-youtube-ytdlp-path",
        type=Path,
        default=Path("data/raw/all_in_youtube_ytdlp.json"),
        help="Where to store the yt-dlp playlist dump",
    )
    parser.add_argument(
        "--youtube-map",
        type=Path,
        default=Path("config/youtube_urls.json"),
        help="Optional JSON mapping of episode_id or title to youtube_url",
    )
    parser.add_argument(
        "--episodes-json",
        type=Path,
        default=Path("data/processed/all_in_episodes.json"),
        help="Where to store parsed episode metadata",
    )
    parser.add_argument(
        "--audio-dir",
        type=Path,
        default=Path("data/audio/all_in"),
        help="Directory for downloaded MP3 files",
    )
    parser.add_argument(
        "--download-audio",
        action="store_true",
        help="Download MP3 files referenced by the feed (skips existing files)",
    )
    parser.add_argument(
        "--yt-dlp-path",
        default="yt-dlp",
        help="Path to yt-dlp executable",
    )
    parser.add_argument(
        "--download-limit",
        type=int,
        default=None,
        help="Optional cap on how many episodes to download (useful for smoke tests)",
    )
    args = parser.parse_args(argv)

    print(f"Fetching feed from {args.feed_url} ...")
    feed_bytes = fetch_feed(args.feed_url)
    write_bytes(args.raw_feed_path, feed_bytes)
    print(f"Saved raw feed to {args.raw_feed_path}")

    yt_json_bytes = None
    try:
        print(
            f"Fetching YouTube playlist via yt-dlp from {args.youtube_playlist_url} ..."
        )
        yt_json_bytes = fetch_ytdlp_playlist(
            args.youtube_playlist_url, ytdlp_path=args.yt_dlp_path
        )
        write_bytes(args.raw_youtube_ytdlp_path, yt_json_bytes)
        print(f"Saved yt-dlp playlist JSON to {args.raw_youtube_ytdlp_path}")
    except Exception as exc:  # noqa: BLE001
        print(f"WARNING: failed to fetch playlist via yt-dlp: {exc}")

    episodes = parse_feed(feed_bytes)
    for index, episode in enumerate(episodes, start=1):
        audio_fname = infer_audio_filename(episode, index)
        episode["audio_filename"] = audio_fname
        stem = Path(audio_fname).stem
        episode["episode_id"] = stem
        code_from_title = extract_episode_code(episode.get("title", ""))
        code_from_id = extract_episode_code(stem)
        episode["episode_code"] = code_from_title or code_from_id

    yt_entries: List[Dict[str, Any]] = []
    manual_map: Dict[str, str] = {}
    if args.youtube_map.exists():
        try:
            loaded = json.loads(args.youtube_map.read_text())
            if isinstance(loaded, dict):
                manual_map = {str(k): str(v) for k, v in loaded.items()}
            elif isinstance(loaded, list):
                for item in loaded:
                    if isinstance(item, dict):
                        key = item.get("episode_id") or item.get("title")
                        url = item.get("youtube_url")
                        if key and url:
                            manual_map[str(key)] = str(url)
        except Exception as exc:  # noqa: BLE001
            print(f"WARNING: failed to load youtube map {args.youtube_map}: {exc}")
    if yt_json_bytes:
        yt_entries = parse_ytdlp_entries(yt_json_bytes)
    if yt_entries:
        attach_youtube_links(episodes, yt_entries, manual_map=manual_map)
    elif manual_map:
        attach_youtube_links(episodes, [], manual_map=manual_map)
    write_json(args.episodes_json, episodes)
    print(f"Parsed {len(episodes)} episodes -> {args.episodes_json}")

    if args.download_audio:
        count = download_audio_archive(episodes, args.audio_dir, limit=args.download_limit)
        print(f"Downloaded {count} new audio files into {args.audio_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
