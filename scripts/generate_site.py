#!/usr/bin/env python3
"""Deterministic static site generator. No LLM calls -- pure data -> HTML.

Reads data/episodes.json + data/predictions/*.json + data/checks/*.json,
joins them, computes per-host/guest accuracy stats, and renders the site
directly into the rewrite/ root (index.html, episodes/, host/, static/,
about.html) -- the eventual GitHub Pages "deploy from root" publish
location once rewrite/ replaces the repo root -- using Jinja2 templates +
hand-rolled inline SVG charts. See PRD.md section 9.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

RESULT_KEYS = ["right", "wrong", "ambiguous", "inconclusive", "unvalidated"]
RESULT_COLORS = {
    "right": "#22c55e",
    "wrong": "#ef4444",
    "ambiguous": "#d4c4a8",
    "inconclusive": "#6b7280",
    "unvalidated": "#94a3b8",
}
QUALIFYING_CONFIDENCE = {"high", "medium"}
VALID_CHECK_RESULTS = {"right", "wrong", "ambiguous", "inconclusive"}
# Home page convention (documented in docs/PRD.md's Home Page Layout notes):
# every prediction-listing section on the home page (Big Ones, Recently
# Settled, Recent Episodes) caps at this many items, so the page stays
# scannable. "See more"/"Browse the full ledger" links cover the rest.
HOME_SECTION_MAX = 6
BAD_WHO_VALUES = {"unknown", "n/a", "none", "null", ""}

# Tag slugs whose correct display casing isn't plain title-case (acronyms,
# stylized brand names, leading-digit names). Anything not listed here falls
# back to splitting on "-" and title-casing each word, e.g.
# "autonomous-vehicles" -> "Autonomous Vehicles".
TAG_DISPLAY_OVERRIDES = {
    "ai": "AI",
}


def tag_display(tag: str) -> str:
    if tag in TAG_DISPLAY_OVERRIDES:
        return TAG_DISPLAY_OVERRIDES[tag]
    return " ".join(
        TAG_DISPLAY_OVERRIDES.get(word, word.capitalize()) for word in tag.split("-")
    )


# Verdict data-model decision (§19.1 item 1, docs/PRD.md §36.1 item 8): the
# underlying `result` values (right/wrong/ambiguous/inconclusive/unvalidated)
# stay unchanged in the data model, so no migration across ~3,455 existing
# checks. Only the *display* copy changes: read against real check
# explanations, "ambiguous" is used in practice for a mixed/partial outcome
# ("partly right") and "inconclusive" for a timeframe that hasn't elapsed yet
# ("too early") - so those are the display strings, everywhere a verdict
# renders as visible copy. Keep in sync with VERDICT_DISPLAY_OVERRIDES in
# site_src/static/app.js.
VERDICT_DISPLAY_OVERRIDES = {
    "ambiguous": "Partly Right",
    "inconclusive": "Too Early",
}


def verdict_display(result: str) -> str:
    if result in VERDICT_DISPLAY_OVERRIDES:
        return VERDICT_DISPLAY_OVERRIDES[result]
    return result.capitalize()


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
        prev = cur
    return prev[-1]


class DataValidationError(Exception):
    """Raised when data/predictions or data/checks don't match the §7 schema.

    generate_site.py has no client-side or upstream schema enforcement, so a
    hand-edited or migration-script-written prediction file can otherwise
    render silently-wrong host cards (the freeberg/unknown incident this
    check exists to catch a repeat of)."""


def validate_prediction(episode_id: str, p: Dict[str, Any], permanent_hosts: List[str]) -> List[str]:
    """Only checks records that would actually render as a speaker card
    (role == host, or speaker_confidence high/medium - the same `qualifies`
    condition build_speaker_index uses), since a bad `who`/`role` on a
    low-confidence/unattributed line never reaches the page. This is the
    exact class of record that caused the freeberg/unknown incident."""
    errors: List[str] = []
    pred_id = p.get("id") or "<missing id>"
    who = p.get("who")
    role = p.get("role")
    qualifies = role == "host" or p.get("speaker_confidence") in QUALIFYING_CONFIDENCE
    if not qualifies:
        return errors

    if not who or not isinstance(who, str) or who.lower() in BAD_WHO_VALUES:
        errors.append(f"{episode_id}/{pred_id}: qualifying prediction has a missing/placeholder 'who' ({who!r})")
        return errors

    if role is not None and role not in ("host", "guest", "unknown"):
        errors.append(f"{episode_id}/{pred_id}: 'role' ({role!r}) must be 'host', 'guest', 'unknown', or omitted")
    if who in permanent_hosts and role == "guest":
        errors.append(f"{episode_id}/{pred_id}: 'who' ({who!r}) is a permanent host but 'role' is 'guest'")
    elif who not in permanent_hosts and role == "host":
        # role:"host" must use one of the exact config/hosts.yaml slugs - a
        # display-name-style variant (e.g. "chamath-palihapitiya" instead of
        # "chamath") silently fabricates a second page for the same person
        # rather than tripping the near-miss check below, since it's not a
        # short typo. This is exactly the chamath-palihapitiya/david-friedberg
        # incident this branch exists to catch a repeat of.
        errors.append(
            f"{episode_id}/{pred_id}: 'who' ({who!r}) has role 'host' but is not one of the "
            f"canonical permanent-host slugs {sorted(permanent_hosts)} from config/hosts.yaml - "
            f"use the exact slug (e.g. 'chamath', not 'chamath-palihapitiya')"
        )
    elif who not in permanent_hosts:
        near = [h for h in permanent_hosts if 0 < levenshtein(who, h) <= 2]
        if near:
            errors.append(
                f"{episode_id}/{pred_id}: 'who' ({who!r}) is suspiciously close to permanent host(s) "
                f"{near} - likely a misspelling rather than a real guest"
            )
    return errors


def validate_check_result(episode_id: str, check: Dict[str, Any]) -> List[str]:
    result = check.get("result")
    check_id = check.get("id") or "<missing id>"
    if result not in VALID_CHECK_RESULTS:
        return [f"{episode_id}/{check_id}: check 'result' ({result!r}) is not one of {sorted(VALID_CHECK_RESULTS)}"]
    return []


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def timestamp_to_seconds(ts: str) -> Optional[int]:
    m = re.match(r"^(\d+):(\d{2}):(\d{2})$", ts or "")
    if not m:
        return None
    h, mi, s = (int(x) for x in m.groups())
    return h * 3600 + mi * 60 + s


def capitalize_who(who: str) -> str:
    return " ".join(part.capitalize() for part in who.split("-"))


def display_name_for(who: str, hosts_cfg: Dict[str, Any]) -> str:
    """Full "First Last" name for the four permanent hosts (config/hosts.yaml
    `display_name`, since their canonical slugs are short nicknames like
    "jason"/"sacks"), falling back to the slug-derived capitalization for
    everyone else (guest slugs are already full-name, e.g. "elon-musk")."""
    host_entry = hosts_cfg.get("hosts", {}).get(who)
    if host_entry and host_entry.get("display_name"):
        return host_entry["display_name"]
    return capitalize_who(who)


def load_all_data(root: Path) -> Dict[str, Any]:
    episodes = load_json(root / "data" / "episodes.json", [])
    hosts_cfg = yaml.safe_load((root / "config" / "hosts.yaml").read_text())
    permanent_hosts = list(hosts_cfg.get("hosts", {}).keys())

    validation_errors: List[str] = []
    episodes_out = []
    for ep in episodes:
        episode_id = ep["episode_id"]
        pred_data = load_json(root / "data" / "predictions" / f"{episode_id}.json")
        if not pred_data:
            continue
        checks_data = load_json(root / "data" / "checks" / f"{episode_id}.json", {})
        check_map = {c["id"]: c for c in checks_data.get("checks", [])}
        for c in checks_data.get("checks", []):
            validation_errors.extend(validate_check_result(episode_id, c))

        merged_predictions = []
        for p in pred_data.get("predictions", []):
            validation_errors.extend(validate_prediction(episode_id, p, permanent_hosts))
            check = check_map.get(p["id"])
            merged = dict(p)
            merged["timestamp_seconds"] = timestamp_to_seconds(p.get("timestamp", ""))
            merged["result"] = check["result"] if check else None
            merged["explanation"] = check.get("explanation") if check else None
            merged["sources"] = check.get("sources", []) if check else []
            merged["who_display"] = display_name_for(p["who"], hosts_cfg)
            merged_predictions.append(merged)

        episodes_out.append(
            {
                "episode_id": episode_id,
                "title": ep.get("title") or episode_id,
                "published": ep.get("published"),
                "published_iso": ep.get("published_iso"),
                "youtube_url": ep.get("youtube_url"),
                "video_id": ep.get("video_id"),
                "predictions": merged_predictions,
            }
        )

    if validation_errors:
        report = "\n".join(f"  - {e}" for e in validation_errors)
        raise DataValidationError(
            f"{len(validation_errors)} data/predictions or data/checks record(s) failed schema "
            f"validation; refusing to generate a site with bad data:\n{report}"
        )

    # newest first
    episodes_out.sort(key=lambda e: e.get("published_iso") or "", reverse=True)
    return {"episodes": episodes_out, "permanent_hosts": permanent_hosts, "hosts_cfg": hosts_cfg}


def empty_bucket() -> Dict[str, int]:
    return {k: 0 for k in RESULT_KEYS}


def bump(bucket: Dict[str, int], result: Optional[str]) -> None:
    bucket[result or "unvalidated"] = bucket.get(result or "unvalidated", 0) + 1


def pct_bucket(bucket: Dict[str, int], denom: int) -> Dict[str, Optional[float]]:
    """Each key's count as a percentage of `denom`, rounded to 1 decimal.
    None (not 0) when denom is 0, so templates can render an em dash instead
    of a misleading "0%"."""
    if not denom:
        return {k: None for k in bucket}
    return {k: round(100 * v / denom, 1) for k, v in bucket.items()}


def build_speaker_index(
    episodes: List[Dict[str, Any]], permanent_hosts: List[str], hosts_cfg: Dict[str, Any]
) -> Dict[str, Dict[str, Any]]:
    """One entry per speaker (host or guest) who qualifies for a scorecard."""
    speakers: Dict[str, Dict[str, Any]] = {}

    def ensure(who: str, role: str) -> Dict[str, Any]:
        if who not in speakers:
            speakers[who] = {
                "who": who,
                "who_display": display_name_for(who, hosts_cfg),
                "role": role,
                "stats": empty_bucket(),
                "predictions": [],
                "chart_entries": [],
            }
        return speakers[who]

    for host in permanent_hosts:
        ensure(host, "host")

    for ep in episodes:
        year = (ep.get("published_iso") or "")[:4] or None
        for p in ep["predictions"]:
            who, role = p["who"], p.get("role") or ("host" if p["who"] in permanent_hosts else "guest")
            qualifies = role == "host" or p.get("speaker_confidence") in QUALIFYING_CONFIDENCE
            if not qualifies:
                continue
            entry = ensure(who, role)
            entry["predictions"].append({**p, "episode_id": ep["episode_id"], "episode_title": ep["title"],
                                          "episode_published": ep.get("published"), "youtube_url": ep.get("youtube_url")})
            if p.get("speaker_confidence") in QUALIFYING_CONFIDENCE:
                bump(entry["stats"], p.get("result"))
                # Lightweight per-prediction record for client-side topic/year
                # filtering (§27): kept in sync with the stats bucket above by
                # only including entries that also count toward it.
                entry["chart_entries"].append(
                    {"result": p.get("result") or "unvalidated", "tags": p.get("tags") or [], "year": year}
                )

    return speakers


def html_attr_json(obj: Any) -> str:
    """json.dumps, escaped so the result can sit inside an HTML attribute value."""
    raw = json.dumps(obj, separators=(",", ":"))
    return (
        raw.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def donut_svg(stats: Dict[str, int], keys: List[str], *, size: int = 160, stroke: int = 22) -> str:
    total = sum(stats.get(k, 0) for k in keys)
    r = (size - stroke) / 2
    cx = cy = size / 2
    circumference = 2 * math.pi * r
    if total == 0:
        return (
            f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" role="img" aria-label="No data">'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="rgba(255,255,255,0.12)" stroke-width="{stroke}" />'
            f"</svg>"
        )
    offset = 0.0
    segments = []
    for key in keys:
        val = stats.get(key, 0)
        if val <= 0:
            continue
        frac = val / total
        length = frac * circumference
        dasharray = f"{length:.2f} {circumference - length:.2f}"
        rotate = (offset / total) * 360 - 90
        segments.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{RESULT_COLORS[key]}" '
            f'stroke-width="{stroke}" stroke-dasharray="{dasharray}" '
            f'transform="rotate({rotate:.2f} {cx} {cy})" />'
        )
        offset += val
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" role="img" aria-label="Accuracy chart">'
        + "".join(segments)
        + "</svg>"
    )


def render_site(root: Path, out_dir: Path) -> None:
    data = load_all_data(root)
    episodes = data["episodes"]
    permanent_hosts = data["permanent_hosts"]
    speakers = build_speaker_index(episodes, permanent_hosts, data["hosts_cfg"])

    for s in speakers.values():
        s["donut_svg"] = donut_svg(s["stats"], ["right", "wrong"])
        s["donut_svg_all"] = donut_svg(s["stats"], ["right", "wrong", "ambiguous", "inconclusive"])
        s["total_resolved"] = s["stats"]["right"] + s["stats"]["wrong"]
        s["total_all"] = sum(s["stats"].values())
        s["chart_json"] = html_attr_json(s["chart_entries"])
        s["accuracy_pct"] = (
            round(100 * s["stats"]["right"] / s["total_resolved"], 1) if s["total_resolved"] else None
        )
        s["small_sample"] = s["role"] == "guest" and s["total_all"] < 3
        # Per-key percentage-of-total breakdowns, for showing "N (P%)" next to
        # each verdict count rather than raw counts alone.
        s["pct_all"] = pct_bucket(s["stats"], s["total_all"])
        s["pct_resolved"] = pct_bucket(s["stats"], s["total_resolved"])

    hosts_sorted = sorted(
        (s for s in speakers.values() if s["role"] == "host"),
        key=lambda s: permanent_hosts.index(s["who"]) if s["who"] in permanent_hosts else 99,
    )
    guests_sorted = sorted(
        (s for s in speakers.values() if s["role"] == "guest"),
        key=lambda s: -s["total_all"],
    )

    # Combined accuracy leaderboard (§34/§36 items 1-3): every host + guest,
    # ranked by resolved-prediction accuracy (unranked/no-data speakers sort
    # last). Small-sample guests stay in the list but are flagged so the
    # figure isn't read as statistically meaningful.
    leaderboard = sorted(
        speakers.values(),
        key=lambda s: (-s["stats"]["right"], s["accuracy_pct"] is None, -(s["accuracy_pct"] or 0)),
    )

    # Topic tags appearing on any HOST's qualifying predictions, for the home
    # page topic filter (§27) -- scoped to hosts because that's all the home
    # page's scorecards actually filter; a guest-only tag would just zero
    # out every card if offered there.
    host_topics = sorted({tag for s in hosts_sorted for e in s["chart_entries"] for tag in e["tags"]})

    # §19.1 item 3 "Topic Index": live per-topic counts for the home page tag
    # cloud, scoped to the same host-only set as host_topics/the topic filter
    # above (so a pill's count always matches what clicking it actually
    # filters to). Sorted by count descending so the biggest topics lead.
    topic_counts = Counter(tag for s in hosts_sorted for e in s["chart_entries"] for tag in e["tags"])
    topic_index = sorted(topic_counts.items(), key=lambda kv: (-kv[1], kv[0]))

    # Every topic tag appearing on ANY qualifying prediction sitewide (host
    # or guest), for the Full Ledger filter (§36), which browses all of them.
    # Using host_topics here was the bug: dozens of guest-only tags (spacex,
    # openai, robotics, etc.) were silently missing from the ledger's filter
    # even though the ledger itself includes those predictions.
    all_topics = sorted({tag for s in speakers.values() for e in s["chart_entries"] for tag in e["tags"]})

    # Distinct years with at least one episode, newest first, for the
    # Annual Predictions episode filter (§17) and the Full Ledger filter.
    years = sorted({(ep.get("published_iso") or "")[:4] for ep in episodes if ep.get("published_iso")}, reverse=True)

    # Sitewide overall headline stat (§36 item 2): summed across every
    # speaker's qualifying-prediction bucket, so it matches what the
    # scorecards already show rather than recomputing from raw files.
    overall_stats = empty_bucket()
    for s in speakers.values():
        for k in RESULT_KEYS:
            overall_stats[k] += s["stats"][k]
    overall_total_resolved = overall_stats["right"] + overall_stats["wrong"]
    overall_total_all = sum(overall_stats.values())
    overall_accuracy_pct = (
        round(100 * overall_stats["right"] / overall_total_resolved, 1) if overall_total_resolved else None
    )
    overall_pct_all = pct_bucket(overall_stats, overall_total_all)
    overall_pct_resolved = pct_bucket(overall_stats, overall_total_resolved)

    # "Recently settled" feed (§36 item 6): the most recent qualifying
    # predictions with a resolved-ish verdict, newest episode first.
    recently_settled: List[Dict[str, Any]] = []
    for ep in episodes:
        for p in ep["predictions"]:
            if p.get("result") not in ("right", "wrong", "ambiguous"):
                continue
            qualifies = p.get("role") == "host" or p.get("speaker_confidence") in QUALIFYING_CONFIDENCE
            if not qualifies:
                continue
            recently_settled.append(
                {**p, "episode_id": ep["episode_id"], "episode_title": ep["title"],
                 "episode_published": ep.get("published"), "youtube_url": ep.get("youtube_url")}
            )
        if len(recently_settled) >= 20:
            break
    recently_settled = recently_settled[:20]

    # "Big Ones" (roadmap item 3): a hand-curated pool of the highest-profile
    # predictions, listed in config/big_ones.json as {episode_id, id,
    # impact_score} entries. impact_score (1.0-1000) is an editorial judgment
    # of real-world significance -- NOT confidence or correctness -- used
    # only to rank this candidate pool; it's a backend field, never rendered
    # on the site. Resolved from the same merged prediction records as
    # everywhere else, so quote/result/tags/who_display stay in sync
    # automatically as new checks come in. Entries whose episode_id/id no
    # longer resolve (a rename, a corrected id) are skipped with a warning
    # rather than breaking the build. The home page shows only the top 6,
    # confirmed-right entries by impact_score, so a wrong/inconclusive
    # prediction never displaces the highlight reel with a miss.
    pred_lookup: Dict[tuple, Dict[str, Any]] = {}
    for ep in episodes:
        for p in ep["predictions"]:
            pred_lookup[(ep["episode_id"], p["id"])] = {
                **p, "episode_id": ep["episode_id"], "episode_title": ep["title"],
                "episode_published": ep.get("published"), "youtube_url": ep.get("youtube_url"),
            }
    big_ones_cfg = load_json(root / "config" / "big_ones.json", [])
    big_ones_pool: List[Dict[str, Any]] = []
    for entry in big_ones_cfg:
        key = (entry.get("episode_id"), entry.get("id"))
        record = pred_lookup.get(key)
        if record is None:
            print(f"[warn] big_ones.json entry not found, skipping: {entry}", file=sys.stderr)
            continue
        big_ones_pool.append({**record, "impact_score": entry.get("impact_score", 0)})
    big_ones = sorted(
        (r for r in big_ones_pool if r.get("result") == "right"),
        key=lambda r: -r["impact_score"],
    )[:HOME_SECTION_MAX]

    # "This Episode's Calls" (§19.1 item 5): every qualifying prediction from
    # the single most recent episode (episodes is already newest-first, same
    # assumption "Recent Episodes"/recently_settled above rely on), so the
    # newest show gets its own highlight strip distinct from the curated
    # Big Ones and time-scoped Recently Settled sections. Capped at
    # HOME_SECTION_MAX like every other home page section.
    latest_episode = episodes[0] if episodes else None
    this_episode_calls: List[Dict[str, Any]] = []
    if latest_episode:
        for p in latest_episode["predictions"]:
            qualifies = p.get("role") == "host" or p.get("speaker_confidence") in QUALIFYING_CONFIDENCE
            if not qualifies:
                continue
            this_episode_calls.append(
                {**p, "episode_id": latest_episode["episode_id"], "episode_title": latest_episode["title"],
                 "episode_published": latest_episode.get("published"), "youtube_url": latest_episode.get("youtube_url")}
            )
        this_episode_calls = this_episode_calls[:HOME_SECTION_MAX]

    # Full Ledger (§36 item 5): a lightweight, client-filterable index of
    # every qualifying prediction sitewide. Kept deliberately thin (no quote/
    # explanation/sources) so the JSON stays small - the full record lives on
    # the episode page this links to.
    ledger_entries = []
    for ep in episodes:
        year = (ep.get("published_iso") or "")[:4] or None
        for p in ep["predictions"]:
            qualifies = p.get("role") == "host" or p.get("speaker_confidence") in QUALIFYING_CONFIDENCE
            if not qualifies:
                continue
            ledger_entries.append(
                {
                    "id": p["id"],
                    "who": p["who"],
                    "who_display": p["who_display"],
                    "episode_id": ep["episode_id"],
                    "episode_title": ep["title"],
                    "published": ep.get("published"),
                    "year": year,
                    "result": p.get("result") or "unvalidated",
                    "tags": p.get("tags") or [],
                    "prediction": p.get("prediction") or "",
                }
            )

    # Sitewide search index (roadmap item 4): one flat JSON array combining
    # predictions, episodes, and host/guest pages, so a single client-side
    # search box can find any of them. Kept thin like the ledger, plus a
    # lowercase "text" field for the client to substring-match against
    # without recomputing it per-keystroke.
    search_index: List[Dict[str, Any]] = []
    for ep in episodes:
        search_index.append(
            {
                "type": "episode",
                "title": ep["title"],
                "subtitle": ep.get("published") or "",
                "url": f"episodes/{ep['episode_id']}.html",
                "text": (ep["title"] or "").lower(),
            }
        )
        for p in ep["predictions"]:
            qualifies = p.get("role") == "host" or p.get("speaker_confidence") in QUALIFYING_CONFIDENCE
            if not qualifies:
                continue
            search_index.append(
                {
                    "type": "prediction",
                    "title": p.get("prediction") or "",
                    "subtitle": f"{p['who_display']} · {ep['title']}",
                    "result": p.get("result") or "unvalidated",
                    "url": f"episodes/{ep['episode_id']}.html#{p['id']}",
                    "text": f"{p.get('prediction') or ''} {p['who_display']} {ep['title']}".lower(),
                }
            )
    for s in speakers.values():
        search_index.append(
            {
                "type": "host" if s["role"] == "host" else "guest",
                "title": s["who_display"],
                "subtitle": f"{s['total_all']} prediction{'' if s['total_all'] == 1 else 's'}"
                + (f" · {s['accuracy_pct']}% accuracy" if s["accuracy_pct"] is not None else ""),
                "url": f"host/{s['who']}.html",
                "text": s["who_display"].lower(),
            }
        )

    templates_dir = root / "site_src" / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["tag_display"] = tag_display
    env.filters["verdict_display"] = verdict_display

    # Only clean the specific generated paths -- out_dir may be the rewrite/
    # root itself (so the site's index.html etc. sit at the eventual repo
    # root for GitHub Pages "deploy from root"), which also holds source
    # directories (scripts/, data/, config/, site_src/, prompts/, docs/) that
    # must never be touched by a site rebuild.
    GENERATED_TOP_LEVEL = ["index.html", "about.html", "leaderboard.html", "ledger.html", "search.html", "episodes", "host", "static"]
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in GENERATED_TOP_LEVEL:
        p = out_dir / name
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        elif p.exists():
            p.unlink()
    (out_dir / "episodes").mkdir(exist_ok=True)
    (out_dir / "host").mkdir(exist_ok=True)

    static_src = root / "site_src" / "static"
    static_dst = out_dir / "static"
    if static_src.exists():
        shutil.copytree(static_src, static_dst, dirs_exist_ok=True)

    last_updated = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    common = {"site_title": "All-In Predictions", "last_updated": last_updated}

    (out_dir / "index.html").write_text(
        env.get_template("index.html").render(
            **common, hosts=hosts_sorted, guests=guests_sorted, episodes=episodes[:HOME_SECTION_MAX],
            total_episode_count=len(episodes), topics=host_topics,
            overall_stats=overall_stats, overall_total_resolved=overall_total_resolved,
            overall_total_all=overall_total_all, overall_accuracy_pct=overall_accuracy_pct,
            overall_pct_all=overall_pct_all, overall_pct_resolved=overall_pct_resolved,
            recently_settled=recently_settled[:HOME_SECTION_MAX], big_ones=big_ones,
            topic_index=topic_index, latest_episode=latest_episode, this_episode_calls=this_episode_calls,
        )
    )

    (out_dir / "episodes" / "index.html").write_text(
        env.get_template("episodes_index.html").render(**common, episodes=episodes, years=years, asset_prefix="../")
    )

    (out_dir / "leaderboard.html").write_text(
        env.get_template("leaderboard.html").render(
            **common, leaderboard=leaderboard,
            overall_stats=overall_stats, overall_total_resolved=overall_total_resolved,
            overall_total_all=overall_total_all, overall_accuracy_pct=overall_accuracy_pct,
            overall_pct_all=overall_pct_all, overall_pct_resolved=overall_pct_resolved,
        )
    )

    (out_dir / "ledger.html").write_text(
        env.get_template("ledger.html").render(**common, topics=all_topics, years=years, ledger_count=len(ledger_entries))
    )
    (static_dst / "ledger.json").write_text(json.dumps(ledger_entries, ensure_ascii=False))

    (out_dir / "search.html").write_text(
        env.get_template("search.html").render(**common, search_count=len(search_index))
    )
    (static_dst / "search_index.json").write_text(json.dumps(search_index, ensure_ascii=False))

    for ep in episodes:
        (out_dir / "episodes" / f"{ep['episode_id']}.html").write_text(
            env.get_template("episode.html").render(**common, episode=ep, asset_prefix="../")
        )

    (out_dir / "host" / "index.html").write_text(
        env.get_template("host_index.html").render(**common, hosts=hosts_sorted, guests=guests_sorted, asset_prefix="../")
    )

    for s in speakers.values():
        s["predictions"].sort(key=lambda p: p.get("episode_published") or "", reverse=True)
        speaker_topics = sorted({tag for e in s["chart_entries"] for tag in e["tags"]})
        (out_dir / "host" / f"{s['who']}.html").write_text(
            env.get_template("host.html").render(
                **common, speaker=s, asset_prefix="../", topics=speaker_topics,
            )
        )

    (out_dir / "about.html").write_text(env.get_template("about.html").render(**common))

    print(f"Generated site: {len(episodes)} episode pages, {len(speakers)} host/guest pages -> {out_dir}")


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    out_dir = args.out or args.root
    render_site(args.root, out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
