# Design System

Source of truth: `site_src/static/style.css` and `site_src/templates/*.html`. This document explains and organizes what's already implemented there; if the two ever disagree, the CSS/templates are correct and this file needs updating, not the other way around.

## Design philosophy

Dark, quiet, and citation-first: the UI should get out of the way of the actual content (a quote, a prediction, a verdict, a source), not perform enthusiasm about it. No framework, no animation for its own sake, no color used decoratively; every non-neutral color on the site means a specific verdict (right/wrong/ambiguous/inconclusive), never just "brand."

## Color palette

All colors are defined as CSS custom properties in `:root` (`site_src/static/style.css`).

| Token | Value | Use |
|---|---|---|
| `--bg` | `#080d0b` | Page background (near-black, slight green tint) |
| `--fg` | `#f5f5f5` | Primary text |
| `--muted` | `#9ca3af` | Secondary text (dates, counts, captions) |
| `--border` | `rgba(255, 255, 255, 0.1)` | Card/section borders, dividers |
| `--card-bg` | `rgba(255, 255, 255, 0.03)` | Card background fill |
| `--right` | `#22c55e` | "Right" verdict (green) |
| `--wrong` | `#ef4444` | "Wrong" verdict (red) |
| `--ambiguous` | `#d4c4a8` | "Ambiguous" verdict (warm tan, deliberately not red/green/gray so it doesn't read as "leaning right or wrong") |
| `--inconclusive` | `#6b7280` | "Inconclusive" verdict (neutral gray) |
| `--unvalidated` | `#94a3b8` | "Unvalidated" state (light slate, visually the least emphasized) |

Verdict colors are also used at reduced opacity for badge backgrounds (e.g. `rgba(34,197,94,.18)` for the right-badge background, with a lighter tint like `#bbf7d0` for its text); see `.badge-*` classes in `style.css` for the exact pairing per verdict.

**Rule:** never introduce a new color outside this palette for a new UI element without a reason tied to meaning (a new verdict type, a new semantic state). If a new element just needs visual hierarchy, reuse `--muted`, `--border`, or opacity variants of `--fg`/white, don't invent a new hex value.

## Typography

No custom web fonts are loaded (keeps the site dependency-free and fast). The stack is the OS-native system font:
```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
```

| Role | Size | Weight | Notes |
|---|---|---|---|
| H1 | `1.75rem` | default (browser bold for `<h1>`) | Page titles (episode title, host name) |
| H2 | `1.25rem` | default bold | Section headers ("Host Accuracy", "Recent Episodes") |
| Body | `1rem` (browser default), `line-height: 1.5` | normal | Prediction text, explanations |
| Caption / label | `.75rem`–`.875rem` | normal | `.muted` text (dates, counts), tags (`.7rem`, uppercase, letter-spaced) |
| Badge / code-like | `.7rem`–`.85rem` | `600` (semibold) | Who-badges, status badges, timestamps |

There is no monospace/code role in the current UI (no code is ever rendered to end users).

## Spacing system

Not a strict fixed base unit (like a rigid 4px/8px grid): spacing is expressed directly in `rem` at the values actually needed, drawn from a small, consistent set: `.25rem .5rem .75rem 1rem 1.5rem 2rem 2.5rem`. In practice this behaves like an approximate 4px base (`.25rem` = 4px at the default 16px root) scaled up in those increments. When adding new spacing, pick from that existing set rather than an arbitrary value.

## Breakpoints

There is exactly **one** breakpoint in the current CSS:

```css
@media (max-width: 700px) {
  .grid-2 { grid-template-columns: minmax(0, 1fr); }
}
```

At 700px and below, the two-column grid (`.grid-2`, used for host scorecards, episode cards) collapses to a single column. Everything else in the layout is fluid/flex-wrap based (`flex-wrap: wrap` on header nav, scorecard heads, prediction card heads) rather than breakpoint-based, so it reflows naturally at other widths without needing additional media queries.

**Note:** a formal mobile-responsiveness audit across more widths (375px, 900px, 1150px, 1440px, 1920px per the methodology in the rewrite's roadmap) is planned but has not yet run (see PRD.md §16.3). This single breakpoint has not yet been stress-tested at the narrower widths.

## Component patterns

- **Cards** (`.card`): `1px solid var(--border)`, `.5rem` border-radius, `1rem` padding, `var(--card-bg)` fill. This is the base building block for scorecards, episode-list cards, and prediction cards; always start a new component from `.card` rather than redefining border/radius/background from scratch.
- **Scorecards** (`.scorecard`): a `.card` containing a name/count header (`.scorecard-head`) and a body (`.scorecard-body`) holding the donut chart + legend table side by side (wraps on narrow widths via `flex-wrap`).
- **Prediction cards** (`.prediction-card`): a `.card` with a header row (who-badge, verdict badge, optional low-confidence badge, timestamp, tags), the prediction text, a blockquote-styled original quote (`.quote`, left-border accent), and an optional collapsible explanation block with cited sources.
- **Badges** (`.badge`, `.who-badge`, `.tag`): small, pill/rounded-rect labels, `.2rem-.25rem` padding, `.7rem-.75rem` font, `600` weight for status/who badges. Verdict badges (`.badge-right` etc.) always pair a tinted background with a lighter, higher-contrast text color in the same hue family, never plain `--fg` text on a tinted background.
- **Charts:** donut and stacked-bar charts are hand-rolled inline SVG (no chart library), generated server-side at build time for the default view, with a click-to-toggle alternate view swapped in client-side by `app.js` (see PRD.md §9.3). Always use the verdict color tokens above for chart segments, in the same order as the legend.
- **Modals** (`.modal`): fixed, full-viewport, centered flex, `rgba(0,0,0,.7)` scrim, a `28rem`-max-width box using the same border/radius/background language as `.card`. Currently used only for the one-time YouTube-link disclaimer.

## Accessibility

- **Target:** no formal WCAG level has been certified, but the palette and type choices are informally targeting **WCAG AA** contrast for primary text (`--fg` `#f5f5f5` on `--bg` `#080d0b` is a very high-contrast pairing well above AA). Verdict badge text/background pairs (e.g. `#bbf7d0` on `rgba(34,197,94,.18)`) have not been formally contrast-checked against AA and should be verified as part of a future accessibility pass.
- **Keyboard navigation:** all interactive elements (`<a>`, `<button>`) are native HTML elements, not custom `<div>`-based controls, so they get keyboard focus and activation for free without extra ARIA work. The chart-toggle interaction (`app.js`) is attached to the donut's container `<div>`, which is a known gap: it's currently mouse/touch-only (`click` listener) with no keyboard equivalent; this should be fixed (e.g. make it a real `<button>`, or add a keyboard handler) as part of a future accessibility pass rather than left as-is indefinitely.
- **No custom focus styles** are currently defined (relying on browser defaults), which is acceptable but not ideal; worth revisiting alongside the contrast check above.

## Animation & motion

Deliberately minimal:
- Chart.js-style animated transitions are **not** used; SVG chart redraws (on filter/toggle) are instant DOM swaps, not animated.
- The only CSS transition-adjacent effect is `backdrop-filter: blur(6px)` on the sticky header, which is a static visual effect, not a motion animation.
- No page-load animations, no hover-lift effects, no scroll-triggered animations exist anywhere in the current CSS.
- **Rule:** motion should only ever be added if it clarifies a state change (e.g., a future smooth transition between chart views), never purely decorative. Given G1/G4's "keep it simple, dependency-free" tenets (see PRD.md §18), any animation should be pure CSS, not a new JS animation library.

## Notes for future work (AI or human)

- When adding a new page, always extend `base.html` and pass `asset_prefix` explicitly if the new page lives one level below `rewrite/` root (see PRD.md §21's runbook entry on this exact bug): the header/nav/footer render before any per-page `{% set %}` would take effect, so it must come from the render call, not the template body.
- The site's dark theme is not currently theme-switchable (no light mode). If a light mode is ever added, every token in the palette table above needs a light-mode counterpart, and the verdict colors in particular need to be re-checked for contrast against a light background.
- Keep new components built from `.card` and the existing badge/tag patterns rather than introducing new visual primitives, to keep the "quiet, citation-first" philosophy intact as the site grows (more pages, the Annual Predictions filter feature, etc.).
