#!/usr/bin/env python3
"""
Build paste-ready Squarespace Code Block files, one per page, into
squarespace-ready/.

Two kinds of pages:

1. Marker pages — the standalone HTML already contains a
   `BEGIN ha-xxx` … `END ha-xxx` block authored for injection. We just
   slice that block out (dropping the preview-only <html>/<head>/nav
   chrome) and write it to its own file.

2. Homepage (index.html) — never had injection markers. It was built as
   a full standalone page with global CSS resets and a fixed-nav chrome.
   We assemble a scoped injection: fonts + the head <style> (with the 6
   global rules scoped to #ha-home-embed so they can't leak into the
   Squarespace template) + the content sections (hero…get-involved,
   dropping announce/nav/footer) + the behaviour scripts (the two chrome
   scripts are null-guarded, so they no-op harmlessly).

Run:  python3 scripts/build_squarespace.py
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "squarespace-ready")

# Relative asset paths (assets/…) resolve against the Squarespace page URL
# once pasted, so images 404. Rewrite them to absolute URLs on the GitHub
# Pages host, which serves the same asset tree. NOTE: this hotlinks assets
# from GitHub Pages — a stopgap; for production, upload the images to
# Squarespace and swap these URLs so the site doesn't depend on Pages.
ASSET_BASE = "https://dtomkatsu.github.io/Hawaii-Appleseed-website/"


# The issue pages carry fixed-position scroll enhancements — a scroll
# progress bar and a sticky pill/tab nav pinned at top:107px (below the
# GitHub site's fixed nav). position:fixed can't anchor to the viewport
# inside a code block (transformed section wrappers capture it, and there
# is no fixed site nav at 107px). Rebuild the nav as position:sticky
# (code-block-safe) anchored at top:0, collapsing to 0 height until its
# reveal-on-scroll class fires so it leaves no gap in the flow. The thin
# scroll-progress line has no sticky equivalent, so it stays hidden. Class
# names exist only on the issue pages, so this is a no-op elsewhere.
# How the sticky rebuild works (verified in-browser):
#   1. The page roots use overflow-x:hidden, which forces overflow-y:auto —
#      a scroll container that traps position:sticky (it anchors to the root
#      instead of the viewport and never engages). overflow:clip clips the
#      same way WITHOUT creating a scroll container.
#   2. The bar becomes position:sticky top:0 (its markup is already the
#      first child of the page-root section, so it can stick for the whole
#      page).
#   3. A tiny script gives the bar a negative bottom margin equal to its
#      height, so it occupies ZERO net flow space — while hidden (opacity 0,
#      the original reveal state) it overlays the hero top with no gap, and
#      the page's existing IntersectionObserver reveal keeps working as
#      designed. ResizeObserver keeps the margin in sync when pills wrap.
# The thin scroll-progress line has no sticky equivalent and stays hidden.
STICKY_BAR_OVERRIDE = (
    "\n<style>\n"
    "/* Squarespace-fit: fixed-position bars can't anchor to the viewport\n"
    "   inside a code block. Hide the progress line; rebuild the pill/tab\n"
    "   nav as a sticky overlay (see build_squarespace.py). */\n"
    ".ha-progress { display: none !important; }\n"
    ".ha-issues, .ha-tax, .ha-food, .ha-housing, .ha-transit, .ha-wages "
    "{ overflow: clip !important; }\n"
    ".ha-nav-bar, [class*=\"__stuck-bar\"] {\n"
    "  position: sticky !important; top: 0 !important;\n"
    "  left: auto !important; right: auto !important;\n"
    "}\n"
    "</style>\n"
    "<script>\n"
    "(function(){\n"
    "  // Sticky overlay: cancel the bar's flow height so it overlays the\n"
    "  // hero top while hidden (no gap); resync when the pills wrap.\n"
    "  document.querySelectorAll('.ha-nav-bar, [class*=\"__stuck-bar\"]')"
    ".forEach(function(bar){\n"
    "    var sync = function(){ "
    "bar.style.marginBottom = -bar.offsetHeight + 'px'; };\n"
    "    if (window.ResizeObserver) "
    "new ResizeObserver(sync).observe(bar);\n"
    "    window.addEventListener('resize', sync);\n"
    "    sync();\n"
    "  });\n"
    "})();\n"
    "</script>\n"
)


# Internal cross-page links (href="food-security.html", "issues.html", …)
# point at our source filenames, which don't exist as Squarespace pages —
# the live site uses its own slugs. Confirmed against the real site
# (hiappleseed.org) and from the user directly. Query strings and #anchors
# on the original href are preserved (e.g. "support.html#give" ->
# "/support#give", "publications.html?cat=X" -> "/publications?cat=X").
INTERNAL_LINK_MAP = {
    "index.html":               "/",
    "issues.html":               "/issues",
    "our-mission.html":          "/our-mission",
    "our-mission-light.html":    "/our-mission",
    "our-story.html":            "/our-history",
    "our-story-light.html":      "/our-history",
    "our-team.html":             "/our-team",
    "board-of-directors.html":   "/board-of-directors",
    "publications.html":         "/publications",
    "in-the-news.html":          "/in-the-news",
    "support.html":              "/support",
    "taxes-budget.html":         "/taxes-budget",
    "food-security.html":        "/food-equity",
    "housing.html":              "/affordable-housing",
    "transportation.html":       "/transportation-equity",
    "wages-labor.html":          "/wages-labor",
}


def remap_internal_links(html):
    """href="food-security.html?cat=X#foo" -> href="/food-equity?cat=X#foo" """
    names = "|".join(re.escape(k) for k in INTERNAL_LINK_MAP)
    pattern = r'href="(' + names + r')((?:[?#][^"]*)?)"'
    return re.sub(
        pattern,
        lambda m: 'href="' + INTERNAL_LINK_MAP[m.group(1)] + m.group(2) + '"',
        html,
    )


def absolutize_assets(html):
    """Rewrite relative resource paths to absolute Pages URLs:
      • src/url()/href to assets/…  (images, etc.)
      • the data files scripts fetch() at the site root — publications.json,
        news.json — which otherwise 404 against the Squarespace domain and
        collapse the section to its fallback text. GitHub Pages serves these
        with Access-Control-Allow-Origin:* so the cross-origin fetch works.
    Internal .html page links are handled separately by
    remap_internal_links(), below, since they map to real Squarespace
    page slugs rather than the Pages preview."""
    html = re.sub(r"""(["'(])(?:\./)?(assets/)""",
                  lambda m: m.group(1) + ASSET_BASE + m.group(2), html)
    html = re.sub(r"""(["'])((?:publications|news)\.json)(["'])""",
                  lambda m: m.group(1) + ASSET_BASE + m.group(2) + m.group(3),
                  html)
    return html

# (source file, marker slug, Squarespace page name, note)
MARKER_PAGES = [
    ("our-mission.html",        "ha-mission",      "Our Mission",     ""),
    ("our-mission-light.html",  "ha-mission",      "Our Mission",     "light-background variant — use this OR our-mission, not both"),
    ("our-story.html",          "ha-story",        "Our Story",       ""),
    ("our-story-light.html",    "ha-story",        "Our Story",       "light-background variant — use this OR our-story, not both"),
    ("issues.html",             "ha-issues",       "Issues",          ""),
    ("our-team.html",           "ha-team",         "Our Team",        ""),
    ("board-of-directors.html", "ha-board",        "Board",           ""),
    ("taxes-budget.html",       "ha-tax",          "Taxes & Budget",  ""),
    ("food-security.html",      "ha-food",         "Food Security",   ""),
    ("housing.html",            "ha-housing",      "Housing",         ""),
    ("transportation.html",     "ha-transit",      "Transportation",  ""),
    ("wages-labor.html",        "ha-wages",        "Wages & Labor",   ""),
    ("publications.html",       "ha-publications", "Publications",    ""),
]


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return f.read().split("\n")


def entity_encode(html):
    """Escape every non-ASCII character so the output survives pasting into
    a Squarespace Code Block regardless of how Squarespace (mis)handles the
    byte encoding — a raw paste showed 'Hawai ᵃi' / 'ISSUES,üi'.

    Encoding is context-aware, because the right escape differs by where the
    character sits:
      • markup/text  -> HTML numeric entity   (&#699;)
      • <script> JS  -> JS unicode escape      (\\u02bb)  — valid in string
                        literals, harmless in comments; entities would NOT
                        be decoded here.
      • <style> CSS  -> CSS hex escape         (\\2bb ) — valid in values,
                        harmless in comments.
    The surrounding <script>/<style> tags are ASCII, so only the inner
    non-ASCII characters are touched."""
    parts = re.split(r"(<script[\s\S]*?</script>|<style[\s\S]*?</style>)", html,
                     flags=re.I)
    out = []
    for i, part in enumerate(parts):
        if i % 2 == 0:                                   # markup / text
            out.append("".join(
                c if ord(c) < 128 else "&#%d;" % ord(c) for c in part))
        elif part[:7].lower() == "<script":             # JS
            out.append("".join(
                c if ord(c) < 128 else "\\u%04x" % ord(c) for c in part))
        else:                                            # CSS
            out.append("".join(
                c if ord(c) < 128 else "\\%x " % ord(c) for c in part))
    return "".join(out)


def header(page, note):
    n = ("\n     NOTE: " + note) if note else ""
    return (
        "<!-- =====================================================================\n"
        "     PASTE-READY Squarespace injection for the \"%s\" page.\n"
        "     Generated by scripts/build_squarespace.py — do not hand-edit;\n"
        "     edit the source page and re-run the script.\n"
        "     HOW: %s page > Edit > add a Code Block > paste ALL of this >\n"
        "          make sure \"Display Source\" is OFF > Save.%s\n"
        "     ===================================================================== -->\n"
        % (page, page, n)
    )


def extract_marker(lines, slug):
    """Return the lines between the BEGIN and END markers for a slug,
    working for all three marker comment styles.

    The instruction comment itself mentions "BEGIN <slug>" and "END
    <slug>" in prose, so we take the LAST occurrence of each — that is
    always the real marker, never the prose mention."""
    begins = [i for i, l in enumerate(lines) if ("BEGIN " + slug) in l]
    ends = [i for i, l in enumerate(lines) if ("END " + slug) in l]
    begin = begins[-1]
    # the BEGIN token may sit inside a multi-line instruction comment;
    # content starts after that comment closes.
    j = begin
    while "-->" not in lines[j]:
        j += 1
    start = j + 1
    end = ends[-1]
    return lines[start:end]


def _find(lines, needle, start=0):
    return next(i for i in range(start, len(lines)) if needle in lines[i])


def build_homepage(lines):
    # Locate everything by content landmarks (not line numbers) so the
    # script survives edits to index.html.
    body_i = _find(lines, "<body")

    # Fonts: the preconnect + the googleapis css2 stylesheet link (head).
    f_pre = _find(lines, 'rel="preconnect" href="https://fonts.gstatic.com"')
    f_css = _find(lines, "fonts.googleapis.com/css2")
    fonts = "\n".join([lines[f_pre], lines[f_css]])

    # CSS: first <style> in the head through the last </style> before <body>.
    css_start = _find(lines, "<style>")
    css_end = max(i for i in range(body_i) if "</style>" in lines[i])
    css = "\n".join(lines[css_start:css_end + 1])

    # Markup: the real hero (big headline + 3D parallax) through the last
    # content section, footer chrome excluded. The clipping that once forced
    # a swap to the simpler video-hero card was the ID-specificity reset
    # zeroing the hero's padding — now fixed with :where() below — plus a
    # container-fit override appended to the CSS.
    hero_i = _find(lines, '<section class="ha-home__hero"')
    footer_i = _find(lines, 'class="px-footer"', hero_i)
    markup_lines = lines[hero_i:footer_i]
    while markup_lines and (not markup_lines[-1].strip()
                            or markup_lines[-1].strip().startswith("<!--")):
        markup_lines.pop()
    markup = "\n".join(markup_lines)

    # Scripts: everything between </footer> and </body> (behaviour scripts;
    # the two chrome scripts are null-guarded no-ops).
    footer_close = _find(lines, "</footer>", footer_i)
    scripts_start = _find(lines, "<script", footer_close)
    body_close = _find(lines, "</body>")
    scripts = "\n".join(lines[scripts_start:body_close])

    # Scope the 6 global rules so they cannot bleed into the Squarespace page.
    #
    # The two universal (*) resets MUST stay at zero specificity, so wrap them
    # in :where(): a plain `#ha-home-embed *{padding:0}` carries ID specificity
    # and would beat every class rule like `.ha-home__issues{padding:7rem 8%}`,
    # collapsing all section padding (content jams to the left edge). :where()
    # contributes 0 specificity, preserving the original global-reset cascade
    # where class padding wins.
    css = css.replace(
        "*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }",
        ":where(#ha-home-embed, #ha-home-embed *, #ha-home-embed *::before, #ha-home-embed *::after) { box-sizing: border-box; margin: 0; padding: 0; }",
    )
    css = css.replace(
        "*, *::before, *::after{",
        ":where(#ha-home-embed *, #ha-home-embed *::before, #ha-home-embed *::after){",
    )
    # These target specific elements (not `*`), so ID specificity is harmless.
    css = css.replace("html { scroll-behavior: smooth; }", "")
    css = re.sub(r"(?m)^(\s*)body\s*\{", r"\1#ha-home-embed {", css, count=1)
    css = css.replace(
        "section[id] { scroll-margin-top: 124px; }",
        "#ha-home-embed section[id] { scroll-margin-top: 124px; }",
    )
    css = css.replace(
        "a, button { -webkit-tap-highlight-color: transparent; }",
        "#ha-home-embed a, #ha-home-embed button { -webkit-tap-highlight-color: transparent; }",
    )

    # Squarespace-fit override (appended so it wins the cascade). The hero's
    # 92svh height + 7rem top padding assume a fixed nav overlapping its top
    # (as on GitHub Pages). A Squarespace section has no such overlap, so that
    # space reads as a big gap under the header — trim the height and top pad.
    # NOTE: css includes its own <style>…</style> tags, so the override must
    # live in its OWN <style> block or it lands outside any stylesheet.
    css += (
        "\n<style>\n"
        "/* --- Squarespace-fit hero (no fixed-nav overlap here) --- */\n"
        "#ha-home-embed .ha-home__hero, #ha-home-embed .hero-inner "
        "{ min-height: 80svh !important; }\n"
        "#ha-home-embed .hero-inner { padding-top: 2.5rem !important; }\n"
        "</style>\n"
    )

    note = ("the real homepage hero (big headline + parallax) with a "
            "Squarespace-fit height override; everything below is the live "
            "homepage. Video controls sit bottom-left with a seek scrubber.")
    return (
        header("Home", note)
        + "<!-- BEGIN ha-home -->\n"
        + '<div id="ha-home-embed">\n'
        + fonts + "\n"
        + css + "\n"
        + markup + "\n"
        + scripts + "\n"
        + "</div>\n"
        + "<!-- END ha-home -->\n"
    )


def main():
    os.makedirs(OUT, exist_ok=True)
    manifest = []

    for src, slug, page, note in MARKER_PAGES:
        block = extract_marker(read(src), slug)
        out_name = src  # keep the same stem so the mapping is obvious
        body = entity_encode(remap_internal_links(absolutize_assets(
            header(page, note) + "\n".join(block).strip()
            + STICKY_BAR_OVERRIDE)))
        with open(os.path.join(OUT, out_name), "w", encoding="utf-8") as f:
            f.write(body)
        manifest.append((out_name, page, len(body)))

    home = entity_encode(remap_internal_links(
        absolutize_assets(build_homepage(read("index.html")))))
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(home)
    manifest.append(("index.html", "Home", len(home)))

    print("Wrote %d files to squarespace-ready/:" % len(manifest))
    for name, page, size in manifest:
        print("  %-26s -> %-16s (%d KB)" % (name, page, round(size / 1024)))


if __name__ == "__main__":
    main()
