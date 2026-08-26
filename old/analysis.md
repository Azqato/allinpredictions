# Analysis: All-In Predictions

**Live site:** https://allin-predictions.pages.dev/
**Repo:** forked from `Azqato/allinpredictions` (origin author's project: `schnerd/podcast-predictions`)

## 1. What this project is

An end-to-end pipeline that:
1. Downloads every episode of the **All-In Podcast** (audio + metadata).
2. Transcribes and diarizes (speaker-separates) each episode.
3. Identifies *which host* said each line (Jason Calacanis, Chamath Palihapitiya, David Sacks, David Friedberg) using voice-embedding matching.
4. Uses an LLM (GPT-5.1) to extract concrete, falsifiable **predictions** made by the hosts, with quotes and timestamps.
5. Uses an LLM with web search (and optionally Grok) to **validate** whether each prediction came true, producing a verdict (`right` / `wrong` / `ambiguous` / `inconclusive`) with a cited explanation.
6. Tags each prediction with a topic (politics, tech, ai, markets, economy, etc.).
7. Publishes everything as a static Next.js website with per-host accuracy scorecards, charts, and a browsable episode/prediction archive.

It was built (per `DEVELOPMENT.md`) in a weekend using OpenAI's **Codex CLI**. The core idea: use AI not just to generate content, but to fact-check public figures' predictions at scale — a positive/accountability use of AI in contrast to misinformation concerns.

The repo is a fork; only the underlying pipeline/site code is versioned in git (2 commits: "Initial commit" and "update meta"). All generated data — audio, transcripts, embeddings, predictions — is *not* tracked in git (gitignored) but happens to be present in this checkout under `data/` (327 episodes worth of processed transcripts/predictions already exist locally).

## 2. Repository layout

```
allinpredictions/
├── AGENTS.md              — coding/style conventions for contributors (and AI agents)
├── DEVELOPMENT.md         — pipeline usage instructions (the real "how it works" doc)
├── README.md              — one-paragraph pitch + links
├── requirements.txt       — Python deps for the data pipeline
├── config/
│   └── speakers.yaml      — canonical host roster + paths to their voice embeddings
├── data/                  — generated artifacts (gitignored, but populated in this clone)
│   ├── raw/                     — raw RSS feed XML, yt-dlp playlist dump
│   ├── processed/
│   │   ├── all_in_episodes.json       — master episode index (title, dates, audio URL, YouTube URL, episode code)
│   │   └── transcripts_speechmatics/  — one folder per episode (see §4)
│   ├── audio/                   — downloaded MP3s
│   └── speakers/                — .npy voice-embedding files per host
├── scripts/                — the Python data pipeline (see §3)
└── web/                     — the Next.js 14 static site (see §5)
```

## 3. The data pipeline (Python, `scripts/`)

The pipeline is a chain of standalone CLI scripts, each idempotent (skips work already done unless `--force` is passed), designed to be run manually/sequentially rather than orchestrated by a single framework.

### Step 1 — `all_in_downloader.py`: fetch the archive
- Downloads the All-In podcast **RSS feed** (Libsyn) and parses every episode's title, publish date, description, and MP3 enclosure URL → `data/raw/all_in_feed.xml` → normalized into `data/processed/all_in_episodes.json`.
- Because the RSS feed only exposes ~15 recent items, it also shells out to **`yt-dlp`** against the All-In YouTube channel (`@allin/videos`) to get the *full* upload history, then fuzzy-matches each RSS episode to its YouTube video by:
  1. Manual override map (`config/youtube_urls.json`), by episode ID or title.
  2. Normalized title match.
  3. Parsed episode code (`E123` extracted via regex from titles/filenames).
  4. Nearest-publish-date match (within 30 days) as a fallback.
  5. Extracting a YouTube link straight out of the episode description text as a last resort.
- This YouTube URL becomes `youtube_url` on each episode, later used by the web UI to deep-link predictions to `youtube.com/watch?v=...&t=<seconds>`. Coverage is ~87% (per `AGENTS.md`); unmatched episodes show a tooltip instead of a link.
- With `--download-audio`, MP3s are streamed to `data/audio/all_in/`, skipping files that already exist (resumable archive mirroring).

### Step 2 — Transcription (`transcribe_speechmatics.py`, plus `_deepgram.py`, `_openai.py`, `_assemblyai.py`)
- Multiple ASR providers were evaluated; **Speechmatics** was chosen as the production source (best word-error-rate/diarization/long-form balance — see `DEVELOPMENT.md`), but the code keeps the other three providers as alternates (`speaker_utils.TRANSCRIPTION_DIRS` maps all four).
- Output per episode lands in `data/processed/transcripts_speechmatics/<episode_id>/`:
  - `speechmatics_raw.json` — untouched API response
  - `segments.json` — speaker-labeled segments with `start`/`end`/timestamps and raw diarization labels (`A`, `B`, `C`, …)
  - `transcript.txt` — human-readable transcript
  - `metadata.json` — episode title/published date/duration/audio filename, summary info used downstream

### Step 3 — Speaker identification (voiceprint matching)
This is the most technically interesting part — turning generic diarization labels ("Speaker A") into real names.

- **`build_speaker_profiles.py`**: for a reference episode with known speaker mapping (e.g., `ALLIN-E000` where `A=jason, B=chamath, C=friedberg`), it:
  1. Loads that episode's diarized segments.
  2. Picks the longest, cleanest segments per label (`select_segments`, requiring a minimum duration).
  3. Extracts the raw audio for those spans via `ffmpeg` (`load_audio_segment` — decodes to 16kHz mono PCM).
  4. Computes a **voice embedding** for each segment using either:
     - `mfcc` strategy — classic MFCC features (mean+std over 20 cepstral coefficients), or
     - `speechbrain` strategy (the one actually used) — a pretrained **ECAPA-TDNN** speaker-recognition model (`speechbrain/spkrec-ecapa-voxceleb`, downloaded from Hugging Face) that produces a neural speaker embedding vector.
  5. Averages multiple segment embeddings into one canonical vector per speaker, saved as `.npy` under `data/speakers/`, and records the path + strategy in `config/speakers.yaml`.
- **`assign_speakers.py`**: for every other episode, it computes the same kind of embedding for each diarized label's segments and compares it via **cosine similarity** against the canonical host embeddings. If similarity ≥ threshold (default 0.97) and segment duration ≥ minimum (default 3s), the label is renamed to the canonical speaker (`jason`, `chamath`, `sacks`, `friedberg`); otherwise it's left as `Speaker X` and logged for manual review in `speaker_map.json`. This also produces `transcript_named.txt`.
- This step must be re-run after every new transcription to keep names consistent, and can run in parallel across the whole archive (`--all --max-concurrency N`).

### Step 4 — Prediction extraction (`prediction_pipeline.py`, extraction half)
- Loads an episode's `segments.json`, builds plain-text lines (`Speaker [hh:mm:ss.mmm]: text`), and **chunks** the transcript into ~60,000-character windows with an 8-line overlap between chunks (so predictions spanning a chunk boundary aren't lost).
- For each chunk, calls **OpenAI `gpt-5.1`** via the Responses API with **structured output** (`text_format=PredictionExtraction`, a Pydantic schema: list of `{id, who, quote, timestamp, prediction}`), using `reasoning: {effort: low}`. System prompt instructs the model to extract only concrete, falsifiable, time-bound predictions — not vague futurism.
- Deterministic IDs are generated as `<speaker-label>-<timestamp>` so re-runs are stable and dedupe-able (`dedupe_predictions`).
- Raw diarization labels are remapped to canonical speaker keys via the episode's `speaker_map.json` (`apply_speaker_map`).
- Output: `predictions.json` per episode, with a `meta.count_by_who` summary.

