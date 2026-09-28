# YouTube Transcript Rate Limits: Research Notes

Researched 2026-09-28. YouTube publishes no limits for caption requests, so everything here is either a third-party report or our own observation. Each item is labeled with where it came from. Estimates are predictions, not measurements, and should be replaced by numbers from `data/transcripts/_fetch_log.jsonl` as batches run.

## Summary

| | Estimate | Confidence |
|---|---|---|
| Burst allowance | about 20-30 caption requests close together | Medium: two independent reports plus our own run |
| Probably safe steady rate | about 1 request every 1-2 minutes, with random variation (30-60 an hour) | Low to medium |
| Daily ceiling | around 100-200 from one home connection | Low: inferred, no direct source |
| Block length once triggered | several hours, possibly 24-48 hours | Medium: community reports plus our 5+ hour block |
| Scope | per IP address, shared by every method including tactiq | High: observed directly |

## Sources

### Official

- **Google, YouTube Data API `captions.download`.** Costs 200 quota units and works only for videos on a channel the signed-in user owns; third-party videos return 403. There is no official way to get captions for someone else's videos, and no published limit for the unofficial caption endpoint that all our tools use.
  https://developers.google.com/youtube/v3/docs/captions/download
  https://dev.to/qcrao/what-i-learned-squeezing-the-youtube-data-api-v3-quota-for-a-side-project-3304

### Tool maintainers

- **yt-dlp wiki (Extractors page).** "The rate limit for guest sessions is ~300 videos/hour (~1000 webpage/player requests per hour). For accounts, it is ~2000 videos/hour (~4000 webpage/player requests per hour)." Recommends "a delay of around 5-10 seconds between downloads". These figures are for video pages and player requests, not caption requests specifically, which appear to be limited more tightly.
  https://github.com/yt-dlp/yt-dlp/wiki/Extractors
- **youtube-transcript-api (PyPI and maintainer comments, as summarized in an independent guide).** Limits are undocumented and reports vary; YouTube tightened limits on the caption endpoint in July 2025. Cloud and data-center IPs are usually blocked on the first request; home connections get a real, if small, allowance.
  https://pypi.org/project/youtube-transcript-api/
  https://github.com/hxckya/youtube-transcript-ip-blocked-guide
- **yt-dlp issue #13831 (maintainer's pinned comment).** A separate 429 wave affected only auto-translated captions; original-language auto captions were not affected. Does not apply to us (we request original English).
  https://github.com/yt-dlp/yt-dlp/issues/13831

### Developer reports

- **About 30 fetches from a home connection** before youtube-transcript-api raised IpBlocked.
  https://dev.to/xixisuperman/getting-youtube-transcripts-without-the-data-api-and-why-translate-to-100-languages-is-usually-43m8
- **10-20 videos through a VPN** before each block (April 2026 report, cited in the guide above).
  https://github.com/hxckya/youtube-transcript-ip-blocked-guide
- **Spacing matters, but is not enough on its own.** Youtarr got 429s with 2 seconds between caption requests; 5 seconds fixed it. Other users still got 429s at 1, 10 and 60 seconds, which suggests a cap on total count as well as on rate.
  https://github.com/DialmasterOrg/Youtarr/issues/821
  https://github.com/yt-dlp/yt-dlp/issues/7123
  https://github.com/yt-dlp/yt-dlp/issues/11059
- **Block length.** Community reports put hard IP blocks at 24-48 hours; YouTube publishes nothing.
  https://skipthewatch.com/blog/youtube-transcript-api-not-working
- **Retrying may extend a block.** One unofficial help site says every retry during a 429 restarts the timer. Not confirmed anywhere else; our attempt log can test it.
  https://yt-dlp.net/errors/http-error-429-too-many-requests
- **Pacing advice.** `--sleep-requests 2`, and random 5-15 second pauses, since an exact interval can itself look automated.
  https://decodo.com/blog/youtube-error-429
- **Security token (PO token) on caption requests, since 2025.** For some videos the caption URL carries `exp=xpe`, and without a token minted by YouTube's own player the request returns an empty HTTP 200, not an error. So an empty reply does not reliably mean "no captions".
  https://github.com/jdepoix/youtube-transcript-api/issues/592
  https://dev.to/jamhimself/why-your-youtube-transcript-scraper-started-returning-empty-strings-and-how-to-fix-it-in-2026-20ed

