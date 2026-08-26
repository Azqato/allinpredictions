# Patch Notes

All notable changes to this project, in reverse chronological order. Format: semantic version, date (YYYY-MM-DD), then Added/Changed/Fixed/Removed sections with one line per change, past tense.

## v0.13.0 (2026-08-26)

### Added
- Validated a seventh batch of predictions (20 episodes, fewest-predictions-first per the standing sweep order; the third of five 20-episode batches requested toward a 100-episode sweep), bringing the archive-wide validated count to 132/357. 116 individual predictions were checked (right/wrong/ambiguous/inconclusive with cited sources), the largest single batch of the sweep so far.

## v0.12.0 (2026-08-26)

### Added
- Validated a sixth batch of predictions (20 episodes, fewest-predictions-first per the standing sweep order; the second of five 20-episode batches requested toward a 100-episode sweep), bringing the archive-wide validated count to 112/357. 77 individual predictions were checked (right/wrong/ambiguous/inconclusive with cited sources); two episodes (h-1b-shakeup..., E069) had 0 qualifying predictions and were written as empty, explicitly-processed check files.

## v0.11.0 (2026-08-26)

### Added
- Validated a fifth batch of predictions (20 episodes, fewest-predictions-first per the standing sweep order; the first of five 20-episode batches requested toward a 100-episode sweep), bringing the archive-wide validated count to 92/357. 67 individual predictions were checked (right/wrong/ambiguous/inconclusive with cited sources), including several conditional predictions (Ryan Cohen's eBay takeover, Reza and Shervin's Iran regime-change predictions in E536) scored `inconclusive` because their premise wasn't fulfilled rather than forcing a right/wrong verdict.

## v0.10.0 (2026-08-26)

### Added
- Validated a fourth batch of predictions (20 episodes, fewest-predictions-first per the standing sweep order), bringing the archive-wide validated count to 72/357. 41 individual predictions were checked (right/wrong/ambiguous/inconclusive with cited sources); the joe-manchin episode had 0 qualifying predictions (both were low-confidence unattributed lines), so its `data/checks/<episode_id>.json` was written as an empty, explicitly-processed file rather than left missing.

## v0.9.0 (2026-08-26)

### Added
- A data-validation layer in `generate_site.py`: `load_all_data()` now checks every prediction/check record that would actually render as a speaker card and raises `DataValidationError` with a full report before generating any HTML, instead of silently rendering bad data. Catches a missing/placeholder `who`, an invalid `role`, a permanent host tagged `role: "guest"`, a `who` that's a near-miss (Levenshtein distance <=2) of a permanent host slug (the exact shape of the freeberg/unknown incident), and check `result` values outside `right/wrong/ambiguous/inconclusive`. Records that never reach the page (low-confidence unattributed lines, e.g. `who: "unknown-c"`) are intentionally left unvalidated.

### Fixed
- `scripts/fetch_episodes.py`'s yt-dlp lookup was silently failing on this project's Windows dev environment: `yt-dlp` is pip-installed as a Python module only, not a standalone binary on PATH, so `fetch_ytdlp_playlist()`'s `subprocess.run` raised `FileNotFoundError`, which was caught and logged only as a warning, degrading video_id resolution to 2/411 episodes with no hard failure. Fixed by shlex-splitting the configured `--yt-dlp-path` and automatically falling back to `<this interpreter> -m yt_dlp` when the primary command isn't found; verified via a live smoke test (14/20 resolved with zero flags, up from 2/20).
- 8 predictions across `data/predictions/E002.json`, `E003.json`, `E005.json`, `E006.json`, `E008.json`, `E009.json` had David Sacks tagged `role: "guest"` instead of `"host"`, a real pre-existing data bug surfaced by the new validation layer above (masked in live output only because `build_speaker_index()` pre-seeds all four permanent hosts before the episode loop runs, so the bug never reached the page, but the raw data was wrong).

### Changed
- `docs/PRD.md` §31 open question about `data/manifest.json`'s `generated_at` staleness marked resolved: `build_manifest.py` sets it unconditionally on every run and was never buggy, the timestamp that looked stale during the 2026-08-25 audit simply hadn't been refreshed since 2026-08-05 yet at that point in the session.
- `docs/PRD.md` §21 Runbook's Common Errors table gained two new rows (the yt-dlp fix above and the new `DataValidationError` failure mode).

## v0.8.0 (2026-08-25)

### Added
- Validated a third batch of predictions (20 episodes, fewest-predictions-first per the standing sweep order), bringing the archive-wide validated count to 52/357. 14 individual predictions were checked (right/wrong/ambiguous/inconclusive with cited sources); the remaining 6 of the 20 episodes had 0 qualifying predictions in their extraction file, so their `data/checks/<episode_id>.json` was written as an empty, explicitly-processed file rather than left missing.

## v0.7.0 (2026-08-25)

