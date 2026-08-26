# PRD: All-In Predictions — Free-Tooling / Claude-Native Rewrite

## 0. Summary

Rebuild the "All-In Predictions" project from scratch in `rewrite/`, replacing every piece of the original stack that required a paid API (OpenAI, xAI/Grok, Speechmatics/Deepgram/AssemblyAI, Next.js/Node build+hosting) with:

1. **Free, no-API-key tooling** for transcript acquisition (YouTube's own captions, not downloaded audio + paid ASR).
2. **Claude (this agent, running in Claude Code)** as the entire "intelligence" layer — prediction extraction, speaker attribution, web-search validation, and topic tagging — instead of calling OpenAI/xAI APIs from a script.
3. **Vanilla HTML/CSS/JS**, statically generated (no Next.js/React/Node build pipeline), deployable directly on **GitHub Pages** with zero build infrastructure beyond a Python script Claude runs locally.

The output is the same in spirit — a browsable site scoring the All-In hosts' (Jason, Chamath, Sacks, Friedberg) predictions as right/wrong/ambiguous/inconclusive, with quotes, timestamps, YouTube deep-links, and cited explanations — but the entire toolchain is free to operate indefinitely and every "AI" step is something *I* (Claude) do directly, rather than code that calls a billed model API.

---

## 1. Goals

- **G1 — Zero paid dependencies.** No OpenAI/xAI/Speechmatics/Deepgram/AssemblyAI API keys anywhere. Every external call is either a free public endpoint (YouTube captions, podcast RSS) or done by Claude itself.
- **G2 — Claude is the runtime, not just the builder.** The pipeline's "LLM steps" (extraction, attribution, validation, tagging) are executed by Claude Code — either interactively in a session, or via scripted headless `claude -p` invocations — not by SDK calls to a third-party model API from Python.
- **G3 — No audio downloads.** Skip MP3 archiving and ASR entirely. Pull transcripts straight from YouTube's caption/subtitle track (auto-generated or manual) for each episode's video.
- **G4 — Vanilla static frontend.** Plain HTML/CSS/JS, no npm install, no bundler, no framework runtime in the browser. Must run correctly when served as flat files by GitHub Pages.
- **G5 — Same core value proposition.** Per-host accuracy scorecards (donut/bar charts), episode-by-episode prediction lists, individual prediction permalinks, YouTube timestamp deep-links, topic tagging/filtering, and cited validation explanations.
- **G6 — Incremental & idempotent.** Re-running the pipeline on the full archive should skip episodes already processed; adding new episodes should be a cheap, mostly-automatic update.
- **G7 — Transparent about accuracy tradeoffs.** Because we're dropping voice-embedding speaker diarization (which required downloaded audio), speaker attribution is inherently less precise. The product must surface this honestly (confidence/unknown states) rather than silently guessing.
- **G8 — Guests are first-class, not an afterthought.** Any named speaker (host or guest) whose predictions can be attributed with reasonable confidence gets their own scorecard, not just the four permanent hosts. See §6.4 and the Decisions Log (§14).
- **G9 — Prove attribution quality before scaling it.** Contextual (audio-free) speaker attribution is unproven at this project's outset. It must be validated on a small sample and explicitly signed off before being run across the full archive — see §6.4's validation gate and Phase 2 in §13.

## 2. Non-Goals

- Pixel-parity with the old Next.js UI. We're free to simplify/restyle as long as the core views exist.
- Real-time/dynamic backend. This remains a fully static site — all data is pre-baked into JSON/HTML at "build" time (a Claude-run script), not fetched from a live server at request time.
- Perfect speaker diarization. We are explicitly trading some attribution precision for zero cost/zero audio downloads (see §6.4 and §12).
- Multi-podcast generalization in v1 (the original project mentions this as a stretch goal too) — we'll keep the architecture podcast-agnostic where cheap to do so, but won't build a full plugin system now.

## 3. Comparison to Original Project

| Concern | Original (`allinpredictions`) | Rewrite (`rewrite/`) |
|---|---|---|
| Episode discovery | Libsyn RSS + yt-dlp YouTube playlist match | Same idea, kept (both free) |
| Audio | Downloaded full MP3 archive | **Not downloaded at all** |
| Transcription | Paid ASR (Speechmatics primary; Deepgram/OpenAI/AssemblyAI alternates) | **Free YouTube captions** (`youtube-transcript-api` / `yt-dlp --write-auto-sub`) |
| Speaker diarization | SpeechBrain ECAPA-TDNN voice embeddings, cosine similarity vs. canonical host voiceprints | **Claude contextual attribution** from caption text only (no audio) — lower precision, explicitly flagged |
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
                     │  rewrite/ root (index.html,│ ──► GitHub Pages
                     │  episodes/, host/, static/)│
                     └──────────────────────────┘
```

Two clean layers:
- **Mechanical layer** (deterministic Python scripts, no LLM): episode discovery, caption fetching, chunking, JSON→HTML site generation. Cheap to re-run, fully scriptable, no Claude involvement needed once written.
- **Judgment layer** (Claude Code): everything requiring reading comprehension, world knowledge, or web research. This is the part that satisfies "should be ran/updated entirely in Claude" — there is no OpenAI/xAI SDK call anywhere; Claude Code *is* the model doing the work, using its native tools (Read/Write/WebSearch/WebFetch).

## 5. Tooling & Cost Model

| Task | Tool | Cost | Auth needed? |
|---|---|---|---|
| Episode metadata | `yt-dlp -J --flat-playlist` against `@allin/videos`, or podcast RSS | Free | No |
| Captions | `youtube-transcript-api` (pip) — preferred; falls back to `yt-dlp --write-auto-sub --skip-download` | Free | No |
| Prediction extraction | Claude Code (this agent) | Free¹ | No (uses existing Claude Code session/subscription) |
| Speaker attribution | Claude Code, contextual inference from caption text | Free¹ | No |
| Validation research | Claude Code `WebSearch` / `WebFetch` tools | Free¹ | No |
| Topic tagging | Claude Code | Free¹ | No |
| Site build | Python + Jinja2 (or hand-rolled string templates to avoid even that dependency) | Free | No |
| Hosting | GitHub Pages | Free | GitHub account (already have) |

¹ "Free" relative to the old pipeline's per-token OpenAI/xAI/ASR billing — this work consumes your existing Claude usage instead of a separate metered API. Large archives (300+ episodes) still take real session time/turns, so batching and incremental runs matter (see §10).

## 6. Data Pipeline — Detailed Stages

### 6.1 Episode discovery
- Script: `scripts/fetch_episodes.py`.
- Pulls the All-In RSS feed (title, publish date, description, episode code parsed via regex) — reused logic from the original `all_in_downloader.py`, minus the MP3 download step.
- Pulls the YouTube channel's full upload list via `yt-dlp -J --flat-playlist` (metadata only, **no video/audio download**) and matches each RSS episode to a `video_id` using the same layered heuristics as the original (episode-code regex → normalized title match → nearest publish date → description link extraction). This gives us the `video_id` needed to fetch captions.
- **Canonical ordering/reference source:** [allin.com/episodes](https://allin.com/episodes) is the official episode index and is the source of truth for episode numbering and order. It lists episodes reverse-chronologically with a numeric `Episode #NNN`, publish date, title/description, and links out to YouTube/Apple/Spotify/X. It appears to run on "PodcastAI" infra; no public JSON/RSS feed was found behind it during inspection, so it's used as a **human-checkable reference for correct episode numbering/order**, not as a scraped data source — our own `episode_code` (parsed from RSS/YouTube titles, e.g. `E211`) must be reconciled against allin.com's numbering so the site's episode list/navigation matches the canonical order. Every episode transcript and prediction file in this rewrite should be ordered/numbered consistent with allin.com/episodes.
- Output: `data/episodes.json` — one row per episode: `{episode_id, title, published, published_iso, episode_code, video_id, youtube_url}`, with `episode_code` validated against allin.com/episodes numbering where possible.
- **Independent derivation + cross-check (per Decisions Log §14.4):** the rewrite derives its own episode↔YouTube matching from scratch (RSS + `yt-dlp` + allin.com/episodes numbering), rather than seeding from the old repo's output. Once derived, a comparison script (`scripts/compare_episode_sources.py`) diffs the rewrite's `data/episodes.json` against the old repo's `data/processed/all_in_episodes.json` (`video_id`/`youtube_url` per `episode_id`) and reports: episodes matched identically, episodes where the two disagree, and episodes either source is missing. This serves two purposes — a free correctness check for the rewrite's independent matching logic (using the old, already-debugged results as a reference oracle), and QA evidence supporting the eventual decision to fully replace the old pipeline (§14.5) once the rewrite is proven at least as accurate.
- Disagreements are resolved by hand against allin.com/episodes (the canonical numbering source) and logged to `data/episode_source_diff.json` for traceability — this diff report is expected input to the Phase-6+ decision on retiring the old pipeline.

### 6.2 Transcript acquisition
- Script: `scripts/fetch_transcripts.py`.
- For each episode's `video_id`, fetch the caption track via `youtube_transcript_api.YouTubeTranscriptApi.get_transcript(video_id)` (prefers manually-created captions if present, otherwise auto-generated). No API key, no rate-limit auth — it's an unofficial wrapper around YouTube's public timedtext endpoint.
- Fallback if that library is blocked/unavailable for a given video: `yt-dlp --write-auto-sub --sub-lang en --skip-download --convert-subs srt`, then parse the SRT/VTT locally.
- Output per episode: `data/transcripts/<episode_id>.json` — list of `{text, start_seconds, duration_seconds}` caption cues, essentially the original's `segments.json` but **without a `speaker_label` field** (this is the key structural difference from the old pipeline — see §6.4).
- Skips episodes whose captions are unavailable/disabled entirely (logs to `data/transcripts/_missing.json` for visibility; these episodes simply won't have predictions).

### 6.3 Transcript normalization & chunking
- Script: `scripts/prepare_chunks.py` (pure Python, deterministic — ports the original's `build_lines`/`chunk_lines` logic).
- Merges consecutive caption cues into readable lines, stamps each with `hh:mm:ss` (derived from `start_seconds`), and splits into ~15–25k character chunks with small line overlap between chunks (smaller than the original's 60k, because Claude Code's context budget per turn is the constraint here rather than an API's context window, and per-chunk analysis quality is better with smaller windows).
- Output: `data/chunks/<episode_id>/chunk_<n>.txt` — plain text, ready for Claude to read directly.

### 6.4 Speaker attribution (the key architecture change)
This is the hardest problem introduced by dropping audio/ASR diarization, and deserves explicit design:

**Why it's hard now:** YouTube captions (manual or auto-generated) do not include speaker labels. The original pipeline solved "who said this" with voice embeddings computed from downloaded audio; we have no audio.

**Approach — contextual attribution by Claude:**
- When Claude extracts a prediction from a chunk, it also assigns a `who` field using in-text contextual cues available in the transcript alone:
  - Direct address / reply patterns ("Jason, I think...", "No, Chamath, that's wrong because...").
  - Self-reference and recurring personal context (e.g., a speaker referencing their own fund/SPACs → likely Chamath; referencing their agency/politics commentary → likely Sacks; referencing biotech/Ohalo/agriculture → likely Friedberg; hosting/sponsor-read cadence → likely Jason).
  - Structural cues: the show's intro sequence and recurring bits (e.g., "Besties are back") sometimes name who's present that episode.
  - Cross-chunk consistency: Claude tracks a running best-guess "who's talking" state across the transcript rather than judging each line in isolation.
- Each prediction gets a `who` field — **not a fixed enum**. Per the Decisions Log (§14.2), guests get their own scorecards, so `who` is any identified speaker name Claude can attribute with reasonable confidence: the four canonical hosts (`jason|chamath|sacks|friedberg`), or a normalized guest identifier derived from the episode's title/description (e.g. `rep-swalwell`, `tom-emmer`) when the transcript context and episode metadata together make the attribution reasonably clear. Falls back to `unknown` when no attribution is possible.
- A `role` field (`host|guest`) accompanies `who` so the UI can distinguish "the four permanent hosts" from "everyone else" in navigation/listing without re-deriving it from the name.
- Each prediction also gets a `speaker_confidence` (`high|medium|low`).
- **Product decision:** a speaker (host or guest) only gets their own scorecard page if they have at least one prediction at `high` or `medium` confidence; `low`-confidence and `unknown` predictions are still recorded in the data (for transparency/debugging), still shown on their episode's page, but excluded from *any* accuracy scorecard — mirroring how the original excluded unmatched `Speaker X` labels, just with a visible confidence gradient instead of a hard embedding threshold, and extended to any named speaker rather than only the four hosts.
- Guest scorecards will naturally have small sample sizes (often one episode's worth of predictions) — the UI should show the underlying count prominently (e.g. "3 predictions") next to any guest's accuracy percentage so a thin sample isn't presented with false confidence.
- This is **strictly lower precision** than voice-embedding matching and must be disclosed in the site's footer/about page, same spirit as the original's existing disclaimer.
- **Validation gate — required before scaling (per Decisions Log §14.1):** contextual attribution must be proven on a small sample before it's trusted for the full archive. Concretely, as part of Phase 2 (§13): run extraction+attribution on the 3–5 sample episodes, then hand-check every attributed prediction's `who`/`speaker_confidence` against a human read of the actual transcript/video. Compute a rough precision estimate (correct attributions ÷ total attributed at `high`/`medium` confidence). This checkpoint must be explicitly reviewed and signed off (by the user) before Phase 4 (full-archive scale-out) begins. If precision is unacceptably low, the fallback is the local-diarization alternative below — not silently shipping a low-quality attribution scheme across 300+ episodes.
- **Documented alternative for later** (triggered only if the validation gate above fails): a v2 could add a *local, free* diarization pass using an open-source model (e.g., `pyannote.audio` community pipelines) run against a temporarily-downloaded/streamed audio snippet — this would reintroduce a limited, on-demand audio fetch (not a full archive download) solely to get a diarization *label sequence* (A/B/C/D) that we then align to caption timestamps, without ever needing paid ASR.

### 6.5 Prediction extraction
- Claude reads each chunk (from §6.3) directly (via the `Read` tool) and produces structured prediction entries following the same substantive rubric as the original prompt: concrete, falsifiable, time-bound claims only; skip vague futurism.
- For each prediction: `{id, who, speaker_confidence, quote, timestamp, prediction}` — `id` stays deterministic (`<who>-<timestamp>`, or `unknown-<timestamp>` when unattributed) so re-runs are stable/dedupeable.
- Claude writes results with the `Write`/`Edit` tool straight to `data/predictions/<episode_id>.json` — no intermediate API round-trip, no JSON-mode SDK object; Claude simply authors the JSON file per the schema in §7.
- Batching: for a full-archive run, a driver script (`scripts/run_extraction.sh` or a `/extract-episode` slash command) iterates episodes and either (a) is executed turn-by-turn interactively by Claude in a session, or (b) shells out to `claude -p "<extraction prompt> <chunk path>" --output-format json` per chunk for unattended batch runs. Both paths are documented so the "who runs it" question always resolves to "Claude," just with different levels of interactivity.

### 6.6 Prediction validation
- For each extracted prediction, Claude uses its `WebSearch` (and `WebFetch` for specific promising sources) tools to research whether it came true, exactly mirroring the original's `result ∈ {right, wrong, ambiguous, inconclusive}` + cited `explanation` design — just executed by Claude directly instead of via OpenAI's hosted `web_search` tool.
- Output: `data/checks/<episode_id>.json`, `{id, result, explanation, sources: [{title, url}]}`.
- No second "Grok cross-check" model in v1 (that existed in the original purely as a second *paid* opinion) — Claude's own single validation pass is the default. If we want a second opinion later without paying for another model API, we could re-run validation in a fresh Claude session and diff the two verdicts — documented as a possible Phase 2 addition, not required now.
- Idempotency: skip predictions that already have a `checks` entry unless explicitly forced (same `--force` convention as the original).

### 6.7 Topic tagging
- Reuses the original's fixed tag enum (`politics, government, conflict, venture, tech, ai, markets, economy, health, climate, science`) for continuity with existing mental model, adjustable via a config file (`config/tags.json`).
- Claude assigns 0+ tags per prediction directly while doing extraction (fold into §6.5 rather than a separate pass, since Claude is already reading the full context) — simplifies the pipeline from 3 Claude passes (extract/validate/tag) in the original design down to 2 (extract+tag, then validate).

### 6.8 Incremental & idempotent updates
- Every stage checks for existing output files and skips unless `--force`/explicitly asked to redo — same discipline as the original scripts.
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

## 8. Repository Structure (`rewrite/`)

```
rewrite/
├── README.md                  ← developer-facing quickstart (root only, per §16.1's folder standard)
├── docs/
│   ├── PRD.md                  ← this document
│   ├── DESIGN.md                ← visual/UX system: colors, type, spacing, breakpoints, components
│   └── PATCHNOTES.md            ← dated changelog
├── requirements.txt           ← youtube-transcript-api, yt-dlp, jinja2, pyyaml (all free/OSS)
├── config/
│   ├── hosts.yaml              ← canonical *permanent* host roster (jason/chamath/sacks/friedberg) + attribution hints (bio keywords, recurring topics). Guests are NOT listed here — they're derived per-episode from title/description + transcript context (§6.4) and don't need config entries.
│   └── tags.json                ← allowed topic tag enum
├── data/
│   ├── episodes.json
│   ├── manifest.json
│   ├── transcripts/<episode_id>.json
│   ├── chunks/<episode_id>/chunk_*.txt
│   ├── predictions/<episode_id>.json
│   └── checks/<episode_id>.json
├── scripts/
│   ├── fetch_episodes.py
│   ├── fetch_transcripts.py
│   ├── prepare_chunks.py
│   ├── build_manifest.py
│   └── generate_site.py        ← deterministic templater, no LLM calls
├── prompts/
│   ├── extract_and_tag.md      ← the instruction Claude follows per chunk
│   └── validate.md             ← the instruction Claude follows per prediction
├── site_src/
│   ├── templates/               ← Jinja2 templates (or plain .html w/ {{ }} placeholders)
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── episode.html
│   │   └── host.html
│   └── static/
│       ├── style.css
│       └── app.js               ← vanilla JS: chart rendering + filter interactivity
│
│   BUILD OUTPUT (generated directly into rewrite/ root, not a subfolder —
│   see §8.1 for why):
├── index.html
├── about.html
├── episodes/*.html
├── host/*.html
└── static/                      ← copied from site_src/static/ at build time
```

The generated site files (`index.html`, `about.html`, `episodes/`, `host/`, `static/`) are git-tracked (unlike the original's gitignored `data/`) since GitHub Pages needs the built output committed (no CI build step in v1 — see §11). `scripts/generate_site.py` only ever cleans/rewrites those specific generated paths on rebuild — it never touches `scripts/`, `data/`, `config/`, `site_src/`, `prompts/`, or documentation files, even though they all live alongside the generated output at the same directory level.

### 8.1 Why the site is generated into `rewrite/` root, not a `docs/` subfolder (decided 2026-08-04)
GitHub Pages only supports two publish locations: the repo root, or a `/docs` folder on the branch. The original plan (§9, §11 below) used `rewrite/docs/` as that publish folder. That was changed for two reasons:
1. **Matches the eventual final structure now, not just at cutover time.** Per the Decisions Log (§14.5), `rewrite/` is intended to eventually *become* the repo root when the old pipeline is retired. Generating the site directly into `rewrite/` root means the working directory already looks like what the final repo root will look like — `index.html` sits where it will always sit — rather than needing a path shuffle at cutover.
2. **Frees up the `docs/` name for actual documentation.** The documentation-consolidation standard from §16.1 requires `/docs/PRD.md`, `/docs/DESIGN.md`, `/docs/PATCHNOTES.md` at the repo root. That directly collides with GitHub Pages' `/docs`-as-site-output convention — the same folder can't cleanly be both "the published website" and "the project's markdown documentation." Generating the site into root instead of `rewrite/docs/` resolves this: `docs/` is reserved exclusively for documentation, and GitHub Pages will eventually be configured as **Deploy from branch → main / (root)** rather than `/docs` (see §11).

This does mean generated site files and source directories (`scripts/`, `data/`, `config/`, `site_src/`, `prompts/`) sit side by side at the same level in `rewrite/`. That's intentional and matches how many static sites are structured when deployed from repo root; the generator's targeted cleanup (only ever touching its known generated paths, never a blanket wipe of the output directory) is what keeps this safe.

## 9. Site Generation & Frontend Architecture

### 9.1 Why static-generate instead of a client-side SPA
A pure client-rendered single-page app (fetch JSON, route via `#hash`, render with vanilla JS) is possible but sacrifices real URLs, crawlability, and simplicity. Instead we pre-render actual `.html` files per episode/host at build time using a small Python templater (Jinja2 is free/OSS and doesn't require Node), then layer a *little* vanilla JS on top purely for client-side interactivity (chart filter toggles). This is the closest vanilla-tooling analog to what Next.js's `output: 'export'` was doing, minus React/Node.

### 9.2 Pages
- `/index.html` — host scorecards (charts) + recent episodes, same as original home page.
- `/episodes/index.html` — full episode list.
- `/episodes/<episode_id>.html` — one episode's predictions.
- `/host/<who>.html` — one speaker's full prediction history + scorecard. Generated for **any** speaker (host or guest) with ≥1 prediction at `high`/`medium` confidence, not just the four permanent hosts (per Decisions Log §14.2) — so the set of host pages is dynamic, driven by `data/predictions/*.json`, not a hardcoded list of four.
- `/host/index.html` — directory of all speaker pages, visually separating the four permanent hosts from guests (using the `role` field) so the homepage/nav isn't cluttered with dozens of one-episode guest scorecards.
- `/about.html` — static about/disclaimer page.
- Prediction "permalinks" become simple in-page anchors (`/episodes/<id>.html#<pred_id>`) rather than a separate route — removes the need for the original's base62 ID encoding scheme entirely (that existed to make Next.js dynamic-route URLs; a static anchor doesn't need it).

### 9.3 Charts — vanilla, no Chart.js
- Because we have no bundler and don't want a CDN dependency (keeps the site fully offline-buildable and free of third-party script risk), charts are hand-rolled:
  - **Donut/accuracy chart**: pre-computed percentages rendered as an inline `<svg>` with `stroke-dasharray` arcs, generated at build time by the Python templater (deterministic, no client JS needed for the default view).
  - **By-year / by-topic stacked bars**: same idea — SVG `<rect>`s sized server-side (at build time) for the default filter state.
  - **Client-side interactivity** (the "Resolved only" checkbox, topic dropdown, Year/Topic toggle): a small `app.js` (~150-300 lines, no dependencies) holds the *already-computed* aggregate stats as an inline `<script type="application/json">` blob per page (small — just counts, not full prediction text) and redraws the SVG on filter change using plain DOM APIs. This matches the original `HostCharts.tsx` behavior without React.

### 9.4 Styling
- Hand-written `style.css`, dark theme carried over from the original (`#080d0b` background, white text) for visual continuity. No Tailwind (would require a build step); plain CSS custom properties for the small color palette (right/wrong/ambiguous/inconclusive colors) instead.

### 9.5 YouTube deep links
- Same UX as original: prediction cards link to `https://www.youtube.com/watch?v=<video_id>&t=<seconds>`, with a one-time `localStorage`-gated disclaimer modal (small vanilla JS, ports directly from the original's `YoutubeLink.tsx` logic without React).

## 10. Automation Workflow — "How Claude Runs This"

Two supported modes, both documented in `rewrite/README.md`:

**Interactive (recommended for initial buildout / spot fixes):**
1. User runs the mechanical scripts (§6.1–6.3) via Claude Code's Bash tool to produce `data/chunks/*`.
2. Claude reads chunks with `Read`, extracts/tags predictions with `Write`/`Edit` following `prompts/extract_and_tag.md`, validates with `WebSearch`/`WebFetch` following `prompts/validate.md` — all within the normal conversational flow, a handful of episodes per turn.
3. Claude runs `scripts/generate_site.py` to rebuild the site (generated directly into `rewrite/` root — see §8.1).
4. Commit + push (user confirms, per this session's standing git-safety norms).

**Headless/batch (for scaling to the full ~300+ episode archive without manual back-and-forth):**
- A driver script loops over pending episodes/chunks and invokes `claude -p "$(cat prompts/extract_and_tag.md) $(cat chunk.txt)" --output-format json` (or the equivalent Claude Code headless invocation), writing each response to the right `data/predictions/<id>.json` path. Same for validation, with `WebSearch`/`WebFetch` tool access granted to the headless invocation.
- This keeps "the LLM doing the work" strictly as Claude in every case — never a third-party model API — while still allowing unattended, scriptable batch runs.
- Concurrency/pacing: headless batch runs should throttle themselves (small delays / modest parallelism) — unlike the original's `ThreadPoolExecutor(max_workers=10)` against a metered API, we're bound by session/turn economics, not $ per call, so the right default is "a handful of episodes per invocation," not maximum parallelism.

**Update cadence:** run the discovery step periodically (manually, e.g. weekly) to pick up new episodes; the manifest-driven incremental design (§6.8) means this is a small, bounded amount of new Claude work each time, not a full re-run.

## 11. Deployment (GitHub Pages)

- v1: commit the generated site files (`index.html`, `about.html`, `episodes/`, `host/`, `static/`) directly at the repo's root on the default branch; enable **GitHub Pages → Deploy from branch → `main` / `(root)`** in repo settings (see §8.1 for why root instead of `/docs`). No CI required — Claude (or the user) runs `generate_site.py` locally/in-session and commits the output alongside the source data.
- Custom domain: optional, via a `CNAME` file at the repo root if desired later (not required for v1).
- Phase 2 (optional): a GitHub Action that runs the mechanical scripts + `generate_site.py` on a schedule and opens a PR — deliberately **not** in v1 scope, because the "intelligent" pipeline stages must run through Claude, and CI can't invoke this coding-assistant session. Automating *only* the deterministic regeneration (not the analysis) could still be a small later add-on.

## 12. Risks & Limitations

| Risk | Impact | Mitigation |
|---|---|---|
| No true speaker diarization → attribution errors | Wrong host credited/blamed for a prediction | `speaker_confidence` field; low-confidence excluded from host stats; clear disclaimer; Phase 2 optional local diarization (§6.4) |
| YouTube auto-captions have transcription errors (no human review, unlike Speechmatics) | Garbled quotes, missed predictions, wrong timestamps | Prefer manually-created captions when available; treat quotes as "best effort," same disclaimer language as original |
| `youtube-transcript-api` can be blocked/rate-limited by YouTube without warning (it's an unofficial API) | Pipeline stalls on caption fetch | `yt-dlp --write-auto-sub` fallback (different code path, same source data); backoff/retry; treat missing captions as a skip, not a hard failure |
| Claude session/turn cost of processing 300+ episodes | Slow full-archive buildout | Incremental manifest-driven processing (§6.8); headless batch mode (§10); process newest/most-relevant episodes first |
| Single-model validation (no Grok cross-check) | Slightly less error-correction on validation verdicts than original | Optional future "re-validate in a fresh session and diff" pattern; not required for v1 |
| Hand-rolled SVG charts vs. Chart.js | More code to write/maintain ourselves | Scope tightly to the 3 chart types actually used; keep `app.js` small and dependency-free by design |
| No SSR analytics/OG image pipeline parity | Minor — original had Next `Metadata`/OG image | Port `<meta>` tags + a static `og.png` by hand; trivial in plain HTML |

## 13. Phased Implementation Plan

**Phase 0 — Scaffolding**
- Create `rewrite/` structure per §8, `requirements.txt`, `config/hosts.yaml`, `config/tags.json`, empty `prompts/*.md`.

**Phase 1 — Mechanical pipeline (deterministic scripts, no Claude analysis yet)**
- `fetch_episodes.py`, `fetch_transcripts.py`, `prepare_chunks.py`, `build_manifest.py`.
- Validate against a small sample (3–5 episodes) end-to-end: episode list → captions → chunks on disk, correct and readable.

**Phase 2 — Claude analysis loop, small batch**
- Write `prompts/extract_and_tag.md` and `prompts/validate.md`.
- Run extraction + validation interactively on the same 3–5 sample episodes; hand-check quality of speaker attribution, prediction quality, and validation verdicts before scaling up.
- Iterate on the attribution heuristics (§6.4) and prompts based on real output.

**Phase 3 — Static site generator**
- Build `generate_site.py` + Jinja2 templates + `style.css` + `app.js` against the Phase 2 sample data; get the home page charts, episode pages, and host pages fully working locally (generated directly into `rewrite/` root — open `rewrite/index.html` directly in a browser).

**Phase 4 — Scale to full archive**
- Run the pipeline (interactive and/or headless batch) across all discovered episodes, respecting the manifest for incremental resume.
- Regenerate the full site.
- **Batching process (confirmed 2026-08-04):** two separate, sequential sweeps rather than interleaving extraction and validation per episode:
  1. **Extraction sweep, chronological, oldest-first.** Starting from episode 1 (the earliest episode in the archive), process 10 episodes at a time in publish order, extracting + attributing + tagging predictions for each (per `prompts/extract_and_tag.md`) until every episode in the archive has a `data/predictions/<episode_id>.json`. Batch size is a target, not a hard rule — dense episodes (the annual "predictions" specials) take meaningfully longer per episode than a typical week's episode or a retrospective "Bestie Awards" show, so a batch may need to flex smaller when it lands on several dense episodes in a row.
  2. **Validation sweep, ascending by prediction count, fewest-first (updated 2026-08-04).** Only after the full extraction sweep is complete, go back through and validate 10 predictions at a time (per `prompts/validate.md`), selecting whole episodes ordered by ascending `count` of predictions in `data/predictions/<episode_id>.json` (episodes with the fewest predictions first) rather than by publish date, so a "batch" clears complete episodes quickly instead of leaving many episodes partially validated. Episodes with equal prediction counts are tie-broken oldest-first, preserving the original rationale that older predictions have had more time to resolve and are more likely to produce a real `right`/`wrong` verdict rather than `inconclusive`. (Superseded rule, kept for context: earlier sessions used strict chronological oldest-first; that produced very uneven batch sizes, since some early episodes like live election-night specials have 50+ predictions each.)
  - Rationale for two separate sweeps instead of one combined pass: it keeps each pass focused on one kind of judgment call (attribution vs. fact-checking), makes progress independently trackable via `data/manifest.json`'s `predictions_extracted` and `validated` flags, and means a full-archive extraction pass doesn't stall waiting on web-search-heavy validation work.
  - Expect early episodes to need more manual entries in `config/youtube_urls_override.json` — the automatic episode-code/title/nearest-date matching (§6.1) tends to be more reliable on episodes with consistent "E211"-style numbering in the title, which is less consistent in the earliest parts of the archive.
  - This sweep-based process is the standing plan for ongoing archive maintenance too, not just the initial backfill: "run it every once in a while" to pick up new episodes and steadily work down the validation backlog, rather than a one-time push.

**Phase 5 — Deploy**
- Push the generated site (now at repo root after the §14.5 restructure) to GitHub, enable Pages (Deploy from branch → root, per §8.1/§11), verify the live URL end-to-end (charts render, links work, YouTube deep-links resolve, mobile layout is usable).
- **Sequencing note (updated 2026-08-25, see §19):** Deploy now runs *early*, right after the repo restructure/full site replacement (§14.5) and the pre-launch parity pass (§27), as an MVP launch, not as the final step. The full-archive validation sweep and the §16.2/§16.3/§17 hardening/feature passes are explicitly **not** gates on this deploy; they continue as post-launch work checked against the live URL. (Superseded rule, kept for context: the 2026-08-04 plan had Deploy running last, after full local parity/QA confidence.)

**Phase 6 (optional, post-v1)**
- Local diarization enhancement (§6.4 alternative), if the Phase 2 validation gate flags contextual attribution as insufficient.
- Second-opinion validation pattern.
- GitHub Action for the deterministic-only regeneration step.
- Annual Predictions episode filter — see §17 for full detail.

## 14. Decisions Log

The five open questions from the initial draft of this PRD have been resolved as follows. Recorded here (rather than deleted) so the reasoning survives for future sessions.

### 14.1 Attribution strictness — **Contextual-guess only, gated by a validation checkpoint**
Decision: go with audio-free contextual attribution (§6.4) as the v1 approach — but explicitly **do not fully commit to it** until it's tested and verified on a small sample. A validation gate is now a required, non-skippable step in Phase 2 (§13): hand-check attribution precision on the 3–5 sample episodes and get explicit sign-off before scaling to the full archive. If precision comes back too low, the fallback is the local-diarization alternative (§6.4), not shipping the weak version broadly. This nuance is also captured as new Goal **G9** (§1).

### 14.2 Host roster / guest handling — **Guests get their own scorecards too**
Decision: any named speaker (host or guest) with at least one `high`/`medium`-confidence prediction gets a real scorecard page, not just the four permanent hosts. A `role` field (`host|guest`) distinguishes the two in navigation so the site doesn't read as "four hosts plus noise" — guests are first-class, just visually separated (§9.2's `/host/index.html` directory) and always shown with their raw prediction count next to their accuracy percentage so small samples aren't misread as statistically meaningful. Captured as new Goal **G8** (§1); data model, page generation, and config sections updated accordingly (§6.4, §7, §8, §9.2).

### 14.3 Batch execution mode — **Interactive first, batch later**
Decision: confirmed as originally recommended. Early episodes are processed visibly, turn-by-turn, in normal conversation so quality can be sanity-checked cheaply; the headless `claude -p` batch driver (§10) is built only once interactive results look right — practically, this lines up with clearing the §14.1 validation gate before Phase 4's full-archive run.

### 14.4 Starting data — **Independently re-derive AND cross-check against the old repo**
Decision: neither pure option — the rewrite derives its own episode↔YouTube matching from scratch (not seeded from the old repo), but then diffs its results against the old repo's already-resolved `data/processed/all_in_episodes.json` as a free correctness check and as the evidence base for eventually retiring the old pipeline. Full mechanism documented in the new cross-check step added to §6.1 (`scripts/compare_episode_sources.py`, `data/episode_source_diff.json`).

### 14.5 Repo scope — **MVP-first cutover (superseded 2026-08-25): replace now, don't wait for full validation**
Original decision (2026-08-04): `rewrite/` stays a parallel/experimental sibling short-term, cutover timing deferred until parity/QA confidence.

**Superseded 2026-08-25.** The user made the explicit call to push an MVP to production *before* the full-archive validation sweep finishes, rather than waiting for validation to be "meaningfully progressed" as originally planned. The cutover mechanism stays a full replacement, but happens now:
- Repo root becomes the generated site: everything currently under `rewrite/` (site output, `data/`, `scripts/`, `config/`, `docs/`, `prompts/`) moves up to the repo root.
- The old pipeline (root-level `scripts/`, `web/`, `config/`, `data/`, plus `AGENTS.md`, `DEVELOPMENT.md`, `analysis.md`, root `requirements.txt`) is archived, not deleted, into a new top-level `old/` folder, preserving it for reference/rollback.
- GitHub Pages then deploys from the new repo root, per §8.1/§11.
- Full-archive validation (and the remaining hardening/feature passes: §16.2, §16.3, §17, `video_id` resolution) become **post-launch, ongoing work against the live site**, not pre-launch gates. "MVP" here means the site is live, correct, and clearly labeled as a work in progress (unvalidated predictions show as such), not that every prediction has been checked.
- This should be treated as the settled strategic direction going forward: future sessions should default to shipping early and iterating live, not batching every improvement before the first deploy.

### 14.6 Extraction sub-agent concurrency — **Max 5 concurrent, no sub-sub-agents**
Decision, made after an incident on 2026-08-04: a parallel extraction batch of ~10 agents recursively self-spawned further per-episode sub-agents instead of working sequentially, ballooning to 30+ concurrent agents and burning through the usage budget far faster than expected before being manually stopped mid-batch (v0.4.0 patch note). Going forward, any parallel extraction (or similar) batch is capped at 5 concurrently-running agents, and each agent's instructions must explicitly forbid delegating to further sub-agents — batches larger than 5 episodes are run as sequential waves of ≤5, not as one larger parallel burst. This is a standing rule, not specific to this one incident.

## 15. Success Criteria

- The generated site (at `rewrite/` root) renders correctly as a static site with zero JavaScript build step, served locally by opening the file or via `python -m http.server`, and confirmed working once pushed to GitHub Pages.
- At least one full episode is processed end-to-end (captions → predictions → validated → tagged → on the site) with no OpenAI/xAI/paid-ASR calls anywhere in the process.
- Host scorecards, episode pages, and host pages all render with real data, including the resolved-only/topic/year chart interactivity.
- Pipeline is demonstrably incremental: re-running discovery + processing after adding one new episode only does new work for that episode.
- README/PRD are sufficient that a future Claude Code session (with no memory of this conversation) could pick up the pipeline and continue it correctly from the docs alone.

## 16. Post-MVP Roadmap (Deferred — Do Not Execute Until MVP Ships)

Three hardening passes are queued for after the MVP (Phases 0–5) is live and working. These are explicitly **not** part of v1 scope — they assume there is a working site with real content to audit, fix, and document. Each is written up here in full detail now so a future session (with or without this conversation's memory) can execute it correctly without re-deriving the plan.

### 16.1 Documentation audit & consolidation

**Status: partially executed on 2026-08-04.** The original trigger below assumed this would wait until deployment and a meaningful slice of the archive were done. The user asked for the folder-structure move and documentation audit earlier than planned (before Phase 5 deploy, before the mobile-responsive and writing-style sweeps, and with only 9 of ~404 episodes processed), so this pass has been run now, against the current MVP state, on the explicit understanding that it will need a follow-up pass once more of the archive is processed and the site is live — content here reflects "true as of 2026-08-04," not a permanent final state. The mobile-responsive pass (§16.3) and writing-style/em-dash sweep (§16.2) remain deferred until after GitHub Pages deployment and full-archive processing, per the user's explicit instruction; the *methodology* for the writing-style rule (§16.2) is being followed prospectively starting now even though the formal sweep hasn't run yet (see §26).

**Original trigger (superseded above, kept for reference):** once the MVP site is deployed and the pipeline has processed a meaningful slice of the archive (not necessarily the full 300+ episodes, but enough that the docs describe real, working behavior rather than aspirational design).

**Objective:** perform a full documentation audit of this project's docs, ensuring every document accurately reflects the current state of the codebase, with no gaps, outdated information, or missing coverage — then consolidate everything into exactly four files.

**Required end-state folder structure:**
```
/project-root
├── README.md          ← root only, never inside /docs
└── /docs
    ├── PRD.md
    ├── DESIGN.md
    └── PATCHNOTES.md
```
Any documentation file that exists outside `/docs` (other than root `README.md`) must be moved into `/docs`. If `/docs` doesn't exist yet at that point, create it. This PRD itself (currently `rewrite/PRD.md`) is expected to relocate to `rewrite/docs/PRD.md` as part of this pass, with `rewrite/README.md` staying at `rewrite/`'s root.

**Process (in order):**
1. **Full codebase scan first, before touching any documentation.** Crawl the entire rewrite codebase and build a complete picture of what exists: all files, features, components/templates, routes/pages, configs, scripts, and pipeline logic. Do not skip this step or start editing docs from memory/assumption.
2. Open every existing documentation file one by one (this PRD, the rewrite README, any prompts/*.md, any inline docs).
3. For each, diff its claims against the actual codebase: what's outdated, missing, inaccurate, or incomplete.
4. Rewrite/update each document so it is fully accurate and comprehensive for the *current* version of the site — not the originally planned version if the plan drifted during implementation.
5. Consolidate all documentation into the four target files. Every other doc file must be reviewed and folded in — none skipped.
6. Create any missing documentation files/sections the codebase clearly warrants but that don't exist yet.
7. After all documents are updated, produce a summary of what changed in each file and why.

**Standard to hold every doc to:** thorough enough that a new contributor or another AI model could understand the entire project from `/docs` alone, without needing to read the source code first.

**Required contents per file:**

- **`README.md` (root)** — developer-facing, no marketing language. Must include: project name + one-sentence description; link to the live GitHub Pages site; tech stack list with versions; prerequisites (Python version, any package manager, environment requirements); exact installation commands in order; how to run locally (which script/command, any local server + port for previewing `docs/`); environment variable reference (name, purpose, required/optional — expected to be short/empty here since v1 has no API keys, but must still be stated explicitly rather than omitted); build and deploy instructions (how `generate_site.py` output gets to GitHub Pages); link to `/docs` for full documentation.

- **`/docs/DESIGN.md`** — the visual/UX system. Must include: design philosophy (1–3 sentences); full color palette (every token, hex value, intended use — right/wrong/ambiguous/inconclusive colors, background, text, borders); typography (font families, sizes, weights, line heights per role: H1–H3, body, caption, label, code); spacing system/base unit; every responsive breakpoint used and what changes at each; component pattern rules (prediction cards, buttons, charts, modals, filters — how each should be built/styled consistently); accessibility standards (WCAG level targeted, contrast requirements, keyboard navigation expectations — relevant since this rewrite drops React's accessibility conveniences and hand-rolls SVG/DOM); animation/motion rules (timing, easing, when motion is/isn't appropriate — e.g. the chart redraw on filter change, the YouTube disclaimer modal); any other context a future AI model would need to stay visually consistent when adding pages.

- **`/docs/PATCHNOTES.md`** — running changelog. Each entry: semantic version (MAJOR.MINOR.PATCH), date (YYYY-MM-DD), and Added/Changed/Fixed/Removed sections, one line per change, past tense. Since no changelog exists yet at that point, this pass must create an initial entry summarizing the MVP build as `v0.1.0` (or nearest appropriate version) before adding the audit's own entry on top.

- **`/docs/PRD.md`** — the most comprehensive document, meant to make the *entire* project understandable without reading code. Beyond standard PRD sections (problem statement, target users/personas, goals, non-goals, user stories in "As a [user], I want to [action] so that [outcome]" form, MVP vs. Future feature list, constraints, assumptions, success criteria), it must also carry:
  - **Tenets** — 3–7 opinionated, prioritized product principles, each with a short title and 2–4 sentence rationale, ordered so higher tenets win conflicts. (Candidate material already implicit in this PRD's Goals §1 and the free-tooling framing — e.g. "zero paid dependencies over best-possible accuracy," "Claude as runtime, not just builder" — should be sharpened into true tenets during this pass, not just copied verbatim.)
  - **Roadmap** — current phase name/description, a milestone table (name, target/relative timeframe, status: Planned/In Progress/Complete/Blocked), feature breakdown per milestone, and explicitly deferred items with reasons (this §16 itself is an example of a properly-documented deferred item).
  - **Metrics** — north star metric, acquisition/engagement/retention/performance metrics, target values + timeframes, measurement method per metric, reporting cadence. (Note: this is a static informational site with no accounts/backend, so metrics here will mostly be traffic/engagement-via-static-analytics and technical health, not product usage funnels — define honestly for what this project actually is.)
  - **Runbook** — local setup from a fresh machine, exact build command + output location, step-by-step deploy process per environment (this project effectively has one environment: GitHub Pages), rollback procedure (git revert of `docs/` + re-push), environment configs, a table of common errors/likely cause/fix, and where to check for monitoring/build health (GitHub Pages build status, browser console for client JS errors).
  - **Technical Requirements** — system architecture description (static-generated, no server, Claude-driven analysis layer), full tech stack with versions, annotated folder structure, every data model (episode/prediction/check schemas from §7 of this PRD, kept current), "API design" reinterpreted as internal data flow (since this is browser-only/no backend — document how `app.js` reads embedded JSON and redraws charts), state management (client-side JS state only, no framework store), third-party integrations (YouTube captions endpoint, yt-dlp, GitHub Pages — what data flows where and how each is "authenticated," i.e. none require keys), performance requirements (page weight/load time targets given hand-rolled SVG and no framework), known technical debt with notes on the "correct" fix.
  - **Security** — authentication/authorization models (both effectively "none" for a static public site — state that explicitly rather than omitting the section), what data is stored/where (no user data collected; predictions/transcripts are public podcast content), confirmation no secrets are hardcoded plus a list of any env vars, third-party trust list (which external services see any data, and what — e.g. YouTube's caption endpoint sees only the video ID being requested), known attack surface (e.g. XSS risk if any user-supplied content were ever rendered — currently none exists, but document the assumption), dependency monitoring policy (how `requirements.txt`/`yt-dlp` versions get checked for vulnerabilities over time).
  - **Press Release** (Amazon/Working-Backwards style) — written as if launched: headline, subheadline, dateline, opening paragraph (who/what/when/where/why), problem statement from the customer's perspective, plain-language solution description, a realistic fictional customer quote, call to action, short company/project boilerplate. Plain language, no jargon, general audience.
  - **FAQ** — 10–25 realistic user questions covering: what the site is/who it's for, how to use it, cost (free), what data it uses (public YouTube captions + web search, no paid APIs), what it explicitly doesn't do (perfect speaker attribution, real-time updates), technical requirements/compatibility, how it differs from the original Cloudflare/Next.js version and from doing this manually, known v1 limitations, how to get help/report an issue, and a short "internal stakeholder" subsection (why this rewrite, what success looks like, what's next).

**After this pass:** add a dated entry to `PATCHNOTES.md` describing the audit itself (what was consolidated, moved, or rewritten and why), and update `PRD.md`'s Roadmap to reflect the audit as complete, plus document — inside `PRD.md` — how this documentation process should be repeated going forward (i.e., this same audit methodology becomes the standing process for keeping docs in sync with the codebase after future feature work, not a one-time event).

### 16.2 Writing-style sweep: em dashes and double dashes

**Trigger:** same post-MVP window as §16.1; can be done in the same pass or immediately after.

**Objective:** audit every HTML page and every documentation file in the project for em dashes and double-dash punctuation, and replace them with contextually appropriate standard punctuation.

**What to search for (independently — a search for one form will not catch the others):**
1. The literal Unicode em dash character (—).
2. The HTML entity form (`&mdash;`).
3. Double dashes used as punctuation (`--`) — but **not** CSS custom properties, which legitimately use a leading double-dash (e.g. `--bg`, `--accent`, `--space-4`); those must be left untouched.

**Replacement rule (choose based on context, not a single default):**
- **Comma** — the most natural default in most cases; keeps the sentence flowing without drawing attention to the punctuation itself.
- **Colon** — when introducing a list, explanation, or elaboration after a complete clause.
- **Semicolon** — when joining two closely related independent clauses that could each stand alone.
- **Parentheses** — for asides/supplementary information that isn't central to the sentence.
- **Period** — when the cleanest fix is splitting into two sentences; shorter sentences are often clearer anyway.

**Deliverable:** after fixing every instance, add a **Writing Style** section to `/docs/PRD.md` (once relocated per §16.1) documenting this exact methodology — explicitly noting that em dashes appear in both literal-character and HTML-entity form, that both are prohibited project-wide, that double dashes as punctuation are likewise prohibited (with the CSS custom-property carve-out stated explicitly so it isn't mistakenly "fixed" in a future pass), and the five-way replacement decision rule above so future contributions (human or AI) follow the same standard going forward rather than reintroducing em dashes.

**Also required:** update `PATCHNOTES.md` with a dated entry describing this sweep (scope: all HTML + docs; what was found/fixed; the new standing rule), consistent with §16.1's documentation-currency standard.

### 16.3 Mobile-friendliness / responsive audit-and-fix pass

**Trigger:** same post-MVP window; logically follows §16.1–16.2 since it should be documented using whatever conventions those establish.

**Objective:** a full responsive audit and fix pass across every page/view the rewrite ships (home, episode list, episode detail, host page, about page), verified programmatically rather than by eyeballing screenshots.

**1. Audit scope — widths to check on every page:** 375px, 700px, 900px, 1023px (or this site's effective desktop breakpoint if different), 1150px, 1440px, 1920px. At each width, check for: horizontal page overflow (page wider than viewport); elements overflowing their own container without an intended scroll affordance; any wide toolbar/filter row/chart legend that doesn't wrap or reflow cleanly; modal sizing at narrow widths (the YouTube-link disclaimer modal); clipped or overlapping text/labels.

**2. Specific bug patterns to check for** (common, easy to introduce, easy to miss — especially relevant here since this rewrite hand-writes CSS/SVG instead of relying on Tailwind/Chart.js defaults):
- **`overflow` shorthand collision** — if any element sets `overflow-x: auto` and a bare `overflow: <value>` shorthand is also set (same rule or a later one), the shorthand silently resets both axes and cancels the x-axis setting. Grep for elements with both an explicit `overflow-x`/`overflow-y` and a bare `overflow`.
- **CSS Grid implicit min-width on bare `1fr` tracks** — a bare `1fr` grid track has an implicit `min-width: auto` (intrinsic content width, not zero). Wide content in a cell (a stat table, a long filter/button row) can force the whole grid — and page — wider than the viewport. Fix: `minmax(0, 1fr)` instead of bare `1fr`. Check this in **every** media query touching the same grid, since it's common to fix the desktop rule and have a mobile override silently reintroduce a bare `1fr`.
- **Flexbox children with default `min-width`/`min-height: auto`** — a flex item defaults to `min-size: auto`, which for large content (e.g. a scrollable chart/table wrapper inside a `flex: 1` column) resolves to "big enough for all content," not "shrink to available space" — causing overflow instead of internal scrolling. Fix: `min-width: 0` / `min-height: 0` on the flex item.
- **Redundant spacing with `gap` + `margin`** — if a flex/grid container already declares `gap`, don't also add `margin` on a child for the same spacing; they stack and double the gap. Check anything moved into a `gap`-based container after being styled for a different original layout.

**3. Verification methodology — do not rely on screenshots alone.** Headless Chrome enforces an effective minimum viewport (~485–500px) even when a smaller `--window-size` is requested, and screenshot pixel dimensions don't reliably match the actual layout viewport — screenshots below that width can look broken with zero real overflow, and can also miss genuine bugs at specific widths. Instead:
- Inject a small debug `<script>` into a scratch copy of the page printing `window.innerWidth`, `document.documentElement.scrollWidth`, `document.documentElement.clientWidth`, and `getBoundingClientRect()` for suspect elements.
- The reliable "is there page-level overflow" check is `scrollWidth === clientWidth`, not a visual read of a screenshot.
- For subtler layout bugs (uneven spacing between sibling elements, e.g. host scorecards or filter buttons), measure `getBoundingClientRect().left`/`.right` for every sibling and diff the gaps programmatically rather than eyeballing a zoomed screenshot.
- Test against a local copy served via `python -m http.server` (already this rewrite's stated local-preview method — see §11), not the live GitHub Pages site, so fixes are verified before shipping.

**4. Design decisions — ask, don't guess.** If fixing an overflow requires a real design choice (e.g. should the by-topic stacked bar chart's legend wrap, truncate, or scroll on narrow screens; should the episode list switch to a card layout below a breakpoint; should hidden filter options be recoverable via a menu), stop and ask which approach to use before implementing. Only proceed unprompted for pure CSS-correctness bugs with one obviously correct fix (the four patterns in §16.3.2).

**5. Regression safety.** Before and after each fix, reconfirm this project's zero-regression check still holds — e.g. a known-good episode/host page's data renders identically (same predictions, same counts, same chart values) before and after the CSS/layout change, since these are meant to be render-only changes that never touch the underlying JSON data or the generation logic in `generate_site.py`.

**6. Documentation.** After fixes are verified, add a dated `PATCHNOTES.md` entry describing what was found and fixed by root cause (e.g. "bare `1fr` grid track in the host-scorecard grid caused horizontal overflow below 1023px when a stacked bar chart's legend exceeded the cell's intrinsic width"), not a vague "fixed mobile bugs" line, and update the Roadmap section of `PRD.md` if this pass changes what's considered shipped/complete. Follow whatever documentation structure §16.1–16.2 have already established by that point rather than introducing a new format.

**Process order for this whole pass:** audit first and report findings across all breakpoints → ask about any open design-decision questions from step 4 → implement and verify fixes → document per step 6. Do not implement fixes before the audit-and-report step, and do not skip the "ask" step for anything beyond pure bug fixes.

## 17. Planned Feature: Annual Predictions Episode Filter (Roadmap, Post-MVP)

**Trigger:** post-MVP, once the core pipeline (§6) and site (§9) are working end-to-end on real data. Listed in Phase 6 (§13) but detailed fully here since it's a real planned feature, not just a hardening pass.

**Context:** the All-In hosts periodically record a dedicated "predictions episode" (typically an annual, start-of-year special) where each host runs through a deliberate, structured list of predictions for the coming year — distinct in kind from the incidental, off-the-cuff predictions made during normal news-discussion episodes. These are the highest-density, most-intentional predictions in the archive and deserve to be independently browsable, not just findable by scrolling through regular episodes.

**Goal:** let a site visitor filter the whole site (or view a dedicated page) showing *only* predictions that came from these annual predictions episodes, separate from everything else.

**Data model change:**
- Add an `episode_type` field to `data/episodes.json` — `"regular"` (default) or `"annual_predictions"`.
- Detection is two-layered, mirroring the manual-override pattern already used for YouTube matching (§6.1):
  1. **Automatic heuristic** during episode discovery (§6.1): match episode titles/descriptions against a pattern (e.g., containing "predictions" alongside a year, or matching the show's known recurring naming convention for these specials) to flag likely candidates.
  2. **Manual override list** — `config/annual_prediction_episodes.json`, a simple array of `episode_id`s — since heuristic title-matching is expected to miss or mis-tag some episodes (naming isn't perfectly consistent year to year) and this is a small, stable, human-curatable list worth just verifying by hand once discovered (cross-referenced against allin.com/episodes, consistent with §6.1's canonical-ordering practice).
- `data/predictions/<episode_id>.json` doesn't need its own change — a prediction's episode-level type is looked up via `episode_id` at site-generation time, keeping the "annual" flag a property of the episode, not duplicated onto every prediction.

**Site feature:**
- A dedicated page, `/predictions/annual.html`, listing every prediction sourced from `episode_type: annual_predictions` episodes, grouped by year and then by host — this is the primary new view.
- A filter toggle (same interaction pattern as the existing "Resolved only" checkbox and topic-tag dropdown in `HostCharts`-equivalent §9.3 charts) on the home page and host pages: "Annual predictions only," which recomputes the on-page chart stats client-side using the same embedded-JSON-plus-vanilla-JS-redraw approach already specified for topic/year filtering (§9.3) — no new architecture needed, just another filter dimension threaded through the existing stats-recompute code path.
- A small visual badge on prediction cards (§9.5-style, ports the original's tag-badge visual language) indicating a prediction came from an annual predictions episode, visible wherever that prediction appears (episode page, host page, home page previews).

**Why this belongs in the roadmap and not v1:** it depends on the core pipeline and site already working end-to-end with real predictions in hand — there's nothing to filter until predictions exist, and doing the episode-type classification well benefits from having already built the manual-override pattern once for YouTube matching (§6.1), so this is naturally sequenced after the MVP proves out.

## 18. Tenets

Ordered by priority; when two conflict, the higher one wins.

1. **Free tooling beats maximum accuracy.** Every architectural choice in this rewrite (captions instead of paid ASR, contextual attribution instead of voice embeddings, Claude instead of a billed API) trades some precision for zero ongoing cost. When a future decision pits "more accurate" against "costs money to run," free wins unless the accuracy loss is severe enough to make the site actively misleading (see G7/G9 and the validation gate).
2. **Claude does the thinking, always.** No step in this pipeline ever calls a third-party model API (OpenAI, xAI, or otherwise). If a future feature seems to need "a smarter model," the answer is a better prompt or a smarter use of Claude's existing tools (WebSearch, WebFetch), not a new SDK dependency. This is non-negotiable, not a cost tradeoff: it's the entire premise of "ran/updated entirely in Claude."
3. **Show your confidence, don't fake certainty.** Every attributed prediction carries a `speaker_confidence`, every validated one carries cited sources, and low-confidence data stays visible (on episode pages) rather than silently dropped, even though it's excluded from scorecards. When a design choice would hide uncertainty to make the UI look cleaner, uncertainty wins.
4. **Breadth before depth, in that order.** When processing the archive, cover more episodes with lighter validation before exhaustively validating fewer episodes (§13 Phase 4's two-sweep design: extract everything, then validate everything, never both at once per episode). A half-covered archive with thin validation beats a fully-validated tenth of the archive, because the product's core promise is "every prediction," not "every prediction, perfectly checked, eventually."
5. **Every voice counts, but hosts anchor the site.** Guests get real scorecards (G8): this project doesn't pretend only the four permanent hosts make predictions worth tracking. But navigation, defaults, and the home page are built around the four hosts first; guests are discoverable, not equally prominent, because a guest's one-episode sample size is a fundamentally different kind of data than a host's running record.

## 19. Roadmap

**Current phase:** MVP-first launch push (repo restructure + deploy), per the 2026-08-25 sequencing change (Decisions Log §14.5), as of 2026-08-25.

**Sequencing change (2026-08-25):** the user made the explicit call to ship an MVP to production *before* the full-archive validation sweep (and the remaining hardening/feature passes) finish, rather than waiting for parity/QA confidence as originally planned. The full site replacement and GitHub Pages deploy now move up to right after the extraction sweep, and everything that used to gate deployment (validation completion, §16.2/§16.3, §17, `video_id` resolution) becomes ongoing post-launch work against the live site instead.

| Milestone | Timeframe | Status |
|---|---|---|
| Phase 0-3: MVP build (scaffolding, mechanical pipeline, sample extraction/validation, site generator) | 2026-08-04 | Complete |
| Repo restructure (v1): site generated to `rewrite/` root, `docs/` reserved for documentation (§8.1) | 2026-08-04 | Complete |
| §16.1 documentation audit & consolidation (this pass) | 2026-08-04 | Complete (partial: see §16.1 status note; will need a follow-up pass once more of the archive is processed) |
| Phase 4: extraction sweep against currently-available transcripts, manual/no-agent, oldest-first (§13) | 2026-08-04 | Complete — 357/404 episodes have a predictions file; all 128/128 chunked/captioned episodes are done. Remaining 47 episodes are blocked on captions (45 need `video_id` resolution, 2 have a `video_id` but no fetchable captions), not extraction work |
| Validation sweep, first batch (E010-E020, 155 predictions) | 2026-08-25 | Complete — 32/357 episodes now validated overall |
| Pre-launch parity pass: home page filter UI + "Last updated" date (§27) | Immediately, checked via local `python -m http.server` preview; no longer gated on validation progress | Planned (next up) |
| **Full site replacement (repo restructure v2, per Decisions Log §14.5): move `rewrite/` contents to repo root; archive old pipeline (`scripts/`, `web/`, `config/`, old `data/`, `AGENTS.md`, `DEVELOPMENT.md`, `analysis.md`, root `requirements.txt`) into `old/`** | Right after the parity pass, before any further validation/hardening work | Planned |
| **Phase 5: deploy to GitHub Pages (MVP launch)** | Immediately after the repo restructure lands, as the step that makes the site live | Planned |
| Full-archive validation sweep, 10 predictions/batch, ascending by prediction count (fewest-first, oldest-first tiebreak) (§13) | **Post-launch, ongoing**, against the live site; not a launch blocker | Planned (continuing indefinitely as maintenance) |
| §16.2: writing-style / em-dash sweep | Post-launch, checked against the live URL | Planned |
| §16.3: mobile-responsive audit | Post-launch, checked against the live URL | Planned |
| §17: Annual Predictions episode filter | Post-launch | Planned |
| `video_id` resolution (45 episodes) | Post-launch | Planned |
| Follow-up extraction sweep: pick up the 45 episodes unblocked by `video_id` resolution, plus any newly published episodes since the 2026-08-04 sweep | Post-launch, after `video_id` resolution progresses | Planned |

**Explicitly deferred items and why** (see also §12 Risks and §16 for full detail on each):
- Caption-less episode handling (2 episodes with a `video_id` but no captions fetchable via any current method): deferred with no scheduled trigger yet, to be revisited later once a fetch method exists or a manual-transcription fallback is decided on; not on the critical path since it's only 2 of 404 episodes.
- Local voice-diarization enhancement (§6.4 alternative): only triggered if the attribution validation gate (§6.4, §14.1) is later found to have failed at scale; not needed today because the gate passed on the initial sample.
- Second-opinion validation pattern (re-validate in a fresh session and diff): a possible accuracy improvement over single-pass validation, deferred because single-pass validation is working adequately and doubling validation cost isn't justified yet.
- GitHub Action for deterministic-only site regeneration: deferred because there's no CI need yet at this scale; manual regeneration is fast and the Claude-driven steps can't run in CI anyway.
- Multi-podcast generalization: explicitly out of v1 scope per §2 Non-Goals; the architecture stays podcast-agnostic where cheap to do so, but no plugin system is being built now.

## 20. Metrics

This is a static, account-free informational site, so metrics here are honestly scoped to what such a site can actually measure, not a product-usage funnel.

- **North star metric:** total validated (right/wrong/ambiguous, not unvalidated/inconclusive) predictions published on the site. This is the single number that best represents delivered value, since the product's promise is "predictions checked against reality," not just "predictions listed."
- **Acquisition:** organic/referral traffic only (no paid marketing planned): links shared from the repo, social shares of specific host/episode pages, search engine indexing of the static pages. No acquisition tooling is installed yet (see below).
- **Engagement:** pageviews per session, which host/episode pages get visited most, whether visitors use the topic/year filter interactivity. Not yet instrumented: no analytics script exists in `site_src/static/` as of this audit, and adding one is a deliberate future decision (must stay free and privacy-respecting to match G1/G7's spirit), not an oversight to silently fix here.
- **Retention:** low relevance for a static informational site with no accounts; the closest honest proxy would be repeat-visit rate via basic web analytics once instrumented, not tracked today.
- **Performance:** page load time, Lighthouse/PageSpeed score, GitHub Pages uptime (effectively controlled by GitHub's infrastructure, not this project). No target values are set yet because the site isn't deployed; targets should be set against real Lighthouse numbers once Phase 5 ships, not guessed now.
- **Measurement method & reporting cadence:** none configured yet. This whole section should be revisited and filled in with a real analytics choice (e.g., a privacy-respecting, free, script-tag-only option, consistent with G1/G4) as part of, or shortly after, Phase 5 deployment.

## 21. Runbook

**Local setup (fresh machine):**
```bash
git clone <repo-url>
cd rewrite
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
No API keys, no `.env` file, no external accounts needed.

**Build:** `python scripts/generate_site.py` writes `index.html`, `about.html`, `episodes/*.html`, `host/*.html`, and `static/` directly into the `rewrite/` root (§8.1). No separate build tool; this script is the entire build.

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

**Monitoring:** no dedicated monitoring is configured (matches the "no analytics yet" note in §20). GitHub's own Pages deployment status (repo → Actions/Pages tab) is the only current signal that a deploy succeeded; browser DevTools console is the way to check for client-side JS errors in `app.js` during manual QA.

## 22. Technical Requirements (Summary)

This section is a single point of reference pulling together material detailed elsewhere in this PRD, so a reader doesn't have to jump around to get the full technical picture.

- **System architecture:** fully static site, no server, no database, no runtime backend. All "intelligence" (extraction, attribution, tagging, validation) happens offline, ahead of time, in a Claude Code session, and is baked into committed JSON (`data/predictions/*.json`, `data/checks/*.json`) that a deterministic Python script (`scripts/generate_site.py`) turns into static HTML. See §4 for the full pipeline diagram.
- **Tech stack with versions:** see the table in `README.md`'s "Tech stack" section (kept as the single source of truth for exact versions, to avoid this PRD drifting out of sync with `requirements.txt`).
- **Folder structure:** see §8 for the full annotated tree, and §8.1 for why the generated site lives at `rewrite/` root rather than a `docs/` subfolder.
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

**Rule:** no em dashes in either form (the literal Unicode character — or the HTML entity `&mdash;`), and no double dashes (`--`) used as punctuation, anywhere in this project's prose: documentation, HTML page content, prompts, and code comments meant for human readers. The only exception is CSS custom properties, which legitimately use a leading double dash as syntax (e.g. `--bg`, `--accent`) and must never be "fixed."

**Replacement rule, chosen by context, not a single default:**
- **Comma:** the default in most cases; keeps a sentence flowing without drawing attention to the punctuation itself.
- **Colon:** when introducing a list, explanation, or elaboration after a complete clause.
- **Semicolon:** when joining two closely related independent clauses that could each stand alone.
- **Parentheses:** for an aside or supplementary detail that isn't central to the sentence.
- **Period:** when the cleanest fix is splitting into two sentences; shorter sentences are often clearer anyway.

**Status:** the formal, project-wide sweep for existing em dashes/double dashes (§16.2) is now a **post-launch** task per the 2026-08-25 MVP-first sequencing (§19): it runs against the live site after the GitHub Pages deploy, not before it. However, this rule is being followed **prospectively starting 2026-08-04**: all new documentation, prompts, and content written from this date forward should already comply, so the eventual formal sweep only needs to catch older material rather than a constantly-growing backlog.

## 27. Pre-Replacement Parity Checklist: Home Page Filter UI & "Last Updated" Date

**Trigger:** immediately, as the last local step before the full site replacement and GitHub Pages deploy (Decisions Log §14.5, §19) — **no longer gated on the validation sweep's progress**, per the 2026-08-25 MVP-first sequencing change. Checked locally via `python -m http.server` since this runs just before the repo restructure/deploy. Flagged by the user on 2026-08-04 against the live original site as a real feature gap in the rewrite's MVP, not a nice-to-have.

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
