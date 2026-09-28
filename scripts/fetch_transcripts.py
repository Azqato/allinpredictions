#!/usr/bin/env python3
"""Fetch YouTube transcripts into data/transcripts/<episode_id>.json.

Same process as the financialeducation project (see docs/PRD.md section 6.2
and docs/YOUTUBE-LIMITS.md). Episodes come from data/episodes.json.

Process: one episode at a time. Fetch one, process it, then fetch the next,
so a block or failure never strands fetched-but-unprocessed episodes.

Methods, in order (1-4 are server-side services, 5-7 use this IP):
  1. FreeTranscriptAPI. Max 18 calls per rolling hour (its free limit is 20).
  2. YTTools (yttools.co/api/transcript). No published limit; we cap at 30/hour.
  3. yt-to-text (yt-to-text.com/api/v1/Subtitles, the backend of tubetranscript.com).
     No published limit; we cap at 30/hour.
  4. YouTubeTranscript.pro. Free tier is 10 credits a month, so it is tried last
     and capped at 10 per rolling 30 days.
     The services fetch from YouTube on their own servers, so they never use this
     IP's YouTube budget. Each waits 20-40s between its own calls; a 429, bot page
     or "blocked" reply pauses that service for an hour. 2 and 3 are undocumented
     endpoints their own web pages use, so any unexpected reply is just a failure
     for that service. A service's "no captions" is not trusted on its own.
  5. youtube-transcript-api. Direct from this IP; 1-2 YouTube requests.
  6. headless Microsoft Edge + tactiq.io. tactiq plays the video in an embedded
     YouTube player inside our browser, so its caption request also comes from
     this IP (about 6-8 YouTube requests). Only reached when method 5 failed
     without a rate limit or a "no captions" answer.
  7. yt-dlp auto-subs (`python -m yt_dlp`, deno as its JavaScript runtime).
     Retry queue and final check only.
Normal runs use methods 1-6. `--all-methods`, `--retry-queue` or
`--no-captions-check` adds 7.

A YouTube cool-off or cap only blocks methods 5-7. While any service is open the
run keeps going: a video the services all miss is queued as `deferred` and the run
moves to the next one. The run stops only when every service is paused or capped
and YouTube is also waiting.

Every failure is classified:
  rate_limited  YouTube answered 429 / IpBlocked. A cool-off time is saved; the
                run continues on the services, or stops if none is open.
  deferred      the services all missed and YouTube was on a cool-off or cap.
  no_captions   YouTube says captions are disabled or missing. The video is not
                tried with any further method (saves tactiq's ~6-8 YouTube
                requests) and never causes a cool-off.
  timeout       a FreeTranscriptAPI timeout; it is retried once after 15s first.
  unknown       anything else.
Failed videos go to the retry queue, data/transcripts/_missing.json, with the
reason and an attempt count. no_captions videos go to a separate list,
data/transcripts/_no_captions.json, instead: they are not retried with the
backlog or the retry queue, only once more with every method at the very end
(--no-captions-check). Nothing is ever skipped by this script.

Pacing (state in data/transcripts/_fetch_state.json, so it holds across runs),
set from docs/YOUTUBE-LIMITS.md:
  - 60-120s between attempts (60s base plus random jitter, so gaps are never regular)
  - at most 20 attempts per rolling hour and 100 per rolling 24 hours; a run
    that reaches a cap exits and prints when it may resume
  - a rate limit doubles the base gap (up to 15 min), stops the run, and sets
    a cool-off: 10 min, doubling per consecutive rate limit up to 30 min
  - each success halves the base gap back toward 60s and resets the cool-off
Every attempt is appended to data/transcripts/_fetch_log.jsonl with the gap
since the previous attempt, so the limits can be re-tuned from real data.

All requests are anonymous: no Google or YouTube account is ever used (author
decision, 2026-09-27).

Usage:
  python scripts/fetch_transcripts.py [--all-methods] [EPISODE_ID ...]   (no IDs = every unfetched episode)
  python scripts/fetch_transcripts.py --retry-queue      (all methods, whole queue)
  python scripts/fetch_transcripts.py --no-captions-check   (last: all methods, no-captions list)
"""
from __future__ import annotations