### Added
- Validated a second batch of predictions (episodes E010-E020, 155 predictions), bringing the archive-wide validated count to 32/357.
- Home page filter controls (pre-launch parity pass, PRD.md §27): a "resolved only" checkbox, a topic-filter dropdown, and a Total/By Year/By Topic segmented toggle per host scorecard, all recomputed client-side by a rewritten `app.js` from a per-card `data-entries` JSON attribute. Added a matching `stacked_bar_svg`-equivalent rendering path alongside the existing donut chart.
- A "Last updated: <date>" label in the site header, computed at generation time from the current date, not hand-maintained.
- A dismissible welcome banner on the home page, matching the original site's disclaimer banner, gated behind its own `localStorage` flag.
- `.nojekyll` at the repo root so GitHub Pages serves the static output without Jekyll processing it.
- Six new PRD sections that this documentation-audit pass found genuinely missing: Conventions, Browser Testing, Deprecation and Removal, Documentation Versus Reality, Risks and Open Questions, and Working Practice (docs/PRD.md §28-§33).

### Changed
- **MVP launched to production.** Promoted the former `rewrite/` directory's contents to the repo root; archived the old (paid-API) pipeline into `old/` rather than deleting it. This moved up the site's public launch to *before* the full-archive validation sweep finishes, per an explicit sequencing change (Decisions Log §14.5, Roadmap §19) - the remaining validation work, the mobile-responsive audit (§16.3), and the Annual Predictions filter (§17) all continue as ongoing work against the now-live site instead of gating the first deploy.
- Rewrote `README.md` from a developer-facing quickstart (tech-stack table, install commands, environment-variable section) to a general-reader front door: what the site is, who it's for, a link to the live URL, and a pointer into `/docs` for everything else. The install/version/runbook content it used to carry lives in `docs/PRD.md`'s Runbook (§21) and Technical Requirements (§22) sections instead, which already covered the same ground.
- Ran a full documentation audit and rewrite of `docs/PRD.md`, `docs/DESIGN.md`, and this file: reconciled every stale `rewrite/`-as-subfolder path reference against the actual post-restructure repo layout, updated the Roadmap (§19) and every "Planned"/"post-launch" status line that had since actually shipped, and logged every discrepancy found between the docs and the live codebase in a new Documentation Versus Reality table (§29) instead of silently correcting them.
- Ran the writing-style sweep (§16.2) - originally scheduled for a post-launch window - in this same pass instead, per explicit request: replaced 166 em dashes across `docs/PRD.md`/`docs/PATCHNOTES.md`, one leftover `&mdash;` reference, and prose double dashes in `config/hosts.yaml`, `prompts/*.md`, and script docstrings/comments, using a colon after labeled terms and a spaced hyphen elsewhere. Extended the Writing Style rule (§26) with a fifth replacement option (a single hyphen, encouraged in titles/headings/version lines) per a live instruction, without discarding the original four-option rule. Deliberately left untouched, as a stated exception: verbatim transcript quotes and citation titles in `data/predictions/*.json`/`data/checks/*.json`, since altering their punctuation would misrepresent the source.

### Fixed
- **Live-site bug:** two prediction files had a `freeberg` typo instead of `friedberg` in their `who`/`id` fields, and several `unknown`-speaker predictions had a bare `role: "host"` or `role: "unknown"` instead of `null` - both bypassed `build_speaker_index()`'s permanent-host check in `generate_site.py` and produced bogus "Freeberg" and "Unknown" scorecards on the live site. Fixed via targeted edits (not a full JSON re-serialization, to keep the diff scoped) across the six affected prediction files, regenerated, and confirmed fixed on the live GitHub Pages URL.

## v0.6.0 (2026-08-25)

### Added
- Manually extracted predictions for episodes E018, E019, and E020 (superseded by the broader E010-E020 batch recorded under v0.7.0 above, listed here for completeness since it was a separate step in this session).

### Status snapshot (as of this release, not a target)
- 357/357 currently-extractable episodes have `data/predictions/<episode_id>.json` (unchanged from v0.5.0; this release only added validation coverage, not new extractions).
- 32/357 episodes validated after this batch.

## v0.5.0 (2026-08-04)

### Added
- Manually extracted predictions (no sub-agents, per the standing project-specific rule) for the remaining 47 episodes that had transcripts and chunks but no `data/predictions/<episode_id>.json` file yet, closing out the extraction backlog left after the v0.4.0 sub-agent incident. Extraction followed `prompts/extract_and_tag.md` sequentially, chunk-by-chunk, favoring a small number of genuinely falsifiable, forward-looking, timestamped predictions per episode over padding with vague or retrospective statements.
- Regenerated `data/manifest.json`: all 128 chunked episodes now have `predictions_extracted: true` (0 chunked episodes remain without a predictions file).

### Status snapshot (as of this release, not a target)
- 128/128 chunked/captioned episodes now have `data/predictions/<episode_id>.json`; the extraction sweep against currently-available transcripts is complete.
- 357/404 unique archive episodes have a predictions file in total (includes episodes adapted earlier from `data/processed`, outside the chunk pipeline).
- Of the 404 total archive episodes, 45 remain blocked on a resolvable YouTube `video_id` (deferred, to be resolved manually later per standing decision) and 2 have a `video_id` but no captions available via any current fetch method - neither category has transcripts/chunks yet, so neither was in scope for this sweep.
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
- Of the 119 remaining: 72 already have transcripts + chunks and are ready for extraction with no further fetch work needed; 47 are blocked on captions - 45 lack a resolvable YouTube `video_id` (deferred, to be resolved manually later per standing decision) and 2 have a `video_id` but no captions available via any current fetch method.
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
