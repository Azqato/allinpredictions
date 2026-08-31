# Patch Notes

All notable changes to this project, in reverse chronological order. Format: semantic version, date (YYYY-MM-DD), then Added/Changed/Fixed/Removed sections with one line per change, past tense.

## v0.56.0 (2026-08-31)

### Changed
- Moved the "Big Ones" home page section (below "Guest Predictions" instead of above "Host Accuracy"), per user request, so visitors see the per-host scorecards and guest predictions first before the curated highlight reel.
- Added a "Home" link as the first item in the site nav (`base.html`), per user request — previously the only way back to the home page was the logo/brand link.

## v0.55.0 (2026-08-31)

### Added
- **"The Big Ones" home page section**: a hand-curated highlight reel of 12 of the show's boldest, highest-stakes predictions (5 confirmed hits, 5 confident misses, 2 huge still-inconclusive calls to watch), listed by `episode_id`/`id` in the new `config/big_ones.json` and resolved against the live prediction/check data at build time, so it always reflects the current verdict. Includes Chamath's crypto-market-cap call ($2-3T &rarr; $6T, right), Sacks predicting Sam Altman would consolidate control of OpenAI within months of the November 2023 board crisis (right), Jason's "President Kamala for four months" 2024 call (wrong), Howard Lutnick's $1 trillion DOGE-waste-cut pledge (wrong), Brad Gerstner's $2 trillion SpaceX IPO valuation call (wrong, SpaceX still private), and both of today's new inconclusive predictions.
- **Sitewide search** (`search.html`, nav link "Search"): a single search box across every prediction, episode, and host/guest page (4,001 indexed items total), filterable by type. Built from a new `static/search_index.json` generated alongside the existing `ledger.json`; results only render once the visitor starts typing rather than dumping the full index unfiltered.

## v0.54.0 (2026-08-31)

### Added
- `resolves_by` field on check entries (`data/checks/{episode_id}.json`): an ISO date marking when a prediction's forecast window is expected to become evaluable. Applied going forward to all newly-written checks (including today's two: Chamath's Social Security 2030-2032 forecast and Ray Dalio's 2026-midterms forecast), plus a 5-check test batch backfilled retroactively (see below). The ~685 remaining pre-existing `inconclusive` checks do not have this field yet; full retroactive backfill is planned in batches of 5 (roadmap, not started).
- `scripts/list_due_rechecks.py`: scans all checks files and lists every `inconclusive` check whose `resolves_by` date has passed (or would pass as of a given `--as-of` date), so a future recheck pass has a ready-made worklist instead of manually hunting for overdue predictions.
- Backfilled `resolves_by` on a 5-check test batch to prove out the retroactive-backfill workflow: `chamath-00:59:45` (2065, from a 40-50yr NYC-decline forecast), `chamath-01:01:35` (2028, vague "coming years" NYC real estate crash), `friedberg-01:11:59` (2035, age-reversal therapy), `andrew-ross-sorkin-00:39:59` (2040, "end of empire" inflection point), `andrew-ross-sorkin-00:44:34` (2035, 10-year tariff/auto-tech window).

### Changed
- `scripts/build_manifest.py`: added a `legacy_no_transcript` status count and a `notes` field explaining that `captions_fetched`/`chunked` reading `false` alongside `predictions_extracted: true` reflects real historical episodes whose raw transcript/chunk files were never retained (not a bug and not "unprocessed") — 229 episodes fall into this category. `predictions_extracted`/`validated` (or actual `data/predictions/`, `data/checks/` file presence) remain the correct ground truth for pipeline completeness, now documented directly in the manifest instead of only in project memory.

## v0.53.0 (2026-08-31)

