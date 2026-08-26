# All-In Predictions (Rewrite)

Tracks predictions made on the All-In Podcast and checks whether they came true, using free-only tooling (YouTube captions, no paid ASR) and Claude Code (no OpenAI/xAI API calls) for extraction, attribution, tagging, and validation.

**Live site:** not yet deployed. See [docs/PRD.md](docs/PRD.md) §11 for the deployment plan and §15 for what "live" requires.

## Tech stack

| Component | Tool | Version (as installed) |
|---|---|---|
| Language | Python | 3.14.3 |
| Episode/caption discovery | yt-dlp | 2026.7.4 |
| Caption fetching | youtube-transcript-api | 1.2.4 |
| Templating | Jinja2 | 3.1.6 |
| Config parsing | PyYAML | 6.0.3 |
| Analysis (extraction/attribution/tagging/validation) | Claude Code (this agent), no SDK | n/a |
| Frontend | Vanilla HTML/CSS/JS, no framework, no build step | n/a |
| Hosting (planned) | GitHub Pages | n/a |

Exact pinned versions are in [requirements.txt](requirements.txt) (minimum-version pins; the table above reflects what's actually installed in the working environment as of the last verification).

## Prerequisites

- Python 3.9+ (developed against 3.14.3)
- `pip` for installing dependencies
- No API keys required for any step

## Installation

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Running locally

The pipeline has two kinds of steps: deterministic Python scripts (run directly), and Claude-driven analysis steps (run through a Claude Code session, not a standalone script).

**1. Mechanical steps** (episode discovery → captions → chunks → manifest):

```bash
python scripts/fetch_episodes.py --limit 5           # discover episodes, resolve YouTube video ids
python scripts/compare_episode_sources.py             # cross-check vs. old repo's episode data (QA only)
python scripts/fetch_transcripts.py --limit 5          # pull YouTube captions (free, no API key)
python scripts/prepare_chunks.py                       # normalize + chunk transcripts for Claude
python scripts/build_manifest.py                       # refresh data/manifest.json
```

**2. Claude-driven analysis steps** (extraction, speaker/guest attribution, topic tagging, validation): performed by Claude Code directly inside a session, reading `data/chunks/*` and writing `data/predictions/*.json` and `data/checks/*.json`, following the instructions in `prompts/extract_and_tag.md` and `prompts/validate.md`. There is no script to run for this step and no third-party LLM API call anywhere in the pipeline; see [docs/PRD.md](docs/PRD.md) §6 and §10 for the full process, including the batching process for scaling to the full archive.

**3. Site generation** (deterministic, no LLM):

```bash
python scripts/generate_site.py
python -m http.server 8000      # from the rewrite/ root; preview at http://localhost:8000
```

`generate_site.py` writes `index.html`, `about.html`, `episodes/`, `host/`, and `static/` directly into the `rewrite/` root (not a subfolder); see [docs/PRD.md](docs/PRD.md) §8.1 for why.

## Environment variables

None required. This project has no paid API keys, no secrets, and no `.env` file. If this ever changes, this section and `docs/PRD.md` §23 (Security) must both be updated before committing anything that reads an environment variable.

## Build and deploy

There is no separate "build" step beyond `python scripts/generate_site.py` (see above): it *is* the build. To deploy:

1. Run `scripts/generate_site.py` to regenerate the site files at the `rewrite/` root.
2. Commit the generated files (`index.html`, `about.html`, `episodes/`, `host/`, `static/`) alongside the source changes.
3. Push to the repository's default branch.
4. In GitHub repo settings → Pages, set **Deploy from branch → main / (root)**.

No CI pipeline is required or used for v1; see [docs/PRD.md](docs/PRD.md) §11 for the full deployment plan, including the deferred optional GitHub Action for the deterministic-only regeneration step.

## Documentation

Full requirements, architecture, data schemas, design system, decisions log, roadmap, and changelog live in [docs/](docs/):
- [docs/PRD.md](docs/PRD.md): what this is, why, architecture, data model, roadmap, and everything else about project direction
- [docs/DESIGN.md](docs/DESIGN.md): visual/UX system (colors, type, spacing, breakpoints, components)
- [docs/PATCHNOTES.md](docs/PATCHNOTES.md): dated changelog