import datetime
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import random
import time
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "transcripts"
MISSING_LOG = OUT_DIR / "_missing.json"
NO_CAPTIONS_LOG = OUT_DIR / "_no_captions.json"   # option B: checked once more at the very end
STATE_FILE = OUT_DIR / "_fetch_state.json"
ATTEMPT_LOG = OUT_DIR / "_fetch_log.jsonl"
EPISODES = ROOT / "data" / "episodes.json"

# Limits from docs/YOUTUBE-LIMITS.md: ~20-30 caption requests in a burst per IP,
# blocks lasting hours. Stay well under that; slower is fine.
MIN_COOLDOWN = 60             # base gap between attempts
JITTER_SECONDS = 60           # plus a random 0-60s, so gaps are 60-120s and never regular
HOURLY_CAP = 20               # attempts per rolling hour
DAILY_CAP = 100               # attempts per rolling 24 hours
MAX_COOLDOWN = 900
COOL_OFF_START = 10 * 60      # first rate limit: wait 10 min before the next run
COOL_OFF_MAX = 30 * 60        # doubles per consecutive rate limit, capped at 30 min
STOP_AFTER_RATE_LIMITS = 1  # every method shares one IP, so one 429 means stop
FTA_URL = "https://api.freetranscriptapi.com/v1/transcript"
FTA_HOURLY_CAP = 18           # service allows 20/hour per IP anonymously; stay under
FTA_TIMEOUT_RETRY_SECONDS = 15  # one retry after a FreeTranscriptAPI timeout
FTA_MIN_GAP = 20              # seconds between FreeTranscriptAPI calls, plus 0-20s jitter
SERVICE_GAP = 20              # seconds between calls to the same service, plus 0-20s jitter
# Server-side services: they fetch from YouTube on their own servers, so they never
# use this IP's YouTube budget. key = state-file prefix; cap = calls per rolling window.
# YTTools and yt-to-text publish no limit; 30/hour is our own conservative choice.
SERVICES = {
    "freetranscriptapi": {"key": "fta", "cap": FTA_HOURLY_CAP, "window": 3600, "label": "FreeTranscriptAPI"},
    "yttools": {"key": "yttools", "cap": 30, "window": 3600, "label": "YTTools"},
    "yt_to_text": {"key": "yttotext", "cap": 30, "window": 3600, "label": "yt-to-text"},
    # free tier is 10 credits a month, so it is the last service tried
    "youtubetranscript_pro": {"key": "yttpro", "cap": 10, "window": 30 * 86400, "label": "YouTubeTranscript.pro"},
}
TACTIQ_POLL_SECONDS = 3
TACTIQ_MAX_SECONDS = 90
# Headless Edge otherwise reports "HeadlessEdg", which tactiq may treat differently.
EDGE_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0"
)
TACTIQ_TS_RE = re.compile(r"^(\d{2}):(\d{2}):(\d{2})\.(\d{3})$")
SRT_TIME_RE = re.compile(r"(\d+):(\d+):(\d+),(\d+)")


class FetchError(Exception):
    def __init__(self, kind: str, detail: str):
        super().__init__(f"{kind}: {detail}")
        self.kind = kind


def classify(exc: Exception) -> str:
    if isinstance(exc, FetchError):
        return exc.kind
    text = f"{type(exc).__name__} {exc}"
    if re.search(r"IpBlocked|RequestBlocked|TooManyRequests|429", text):
        return "rate_limited"
    if re.search(r"timed out|TimeoutError|timeout", text, re.I):
        return "timeout"
    if re.search(r"TranscriptsDisabled|NoTranscriptFound|no subtitles|no captions", text, re.I):
        return "no_captions"
    return "unknown"


def _now() -> float:
    return time.time()


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"cooldown_seconds": MIN_COOLDOWN, "last_attempt_end": 0, "blocked_until": 0}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def log_attempt(entry: dict) -> None:
    with ATTEMPT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def _iso(ts: float) -> str:
    return datetime.datetime.fromtimestamp(ts).isoformat(timespec="seconds")


# ---------- methods ----------

