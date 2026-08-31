# PRD: All-In Predictions - Free-Tooling / Claude-Native Rewrite

## 0. Summary

Rebuild the "All-In Predictions" project from scratch in the repo root, replacing every piece of the original stack that required a paid API (OpenAI, xAI/Grok, Speechmatics/Deepgram/AssemblyAI, Next.js/Node build+hosting) with:

1. **Free, no-API-key tooling** for transcript acquisition (YouTube's own captions, not downloaded audio + paid ASR).
2. **Claude (this agent, running in Claude Code)** as the entire "intelligence" layer - prediction extraction, speaker attribution, web-search validation, and topic tagging - instead of calling OpenAI/xAI APIs from a script.
3. **Vanilla HTML/CSS/JS**, statically generated (no Next.js/React/Node build pipeline), deployable directly on **GitHub Pages** with zero build infrastructure beyond a Python script Claude runs locally.

The output is the same in spirit: a browsable site scoring the All-In hosts' (Jason, Chamath, Sacks, Friedberg) predictions as right/wrong/ambiguous/inconclusive, with quotes, timestamps, YouTube deep-links, and cited explanations - but the entire toolchain is free to operate indefinitely and every "AI" step is something *I* (Claude) do directly, rather than code that calls a billed model API.

---

## 1. Goals

- **G1 - Zero paid dependencies.** No OpenAI/xAI/Speechmatics/Deepgram/AssemblyAI API keys anywhere. Every external call is either a free public endpoint (YouTube captions, podcast RSS) or done by Claude itself.
- **G2 - Claude is the runtime, not just the builder.** The pipeline's "LLM steps" (extraction, attribution, validation, tagging) are executed by Claude Code - either interactively in a session, or via scripted headless `claude -p` invocations - not by SDK calls to a third-party model API from Python.
- **G3 - No audio downloads.** Skip MP3 archiving and ASR entirely. Pull transcripts straight from YouTube's caption/subtitle track (auto-generated or manual) for each episode's video.
- **G4 - Vanilla static frontend.** Plain HTML/CSS/JS, no npm install, no bundler, no framework runtime in the browser. Must run correctly when served as flat files by GitHub Pages.
- **G5 - Same core value proposition.** Per-host accuracy scorecards (donut/bar charts), episode-by-episode prediction lists, individual prediction permalinks, YouTube timestamp deep-links, topic tagging/filtering, and cited validation explanations.
- **G6 - Incremental & idempotent.** Re-running the pipeline on the full archive should skip episodes already processed; adding new episodes should be a cheap, mostly-automatic update.
- **G7 - Transparent about accuracy tradeoffs.** Because we're dropping voice-embedding speaker diarization (which required downloaded audio), speaker attribution is inherently less precise. The product must surface this honestly (confidence/unknown states) rather than silently guessing.
- **G8 - Guests are first-class, not an afterthought.** Any named speaker (host or guest) whose predictions can be attributed with reasonable confidence gets their own scorecard, not just the four permanent hosts. See §6.4 and the Decisions Log (§14).
- **G9 - Prove attribution quality before scaling it.** Contextual (audio-free) speaker attribution is unproven at this project's outset. It must be validated on a small sample and explicitly signed off before being run across the full archive - see §6.4's validation gate and Phase 2 in §13.

## 2. Non-Goals

- Pixel-parity with the old Next.js UI. We're free to simplify/restyle as long as the core views exist.
- Real-time/dynamic backend. This remains a fully static site - all data is pre-baked into JSON/HTML at "build" time (a Claude-run script), not fetched from a live server at request time.
- Perfect speaker diarization. We are explicitly trading some attribution precision for zero cost/zero audio downloads (see §6.4 and §12).
- Multi-podcast generalization in v1 (the original project mentions this as a stretch goal too) - we'll keep the architecture podcast-agnostic where cheap to do so, but won't build a full plugin system now.

## 3. Comparison to Original Project

| Concern | Original (`allinpredictions`) | Rewrite (the repo root) |
|---|---|---|
| Episode discovery | Libsyn RSS + yt-dlp YouTube playlist match | Same idea, kept (both free) |
| Audio | Downloaded full MP3 archive | **Not downloaded at all** |
| Transcription | Paid ASR (Speechmatics primary; Deepgram/OpenAI/AssemblyAI alternates) | **Free YouTube captions** (`youtube-transcript-api` / `yt-dlp --write-auto-sub`) |
| Speaker diarization | SpeechBrain ECAPA-TDNN voice embeddings, cosine similarity vs. canonical host voiceprints | **Claude contextual attribution** from caption text only (no audio) - lower precision, explicitly flagged |
| Prediction extraction | OpenAI `gpt-5.1` via Responses API (paid, structured outputs) | **Claude Code** reading transcript chunks directly, writing structured JSON |
| Validation | OpenAI `gpt-5.1` + `web_search` tool, optional Grok cross-check (both paid) | **Claude Code** using its own `WebSearch`/`WebFetch` tools (free, built into Claude Code) |
| Topic tagging | OpenAI structured output | **Claude Code**, same enum-constrained approach |
| Frontend | Next.js 14, static export, Tailwind, Chart.js, React | **Vanilla HTML/CSS/JS**, hand-rolled SVG charts, no build step |
| Hosting | Cloudflare Pages | **GitHub Pages** |
| Ongoing cost | OpenAI/xAI/ASR API bills per run | **$0** |
| "Who runs the AI steps" | Python scripts calling external LLM APIs | **Claude Code itself**, via this repo's scripts as a scaffold |

## 4. High-Level Architecture

```
                     ┌──────────────────────────┐
                     │  Podcast RSS + YouTube    │   (free, no auth)
                     │  channel listing (yt-dlp  │
                     │  --flat-playlist, no dl)  │
                     └────────────┬──────────────┘
                                  │ episode index (id, title, date, video_id)
                                  ▼
                     ┌──────────────────────────┐
                     │ YouTube caption fetch      │   (free: youtube-transcript-api
                     │ (per episode video_id)     │    or yt-dlp --write-auto-sub)
                     └────────────┬──────────────┘
                                  │ raw captions (text + start/duration, no speaker labels)
                                  ▼
                     ┌──────────────────────────┐
                     │ Normalize + chunk          │   (plain Python, deterministic)
                     │ transcript                 │
                     └────────────┬──────────────┘
                                  │ transcript_chunks/*.txt
                                  ▼
        ┌─────────────────────────────────────────────────────┐
        │           CLAUDE-DRIVEN ANALYSIS STAGE                │
        │  (run interactively in Claude Code, or headless via   │
        │   `claude -p` invoked per-episode from a driver script)│
        │                                                        │
        │  1. Speaker attribution (contextual, per prediction)   │
        │  2. Prediction extraction → predictions.json           │
        │  3. Validation w/ WebSearch/WebFetch → checks.json      │
        │  4. Topic tagging → tags on each prediction             │
        └────────────────────────┬────────────────────────────┘
                                  │ per-episode JSON artifacts
                                  ▼
                     ┌──────────────────────────┐
                     │ Site generator (Python,    │   (deterministic, no LLM)
                     │ Jinja2 templates → static  │
                     │ HTML + embedded JSON)      │
                     └────────────┬──────────────┘
                                  │
                                  ▼
                     ┌──────────────────────────┐
                     │  repo root (index.html,│ ──► GitHub Pages
                     │  episodes/, host/, static/)│
                     └──────────────────────────┘
```

Two clean layers:
- **Mechanical layer** (deterministic Python scripts, no LLM): episode discovery, caption fetching, chunking, JSON→HTML site generation. Cheap to re-run, fully scriptable, no Claude involvement needed once written.
- **Judgment layer** (Claude Code): everything requiring reading comprehension, world knowledge, or web research. This is the part that satisfies "should be ran/updated entirely in Claude" - there is no OpenAI/xAI SDK call anywhere; Claude Code *is* the model doing the work, using its native tools (Read/Write/WebSearch/WebFetch).

## 5. Tooling & Cost Model

| Task | Tool | Cost | Auth needed? |
|---|---|---|---|
| Episode metadata | `yt-dlp -J --flat-playlist` against `@allin/videos`, or podcast RSS | Free | No |
| Captions | `youtube-transcript-api` (pip) - preferred; falls back to `yt-dlp --write-auto-sub --skip-download` | Free | No |
| Prediction extraction | Claude Code (this agent) | Free¹ | No (uses existing Claude Code session/subscription) |
| Speaker attribution | Claude Code, contextual inference from caption text | Free¹ | No |
| Validation research | Claude Code `WebSearch` / `WebFetch` tools | Free¹ | No |
| Topic tagging | Claude Code | Free¹ | No |
| Site build | Python + Jinja2 (or hand-rolled string templates to avoid even that dependency) | Free | No |
| Hosting | GitHub Pages | Free | GitHub account (already have) |

¹ "Free" relative to the old pipeline's per-token OpenAI/xAI/ASR billing - this work consumes your existing Claude usage instead of a separate metered API. Large archives (300+ episodes) still take real session time/turns, so batching and incremental runs matter (see §10).

## 6. Data Pipeline - Detailed Stages

### 6.1 Episode discovery
- Script: `scripts/fetch_episodes.py`.
- Pulls the All-In RSS feed (title, publish date, description, episode code parsed via regex) - reused logic from the original `all_in_downloader.py`, minus the MP3 download step.
- Pulls the YouTube channel's full upload list via `yt-dlp -J --flat-playlist` (metadata only, **no video/audio download**) and matches each RSS episode to a `video_id` using the same layered heuristics as the original (episode-code regex → normalized title match → nearest publish date → description link extraction). This gives us the `video_id` needed to fetch captions.
- **Canonical ordering/reference source:** [allin.com/episodes](https://allin.com/episodes) is the official episode index and is the source of truth for episode numbering and order. It lists episodes reverse-chronologically with a numeric `Episode #NNN`, publish date, title/description, and links out to YouTube/Apple/Spotify/X. It appears to run on "PodcastAI" infra; no public JSON/RSS feed was found behind it during inspection, so it's used as a **human-checkable reference for correct episode numbering/order**, not as a scraped data source - our own `episode_code` (parsed from RSS/YouTube titles, e.g. `E211`) must be reconciled against allin.com's numbering so the site's episode list/navigation matches the canonical order. Every episode transcript and prediction file in this rewrite should be ordered/numbered consistent with allin.com/episodes.
- Output: `data/episodes.json`: one row per episode: `{episode_id, title, published, published_iso, episode_code, video_id, youtube_url}`, with `episode_code` validated against allin.com/episodes numbering where possible.
- **Independent derivation + cross-check (per Decisions Log §14.4):** the rewrite derives its own episode↔YouTube matching from scratch (RSS + `yt-dlp` + allin.com/episodes numbering), rather than seeding from the old repo's output. Once derived, a comparison script (`scripts/compare_episode_sources.py`) diffs the rewrite's `data/episodes.json` against the old repo's `data/processed/all_in_episodes.json` (`video_id`/`youtube_url` per `episode_id`) and reports: episodes matched identically, episodes where the two disagree, and episodes either source is missing. This serves two purposes - a free correctness check for the rewrite's independent matching logic (using the old, already-debugged results as a reference oracle), and QA evidence supporting the eventual decision to fully replace the old pipeline (§14.5) once the rewrite is proven at least as accurate.
- Disagreements are resolved by hand against allin.com/episodes (the canonical numbering source) and logged to `data/episode_source_diff.json` for traceability - this diff report is expected input to the Phase-6+ decision on retiring the old pipeline.

### 6.2 Transcript acquisition
- Script: `scripts/fetch_transcripts.py`.
- For each episode's `video_id`, fetch the caption track via `youtube_transcript_api.YouTubeTranscriptApi.get_transcript(video_id)` (prefers manually-created captions if present, otherwise auto-generated). No API key, no rate-limit auth - it's an unofficial wrapper around YouTube's public timedtext endpoint.
- Fallback if that library is blocked/unavailable for a given video: `yt-dlp --write-auto-sub --sub-lang en --skip-download --convert-subs srt`, then parse the SRT/VTT locally.
- Output per episode: `data/transcripts/<episode_id>.json` - list of `{text, start_seconds, duration_seconds}` caption cues, essentially the original's `segments.json` but **without a `speaker_label` field** (this is the key structural difference from the old pipeline - see §6.4).
- Skips episodes whose captions are unavailable/disabled entirely (logs to `data/transcripts/_missing.json` for visibility; these episodes simply won't have predictions).

### 6.3 Transcript normalization & chunking
- Script: `scripts/prepare_chunks.py` (pure Python, deterministic - ports the original's `build_lines`/`chunk_lines` logic).
- Merges consecutive caption cues into readable lines, stamps each with `hh:mm:ss` (derived from `start_seconds`), and splits into ~15–25k character chunks with small line overlap between chunks (smaller than the original's 60k, because Claude Code's context budget per turn is the constraint here rather than an API's context window, and per-chunk analysis quality is better with smaller windows).
- Output: `data/chunks/<episode_id>/chunk_<n>.txt` - plain text, ready for Claude to read directly.

### 6.4 Speaker attribution (the key architecture change)
This is the hardest problem introduced by dropping audio/ASR diarization, and deserves explicit design:

**Why it's hard now:** YouTube captions (manual or auto-generated) do not include speaker labels. The original pipeline solved "who said this" with voice embeddings computed from downloaded audio; we have no audio.

**Approach - contextual attribution by Claude:**
- When Claude extracts a prediction from a chunk, it also assigns a `who` field using in-text contextual cues available in the transcript alone:
  - Direct address / reply patterns ("Jason, I think...", "No, Chamath, that's wrong because...").
  - Self-reference and recurring personal context (e.g., a speaker referencing their own fund/SPACs → likely Chamath; referencing their agency/politics commentary → likely Sacks; referencing biotech/Ohalo/agriculture → likely Friedberg; hosting/sponsor-read cadence → likely Jason).
  - Structural cues: the show's intro sequence and recurring bits (e.g., "Besties are back") sometimes name who's present that episode.
  - Cross-chunk consistency: Claude tracks a running best-guess "who's talking" state across the transcript rather than judging each line in isolation.
- Each prediction gets a `who` field: **not a fixed enum**. Per the Decisions Log (§14.2), guests get their own scorecards, so `who` is any identified speaker name Claude can attribute with reasonable confidence: the four canonical hosts (`jason|chamath|sacks|friedberg`), or a normalized guest identifier derived from the episode's title/description (e.g. `rep-swalwell`, `tom-emmer`) when the transcript context and episode metadata together make the attribution reasonably clear. Falls back to `unknown` when no attribution is possible.
- A `role` field (`host|guest`) accompanies `who` so the UI can distinguish "the four permanent hosts" from "everyone else" in navigation/listing without re-deriving it from the name.
- Each prediction also gets a `speaker_confidence` (`high|medium|low`).
- **Product decision:** a speaker (host or guest) only gets their own scorecard page if they have at least one prediction at `high` or `medium` confidence; `low`-confidence and `unknown` predictions are still recorded in the data (for transparency/debugging), still shown on their episode's page, but excluded from *any* accuracy scorecard - mirroring how the original excluded unmatched `Speaker X` labels, just with a visible confidence gradient instead of a hard embedding threshold, and extended to any named speaker rather than only the four hosts.
- Guest scorecards will naturally have small sample sizes (often one episode's worth of predictions) - the UI should show the underlying count prominently (e.g. "3 predictions") next to any guest's accuracy percentage so a thin sample isn't presented with false confidence.
- This is **strictly lower precision** than voice-embedding matching and must be disclosed in the site's footer/about page, same spirit as the original's existing disclaimer.
- **Validation gate - required before scaling (per Decisions Log §14.1):** contextual attribution must be proven on a small sample before it's trusted for the full archive. Concretely, as part of Phase 2 (§13): run extraction+attribution on the 3–5 sample episodes, then hand-check every attributed prediction's `who`/`speaker_confidence` against a human read of the actual transcript/video. Compute a rough precision estimate (correct attributions ÷ total attributed at `high`/`medium` confidence). This checkpoint must be explicitly reviewed and signed off (by the user) before Phase 4 (full-archive scale-out) begins. If precision is unacceptably low, the fallback is the local-diarization alternative below - not silently shipping a low-quality attribution scheme across 300+ episodes.
- **Documented alternative for later** (triggered only if the validation gate above fails): a v2 could add a *local, free* diarization pass using an open-source model (e.g., `pyannote.audio` community pipelines) run against a temporarily-downloaded/streamed audio snippet - this would reintroduce a limited, on-demand audio fetch (not a full archive download) solely to get a diarization *label sequence* (A/B/C/D) that we then align to caption timestamps, without ever needing paid ASR.

### 6.5 Prediction extraction
- Claude reads each chunk (from §6.3) directly (via the `Read` tool) and produces structured prediction entries following the same substantive rubric as the original prompt: concrete, falsifiable, time-bound claims only; skip vague futurism.
- For each prediction: `{id, who, speaker_confidence, quote, timestamp, prediction}` - `id` stays deterministic (`<who>-<timestamp>`, or `unknown-<timestamp>` when unattributed) so re-runs are stable/dedupeable.
- Claude writes results with the `Write`/`Edit` tool straight to `data/predictions/<episode_id>.json` - no intermediate API round-trip, no JSON-mode SDK object; Claude simply authors the JSON file per the schema in §7.
- Batching: for a full-archive run, a driver script (`scripts/run_extraction.sh` or a `/extract-episode` slash command) iterates episodes and either (a) is executed turn-by-turn interactively by Claude in a session, or (b) shells out to `claude -p "<extraction prompt> <chunk path>" --output-format json` per chunk for unattended batch runs. Both paths are documented so the "who runs it" question always resolves to "Claude," just with different levels of interactivity.

### 6.6 Prediction validation
- For each extracted prediction, Claude uses its `WebSearch` (and `WebFetch` for specific promising sources) tools to research whether it came true, exactly mirroring the original's `result ∈ {right, wrong, ambiguous, inconclusive}` + cited `explanation` design - just executed by Claude directly instead of via OpenAI's hosted `web_search` tool.
- Output: `data/checks/<episode_id>.json`, `{id, result, explanation, sources: [{title, url}]}`.
- No second "Grok cross-check" model in v1 (that existed in the original purely as a second *paid* opinion) - Claude's own single validation pass is the default. If we want a second opinion later without paying for another model API, we could re-run validation in a fresh Claude session and diff the two verdicts - documented as a possible Phase 2 addition, not required now.
- Idempotency: skip predictions that already have a `checks` entry unless explicitly forced (same `--force` convention as the original).

### 6.7 Topic tagging
- Reuses the original's fixed tag enum (`politics, government, conflict, venture, tech, ai, markets, economy, health, climate, science`) for continuity with existing mental model, adjustable via a config file (`config/tags.json`).
- Claude assigns 0+ tags per prediction directly while doing extraction (fold into §6.5 rather than a separate pass, since Claude is already reading the full context) - simplifies the pipeline from 3 Claude passes (extract/validate/tag) in the original design down to 2 (extract+tag, then validate).

### 6.8 Incremental & idempotent updates
- Every stage checks for existing output files and skips unless `--force`/explicitly asked to redo - same discipline as the original scripts.
- A `data/manifest.json` tracks per-episode pipeline status (`captions_fetched`, `predictions_extracted`, `validated`, `tagged`, timestamps) so "update the site with new episodes" is a single command that only touches what's new.
- New-episode workflow: re-run `fetch_episodes.py` → diff against `data/manifest.json` → run §6.2–§6.7 only for new episode IDs → regenerate site (§9) → commit.

## 7. Data Model (JSON Schemas)

`data/episodes.json` (array):
```json
{
  "episode_id": "E250119_CONGRESS",
  "title": "Inauguration Interviews: ...",
  "published": "2025-01-20",
  "episode_code": "E211",
  "video_id": "dQw4w9WgXcQ",
  "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

`data/predictions/<episode_id>.json`:
```json
{
  "meta": { "count": 4, "count_by_who": { "jason": 2, "chamath": 1, "unknown": 1 } },
  "predictions": [
    {
      "id": "chamath-00:12:34",
      "who": "chamath",
      "role": "host",
      "speaker_confidence": "high",
      "quote": "...",
      "timestamp": "00:12:34",
      "prediction": "...",
      "tags": ["markets", "economy"]
    },
    {
      "id": "rep-swalwell-00:41:02",
      "who": "rep-swalwell",
      "role": "guest",
      "speaker_confidence": "medium",
      "quote": "...",
      "timestamp": "00:41:02",
      "prediction": "...",
      "tags": ["politics"]
    }
  ]
}
```

`data/checks/<episode_id>.json`:
```json
{
  "meta": { "count": 4, "count_by_result": { "right": 2, "wrong": 1, "inconclusive": 1 } },
  "checks": [
    {
      "id": "chamath-00:12:34",
      "result": "right",
      "explanation": "...markdown with citations...",
      "sources": [{ "title": "...", "url": "..." }]
    }
  ]
}
```

Site generation joins these three by `episode_id`/`id` into the final per-episode and per-host artifacts the static generator consumes (§9).

## 8. Repository Structure (the repo root)

**Status (2026-08-25): this tree reflects the actual repo root after the §14.5 restructure**, not an aspirational future state - `rewrite/` no longer exists as a subfolder; everything below lives directly at the repo root, alongside the archived `old/` pipeline (kept for reference, out of scope for this PRD - see §32).

```
├── README.md                  ← general-reader front door (root only, per §16.1's folder standard)
├── LICENSE
├── .nojekyll                  ← empty file; tells GitHub Pages not to run Jekyll on the static output
├── docs/
│   ├── PRD.md                  ← this document
│   ├── DESIGN.md                ← visual/UX system: colors, type, spacing, breakpoints, components
│   └── PATCHNOTES.md            ← dated changelog
├── requirements.txt           ← youtube-transcript-api, yt-dlp, jinja2, pyyaml (all free/OSS)
├── config/
│   ├── hosts.yaml              ← canonical *permanent* host roster (jason/chamath/sacks/friedberg) + attribution hints. Guests are NOT listed here - they're derived per-episode from title/description + transcript context (§6.4) and don't need config entries.
│   ├── tags.json                ← allowed topic tag enum
│   ├── youtube_urls_override.json ← manual episode_id → video_id overrides for episodes automatic matching can't resolve
│   └── annual_prediction_episodes.json ← episode ids flagged as the yearly "predictions" specials, for the planned Annual Predictions filter (§17)
├── data/
│   ├── episodes.json           ← full 404-episode archive index
│   ├── manifest.json           ← per-episode pipeline status (captions/chunked/predictions_extracted/validated), regenerated by build_manifest.py
│   ├── raw_feed.xml, episode_source_diff.json, episodes_full_archive.json, episodes_all_missing.json, episodes_refetch.json, processed_episode_map.json ← intermediate/QA artifacts from episode discovery and the old-repo cross-check (§6.1, §14.4); not consumed by the site generator
│   ├── transcripts/<episode_id>.json
│   ├── chunks/<episode_id>/chunk_*.txt
│   ├── predictions/<episode_id>.json ← 355-357 files (see §29 for the exact-count discrepancy note)
│   └── checks/<episode_id>.json ← 32 files as of 2026-08-25
├── scripts/
│   ├── fetch_episodes.py       ← RSS + yt-dlp episode/video_id discovery (§6.1)
│   ├── compare_episode_sources.py ← QA diff against the archived old pipeline's episode data (§14.4)
│   ├── fetch_transcripts.py    ← YouTube caption fetch (§6.2)
│   ├── prepare_chunks.py       ← transcript chunking (§6.3)
│   ├── build_manifest.py       ← refreshes data/manifest.json (§6.8)
│   ├── generate_site.py        ← deterministic templater, no LLM calls (§9)
│   ├── map_processed_episodes.py, reconcile_batch1.py, dedup_reconciled.py, adapt_processed_predictions.py ← one-time migration scripts that carried already-processed predictions over from the archived old pipeline's `data/processed/` into this rewrite's schema; not part of the ongoing pipeline, kept for provenance. **Not yet individually documented in this PRD** - see §29's Documentation Versus Reality table.
├── prompts/
│   ├── extract_and_tag.md      ← the instruction Claude follows per chunk
│   └── validate.md             ← the instruction Claude follows per prediction
├── site_src/
│   ├── templates/               ← Jinja2 templates
│   │   ├── base.html, index.html, episodes_index.html, episode.html, host.html, host_index.html, about.html
│   └── static/
│       ├── style.css
│       └── app.js               ← vanilla JS: chart rendering + filter interactivity (§9.3, §27)
│
│   BUILD OUTPUT (generated directly into the repo root, not a subfolder - see §8.1 for why):
├── index.html
├── about.html
├── episodes/*.html
├── host/*.html
└── static/                      ← copied from site_src/static/ at build time
```

The generated site files (`index.html`, `about.html`, `episodes/`, `host/`, `static/`) are git-tracked (unlike the original's gitignored `data/`) since GitHub Pages needs the built output committed (no CI build step in v1 - see §11). `scripts/generate_site.py` only ever cleans/rewrites those specific generated paths on rebuild - it never touches `scripts/`, `data/`, `config/`, `site_src/`, `prompts/`, `old/`, or documentation files, even though they all live alongside the generated output at the same directory level.

### 8.1 Why the site is generated into the repo root, not a `docs/` subfolder (decided 2026-08-04)
GitHub Pages only supports two publish locations: the repo root, or a `/docs` folder on the branch. The original plan (§9, §11 below) used `docs/` as that publish folder. That was changed for two reasons:
1. **Matches the eventual final structure now, not just at cutover time.** Per the Decisions Log (§14.5), the repo root is intended to eventually *become* the repo root when the old pipeline is retired. Generating the site directly into the repo root means the working directory already looks like what the final repo root will look like - `index.html` sits where it will always sit - rather than needing a path shuffle at cutover.
2. **Frees up the `docs/` name for actual documentation.** The documentation-consolidation standard from §16.1 requires `/docs/PRD.md`, `/docs/DESIGN.md`, `/docs/PATCHNOTES.md` at the repo root. That directly collides with GitHub Pages' `/docs`-as-site-output convention - the same folder can't cleanly be both "the published website" and "the project's markdown documentation." Generating the site into root instead of `docs/` resolves this: `docs/` is reserved exclusively for documentation, and GitHub Pages will eventually be configured as **Deploy from branch → main / (root)** rather than `/docs` (see §11).

This does mean generated site files and source directories (`scripts/`, `data/`, `config/`, `site_src/`, `prompts/`) sit side by side at the same level in the repo root. That's intentional and matches how many static sites are structured when deployed from repo root; the generator's targeted cleanup (only ever touching its known generated paths, never a blanket wipe of the output directory) is what keeps this safe.

## 9. Site Generation & Frontend Architecture

### 9.1 Why static-generate instead of a client-side SPA
A pure client-rendered single-page app (fetch JSON, route via `#hash`, render with vanilla JS) is possible but sacrifices real URLs, crawlability, and simplicity. Instead we pre-render actual `.html` files per episode/host at build time using a small Python templater (Jinja2 is free/OSS and doesn't require Node), then layer a *little* vanilla JS on top purely for client-side interactivity (chart filter toggles). This is the closest vanilla-tooling analog to what Next.js's `output: 'export'` was doing, minus React/Node.

### 9.2 Pages
- `/index.html`: host scorecards (charts) + recent episodes, same as original home page.

**Home page layout convention:** every prediction-listing section on the home page (The Big Ones, Recently Settled, Recent Episodes) caps at 6 items, controlled by a single `HOME_SECTION_MAX = 6` constant in `generate_site.py`. Each section pairs its capped preview with a "Browse the full ledger"/"View all" link to the corresponding full page, so the home page stays scannable while the complete data is always one click away. If the cap ever needs to change, update `HOME_SECTION_MAX` once rather than each section's slice individually.

**Host/guest page convention:** `host.html` renders identically for every speaker (host or guest) via the same `build_speaker_index()`/render loop, so any change to that template automatically applies to both. The page's chart-filter UI (§27) also drives the prediction-card list below it: the topic dropdown and the resolved-only checkbox both filter the cards (via each card's `data-tags`/`data-result` attributes) as well as the chart, so they stay in sync; the year/topic chart view stays chart-only since the card list already shows every year. A "Collapse"/"Expand" button collapses the card list independently of the chart (toggling `style.display` directly, not the `hidden` attribute -- `.predictions { display: flex; }` in the author stylesheet overrides the browser's UA `[hidden]{display:none}` default).
- `/episodes/index.html`: full episode list.
- `/episodes/<episode_id>.html`: one episode's predictions.
- `/host/<who>.html`: one speaker's full prediction history + scorecard. Generated for **any** speaker (host or guest) with ≥1 prediction at `high`/`medium` confidence, not just the four permanent hosts (per Decisions Log §14.2) - so the set of host pages is dynamic, driven by `data/predictions/*.json`, not a hardcoded list of four.
- `/host/index.html`: directory of all speaker pages, visually separating the four permanent hosts from guests (using the `role` field) so the homepage/nav isn't cluttered with dozens of one-episode guest scorecards.
- `/about.html`: static about/disclaimer page.
- Prediction "permalinks" become simple in-page anchors (`/episodes/<id>.html#<pred_id>`) rather than a separate route - removes the need for the original's base62 ID encoding scheme entirely (that existed to make Next.js dynamic-route URLs; a static anchor doesn't need it).

### 9.3 Charts - vanilla, no Chart.js
- Because we have no bundler and don't want a CDN dependency (keeps the site fully offline-buildable and free of third-party script risk), charts are hand-rolled:
  - **Donut/accuracy chart**: pre-computed percentages rendered as an inline `<svg>` with `stroke-dasharray` arcs, generated at build time by the Python templater (deterministic, no client JS needed for the default view).
  - **By-year / by-topic stacked bars**: same idea - SVG `<rect>`s sized server-side (at build time) for the default filter state.
  - **Client-side interactivity** (the "Resolved only" checkbox, topic dropdown, Year/Topic toggle): a small `app.js` (~150-300 lines, no dependencies) holds the *already-computed* aggregate stats as an inline `<script type="application/json">` blob per page (small - just counts, not full prediction text) and redraws the SVG on filter change using plain DOM APIs. This matches the original `HostCharts.tsx` behavior without React.

### 9.4 Styling
- Hand-written `style.css`, dark theme carried over from the original (`#080d0b` background, white text) for visual continuity. No Tailwind (would require a build step); plain CSS custom properties for the small color palette (right/wrong/ambiguous/inconclusive colors) instead.

### 9.5 YouTube deep links
- Same UX as original: prediction cards link to `https://www.youtube.com/watch?v=<video_id>&t=<seconds>`, with a one-time `localStorage`-gated disclaimer modal (small vanilla JS, ports directly from the original's `YoutubeLink.tsx` logic without React).

## 10. Automation Workflow - "How Claude Runs This"

Two supported modes, both documented in `README.md`:

**Interactive (recommended for initial buildout / spot fixes):**
1. User runs the mechanical scripts (§6.1–6.3) via Claude Code's Bash tool to produce `data/chunks/*`.
2. Claude reads chunks with `Read`, extracts/tags predictions with `Write`/`Edit` following `prompts/extract_and_tag.md`, validates with `WebSearch`/`WebFetch` following `prompts/validate.md` - all within the normal conversational flow, a handful of episodes per turn.
3. Claude runs `scripts/generate_site.py` to rebuild the site (generated directly into the repo root - see §8.1).
4. Commit + push (user confirms, per this session's standing git-safety norms).

**Headless/batch (for scaling to the full ~300+ episode archive without manual back-and-forth):**
- A driver script loops over pending episodes/chunks and invokes `claude -p "$(cat prompts/extract_and_tag.md) $(cat chunk.txt)" --output-format json` (or the equivalent Claude Code headless invocation), writing each response to the right `data/predictions/<id>.json` path. Same for validation, with `WebSearch`/`WebFetch` tool access granted to the headless invocation.
- This keeps "the LLM doing the work" strictly as Claude in every case - never a third-party model API - while still allowing unattended, scriptable batch runs.
- Concurrency/pacing: headless batch runs should throttle themselves (small delays / modest parallelism) - unlike the original's `ThreadPoolExecutor(max_workers=10)` against a metered API, we're bound by session/turn economics, not $ per call, so the right default is "a handful of episodes per invocation," not maximum parallelism.

**Update cadence:** run the discovery step periodically (manually, e.g. weekly) to pick up new episodes; the manifest-driven incremental design (§6.8) means this is a small, bounded amount of new Claude work each time, not a full re-run.

## 11. Deployment (GitHub Pages)

- v1: commit the generated site files (`index.html`, `about.html`, `episodes/`, `host/`, `static/`) directly at the repo's root on the default branch; enable **GitHub Pages → Deploy from branch → `main` / `(root)`** in repo settings (see §8.1 for why root instead of `/docs`). No CI required - Claude (or the user) runs `generate_site.py` locally/in-session and commits the output alongside the source data.
- Custom domain: optional, via a `CNAME` file at the repo root if desired later (not required for v1).
- Phase 2 (optional): a GitHub Action that runs the mechanical scripts + `generate_site.py` on a schedule and opens a PR - deliberately **not** in v1 scope, because the "intelligent" pipeline stages must run through Claude, and CI can't invoke this coding-assistant session. Automating *only* the deterministic regeneration (not the analysis) could still be a small later add-on.

## 12. Risks & Limitations

| Risk | Impact | Mitigation |
|---|---|---|
| No true speaker diarization → attribution errors | Wrong host credited/blamed for a prediction | `speaker_confidence` field; low-confidence excluded from host stats; clear disclaimer; Phase 2 optional local diarization (§6.4) |
| YouTube auto-captions have transcription errors (no human review, unlike Speechmatics) | Garbled quotes, missed predictions, wrong timestamps | Prefer manually-created captions when available; treat quotes as "best effort," same disclaimer language as original |
| `youtube-transcript-api` can be blocked/rate-limited by YouTube without warning (it's an unofficial API) | Pipeline stalls on caption fetch | `yt-dlp --write-auto-sub` fallback (different code path, same source data); backoff/retry; treat missing captions as a skip, not a hard failure |
| Claude session/turn cost of processing 300+ episodes | Slow full-archive buildout | Incremental manifest-driven processing (§6.8); headless batch mode (§10); process newest/most-relevant episodes first |
| Single-model validation (no Grok cross-check) | Slightly less error-correction on validation verdicts than original | Optional future "re-validate in a fresh session and diff" pattern; not required for v1 |
| Hand-rolled SVG charts vs. Chart.js | More code to write/maintain ourselves | Scope tightly to the 3 chart types actually used; keep `app.js` small and dependency-free by design |
| No SSR analytics/OG image pipeline parity | Minor - original had Next `Metadata`/OG image | Port `<meta>` tags + a static `og.png` by hand; trivial in plain HTML |

## 13. Phased Implementation Plan

**Phase 0 - Scaffolding**
- Create the repo root structure per §8, `requirements.txt`, `config/hosts.yaml`, `config/tags.json`, empty `prompts/*.md`.

**Phase 1 - Mechanical pipeline (deterministic scripts, no Claude analysis yet)**
- `fetch_episodes.py`, `fetch_transcripts.py`, `prepare_chunks.py`, `build_manifest.py`.
- Validate against a small sample (3–5 episodes) end-to-end: episode list → captions → chunks on disk, correct and readable.

**Phase 2 - Claude analysis loop, small batch**
- Write `prompts/extract_and_tag.md` and `prompts/validate.md`.
- Run extraction + validation interactively on the same 3–5 sample episodes; hand-check quality of speaker attribution, prediction quality, and validation verdicts before scaling up.
- Iterate on the attribution heuristics (§6.4) and prompts based on real output.

**Phase 3 - Static site generator**
- Build `generate_site.py` + Jinja2 templates + `style.css` + `app.js` against the Phase 2 sample data; get the home page charts, episode pages, and host pages fully working locally (generated directly into the repo root - open `index.html` directly in a browser).

**Phase 4 - Scale to full archive**
- Run the pipeline (interactive and/or headless batch) across all discovered episodes, respecting the manifest for incremental resume.
- Regenerate the full site.
- **Batching process (confirmed 2026-08-04; scope narrowed to initial load on 2026-08-27 - see the incremental process below for anything after that):** two separate, sequential sweeps rather than interleaving extraction and validation per episode. This two-sweep design applied to the **initial full-archive backfill only** (getting from 0 episodes processed to the point where every episode discoverable at the time had both predictions extracted and validated) - it is not the standing process for new/incremental episodes going forward (see "Incremental process" below).
  1. **Extraction sweep, chronological, oldest-first.** Starting from episode 1 (the earliest episode in the archive), process 10 episodes at a time in publish order, extracting + attributing + tagging predictions for each (per `prompts/extract_and_tag.md`) until every episode in the archive has a `data/predictions/<episode_id>.json`. Batch size is a target, not a hard rule - dense episodes (the annual "predictions" specials) take meaningfully longer per episode than a typical week's episode or a retrospective "Bestie Awards" show, so a batch may need to flex smaller when it lands on several dense episodes in a row.
  2. **Validation sweep, ascending by prediction count, fewest-first (updated 2026-08-04).** Only after the full extraction sweep is complete, go back through and validate 10 predictions at a time (per `prompts/validate.md`), selecting whole episodes ordered by ascending `count` of predictions in `data/predictions/<episode_id>.json` (episodes with the fewest predictions first) rather than by publish date, so a "batch" clears complete episodes quickly instead of leaving many episodes partially validated. Episodes with equal prediction counts are tie-broken oldest-first, preserving the original rationale that older predictions have had more time to resolve and are more likely to produce a real `right`/`wrong` verdict rather than `inconclusive`. (Superseded rule, kept for context: earlier sessions used strict chronological oldest-first; that produced very uneven batch sizes, since some early episodes like live election-night specials have 50+ predictions each.)
  - Rationale for two separate sweeps instead of one combined pass, for the initial load specifically: it kept each pass focused on one kind of judgment call (attribution vs. fact-checking), made progress independently trackable via `data/manifest.json`'s `predictions_extracted` and `validated` flags, and meant a full-archive extraction pass didn't stall waiting on web-search-heavy validation work across 300+ episodes at once.
  - Expect early episodes to need more manual entries in `config/youtube_urls_override.json` - the automatic episode-code/title/nearest-date matching (§6.1) tends to be more reliable on episodes with consistent "E211"-style numbering in the title, which is less consistent in the earliest parts of the archive and in guest-interview/special episodes whose titles don't follow that convention at all (see the incremental process below, which hits this same issue on the post-initial-load backlog).
  - **Status: the initial full-archive load this two-sweep process governed is complete** as of 2026-08-27 (357/357 validation-eligible episodes extracted and validated). What remains (episodes discovered after that point, plus a 47-episode backlog that was never run through extraction at all - see below) is governed by the incremental process instead, not by resuming this two-sweep design.

- **Incremental process for new/backlog episodes (adopted 2026-08-27, supersedes the two-sweep design above for anything past the initial load):** once the initial full-archive extract-then-validate backfill is done, running a second full sweep across the whole archive for every newly-discovered batch of episodes is unnecessary overhead - the volumes involved (typically single-digit episodes at a time: new weekly episodes, or working down a smaller pre-existing backlog) are small enough that splitting extraction and validation into separate passes just doubles the fixed overhead (manifest rebuild, site regen, docs updates, commit/push) for no real benefit. Instead, extraction and validation are combined into one pass per batch:
  1. **Batch size: 5 episodes at a time,** oldest-published-first among whatever's unprocessed (confirmed via `data/manifest.json`'s `predictions_extracted` flag cross-checked against actual `data/predictions/<episode_id>.json` file existence - the manifest's `captions_fetched`/`chunked` booleans are not reliable ground truth, see the note on this in project memory/PRD framing elsewhere). Recompute the candidate list fresh each time rather than reusing a stale cached list.
  2. **Per batch, run the full pipeline for those 5 episodes together:** resolve `video_id` (re-run `fetch_episodes.py`; add manual `config/youtube_urls_override.json` entries for anything the automatic matcher misses - expect this routinely for guest-interview/special episodes whose titles don't carry an "E###" code) → fetch transcripts (`fetch_transcripts.py`) → chunk (`prepare_chunks.py`) → Claude extraction/attribution/tagging (`prompts/extract_and_tag.md`) → Claude validation (`prompts/validate.md`) on the same 5 episodes' predictions, all within the same batch before moving to the next 5.
  3. **Then the same close-out steps used throughout this project's validation batches:** `build_manifest.py` → `generate_site.py` (must pass clean) → update `docs/PATCHNOTES.md` (new version entry) and this PRD's §19 roadmap (new row) → commit → push.
  4. **This is the standing process for all future episodes too, not just the pre-existing 47-episode backlog.** A periodic (e.g. weekly, or whenever asked) discovery run (`fetch_episodes.py`) picks up newly published episodes; they enter the same "unprocessed" pool as the backlog and get worked in the next batch(es) of 5 using this identical procedure. There is no separate "new episode" playbook - backlog clearance and ongoing maintenance are the same process.
  5. **Attribution caveat specific to this pool:** the pre-existing 47-episode backlog is overwhelmingly guest-interview and special/live episodes rather than the usual 4-host panel format. `prompts/extract_and_tag.md`'s "solo guest-interview episodes" rule (non-guest speaker defaults to `jason` at `medium` confidence) covers most of these cleanly, but multi-guest panel episodes (e.g. episodes with several named guests at once) don't fit that default and need more careful per-speaker contextual judgment; flag any episode where attribution confidence comes back broadly low rather than silently guessing.

**Phase 5 - Deploy**
- Push the generated site (now at repo root after the §14.5 restructure) to GitHub, enable Pages (Deploy from branch → root, per §8.1/§11), verify the live URL end-to-end (charts render, links work, YouTube deep-links resolve, mobile layout is usable).
- **Sequencing note (updated 2026-08-25, see §19):** Deploy now runs *early*, right after the repo restructure/full site replacement (§14.5) and the pre-launch parity pass (§27), as an MVP launch, not as the final step. The full-archive validation sweep and the §16.2/§16.3/§17 hardening/feature passes are explicitly **not** gates on this deploy; they continue as post-launch work checked against the live URL. (Superseded rule, kept for context: the 2026-08-04 plan had Deploy running last, after full local parity/QA confidence.)

**Phase 6 (optional, post-v1)**
- Local diarization enhancement (§6.4 alternative), if the Phase 2 validation gate flags contextual attribution as insufficient.
- Second-opinion validation pattern.
- GitHub Action for the deterministic-only regeneration step.
- Annual Predictions episode filter: see §17 for full detail.

## 14. Decisions Log

The five open questions from the initial draft of this PRD have been resolved as follows. Recorded here (rather than deleted) so the reasoning survives for future sessions.

### 14.1 Attribution strictness - **Contextual-guess only, gated by a validation checkpoint**
Decision: go with audio-free contextual attribution (§6.4) as the v1 approach - but explicitly **do not fully commit to it** until it's tested and verified on a small sample. A validation gate is now a required, non-skippable step in Phase 2 (§13): hand-check attribution precision on the 3–5 sample episodes and get explicit sign-off before scaling to the full archive. If precision comes back too low, the fallback is the local-diarization alternative (§6.4), not shipping the weak version broadly. This nuance is also captured as new Goal **G9** (§1).

### 14.2 Host roster / guest handling - **Guests get their own scorecards too**
Decision: any named speaker (host or guest) with at least one `high`/`medium`-confidence prediction gets a real scorecard page, not just the four permanent hosts. A `role` field (`host|guest`) distinguishes the two in navigation so the site doesn't read as "four hosts plus noise" - guests are first-class, just visually separated (§9.2's `/host/index.html` directory) and always shown with their raw prediction count next to their accuracy percentage so small samples aren't misread as statistically meaningful. Captured as new Goal **G8** (§1); data model, page generation, and config sections updated accordingly (§6.4, §7, §8, §9.2).

### 14.3 Batch execution mode - **Interactive first, batch later**
Decision: confirmed as originally recommended. Early episodes are processed visibly, turn-by-turn, in normal conversation so quality can be sanity-checked cheaply; the headless `claude -p` batch driver (§10) is built only once interactive results look right - practically, this lines up with clearing the §14.1 validation gate before Phase 4's full-archive run.

### 14.4 Starting data - **Independently re-derive AND cross-check against the old repo**
Decision: neither pure option: the rewrite derives its own episode↔YouTube matching from scratch (not seeded from the old repo), but then diffs its results against the old repo's already-resolved `data/processed/all_in_episodes.json` as a free correctness check and as the evidence base for eventually retiring the old pipeline. Full mechanism documented in the new cross-check step added to §6.1 (`scripts/compare_episode_sources.py`, `data/episode_source_diff.json`).

### 14.5 Repo scope - **MVP-first cutover (superseded 2026-08-25): replace now, don't wait for full validation**
Original decision (2026-08-04): the repo root stays a parallel/experimental sibling short-term, cutover timing deferred until parity/QA confidence.

**Superseded 2026-08-25.** The user made the explicit call to push an MVP to production *before* the full-archive validation sweep finishes, rather than waiting for validation to be "meaningfully progressed" as originally planned. The cutover mechanism stays a full replacement, but happens now:
- Repo root becomes the generated site: everything currently under the repo root (site output, `data/`, `scripts/`, `config/`, `docs/`, `prompts/`) moves up to the repo root.
- The old pipeline (root-level `scripts/`, `web/`, `config/`, `data/`, plus `AGENTS.md`, `DEVELOPMENT.md`, `analysis.md`, root `requirements.txt`) is archived, not deleted, into a new top-level `old/` folder, preserving it for reference/rollback.
- GitHub Pages then deploys from the new repo root, per §8.1/§11.
- Full-archive validation (and the remaining hardening/feature passes: §16.2, §16.3, §17, `video_id` resolution) become **post-launch, ongoing work against the live site**, not pre-launch gates. "MVP" here means the site is live, correct, and clearly labeled as a work in progress (unvalidated predictions show as such), not that every prediction has been checked.
- This should be treated as the settled strategic direction going forward: future sessions should default to shipping early and iterating live, not batching every improvement before the first deploy.

### 14.6 Extraction sub-agent concurrency - **Max 5 concurrent, no sub-sub-agents**
Decision, made after an incident on 2026-08-04: a parallel extraction batch of ~10 agents recursively self-spawned further per-episode sub-agents instead of working sequentially, ballooning to 30+ concurrent agents and burning through the usage budget far faster than expected before being manually stopped mid-batch (v0.4.0 patch note). Going forward, any parallel extraction (or similar) batch is capped at 5 concurrently-running agents, and each agent's instructions must explicitly forbid delegating to further sub-agents - batches larger than 5 episodes are run as sequential waves of ≤5, not as one larger parallel burst. This is a standing rule, not specific to this one incident.

## 15. Success Criteria

- The generated site (at the repo root) renders correctly as a static site with zero JavaScript build step, served locally by opening the file or via `python -m http.server`, and confirmed working once pushed to GitHub Pages.
- At least one full episode is processed end-to-end (captions → predictions → validated → tagged → on the site) with no OpenAI/xAI/paid-ASR calls anywhere in the process.
- Host scorecards, episode pages, and host pages all render with real data, including the resolved-only/topic/year chart interactivity.
- Pipeline is demonstrably incremental: re-running discovery + processing after adding one new episode only does new work for that episode.
- README/PRD are sufficient that a future Claude Code session (with no memory of this conversation) could pick up the pipeline and continue it correctly from the docs alone.

## 16. Post-MVP Roadmap (Deferred - Do Not Execute Until MVP Ships)

Three hardening passes are queued for after the MVP (Phases 0–5) is live and working. These are explicitly **not** part of v1 scope - they assume there is a working site with real content to audit, fix, and document. Each is written up here in full detail now so a future session (with or without this conversation's memory) can execute it correctly without re-deriving the plan.

### 16.1 Documentation audit & consolidation

**Status: executed twice - partially on 2026-08-04, then completed in full on 2026-08-25.** The 2026-08-04 pass ran the folder-structure move and an initial documentation audit early (before Phase 5 deploy, before the mobile-responsive and writing-style sweeps, and with only 9 of ~404 episodes processed), explicitly flagged at the time as needing a follow-up once the site was live and more of the archive was processed. The 2026-08-25 pass is that follow-up: it ran after the MVP was live (357/404 episodes with extracted predictions, 32 validated, the repo restructure and GitHub Pages deploy both complete), re-crawled the full codebase, added the sections this PRD was still missing (§28-§33 below: Conventions, Browser Testing, Deprecation and Removal, Documentation Versus Reality, Risks and Open Questions, Working Practice), reconciled every "planned"/"post-launch" status line that had since actually shipped, and ran the writing-style sweep (§16.2) in the same pass rather than waiting for a separate post-launch window, per the user's explicit request. §16.3 (mobile-responsive audit) remains genuinely deferred, not yet run.

One deliberate change made in the 2026-08-25 pass: the README requirements below (tech stack table, install commands, version numbers) were the *original* README spec from the 2026-08-04 audit and are what the current root `README.md` still follows. A later, more specific instruction for this same 2026-08-25 pass asked for a stricter, general-reader-facing README instead - no install steps, no version numbers, no dependency lists, all of that content living only in this PRD's Runbook (§21) and Technical Requirements (§22) sections. That stricter spec is what `README.md` was rewritten to in this pass; the bullet below is left as written (rather than silently edited) so the supersession is visible, per this project's own "flag, don't silently overwrite" documentation policy (see §29).

**Original trigger (superseded above, kept for reference):** once the MVP site is deployed and the pipeline has processed a meaningful slice of the archive (not necessarily the full 300+ episodes, but enough that the docs describe real, working behavior rather than aspirational design).

**Objective:** perform a full documentation audit of this project's docs, ensuring every document accurately reflects the current state of the codebase, with no gaps, outdated information, or missing coverage - then consolidate everything into exactly four files.

**Required end-state folder structure:**
```
/project-root
├── README.md          ← root only, never inside /docs
└── /docs
    ├── PRD.md
    ├── DESIGN.md
    └── PATCHNOTES.md
```
Any documentation file that exists outside `/docs` (other than root `README.md`) must be moved into `/docs`. If `/docs` doesn't exist yet at that point, create it. This PRD itself (currently `docs/PRD.md`) is expected to relocate to `docs/PRD.md` as part of this pass, with `README.md` staying at `the repo root's root.

**Process (in order):**
1. **Full codebase scan first, before touching any documentation.** Crawl the entire rewrite codebase and build a complete picture of what exists: all files, features, components/templates, routes/pages, configs, scripts, and pipeline logic. Do not skip this step or start editing docs from memory/assumption.
2. Open every existing documentation file one by one (this PRD, the rewrite README, any prompts/*.md, any inline docs).
3. For each, diff its claims against the actual codebase: what's outdated, missing, inaccurate, or incomplete.
4. Rewrite/update each document so it is fully accurate and comprehensive for the *current* version of the site - not the originally planned version if the plan drifted during implementation.
5. Consolidate all documentation into the four target files. Every other doc file must be reviewed and folded in - none skipped.
6. Create any missing documentation files/sections the codebase clearly warrants but that don't exist yet.
7. After all documents are updated, produce a summary of what changed in each file and why.

**Standard to hold every doc to:** thorough enough that a new contributor or another AI model could understand the entire project from `/docs` alone, without needing to read the source code first.

**Required contents per file:**

- **`README.md` (root)**: developer-facing, no marketing language. Must include: project name + one-sentence description; link to the live GitHub Pages site; tech stack list with versions; prerequisites (Python version, any package manager, environment requirements); exact installation commands in order; how to run locally (which script/command, any local server + port for previewing `docs/`); environment variable reference (name, purpose, required/optional - expected to be short/empty here since v1 has no API keys, but must still be stated explicitly rather than omitted); build and deploy instructions (how `generate_site.py` output gets to GitHub Pages); link to `/docs` for full documentation.

- **`/docs/DESIGN.md`**: the visual/UX system. Must include: design philosophy (1–3 sentences); full color palette (every token, hex value, intended use - right/wrong/ambiguous/inconclusive colors, background, text, borders); typography (font families, sizes, weights, line heights per role: H1–H3, body, caption, label, code); spacing system/base unit; every responsive breakpoint used and what changes at each; component pattern rules (prediction cards, buttons, charts, modals, filters - how each should be built/styled consistently); accessibility standards (WCAG level targeted, contrast requirements, keyboard navigation expectations - relevant since this rewrite drops React's accessibility conveniences and hand-rolls SVG/DOM); animation/motion rules (timing, easing, when motion is/isn't appropriate - e.g. the chart redraw on filter change, the YouTube disclaimer modal); any other context a future AI model would need to stay visually consistent when adding pages.

- **`/docs/PATCHNOTES.md`**: running changelog. Each entry: semantic version (MAJOR.MINOR.PATCH), date (YYYY-MM-DD), and Added/Changed/Fixed/Removed sections, one line per change, past tense. Since no changelog exists yet at that point, this pass must create an initial entry summarizing the MVP build as `v0.1.0` (or nearest appropriate version) before adding the audit's own entry on top.

- **`/docs/PRD.md`**: the most comprehensive document, meant to make the *entire* project understandable without reading code. Beyond standard PRD sections (problem statement, target users/personas, goals, non-goals, user stories in "As a [user], I want to [action] so that [outcome]" form, MVP vs. Future feature list, constraints, assumptions, success criteria), it must also carry:
  - **Tenets**: 3–7 opinionated, prioritized product principles, each with a short title and 2–4 sentence rationale, ordered so higher tenets win conflicts. (Candidate material already implicit in this PRD's Goals §1 and the free-tooling framing - e.g. "zero paid dependencies over best-possible accuracy," "Claude as runtime, not just builder" - should be sharpened into true tenets during this pass, not just copied verbatim.)
  - **Roadmap**: current phase name/description, a milestone table (name, target/relative timeframe, status: Planned/In Progress/Complete/Blocked), feature breakdown per milestone, and explicitly deferred items with reasons (this §16 itself is an example of a properly-documented deferred item).
  - **Metrics**: north star metric, acquisition/engagement/retention/performance metrics, target values + timeframes, measurement method per metric, reporting cadence. (Note: this is a static informational site with no accounts/backend, so metrics here will mostly be traffic/engagement-via-static-analytics and technical health, not product usage funnels - define honestly for what this project actually is.)
  - **Runbook**: local setup from a fresh machine, exact build command + output location, step-by-step deploy process per environment (this project effectively has one environment: GitHub Pages), rollback procedure (git revert of `docs/` + re-push), environment configs, a table of common errors/likely cause/fix, and where to check for monitoring/build health (GitHub Pages build status, browser console for client JS errors).
  - **Technical Requirements**: system architecture description (static-generated, no server, Claude-driven analysis layer), full tech stack with versions, annotated folder structure, every data model (episode/prediction/check schemas from §7 of this PRD, kept current), "API design" reinterpreted as internal data flow (since this is browser-only/no backend - document how `app.js` reads embedded JSON and redraws charts), state management (client-side JS state only, no framework store), third-party integrations (YouTube captions endpoint, yt-dlp, GitHub Pages - what data flows where and how each is "authenticated," i.e. none require keys), performance requirements (page weight/load time targets given hand-rolled SVG and no framework), known technical debt with notes on the "correct" fix.
  - **Security**: authentication/authorization models (both effectively "none" for a static public site - state that explicitly rather than omitting the section), what data is stored/where (no user data collected; predictions/transcripts are public podcast content), confirmation no secrets are hardcoded plus a list of any env vars, third-party trust list (which external services see any data, and what - e.g. YouTube's caption endpoint sees only the video ID being requested), known attack surface (e.g. XSS risk if any user-supplied content were ever rendered - currently none exists, but document the assumption), dependency monitoring policy (how `requirements.txt`/`yt-dlp` versions get checked for vulnerabilities over time).
  - **Press Release** (Amazon/Working-Backwards style) - written as if launched: headline, subheadline, dateline, opening paragraph (who/what/when/where/why), problem statement from the customer's perspective, plain-language solution description, a realistic fictional customer quote, call to action, short company/project boilerplate. Plain language, no jargon, general audience.
  - **FAQ**: 10–25 realistic user questions covering: what the site is/who it's for, how to use it, cost (free), what data it uses (public YouTube captions + web search, no paid APIs), what it explicitly doesn't do (perfect speaker attribution, real-time updates), technical requirements/compatibility, how it differs from the original Cloudflare/Next.js version and from doing this manually, known v1 limitations, how to get help/report an issue, and a short "internal stakeholder" subsection (why this rewrite, what success looks like, what's next).

**After this pass:** add a dated entry to `PATCHNOTES.md` describing the audit itself (what was consolidated, moved, or rewritten and why), and update `PRD.md`'s Roadmap to reflect the audit as complete, plus document - inside `PRD.md` - how this documentation process should be repeated going forward (i.e., this same audit methodology becomes the standing process for keeping docs in sync with the codebase after future feature work, not a one-time event).

### 16.2 Writing-style sweep: em dashes and double dashes

**Status: complete as of 2026-08-25**, run in the same pass as §16.1 rather than in a separate post-launch window, per the user's explicit instruction. Fixed: 166 em dashes across `docs/PRD.md` and `docs/PATCHNOTES.md` (replaced with a colon after a bold/labeled term, or a spaced hyphen elsewhere), one `&mdash;` entity reference (in this section's own description of the rule, kept intentionally since it names the entity as an example), and prose double dashes in `config/hosts.yaml`, `prompts/extract_and_tag.md`, `prompts/validate.md`, and script docstrings/comments in `scripts/`. CLI flag tokens (`--limit`, `--force`, `--write-auto-sub`, etc.) were left untouched, since those are literal argument syntax, not punctuation. Left untouched, and flagged as an explicit exception rather than fixed: verbatim transcript `quote` fields and validation citation titles in `data/predictions/*.json` and `data/checks/*.json` - these are direct quotations of what a host/guest said or what an external source is titled, and altering their punctuation would misrepresent the source; a small number of Claude-authored `prediction` text fields in that same data still contain the pattern and are tracked as a known gap in §31 rather than silently rewritten mid-audit.

**Trigger (original, now satisfied):** same post-MVP window as §16.1; can be done in the same pass or immediately after.

**Objective:** audit every HTML page and every documentation file in the project for em dashes and double-dash punctuation, and replace them with contextually appropriate standard punctuation.

**What to search for (independently - a search for one form will not catch the others):**
1. The literal Unicode em dash character (-).
2. The HTML entity form (`&mdash;`).
3. Double dashes used as punctuation (`--`) - but **not** CSS custom properties, which legitimately use a leading double-dash (e.g. `--bg`, `--accent`, `--space-4`); those must be left untouched.

**Replacement rule (choose based on context, not a single default):**
- **Comma**: the most natural default in most cases; keeps the sentence flowing without drawing attention to the punctuation itself.
- **Colon**: when introducing a list, explanation, or elaboration after a complete clause.
- **Semicolon**: when joining two closely related independent clauses that could each stand alone.
- **Parentheses**: for asides/supplementary information that isn't central to the sentence.
- **Period**: when the cleanest fix is splitting into two sentences; shorter sentences are often clearer anyway.

**Deliverable:** after fixing every instance, add a **Writing Style** section to `/docs/PRD.md` (once relocated per §16.1) documenting this exact methodology - explicitly noting that em dashes appear in both literal-character and HTML-entity form, that both are prohibited project-wide, that double dashes as punctuation are likewise prohibited (with the CSS custom-property carve-out stated explicitly so it isn't mistakenly "fixed" in a future pass), and the five-way replacement decision rule above so future contributions (human or AI) follow the same standard going forward rather than reintroducing em dashes.

**Also required:** update `PATCHNOTES.md` with a dated entry describing this sweep (scope: all HTML + docs; what was found/fixed; the new standing rule), consistent with §16.1's documentation-currency standard.

### 16.3 Mobile-friendliness / responsive audit-and-fix pass

**Trigger:** same post-MVP window; logically follows §16.1–16.2 since it should be documented using whatever conventions those establish.

**Objective:** a full responsive audit and fix pass across every page/view the rewrite ships (home, episode list, episode detail, host page, about page), verified programmatically rather than by eyeballing screenshots.

**1. Audit scope - widths to check on every page:** 375px, 700px, 900px, 1023px (or this site's effective desktop breakpoint if different), 1150px, 1440px, 1920px. At each width, check for: horizontal page overflow (page wider than viewport); elements overflowing their own container without an intended scroll affordance; any wide toolbar/filter row/chart legend that doesn't wrap or reflow cleanly; modal sizing at narrow widths (the YouTube-link disclaimer modal); clipped or overlapping text/labels.

**2. Specific bug patterns to check for** (common, easy to introduce, easy to miss - especially relevant here since this rewrite hand-writes CSS/SVG instead of relying on Tailwind/Chart.js defaults):
- **`overflow` shorthand collision**: if any element sets `overflow-x: auto` and a bare `overflow: <value>` shorthand is also set (same rule or a later one), the shorthand silently resets both axes and cancels the x-axis setting. Grep for elements with both an explicit `overflow-x`/`overflow-y` and a bare `overflow`.
- **CSS Grid implicit min-width on bare `1fr` tracks**: a bare `1fr` grid track has an implicit `min-width: auto` (intrinsic content width, not zero). Wide content in a cell (a stat table, a long filter/button row) can force the whole grid - and page - wider than the viewport. Fix: `minmax(0, 1fr)` instead of bare `1fr`. Check this in **every** media query touching the same grid, since it's common to fix the desktop rule and have a mobile override silently reintroduce a bare `1fr`.
- **Flexbox children with default `min-width`/`min-height: auto`**: a flex item defaults to `min-size: auto`, which for large content (e.g. a scrollable chart/table wrapper inside a `flex: 1` column) resolves to "big enough for all content," not "shrink to available space" - causing overflow instead of internal scrolling. Fix: `min-width: 0` / `min-height: 0` on the flex item.
- **Redundant spacing with `gap` + `margin`**: if a flex/grid container already declares `gap`, don't also add `margin` on a child for the same spacing; they stack and double the gap. Check anything moved into a `gap`-based container after being styled for a different original layout.

**3. Verification methodology - do not rely on screenshots alone.** Headless Chrome enforces an effective minimum viewport (~485–500px) even when a smaller `--window-size` is requested, and screenshot pixel dimensions don't reliably match the actual layout viewport - screenshots below that width can look broken with zero real overflow, and can also miss genuine bugs at specific widths. Instead:
- Inject a small debug `<script>` into a scratch copy of the page printing `window.innerWidth`, `document.documentElement.scrollWidth`, `document.documentElement.clientWidth`, and `getBoundingClientRect()` for suspect elements.
- The reliable "is there page-level overflow" check is `scrollWidth === clientWidth`, not a visual read of a screenshot.
- For subtler layout bugs (uneven spacing between sibling elements, e.g. host scorecards or filter buttons), measure `getBoundingClientRect().left`/`.right` for every sibling and diff the gaps programmatically rather than eyeballing a zoomed screenshot.
- Test against a local copy served via `python -m http.server` (already this rewrite's stated local-preview method - see §11), not the live GitHub Pages site, so fixes are verified before shipping.

**4. Design decisions - ask, don't guess.** If fixing an overflow requires a real design choice (e.g. should the by-topic stacked bar chart's legend wrap, truncate, or scroll on narrow screens; should the episode list switch to a card layout below a breakpoint; should hidden filter options be recoverable via a menu), stop and ask which approach to use before implementing. Only proceed unprompted for pure CSS-correctness bugs with one obviously correct fix (the four patterns in §16.3.2).

**5. Regression safety.** Before and after each fix, reconfirm this project's zero-regression check still holds - e.g. a known-good episode/host page's data renders identically (same predictions, same counts, same chart values) before and after the CSS/layout change, since these are meant to be render-only changes that never touch the underlying JSON data or the generation logic in `generate_site.py`.

**6. Documentation.** After fixes are verified, add a dated `PATCHNOTES.md` entry describing what was found and fixed by root cause (e.g. "bare `1fr` grid track in the host-scorecard grid caused horizontal overflow below 1023px when a stacked bar chart's legend exceeded the cell's intrinsic width"), not a vague "fixed mobile bugs" line, and update the Roadmap section of `PRD.md` if this pass changes what's considered shipped/complete. Follow whatever documentation structure §16.1–16.2 have already established by that point rather than introducing a new format.

**Process order for this whole pass:** audit first and report findings across all breakpoints → ask about any open design-decision questions from step 4 → implement and verify fixes → document per step 6. Do not implement fixes before the audit-and-report step, and do not skip the "ask" step for anything beyond pure bug fixes.

## 17. Planned Feature: Annual Predictions Episode Filter (Roadmap, Post-MVP)

**Trigger:** post-MVP, once the core pipeline (§6) and site (§9) are working end-to-end on real data. Listed in Phase 6 (§13) but detailed fully here since it's a real planned feature, not just a hardening pass.

**Context:** the All-In hosts periodically record a dedicated "predictions episode" (typically an annual, start-of-year special) where each host runs through a deliberate, structured list of predictions for the coming year - distinct in kind from the incidental, off-the-cuff predictions made during normal news-discussion episodes. These are the highest-density, most-intentional predictions in the archive and deserve to be independently browsable, not just findable by scrolling through regular episodes.

**Goal:** let a site visitor filter the whole site (or view a dedicated page) showing *only* predictions that came from these annual predictions episodes, separate from everything else.

**Data model change:**
- Add an `episode_type` field to `data/episodes.json` - `"regular"` (default) or `"annual_predictions"`.
- Detection is two-layered, mirroring the manual-override pattern already used for YouTube matching (§6.1):
  1. **Automatic heuristic** during episode discovery (§6.1): match episode titles/descriptions against a pattern (e.g., containing "predictions" alongside a year, or matching the show's known recurring naming convention for these specials) to flag likely candidates.
  2. **Manual override list**: `config/annual_prediction_episodes.json`, a simple array of `episode_id`s - since heuristic title-matching is expected to miss or mis-tag some episodes (naming isn't perfectly consistent year to year) and this is a small, stable, human-curatable list worth just verifying by hand once discovered (cross-referenced against allin.com/episodes, consistent with §6.1's canonical-ordering practice).
- `data/predictions/<episode_id>.json` doesn't need its own change - a prediction's episode-level type is looked up via `episode_id` at site-generation time, keeping the "annual" flag a property of the episode, not duplicated onto every prediction.

**Site feature:**
- A dedicated page, `/predictions/annual.html`, listing every prediction sourced from `episode_type: annual_predictions` episodes, grouped by year and then by host - this is the primary new view.
- A filter toggle (same interaction pattern as the existing "Resolved only" checkbox and topic-tag dropdown in `HostCharts`-equivalent §9.3 charts) on the home page and host pages: "Annual predictions only," which recomputes the on-page chart stats client-side using the same embedded-JSON-plus-vanilla-JS-redraw approach already specified for topic/year filtering (§9.3) - no new architecture needed, just another filter dimension threaded through the existing stats-recompute code path.
- A small visual badge on prediction cards (§9.5-style, ports the original's tag-badge visual language) indicating a prediction came from an annual predictions episode, visible wherever that prediction appears (episode page, host page, home page previews).

**Why this belongs in the roadmap and not v1:** it depends on the core pipeline and site already working end-to-end with real predictions in hand - there's nothing to filter until predictions exist, and doing the episode-type classification well benefits from having already built the manual-override pattern once for YouTube matching (§6.1), so this is naturally sequenced after the MVP proves out.

## 18. Tenets

Ordered by priority; when two conflict, the higher one wins.

1. **Free tooling beats maximum accuracy.** Every architectural choice in this rewrite (captions instead of paid ASR, contextual attribution instead of voice embeddings, Claude instead of a billed API) trades some precision for zero ongoing cost. When a future decision pits "more accurate" against "costs money to run," free wins unless the accuracy loss is severe enough to make the site actively misleading (see G7/G9 and the validation gate).
2. **Claude does the thinking, always.** No step in this pipeline ever calls a third-party model API (OpenAI, xAI, or otherwise). If a future feature seems to need "a smarter model," the answer is a better prompt or a smarter use of Claude's existing tools (WebSearch, WebFetch), not a new SDK dependency. This is non-negotiable, not a cost tradeoff: it's the entire premise of "ran/updated entirely in Claude."
3. **Show your confidence, don't fake certainty.** Every attributed prediction carries a `speaker_confidence`, every validated one carries cited sources, and low-confidence data stays visible (on episode pages) rather than silently dropped, even though it's excluded from scorecards. When a design choice would hide uncertainty to make the UI look cleaner, uncertainty wins.
4. **Breadth before depth, in that order.** When processing the archive, cover more episodes with lighter validation before exhaustively validating fewer episodes (§13 Phase 4's two-sweep design: extract everything, then validate everything, never both at once per episode). A half-covered archive with thin validation beats a fully-validated tenth of the archive, because the product's core promise is "every prediction," not "every prediction, perfectly checked, eventually."
5. **Every voice counts, but hosts anchor the site.** Guests get real scorecards (G8): this project doesn't pretend only the four permanent hosts make predictions worth tracking. But navigation, defaults, and the home page are built around the four hosts first; guests are discoverable, not equally prominent, because a guest's one-episode sample size is a fundamentally different kind of data than a host's running record.

## 19. Roadmap

**Current phase:** live MVP, post-launch hardening and archive maintenance, as of 2026-08-25. The site is deployed and publicly reachable; the remaining roadmap items below are ongoing improvements against the live site, not pre-launch gates. **As of 2026-08-27 (Batch 11), the 47-episode unprocessed backlog is fully cleared** (411/412 tracked episodes have predictions extracted; only Ray Dalio's permanently-unresolvable episode is excluded), which satisfies the "after the full ingest-and-validation sweep completes" trigger for §36/§36.1-36.5 below. **As of 2026-08-31 (Batch 12), the ongoing incremental process now also covers newly-published episodes** (413 tracked, 412 with predictions extracted). **Also on 2026-08-31, the last remaining "permanently unresolvable" episode (Ray Dalio's "Our System Is in Jeopardy") was recovered** by locating its retitled YouTube upload manually, closing the last gap: 413/413 tracked episodes now have predictions extracted.

**Sequencing change (2026-08-25):** the user made the explicit call to ship an MVP to production *before* the full-archive validation sweep (and the remaining hardening/feature passes) finish, rather than waiting for parity/QA confidence as originally planned. The full site replacement and GitHub Pages deploy moved up to right after the extraction sweep and the parity pass, and everything that used to gate deployment (validation completion, §16.2/§16.3, §17, `video_id` resolution) is now ongoing post-launch work against the live site. That restructure and deploy, and the pre-launch parity pass, are now complete (see the table below); this documentation audit and the writing-style sweep were pulled forward into the same 2026-08-25 session rather than waiting for the originally-planned post-launch window.

| Milestone | Timeframe | Status |
|---|---|---|
| Phase 0-3: MVP build (scaffolding, mechanical pipeline, sample extraction/validation, site generator) | 2026-08-04 | Complete |
| Repo restructure (v1): site generated to the repo root, `docs/` reserved for documentation (§8.1) | 2026-08-04 | Complete |
| §16.1 documentation audit & consolidation (this pass) | 2026-08-04 | Complete (partial: see §16.1 status note; will need a follow-up pass once more of the archive is processed) |
| Phase 4: extraction sweep against currently-available transcripts, manual/no-agent, oldest-first (§13) | 2026-08-04 | Complete - 357/404 episodes have a predictions file; all 128/128 chunked/captioned episodes are done. Remaining 47 episodes are blocked on captions (45 need `video_id` resolution, 2 have a `video_id` but no fetchable captions), not extraction work |
| Validation sweep, first batch (E010-E020, 155 predictions) | 2026-08-25 | Complete - 32/357 episodes validated after this batch |
| Validation sweep, second batch (20 episodes, fewest-predictions-first, 14 predictions checked) | 2026-08-25 | Complete - 52/357 episodes now validated overall |
| Validation sweep, third batch (20 episodes, fewest-predictions-first, 41 predictions checked) | 2026-08-26 | Complete - 72/357 episodes now validated overall |
| Validation sweep, fourth batch (20 episodes, fewest-predictions-first, 67 predictions checked; first of five 20-episode batches toward a 100-episode sweep) | 2026-08-26 | Complete - 92/357 episodes now validated overall |
| Validation sweep, fifth batch (20 episodes, fewest-predictions-first, 77 predictions checked; second of five 20-episode batches toward a 100-episode sweep) | 2026-08-26 | Complete - 112/357 episodes now validated overall |
| Validation sweep, sixth batch (20 episodes, fewest-predictions-first, 116 predictions checked; third of five 20-episode batches toward a 100-episode sweep) | 2026-08-26 | Complete - 132/357 episodes now validated overall |
| Validation sweep, seventh batch (20 episodes, fewest-predictions-first recomputed fresh against the live manifest, 110 predictions checked; fourth of five 20-episode batches toward a 100-episode sweep) | 2026-08-27 | Complete - 152/357 episodes now validated overall |
| Validation sweep, eighth batch (20 episodes, fewest-predictions-first recomputed fresh against the live manifest, 144 predictions checked; fifth and final of five 20-episode batches toward the 100-episode sweep) | 2026-08-27 | Complete - 172/357 episodes now validated overall; the 100-episode validation request is fully complete |
| Validation sweep, ninth batch (20 episodes, fewest-predictions-first recomputed fresh against the live manifest, 157 predictions checked; first of four additional 20-episode batches requested beyond the completed 100-episode sweep) | 2026-08-27 | Complete - 192/357 episodes now validated overall |
| Validation sweep, tenth batch (20 episodes, fewest-predictions-first recomputed fresh against the live manifest, 165 predictions checked; second of four additional 20-episode batches requested beyond the completed 100-episode sweep) | 2026-08-27 | Complete - 212/357 episodes now validated overall |
| Validation sweep, eleventh batch (20 episodes, fewest-predictions-first recomputed fresh against the live manifest, 195 predictions checked; third of four additional 20-episode batches requested beyond the completed 100-episode sweep) | 2026-08-27 | Complete - 233/357 episodes now validated overall |
| Validation sweep, twelfth batch (20 episodes, fewest-predictions-first recomputed fresh against the live manifest, 210 predictions checked; fourth and final of four additional 20-episode batches requested beyond the completed 100-episode sweep) | 2026-08-27 | Complete - 253/357 episodes now validated overall; the four-additional-batch request is fully complete |
| Validation sweep, thirteenth batch (20 episodes, fewest-predictions-first recomputed fresh against the live manifest, 207 predictions checked; first of three additional 20-episode batches requested beyond the just-completed 80-episode sweep) | 2026-08-27 | Complete - 274/357 episodes now validated overall |
| Validation sweep, fourteenth batch (20 episodes, fewest-predictions-first recomputed fresh against the live manifest, 227 predictions checked; second of three additional 20-episode batches requested beyond the just-completed thirteenth-batch validation) | 2026-08-27 | Complete - 294/357 episodes now validated overall |
| Validation sweep, fifteenth batch (20 episodes, fewest-predictions-first recomputed fresh against the live manifest, 261 predictions checked; third and final of three additional 20-episode batches requested beyond the just-completed fourteenth-batch validation) | 2026-08-27 | Complete - 314/357 episodes now validated overall; the three-additional-batch request is fully complete |
| Validation sweep, batch size reduced to 5 episodes (temporary test, per user request); Batch J, first of two 5-episode test batches (E145, E140, E128, E079, E067, 75 predictions checked) | 2026-08-27 | Complete - 319/357 episodes now validated overall (312/402 in full-pipeline terms including the 47-episode unprocessed backlog); second 5-episode test batch (Batch K) to follow |
| Validation sweep, Batch K, second of two 5-episode test batches (E052, E043, ai-sovereignty-wars-palantir-nvidia-deal-scotus-birthright-ruling-newsom-s-ca-budget-lie, E155, E153, 78 predictions checked) | 2026-08-27 | Complete - 324/357 episodes now validated overall (317/402 in full-pipeline terms); the two-batch 5-episode test is complete, 33 episodes remain in the validation-eligible pool |
| Validation sweep, Batch L, first of five additional 5-episode batches requested beyond the two-batch test (E143, E121, E101, E095, E074, 80 predictions checked) | 2026-08-27 | Complete - 329/357 episodes now validated overall (322/402 in full-pipeline terms) |
| Validation sweep, Batch M, second of five additional 5-episode batches (E068, E057, E033, E024, inside-the-white-house-tech-dinner-..., 81 predictions checked) | 2026-08-27 | Complete - 334/357 episodes now validated overall (327/402 in full-pipeline terms) |
| Validation sweep, Batch N, third of five additional 5-episode batches (trump-vs-powell-..., markets-turn-trump-..., dueling-presidential-interviews-..., E119, E080, 85 predictions checked) | 2026-08-27 | Complete - 339/357 episodes now validated overall (332/402 in full-pipeline terms) |
| Validation sweep, Batch O, fourth of five additional 5-episode batches (E072, E059, E038, presidential-debate-reaction-..., E151, 87 predictions checked) | 2026-08-27 | Complete - 344/357 episodes now validated overall (337/402 in full-pipeline terms) |
| Validation sweep, Batch P, fifth and final of five additional 5-episode batches (E106, E084, gpt-4o-launches-glue-demo-..., E171, E156, 93 predictions checked) | 2026-08-27 | Complete - 349/357 episodes now validated overall (342/402 in full-pipeline terms); the "5 more batches" request is fully complete, 8 episodes remain in the validation-eligible pool |
| Validation sweep, Batch Q, final batch closing out the entire validation-eligible pool (trump-wins-how-it-happened-..., trump-verdict-covid-cover-up-..., E132, E114, E051, ipos-and-spacs-are-back-..., E103, E045, 180 predictions checked) | 2026-08-27 | Complete - 357/357 episodes now validated overall (100% of validation-eligible pool; 350/402 in full-pipeline terms). No episodes remain in the validation-eligible pool; remaining work is the 47-episode unprocessed backlog |
| Documented the incremental backlog/new-episode process (§13 Phase 4): the original two-sweep extract-then-validate design is now scoped explicitly to the completed initial full-archive load; a new combined extract+validate-in-one-pass process, batches of 5 episodes at a time, is the standing procedure for the 47-episode unprocessed backlog and all future newly-published episodes going forward | 2026-08-27 | Complete - documentation only, no pipeline work yet. Next: run the first 5-episode test batch against the unprocessed backlog |
| Incremental process, Batch 1 of 5 test batches against the 47-episode unprocessed backlog (ais-mp-materials-ceo-james-litinsky-..., ais-the-lanby-s-tandice-urban-..., jonathan-haidt-the-all-in-interview, john-mearsheimer-and-jeffrey-sachs-all-in-summit-2024, senator-ted-cruz-the-all-in-inauguration-series; 14 predictions extracted and validated) | 2026-08-27 | Complete - first backlog batch fully run end-to-end (video_id resolution -> transcript -> chunk -> extract -> validate); 42 backlog episodes remain, 4 more test batches planned |
| Incremental process, Batch 2 of 5 test batches against the 47-episode unprocessed backlog (antonio-gracias-doge-updates-voter-fraud-arrests-finding-big-balls-all-in-live-from-miami, ray-dalio-the-all-in-interview, scott-bessent-all-in-dc, howard-lutnick-all-in-dc, inauguration-interviews-trump-s-talent-democratic-rebrand-more-with-house-whip-emmer-reps-swalwell-khanna; 10 predictions extracted and validated) | 2026-08-27 | Complete - second backlog batch fully run end-to-end; 37 backlog episodes remain, 3 more test batches planned |
| Incremental process, Batch 3 of 5 test batches against the 47-episode unprocessed backlog (miami-mayor-francis-suarez-..., energy-secretary-chris-wright-on-the-future-of-american-energy-all-in-summit-2025, the-new-era-of-the-stock-market-with-nasdaq-ceo-adena-friedman-all-in-summit-2025, how-to-save-america-mark-cuban-and-tucker-carlson-debate-all-in-summit-2025, winning-the-ai-race-part-1-michael-kratsios-kelly-loeffler-chris-power-shyam-sankar-paul-buchheit-jake-loosararian; 4 predictions extracted and validated) | 2026-08-27 | Complete - third backlog batch fully run end-to-end; 32 backlog episodes remain, 2 more test batches planned |
| Incremental process, Batch 4 of 5 test batches against the 47-episode unprocessed backlog (google-deepmind-ceo-demis-hassabis-on-ai-creativity-and-a-golden-age-of-science-all-in-summit, ro-khanna-on-crime-censorship-congress-fixing-what-s-broken-in-america, joe-tsai-on-us-china-rivalry-ai-s-future-owning-the-nets-liberty-caitlin-clark-s-major-impact, bryan-johnson-the-1-longevity-secret-you-can-start-doing-today, how-orlando-bravo-built-one-of-the-most-successful-firms-in-private-equity; 3 predictions extracted and validated) | 2026-08-27 | Complete - fourth backlog batch fully run end-to-end (video_ids resolved via yt-dlp channel search after direct WebSearch failed to locate them); 27 backlog episodes remain, 1 more test batch planned |
| Incremental process, Batch 5 of 5 test batches against the 47-episode unprocessed backlog (nobel-prize-in-physics-winner-john-martinis-on-the-state-of-quantum, nobel-peace-prize-winner-mar-a-corina-machado-on-defeating-maduro-socialism-freeing-venezuela, triple-h-on-wwe-s-evolution-the-rise-of-the-antihero-and-the-psychology-of-stardom, ari-emanuel-on-the-future-of-entertainment-hollywood-ai-creator-economy-youtube-vs-netflix, molly-s-game-uncensored-the-truth-behind-the-world-s-most-infamous-poker-game; 2 predictions extracted and validated) | 2026-08-27 | Complete - fifth and final backlog test batch fully run end-to-end (video_ids resolved via yt-dlp channel search); the "5 batches as a test" request is fully complete (25 episodes processed, 22 backlog episodes remain in the full 402-episode pipeline). Machado's Maduro-ouster prediction came back right (Maduro captured/arrested by the U.S. on January 3, 2026); Martinis's 8-10-year quantum-scaling prediction was marked inconclusive (timeframe far from elapsed) |
| Incremental process, Batch 6 against the 47-episode unprocessed backlog, first batch beyond the completed "5 batches as a test" run, now proceeding one batch at a time per user request (bernie-sanders-stop-all-ai-china-s-euv-breakthrough-inflation-down-golden-age-in-2026, microsoft-ceo-satya-nadella-on-ai-s-business-revolution-what-happens-to-saas-openai-and-microsoft-live-from-davos, under-secretary-of-state-sarah-b-rogers-on-dismantling-the-censorship-industrial-complex, cz-s-untold-story-the-rise-fall-and-redemption-of-binance-s-founder, inside-the-iran-war-and-the-pentagon-s-feud-with-anthropic-with-under-secretary-of-war-emil-michael; 6 predictions extracted and validated) | 2026-08-27 | Complete - sixth backlog batch fully run end-to-end (Ray Dalio's "Our System Is in Jeopardy" episode was unresolvable on the official All-In YouTube channel and was substituted with the next-oldest backlog episode). Chamath's 90-day Google co-work-competitor prediction came back right; Friedberg's US-China "grand bargain" prediction came back wrong (spring 2026 Trump-Xi summit produced only modest trade outcomes); the remaining 4 predictions (Codex-closes-the-gap, Anthropic $1.5T valuation, Huawei/EUV 2026-2027, California billionaire-tax impact) were marked inconclusive. 39/402 backlog episodes processed overall, 21 remain |
| Data-quality fix: Batch 6 used display-name-style `who` slugs (`chamath-palihapitiya`, `david-friedberg`) instead of the canonical `config/hosts.yaml` slugs, fabricating two duplicate host pages; also hardened `generate_site.py`'s validator so `role: "host"` now requires an exact `config/hosts.yaml` slug match (hard build failure), closing the gap the prior near-miss/typo-only check left open - this is the same class of bug as the 2026-08-25 post-deploy `freeberg` typo fix (line above §"Post-deploy data-quality fix"), now caught by tooling instead of manual review | 2026-08-27 | Complete - fixed in commit `5ac4fd1`, verified the hardened validator catches the exact bug pattern |
| Incremental process, Batch 7 against the unprocessed backlog (graham-allison-on-the-global-realignment-iran-china-israel-greenland, rewriting-the-rules-the-sec-cftc-on-crypto-ipos-the-future-of-american-markets, travis-kalanick-michael-dell-live-from-austin-texas, john-fetterman-the-rogue-democrat-who-broke-party-ranks, jensen-huang-live-nvidia-s-future-physical-ai-rise-of-the-agent-inference-explosion-ai-pr-crisis; 7 predictions extracted, 4 validated so far) | 2026-08-27 | Complete - seventh backlog batch fully run end-to-end (2 video_ids found via WebSearch, 3 via yt-dlp channel search matching upload date against RSS publish date since YouTube's public titles differ from the RSS feed titles). Michael Dell's ~100%-quarterly-infrastructure-growth guidance came back right; Graham Allison's Iran-war-over-before-China-trip and Brad Gerstner's 10-million-Trump-accounts-by-July-4 predictions both came back wrong; Allison's Taiwan-invasion-probability prediction and all 3 of Jensen Huang's multi-year forecasts were marked inconclusive. 392/412 tracked episodes now have predictions extracted, 20 remain |
| Incremental process, Batch 8 against the unprocessed backlog (anthropic-s-generational-run-openai-panics-ai-moats-meta-loses-lawsuits, the-companies-changing-warfare-forever-palantir-anduril-execs-on-drones-ai-the-future-of-war, charles-chase-koch-on-how-they-quietly-built-a-150b-empire, bill-ackman-investment-strategy-what-the-market-is-missing-how-ai-breaks-businesses, thomas-laffont-the-4t-ai-ipo-wave-2026-s-unicorn-economy-and-the-10x-paradox; 5 predictions extracted and validated) | 2026-08-27 | Complete - eighth backlog batch fully run end-to-end (all 5 video_ids resolved via yt-dlp channel search since YouTube's public titles differ from the RSS feed titles, each verified against the official channel_id and the RSS `published_iso` upload date). Both of Jason's ChatGPT predictions (1-billion-users-within-1-2-months, consumer-market-share-well-under-50%) came back right; Thomas Laffont's AI-revenue-doubling-to-2027 and OpenAI/Anthropic-vs-AWS/Microsoft predictions and Bill Ackman's 22-year Pershing Square AUM forecast were marked inconclusive. This "do 2 batches now" request is now fully complete (Batches 7 and 8); 397/412 tracked episodes now have predictions extracted, 15 remain |
| Incremental process, Batch 9 against the unprocessed backlog (inside-the-private-stock-market-boom-spacex-anthropic-openai-the-rise-of-secondaries, nikesh-arora-mythos-is-real-analytical-saas-is-dead-and-google-can-be-a-10t-company, dan-dreyfus-america-s-critical-minerals-crisis-is-here, nate-silver-predicts-democrats-take-the-house-newsom-is-fading-aoc-might-win-it-all-in-2028, more-trillion-dollar-ipos-anthropic-3t-zuck-s-price-war-china-ends-open-source-trump-accounts; 17 predictions extracted and validated) | 2026-08-27 | Complete - ninth backlog batch fully run end-to-end (all 5 video_ids resolved via yt-dlp channel search). All 17 predictions marked inconclusive (election forecasts and multi-year IPO/valuation/policy targets, none of which have elapsed yet). 402/412 tracked episodes now have predictions extracted, 10 remain |
| Incremental process, Batch 10 against the unprocessed backlog (saronic-founders-autonomous-warships-china-s-230x-advantage-swarms-of-robot-ships, the-1-hour-worker-four-robotics-ceos-on-humanoids-at-home-china-s-threat-and-the-end-of-dangerous-jobs, google-s-ai-brain-drain-spacex-s-huge-quarter-airtable-s-90-collapse-us-data-fuels-china-ai, rahm-emanuel-trump-s-foreign-policy-china-europe-s-decline-immigration-dsa-vs-democrats, anthropic-s-2t-ipo-zuck-s-ai-manifesto-nvidia-s-500b-ai-bet-grok-s-comeback; 14 predictions extracted and validated) | 2026-08-27 | Complete - tenth backlog batch fully run end-to-end. Gavin Baker's "Grok 4.7 in a few weeks" prediction came back wrong (delayed to September per multiple reports as of August 23, 2026); the remaining 13 predictions (SpaceX/Starlink, Anthropic IPO/ARR, robotics-shipping, China-fleet-size forecasts) were marked inconclusive. 407/412 tracked episodes now have predictions extracted, 5 remain |
| Incremental process, Batch 11, the final batch against the 47-episode unprocessed backlog (flock-ceo-garrett-langley-on-controversy-surveillance-state-claims-and-privacy-vs-safety, michael-kratsios-trump-s-science-agenda-anti-science-claims-fauci-s-damage-dei-china, eric-weinstein-the-state-of-american-science-breakthrough-coverups-and-the-danger-of-physics, dario-defends-himself-datacenter-panic-ai-doomer-trap-senate-toss-up; 8 predictions extracted and validated) | 2026-08-27 | Complete - eleventh and final backlog batch fully run end-to-end. All 8 predictions marked inconclusive (government policy targets dated 2028-2035 and 2026/2028 election forecasts). **All 14 non-Ray-Dalio backlog episodes are now fully processed; 411/412 tracked episodes have predictions extracted.** Ray Dalio's "Our System Is in Jeopardy" episode remains permanently unresolvable on the official All-In YouTube channel and is excluded from the pipeline |
| **Approved development plan (post-backlog), sequenced shortest-to-longest with two dependency-driven reorderings:** (1) host/guest name-accuracy audit; (2) per-host verdict-count breakdown, §17 annual filter, home page accuracy/leaderboard stat, "recently settled" feed, §34 league table, unified "Full Ledger" browse page - batched together since all read off the same `speakers`/`episodes` data already computed in `generate_site.py`; (3) curated "Big Ones" high-impact section; (4) prediction expected-resolution-date tracking; (5) sitewide search; (6) §16.3 mobile-responsive audit; (7) §36.1-36.5 visual/UX re-audit, the largest item, done last so redesign work happens once against the final page set rather than twice | Post-launch, sequencing agreed 2026-08-27 | **Approved by user 2026-08-27** ("yes and document that i have approved this development plan to do list"). Estimated ~9.5-13 hrs total across all items excluding the deferred §35 listener-voting feature. Work starts now with item (1) |
| Host/guest name-accuracy audit - verify every `who` slug across `data/predictions/` maps to a real, correctly spelled "First Name Last Name" (permanent hosts already use their canonical short slugs per `config/hosts.yaml`; this targets guest slugs and display names, which should never be a bare first name, a bare last name, a nickname, or a misspelling) | Post-launch, after the incremental-process backlog is complete (satisfied 2026-08-27) | **Complete 2026-08-27** - first item of the approved development plan above. Found and fixed 3 classes of bug across 182 individual prediction records in ~65 episode files: (1) **underscore-formatted slugs** (`ben_shapiro`, `brad_gerstner`, `jared_kushner`, `nassim_taleb`, `reid_hoffman`, `rfk_jr`) normalized to hyphens; (2) **duplicate-identity slugs** that were silently fragmenting one person's scorecard across 2-3 different pages - merged 15 identities (e.g. `brad`/`brad-gerstner`/`brad_gerstner` -> `brad-gerstner`; `elon`/`musk`/`elon-musk` -> `elon-musk`; `gavin`/`gavin-baker` -> `gavin-baker`; `cuban`/`mark-cuban` -> `mark-cuban`; `trump`/`donald-trump` -> `donald-trump`; `kennedy`/`rfk_jr` -> `robert-f-kennedy-jr`; `keith`/`keith-rabois`, `jared`/`jared_kushner`, `antonio`/`antonio-gracias`, `joe` x2 episodes/`thomas` -> their existing full-slug counterparts); (3) **bare-first-name-only slugs with no counterpart** identified via episode-title/WebSearch research and renamed to full First-Last slugs (26 people, e.g. `balaji`->`balaji-srinivasan`, `sergey`->`sergey-brin`, `tucker`->`tucker-carlson`, `vivek`->`vivek-ramaswamy`, `oz`->`mehmet-oz`, `reza`->`reza-pahlavi`, `shervin`->`shervin-pishevar`, full list in commit). Also caught and fixed 2 real data-quality bugs of the same class as the 2026-08-25 freeberg-typo incident: E088's `who: "david"` was actually a Friedberg quote mislabeled as a guest (fixed to `friedberg`/`role: host`), and the trump-vs-powell episode had the exact same statement extracted twice under two different speaker labels (`other-00:58:05` and `bo-00:58:16`) - removed the duplicate and renamed the survivor to `bo-hines`, plus renamed two more `other`-labeled predictions in that episode to the correctly-identified guest `bill-hagerty`. Site rebuilt clean (132 host/guest pages, down from 145 stale/duplicate pages, zero validator errors). **2 records remain unresolved** and are intentionally left as-is rather than guessed: 3 predictions in E129 (`who: "david"`) and 3 in E114/epstein-files-flop (`who: "other"`) are confirmed host-only episodes with no named guest, but the transcripts for these older-batch episodes were never retained, so there's no way to confirm which of the two hosts named David (Sacks or Friedberg) is speaking, or which host "other" refers to, without re-fetching those transcripts - flagged for a future pass if/when a transcript re-fetch is done |
| Batched cheap items (item 2 of the approved development plan): per-host verdict-count breakdown, §17 annual filter, home page accuracy/leaderboard stat, "recently settled" feed, §34 league table, unified "Full Ledger" browse page | Post-launch, second item of the approved development plan above | **Complete 2026-08-27** - all six read off the same `speakers`/`episodes` data already computed by `build_speaker_index()`, so no new data-model work was needed. New home page headline stat (sitewide accuracy %, computed by summing every speaker's qualifying-prediction bucket) and a "Recently Settled" section (8 most-recently-resolved qualifying predictions, deep-linked to the source episode). New `leaderboard.html`: a single ranked table combining the accuracy leaderboard, host-vs-guest §34 comparison, and full verdict-count breakdown (not just right/wrong) for all 132 speakers, with a small-sample flag for guests under 3 predictions. New `ledger.html` + `static/ledger.json`: a client-side searchable/filterable browse of all 3453 qualifying predictions (text search, year, topic, result filters; 50-at-a-time "load more" pager). Added a year-filter dropdown to the Episodes index page, reusing the existing home page filter JS pattern. Nav updated to `Episodes \| Leaderboard \| Ledger \| Hosts \| About`. Site rebuilt clean, zero validator errors |
| Post-batch polish, user-requested 2026-08-27: (a) percentages on every accuracy breakdown; (b) leaderboard sortable by any column, default changed from accuracy % to sheer right-prediction count; (c) fixed the topic filter dropdown (incomplete on the Ledger, mis-capitalized everywhere) and consolidated the tag taxonomy | Post-launch, ad hoc follow-up to item 2 above | **Complete 2026-08-27** - (a) new `pct_bucket()` helper adds "N (P%)" everywhere a verdict count is shown, mirrored client-side. (b) `leaderboard.html` columns are now click-to-sort (`setupLeaderboardSort()` in `app.js`), defaulting to `stats.right` descending instead of `accuracy_pct` descending. (c) found two real bugs: the home page's `topics` list was reused for the Ledger's filter even though it was scoped to host-only predictions, silently hiding ~40 guest-only tags from the Ledger (fixed by giving the Ledger its own sitewide `all_topics` list); and `\|capitalize` mangled multi-word/acronym tags ("ai"->"Ai", "spacex"->"Spacex") (fixed with a new `tag_display()`/`tagDisplay()` filter, kept in sync between Python and JS). Also consolidated the tag taxonomy from 72 tags down to 30 general themes per user request (no individual company/person names as tags) - retagged 49 predictions across 16 episode files, merging companies/products into their domain (anthropic/openai/xai/grok/meta->ai, spacex/starlink->space, waymo->autonomous-vehicles), dropping person names (zuckerberg, elon-musk, aoc), merging single-material tags into "commodities", merging narrow subtopics into their nearest general theme, and collapsing year-specific election tags into one "elections" tag (year is separately filterable via the Ledger's Year dropdown). Verified every merge against actual prediction text; no prediction left with an empty tag list. Site rebuilt clean, zero validator errors |
| Tag rollup pass 2, user-requested 2026-08-27: "categories with less than 20 overall predictions should be rolled up into another one" | Post-launch, direct follow-up to the row above | **Complete 2026-08-27** - retagged 47 predictions across 8 episode files with straight renames (no data loss): `autonomous-vehicles`/`open-source`/`robotics`->`tech`; `business`/`energy`/`macro`/`manufacturing`->`economy`; `policy`->`government`; `commodities`/`finance`/`ipo`/`revenue`/`valuation`->`markets`; `elections`/`midterms`->`politics`; `china`/`defense`/`space`->`geopolitics`. Taxonomy is now 12 broad tags, every one with at least 20 predictions (`economy` 1211, `politics` 1171, `tech` 843, `government` 823, `markets` 813, `ai` 635, `venture` 280, `health` 272, `conflict` 184, `science` 171, `climate` 123, `geopolitics` 20). Home page and Full Ledger topic dropdowns now show the identical 12-tag list. Site rebuilt clean, zero validator errors |
| Incremental process, Batch 12, first new-episode sweep after the backlog was cleared (nvidia-s-historic-quarter-saas-comeback-bessent-vs-druck-america-s-debt-crisis-cancer-vaccine, published 2026-08-29; 1 prediction extracted and validated) | 2026-08-31 | Complete - RSS/YouTube sweep found exactly one new episode since Batch 11. Fetched transcript and 7 chunks, read the full episode end-to-end (Nvidia/Salesforce SaaS-apocalypse debate, Bessent-vs-Druckenmiller bond market/deficit debate, Druckenmiller AI-op-ed ethics debate, CIA-Moscow/Ukraine commentary, Moderna mRNA cancer-vaccine science corner). Extracted Chamath's dated Social Security insolvency / state-bankruptcy-and-restructuring forecast for "around 2030 to 2032" (the only sufficiently falsifiable, dated host prediction in the episode - Sacks's undated "I don't think Ukraine's going to come out on top" was judged too vague/undated to extract, consistent with prior batches' bar). Marked `inconclusive` since the 2030-2032 window hasn't started. 413 tracked episodes, 412 with predictions extracted (only Ray Dalio's episode remains permanently excluded) |
| Recovery: Ray Dalio's "Our System Is in Jeopardy - Debt, AI & the Cycle That Destroyed Rome" episode, previously marked permanently unresolvable on the official YouTube channel | 2026-08-31 | Complete - user asked directly whether two candidate YouTube URLs matched; the first (`u-vMNzHgSHI`, public title "Ray Dalio: 'AI Is Eating Everything - and It Might Eat Itself'", published 2026-03-03) turned out to be this exact episode under a different YouTube title - confirmed via matching chapter markers and description text word-for-word. The earlier yt-dlp channel-search resolution had failed because it was searching against the RSS title, not this retitled one. Added the mapping to `config/youtube_urls_override.json`, fetched the transcript and 3 chunks, extracted 1 falsifiable dated prediction (Ray Dalio: Democrats will likely take the House in the 2026 midterms), validated `inconclusive` (election hasn't happened yet; current polling favors Democrats). **413/413 tracked episodes now have predictions extracted - zero gaps remain in the pipeline** |
| Manifest interpretability fix - `data/manifest.json`'s `captions_fetched`/`chunked` flags were being misread as stale/buggy when they're actually accurate for 229 legacy episodes whose raw transcript/chunk files were never retained | Ranked #1 by effort in a 6-item remaining-roadmap prioritization, user-requested 2026-08-31 | **Complete 2026-08-31** - confirmed `build_manifest.py` already recomputes every flag from live file existence on each run (nothing cached/stale in the code itself); the confusion was in interpreting `false` flags on episodes that are actually fully processed. Added a `legacy_no_transcript` status count and a `notes` field explaining the semantics directly in the generated `manifest.json`, so the distinction no longer depends on tribal knowledge. No behavior change, no site rebuild impact |
| Prediction expected-resolution-date tracking - add an expected-resolution date to each prediction check (particularly `inconclusive` verdicts whose timeframe hasn't elapsed yet or whose premise hasn't been met), so a future validation pass can automatically flag predictions past their expected date for recheck; if still unresolved at recheck time, the date rolls forward to a new expectation rather than being left stale indefinitely | Ranked #2 by effort in the same prioritization, user-requested 2026-08-31 | **Schema + tooling complete 2026-08-31** - added a `resolves_by` ISO-date field to the check schema and `scripts/list_due_rechecks.py` (scans `data/checks/*.json` for `inconclusive` checks whose `resolves_by` has passed, supports `--as-of` for testing). Applied going forward to all new checks (today's 2 new predictions) plus a 5-check test batch backfilled retroactively at user request to validate the workflow (`chamath-00:59:45`→2065, `chamath-01:01:35`→2028, `friedberg-01:11:59`→2035, `andrew-ross-sorkin-00:39:59`→2040, `andrew-ross-sorkin-00:44:34`→2035). **~685 of ~690 pre-existing `inconclusive` checks still lack a `resolves_by` date and need retroactive backfill.** |
| Curated "Big Ones" high-impact section (item 3) and sitewide search (item 4), done together | Ranked #3 and #4 by effort in the same 2026-08-31 prioritization, user-requested to do both in one go | **Complete 2026-08-31**, revised same day - (3) `config/big_ones.json` originally listed 12 hand-picked `{episode_id, id}` pairs mixing right/wrong/inconclusive predictions, rendered between the headline stat and Host Accuracy. Per follow-up user requests, revised to: right-calls-only, moved below Guest Predictions, capped at the top 6 by a new backend `impact_score` field (1.0-1000 per candidate in a 9-entry pool, editorial judgment of real-world significance, never displayed) - see the dedicated row below for full detail. (4) New `search.html` + `static/search_index.json`: single search box across all 4,001 predictions/episodes/hosts/guests, type-filterable, results render only once the visitor types (avoids dumping the full index). Both reuse the existing `prediction-card`/`badge-*` CSS patterns, no new styling needed. Site rebuilt clean |
| Big Ones refinements: home nav "Home" link; section moved below Guest Predictions; right-calls-only with a new backend `impact_score` ranking, capped at top 6 | Same-day follow-up requests, 2026-08-31 | **Complete 2026-08-31** - added "Home" as the first nav link in `base.html` (previously only the logo linked home). Moved the "Big Ones" section to after Guest Predictions instead of before Host Accuracy. Changed selection to right-verdict-only, top 6 by a new `impact_score` field (1.0-1000, backend-only, never rendered) added to each of 9 candidates in `config/big_ones.json`; `generate_site.py` filters to `result == "right"` and sorts by `impact_score` descending before slicing to 6. Also caught and fixed, during a user-requested `docs/PRD.md` em-dash review: 4 em dashes introduced earlier the same day in `docs/PATCHNOTES.md`, one in the Big Ones description in `index.html`, plus 2 pre-existing `&mdash;` "no data" placeholders (`index.html`, `leaderboard.html`) and one older historical `PATCHNOTES.md` entry, all replaced per §26. `docs/PRD.md` itself had no new violations; its only remaining em-dash mentions are the §26 rule's own self-referential examples |
| Home page 6-max convention: Recently Settled capped to 6 (was 8), and the cap formalized as a single `HOME_SECTION_MAX` constant applied to all three home page prediction/episode sections, documented in §9.2 | Same-day follow-up request, 2026-08-31: "top 6 for recently settled too please. also document on the homepage each section of predictions should only list 6 max" | **Complete 2026-08-31** - `generate_site.py` now defines `HOME_SECTION_MAX = 6` and uses it for the Big Ones, Recently Settled, and Recent Episodes slices (previously three separate hardcoded numbers: 6, 8, 6). Documented the convention in §9.2 above |
| Extend the §27 home page filter UI to every individual host and guest page | Same-day follow-up request, 2026-08-31: "can we also add these filters to each host's individual page?" (this row already existed as a "Planned" roadmap item above, now built) | **Complete 2026-08-31** - `host.html` now renders the same Resolved-only checkbox / topic dropdown / Total-Year-Topic segmented toggle as the home page's Host Accuracy section, scoped to that one speaker's `chart_entries` and topic list. No new client JS: `setupHomeCharts()` already worked off generic `.scorecard[data-who]` + filter-control IDs, so it drives the single-card host page unchanged |
| Permanent hosts display their full "First Last" name everywhere (was first-name-only, e.g. "Jason" instead of "Jason Calacanis") | Same-day follow-up request, 2026-08-31: "also on the host's page can we display their full name (First Name Last Name) rather than just first name?" | **Complete 2026-08-31** - new `display_name_for()` helper in `generate_site.py` prefers `config/hosts.yaml`'s existing `display_name` field for the four permanent hosts (whose slugs are short nicknames), falling back to the prior slug-capitalization behavior for guests (already full names). Fixed at the shared `who_display` source, so it applies sitewide (host pages, home page scorecards, leaderboard, search), not just the host page originally asked about |
| Host/guest page topic filter also filters the predictions list; collapse button for the predictions list; confirmed guest pages already match host page functionality | Same-day follow-up request, 2026-08-31: "on the hosts' page can we make the filter of topics also apply to the predictions listed below them? Also can we add a collapse button for the predictions. also can we make the guest pages the same functionality as the host pages?" | **Complete 2026-08-31** - the topic dropdown's `render()` in `app.js` now also hides/shows `#predictions-list` cards by their `data-tags` attribute, with a "no predictions match this topic" fallback message. New "Hide predictions"/"Show predictions" button toggles `#predictions-list`'s `hidden` attribute. Guest pages needed no code changes: `host.html` already renders identically for every speaker, so both new features apply to guest pages automatically - confirmed by inspecting a built guest page (`host/elon-musk.html`) alongside a host page |
| Fixed the collapse button (didn't actually hide the list) and renamed its labels | Same-day follow-up bug report, 2026-08-31: "the hide and show predictions button isn't working. please ensure its working and rename it 'Collapse' and 'Expand'" | **Complete 2026-08-31** - root cause: `.predictions { display: flex; }` in the author stylesheet overrides the browser's default `[hidden]{display:none}` rule, since author CSS always wins over UA defaults regardless of selector specificity, so toggling the `hidden` attribute was a no-op. Fixed by toggling `style.display` directly in `app.js`. Relabeled "Hide predictions"/"Show predictions" to "Collapse"/"Expand" |
| Extended the "Resolved only" checkbox on host/guest pages to also filter the predictions list, matching the topic dropdown's existing scope | Same-day follow-up request, 2026-08-31: "can we also get the resolved only filter to apply on the hosts/guests pages?" | **Complete 2026-08-31** - each prediction card now carries a `data-result` attribute; `app.js`'s `render()` hides ambiguous/inconclusive/unvalidated cards when the checkbox is checked, alongside the existing topic filter. Generalized the empty-list fallback message from "this topic" to "this filter" since either control can now empty the list |
| Fixed the resolved-only/topic filters not applying to the predictions list on first load (needed two clicks) | Same-day follow-up bug report, 2026-08-31: "can you make the default state also hide then? its only working when i click multiple times on it" | **Complete 2026-08-31** - `render()` was only wired to each filter control's `change` event, never called on initial page load, so the list started unfiltered despite "Resolved only" defaulting to checked (the chart matched by coincidence, since the server-rendered donut already only counts right/wrong). Fixed with one `render()` call at the end of `setupHomeCharts()`'s setup |
| Pre-launch parity pass: home page filter UI + "Last updated" date (§27) | 2026-08-25 | Complete - resolved-only checkbox, topic dropdown, Total/By Year/By Topic segmented toggle, "Last updated" date, and a dismissible welcome banner all shipped in `generate_site.py`/`app.js`/templates |
| **Full site replacement (repo restructure v2, per Decisions Log §14.5): promote the former `rewrite/` contents to the repo root; archive old pipeline (`scripts/`, `web/`, `config/`, old `data/`, `AGENTS.md`, `DEVELOPMENT.md`, `analysis.md`, root `requirements.txt`) into `old/`** | 2026-08-25 | Complete |
| **Phase 5: deploy to GitHub Pages (MVP launch)** | 2026-08-25 | Complete - live at https://azqato.github.io/allinpredictions/ |
| Post-deploy data-quality fix: two prediction files had a `freeberg` typo (should be `friedberg`) and a handful of `unknown`-speaker predictions had a bare `role: "host"`/`"unknown"` instead of `null`, producing bogus "Freeberg"/"Unknown" scorecards on the live site | 2026-08-25 | Complete - fixed in commit `3c579b9`, confirmed live |
| Documentation audit & consolidation, full pass (§16.1) | 2026-08-25 | Complete - this pass; supersedes the partial 2026-08-04 pass |
| §16.2: writing-style / em-dash sweep | 2026-08-25 | Complete - run against the live repo in this same pass, ahead of the original "post-launch" trigger since the user asked for it explicitly alongside this documentation audit |
| Full-archive validation sweep (10 predictions/batch, ascending by prediction count, fewest-first/oldest-first tiebreak, §13), **combined with** the full retroactive `resolves_by` backfill across all pre-existing `inconclusive` checks (~685 remaining, in batches of 5 per the 2026-08-31 test batch) | **Post-launch, ongoing**, against the live site; not a launch blocker. Combined into one row 2026-08-31 at user request ("combine this one into full-archive validation and make its status as planned") - both are the same kind of work (reading a prediction, researching its real-world outcome, writing/updating its verdict record), so tracking them as one ongoing maintenance stream instead of two avoids duplicating the same research pass | Planned, continuing indefinitely as maintenance |
| §16.3: mobile-responsive audit | Post-launch, checked against the live URL | Planned |
| §17: Annual Predictions episode filter | Post-launch | Complete 2026-08-27 - shipped as part of the batched-items row above |
| `video_id` resolution (45 episodes) | Post-launch | **Complete 2026-08-27/31** - superseded by the incremental-process backlog batches above; all 45 originally-blocked episodes were resolved (yt-dlp channel search / manual retitled-upload matching) as part of Batches 1-12 and the Ray Dalio recovery. This row predates that work and was left stale; see the "413/413 tracked episodes" note at the top of this Roadmap section |
| Follow-up extraction sweep: pick up the 45 episodes unblocked by `video_id` resolution, plus any newly published episodes since the 2026-08-04 sweep | Post-launch, after `video_id` resolution progresses | **Complete, ongoing** - folded into the incremental process (§13 Phase 4): the 45-episode backlog is fully cleared, and newly-published episodes are picked up automatically each sweep (most recently Batch 12, 2026-08-31) |
| §34: Host vs. guest prediction league table (Reddit feedback, 2026-08-27) | Post-launch; ready to build once accuracy-formula/min-sample/guest-page questions are answered | Complete 2026-08-27 - shipped as the `leaderboard.html` table in the batched-items row above |
| §35: Listener voting/feedback mechanism (Reddit feedback, 2026-08-27) | Long-term, no scheduled trigger; needs a real backend/storage decision this static site doesn't have yet | **Full feature still Deferred**; a lightweight substitute (footer link to `github.com/Azqato/allinpredictions/issues`) **shipped 2026-08-31** at user request - see §35 for detail |
| Extend the §27 home page filter UI (Resolved only checkbox, topic dropdown, Total/By Year/By Topic segmented toggle) to every individual host and guest page, not just the home page | Post-launch; user-requested 2026-08-27 | **Complete 2026-08-31** - see the dedicated row in the same-day follow-ups above |
| §36: competitor-audit feature gaps, all 8 approved for implementation (accuracy %/hit-rate everywhere, home page headline stat, host leaderboard, sitewide search, unified all-predictions browse page, "recently settled" feed, curated high-impact-calls section, per-host verdict-count breakdown) | After the full ingest-and-validation sweep completes (47-episode backlog + remaining validation batches); user-requested and approved 2026-08-27 | **Complete 2026-08-31** - all 8 shipped: 6 in the batched-items row above, plus sitewide search and the curated "Big Ones" section in the row below (2026-08-31) |
| Combined the `resolves_by` backfill into the full-archive validation sweep row; added a footer link to GitHub Issues as a lightweight §35 feedback substitute | Same-day follow-up request, 2026-08-31: "combine this one into full-archive validation and make its status as planned" / "for this one, lets point people towards this page: github.com/Azqato/allinpredictions/issues" | **Complete 2026-08-31** - merged the two rows (both are the same "research a prediction, write its verdict" work) into one "Planned, continuing indefinitely as maintenance" row. Added a footer link on every page ("Open an issue on GitHub") pointing to the repo's Issues tab, which was already public/enabled by default (confirmed via the GitHub API, no repo setting needed changing). The full voting/backend feature (§35) stays deferred; this only answers general feedback intake |
| Removed "About" from the site nav | Same-day follow-up request, 2026-08-31: "can you remove the About page from navigation?" | **Complete 2026-08-31** - dropped the `about.html` link from `base.html`'s nav. The page itself is untouched and still generates/reachable by direct URL, just no longer linked from the header |
| §36.1-36.5: visual/UX detail re-audit (hero block, per-host highlight cards, "Fresh Verdicts" feed, "The Standings" leaderboard, "The Big Ones" curated section, "This Episode's Calls", topic tag cloud), a new "The Roster" host+guest index page sorted by prediction count, a new "The Full Ledger" browse/search/filter page, a redesigned Methodology page, and a sitewide distinct-naming convention | Same sequencing as §36 (after the full ingest-and-validation sweep); documentation-only pass 2026-08-27, no implementation yet | **Split into 11 tracked subtasks 2026-08-31, re-sequenced by dependencies + effort the same day** (see §19.1 below) - broken down at user request ("can we split #2 up into subtasks?"), then resequenced at follow-up request ("sort the roadmap based on dependencies and what requires the least effort first"). Not started; §19.1 is now the authoritative task list and execution order for this item |

**Explicitly deferred items and why** (see also §12 Risks and §16 for full detail on each):
- Caption-less episode handling (2 episodes with a `video_id` but no captions fetchable via any current method): deferred with no scheduled trigger yet, to be revisited later once a fetch method exists or a manual-transcription fallback is decided on; not on the critical path since it's only 2 of 404 episodes.
- Local voice-diarization enhancement (§6.4 alternative): only triggered if the attribution validation gate (§6.4, §14.1) is later found to have failed at scale; not needed today because the gate passed on the initial sample.
- Second-opinion validation pattern (re-validate in a fresh session and diff): a possible accuracy improvement over single-pass validation, deferred because single-pass validation is working adequately and doubling validation cost isn't justified yet.
- GitHub Action for deterministic-only site regeneration: deferred because there's no CI need yet at this scale; manual regeneration is fast and the Claude-driven steps can't run in CI anyway.
- Multi-podcast generalization: explicitly out of v1 scope per §2 Non-Goals; the architecture stays podcast-agnostic where cheap to do so, but no plugin system is being built now.
- Listener voting/feedback mechanism (§35): deferred with no scheduled trigger; the user's own framing of this Reddit-sourced idea flagged it as long-term, and it genuinely needs a backend/storage decision (accounts-free voting has no natural anti-abuse mechanism) this static, accountless site doesn't have today.

### 19.1 §36.1-36.5 Subtask Breakdown (the full roadmap moving forward)

**Status:** planned, split out 2026-08-31 at explicit user request ("can we split #2 up into subtasks? that's a lot in one to tackle at once"), where "#2" referred to the §36.1-36.5 visual/UX re-audit item as presented in a prior "what's next" summary. This table is now the authoritative, granular task list for that roadmap item - update rows here as each subtask ships, rather than tracking it as one line.

Note: some ground originally scoped into §36.1-36.5 back on 2026-08-27 (sitewide search, the Full Ledger's existence, a home page "recently settled"/"Big Ones" section, the leaderboard page) has since shipped under other roadmap rows above. The subtasks below are what's genuinely still outstanding against the live site as of 2026-08-31 - visual/structural refinement and net-new pages, not the underlying data/functionality, which already exists.

**Re-sequenced 2026-08-31** at explicit user request ("sort the roadmap based on dependencies and what requires the least effort first based on dependencies") - this is a real execution-order change, not a relabeling. Rule applied: items with no unmet prerequisite come before items that need one, and within a tier (same set of satisfied prerequisites) the lower-effort item goes first. Row 11 (naming) has no independent slot since it's not a standalone deliverable - it rides along with rows 4-10 as each ships. Effort is a rough t-shirt estimate (Low/Medium/High) based on how much net-new curation, copy, or cross-page rework each item needs versus reusing what rows 1-2 build.

| # | Subtask | Depends on | Effort | Status |
|---|---|---|---|---|
| 1 | Verdict data-model decision: resolve whether `ambiguous`/`inconclusive` map cleanly to "partly right"/"too early," or need reframing/a new state, before any accuracy or leaderboard visual locks in a denominator (§36.1 item 8, §36.4) | None | Low | Planned |
| 2 | Reusable prediction-card component: one markup/JS pattern for a prediction card, used by every section/page that renders one (home sections, Full Ledger, episode pages) instead of near-duplicate card HTML per template (per §36.3's note) | None | Medium | Planned |
| 3 | "Topic Index" tag cloud with live per-topic counts on the home page (§36.1 item 7) | #2 | Low | Planned |
| 4 | Home page hero block: bold two-line headline + one-line sitewide stat as a CTA (§36.1 item 1) | #1 | Low-Medium | Planned |
| 5 | "This Episode's Calls": every call from the single most-recent episode (including ungraded), distinct from the existing Recently Settled section (§36.1 item 6) | #2 | Low-Medium | Planned |
| 6 | Methodology page redesign: numbered pipeline steps (§6) + a verdict glossary, explicitly noting guest predictions are scored too (a stated point of difference from the competitor) (§36.4) | #1 | Medium | Planned |
| 7 | "The Full Ledger" upgrade: replace the current year/topic/result dropdowns with pill filters (host x verdict x topic) (§36.3) | #2 | Medium | Planned |
| 8 | "The Standings": leaderboard-style component with a segmented verdict bar per host + superlative badges (§36.1 item 4) | #1, #2 | Medium | Planned |
| 9 | "The Roster": redesign `host/index.html` with avatars, hit-rate %, and guests sorted descending by prediction count (§36.2) - avatar sourcing for guests is still unresolved (§36.2's own "not yet scoped" note), which is why this sits above the per-host cards despite a similar dependency set | #1, #2 | Medium-High | Planned |
| 10 | Per-host highlight cards on the home page: "Signature Calls" (top hits) / "The Misses" (collapsed) in a 4-up grid (§36.1 item 2) | #1, #2 | High | Planned |
| 11 | Naming-convention pass (§36.5): apply the distinct working names (table already in §36.5) to each item above as it ships, so nothing launches under the competitor's own copy | Rides along with #4-#10, not a standalone step | - | Planned |

**Explicitly kept separate from this breakdown, and from this reorder:**
- §16.3 (mobile-responsive audit) stays its own roadmap row, done after rows 1-10 above land - it's testing against whatever layout results from this pass, not redesign work itself, so resequencing it earlier wouldn't make sense.
- The full-archive validation sweep (now combined with the `resolves_by` backfill into one row above in the main §19 table) is an independent maintenance track with no dependency relationship to this UI work - nothing here blocks it and it blocks nothing here, so it's left at its existing, user-set cadence rather than folded into this dependency sort.
- §35 Listener voting/feedback stays deferred with no scheduled trigger; it's blocked on an unmade backend/storage decision outside this dependency graph, not on effort ordering.

## 20. Metrics

This is a static, account-free informational site, so metrics here are honestly scoped to what such a site can actually measure, not a product-usage funnel.

- **North star metric:** total validated (right/wrong/ambiguous, not unvalidated/inconclusive) predictions published on the site. This is the single number that best represents delivered value, since the product's promise is "predictions checked against reality," not just "predictions listed."
- **Acquisition:** organic/referral traffic only (no paid marketing planned): links shared from the repo, social shares of specific host/episode pages, search engine indexing of the static pages. No acquisition tooling is installed yet (see below).
- **Engagement:** pageviews per session, which host/episode pages get visited most, whether visitors use the topic/year filter interactivity. Not yet instrumented: no analytics script exists in `site_src/static/` as of this audit, and adding one is a deliberate future decision (must stay free and privacy-respecting to match G1/G7's spirit), not an oversight to silently fix here.
- **Retention:** low relevance for a static informational site with no accounts; the closest honest proxy would be repeat-visit rate via basic web analytics once instrumented, not tracked today.
- **Performance:** page load time, Lighthouse/PageSpeed score, GitHub Pages uptime (effectively controlled by GitHub's infrastructure, not this project). The site is now deployed (https://azqato.github.io/allinpredictions/) but no Lighthouse/PageSpeed baseline has been captured yet; that is genuinely open, not a stated target being tracked against, and should be filled in the next time this section is revisited.
- **Measurement method & reporting cadence:** none configured yet. This whole section should be revisited and filled in with a real analytics choice (e.g., a privacy-respecting, free, script-tag-only option, consistent with G1/G4) as part of, or shortly after, Phase 5 deployment.

## 21. Runbook

**Local setup (fresh machine):**
```bash
git clone <repo-url>
cd allinpredictions
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
No API keys, no `.env` file, no external accounts needed.

**Build:** `python scripts/generate_site.py` writes `index.html`, `about.html`, `episodes/*.html`, `host/*.html`, and `static/` directly into the the repo root (§8.1). No separate build tool; this script is the entire build.

**Deploy (only environment: GitHub Pages):**
1. Ensure `data/predictions/*.json` and `data/checks/*.json` reflect the latest processed episodes (run the mechanical + Claude-driven steps per §6 and §10 first).
2. `python scripts/generate_site.py`.
3. Commit the regenerated site files and the updated `data/` alongside them.
4. Push to the default branch.
5. GitHub repo settings → Pages → Deploy from branch → `main` / `(root)` (one-time setup; subsequent pushes auto-deploy).

**Rollback:** `git revert` the deploying commit (or `git reset` to the prior commit and force-push only with explicit user approval, per this project's standing git-safety norms) and push again; GitHub Pages redeploys from whatever is at the tip of the branch. There is no database or stateful backend to roll back separately; the site is fully derived from the committed `data/` + generated HTML.

**Environment configs:** one environment only (GitHub Pages production). No staging environment exists or is planned for v1; local `python -m http.server` preview (§ README "Running locally") serves as the pre-push check instead.

**Common errors:**

| Error | Likely cause | Fix |
|---|---|---|
| `generate_site.py` raises a YAML parse error | `config/hosts.yaml` has an unquoted string containing a colon or a leading-quote-then-unquoted-text pattern | Quote the offending list item fully (see the two real instances of this hit during Phase 0/3 build) |
| Host/episode pages render unstyled (no CSS) | `asset_prefix` not passed into a one-level-deep template's render call, so `static/style.css` resolves relative to the wrong directory | Pass `asset_prefix="../"` explicitly in the `env.get_template(...).render(...)` call for any page one level below root (this exact bug was hit and fixed on 2026-08-04, see PATCHNOTES) |
| `shutil.rmtree` / `PermissionError` when regenerating the site | An OS-level file lock (e.g., an editor or the OneDrive sync client) is holding one of the generated files/folders open | Re-run the script (it now uses `ignore_errors=True` and only touches known generated paths, not the whole output directory) |
| `fetch_transcripts.py` fails for a specific episode | Captions disabled on that YouTube video, or `youtube-transcript-api` blocked/rate-limited (unofficial API) | Confirm via the `yt-dlp --write-auto-sub` fallback path already built into the script; if that also fails, the episode is logged to `data/transcripts/_missing.json` and skipped, not treated as a hard failure |
| `fetch_episodes.py` can't resolve a video_id for an episode | Automatic matching (episode-code/title/nearest-date) failed, common on older or inconsistently-titled episodes | Add a manual entry to `config/youtube_urls_override.json` (`episode_id: video_id`) |
| `fetch_episodes.py` resolves almost no video_ids and only logs a WARNING | `yt-dlp` is pip-installed as a Python module only (no standalone binary on PATH), common on Windows dev machines; `fetch_ytdlp_playlist()`'s `subprocess.run` raised `FileNotFoundError`, was caught, and silently degraded to near-zero matches instead of hard-failing | Fixed 2026-08-25: `fetch_ytdlp_playlist()` now shlex-splits `--yt-dlp-path` and automatically falls back to `<this interpreter> -m yt_dlp` if the primary command isn't found, so no flag is needed by default; see PATCHNOTES |
| `generate_site.py` raises `DataValidationError` and refuses to build | A `data/predictions/*.json` or `data/checks/*.json` record that would render as a speaker card has a missing/placeholder `who`, an invalid `role`, a `who`/permanent-host role mismatch, a `who` that's a near-miss (edit distance <=2) of a permanent host slug, or a check `result` outside `right/wrong/ambiguous/inconclusive` | Fix the offending record listed in the error report (added 2026-08-26 specifically to catch a repeat of the freeberg/unknown host-card incident at build time instead of on the live site; see §28, §31) |

**Monitoring:** no dedicated monitoring is configured (matches the "no analytics yet" note in §20). GitHub's own Pages deployment status (repo → Actions/Pages tab) is the only current signal that a deploy succeeded; browser DevTools console is the way to check for client-side JS errors in `app.js` during manual QA.

## 22. Technical Requirements (Summary)

This section is a single point of reference pulling together material detailed elsewhere in this PRD, so a reader doesn't have to jump around to get the full technical picture.

- **System architecture:** fully static site, no server, no database, no runtime backend. All "intelligence" (extraction, attribution, tagging, validation) happens offline, ahead of time, in a Claude Code session, and is baked into committed JSON (`data/predictions/*.json`, `data/checks/*.json`) that a deterministic Python script (`scripts/generate_site.py`) turns into static HTML. See §4 for the full pipeline diagram.
- **Tech stack with versions:** see the table in `README.md`'s "Tech stack" section (kept as the single source of truth for exact versions, to avoid this PRD drifting out of sync with `requirements.txt`).
- **Folder structure:** see §8 for the full annotated tree, and §8.1 for why the generated site lives at the repo root rather than a `docs/` subfolder.
- **Data models:** see §7 for the full JSON schemas (`episodes.json`, `predictions/<id>.json`, `checks/<id>.json`).
- **"API design" (internal data flow, since this is browser-only):** at build time, `generate_site.py` joins episodes + predictions + checks into per-page context objects and renders them into static HTML via Jinja2 templates (`site_src/templates/*.html`); aggregate chart stats are also computed at build time and embedded as data attributes / inline SVG. At runtime in the browser, `app.js` reads only what's already embedded in the page DOM (the pre-rendered SVG plus a small alternate-view SVG string in a `data-*` attribute): there is no client-side fetch of JSON, no runtime API calls of any kind.
- **State management:** none beyond what plain DOM APIs need. `app.js` holds no framework state; the two pieces of client-side interactivity (donut chart toggle, YouTube-warning modal) each use a couple of local JS variables scoped to their own IIFE, plus one `localStorage` key (`predict_timestamp_notice_seen`) for the one-time YouTube disclaimer.
- **Third-party integrations:** YouTube (captions via `youtube-transcript-api`/`yt-dlp`, no auth), the All-In podcast RSS feed (public, no auth), GitHub Pages (static hosting). Claude Code's own `WebSearch`/`WebFetch` tools are used during validation but are not a project dependency in the traditional sense: they're part of the agent doing the work, not an API this codebase calls directly.
- **Performance requirements:** no formal budget is set yet (ties to §20's "not deployed, no real Lighthouse numbers yet" caveat). Directionally: the site should stay lightweight given it's hand-rolled HTML/CSS/SVG with a small (~150-300 line) vanilla JS file and no framework runtime, but a real target (e.g., page weight, Time to Interactive) should be set once Phase 5 ships and can be measured against actual hosting.
- **Known technical debt:**
  - No analytics/monitoring installed (§20, §21): acceptable for now, should be revisited at or after Phase 5.
  - `generate_site.py`'s targeted-cleanup approach (§8) assumes the list of generated top-level paths (`index.html`, `about.html`, `episodes`, `host`, `static`) stays exhaustive; a future template that introduces a new top-level generated path would need that list updated too, or stale files could linger after a rename/removal.
  - No automated tests exist for the mechanical scripts or the site generator; correctness has been verified manually (local server + `curl` status checks + manual content spot-checks) rather than via a test suite. Acceptable at current scale, worth reconsidering if the pipeline grows more complex.

## 23. Security

- **Authentication model:** none. This is a public, static, read-only site with no user accounts, no login, no sessions.
- **Authorization model:** none; there are no user roles; every visitor sees the same content.
- **Data storage:** no user data is collected or stored anywhere (no forms, no cookies beyond the single `localStorage` flag noted in §22, which stores nothing personal, just "has this browser dismissed the YouTube-link disclaimer"). The only data the site stores is public podcast content (episode metadata, transcribed quotes, predictions, validation research) committed to the repo.
- **Environment variables / secrets:** none exist in this project. Confirmed: no `.env` file, no hardcoded API keys or tokens anywhere in `scripts/`, `config/`, or `site_src/` (there is nothing *to* hardcode, since every external call, YouTube captions and the RSS feed, is unauthenticated). If a future feature ever needs a secret, it must go through environment variables (never committed) and get documented here and in `README.md`'s "Environment variables" section before merging.
- **Third-party trust:** YouTube's caption/timedtext endpoints and `yt-dlp` see only a public video ID per request (no personal data). The All-In RSS feed is fetched read-only. Claude Code's `WebSearch`/`WebFetch` tools (used during validation) send prediction text and search queries to the underlying search backend as part of Claude's own tool use; no project-specific credentials are involved. GitHub Pages serves the built static files; it does not execute any server-side code on this project's behalf.
- **Known attack surface:** minimal, given no forms, no user input, no server. The main theoretical risk is XSS if untrusted content were ever rendered unescaped (this doesn't currently apply, since all rendered content originates from Claude's own extraction/validation output and the project's own YAML/JSON config, not arbitrary user input), and Jinja2's autoescaping is explicitly enabled (`autoescape=select_autoescape(["html"])` in `generate_site.py`) as a defense-in-depth measure regardless.
- **Dependency policy:** no automated vulnerability scanning is configured yet (no Dependabot, no `pip-audit` in CI, since there is no CI). Given the small, stable dependency list (`youtube-transcript-api`, `yt-dlp`, `jinja2`, `pyyaml`), manual periodic `pip list --outdated` checks are the current practice; enabling GitHub's free Dependabot alerts once the repo is public-facing is a reasonable low-effort addition worth doing before or shortly after Phase 5.

## 24. Press Release

**All-In Predictions: A Free, AI-Checked Scorecard for Podcast Predictions**

*Track record, not just talk, for the All-In Podcast's four hosts and their guests.*

San Francisco, California. All-In Predictions is a free website that tracks every prediction made on the All-In Podcast and checks, using AI-assisted research, whether each one came true. Visitors can see each host's track record at a glance, read the original quote and timestamp behind any prediction, jump straight to the moment in the source video, and read a cited explanation of why a prediction was judged right, wrong, or too soon to call.

Podcast listeners hear hosts make confident calls about politics, markets, and technology every week, but rarely get to see, months or years later, whether those calls held up. All-In Predictions solves that by systematically extracting predictions from every episode's transcript, attributing each one to the host or guest who made it, and researching the outcome once enough time has passed.

The site is built entirely on free tools: it reads YouTube's own caption tracks instead of paying for transcription, and every step that requires judgment (figuring out who's speaking, deciding what counts as a real prediction, and researching whether it came true) is done directly by Claude, Anthropic's AI assistant, rather than a separate paid API. That keeps the project free to run indefinitely and means it can be extended or forked without needing anyone's credit card.

"I always wondered if the guys were actually right as often as they sounded," said a hypothetical longtime listener. "Now I can just look it up instead of taking their word for it."

Visit the site to browse by host, by episode, or by topic, and to see the full track record for yourself. The project is open about its limitations (speaker attribution is inferred from context rather than voice matching, and the underlying data is continuously being expanded), and every page says so.

All-In Predictions is an independent, unofficial project. It is not affiliated with the All-In Podcast or its hosts.

## 25. FAQ

**Core & audience**
1. *What is All-In Predictions?* A site that extracts predictions made on the All-In Podcast and checks whether they came true, with sources cited.
2. *Who is this for?* Listeners of the All-In Podcast who want an accountability record for the hosts' (and guests') public predictions.
3. *Is this affiliated with the All-In Podcast?* No. It's an independent, unofficial project.

**Usage**
4. *How do I find a specific host's track record?* Go to their scorecard page (`/host/<name>.html`), which shows a right/wrong breakdown plus every tracked prediction they made.
5. *Can I filter by topic or year?* Yes, on the home page's host scorecards, using the topic dropdown and the Total/By Year/By Topic toggle.
6. *What does "Resolved only" mean?* It shows accuracy as right-vs-wrong only, excluding predictions still too early to judge (`inconclusive`) or genuinely unclear (`ambiguous`) from the percentage.
7. *Can I jump to the moment in the original episode?* Yes, most prediction cards have a "View on YouTube" link that deep-links to the exact timestamp (with a one-time disclaimer about timestamp accuracy).

**Cost & data**
8. *Is this free to use?* Yes, entirely: there's no paywall, no account, no ads.
9. *What data does the site use?* Publicly available YouTube captions for the podcast, plus web research (via Claude's search tools) to validate each prediction, with sources always cited.
10. *Does this cost anything to run?* No paid APIs are used anywhere in the pipeline (see §1 Goals, G1); that's a deliberate design constraint, not an accident.
11. *Do you store any of my personal data?* No. There are no accounts, no forms, and the only browser storage used is a single flag remembering whether you've seen the YouTube-link disclaimer once.

**Technical**
12. *What browsers/devices does it work on?* Plain HTML/CSS/JS with no framework runtime; it should work in any modern browser. A dedicated mobile-responsive audit is planned post-launch (§16.3) but not yet completed.
13. *Do I need to install anything to browse the site?* No, it's a static website.
14. *How is this different from the earlier version of this project?* The earlier version used paid transcription and OpenAI/xAI APIs and ran on Next.js/Cloudflare Pages; this rewrite uses only free tooling and Claude, and runs as a vanilla static site on GitHub Pages (see §3 for the full comparison table).

**Limitations**
15. *How accurate is the speaker attribution?* It's inferred from transcript context (who's addressed by name, self-reference, recurring topics), not voice matching, because no audio is downloaded or processed. Each prediction shows a confidence level, and low-confidence ones are excluded from host/guest scorecards (though still visible on the episode page). See §6.4 for the full design and its tradeoffs.
16. *Could a prediction be misattributed to the wrong person?* It's possible, especially in solo guest-interview episodes without clear direct-address cues. This is a known, disclosed limitation, not a hidden one.
17. *Is every episode covered?* Not yet: the archive is being processed incrementally (§13 Phase 4); check the site's episode list for current coverage.
18. *Are all predictions validated?* Not immediately: extraction and validation happen in separate passes (§13), so newly extracted predictions may show as "Unvalidated" until the validation sweep reaches them.
19. *What happens to very recent predictions?* They're typically marked `inconclusive` since not enough time has passed to check them; the site doesn't force a right/wrong verdict before it's fair to do so.

**Support & internal**
20. *How do I report an error or bad attribution?* Via the project's repository (issue tracker, once public); there is no in-page reporting flow in v1.
21. *Why build this instead of just reading the old site?* The old site works but costs money to keep running and requires paid API keys to update; this rewrite exists so the project can be maintained indefinitely for free (see the Decisions Log §14.5 for the long-term plan to fully replace the old pipeline).
22. *What does success look like for this rewrite?* See §15 Success Criteria and the north star metric in §20: a fully processed, validated archive rendered as a working, deployed static site, with documentation good enough that a future Claude Code session could pick up the project cold.
23. *What's next after the MVP?* As of the 2026-08-25 sequencing change (§14.5, §19): the pre-launch parity pass (§27), then the full site replacement (repo restructure, old pipeline archived to `old/`), then GitHub Pages deployment (Phase 5), all ahead of finishing the full-archive validation sweep. The remaining validation batches, the §16.2/§16.3 hardening passes, and the Annual Predictions filter (§17) continue after that, as ongoing post-launch work against the live site rather than pre-launch gates.

## 26. Writing Style

**Rule:** no em dashes in either form (the literal Unicode character "—" or the HTML entity `&mdash;`), and no double dashes (`--`) used as punctuation, anywhere in this project's prose: documentation, HTML page content, prompts, and code comments meant for human readers. The only exceptions: CSS custom properties, which legitimately use a leading double dash as syntax (e.g. `--bg`, `--accent`) and must never be "fixed"; CLI flag tokens (e.g. `--limit`, `--force`), which are argument syntax, not punctuation; and verbatim quoted source material (transcript `quote` fields, external citation titles) - see §16.2's status note for why those are a deliberate exception rather than an oversight.

**Replacement rule, chosen by context, not a single default:**
- **Comma:** the default in most cases; keeps a sentence flowing without drawing attention to the punctuation itself.
- **Colon:** when introducing a list, explanation, or elaboration after a complete clause (this includes a bolded/labeled term followed by its definition, e.g. "**Term:** explanation" - the single most common pattern in this document).
- **Semicolon:** when joining two closely related independent clauses that could each stand alone.
- **Parentheses:** for an aside or supplementary detail that isn't central to the sentence.
- **Period:** when the cleanest fix is splitting into two sentences; shorter sentences are often clearer anyway.
- **Single hyphen** (a plain `-`, spaced or unspaced): acceptable where none of the above reads naturally, and specifically encouraged in document titles, section headings, and version lines (e.g. "PRD: All-In Predictions - Free-Tooling / Claude-Native Rewrite"). This fifth option was added on 2026-08-25 as a live instruction from the user, reconciling this section's original four-way rule (written 2026-08-04) with the broader replacement set actually used in the 2026-08-25 sweep; the original four options are unchanged, this is an addition, not a replacement of them.

**Status:** the formal, project-wide sweep for existing em dashes/double dashes ran on 2026-08-25 (§16.2), ahead of the originally-planned post-launch window, per the user's explicit request in the same session as this documentation audit. This rule has been followed prospectively since 2026-08-04 for new content, so the sweep's job was to catch older material, not a large ongoing backlog. Going forward, this rule applies to all new documentation, prompts, code comments, and generated site copy from this point on.

## 27. Pre-Replacement Parity Checklist: Home Page Filter UI & "Last Updated" Date

**Status: complete as of 2026-08-25.** All six rows in the gap table below have shipped: `generate_site.py` now builds per-host `chart_entries`/`chart_json`, `app.js` was rewritten to drive the resolved-only checkbox, topic dropdown, and Total/By Year/By Topic segmented toggle client-side from that embedded data, `base.html` carries a "Last updated" date and a dismissible welcome banner, and `style.css` has the matching component styles. Verified locally before the repo restructure and again against the live GitHub Pages URL after deploy.

**Original trigger (satisfied above):** immediately, as the last local step before the full site replacement and GitHub Pages deploy (Decisions Log §14.5, §19) - **no longer gated on the validation sweep's progress**, per the 2026-08-25 MVP-first sequencing change. Checked locally via `python -m http.server` since this runs just before the repo restructure/deploy. Flagged by the user on 2026-08-04 against the live original site as a real feature gap in the rewrite's MVP, not a nice-to-have.

**Objective:** bring the rewrite's home page up to parity with the original site's interactive host-accuracy section before that page is treated as a replacement for the original.

**Confirmed gap (rewrite MVP vs. original site, per the original's `HostCharts.tsx` and `layout.tsx`, both read during the initial codebase analysis):**

| Feature | Original site | Rewrite MVP (current) |
|---|---|---|
| "Resolved only" checkbox | Explicit checkbox; unchecked shows right/wrong/ambiguous/inconclusive, checked shows right/wrong only | Not present; the donut only supports a click-to-toggle between two fixed views (§9.3), with no checkbox and no labeled state |
| Topic filter dropdown | "All topics" dropdown listing every tag (AI, Climate, Conflict, Economy, Government, Health, Markets, Politics, Science, Tech, Venture) that recomputes all four host cards live | Not implemented at all |
| Total / By Year / By Topic segmented toggle | Three-way toggle; "By Year" renders a stacked bar chart per host (one bar per year, right/wrong stacked to 100%); "By Topic" renders the same per topic tag | Not implemented; `generate_site.py` only has a `donut_svg` helper (§4's site generator step), no stacked-bar equivalent exists yet in either the Python generator or `app.js` |
| "Last updated: <date>" | Displayed top-right of the header, next to the nav | Not present in `base.html` |
| Dismissible "Welcome" disclaimer banner | A top-of-page banner ("All predictions were automatically extracted and validated by LLMs, so there may be inaccuracies or mistakes.") with a "Dismiss" button | Not present; the rewrite only has the always-visible footer disclaimer (§9's about/footer content) |
| Verdict set shown | Four verdicts: Right, Wrong, Ambiguous, Inconclusive (color-coded, no separate "Unvalidated" slice) | Matches: `RESULT_KEYS`/`RESULT_COLORS` in `generate_site.py` already cover the same four plus `unvalidated`, so the data model doesn't need to change, only the UI |

**Implementation notes for when this is picked up:**
- The stacked-bar-by-year and stacked-bar-by-topic views need a new `stacked_bar_svg`-equivalent generator function alongside the existing `donut_svg` in `generate_site.py` (§4), following the same "compute server-side for the default state, embed an alternate-state SVG string for client-side swap" pattern already established for the donut toggle (§9.3), rather than introducing a client-side charting library (staying consistent with Tenet 2/G4, §18).
- The topic dropdown and the Resolved-only checkbox both need real client-side recomputation in `app.js` (not just a swap between two pre-rendered states), since the combination of topic and resolved-only and Total/By Year/By Topic is a larger state space than the current single donut toggle. This likely means embedding the full per-host, per-tag, per-year breakdown as a small inline JSON blob per page (already anticipated in §9.3's "holds the already-computed aggregate stats" language) and having `app.js` redraw the relevant SVG from that data on any filter change, still with zero external charting dependency.
- "Last updated" should be computed from the most recent entry in `data/manifest.json` (or the most recent git commit touching `data/predictions/` or `data/checks/`) at generation time, not hardcoded, so it stays accurate without manual editing on every regeneration.
- The dismissible welcome banner needs the same `localStorage`-flag pattern already used for the YouTube-link disclaimer (§9.5, `app.js`), just a second independent flag and a second small modal-adjacent component, not a new interaction pattern.
- This checklist item should be treated as complete only when a side-by-side comparison against the original site's home page confirms behavioral parity on all six rows above, not just visual similarity.

## 28. Conventions

Derived from the actual code and git history as of 2026-08-25, not a style guide imposed from outside. Where the codebase is inconsistent, the dominant pattern is named first and the deviation second.

- **Naming:** Python files and functions are `snake_case` (`fetch_episodes.py`, `build_speaker_index()`); JSON data keys are `snake_case` (`episode_id`, `speaker_confidence`); CSS classes are `kebab-case` (`.scorecard-head`, `.chart-controls`); CSS custom properties are `--kebab-case` (`--bg`, `--right`). Episode ids are the RSS/YouTube slugified title (kebab-case, no episode-number prefix); host/guest ids in `who` are lowercase single tokens (`jason`) or hyphenated full names for guests (`aaron-cowen`).
- **Formatting:** Python has no configured formatter (no `black`/`ruff` config file in the repo) - the dominant in-file style is 4-space indent, double-quoted strings, and `argparse` for any script-level CLI flags; this is a convention by consistent practice, not an enforced rule. JSON data files are hand-edited with 2-space indentation and compact single-line arrays for short lists (e.g. `"tags": ["ai", "tech"]`) - **preserve this exact formatting when hand-editing**, since a full `json.dump(..., indent=2)` re-serialization reformats every array onto multiple lines and produces large, noisy diffs unrelated to the actual change (this happened once during this session's data-quality fix and was reverted in favor of targeted string edits; see §31 for why this matters for future edits).
- **Organization:** one script per pipeline stage in `scripts/`, one Jinja2 template per page type in `site_src/templates/`, one JSON file per episode in `data/transcripts/`, `data/predictions/`, and `data/checks/` (never one combined file for the whole archive, to keep incremental/idempotent runs cheap - §6.8).
- **Comment density:** low. Module-level docstrings exist on most `scripts/*.py` files (one to a few sentences stating purpose) but inline comments are sparse and reserved for non-obvious constraints (e.g. the `asset_prefix` timing bug note in `generate_site.py`), not restating what a line does. This PRD and the templates/CSS follow the same low-comment-density norm as the code.
- **Error handling / logging / validation:** mechanical scripts (`fetch_*.py`) treat a per-episode failure (missing captions, unresolved `video_id`) as a skip-and-log, not a hard failure - the run continues and the gap is recorded in `data/manifest.json`/`data/transcripts/_missing.json` rather than crashing the whole batch. There is no structured logging framework; scripts print plain status lines to stdout. `generate_site.py` has no data-validation layer of its own - it trusts that `data/predictions/*.json` and `data/checks/*.json` already conform to the schemas in §7, since that data is written by Claude following `prompts/extract_and_tag.md`/`validate.md` rather than by unvalidated user input. This is a real gap, not a deliberate design choice - see §31.
- **Commit-message / branching style:** derived from `git log` as of this pass - short, imperative, present-tense subject lines (e.g. "Fix bogus host cards on the live site: freeberg typo, bare unknown role", "Add .nojekyll for GitHub Pages", "MVP launch: replace repo root with the rewrite site, archive old pipeline to old/"), no enforced prefix convention (no `feat:`/`fix:` tags), one focused change per commit, all authored so far by a single contributor working directly on `main` (no branches or PRs used yet in this repo's history - the workflow is commit-directly-to-main after local verification, consistent with the single-maintainer, no-CI setup described in §11 and §21).

## 29. Documentation Versus Reality

Discrepancies found while comparing this PRD, `README.md`, `docs/DESIGN.md`, and `docs/PATCHNOTES.md` against the actual codebase during the 2026-08-25 audit. Per this project's documentation policy (§33), a discrepancy between a doc and the code is resolved by trusting the code and updating the doc to match, *and* keeping a record here rather than silently deleting the old claim - this table is that record. Resolved entries are kept, marked resolved, not removed, so the reasoning survives.

| # | Discrepancy | Source of truth trusted, and why | Status |
|---|---|---|---|
| 1 | This PRD (§8, §8.1, §10, §11, §13, §21) referred throughout to `rewrite/` as a subfolder of the repo, but the 2026-08-25 restructure (§14.5) already promoted its contents to the repo root and archived the old pipeline into `old/`. | The filesystem: `ls` at repo root shows `config/`, `data/`, `docs/`, `episodes/`, `host/`, `prompts/`, `scripts/`, `site_src/`, `static/`, `old/`, plus generated `index.html`/`about.html` directly at root, no `rewrite/` directory anywhere. | **Resolved in this pass** - path references updated throughout; §8's tree rewritten to match the live layout. |
| 2 | `README.md` (as of 2026-08-04) was written to a developer-facing spec requiring a tech-stack-with-versions table, exact install commands, and an environment-variables section - directly required by the original §16.1 audit spec. A newer, more specific instruction for this 2026-08-25 pass asked for a general-reader front door instead, explicitly excluding install steps, version numbers, and dependency lists from `README.md`. | The 2026-08-25 instruction, as the most recent and most specific instruction given directly for this exact file, in this exact pass. The install/version content wasn't discarded, it moved into this PRD's Runbook (§21) and Technical Requirements (§22), which already existed and already covered the same ground. | **Resolved in this pass** - `README.md` rewritten to the general-reader spec; §16.1 updated to flag the supersession rather than silently rewriting its own historical requirement text. |
| 3 | `data/manifest.json`'s `status_counts.predictions_extracted` reads `357`, matching `docs/PATCHNOTES.md`'s v0.5.0 entry, but a naive `ls data/predictions \| wc -l` during this audit initially appeared to return `355`. | Re-checked with a set comparison between the manifest's flagged episode ids and the actual filenames on disk: they matched exactly (empty set difference in both directions). The `wc -l` discrepancy was a shell/line-counting artifact, not a real data gap. | **Resolved in this pass, no code/data change needed** - noted here so a future session doesn't re-open this as a real bug. |
| 4 | `scripts/` contains four scripts (`map_processed_episodes.py`, `reconcile_batch1.py`, `dedup_reconciled.py`, `adapt_processed_predictions.py`) that were never documented anywhere in this PRD's pipeline description (§6) or repository structure (§8, prior to this pass). | The filesystem and each script's own docstring (e.g. `adapt_processed_predictions.py`: "Only raw predictions are carried over, NOT predictions_check.json / validation..."). These are one-time migration scripts that ported already-processed predictions from the archived old pipeline into this rewrite's schema. | **Partially resolved in this pass** - listed in §8's tree with a one-line description each; not yet given full dedicated write-ups in §6 (Data Pipeline) since they are migration tooling, not part of the ongoing per-episode pipeline. Flagged as a remaining gap in §31, not silently left undocumented. |
| 5 | `prompts/extract_and_tag.md` and `prompts/validate.md` live in `prompts/`, not `/docs/`. The documentation-consolidation folder rule (§16.1) says any doc file outside `/docs` (other than root `README.md`) must move into `/docs`. | Read both files directly: they are operational instructions Claude follows *during* the pipeline (per-chunk extraction/validation prompts), consumed as input to a process, not reference documentation *about* the project. This PRD (§10) already documents them as pipeline inputs. | **Resolved by explicit scoping decision, not a move** - `prompts/*.md` are treated as pipeline source files, analogous to `scripts/*.py`, and are exempt from the doc-consolidation rule. Recorded here so a future pass doesn't move them reflexively without re-deriving this reasoning. |
| 6 | `old/AGENTS.md`, `old/DEVELOPMENT.md`, `old/README.md`, `old/analysis.md` are documentation-shaped files that exist outside `/docs`. | The Decisions Log (§14.5): `old/` was deliberately archived as historical/reference material from the retired pipeline, explicitly *not* part of the live rewrite this PRD documents. | **Resolved by explicit scoping decision** - treated as archival material outside this audit's scope, left untouched. If `old/` is ever deleted outright (not just archived), these are the only documentation-shaped files in it worth a final glance first, in case anything in them still has forward value (see §32). |

## 30. Browser Testing

This project has no automated/e2e/headless browser test suite as of 2026-08-25 (§22's "known technical debt" already notes there are no automated tests of any kind for the mechanical scripts or site generator). Verification so far has been manual: local `python -m http.server` preview, manual click-through, and a small number of ad hoc scripted checks (e.g. `curl` status checks against the live GitHub Pages URL after deploy).

Because no browser-testing rule existed anywhere in this project's docs before this pass, the following is adopted as the project's default, per this audit's standing instruction to fall back to a stated default when no project-specific rule already exists: **use Microsoft Edge, never Chrome, for any future automated/e2e/headless browser driving** - including ad hoc script or shell invocations that launch a browser - because Chrome is reserved as the maintainer's own live day-to-day browser and should not be driven or occupied by automated tooling. If/when this project adds real browser-driven tests (e.g. a Playwright/Selenium check that `index.html`'s filter controls actually redraw the charts), they must target Edge. The resolved Edge binary path for this environment has not yet been recorded here; the next session that actually runs a headless browser check against this project should locate it (typically `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe` on Windows) and add it to §21's Runbook.

## 31. Risks and Open Questions

**Fragile / not-fully-understood areas:**
- `scripts/fetch_episodes.py`'s layered episode-matching heuristics (episode-code regex → normalized title match → nearest publish date → description link extraction, per §6.1) are the least-tested part of the pipeline on the oldest episodes, where titles are least consistent - `config/youtube_urls_override.json` exists specifically because this heuristic chain doesn't always resolve cleanly, and Phase 4 (§13) notes early episodes need more manual overrides. Changing the matching order or heuristics without re-running `compare_episode_sources.py`'s cross-check risks silently mis-mapping episodes.
- The four migration scripts flagged in §29 (`map_processed_episodes.py`, `reconcile_batch1.py`, `dedup_reconciled.py`, `adapt_processed_predictions.py`) were not individually read function-by-function during this audit pass, only identified and docstring-checked. Their exact transformation logic (how they deduplicated or reconciled the ported predictions) is not fully documented here; treat them as one-time historical tooling, not as scripts to casually re-run, until someone has actually read them in full.
- ~~`generate_site.py` has no data-validation layer~~ **Fixed 2026-08-26.** The freeberg/unknown-role bug fixed on 2026-08-25 (a bad `role: "host"` on a misspelled `who`, bypassing the `permanent_hosts` check in `build_speaker_index()`) was a direct example of this gap causing a real, live, user-visible bug rather than a caught error. `generate_site.py`'s `load_all_data()` now runs `validate_prediction()`/`validate_check_result()` against every record that would actually render as a speaker card (same `qualifies` condition as `build_speaker_index()`: `role == "host"` or `speaker_confidence` high/medium), and raises `DataValidationError` with a full report before generating any HTML if a `who` is missing/placeholder, a `role` isn't `host`/`guest`/`unknown`, a permanent host is tagged `role: "guest"`, a `who` is a near-miss (Levenshtein <=2) of a permanent host slug, or a check `result` isn't one of `right/wrong/ambiguous/inconclusive`. Non-qualifying records (e.g. `who: "unknown-c"` at low confidence, the documented unattributed-line convention from §6.5) are intentionally left unvalidated since they never reach the page. Running the fix against the live archive also caught and fixed a real pre-existing data bug: 8 predictions across E002/E003/E005/E006/E008/E009 had David Sacks tagged `role: "guest"` instead of `"host"` in the raw prediction files (masked in output only because `build_speaker_index()` pre-seeds all four permanent hosts before the episode loop runs).

**Explicit TODO/FIXME/HACK markers:** none found via a repo-wide search as of this pass (excluding `old/`). This project's convention (§28) is to record known gaps in this PRD's prose (Roadmap §19, Risks §12, this section) rather than in inline code comments.

**Work in progress as of 2026-08-26:** none - `git status` is clean and there are no unmerged branches (single-branch `main` history, per §28). The full-archive validation sweep (132/357 episodes validated; three of five 20-episode batches toward a 100-episode sweep complete, two more batches queued) and the `video_id` resolution backlog (45 episodes) are ongoing, tracked work, not uncommitted/stubbed code.

**Open questions for the author:**
1. Should the four migration scripts in §29/this section be deleted now that their one-time job is done, kept as-is for provenance, or given a proper doc write-up in §6? Currently kept as-is, undocumented beyond a one-line description in §8, because deleting them felt premature during a documentation-only pass and nobody has asked for their removal.
2. What is the actual target for the two episodes with a `video_id` but no fetchable captions via any current method (§12, §19)? Currently deferred with no trigger condition; worth deciding whether a manual-transcription fallback is ever worth building for just 2 of 404 episodes.
3. ~~Is `data/manifest.json`'s `generated_at` timestamp expected to be refreshed every time `build_manifest.py` runs?~~ **Resolved 2026-08-26, no code change needed.** `scripts/build_manifest.py` sets `"generated_at": now_iso()` unconditionally on every write (no conditional logic), so it was never a bug - the timestamp that "looked stale" during the 2026-08-25 audit was simply accurate: `build_manifest.py` genuinely hadn't been re-run since 2026-08-05 at that point. It has since been re-run twice as part of this session's validation batches; `generated_at` now correctly reads `2026-08-26T04:02:33Z`. Future sessions can trust this field as load-bearing.

## 32. Deprecation and Removal

No explicit removal-policy rule existed anywhere in this project's docs before this pass, but the Decisions Log (§14.5) already establishes a de facto pattern worth keeping rather than replacing with a generic default: **when retiring a whole pipeline or workflow, archive it into a clearly-named folder (`old/`) rather than deleting it**, preserving it for reference/rollback. This pass adopts that existing pattern and extends it with the file-level distinction below, since §14.5 only covered the folder-level case.

- **Public-facing surface** (needs a redirect/alias/compat note on removal, never a silent delete): the live GitHub Pages URL (https://azqato.github.io/allinpredictions/) and every URL path it serves (`/`, `/about.html`, `/episodes/<id>.html`, `/host/<who>.html`) - a host or episode page that stops existing after a re-generation would 404 any external link pointing at it. There are no published npm/PyPI packages or other exported names this project's code is imported by, so the public surface here is entirely "URLs GitHub Pages currently serves," not code API.
- **Internal, plain-delete surface:** everything else - source files in `scripts/`, `site_src/`, `config/`, `prompts/`, and this project's own `data/` intermediates, even where a filename is reflected in a generated URL (e.g. deleting `site_src/templates/host.html` is an internal change; it only becomes public-facing at the moment `generate_site.py` actually stops emitting `/host/*.html` pages).
- **Deploy boundary:** the line is drawn at what `scripts/generate_site.py` actually writes into the committed, GitHub-Pages-served output (`index.html`, `about.html`, `episodes/`, `host/`, `static/`) plus the live URL itself - everything upstream of that generation step (source templates, data, pipeline scripts) is internal.
- **Compatibility-entry rules:** not yet exercised in this project (no page has ever been removed from the live site), but the standing rule going forward is: a compatibility redirect/stub is permanent once added, is never chained to a second redirect, and is never reused later for unrelated content at the same path.
- **Retired items:** the old pipeline (root-level `scripts/`, `web/`, `config/`, `data/`, `AGENTS.md`, `DEVELOPMENT.md`, `analysis.md`, `requirements.txt`) was retired 2026-08-25 and archived to `old/`, replaced by this rewrite (§14.5). No individual page or URL on the live GitHub Pages site has been retired as of this pass.
- **Changelog integrity:** per `PATCHNOTES.md`'s own stated format (a plain reverse-chronological log), historical entries are never rewritten when something documented in them is later removed - a future removal gets its own new dated entry, the old entry stays as an accurate record of what shipped at the time.

## 33. Working Practice

Concrete instructions for whoever (human or Claude) picks this project up next.

**Before editing, check first / read first:**

| Kind of work | Read this first |
|---|---|
| Changing pipeline logic (`scripts/*.py`) | §6 (Data Pipeline stages) and §28 (Conventions) for the file's stage, then the script's own docstring |
| Changing the data schema (`predictions`/`checks`/`episodes` JSON shape) | §7 (Data Model) - update it in the same change, not after |
| Changing `generate_site.py`, templates, or `app.js` | §9 (Site Generation & Frontend Architecture) and `docs/DESIGN.md` (component patterns, so new UI stays visually consistent) |
| Hand-editing a `data/predictions/*.json` or `data/checks/*.json` file | §7 for the schema, §28 for the "preserve 2-space/compact-array formatting, don't `json.dump` re-serialize the whole file" convention |
| Adding/removing a page, route, or generated file | §8 (Repository Structure) and §32 (Deprecation and Removal) if anything is being removed |
| Anything touching `config/hosts.yaml`'s permanent host roster | §6.4 (speaker attribution) and Decisions Log §14.2 - the four-host roster is a deliberate, load-bearing decision, not an arbitrary list |
| Writing new documentation prose anywhere in the project | §26 (Writing Style) - no em dashes/double dashes; §28 (Conventions) for naming/formatting |

**Never do, and why:**
- Never run a parallel batch of more than 5 concurrent extraction/analysis sub-agents, and never let a sub-agent spawn further sub-agents - the 2026-08-04 incident (Decisions Log §14.6) burned through the usage budget in minutes when this rule was violated once.
- Never re-serialize an entire `data/predictions/*.json` or `data/checks/*.json` file with a generic JSON dump when fixing one field - it destroys the hand-formatted compact-array style and produces a diff many times larger than the actual change (§28); use a targeted string edit instead.
- Never treat `old/` as available for reuse or cleanup without asking first - it's a deliberate archive (§14.5, §32), not dead code.
- Never silently "fix" a documented claim that turns out to be wrong - update the doc, but also record the discrepancy in §29's table, per this project's own documentation policy.

**How to verify a change:**
- Pipeline script change: re-run the specific script against a small `--limit` sample (where supported) and check `data/manifest.json`'s relevant status flag updates correctly.
- Site generation / frontend change: `PYTHONUTF8=1 python scripts/generate_site.py` (the `PYTHONUTF8=1` prefix avoids a `cp1252` `UnicodeEncodeError` on Windows - §21 Runbook), then serve locally with `python -m http.server` and manually click through the affected page(s); for chart/filter changes, specifically exercise the resolved-only checkbox, topic dropdown, and Total/By Year/By Topic toggle together, since their combined state space is larger than any single control (§27).
- Data-quality fix: after editing, re-run `scripts/build_manifest.py` if the fix changes any manifest-tracked status, and regenerate the site to confirm the fix is visible on the affected page(s) before committing.
- **What to update afterward:** add a dated entry to `docs/PATCHNOTES.md` describing the change (§16.1's format), and update this PRD's Roadmap (§19) if the change completes or changes the status of a tracked milestone.

**How this documentation process should be repeated going forward:** the methodology used for this 2026-08-25 audit (§16.1's process list: full codebase crawl first, read every doc in `/docs` in full, diff each against the actual code, merge rather than silently overwrite disagreements into §29's table, then update the four target files) is the standing process for keeping documentation in sync with the codebase after future feature work - not a one-time event. It should be re-run whenever a change is large enough to plausibly make a section of this PRD stale (a new pipeline stage, a schema change, a new page type, a roadmap milestone completing), not on a fixed schedule. A smaller change (a bug fix, a small copy edit) only needs its own `PATCHNOTES.md` entry and, if relevant, a one-line update to the specific PRD section it affects - it does not need a full re-audit.

## 34. Planned Feature: Host vs. Guest Prediction League Table

**Status:** Planned, added to the roadmap 2026-08-27 from Reddit-sourced user feedback (see §19).

**Trigger:** post-MVP, and genuinely buildable now rather than blocked on any future work - unlike §17, this needs no new data-model field. `role: "host" | "guest"` and `who` already exist on every prediction record (§7), so ranking accuracy across both populations is purely an aggregation-and-display feature on top of data the site already has.

**Context:** a recurring piece of feedback (this instance sourced from a Reddit thread asking "what would you like to see on a site that tracks the accuracy of predictions from the All-In Pod hosts") is that the current site (per-host scorecards only, §9) doesn't let a visitor compare the four permanent hosts against the many recurring/one-off guests who also make predictions on the show. A ranked, sortable "league table" spanning both populations is a natural extension of the existing right/wrong/ambiguous/inconclusive scoring the site already computes per speaker.

**Goal:** a single page ranking every host and every guest by prediction accuracy, so a visitor can see at a glance who calls it best, not just how any one individual has done in isolation.

**Design questions to settle before implementation (do not guess - ask):**
- **Accuracy formula:** right / (right + wrong), matching the existing per-host scorecard math, or a variant that folds in `ambiguous` as a partial credit / excludes it entirely. Whatever the existing host scorecards already use (§9) should be the default unless there's a reason to diverge, for consistency.
- **Minimum sample size:** a guest with a 1-for-1 record would rank above every host on raw accuracy despite being statistical noise. Needs an explicit minimum-predictions threshold (e.g. 5+) below which a speaker is either excluded from the ranked table or shown in a separate "not enough data yet" section rather than silently ranked.
- **Guest identity/pages:** today only the four permanent hosts get dedicated `host/*.html` pages (§8, §9); guests appear only inline on episode pages. The league table surfacing guest rows raises whether guests now warrant their own minimal profile page (list of their predictions and record) or whether a table row that deep-links to their prediction cards on the relevant episode pages is sufficient for v1 of this feature.

**Site feature (pending the above):**
- A new page, e.g. `/league.html`, with a sortable table: name, role (host/guest badge), total qualifying predictions, right/wrong/ambiguous/inconclusive counts, accuracy %.
- Likely linked from the home page nav alongside the existing host links.

**Why this belongs in the roadmap and not immediate work:** it's real, well-scoped, and technically ready today, but the design questions above (accuracy formula, minimum-n cutoff, guest page treatment) are product decisions the user should make explicitly rather than have assumed, consistent with this project's "ask, don't guess" norm (§16.3.4) for anything beyond a pure mechanical fix.

## 35. Planned Feature (Long-Term, Deferred): Listener Voting / Feedback Mechanism

**Status:** The full voting mechanism (below) is still explicitly deferred, long-term, no scheduled trigger. **A lighter-weight substitute for general feedback shipped 2026-08-31** at user request: a footer link on every page ("Spot a bad call, a wrong attribution, or have a feature idea? Open an issue on GitHub") pointing to `https://github.com/Azqato/allinpredictions/issues`. This is the "GitHub-Issues-as-votes hack" candidate approach named below, scoped down to plain feedback/bug-report intake rather than per-prediction vote tallying - it answers "how does someone tell us something's wrong" today without the backend/storage decisions the full feature still needs. The repo's Issues tab is public and enabled by default (confirmed via the GitHub API, `has_issues: true`); no repo setting had to change for anyone with a GitHub account to open one.

**Context:** the same feedback thread asked for a way for listeners to vote or otherwise register their own opinion on a prediction's outcome, as a check on (or supplement to) the site's own "house" verdict (`right`/`wrong`/`ambiguous`/`inconclusive`, §7, produced by the validation pipeline in §6).

**Why the full voting feature is a real future feature but not near-term work:** this site is deliberately static and accountless - no backend, no database, no user auth (§1 Goals, §23 Security explicitly states both are "none" by design for a public informational site with zero paid dependencies). A voting mechanism needs somewhere to durably store votes per prediction per (at least pseudonymous) visitor, and cheaply defending that against trivial ballot-stuffing (no accounts means no natural rate-limit) - both are real architecture decisions, not incremental additions to the current `generate_site.py` + embedded-JSON-plus-vanilla-JS model (§9). Candidate approaches (a free-tier serverless function + KV store, a third-party embeddable widget, a GitHub-Issues-as-votes hack) each carry cost, privacy, or reliability trade-offs that should be decided deliberately when this is actually prioritized, not chosen implicitly by whichever is fastest to bolt on.

**Trigger:** none scheduled. Revisit once the core validated-prediction archive (§13 Phase 4, §19) is substantially complete and the league table (§34) has shipped, at which point "how does the house verdict compare to what listeners think" becomes a natural next question rather than a feature bolted onto a still-in-progress data set.

## 36. Competitor Audit: allinscorecard.lovable.app - Feature Gaps

**Status:** Audit complete 2026-08-27, at explicit user request ("index this entire site... identify any core features we are missing and add them to our roadmap"). All 8 items below are **approved for implementation** (user confirmed 2026-08-27: "all of those features are great and i want to implement all of them"), **sequenced after the full ingest-and-validate sweep completes** (§19) - this was an explicit sequencing instruction, not an implicit assumption.

**Context:** [allinscorecard.lovable.app](https://allinscorecard.lovable.app/) is an independent, similarly-scoped site tracking All-In Podcast host predictions. It was indexed (homepage, `/predictions`, `/hosts`, an individual host page, `/episodes`, `/methodology`) to identify features it has that this site (`allinpredictions`) does not. Its stated scope at audit time: 2,741 predictions, 52% overall settled-call success rate, four hosts only (no guest scorecards - a point where this site is already ahead, see §34).

**Gaps identified, ranked by how core they are to a "scorecard" site's value proposition:**

1. **No accuracy/hit-rate percentage computed or displayed anywhere on this site.** This is the single largest gap. Every host page, the host index, and the home page show raw prediction lists and verdict badges, but nowhere does the site roll `right`/`wrong` counts up into a percentage - the core "scorecard" number a visitor most wants (their host cards show e.g. "Friedberg: 57% hit rate, 306 settled calls"). This should be computed the same way §34's planned accuracy formula would compute it (right / (right + wrong), `ambiguous`/`inconclusive` excluded from the denominator pending that same design decision), so this item and §34 should likely be designed together rather than separately.
2. **No sitewide headline stat on the home page** - a single prominent "N predictions checked, X% settled-call accuracy" figure. Their home page leads with this before anything else.
3. **No host leaderboard** ranking the four hosts against each other by accuracy on the hosts index page (`host/index.html` currently lists hosts with no comparative stat at all, per §36 audit). Directly related to gap 1 and to the already-planned §34 league table - once accuracy % exists as a computed value, a simple 4-row host ranking is a near-free addition ahead of or alongside the full host+guest §34 table.
4. **No global full-text search across all predictions.** Their `/predictions` page has a search box ("Looking for a specific call? Search all predictions"). This site has no search anywhere - finding a specific prediction requires knowing which episode or host page to browse to.
5. **No unified "browse all predictions" page independent of episode/host context**, with filter dropdowns by host and by verdict. This site's closest equivalent is the home page's topic-filter + resolved-only toggle (§27) plus per-episode and per-host pages, but there's no single flat list of every prediction across the whole archive with host/verdict filtering.
6. **No "recently settled" feed.** Their home page has a "Just landed" section - the newest graded calls, newest first, regardless of episode date. This site's home page currently surfaces episodes/predictions by year/topic (§27) but not by validation recency.
7. **No curated "high-impact calls" section.** Their home page has a "the calls that mattered" section, calls surfaced via a disclosed weighted notability formula (stakes 35%, specificity 25%, contrarian-positioning 25%, clarity-of-outcome 15%, right/wrong calls only, capped at 2 per host per category). This is a genuine curation/editorial feature this site has no equivalent of.
8. **No per-host verdict-count breakdown block** (e.g. "All: 976 · Right: 284 · Wrong: 295 · Partly right: 88 · Too early: 309") shown compactly on each host's own page. This site's host pages list every individual prediction but never total them up per verdict.

**Not gaps** (already covered or already ahead): an all-episodes index page (`episodes/index.html`), individual episode pages, a topic-filter/resolved-only home page control (§27), and a written methodology explanation (`about.html`) all already exist on this site in some form. Guest scorecards (§34, planned) are a capability the competitor site doesn't have at all - hosts only.

**Why sequenced after ingest-and-validation, not immediate:** the user's own framing when requesting this audit was explicit - identify these as "potential next steps once we finish ingesting and validating every episode" (the 47-episode backlog plus the remaining validation batches, §19). Items 1-3 (accuracy %, headline stat, leaderboard) are cheap, data-only additions that don't strictly require full validation completion, but computing them against a partially-validated archive would produce a percentage that visibly shifts with every subsequent batch - worth flagging as a candidate for earlier execution if the user wants a preview, but not started without that explicit go-ahead.

### 36.1 Re-audit: visual/UX detail pass against fresh screenshots (2026-08-27)

**Status:** documentation only, at explicit user request ("analyze the UI/UX of this website... I want to add these sections to our site... no changes right now just update the roadmap"). Same competitor site as §36 (allinscorecard.lovable.app); this pass adds the specific visual/structural detail visible in five new screenshots (home page hero + host cards, "Just landed" feed, "The leaderboard", "The calls that mattered", "Latest calls" + topic tag cloud) that the original §36 audit described only at the level of "gaps," not layout. These refine and sit on top of the 8 already-approved §36 items - not a reprioritization, just added design fidelity for whenever that work starts.

1. **Home page hero block.** A bold two-line headline framing the whole site as a verdict ("The biggest calls the besties got right - and the ones they blew"), directly above a one-line sitewide stat ("N predictions pulled from the transcripts and checked against what actually happened. X% of the settled ones came true. Click any call for the evidence."). Refines §36 gap 2 with the actual copy pattern - the stat line, not just a number, does double duty as a call-to-action.
2. **Per-host summary cards with curated highlights**, one per host in a 4-up grid on the home page: avatar, colored host name, hit-rate % and settled-call count up top, then a "Biggest calls they nailed" list (top 5, each with date/episode-number/"Read more" link) and a collapsed "And what they got wrong" list (shows 1 by default, "Show 4 more misses" expand), closing with an "All N of their calls ->" link to the full host page. This is richer than §36 gap 3 (leaderboard ranking) - it's a curated best/worst highlight reel living directly on the home page per host, distinct from the sitewide "calls that mattered" section (item 5 below).
3. **"Just landed" feed**: a grid of the most recently *settled* (graded) predictions sitewide, newest first, independent of episode date - refines §36 gap 6 with the exact card anatomy: colored host name, date + episode number, RIGHT/WRONG verdict badge, bold title, one-line snippet, an italicized quote excerpt, topic tag pills, and an "N sources ->" link. A "See all settled ->" link heads the section.
4. **"The leaderboard"**: a ranked (1-4) host list combining §36 gaps 1 and 3 into one component - each row shows a large hit-rate %, a settled/total call count, a horizontal segmented bar chart color-coded by verdict (right / partly right / too early / wrong), and the underlying counts for each segment; badges call out superlatives (e.g. "MOST RIGHT - MOST WRONG"). Notably exposes a 4-state verdict model (right / partly right / too early / wrong) rather than a simple right/wrong split - see the data-model note below.
5. **"The calls that mattered"**: refines §36 gap 7 with the exact layout - two columns, green "Nailed It" and red "Got It Wrong", each numbered 1-4, with a one-line italicized rationale under each entry (e.g. "This was a high-stakes, extremely contrarian call") and a "Called it / Missed it - see the evidence ->" link. A "How the score works" link discloses the weighted notability formula (already captured in §36 gap 7's description).
6. **"Latest calls" section - new item, not in the original §36 list.** Distinct from "Just landed": shows every prediction from the *single most recent episode*, including ungraded ones, with a "Most recent episode graded: [date]" subhead, a "TOO EARLY" badge state for predictions whose timeframe hasn't elapsed, and a "See reasoning ->" link per card (methodology/rationale, not just a verdict). A "See all ->" link heads the section.
7. **Home page "By topic" tag cloud - new item, not in the original §36 list.** A pill-style row of topic tags with live counts (e.g. "politics 899", "economy 886", "government 632"...) sitting directly on the home page as a browse entry point, distinct from this site's existing §27 topic-filter dropdown (which requires opening a control rather than seeing all topics at a glance).
8. **Data-model note for §34/§36 item 1's accuracy-formula design:** the competitor exposes 4 verdict states - right / partly right / too early / wrong - where "too early" cleanly maps to this site's existing `inconclusive`, but "partly right" has no equivalent bucket in this site's current schema (`right` / `wrong` / `ambiguous` / `inconclusive`, per §7). Worth resolving whether `ambiguous` should be renamed/reframed as "partly right" or treated as a distinct fifth state, before the accuracy-percentage and leaderboard work (§34, §36 items 1/3) locks in a denominator formula.

### 36.2 New page request: "The besties, one by one" - unified hosts + guests index, sorted by prediction count (2026-08-27)

**Status:** planned, added at explicit user request alongside the §36.1 re-audit ("i also want a page like this screenshot and add in all of the guests sorted by the amount of predictions they have made"). This targets `host/index.html`, which already exists but currently renders as a plain unstyled list (no avatars, no hit-rate stat, guests in extraction order rather than sorted) per direct inspection.

- **Layout, per the screenshot referenced:** a page headline ("The besties, one by one") plus a one-line explainer, then a card grid - one card per person - each showing an avatar, colored name, hit-rate % + total call count, and a "View ->" link to that person's full page. The screenshot shows only the 4 permanent hosts in this exact layout; extending it downward to include guests is the user's explicit addition.
- **Guest inclusion requirement (user's explicit ask):** every guest currently listed on `host/index.html` (any named guest with at least one confidently-attributed prediction) must appear in this same card format, in its own section below the 4 permanent hosts, **sorted descending by prediction count** - the current page has no defined sort order for guests at all.
- **Relationship to other planned work:** this overlaps with §34 (host vs. guest prediction league table) and §36 item 3 (host leaderboard) - all three want a ranked, accuracy-aware view of hosts/guests - and should likely be designed as one component rather than three, once the accuracy-percentage formula (§36 item 1) is settled. Guest hit-rate display in particular inherits the same "min sample size" open question already flagged in §34 (a guest with 1-2 predictions showing a 0% or 100% hit rate is misleading).
- **Not yet scoped:** avatar sourcing for guests (hosts already have avatar images; most guests currently don't), and whether guests with very low prediction counts (e.g. 1) should be filtered out of this index or shown with a distinct treatment.
- **Working name (ours, not theirs):** "The Roster" (competitor calls this page "The besties, one by one" - per the naming rule in §36.5, this site should not reuse that phrase verbatim).

### 36.3 New page request: unified browse/explore page with search + host/verdict/topic filters (2026-08-27)

**Status:** planned, added at explicit user request ("Explore Page", screenshot of the competitor's `/predictions` page). This directly implements §36 gaps 4 (global full-text search) and 5 (unified browse page with filters) with a concrete UI pattern, rather than the abstract description those gaps originally had.

- **Layout, per the screenshot:** a page headline + one-line explainer, a prominent search box with placeholder examples ("Search predictions - bitcoin, inflation, Tesla...") and a search button, then three rows of pill/chip filters - **Host** (All / each of the 4 hosts), **Verdict** (All / Right / Wrong / Partly Right / Too Early), **Topic** (All / Politics / Economy / Government / Markets / Tech / AI / Health / Venture / Conflict / Science / Climate) - with the active pill in each row highlighted. A live result count ("2,741 predictions") sits above a card grid using the same rich card component as the "Just landed"/"Latest calls" sections (§36.1 items 3 and 6): colored host name, date + episode, verdict badge, title, snippet, italicized quote excerpt, topic pills, "N sources ->"/"See reasoning ->" link.
- **Relationship to existing work:** this supersedes/absorbs the home page's simpler resolved-only-checkbox + single topic-dropdown filter (§27) with a three-dimensional pill-filter model (host x verdict x topic) plus full-text search, on its own dedicated page rather than embedded in the home page. Confirms a single reusable "prediction card" component should be built once and reused across the home page host-highlight sections, "Just landed," "Latest calls," and this browse page, rather than four separate card markups.
- **Nav pattern observed:** the competitor's site header carries a persistent, visually distinct call-to-action button ("Browse," styled apart from the plain-text nav links) that deep-links straight to this page from anywhere on the site - worth adopting as a nav pattern regardless of what this page ends up named.
- **Guest filtering open question:** the competitor's host filter pills are host-only (4 hosts, no guests), consistent with their guest-free scope noted in §36. This site tracks guest scorecards (§34, ahead of the competitor), so this site's equivalent host filter should decide whether to list all guests as filter options too (likely too many to fit as pills - may need a searchable dropdown instead) or keep the pill row hosts-only and let search/topic cover guest discovery.
- **Working name (ours, not theirs):** "The Full Ledger" for the page itself (competitor: "Every prediction" / "Predictions"); nav button labeled "See All Calls" (competitor: "Browse").

### 36.4 New page request: methodology page (2026-08-27)

**Status:** planned, added at explicit user request ("methodology too", screenshot of the competitor's `/methodology` page). This site already has an `about.html` per §36's "not gaps" note, but it does not currently use this numbered-pipeline-plus-verdict-glossary layout - this item is about matching that presentation, not building a page from scratch.

- **Layout, per the screenshot:** an eyebrow label ("Methodology"), a bold two-line headline framing the page as a trust/transparency pitch ("Transcripts in. Evidence-backed verdicts out."), and a one-paragraph subhead making the audit-me case directly ("This site is built by a pipeline - and a pipeline can be audited. Here's exactly what it does."). Below that, a numbered list (01-05) of pipeline stages, each a bold short title plus a one-line plain-English explainer: capture the transcript with timestamps; have a model pull out genuinely falsifiable forecasts (not opinions/jokes/hot takes); attribute each forecast to a speaker; have a second model check it against public reporting and write a sourced verdict; publish the full reasoning and links so any grade can be audited. This maps directly onto this site's own §6 pipeline stages (episode discovery through validation) - the opportunity here is presentation (numbered, punchy, visitor-facing copy), not new pipeline work.
- **"The four verdicts" glossary section:** a definition list below the pipeline steps, one row per verdict state with a colored dot, bold name, and one-line plain-English description (e.g. "Right - Reality matched the call," "Wrong - Reality went the other way," "Partly right - Half landed, half didn't"). Directly reinforces the §36.1 item 8 data-model note about reconciling this site's `ambiguous`/`inconclusive` states with a "partly right"/"too early" framing - this glossary is exactly the artifact that forces that decision to get made and documented.
- **Notable point of difference to preserve, not copy:** the competitor's methodology explicitly states "guest predictions are excluded; only the four regulars are scored" - this site already tracks guest scorecards (§34) and should not adopt this limitation; the equivalent copy on this site's own methodology page should describe attribution running host *and* guest speakers alike, as a stated point of difference from the competitor.
- **Working name (ours, not theirs):** keep "Methodology" as the nav label (generic/functional, not a brand phrase worth avoiding), but write an original headline and step names rather than reusing "Transcripts in. Evidence-backed verdicts out." or the exact five step titles verbatim (see §36.5).

### 36.5 Naming convention for all §36.1-36.4 sections (2026-08-27)

**Status:** standing rule, added at explicit user request ("for every feature, i want to rename it to something slightly different for each section/part of the ui/ux"). Every section/page inspired by the competitor site in §36.1-36.4 gets its own distinct name on this site rather than reusing the competitor's copy verbatim - matching functionality and layout intent is the goal, not matching brand language. Working names proposed so far (to be finalized at implementation time, not locked in now):

| Competitor's name | This site's working name |
|---|---|
| "Just landed" | "Fresh Verdicts" |
| "The leaderboard" | "The Standings" |
| "The calls that mattered" | "The Big Ones" |
| "Latest calls" | "This Episode's Calls" |
| "By topic" (tag cloud) | "Topic Index" |
| "The besties, one by one" | "The Roster" |
| "Every prediction" / "Predictions" (browse page) | "The Full Ledger" |
| "Browse" (nav CTA button) | "See All Calls" |
| Per-host "Biggest calls they nailed" / "And what they got wrong" | "Signature Calls" / "The Misses" |
| "Methodology" headline "Transcripts in. Evidence-backed verdicts out." | original headline, TBD at implementation |
