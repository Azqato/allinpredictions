# All-In Predictions

Tracks predictions made on the All-In Podcast (Jason Calacanis, Chamath Palihapitiya, David Sacks, David Friedberg, plus guests) and checks whether they came true, with quotes, timestamps, YouTube links, and cited research behind every verdict.

**Live site:** https://azqato.github.io/allinpredictions/

## What the site offers

- Per-host accuracy scorecards (right / wrong / ambiguous / inconclusive), filterable by topic, by year, and by resolved-only status.
- Every episode's predictions, each with the original quote, a timestamped YouTube deep link, and (once validated) a cited explanation of how it turned out.
- Guest scorecards alongside the four permanent hosts, so predictions from a one-off guest appearance are tracked too, not just the regulars.

## Who it's for

Anyone curious how often the All-In hosts (and their guests) turn out to be right when they make a concrete, checkable prediction on the show.

## Current status

Live and working, with an archive of hundreds of episodes still being processed incrementally: new episodes are extracted and validated in ongoing batches, and predictions not yet checked are clearly labeled "Unvalidated" rather than guessed at.

## Documentation

Everything about how this project works, why it's built this way, and where it's headed lives in [docs/](docs/):
- [docs/PRD.md](docs/PRD.md): what this is, why, architecture, data model, roadmap, and everything else about project direction
- [docs/DESIGN.md](docs/DESIGN.md): visual/UX system (colors, type, spacing, breakpoints, components)
- [docs/PATCHNOTES.md](docs/PATCHNOTES.md): dated changelog
