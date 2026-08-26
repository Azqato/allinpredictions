# Patch Notes

All notable changes to this project, in reverse chronological order. Format: semantic version, date (YYYY-MM-DD), then Added/Changed/Fixed/Removed sections with one line per change, past tense.

## v0.5.0 (2026-08-04)

### Added
- Manually extracted predictions (no sub-agents, per the standing project-specific rule) for the remaining 47 episodes that had transcripts and chunks but no `data/predictions/<episode_id>.json` file yet, closing out the extraction backlog left after the v0.4.0 sub-agent incident. Extraction followed `prompts/extract_and_tag.md` sequentially, chunk-by-chunk, favoring a small number of genuinely falsifiable, forward-looking, timestamped predictions per episode over padding with vague or retrospective statements.
- Regenerated `data/manifest.json`: all 128 chunked episodes now have `predictions_extracted: true` (0 chunked episodes remain without a predictions file).

### Status snapshot (as of this release, not a target)
- 128/128 chunked/captioned episodes now have `data/predictions/<episode_id>.json`; the extraction sweep against currently-available transcripts is complete.
- 357/404 unique archive episodes have a predictions file in total (includes episodes adapted earlier from `data/processed`, outside the chunk pipeline).
- Of the 404 total archive episodes, 45 remain blocked on a resolvable YouTube `video_id` (deferred, to be resolved manually later per standing decision) and 2 have a `video_id` but no captions available via any current fetch method — neither category has transcripts/chunks yet, so neither was in scope for this sweep.
- 22 episodes have gone through the validation sweep (`data/checks/`); the full-archive validation sweep against all 357 predictions files remains deferred until video_id resolution and caption-less-episode handling are addressed, per the two-sweep process in PRD.md §13.

## v0.4.0 (2026-08-04)

### Added
- Fetched transcripts for 97 of the 144 previously fully-missing episodes (via the `youtube_transcript_api` → `yt-dlp` → tactiq.io/headed-Edge fallback chain in `fetch_transcripts.py`), bringing the archive's total captioned-episode count to 128/402.
- Chunked all 97 newly-fetched transcripts via `prepare_chunks.py` (429 chunks total across 128 chunked episodes).
- Extracted predictions for 25 additional episodes via parallel Claude sub-agents following `prompts/extract_and_tag.md`, before the batch was intentionally halted (see Fixed).

### Fixed
- A parallel sub-agent extraction batch (intended as ~10 concurrent agents, one per small episode group) was found to be recursively spawning further sub-agents per episode instead of working its assigned list sequentially, ballooning to 30+ concurrent agents and consuming the usage budget far faster than expected. All agents were stopped mid-batch once discovered; 25/97 targeted episodes had already completed extraction by that point. Going forward, sub-agent batches are capped at 5 concurrent and must not spawn further sub-agents (tracked as a standing operating rule, not a one-off fix).
- `data/episodes.json` had been left scoped to a 97-episode working subset (from staging the extraction batch above) instead of the full archive; restored to the full 402/404-episode list and regenerated `data/manifest.json` against it.

### Status snapshot (as of this release, not a target)
- 283/402 unique archive episodes have `data/predictions/<episode_id>.json` (~70%).
- Of the 119 remaining: 72 already have transcripts + chunks and are ready for extraction with no further fetch work needed; 47 are blocked on captions — 45 lack a resolvable YouTube `video_id` (deferred, to be resolved manually later per standing decision) and 2 have a `video_id` but no captions available via any current fetch method.
- 22 episodes have gone through the validation sweep (`data/checks/`); the full-archive validation sweep remains deferred until the extraction sweep is complete, per the two-sweep process in PRD.md §13.

## v0.3.0 (2026-08-04)

### Added
- `docs/DESIGN.md`: visual/UX system documentation (color palette, typography, spacing, breakpoints, component patterns, accessibility notes, animation rules), derived from the actual `site_src/static/style.css` and templates.
- `docs/PATCHNOTES.md` (this file).

