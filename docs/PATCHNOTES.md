# Patch Notes

All notable changes to this project, in reverse chronological order. Format: semantic version, date (YYYY-MM-DD), then Added/Changed/Fixed/Removed sections with one line per change, past tense.

## v0.36.0 (2026-08-27)

### Added
- Ran Batch 3 of the incremental process (PRD §13) against the 47-episode unprocessed backlog (third of the "5 batches as a test" run): resolved 5 more missing `video_id`s via WebSearch, fetched transcripts and chunks, then ran full extraction+attribution+tagging and validation in one pass for all 5 episodes -- miami-mayor-francis-suarez-the-recipe-for-creating-america-s-happiest-city-all-in-live-from-miami (0 predictions, city-governance/policy discussion without falsifiable dated claims), energy-secretary-chris-wright-on-the-future-of-american-energy-all-in-summit-2025 (2 predictions), the-new-era-of-the-stock-market-with-nasdaq-ceo-adena-friedman-all-in-summit-2025 (0 predictions, market-structure/business discussion without falsifiable dated claims), how-to-save-america-mark-cuban-and-tucker-carlson-debate-all-in-summit-2025 (0 predictions, healthcare-policy advocacy and cultural commentary without falsifiable dated claims), and winning-the-ai-race-part-1-michael-kratsios-kelly-loeffler-chris-power-shyam-sankar-paul-buchheit-jake-loosararian (2 predictions, from Chris Power and Paul Buchheit; the AI Action Plan, Shyam Sankar, Jake Loosararian, and Kelly Loeffler segments were policy/opinion discussion without clean falsifiable claims). 4 predictions checked (right/wrong/ambiguous/inconclusive with explanations): Chris Wright's small-modular-reactor-criticality-at-Idaho-National-Laboratory-by-July-4-2026 prediction came back right (DOE's Reactor Pilot Program hit the deadline, with Antares Nuclear achieving criticality at INL on June 4, 2026), his 50-year solar-share bet was marked inconclusive (timeframe far from elapsed), Chris Power's Arizona-factory-launch prediction came back ambiguous (Hadrian's Mesa "Factory 3" opened January 29, 2026 -- close to but past the "by Christmas 2025" framing he also gave), and Paul Buchheit's 20-year AI-drug-prediction claim was marked inconclusive. This is the third incremental-process batch against the previously-unprocessed backlog; 32 backlog episodes remain, with 2 more test batches planned.

## v0.35.0 (2026-08-27)

