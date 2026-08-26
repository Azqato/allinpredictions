# Prediction extraction + speaker attribution + tagging

You are analyzing a chunk of an All-In Podcast transcript (YouTube captions,
no speaker labels -- see PRD.md section 6.4) to extract concrete predictions.

## Input
A chunk of transcript text, each line prefixed with a `[hh:mm:ss]` timestamp.
Lines are merged caption cues, not perfectly sentence-bounded. You may also be
given the episode title/description for context (helps identify guests).

## What counts as a prediction
Only extract explicit, falsifiable statements about the future: concrete
events, outcomes, or metrics with enough specificity that a later reader could
check whether it came true. Skip vague futurism, hedge-everything statements,
or generic optimism/pessimism with no checkable claim. Include timeframes
whenever the speaker gives one, and preserve them in the normalized
`prediction` text even if the quote itself is looser.

## Speaker attribution (no audio -- context only)
For each prediction, infer `who` from the surrounding text alone:
- Direct address / reply patterns ("Jason, I think...", "No, Chamath...").
- Self-reference and recurring topic/style cues (see config/hosts.yaml
  attribution_hints per permanent host).
- Guest identification: if a guest is speaking (per episode title/description
  or an in-transcript introduction), use a normalized guest id
  (lowercase, hyphenated, e.g. `rep-swalwell`), not a full name string.
- Track a running best-guess "who's talking" state across the chunk rather
  than judging each line in total isolation -- attribution should be
  internally consistent with nearby lines unless there's a clear turn change.

Assign:
- `who`: `jason` | `chamath` | `sacks` | `friedberg` | a normalized guest id | `unknown`
- `role`: `host` | `guest` (omit/null when `who` is `unknown`)
- `speaker_confidence`: `high` | `medium` | `low`
  - `high`: direct address or unambiguous self-reference nearby.
  - `medium`: consistent with recurring topic/style cues, no direct evidence.
  - `low`: a guess with real uncertainty -- still record it, don't discard.
  - Use `unknown`/`low` rather than forcing a guess when truly unclear.

### Solo guest-interview episodes (learned from the Phase 2 validation gate)
When an episode's transcript is a two-person conversation between a guest and
a single interviewer (rather than the usual 4-host panel), the interviewer is
almost always Jason -- he runs the standalone guest interview segments. If a
prediction comes from the non-guest speaker in a two-person interview and
there's no stronger direct-address/self-reference evidence pointing elsewhere,
attribute it to `jason` at `medium` confidence rather than leaving it
`unknown`. Still prefer direct evidence over this default when it's
available (e.g., the guest addresses the interviewer by another name).

## Output format
Return a JSON array of prediction objects, each shaped as:

```json
{
  "id": "<who>-<hh:mm:ss>",
  "who": "chamath",
  "role": "host",
  "speaker_confidence": "high",
  "quote": "short verbatim excerpt (1-2 sentences max) from the transcript",
  "timestamp": "hh:mm:ss",
  "prediction": "clean, precise restatement suitable for later validation, including timeframe",
  "tags": ["markets", "economy"]
}
```

Notes:
- `id` must be deterministic (`<who>-<timestamp>`, or `unknown-<timestamp>` if
  unattributed) so re-runs are stable and dedupeable.
- `quote` should be a short excerpt (roughly one to two sentences) -- just
  enough to substantiate the prediction, not a long transcript passage.
- `tags`: zero or more values from config/tags.json's allowed_tags list only.
- If a chunk has no qualifying predictions, return an empty array `[]`.
- Do not fabricate timestamps or quotes -- only use what's actually in the
  provided chunk text.

## Where results go
Merge results across all chunks for an episode (dedupe by `id`) and write to
`data/predictions/<episode_id>.json`:

```json
{
  "meta": { "count": N, "count_by_who": { "jason": 2, "chamath": 1 } },
  "predictions": [ ... ]
}
```