def via_freetranscriptapi(video_id: str):
    import urllib.error
    import urllib.request
    from urllib.parse import urlencode

    req = urllib.request.Request(FTA_URL + "?" + urlencode({"video_url": video_id}),
                                 headers={"User-Agent": "financialeducation-wiki/1.0 (personal archive)"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:200]
        if exc.code == 429:
            raise FetchError("service_limited", f"FreeTranscriptAPI 429: {body}") from exc
        if re.search(r"no (captions|transcript|subtitles)|disabled|not available", body, re.I):
            raise FetchError("no_captions", f"FreeTranscriptAPI {exc.code}: {body}") from exc
        raise RuntimeError(f"FreeTranscriptAPI HTTP {exc.code}: {body}") from exc
    lang = str(data.get("language") or "")
    if lang and not lang.lower().startswith("en"):
        raise RuntimeError(f"FreeTranscriptAPI returned language {lang!r}, not English")
    return [
        {"text": str(c["text"]).strip(), "start_seconds": round(float(c["start"]), 3),
         "duration_seconds": round(float(c.get("duration") or 0), 3)}
        for c in data.get("transcript") or [] if str(c.get("text", "")).strip()
    ]


def via_transcript_api(video_id: str):
    from youtube_transcript_api import YouTubeTranscriptApi

    fetched = YouTubeTranscriptApi().fetch(video_id)
    return [
        {"text": s.text, "start_seconds": round(s.start, 3), "duration_seconds": round(s.duration, 3)}
        for s in fetched
    ]


def _srt_seconds(ts: str) -> float:
    h, m, s, ms = map(int, SRT_TIME_RE.match(ts.strip()).groups())
    return h * 3600 + m * 60 + s + ms / 1000


def _deno_env() -> dict:
    env = dict(os.environ)
    if not shutil.which("deno"):
        links = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links"
        pkgs = sorted((Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages").glob("DenoLand.Deno*"))
        extra = [str(p) for p in [links, *pkgs] if (p / "deno.exe").exists()]
        env["PATH"] = os.pathsep.join(extra + [env.get("PATH", "")])
    return env


def via_ytdlp(video_id: str):
    cmd = [sys.executable, "-m", "yt_dlp", "--write-auto-sub", "--sub-lang", "en", "--skip-download",
           "--convert-subs", "srt"]
    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run(
            cmd + ["-o", str(Path(tmp) / "%(id)s.%(ext)s"), f"https://www.youtube.com/watch?v={video_id}"],
            capture_output=True, text=True, env=_deno_env(),
        )
        srt = next(Path(tmp).glob("*.srt"), None)
        if result.returncode or not srt:
            err = result.stderr.strip()
            if "429" in err:
                raise FetchError("rate_limited", "yt-dlp HTTP 429")
            if not err or "no subtitles" in err.lower() or "There are no subtitles" in err:
                raise FetchError("no_captions", "yt-dlp found no English subtitles")
            raise RuntimeError(err.splitlines()[-1])
        cues = []
        for block in re.split(r"\r?\n\r?\n", srt.read_text(encoding="utf-8", errors="replace").strip()):
            lines = [ln for ln in block.splitlines() if ln.strip()]
            timing = next((ln for ln in lines if "-->" in ln), None)
            if not timing:
                continue
            start, end = (p.split(" ")[0] for p in timing.split("-->"))
            text = " ".join(lines[lines.index(timing) + 1:]).strip()
            if text:
                s, e = _srt_seconds(start), _srt_seconds(end)
                cues.append({"text": text, "start_seconds": round(s, 3), "duration_seconds": round(max(e - s, 0), 3)})
        return cues


def _parse_tactiq(body: str):
    lines = body.splitlines()
    cues = []
    for i, line in enumerate(lines[:-1]):
        m = TACTIQ_TS_RE.match(line.strip())
        if m and lines[i + 1].strip():
            h, mi, s, ms = map(int, m.groups())
            cues.append({"text": lines[i + 1].strip(), "start_seconds": round(h * 3600 + mi * 60 + s + ms / 1000, 3)})
    for i, cue in enumerate(cues):
        nxt = cues[i + 1]["start_seconds"] if i + 1 < len(cues) else cue["start_seconds"] + 5
        cue["duration_seconds"] = round(max(nxt - cue["start_seconds"], 0), 3)
    return cues


def via_tactiq_headless_edge(video_id: str):
    from playwright.sync_api import sync_playwright

    yt = f"https://www.youtube.com/watch?v={video_id}"
    timedtext: list[tuple[int, int]] = []  # (status, body length) of YouTube caption responses

    def on_response(resp):
        if "/api/timedtext" in resp.url:
            try:
                size = len(resp.body())
            except Exception:  # noqa: BLE001
                size = -1
            timedtext.append((resp.status, size))

    args = ["--disable-blink-features=AutomationControlled"]
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True, args=args)
        context = browser.new_context(user_agent=EDGE_USER_AGENT, viewport={"width": 1366, "height": 900})
        page = context.new_page()
        page.on("response", on_response)
        page.goto(
            "https://tactiq.io/tools/run/youtube_transcript?yt=" + quote(yt, safe=""),
            wait_until="domcontentloaded",
        )
        cues = []
        for _ in range(TACTIQ_MAX_SECONDS // TACTIQ_POLL_SECONDS):
            page.wait_for_timeout(TACTIQ_POLL_SECONDS * 1000)
            cues = _parse_tactiq(page.locator("body").inner_text())
            if len(cues) > 5:
                break
            if any(status == 429 for status, _ in timedtext):
                break
            if any(status == 200 for status, _ in timedtext):
                # captions arrived; give tactiq a moment to render them
                page.wait_for_timeout(5000)
                cues = _parse_tactiq(page.locator("body").inner_text())
                break
        context.close()
    if len(cues) > 5:
        return cues
    if any(status == 429 for status, _ in timedtext):
        raise FetchError("rate_limited", "YouTube timedtext returned 429 to the tactiq player")
    if any(status == 200 and size == 0 for status, size in timedtext):
        raise FetchError("no_captions", "YouTube timedtext returned an empty caption track")
    if not timedtext:
        raise FetchError("unknown", "tactiq's player never requested captions (possibly none exist)")
    raise FetchError("unknown", f"no transcript after {TACTIQ_MAX_SECONDS}s; timedtext={timedtext}")


def _service_json(name: str, url: str, body: dict | None = None, headers: dict | None = None):
    """GET (or POST JSON) a server-side transcript service; classify its errors."""
    import urllib.error
    import urllib.request

    hdrs = {"User-Agent": EDGE_USER_AGENT, **(headers or {})}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=hdrs), timeout=60) as resp:
            text = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:200]
        if exc.code == 429 or re.search(r"block|rate.?limit|too many", detail, re.I):
            raise FetchError("service_limited", f"{name} {exc.code}: {detail}") from exc
        if re.search(r"no.?(captions|transcript|subtitles)|disabled", detail, re.I):
            raise FetchError("no_captions", f"{name} {exc.code}: {detail}") from exc
        raise RuntimeError(f"{name} HTTP {exc.code}: {detail}") from exc
    try:
        return json.loads(text)
    except ValueError:
        # an HTML page instead of JSON is usually a bot wall in front of the service
        raise FetchError("service_limited", f"{name} returned non-JSON: {text[:120]!r}") from None