Reddit (r/youtubedl and similar) could not be reached: the research tool is blocked from reddit.com, and web searches did not surface the relevant threads.

## Our own observations

- **2026-09-27:** 38 transcripts fetched in one session (20 via tactiq, 18 via youtube-transcript-api) before every method began failing, consistent with the ~30 burst figure.
- **Block length:** first seen around 17:00, still returning 429 at 22:19, so more than 5 hours.
- **Network capture of tactiq (2026-09-27):** described below.

## Does this apply to tactiq?

Yes, to the IP limit. None of the sources above mention tactiq; this comes from recording tactiq's network traffic ourselves.

- **Same limit, same IP.** tactiq does not fetch captions on its servers. Its page embeds a YouTube player in our browser, and that player requests `youtube.com/api/timedtext` from our IP. During the block YouTube answered those requests with 429, exactly as it did for youtube-transcript-api and yt-dlp. All three methods draw from one budget.
- **More YouTube requests per video.** Each tactiq load also makes several other YouTube requests (player, next, video stream, logging), roughly 6-8 per video against 1-2 for the direct tools. If YouTube counts page and player requests too (yt-dlp's wiki suggests it does), tactiq may use up the budget faster per video.
- **The security-token problem mostly does not apply.** tactiq runs YouTube's real player, which mints the token, so an empty reply through tactiq is more likely to be a genuine "no captions" than one from the direct tools.
- **tactiq's own protections are a separate, unknown limit.** Every tactiq load runs a Cloudflare challenge and reCAPTCHA, and its Firebase App Check request returned 403 "App attestation failed" on every load, even on loads that succeeded. tactiq publishes no usage limit for its free tool. If it ever starts refusing us, that would show as a failure with no caption request at all (classified `unknown`).

## Services that fetch on their own servers

Tested 2026-09-28 by requesting videos that YouTube was refusing from our IP at the time. A service that still returns them is fetching from its own servers, so it does not use our IP's YouTube budget. These services still read YouTube's captions; they just do it from their own addresses.

| Service | Free allowance | Key needed | Our test | Notes |
|---|---|---|---|---|
| **FreeTranscriptAPI** (`api.freetranscriptapi.com/v1/transcript?video_url=ID`) | 20 requests per hour per IP, no signup (was 50 until 2026-09-19); 1,000 credits with a free account | No | **Worked**: full 313-line transcript for `bBhhjiTCIK0` while YouTube returned 429 to us | Cue-level timestamps in the same shape we store (`text`, `start`, `duration`). Terms allow scripted use; prohibit reselling free access and abusing limits; users must comply with YouTube's terms. |
| **youtube-transcript.ai** (`youtube-transcript.ai/transcript/ID.txt`) | "Fair use", no number published | No | **Worked** for `HSleP7ug6Hk` while blocked for us | Only paragraph-level `[m:ss]` timestamps, and auto-captions came back with each phrase repeated three times. Usable as a last resort. Free tier is for personal projects and scripts, not bulk ingest. |
| Supadata | 100 per month | Yes (account) | Not tested | Paid from $5/month. |
| TranscriptAPI.com | 100 free credits to start (other sources say 50 a month) | Yes (account) | Not tested | Paid from $5/month for 1,000. |
| youtube-transcript.io | 25 per month; 5 requests per 10 seconds | Yes (account) | Not tested | Paid. |

Browser-based tools (tactiq, NoteGPT, youtubetotranscript.com) run YouTube's player in the visitor's browser or were not verified; tactiq is confirmed to use our IP.

Sources:
https://freetranscriptapi.com/ and https://freetranscriptapi.com/terms
https://youtube-transcript.ai/youtube-transcript-api
https://supadata.ai/pricing and https://supadata.ai/blog/best-youtube-transcript-api
https://transcriptapi.com/
https://www.youtube-transcript.io/api

## How this shapes our settings

- Adopted 2026-09-28: FreeTranscriptAPI is the primary method, so most fetches don't use our IP's YouTube budget at all.

- Adopted 2026-09-28: 60-120 seconds between attempts with random variation, at most 20 attempts per rolling hour and 100 per rolling 24 hours.
- The 10-30 minute cool-off (author decision) is a cheap check: each check is one request and stops the run at once. Expect checks to keep failing for hours after a real block. The attempt log will show whether frequent checks lengthen blocks.
- Do not skip a video as "no captions" from an empty direct-tool reply alone.