### Step 5 — Prediction validation (same script, `--validate`)
- For each prediction, calls `gpt-5.1` again, this time with the **`web_search` tool** enabled (no structured-output schema, because — per an inline comment — structured outputs break tool-use annotations in the Responses API). The model is instructed to return raw JSON: `{result, explanation}` where `result ∈ {right, wrong, inconclusive, ambiguous}`, and `explanation` may cite sources via markdown.
- The response's citation **annotations** (URLs, titles) are captured alongside the explanation as `sources`.
- Optional `--grok` flag additionally queries **xAI's Grok** (`grok-4-1-fast`, via `xai-sdk`, also with web search) as a second, independent verdict, stored as `grok_result`/`grok_explanation` — a way to cross-check the primary OpenAI verdict.
- Results are cached in `predictions_check.json`; re-running without `--force` reuses existing checks so already-validated predictions aren't re-billed.
- Both extraction and validation run in parallel: episodes are processed concurrently (`ThreadPoolExecutor`, `--max-concurrency`), and within an episode, individual prediction validations run concurrently too (`--validate-concurrency`), with `--validate-limit` to cap API spend per run.

### Step 6 — Tagging (`backfill_tags.py`)
- A separate pass that asks the OpenAI API to classify each prediction into zero or more topics from a fixed enum: `politics, government, conflict, venture, tech, ai, markets, economy, health, climate, science` (via a JSON-schema-constrained response). These tags power the "By Topic" chart view and the tag filter dropdown on the site.