def _english(name: str, lang) -> None:
    if lang and not str(lang).lower().startswith("en"):
        raise RuntimeError(f"{name} returned language {lang!r}, not English")


def via_yttools(video_id: str):
    # undocumented endpoint used by yttools.co's own page; offsets are milliseconds
    data = _service_json("YTTools", "https://yttools.co/api/transcript?url="
                         + quote(f"https://www.youtube.com/watch?v={video_id}", safe=""))
    items = data.get("transcript") or []
    if items:
        _english("YTTools", items[0].get("lang"))
    return [{"text": html.unescape(str(c["text"])).strip(), "start_seconds": round(float(c["offset"]) / 1000, 3),
             "duration_seconds": round(float(c.get("duration") or 0) / 1000, 3)}
            for c in items if str(c.get("text", "")).strip()]


def via_yt_to_text(video_id: str):
    # backend of tubetranscript.com; times are strings in seconds, e = end time
    data = _service_json("yt-to-text", "https://yt-to-text.com/api/v1/Subtitles", {"video_id": video_id},
                         {"x-app-version": "1.0", "x-source": "tubetranscript"})
    if data.get("code") == "NO_SUBTITLES":
        raise FetchError("no_captions", "yt-to-text: NO_SUBTITLES")
    items = (data.get("data") or {}).get("transcripts") or []
    return [{"text": html.unescape(str(c["t"])).strip(), "start_seconds": round(float(c["s"]), 3),
             "duration_seconds": round(max(float(c["e"]) - float(c["s"]), 0), 3)}
            for c in items if str(c.get("t", "")).strip()]


