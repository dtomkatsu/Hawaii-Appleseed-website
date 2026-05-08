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

## When touching layout / type / padding

1. Open the page in a browser at **375px wide** (Chrome DevTools device emulation → iPhone SE or custom 375).
2. Verify nav, headlines, CTAs, body text all render readably WITHOUT horizontal scroll.
3. Only after that's good, check desktop ≥1024px.

## Companion docs (in vault)

- `~/.openclaw/workspace/projects/HawaiiAppleseed.md` — full project context.
- `~/.openclaw/workspace/tasks/HawaiiAppleseed.md` — active worklist.
- Distinct from `~/.openclaw/workspace/projects/appleseed-writing-bot.md` (RAG bot, separate repo).