### Shared infrastructure (`speaker_utils.py`)
Central module holding: directory constants for all four transcription providers, `ffmpeg`-based audio slicing, the MFCC/SpeechBrain embedding functions (including monkey-patches to keep older SpeechBrain code compatible with newer `huggingface_hub` APIs), YAML config load/save helpers, and the active-transcription-source switch (`set_transcripts_dir`).

### Pipeline data flow summary

```
RSS feed + YouTube ──► all_in_episodes.json (episode index)
        │
        ▼
   MP3 download ──► Speechmatics transcription ──► segments.json / transcript.txt
        │                                                  │
        │                                                  ▼
        │                                     Voice-embedding speaker ID
        │                                     (cosine sim vs canonical hosts)
        │                                                  │
        │                                                  ▼
        │                                   speaker_map.json / transcript_named.txt
        │                                                  │
        │                                                  ▼
        │                              GPT-5.1 prediction extraction ──► predictions.json
        │                                                  │
        │                                                  ▼
        │                         GPT-5.1 (+optional Grok) web-search validation
        │                                                  │
        │                                                  ▼
        │                                     predictions_check.json
        │                                                  │
        │                                                  ▼
        │                                     GPT tag classification ──► tags on predictions
        │
        ▼
   youtube_url attached to episode ──────► used for deep-link timestamps in the UI
```

## 4. On-disk data format (what the web app actually reads)

For each episode directory `data/processed/transcripts_speechmatics/<episode_id>/`:
- `metadata.json` — `{episode_id, title, published, description, duration, audio_filename}` (sometimes `youtube_url`, `published_iso`)
- `segments.json` — diarized transcript segments
- `predictions.json` — `{meta: {count, count_by_who}, predictions: [{id, who, quote, timestamp, prediction, tags?}]}`
- `predictions_check.json` — `{meta: {count, count_by_result}, predictions: [{id, result, explanation, sources[], grok_result?, grok_explanation?}]}`

The web app never talks to a database — it reads these JSON files directly off disk at **build time**.

## 5. The website (`web/`, Next.js 14 App Router)