### Changed
- Moved `PRD.md` from `rewrite/` root to `rewrite/docs/PRD.md`, per the documentation-consolidation folder standard (README.md stays root-only).
- Rewrote `README.md` to the developer-facing spec: tech stack table with verified installed versions, prerequisites, exact install/run/build/deploy commands, explicit "no environment variables" statement, links into `docs/`.
- Expanded `docs/PRD.md` with the sections required by the documentation-audit standard that didn't exist yet: Tenets (§18), Roadmap (§19), Metrics (§20), Runbook (§21), Technical Requirements Summary (§22), Security (§23), Press Release (§24), FAQ (§25), and Writing Style (§26, the em-dash/double-dash policy, now being followed prospectively in all new content ahead of the formal sweep).
- Changed `scripts/generate_site.py`'s site output location from `rewrite/docs/` to the `rewrite/` root directly (`index.html`, `about.html`, `episodes/`, `host/`, `static/`), so the working directory now matches the eventual final repo-root layout and `docs/` is reserved exclusively for documentation instead of colliding with GitHub Pages' `/docs`-as-site-output convention.
- Updated `docs/PRD.md` §8 (repo structure), §8.1 (new: rationale for the root-output change), and §11 (deployment) to reflect **GitHub Pages → Deploy from branch → main / (root)** instead of `/docs`.

### Fixed
- `scripts/generate_site.py` no longer wipes its entire output directory on rebuild (`shutil.rmtree(out_dir)`); it now only removes its own known generated top-level paths (`index.html`, `about.html`, `episodes/`, `host/`, `static/`), since the output directory is now the same directory that holds source folders (`scripts/`, `data/`, `config/`, `site_src/`, `prompts/`, `docs/`) that must never be touched by a site rebuild.

## v0.2.0 (2026-08-04)

### Changed
- Replaced the initial arbitrary 5-episode sample set with 9 chronologically-relevant episodes chosen for their content density: 5 annual "predictions" specials (E061/2022, E110/2023, E160/2024, the 2025 episode with guest Gavin Baker, and the 2026 episode) and 4 year-end "Bestie Awards" retrospectives (E015/2020, E060/2021, E109/2022, E159/2023).

### Added
- `config/youtube_urls_override.json` for manual episode-id → YouTube-video-id overrides, used for the one target episode (the 2025 predictions episode) that automatic title/episode-code matching couldn't resolve.
- Extracted 81 predictions and validated 26 of them (with cited web-research explanations) across all 9 target episodes, populating `data/predictions/*.json` and `data/checks/*.json` for each.
- A guidance addition to `prompts/extract_and_tag.md`: for solo two-person guest-interview episodes (as opposed to the usual four-host panel format), default the non-guest speaker to `jason` at `medium` confidence rather than leaving him `unknown`, based on a real attribution gap found during the Phase 2 validation-gate review.

## v0.1.1 (2026-08-04)

### Fixed
- Host and episode pages (`host/*.html`, `episodes/*.html`) were rendering completely unstyled: `asset_prefix` was being set via `{% set %}` inside a child template's `content` block, but the base template's `<head>`/header (which reference `asset_prefix` for the stylesheet link and nav links) render before that block executes, so the CSS path resolved incorrectly one directory level off. Fixed by passing `asset_prefix` as an explicit argument to each affected template's `.render(...)` call in `generate_site.py` instead.
- Fixed a "Back home" link on host pages that incorrectly pointed at `index.html` (resolving to a nonexistent `host/index.html` given the page's own location) instead of `../index.html`.

## v0.1.0 (2026-08-04)

Initial MVP build (Phases 0-3 of the rewrite plan).

### Added
- Project scaffolding: `config/hosts.yaml`, `config/tags.json`, `requirements.txt`, initial `README.md`, initial `PRD.md`.
- Mechanical pipeline scripts: `fetch_episodes.py` (RSS + yt-dlp YouTube matching, cross-checked against allin.com/episodes numbering), `compare_episode_sources.py` (QA diff against the original project's already-resolved episode data), `fetch_transcripts.py` (YouTube captions via `youtube-transcript-api`, with a `yt-dlp --write-auto-sub` fallback), `prepare_chunks.py` (transcript normalization/chunking), `build_manifest.py` (per-episode pipeline status tracking for incremental runs).
- Claude-driven analysis prompts: `prompts/extract_and_tag.md`, `prompts/validate.md`.
- Static site generator (`scripts/generate_site.py`), Jinja2 templates (`base.html`, `index.html`, `episodes_index.html`, `episode.html`, `host.html`, `host_index.html`, `about.html`), hand-rolled inline-SVG donut/bar charts, `style.css`, and `app.js` (YouTube-link disclaimer modal, chart-toggle interactivity).
- End-to-end proof of concept: fetched and processed a sample of episodes, extracted and validated a handful of predictions per episode via Claude with `WebSearch`, and generated a working local site confirming the full pipeline (RSS → captions → chunks → Claude extraction → Claude validation → static site) functions with zero paid APIs.