def via_youtubetranscript_pro(video_id: str):
    from urllib.parse import urlencode
    data = _service_json("YouTubeTranscript.pro", "https://youtubetranscript.pro/api/youtube/transcript?"
                         + urlencode({"url": f"https://www.youtube.com/watch?v={video_id}", "videoId": video_id}))
    if data.get("error") and not data.get("data"):
        raise RuntimeError(f"YouTubeTranscript.pro: {str(data)[:150]}")
    body = data.get("data") or {}
    _english("YouTubeTranscript.pro", body.get("lang"))
    return [{"text": html.unescape(str(c["text"])).strip(), "start_seconds": round(float(c["offset"]), 3),
             "duration_seconds": round(float(c.get("duration") or 0), 3)}
            for c in body.get("response") or [] if str(c.get("text", "")).strip()]


# Methods 1-4 are server-side services (see SERVICES): they don't use this IP's
# YouTube budget, each has its own pacing, and one being paused never stops a run.
# Methods 5-7 reach YouTube from this IP and share one budget, paced by wait_for_turn().
SERVICE_METHODS = set(SERVICES)
METHODS = [
    ("freetranscriptapi", via_freetranscriptapi),
    ("yttools", via_yttools),
    ("yt_to_text", via_yt_to_text),
    ("youtubetranscript_pro", via_youtubetranscript_pro),
    ("youtube_transcript_api", via_transcript_api),        # 1-2 YouTube requests per video
    ("tactiq_playwright_edge_headless", via_tactiq_headless_edge),  # real player, ~6-8 requests;
    # only reached when the direct method failed without a rate limit (e.g. empty reply from a
    # video that needs the player's security token)
    ("yt_dlp_auto_sub", via_ytdlp),
]
NORMAL_METHODS = 6  # yt-dlp only with --all-methods / --retry-queue / --no-captions-check


# ---------- pacing ----------

def wait_for_turn(state: dict) -> None:
    now = _now()
    if state.get("blocked_until", 0) > now:
        return (f"[cool-off] YouTube rate-limited this IP recently. Next YouTube fetch allowed after "
                f"{_iso(state['blocked_until'])} ({(state['blocked_until'] - now) / 60:.0f} min).")
    recent = [t for t in state.get("attempt_times", []) if now - t < 86400]
    for cap, window, label in ((DAILY_CAP, 86400, "daily"), (HOURLY_CAP, 3600, "hourly")):
        in_window = sorted(t for t in recent if now - t < window)
        if len(in_window) >= cap:
            resume = in_window[len(in_window) - cap] + window
            return (f"[cap] {label} limit of {cap} YouTube attempts reached. Next YouTube fetch allowed after "
                    f"{_iso(resume)} ({(resume - now) / 60:.0f} min).")
    wait = state["cooldown_seconds"] + random.uniform(0, JITTER_SECONDS) - (_now() - state.get("last_attempt_end", 0))
    if wait > 0:
        print(f"  cooldown {wait:.0f}s")
        time.sleep(wait)
    return None


def _service_times(state: dict, name: str) -> list:
    cfg = SERVICES[name]
    return sorted(t for t in state.get(cfg["key"] + "_times", []) if _now() - t < cfg["window"])


def service_blocked(state: dict, name: str) -> str | None:
    """Why this service can't be called now (paused or at its cap), else None. Never sleeps."""
    cfg, now = SERVICES[name], _now()
    if state.get(cfg["key"] + "_paused_until", 0) > now:
        return f"{cfg['label']} paused until {_iso(state[cfg['key'] + '_paused_until'])}"
    recent = _service_times(state, name)
    if len(recent) >= cfg["cap"]:
        return f"{cfg['label']} cap of {cfg['cap']} reached until {_iso(recent[len(recent) - cfg['cap']] + cfg['window'])}"
    return None


def any_service_open(state: dict, methods) -> bool:
    return any(n in SERVICES and not service_blocked(state, n) for n, _ in methods)