### Framework & deployment
- Next.js 14.2 with `output: 'export'` in `next.config.mjs` — meaning the entire site is **statically generated** (SSG) into plain HTML/JS at build time; there is no server runtime. This is what allows it to be deployed on **Cloudflare Pages** (hence the `.pages.dev` domain).
- Styling: Tailwind CSS, dark theme (`bg-[#080d0b]`, white text).
- Charting: `chart.js` + `react-chartjs-2` (doughnut charts for host accuracy, stacked bar charts for by-year/by-topic breakdowns).
- Markdown rendering: `react-markdown` for validation explanations (which the LLM writes with citations/links).

### Data loading layer (`web/lib/data.ts`)
- At build time, reads every episode's `metadata.json`, `predictions.json`, and `predictions_check.json` directly from `../../data/processed/transcripts_speechmatics/` (relative to the `web/` package — i.e., reaching outside the Next.js project into the sibling `data/` folder).
- **Filters predictions to only the four named hosts** (`jason, chamath, friedberg, sacks`) — predictions attributed to guests or unresolved "Speaker X" labels are dropped from the site entirely (`VALID_SPEAKERS` set). This matches the `AGENTS.md` note that the UI "filters predictions to named speakers only."
- Merges each prediction with its validation result (if any) and parses the `hh:mm:ss.mmm` timestamp into `timestamp_seconds` for YouTube deep-linking.
- Computes per-episode and global aggregate stats (`count_by_who`, `count_by_result`).
- Encodes each prediction's ID with a custom **base62 encoder** (`base62.ts`) for use in clean, short, non-guessable-looking URL slugs (`/episodes/<id>/prediction/<encoded_id>`), decodable back to the original `speaker-timestamp` ID.
- Builds an in-memory `Map` index of `"<host>::<encoded_id>" → {prediction, episode}` for O(1) lookups on host/prediction detail pages, built once and cached module-level (fine for a build-time-only static export).

### Stats/aggregation layer (`web/lib/stats.ts`)
Three aggregation functions, all driven by a common `EMPTY_BUCKET = {right, wrong, ambiguous, inconclusive, unvalidated}` shape and an optional topic-tag filter:
- `aggregateHostStats` — totals per host, optionally filtered by tag.
- `buildYearlyStats` — per-host, per-year breakdown (parses `published_iso`/`published` to extract UTC year).
- `buildTopicStats` — per-host, per-topic-tag breakdown; a prediction with multiple tags counts toward each (unless a specific tag filter is active, in which case only that tag counts).
- `collectTags` — the master sorted list of all tags seen across all predictions, used to populate the topic filter dropdown.

### Pages (App Router, all statically generated via `generateStaticParams`)
- `/` (`page.tsx`) — home page: renders `<HostCharts>` (the interactive scorecards) plus a preview grid of the 6 most recent episodes. Strips `prediction`/`quote`/`explanation` text out of the payload sent to the client component to cut bundle size, since the home page charts only need counts.
- `/episodes` — full episode listing.
- `/episodes/[id]` — one episode's predictions rendered as `PredictionCard`s.
- `/episodes/[id]/prediction/[encodedId]` — a single prediction's permalink/detail view.
- `/host/[hid]` — one host's full prediction history (`HostPredictionsList`), with the same tag filter as the homepage.
- `/host/[hid]/predictions` — presumably a fuller/paginated list variant (same data source).
- `/about` — static about page.

### Key components
- **`HostCharts.tsx`** (client component) — the flagship UI: for each host, a toggle between three views:
  - **Total** — a doughnut chart of right/wrong/ambiguous/inconclusive percentages, with a "Resolved only" checkbox that collapses the view to just right/wrong (removing ambiguous/inconclusive from the denominator) to show a cleaner "accuracy rate."
  - **By Year** — stacked percentage bar chart per host, one bar per year.
  - **By Topic** — stacked percentage bar chart per host, one bar per topic tag (also forces the tag filter to "All" since topic *is* the axis here).
  - A `TagFilter` dropdown further narrows all charts to a single topic.