### Added
- Ran Batch 2 of the incremental process (PRD §13) against the 47-episode unprocessed backlog (second of the "5 batches as a test" run): resolved 5 more missing `video_id`s via WebSearch, fetched transcripts and chunks, then ran full extraction+attribution+tagging and validation in one pass for all 5 episodes -- antonio-gracias-doge-updates-voter-fraud-arrests-finding-big-balls-all-in-live-from-miami (0 predictions, operational/anecdotal DOGE commentary), ray-dalio-the-all-in-interview (0 predictions, macro/debt-cycle analysis without crisp falsifiable claims), scott-bessent-all-in-dc (2 predictions), howard-lutnick-all-in-dc (6 predictions), and the inauguration-interviews-trump-s-talent-democratic-rebrand-more-with-house-whip-emmer-reps-swalwell-khanna panel (2 predictions, from Rep. Tom Emmer; Swalwell and Khanna's segments were opinion/analysis without falsifiable, dated claims). 10 predictions checked (right/wrong/ambiguous/inconclusive with explanations); notably most of Lutnick's DC predictions came back wrong against actual outcomes (the $1T-cut/$1T-revenue budget-balancing pledge, the Trump Card's "two weeks" launch claim, and the 1-million-card sales estimate all fell well short of reality), while his post-quantum-cryptography and gold-card-financing-industry predictions came back right, and Emmer's reconciliation-bill timeline came back wrong (bill signed ~6 weeks later than his Memorial Day target) while his cabinet-confirmation prediction came back right. This is the second incremental-process batch against the previously-unprocessed backlog; 37 backlog episodes remain, with 3 more test batches planned.

## v0.34.0 (2026-08-27)

### Added
- Ran Batch 1 of the new incremental process (PRD §13) against the 47-episode unprocessed backlog, the first batch of the "5 batches as a test" run: resolved missing `video_id`s (3 of 5 episodes needed manual `config/youtube_urls_override.json` entries found by grepping the @allin YouTube channel's full upload list), fetched transcripts and chunks, then ran full extraction+attribution+tagging and validation in one pass for all 5 episodes -- ais-mp-materials-ceo-james-litinsky-on-rare-earths-supply-chain-and-energy-independence (1 prediction), ais-the-lanby-s-tandice-urban-on-solving-healthcare-s-customer-service-problem (0 predictions, purely descriptive guest talk), jonathan-haidt-the-all-in-interview (0 predictions, purely analytical/opinion content), john-mearsheimer-and-jeffrey-sachs-all-in-summit-2024 (3 predictions), and senator-ted-cruz-the-all-in-inauguration-series (10 predictions, mostly Trump second-term/cabinet-confirmation forecasts made the day before the 2025 inauguration). 14 predictions checked (right/wrong/ambiguous/inconclusive with explanations); notably 3 of Cruz's predictions (100 executive orders on day one, Greenland referendum appetite, Panama Canal/China outcome) came back wrong against actual outcomes, while border, tax-cut, energy-regulation, and cabinet-confirmation predictions came back right. This is the first incremental-process batch to touch the previously-unprocessed backlog; 42 backlog episodes remain, with 4 more test batches planned.

## v0.33.0 (2026-08-27)

### Changed
- Updated `docs/PRD.md` §13 Phase 4 to scope the original two-sweep (extract-everything-then-validate-everything) batching design explicitly to the now-complete initial full-archive load, and documented a new standing incremental process for the 47-episode unprocessed backlog and all future newly-published episodes: combined extraction+attribution+tagging+validation in a single pass per batch of 5 episodes, using the exact same close-out steps (manifest rebuild, site regen, docs update, commit/push) established during the validation-only batches. This is now the permanent, reusable process for ongoing archive maintenance, not a one-time plan.

## v0.32.0 (2026-08-27)

### Added
- Validated Batch Q (the final batch, closing out the entire validation-eligible pool), covering the last 8 episodes: trump-wins-how-it-happened-and-what-s-next, trump-verdict-covid-cover-up-crypto-corner-salesforce-drops-20-ai-correction, E132, E114, E051, ipos-and-spacs-are-back-mag-7-showdown-zuck-on-tilt-apple-s-fumble-genius-act-passes-senate, E103, and E045, 180 individual predictions checked (right/wrong/ambiguous/inconclusive with explanations). This brings the archive-wide validated count to 357/357 (100% of the validation-eligible pool; 350/402 in full-pipeline terms including the 47-episode unprocessed backlog). Resolved via general/historical knowledge spanning the November 2024 Trump-win aftermath episode, the May 2024 Fauci-hearing/Biden-debate-swap episode, the June 2023 SEC-crackdown/Coinbase episode, the February 2023 SVB-era pre-crisis market-outlook episode, the October 2021 inflation-onset episode, the June 2025 GENIUS-Act/Mag-7-dispersion episode, the November 2022 midterms/recession-outlook episode (several specific Senate-race predictions resolved definitively wrong against actual 2022 results), and the September 2021 Theranos-trial/SB8-abortion-law episode. This is the final batch of the "finish the batches" request; no further episodes remain in the validation-eligible pool.

## v0.31.0 (2026-08-27)

### Added
- Validated Batch P (fifth and final of five additional 5-episode batches requested), covering E106, E084, the gpt-4o-launches-glue-demo episode, E171, and E156, 93 individual predictions checked (right/wrong/ambiguous/inconclusive with explanations), bringing the archive-wide validated count to 349/357 (342/402 in full-pipeline terms including the 47-episode unprocessed backlog). Resolved via general/historical knowledge spanning the December 2022 Xi-ruler-for-life/SaaS-contraction episode, the June 2022 inflation/recession/2024-election-speculation episode, the May 2024 GPT-4o launch/Ohalo/Perplexity episode, the March 2024 DOJ-vs-Apple/NAR-settlement episode (several DOJ-Apple predictions marked inconclusive as the case remains unresolved), and the December 2023 campus-antisemitism-hearings/Gemini-launch episode. This completes the user's "5 more batches" request in full.

## v0.30.0 (2026-08-27)

### Added
- Validated Batch O (fourth of five additional 5-episode batches requested), covering E072, E059, E038, the presidential-debate-reaction/Biden-hot-swap episode, and E151, 87 individual predictions checked (right/wrong/ambiguous/inconclusive with explanations), bringing the archive-wide validated count to 344/357 (337/402 in full-pipeline terms including the 47-episode unprocessed backlog). Resolved via general/historical knowledge spanning the March 2022 early-invasion ceasefire-hopes episode, the December 2021 affirmative-action/Build-Back-Better episode, the August 2021 Robinhood-IPO/Delta-variant episode, the June 2024 Biden debate-reaction/hot-swap episode, and the October 2023 Israel-Hamas war episode.

## v0.29.0 (2026-08-27)

### Added
- Validated Batch N (third of five additional 5-episode batches requested), covering the trump-vs-powell/GENIUS Act episode, the markets-turn-trump/2024-election-home-stretch episode, the dueling-presidential-interviews/SpaceX-catch episode, E119 (the SVB collapse in real time), and E080 (May 2022 recession deep dive), 85 individual predictions checked (right/wrong/ambiguous/inconclusive with explanations), bringing the archive-wide validated count to 339/357 (332/402 in full-pipeline terms including the 47-episode unprocessed backlog). Resolved via general/historical knowledge spanning the July 2025 GENIUS Act signing and stablecoin-policy predictions, the October 2024 election home-stretch market predictions, the SpaceX Starship-catch/Starlink-subscriber and nuclear-power predictions, the March 2023 SVB collapse's real-time crisis predictions (many conditional on a government non-intervention that didn't occur, marked inconclusive), and the May 2022 recession-risk episode.

## v0.28.0 (2026-08-27)

### Added
- Validated Batch M (second of five additional 5-episode batches requested), covering E068, E057, E033, E024, and the inside-the-white-house-tech-dinner episode, 81 individual predictions checked (right/wrong/ambiguous/inconclusive with explanations), bringing the archive-wide validated count to 334/357 (327/402 in full-pipeline terms including the 47-episode unprocessed backlog). Resolved via general/historical knowledge spanning the February 2022 Canadian trucker convoy episode, the December 2021 Omicron episode, the May 2021 Antonio Garcia Martinez/crypto-pullback episode, the March 2021 COVID-reopening/Newsom-recall episode, and the September 2025 White House tech dinner/tariffs episode (several very-recent 2025-2026 tariff-revenue and investment-timeline predictions marked inconclusive as premature).

## v0.27.0 (2026-08-27)

### Added
- Validated Batch L (first of five additional 5-episode batches requested), covering E143, E121, E101, E095, E074, 80 individual predictions checked (right/wrong/ambiguous/inconclusive with explanations), bringing the archive-wide validated count to 329/357 (322/402 in full-pipeline terms including the 47-episode unprocessed backlog). Resolved via general/historical knowledge spanning the August 2023 GOP primary debate and Nvidia earnings episode, the March 2023 SVB/banking-crisis aftermath and TikTok divestiture saga, the November 2022 post-election market update with guest Brad Gerstner, the September 2022 European energy-crisis episode, and the April 2022 Q1-earnings/recession-risk episode; several long-horizon (2030s-2050s) demographic, tax-rate, and brand-disruption predictions marked inconclusive as premature.
- Added a new roadmap item (PRD §19) at user request: track an expected-resolution date on each prediction check, so unresolved (inconclusive) predictions can be automatically flagged for recheck once that date passes, with the date rolling forward to a new expectation if the outcome still isn't determinable at recheck time.

## v0.26.0 (2026-08-27)

### Added
- Validated the second of two 5-episode test batches (episode ordinal "Batch K"), completing the two-batch test of the reduced 5-episode batch size. Covered E052, E043, the ai-sovereignty-wars-palantir-nvidia-deal-scotus-birthright-ruling-newsom-s-ca-budget-lie episode, E155, and E153, 78 individual predictions checked (right/wrong/ambiguous/inconclusive with explanations), bringing the archive-wide validated count to 324/357 (317/402 in full-pipeline terms including the 47-episode unprocessed backlog). Resolved via general/historical knowledge spanning the 2021 Trump Media/DWAC SPAC saga and 2021 fintech/BNPL consolidation trends through the 2023-2024 OpenAI board crisis, the 2023 Israel-Hamas war's opening months, and 2025-2026 AI-infrastructure and California fiscal-policy predictions (several of the longer-horizon California and AI-labor-market claims marked inconclusive as premature).

## v0.25.0 (2026-08-27)

### Added
- Validated the first of two 5-episode test batches (episode ordinal "Batch J"), switching batch size down from 20 to 5 episodes at the user's request to test a lighter-weight validation cadence. Covered E145, E140, E128, E079, E067, 75 individual predictions checked (right/wrong/ambiguous/inconclusive with explanations), bringing the archive-wide validated count to 319/357 (312/402 in full-pipeline terms, including the 47-episode unprocessed backlog). Mostly resolved via general/historical knowledge for well-established pre-2024 events (LK-99 superconductor debunking, the Dobbs v. Jackson aftermath on Obergefell/affirmative action/state abortion policy, the 2022 trucker convoy, 2023 Treasury-yield and debt-ceiling-era predictions, Hunter Biden's gun/tax cases and 2024 pardon, the 2024 Republican primary and general election outcomes), with no additional web research required for this batch.

## v0.24.0 (2026-08-27)

### Added
- Audited competitor site allinscorecard.lovable.app at user request and documented 8 identified feature gaps in docs/PRD.md §36, added as a new roadmap row in §19: no accuracy/hit-rate percentage computed or shown anywhere on this site (the single largest gap), no home page headline stat, no host leaderboard, no sitewide search across predictions, no unified all-predictions browse page with host/verdict filters, no "recently settled" feed, no curated high-impact-calls section, and no per-host verdict-count breakdown block. Explicitly sequenced to start after the full ingest-and-validation sweep (the 47-episode unprocessed backlog plus remaining validation batches) completes, per the user's own framing of the request.

## v0.23.0 (2026-08-27)

### Added
- Validated a fifteenth batch of predictions (20 episodes, fewest-predictions-first recomputed fresh against the live manifest; the third and final of three additional 20-episode batches requested beyond the just-completed fourteenth-batch validation), bringing the archive-wide validated count to 314/357. 261 individual predictions were checked (right/wrong/ambiguous/inconclusive with cited sources), spanning episodes from 2021 through 2025, with fresh web research on the unanimous March 2024 Trump v. Anderson Supreme Court ruling restoring Trump's ballot eligibility, Google's April 2024 Project Nimbus employee firings, Nikki Haley's March 2024 Super Tuesday exit from the Republican primary, the Gonzalez v. Google Section 230 non-ruling, the August 2024 NAR real-estate commission settlement, the Magnificent Seven's ~34% S&P 500 weight at end of 2025, the US national debt crossing $38 trillion in October 2025, actual 2025 ICE deportation totals, GPT-5's mixed August 2025 reception, and the Waymo-led 2025-2026 robotaxi market. This completes the full three-additional-batch, 60-episode request made beyond the completed thirteenth-batch validation.

## v0.22.0 (2026-08-27)

### Added
- Validated a fourteenth batch of predictions (20 episodes, fewest-predictions-first recomputed fresh against the live manifest; the second of three additional 20-episode batches requested beyond the just-completed thirteenth-batch validation), bringing the archive-wide validated count to 294/357. 227 individual predictions were checked (right/wrong/ambiguous/inconclusive with cited sources), spanning episodes from 2022 through 2026, with fresh web research on the September 2025 Google antitrust remedies ruling, the January 2024 Taiwan election, the 2024 Kursk offensive and its collapse by March 2025, the November 2024 US presidential election margin, Tim Walz's full tenure on the 2024 Harris ticket, the December 2022 Georgia Senate runoff, Nvidia's continued AI accelerator dominance, xAI's Colossus GPU cluster scaling, OpenAI's 2025 revenue run rate, Elon Musk's America Party status heading into the 2026 midterms, Zohran Mamdani's early mayoral term, and Bitcoin's price action in late 2025.

## v0.21.0 (2026-08-27)

### Added
- Validated a thirteenth batch of predictions (20 episodes, fewest-predictions-first recomputed fresh against the live manifest; the first of three additional 20-episode batches requested beyond the just-completed 80-episode/four-batch sweep), bringing the archive-wide validated count to 274/357. 207 individual predictions were checked (right/wrong/ambiguous/inconclusive with cited sources), spanning episodes from 2021 through 2026, with fresh web research on Zohran Mamdani's November 2025 NYC mayoral win, GPT-5's rocky August 2025 launch, Waymo's Los Angeles expansion, the Google-Wiz acquisition's close and Wiz's ARR, the Scarlett Johansson/OpenAI voice dispute resolution, the September-December 2025 Fed rate cuts, the Trump-Musk feud and reconciliation, the Department of Education dismantlement order, the March 2025 JFK files release, asteroid 2024 YR4's downgraded impact probability, the Bob Lee murder conviction, Dean Phillips' 2024 primary collapse, and the April 2025 "Liberation Day" tariffs.

## v0.20.0 (2026-08-27)

### Added
- Validated a thirteenth batch of predictions (20 episodes, fewest-predictions-first recomputed fresh against the live manifest; the fourth and final of four additional 20-episode batches requested beyond the completed 100-episode sweep), bringing the archive-wide validated count to 253/357. 210 individual predictions were checked (right/wrong/ambiguous/inconclusive with cited sources), spanning episodes from 2021 through 2026, with fresh web research on Anthropic's 2026 valuation and revenue run rate, the Nvidia-Groq licensing deal, California's Billionaire Tax Act ballot qualification, CXMT's China DRAM IPO, the Trump administration's Intel equity stake, the September/December 2025 Fed rate cuts, ongoing AI copyright litigation, and TikTok's 2025-2026 forced-divestiture deal. This completes the full four-batch, 80-episode request made beyond the original 100-episode sweep.
- Added a roadmap item (docs/PRD.md §19) to extend the home page's filter UI (Resolved only checkbox, topic dropdown, Total/By Year/By Topic toggle) to every individual host and guest page, per user request.

## v0.19.0 (2026-08-27)

### Added
- Validated a twelfth batch of predictions (20 episodes, fewest-predictions-first recomputed fresh against the live manifest; the third of four additional 20-episode batches requested beyond the completed 100-episode sweep), bringing the archive-wide validated count to 233/357. 195 individual predictions were checked (right/wrong/ambiguous/inconclusive with cited sources), spanning episodes from 2022 through 2024, with fresh web research on 2023 global IPO volume, Instacart and Klaviyo revenue figures, the Texas Stock Exchange's SEC approval timeline, the 2024 Atlantic hurricane season's records, Tesla's Dojo supercomputer shutdown and revival, and the 2025 Musk-Trump public falling out.

## v0.18.0 (2026-08-27)

### Added
- Validated an eleventh batch of predictions (20 episodes, fewest-predictions-first recomputed fresh against the live manifest; the second of four additional 20-episode batches requested beyond the completed 100-episode sweep), bringing the archive-wide validated count to 212/357. 165 individual predictions were checked (right/wrong/ambiguous/inconclusive with cited sources), spanning episodes from 2021 through 2026, with fresh web research on the Adobe-Figma deal's collapse, Google's ad-tech antitrust case, the 2026 California governor's race, ChatGPT's declining market share, SpaceX's pre-IPO financials, and 2025-2026 Treasury yield moves. One episode (E081) had zero qualifying predictions (all speakers unknown/low-confidence) and was marked validated with an empty checks file.

## v0.17.0 (2026-08-27)

### Added
- Validated a tenth batch of predictions (20 episodes, fewest-predictions-first recomputed fresh against the live manifest; the first of four additional 20-episode batches requested beyond the completed 100-episode sweep), bringing the archive-wide validated count to 192/357. 157 individual predictions were checked (right/wrong/ambiguous/inconclusive with cited sources), spanning episodes from 2022 through 2026, including several near-term 2025-2026 tariff/tech/politics episodes requiring fresh web research (Supreme Court IEEPA tariff ruling, China 3nm chip status, Tesla AI5/Optimus/Starship progress, Fed 2025 rate cuts, California billionaire tax ballot qualification, Trump's Greenland pursuit).

## v0.16.0 (2026-08-27)

### Added
- Validated a ninth batch of predictions (20 episodes, fewest-predictions-first recomputed fresh against the live manifest; the fifth and final of five 20-episode batches toward the 100-episode sweep requested this weekend), bringing the archive-wide validated count to 172/357. 144 individual predictions were checked (right/wrong/ambiguous/inconclusive with cited sources), spanning episodes from 2021 through 2026. This completes the full 100-episode validation request (60 episodes validated in the prior session, 40 in this one).

## v0.15.1 (2026-08-27)

### Fixed
- The "All topics" dropdown on the home page charts was unreadable when opened: the site is dark-only but never declared `color-scheme: dark`, so the browser rendered the native `<select>` popup with its default light-theme white background while the CSS-set light foreground text (`--fg: #f5f5f5`) stayed applied, producing near-white-on-white text (user-reported via screenshot). Fixed by adding `color-scheme: dark` to `:root` in `site_src/static/style.css` plus an explicit `.chart-controls select option` background/color rule as a cross-browser fallback.

## v0.15.0 (2026-08-27)

### Added
- Validated an eighth batch of predictions (20 episodes, fewest-predictions-first per the standing sweep order, recomputed fresh against the live manifest rather than reusing a stale saved candidate list from a prior session; the fourth of five 20-episode batches toward a 100-episode sweep), bringing the archive-wide validated count to 152/357. 110 individual predictions were checked (right/wrong/ambiguous/inconclusive with cited sources).

## v0.14.0 (2026-08-27)

### Added
- Two new roadmap entries in `docs/PRD.md`, sourced from Reddit user feedback: §34, a planned host-vs-guest prediction accuracy league table (buildable now, no schema change needed since `role`/`who` already exist per prediction, pending answers on accuracy formula, minimum sample size, and guest page treatment); §35, a long-term-deferred listener voting/feedback mechanism, explicitly flagged as needing a backend/storage decision this static, accountless site doesn't have today. Both added to the §19 Roadmap table and §35 also to the explicitly-deferred-items list.

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
