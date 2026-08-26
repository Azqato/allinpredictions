# Repository Guidelines

## Project Structure & Module Organization
- Source scripts live in `scripts/` (transcription, speaker assignment, prediction extraction).
- Data artifacts are under `data/processed/...` (transcripts, speaker maps, predictions) and `data/audio/...` for inputs.
- Configuration is in `config/` (e.g., `speakers.yaml`), and Python deps are listed in `requirements.txt`.
- New files should stay within the existing layout; place new utilities in `scripts/` alongside peers.

## Build, Test, and Development Commands
- Create/activate venv: `python3 -m venv .venv && source .venv/bin/activate`.
- Install deps: `.venv/bin/pip install -r requirements.txt`.
- Type/check syntax quickly: `.venv/bin/python -m py_compile scripts/*.py`.
- Run pipelines:
  - Assembly/Deepgram/OpenAI/Speechmatics transcription scripts in `scripts/`.
  - Assign speakers: `.venv/bin/python scripts/assign_speakers.py --episode-id ALLIN-E000 --transcription speechmatics --strategy speechbrain`.
  - Build embeddings: `.venv/bin/python scripts/build_speaker_profiles.py ...`.
  - Prediction extraction: `.venv/bin/python scripts/prediction_pipeline.py --episode-id ALLIN-E000 --transcription speechmatics`.
  - Downloader now fetches YouTube URLs via `yt-dlp` (see notes below): `python scripts/all_in_downloader.py --use-ytdlp`.

## Coding Style & Naming Conventions
- Python 3.9+; prefer type hints and dataclasses where helpful.
- Follow existing patterns: small, single-purpose functions; explicit error messages via `SystemExit`.
- Use snake_case for variables/functions, PascalCase for classes, and UPPER_SNAKE for constants.
- Keep line-oriented JSON writing with `indent=2`; timestamps use `hh:mm:ss.mmm`.
- New scripts should support batch mode (`--all` or similar) with `ThreadPoolExecutor` for parallelism and a `--force` flag to overwrite existing outputs.

## Testing Guidelines
- No formal test suite; sanity check changes with `py_compile` and by running relevant scripts on a small episode subset (`--limit` / `--force` flags).
- Favor deterministic outputs (e.g., deterministic IDs in prediction extraction).
- When touching speaker mapping or embeddings, rerun a single episode before scaling to `--all`.

## Commit & Pull Request Guidelines
- Write concise commits in imperative mood (e.g., “add speechbrain strategy to embeddings”).
- In PRs, summarize scope, list key commands run, and note output locations (`data/processed/...`).
- Attach logs or sample snippets when changing LLM prompts, pipelines, or data formats.

## Security & Configuration
- Secrets via `.env` (e.g., `OPENAI_API_KEY`, provider keys); do not commit `.env`.
- Respect sandboxed data paths; avoid writing outside `data/`/`config/`/`scripts/` without discussion.

## Session Notes / Special Handling
- YouTube URLs: RSS only exposes ~15 items; we fetch the full uploads via `yt-dlp` (`@allin/videos`). Episode codes (E1/E001) are parsed for matching; manual overrides can go in `config/youtube_urls.json`. Current automatic coverage ~87%.
- Predictions: web UI renders timestamps as YouTube deep links; first click shows a warning (localStorage flag). Unmatched timestamps show a tooltip instead of a link.
- Validation: `prediction_pipeline.py` can run extraction/validation separately, with `--validate-limit` and `--validate-concurrency` to throttle per-episode checks; `--force` redoes existing outputs.
- Theme: web app uses Tailwind (dark background `#080d0b`, white text) and filters predictions to named speakers only (jason/chamath/friedberg/sacks).