- **`Prediction.tsx`** (`PredictionCard`) — renders one prediction: speaker badge, episode code + timestamp, colored result badge (green=right, red=wrong, amber=ambiguous, gray=inconclusive, slate=unvalidated) with a hover tooltip explaining what each status means (from `lib/const.ts`), the normalized prediction text, the original quote in a blockquote, a YouTube deep-link, and (collapsible) the LLM's markdown-formatted validation explanation with citation links.
- **`YoutubeLink.tsx`** — appends `?t=<seconds>` to the episode's YouTube URL for a deep link. Shows a **one-time warning modal** ("timestamp links are best-effort...") gated by a `localStorage` flag (`predict_timestamp_notice_seen`) before the first-ever outbound YouTube click. If no YouTube URL could be matched for the episode, shows a plain tooltip instead of a link.
- **`TagFilter.tsx`**, **`Collapsible.tsx`**, **`HostPredictionsList.tsx`**, **`WarningBanner.tsx`** (a global disclaimer banner) round out the UI.

### Notable UX/engineering details
- `prefetch={false}` on nearly every `<Link>` — deliberately disables Next.js's automatic route prefetching, likely to avoid excessive requests on a fully static site with many generated pages (hundreds of episodes × predictions × hosts).
- The footer carries a permanent disclaimer that data is AI-generated (transcription + speaker-matching + LLM extraction/validation) and "may contain errors, omissions, or misattributions" — an explicit acknowledgment of the pipeline's imperfection (voice-ID threshold misses, YouTube timestamp mismatches, LLM validation mistakes).
- "Resolved only" toggle exists because a large fraction of predictions are naturally `inconclusive` (not enough time has passed) or `ambiguous` — the toggle lets viewers see a "win rate among predictions we could actually judge."

## 6. How it all fits together end-to-end

1. A cron/manual run of `all_in_downloader.py` keeps the episode index and audio archive current.
2. New episodes get transcribed (Speechmatics), speaker-identified via voiceprint cosine similarity against 4 canonical host embeddings, mined for predictions by GPT-5.1, fact-checked by GPT-5.1 (+ optionally Grok) using live web search, and tagged by topic — all cached to JSON so reruns are cheap and idempotent.
3. The Next.js site statically reads that JSON tree at build time, computes aggregate accuracy stats per host/year/topic, and exports a fully static site (no backend/database at runtime) deployed to Cloudflare Pages.
4. End users browse a "batting average" scorecard for each All-In host, drill into individual episodes or predictions, and jump straight to the moment in the original YouTube video where the prediction was made — with every claim traceable back to a transcript quote and a web-search-sourced validation explanation.

## 7. Observations / things worth knowing if you extend this fork

- **Cost control levers**: `--limit`, `--validate-limit`, `--force`, and concurrency flags throughout the pipeline exist specifically to let you smoke-test on 1–2 episodes before spending OpenAI/web-search credits on the full ~327-episode archive.
- **Secrets**: `.env` (gitignored, `.env.example` present) holds `OPENAI_API_KEY`, `XAI_API_KEY`, and ASR provider keys (Speechmatics, Deepgram, AssemblyAI). None of these are present in this checkout — you'd need to populate `.env` to run the pipeline yourself.
- **Reproducibility caveat**: this is a fork with no `.git` history beyond 2 commits, and the large `data/` tree, while present here, is not tracked by git — so it exists only in this local working copy (likely copied over or pre-generated), not recoverable via `git log`/`git show`.
- **Extensibility**: `README.md` explicitly notes the pipeline is podcast-agnostic and "could be forked and modified to evaluate other podcasts with minor modifications" — the host roster (`config/speakers.yaml`), RSS feed URL, and YouTube channel are the main hard-coded All-In-specific bits.
- **Two independent LLM judges**: the optional Grok cross-check (`--grok`) is a deliberate hedge against single-model bias/hallucination in the validation step, though the UI doesn't currently appear to surface `grok_result` distinctly from the primary OpenAI result (worth checking if you want to display both).