### Fixed
- Recovered the one permanently-"unresolvable" backlog episode, Ray Dalio's "Our System Is in Jeopardy - Debt, AI & the Cycle That Destroyed Rome" (RSS-published 2026-03-03), which had no resolvable `video_id` because the yt-dlp channel search couldn't find it under that title. Found it manually on the official All-In YouTube channel under a different public title, "Ray Dalio: 'AI Is Eating Everything - and It Might Eat Itself'" (`u-vMNzHgSHI`) — same chapter markers and description confirm it's the same upload, just retitled on YouTube. Added a `config/youtube_urls_override.json` entry, fetched its transcript/chunks, and extracted 1 falsifiable dated prediction (Ray Dalio forecasting Democrats will take the House in the 2026 midterms), validated `inconclusive` since the midterms haven't happened yet (though current polling favors that outcome). Episode count now 413 tracked / 413 with extracted predictions — zero gaps remain.

## v0.52.0 (2026-08-31)

### Added
- Processed 1 newly-published episode found via the incremental RSS/YouTube sweep (Batch 12): "Nvidia's Historic Quarter, SaaS Comeback, Bessent vs Druck, America's Debt Crisis, Cancer Vaccine" (published 2026-08-29). Fetched transcript and chunks, extracted 1 falsifiable dated host prediction (Chamath's Social Security insolvency / state bankruptcy and restructuring forecast for "around 2030 to 2032"), and validated it via WebSearch-informed review — marked `inconclusive` since the 2030-2032 window is still years out. Episode count now 413 tracked / 412 with extracted predictions.

## v0.51.0 (2026-08-27)

### Changed
- Rolled up every tag with fewer than 20 total predictions into a broader surviving category, per user request ("categories with less than 20 overall predictions should be rolled up into another one if possible"). Straight renames (no splitting), so no data was lost, just consolidated: `autonomous-vehicles`/`open-source`/`robotics` -> `tech`; `business`/`energy`/`macro`/`manufacturing` -> `economy`; `policy` -> `government`; `commodities`/`finance`/`ipo`/`revenue`/`valuation` -> `markets`; `elections`/`midterms` -> `politics`; `china`/`defense`/`space` -> `geopolitics`. This takes the taxonomy from 30 tags (19 of them under 20 predictions) down to **12 broad tags, every one with at least 20 predictions** (`economy` 1211, `politics` 1171, `tech` 843, `government` 823, `markets` 813, `ai` 635, `venture` 280, `health` 272, `conflict` 184, `science` 171, `climate` 123, `geopolitics` 20). Retagged 47 predictions across 8 episode files. Home page and Full Ledger topic dropdowns are now identical (both host-only and sitewide tag sets converged onto the same 12 categories).

## v0.48.0 (2026-08-27)

### Added
- Added percentages to every prediction-accuracy breakdown sitewide (home page headline stat, per-host scorecards, host/guest pages, leaderboard) via a new `pct_bucket()` helper, mirrored client-side in `app.js` so filtered/re-rendered legends stay consistent (e.g. "3 (37.5%)" instead of a bare count); zero-count cells omit a redundant "(0.0%)".

## v0.49.0 (2026-08-27)

### Changed
- Changed the leaderboard's default sort from accuracy % to sheer number of right predictions (`stats.right` descending, accuracy % as tiebreak), per user request. Every column remains click-to-sort; accuracy is still available, just no longer the default.

## v0.50.0 (2026-08-27)

### Fixed
- Fixed the topic filter dropdowns (home page, Full Ledger): the home page's topic list was silently scoped to only host predictions, so ~40 guest-only tags (spacex, openai, robotics, etc.) never appeared as filter options on the Ledger even though the Ledger displays those predictions. Now the Ledger gets its own `all_topics` list computed across every speaker (host + guest), while the home page correctly keeps its host-scoped list (it only filters host scorecards, so a guest-only option would just zero out every card).
- Fixed topic label casing: the `|capitalize` Jinja filter was mangling multi-word/acronym tags ("ai" -> "Ai", "spacex" -> "Spacex", "ai-policy" -> "Ai-policy"). New `tag_display()` filter (Python) + `tagDisplay()` (JS, kept in sync) special-cases acronyms/brands and title-cases hyphenated compound tags word-by-word ("open-source" -> "Open Source").
- Fixed dead code in `app.js`'s "By Topic" chart view: the stacked-bar group labels were never actually capitalized because the code checked `groupKey === "topic"`, but `groupKey` is only ever `"year"` or `"tags"` — the correct flag is `state.view === "topic"`. Now uses the new `tagDisplay()` for consistent casing.

### Changed
- Consolidated the tag taxonomy from 72 distinct tags down to 30 general themes, per user request ("each tag should be a general theme, not that specific - individual company names shouldn't be a tag"). Retagged 49 predictions across 16 episode files: merged company/product names into their domain (anthropic/openai/xai/grok/meta -> ai; spacex/starlink -> space; waymo -> autonomous-vehicles; google/technology/big-tech/hardware -> tech; saronic/1x/agility-robotics/nasa -> dropped, redundant with a co-occurring general tag), dropped person names (zuckerberg, elon-musk, aoc - redundant with co-occurring topic tags), merged single-material tags into the "commodities" umbrella (copper, silver, critical-minerals), merged narrow subtopics into their nearest general theme (regulation -> policy, foreign-policy/world -> geopolitics, quantum-computing -> science, fusion -> energy, cybersecurity/hard-takeoff/humanoid -> ai/robotics, jobs/supply-chain/growth -> economy, house/senate -> dropped, redundant with co-occurring "midterms"), and collapsed year-specific election tags (2026-election, 2028-election, bare "2028") into a single "elections" tag (the Ledger's separate Year filter already covers the year dimension). Verified every merge against the actual prediction text before mapping; no prediction was left with an empty tag list.

## v0.47.0 (2026-08-27)

### Added
- Shipped item 2 of the approved post-backlog development plan (PRD §19): the batched leaderboard/ledger/filter items, all reading off the speaker-index data `generate_site.py` already computed. New sitewide headline stat on the home page (accuracy %, right/wrong/resolved/total counts, computed by summing every speaker's qualifying-prediction bucket). New "Recently Settled" section on the home page: the 8 most-recently-resolved qualifying predictions (right/wrong/ambiguous), newest episode first, linking to the source episode's deep-linked prediction card.
- New `leaderboard.html` page: a single ranked table combining the accuracy leaderboard, host-vs-guest comparison (§34), and full per-speaker verdict-count breakdown (right/wrong/ambiguous/inconclusive/unvalidated, not just right/wrong) for all 132 hosts and guests, sorted by accuracy % (unranked speakers sort last), with a small-sample flag for guests under 3 tracked predictions.
- New `ledger.html` page: a client-side searchable/filterable browse of every one of the 3453 qualifying predictions sitewide (search text, year, topic, result), backed by a new `static/ledger.json` data file (deliberately thin per-record - no quote/explanation - to keep payload size down) fetched and rendered client-side with a "load more" pager (50 at a time).
- Added a year filter dropdown to the Episodes index page (§17), client-side, reusing the existing show/hide filter pattern from the home page's topic filter.
- Added "Leaderboard" and "Ledger" links to the site nav (now `Episodes | Leaderboard | Ledger | Hosts | About`).

## v0.46.0 (2026-08-27)

### Fixed
- Ran the host/guest name-accuracy audit (PRD §19, item 1 of the approved post-backlog development plan): audited all 144 distinct `who` values across `data/predictions/*.json` and fixed 182 individual prediction records across ~65 episode files. Normalized 6 underscore-formatted slugs to hyphens (`ben_shapiro`, `brad_gerstner`, `jared_kushner`, `nassim_taleb`, `reid_hoffman`, `rfk_jr`). Merged 15 duplicate-identity slugs that were fragmenting one person's scorecard across multiple pages into their canonical full-name slug (`brad`/`brad_gerstner`->`brad-gerstner`; `elon`/`musk`->`elon-musk`; `gavin`->`gavin-baker`; `cuban`->`mark-cuban`; `trump`->`donald-trump`; `kennedy`/`rfk_jr`->`robert-f-kennedy-jr`; and 9 more). Researched and renamed 26 bare-first-name-only slugs to full First-Last slugs via episode-title/WebSearch verification (`balaji`->`balaji-srinivasan`, `sergey`->`sergey-brin`, `tucker`->`tucker-carlson`, `vivek`->`vivek-ramaswamy`, `oz`->`mehmet-oz`, and 21 more).
- Fixed two real data-quality bugs of the same class as the 2026-08-25 freeberg-typo incident: E088 had a Friedberg quote mislabeled `who: "david"`/`role: "guest"` instead of `friedberg`/`host`; the trump-vs-powell episode had the identical statement extracted twice under two different speaker labels 11 seconds apart (`other-00:58:05` and `bo-00:58:16`) - removed the duplicate, kept the survivor renamed to `bo-hines`, and renamed two more `other`-labeled predictions in that episode to the correctly-identified guest `bill-hagerty`. Site rebuilt clean: 132 host/guest pages (down from 145 stale/duplicate pages), zero validator errors. 3 predictions in E129 and 3 in E114/epstein-files-flop remain unresolved (`who: "david"`/`"other"`) - confirmed host-only episodes but the original transcripts were never retained for these older-batch episodes, so which specific host is speaking can't be confirmed without a transcript re-fetch; intentionally left rather than guessed.

## v0.45.0 (2026-08-27)

### Added
- Ran Batch 11, the final batch of the incremental process (PRD §13) against the unprocessed backlog: resolved 4 more missing `video_id`s via yt-dlp channel-filtered search, fetched transcripts and chunks, then ran full extraction+attribution+tagging and validation in one pass for all 4 episodes -- flock-ceo-garrett-langley-on-controversy-surveillance-state-claims-and-privacy-vs-safety (0 predictions, controversy/privacy-policy interview without falsifiable dated claims), michael-kratsios-trump-s-science-agenda-anti-science-claims-fauci-s-damage-dei-china (5 predictions, all specific government science-policy targets -- moon landing and space nuclear reactor by 2028, moon-base elements by 2030, scientifically relevant quantum computer by 2028, fusion by 2035, and a 2028-election prediction), eric-weinstein-the-state-of-american-science-breakthrough-coverups-and-the-danger-of-physics (0 predictions, philosophical/conspiracy-theory science discussion without falsifiable dated claims), and dario-defends-himself-datacenter-panic-ai-doomer-trap-senate-toss-up (3 predictions: Jason's Waymo-ban-in-NY/Boston/DC prediction, Sacks's 2026-midterms House-to-Dems/Senate-holds-GOP split prediction, and Friedberg's AOC-wins-2028-presidency prediction). All 8 predictions checked (right/wrong/ambiguous/inconclusive with explanations); all 8 came back inconclusive (government policy targets dated 2028-2035 and 2026/2028 election forecasts, none of which have elapsed yet). This is the eleventh and final incremental-process batch against the original 47-episode unprocessed backlog; combined with Batches 9 and 10, all 14 non-Ray-Dalio backlog episodes are now fully processed. 411 of 412 tracked episodes now have predictions extracted (Ray Dalio's "Our System Is in Jeopardy" episode remains permanently unresolvable on the official All-In YouTube channel and is excluded).

## v0.44.0 (2026-08-27)

### Added
- Ran Batch 10 of the incremental process (PRD §13) against the unprocessed backlog: resolved 5 more missing `video_id`s via yt-dlp channel-filtered search, fetched transcripts and chunks, then ran full extraction+attribution+tagging and validation in one pass for all 5 episodes -- saronic-founders-autonomous-warships-china-s-230x-advantage-swarms-of-robot-ships (4 predictions), the-1-hour-worker-four-robotics-ceos-on-humanoids-at-home-china-s-threat-and-the-end-of-dangerous-jobs (3 predictions), google-s-ai-brain-drain-spacex-s-huge-quarter-airtable-s-90-collapse-us-data-fuels-china-ai (3 predictions, from Brad Gerstner and Sacks), rahm-emanuel-trump-s-foreign-policy-china-europe-s-decline-immigration-dsa-vs-democrats (0 predictions, political-opinion interview without falsifiable dated claims), and anthropic-s-2t-ipo-zuck-s-ai-manifesto-nvidia-s-500b-ai-bet-grok-s-comeback (4 predictions, from Gavin Baker and Jason). 14 predictions checked (right/wrong/ambiguous/inconclusive with explanations); Gavin Baker's "Grok 4.7 launching in a few weeks" prediction came back wrong (as of August 23, 2026, xAI had delayed the release to September per multiple reports), while the remaining 13 predictions (SpaceX/Starlink valuation targets, Anthropic IPO valuation and ARR targets, robotics-shipping and China-fleet-size forecasts) were all marked inconclusive (timeframes not yet elapsed). This is the tenth incremental-process batch against the previously-unprocessed backlog.

## v0.43.0 (2026-08-27)

### Added
- Ran Batch 9 of the incremental process (PRD §13) against the unprocessed backlog: resolved 5 more missing `video_id`s via yt-dlp channel-filtered search, fetched transcripts and chunks, then ran full extraction+attribution+tagging and validation in one pass for all 5 episodes -- inside-the-private-stock-market-boom-spacex-anthropic-openai-the-rise-of-secondaries (0 predictions, market-structure discussion without falsifiable dated claims), nikesh-arora-mythos-is-real-analytical-saas-is-dead-and-google-can-be-a-10t-company (3 predictions), dan-dreyfus-america-s-critical-minerals-crisis-is-here (3 predictions), nate-silver-predicts-democrats-take-the-house-newsom-is-fading-aoc-might-win-it-all-in-2028 (4 predictions), and more-trillion-dollar-ipos-anthropic-3t-zuck-s-price-war-china-ends-open-source-trump-accounts (7 predictions). All 17 predictions checked (right/wrong/ambiguous/inconclusive with explanations); all 17 came back inconclusive (election forecasts, multi-year IPO/valuation targets, and 2026-2028 policy predictions, none of which have elapsed yet). This is the ninth incremental-process batch against the previously-unprocessed backlog.

## v0.42.0 (2026-08-27)

### Added
- Ran Batch 8 of the incremental process (PRD §13) against the unprocessed backlog: resolved 5 more missing `video_id`s (all via yt-dlp channel-filtered search, since YouTube's public titles for these episodes differ from the RSS feed titles, with upload dates verified against each episode's RSS `published_iso`), fetched transcripts and chunks, then ran full extraction+attribution+tagging and validation in one pass for all 5 episodes -- anthropic-s-generational-run-openai-panics-ai-moats-meta-loses-lawsuits (2 predictions), the-companies-changing-warfare-forever-palantir-anduril-execs-on-drones-ai-the-future-of-war (0 predictions, strategic/philosophical defense-industry discussion without clean falsifiable dated claims), charles-chase-koch-on-how-they-quietly-built-a-150b-empire (0 predictions, business-history/principles interview without falsifiable dated claims), bill-ackman-investment-strategy-what-the-market-is-missing-how-ai-breaks-businesses (1 prediction), and thomas-laffont-the-4t-ai-ipo-wave-2026-s-unicorn-economy-and-the-10x-paradox (2 predictions). All 5 predictions checked (right/wrong/ambiguous/inconclusive with explanations): both of Jason's ChatGPT predictions came back right (ChatGPT crossed 1 billion users within the predicted 1-2 month window, and its consumer market share fell well under 50%, reaching 46.4% by May 2026 as Gemini and Claude gained share); Thomas Laffont's AI-industry-revenue-doubling-to-2027 and OpenAI/Anthropic-surpassing-AWS/Microsoft predictions, and Bill Ackman's 22-year Pershing Square AUM-growth forecast, were all marked inconclusive (timeframes not yet elapsed or too methodologically ambiguous to confirm cleanly). This is the eighth incremental-process batch; 397 of 412 tracked episodes now have predictions extracted, 15 remain unprocessed (Ray Dalio's episode remains permanently unresolvable on the official channel and continues to be skipped).

## v0.41.0 (2026-08-27)

### Added
- Ran Batch 7 of the incremental process (PRD §13) against the unprocessed backlog: resolved 5 more missing `video_id`s (2 found directly via WebSearch, 3 via yt-dlp channel-filtered search matching upload date against the RSS-feed publish date, since YouTube's public titles for these episodes differ from the RSS feed titles), fetched transcripts and chunks, then ran full extraction+attribution+tagging and validation in one pass for all 5 episodes -- graham-allison-on-the-global-realignment-iran-china-israel-greenland (2 predictions), rewriting-the-rules-the-sec-cftc-on-crypto-ipos-the-future-of-american-markets (0 predictions, regulatory policy discussion without falsifiable dated claims), travis-kalanick-michael-dell-live-from-austin-texas (2 predictions, from Michael Dell and Brad Gerstner), john-fetterman-the-rogue-democrat-who-broke-party-ranks (0 predictions, political-opinion interview consistently hedged with "I don't know"), and jensen-huang-live-nvidia-s-future-physical-ai-rise-of-the-agent-inference-explosion-ai-pr-crisis (3 predictions). 4 of the 7 predictions checked so far (right/wrong/ambiguous/inconclusive with explanations); Michael Dell's ~100%-quarterly-infrastructure-growth guidance came back right (Dell's ISG revenue grew 181% the following quarter); Graham Allison's Iran-war-declared-over-before-the-March-29-China-trip prediction came back wrong (the China trip itself was delayed to May over the unresolved war, which still hadn't ended by then); Brad Gerstner's 10-million-Trump-accounts-by-July-4 prediction came back wrong (roughly 6 million had signed up by the July 4, 2026 launch); Allison's ~5%-Taiwan-invasion-probability-for-2026-2027 and all 3 of Jensen Huang's multi-year forecasts (digital biology, robotics, Anthropic revenue) were marked inconclusive (timeframes not yet elapsed). This is the seventh incremental-process batch; 392 of 412 tracked episodes now have predictions extracted, 20 remain unprocessed.

## v0.40.0 (2026-08-27)

### Fixed
- Fixed a naming-convention bug introduced in Batch 6: two predictions used display-name-style `who` slugs (`chamath-palihapitiya`, `david-friedberg`) instead of the canonical `config/hosts.yaml` slugs (`chamath`, `friedberg`), which silently fabricated two duplicate host pages (splitting Chamath's and Friedberg's stats across two cards each) instead of erroring. Also fixed a `role: "guest"` on a Friedberg (permanent host) prediction that should have been `"host"`.
- Hardened `scripts/generate_site.py`'s data validator: `role: "host"` predictions now require an exact match to a `config/hosts.yaml` slug and hard-fail the site build otherwise, closing the gap where the prior near-miss/typo check (Levenshtein distance <=2) missed longer display-name-style variants entirely. Verified against the exact bug pattern before and after the fix.

## v0.39.0 (2026-08-27)

### Added
- Ran Batch 6 of the incremental process (PRD §13) against the 47-episode unprocessed backlog, the first batch beyond the completed "5 batches as a test" run: resolved 5 more missing `video_id`s via yt-dlp channel search (Ray Dalio's "Our System Is in Jeopardy" episode could not be located on the official All-In YouTube channel at all and was substituted with the next-oldest backlog episode), fetched transcripts and chunks, then ran full extraction+attribution+tagging and validation in one pass for all 5 episodes -- bernie-sanders-stop-all-ai-china-s-euv-breakthrough-inflation-down-golden-age-in-2026 (2 predictions), microsoft-ceo-satya-nadella-on-ai-s-business-revolution-what-happens-to-saas-openai-and-microsoft-live-from-davos (0 predictions, vision/philosophy discussion without falsifiable dated claims), under-secretary-of-state-sarah-b-rogers-on-dismantling-the-censorship-industrial-complex (0 predictions, policy/opinion discussion), cz-s-untold-story-the-rise-fall-and-redemption-of-binance-s-founder (0 predictions, biographical narrative interview), and inside-the-iran-war-and-the-pentagon-s-feud-with-anthropic-with-under-secretary-of-war-emil-michael (4 predictions). 6 predictions checked (right/wrong/ambiguous/inconclusive with explanations): Chamath's prediction that Google would ship a competing "co-work"-style agentic product within 90 days came back right (Google shipped Chrome/Workspace agent features within about a month); David Friedberg's prediction of a US-China "grand bargain" at the spring 2026 Trump-Xi summit came back wrong (the summit produced only modest trade outcomes, explicitly no grand agreement); Emil Michael's 12-month OpenAI-Codex-closes-the-gap prediction, Chamath's $1.5 trillion Anthropic valuation prediction, Freeberg's Huawei/EUV 2026-2027 prediction, and Chamath's California billionaire-tax economic-impact prediction were all marked inconclusive (timeframes not yet elapsed, though several are trending toward their predicted outcomes). This is the sixth incremental-process batch and the first beyond the "5 batches as a test" request; 39 backlog episodes processed overall, 21 backlog episodes remain.

## v0.38.0 (2026-08-27)

### Added
- Ran Batch 5 of the incremental process (PRD §13) against the 47-episode unprocessed backlog (fifth and final of the "5 batches as a test" run): resolved 5 more missing `video_id`s via yt-dlp channel search, fetched transcripts and chunks, then ran full extraction+attribution+tagging and validation in one pass for all 5 episodes -- nobel-prize-in-physics-winner-john-martinis-on-the-state-of-quantum (1 prediction), nobel-peace-prize-winner-mar-a-corina-machado-on-defeating-maduro-socialism-freeing-venezuela (1 prediction), triple-h-on-wwe-s-evolution-the-rise-of-the-antihero-and-the-psychology-of-stardom (0 predictions, sports-entertainment/psychology narrative without falsifiable dated claims), ari-emanuel-on-the-future-of-entertainment-hollywood-ai-creator-economy-youtube-vs-netflix (0 predictions, industry commentary without clean falsifiable claims), and molly-s-game-uncensored-the-truth-behind-the-world-s-most-infamous-poker-game (0 predictions, personal-story narrative without falsifiable dated claims). 2 predictions checked (right/wrong/ambiguous/inconclusive with explanations): Maria Corina Machado's prediction that Maduro would leave power soon came back right (Maduro was captured and arrested by the U.S. on January 3, 2026 on narco-terrorism charges, roughly 2.5 months after this October 2025 interview, with Delcy Rodriguez taking over as acting president), while John Martinis's 8-10-year quantum-computing-scaling prediction was marked inconclusive (timeframe far from elapsed). This is the fifth and final batch of the "5 batches as a test" request, completing it in full: 25 episodes processed across the 5 batches, with 22 episodes remaining in the 47-episode unprocessed backlog (402-episode full-pipeline total).

## v0.37.0 (2026-08-27)

### Added
- Ran Batch 4 of the incremental process (PRD §13) against the 47-episode unprocessed backlog (fourth of the "5 batches as a test" run): resolved 5 more missing `video_id`s via yt-dlp channel search (WebSearch alone could not locate these 5 on the All-In YouTube channel directly, so falsifiable-title searches were run against the channel's own uploads via yt-dlp), fetched transcripts and chunks, then ran full extraction+attribution+tagging and validation in one pass for all 5 episodes -- google-deepmind-ceo-demis-hassabis-on-ai-creativity-and-a-golden-age-of-science-all-in-summit (2 predictions), ro-khanna-on-crime-censorship-congress-fixing-what-s-broken-in-america (0 predictions, policy/opinion discussion without falsifiable dated claims), joe-tsai-on-us-china-rivalry-ai-s-future-owning-the-nets-liberty-caitlin-clark-s-major-impact (1 prediction), bryan-johnson-the-1-longevity-secret-you-can-start-doing-today (0 predictions, health advice/philosophy without falsifiable dated claims), and how-orlando-bravo-built-one-of-the-most-successful-firms-in-private-equity (0 predictions, business-history narrative without falsifiable dated claims). 3 predictions checked (right/wrong/ambiguous/inconclusive with explanations): Demis Hassabis's AGI-in-5-to-10-years prediction and Joe Tsai's competing AGI-in-20-years prediction were both marked inconclusive (timeframes far from elapsed), while Hassabis's Isomorphic Labs "pre-clinical phase sometime next year" prediction came back right (Isomorphic's Eli Lilly/Novartis collaborations generated multiple AI-designed preclinical candidates by early 2026, now targeting a first-in-human trial by end of 2026). This is the fourth incremental-process batch against the previously-unprocessed backlog; 27 backlog episodes remain, with 1 more test batch planned.

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
