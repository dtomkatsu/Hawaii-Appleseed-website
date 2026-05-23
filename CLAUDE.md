# HawaiiAppleseed (website) — Claude rules

## HARD rules — NEVER violate

- **Brand palette is canonical**: Ash / Teal / Slate / Charcoal. **NEVER** use the original sage-green prototype colors (`--sage-*`, `--appleseed: #3a7811`) for new work. Migrate sage-green to brand palette when touching any page.
- **Mobile-first verification at 375px**: every layout / typography / padding change must be verified at 375px mobile width, NOT just desktop. Use ≤700px media queries with tighter padding (64–80px vs 110px), 20px page padding, smaller eyebrows, stacked CTAs.
- **Brand fonts**: Manrope (body / UI), Poppins (display), Fraunces (editorial accents only). No other fonts.

## Hard rules — engineering

- **Repo-relative paths only** in commits/prompts. Madison's workdir is `~/repos/HawaiiAppleseed/`.
- **No build step**: hand-rolled HTML/CSS, no SSG, no JS framework. Don't introduce one without explicit approval.
- **Static hosting**: GitHub Pages or drop-in to existing site.

## Pages currently

- `index.html`, `our-mission.html`, `our-story.html` — more in flight.
- `index.html` still contains the legacy sage-green `<style>` block; needs migration.

## Issue deep-dive pages — MIRROR FORMAT

The five issue deep-dive pages share a single canonical format:

- `taxes-budget.html`
- `housing.html`
- `food-security.html`
- `transportation.html`
- `wages-labor.html`

**Structural mirror requirement:** any structural change (tabs added/removed/renamed, section reorder, hero treatment, CTA placement, footer columns) made to *one* issue page must be applied to *all five* in the same commit. The pages should always share:

1. **Same nav + announcement bar** (the `px-*` chrome at top)
2. **Same hero structure**: eyebrow + h1 + lead paragraph + tabs row
3. **Same four tabs in the same order**: `Vision`, `Overview`, `Opportunities`, `Impact`
4. **Same sticky-tabs behavior** (`.ha-{slug}__stuck-tabs` reveals on scroll)
5. **Same panel skeleton** inside each tab (heading, body, supporting blocks)
6. **Same trailing sections**: Research & News → CTA → Footer
7. **Same brand palette + fonts + spacing tokens**

What *differs* between pages (and SHOULD differ):

- The CSS namespace prefix (`.ha-tax__*` → `.ha-housing__*` etc.)
- Per-page copy, stats, and pull-quotes
- Per-page accent color from the brand palette (but stay within Ash / Teal / Teal-deep / Slate / Charcoal)
- SVG icons / charts specific to the issue

**When in doubt about a format change:** ask "would this make sense if applied to all five pages?" If no, the change probably belongs in a *content* block (where pages diverge), not the *structure*.

## When touching layout / type / padding

1. Open the page in a browser at **375px wide** (Chrome DevTools device emulation → iPhone SE or custom 375).
2. Verify nav, headlines, CTAs, body text all render readably WITHOUT horizontal scroll.
3. Only after that's good, check desktop ≥1024px.

## Companion docs (in vault)

- `~/.openclaw/workspace/projects/HawaiiAppleseed.md` — full project context.
- `~/.openclaw/workspace/tasks/HawaiiAppleseed.md` — active worklist.
- Distinct from `~/.openclaw/workspace/projects/appleseed-writing-bot.md` (RAG bot, separate repo).
