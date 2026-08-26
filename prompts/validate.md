# Prediction validation

For a given extracted prediction, determine whether it came true using
WebSearch/WebFetch (free, built into Claude Code -- no OpenAI/xAI calls).

## Input
A single prediction object from `data/predictions/<episode_id>.json`, plus
episode context (title, publish date).

## Task
Research using WebSearch (and WebFetch for promising individual sources) to
determine the outcome. Be concise; cite sources.

Output one of these results:
- `right` -- the prediction appears to have come true.
- `wrong` -- the prediction appears to have been incorrect.
- `ambiguous` -- hard to tell due to confounding factors or unclear data.
- `inconclusive` -- not enough time has passed to know yet.

## Output format
Write to `data/checks/<episode_id>.json`, merging into the existing file if
present (dedupe by `id`, skip already-checked predictions unless re-run with
explicit force):

```json
{
  "meta": { "count": N, "count_by_result": { "right": 2, "wrong": 1 } },
  "checks": [
    {
      "id": "chamath-00:12:34",
      "result": "right",
      "explanation": "Rationale referencing sources, basic markdown ok (bold/italic/links/lists, no headings).",
      "sources": [ { "title": "...", "url": "..." } ]
    }
  ]
}
```

Rules:
- `explanation` must reference the sources that informed the verdict.
- Prefer `inconclusive` over guessing when the prediction's timeframe hasn't
  fully elapsed yet relative to today's date.
- Prefer `ambiguous` over a forced right/wrong when evidence is genuinely
  mixed or the claim is too fuzzy to score cleanly even after enough time has
  passed.
- Keep `explanation` a few sentences, not an essay.