def service_turn(state: dict, name: str) -> str | None:
    blocked = service_blocked(state, name)
    if blocked:
        return blocked
    recent = _service_times(state, name)
    wait = SERVICE_GAP + random.uniform(0, SERVICE_GAP) - (_now() - (recent[-1] if recent else 0))
    if wait > 0:
        print(f"  service gap {wait:.0f}s")
        time.sleep(wait)
    return None


def note_service_call(state: dict, name: str, started: float) -> None:
    state[SERVICES[name]["key"] + "_times"] = _service_times(state, name) + [started]


def record(state: dict, video_id: str, method: str, result: str, kind: str | None, started: float) -> None:
    prev_end = state.get("last_attempt_end", 0)
    end = _now()
    if result == "ok":
        state["cooldown_seconds"] = max(MIN_COOLDOWN, state["cooldown_seconds"] // 2)
        state["rate_limit_streak"] = 0
    elif kind == "rate_limited":
        state["cooldown_seconds"] = min(MAX_COOLDOWN, state["cooldown_seconds"] * 2)
        state["rate_limit_streak"] = state.get("rate_limit_streak", 0) + 1
        state["blocked_until"] = end + min(COOL_OFF_MAX, COOL_OFF_START * 2 ** (state["rate_limit_streak"] - 1))
    state["last_attempt_end"] = end
    state["attempt_times"] = [t for t in state.get("attempt_times", []) if end - t < 86400] + [started]
    save_state(state)
    log_attempt({
        "at": _iso(started), "video_id": video_id, "method": method, "result": result, "kind": kind,
        "seconds": round(end - started, 1),
        "gap_since_previous": round(started - prev_end, 1) if prev_end else None,
        "cooldown_after": state["cooldown_seconds"],
    })


FINAL_CHECK = False  # --no-captions-check: try every method even after "no captions"


def fetch(episode_id: str, video_id: str, title: str, methods, state: dict) -> tuple[bool, str | None]:
    kinds = []
    for name, method in methods:
        service = name in SERVICE_METHODS
        blocked = service_turn(state, name) if service else wait_for_turn(state)
        if blocked:
            print(f"  {name} skipped: {blocked}")
            if not service:
                return False, "waiting:" + blocked
            continue
        started = _now()
        try:
            try:
                cues = method(video_id)
            except Exception as exc:  # noqa: BLE001
                if not (service and classify(exc) == "timeout"):
                    raise
                # a timeout is usually the service being slow, not a limit: one retry
                print(f"  {name} timed out; retrying once in {FTA_TIMEOUT_RETRY_SECONDS}s")
                note_service_call(state, name, started)
                time.sleep(FTA_TIMEOUT_RETRY_SECONDS)
                started = _now()
                cues = method(video_id)
        except Exception as exc:  # noqa: BLE001
            kind = classify(exc)
            if service:
                note_service_call(state, name, started)
                if kind == "service_limited":
                    state[SERVICES[name]["key"] + "_paused_until"] = _now() + 3600
                save_state(state)
                log_attempt({"at": _iso(started), "video_id": video_id, "method": name, "result": "failed",
                             "kind": kind, "seconds": round(_now() - started, 1)})
                print(f"  {name} failed [{kind}]: {str(exc)[:150]}")
                if kind == "no_captions":
                    kinds.append(kind)
                continue
            kinds.append(kind)
            record(state, video_id, name, "failed", kind, started)
            print(f"  {name} failed [{kind}]: {str(exc).strip().splitlines()[0][:150] if str(exc).strip() else type(exc).__name__}")
            if kind == "rate_limited":
                return False, "rate_limited"
            if kind == "no_captions" and not FINAL_CHECK:
                # YouTube itself said captions are disabled or missing: don't spend more
                # YouTube requests (tactiq is ~6-8) on this video now
                return False, "no_captions"
            continue
        if service:
            note_service_call(state, name, started)
            save_state(state)
            log_attempt({"at": _iso(started), "video_id": video_id, "method": name,
                         "result": "ok" if cues else "failed", "kind": None if cues else "unknown",
                         "seconds": round(_now() - started, 1)})
        if cues:
            if not service:
                record(state, video_id, name, "ok", None, started)
            payload = {"episode_id": episode_id, "video_id": video_id, "title": title, "source": name,
                       "cue_count": len(cues), "cues": cues}
            (OUT_DIR / f"{episode_id}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
            print(f"  OK via {name} ({len(cues)} cues)")
            return True, None
        if not service:
            record(state, video_id, name, "failed", "unknown", started)
        kinds.append("unknown")
    return False, ("no_captions" if "no_captions" in kinds else "unknown")


def save_queues(missing: list, no_caps: list) -> None:
    MISSING_LOG.write_text(json.dumps(missing, indent=2), encoding="utf-8")
    NO_CAPTIONS_LOG.write_text(json.dumps(no_caps, indent=2), encoding="utf-8")


def main(argv: list[str]) -> int:
    all_methods = any(a in argv for a in ("--all-methods", "--retry-queue", "--no-captions-check"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    episodes = json.loads(EPISODES.read_text(encoding="utf-8"))
    by_id = {e["episode_id"]: e for e in episodes}
    global FINAL_CHECK
    missing = json.loads(MISSING_LOG.read_text(encoding="utf-8")) if MISSING_LOG.exists() else []
    no_caps = json.loads(NO_CAPTIONS_LOG.read_text(encoding="utf-8")) if NO_CAPTIONS_LOG.exists() else []
    no_caps += [m for m in missing if m.get("likely_no_captions")]
    missing = [m for m in missing if not m.get("likely_no_captions")]
    wanted = [a for a in argv if not a.startswith("--")]
    if "--retry-queue" in argv:
        wanted = [m["episode_id"] for m in missing]
    elif "--no-captions-check" in argv:
        # option B: one last all-methods check, only after the retry queue is empty
        FINAL_CHECK = True
        wanted = [m["episode_id"] for m in no_caps]
    elif not wanted:
        wanted = [e["episode_id"] for e in episodes]
    methods = METHODS if all_methods else METHODS[:NORMAL_METHODS]
    state = load_state()
    print(f"[pacing] cooldown {state['cooldown_seconds']}s; "
          f"methods: {', '.join(n for n, _ in methods)}")
    failed = 0
    for i, eid in enumerate(wanted):
        ep = by_id.get(eid, {})
        vid = ep.get("video_id")
        if (OUT_DIR / f"{eid}.json").exists():
            continue
        if not vid:
            print(f"[skip] {eid} (no video_id resolved)")
            continue
        print(f"[fetch] {eid} ({vid}) {ep.get('title', '')}")
        ok, kind = fetch(eid, vid, ep.get("title", ""), methods, state)
        if kind and kind.startswith("waiting:"):
            if not any_service_open(state, methods):
                print(f"[stop] {kind[8:]} Stopping; this episode was not attempted on YouTube and is not queued.")
                break
            # the services all missed and YouTube is on a wait: retry later, keep going on the services
            print(f"  {kind[8:]}")
            kind = "deferred"
        if ok:
            missing = [m for m in missing if m.get("episode_id") != eid]
            no_caps = [m for m in no_caps if m.get("episode_id") != eid]
        else:
            failed += 1
            prev = next((m for m in missing + no_caps if m.get("episode_id") == eid), {})
            missing = [m for m in missing if m.get("episode_id") != eid]
            no_caps = [m for m in no_caps if m.get("episode_id") != eid]
            kinds = sorted(set(prev.get("kinds", [])) | {kind})
            entry = {"episode_id": eid, "video_id": vid, "title": ep.get("title", ""), "reason": kind, "kinds": kinds,
                     "attempts": prev.get("attempts", 0) + 1, "last_attempt": _iso(_now()),
                     "likely_no_captions": "no_captions" in kinds}
            if kind == "no_captions":
                # option B: no rerun during the backlog or the retry pass; one final check at the very end
                entry["final_checked"] = FINAL_CHECK
                no_caps.append(entry)
                print("  [NO CAPTIONS] moved to the no-captions list for one final check at the end")
            else:
                missing.append(entry)
                print(f"  [FAILED: {kind}] added to retry queue")
            if kind == "rate_limited" and not any_service_open(state, methods):
                rest = [e for e in wanted[i + 1:] if not (OUT_DIR / f"{e}.json").exists()]
                print(f"[stop] YouTube is rate-limiting this IP. Not attempting {len(rest)} remaining episode(s); "
                      f"next run may start after {_iso(state['blocked_until'])}.")
                break
        save_queues(missing, no_caps)
    save_queues(missing, no_caps)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
