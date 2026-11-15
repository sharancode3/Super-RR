# Stage 02 · Build the playful geometric visual system

## Agent prompt

Create a distinctive editorial layout for the competition dashboard. Use real cricket cutouts as the visual anchors and controlled CSS geometry as the background. The look should read as a printed scouting board with offset paper edges. Make the ranking and evidence easy to read in a quick judging pass.

### Layout and hierarchy

- Use one page with four top-level landmarks. Header and primary navigation, ranked athlete boards, the methodology section, and a small source footer. Anchor navigation is **Batters**, **Bowlers**, **How we chose**. Put the two boards next to each other at desktop sizes. Each board begins with its rank-one photo and stays in rank order through the first screen and the following scroll. The hero is the shared page heading “Players RR can back under pressure” or similarly concise copy, one line of scope and the dated cutoff. Include a skip link.
- Use a content max width of `1320px`. At `≥1100px`, use two equal role columns with a `24–32px` gap. Put role titles and both featured leaders within the initial `1440 × 900` view where browser chrome permits. Leader photo wells should be roughly `260–310px` high. Ranks 2–10 use a readable two-card grid inside each board if cards have at least `246px` width. Switch a board to one card across if the content gets tight. Tab order and reading order remain 1–10 within each section.
- At `768–1099px`, stack the boards and let ordinary cards use two columns from `560px` if each has enough width. At smaller widths, use a single column, horizontal compact list entry styling only when portrait and text both fit, and clear sticky anchors. The mobile hero uses one short heading, its one-line context and the lead batting card. The bowlers anchor gives direct mobile access. Use `16px` mobile side padding, `24–40px` desktop, and no horizontal overflow at `320px`.
- The methodology below both boards has a plain-language overview, a short dated project timeline and individual evidence modules. Use cream background and a dark ink heading with readable light-card text. Put all verification-critical caveats where the numbers are presented. Use grounded section names and short descriptions. Reserve big typography for the title and meaningful ranks.

### Tokens

| Token | Exact direction |
| --- | --- |
| Page paper | `#FFF8ED`. Off-white neutral base |
| Cards | `#FFFCF6`. Tinted leader well gradients may be replaced by flat layers |
| Ink | `#20172F`. Main text and strong rules |
| Secondary text | `#534A60`. Captions, credits and units |
| Batters | `#F4CADA` light plane, `#D81465` accent, `#8F0A48` text accent |
| Bowlers | `#CFDAFF` light plane, `#3045A5` accent, `#25367C` text accent |
| Shared small accent | `#F5C24E` decorative or with ink typography |
| Strong UI edge | `#20172F`, 1.5–2px on key interactive surfaces |
| Portrait edge | `#FFF8ED`, precise silhouette outline per Stage 01 |
| Focus ring | Ink or deep cobalt, 3px with 3px offset. Test on every underlying colour |

- Use **Bricolage Grotesque** 700–800 for the masthead and player names, **Inter** 400–600 for body, and Inter tabular numerals for data. Prefer locally served subsetted WOFF2 files with appropriate font licenses. Suggested heading size is `clamp(2.5rem,5vw,5rem)` at line-height `.97–1.05`. Section headings `32–52px`, leader names `27–36px`, other names `20–24px`, body `16–17px` line-height `1.5–1.65`, metrics and captions `14–16px`. Permit long real names to wrap naturally without ellipses.
- Space using 4, 8, 12, 16, 24, 32, 48, 64 and 96px. Page section gaps use `64–96px` desktop and `44–64px` mobile. Cards use `14–18px` corner radii, `12–20px` internal padding, soft or offset 2–4px paper shadows. Buttons use at least `44px` high by `44px` wide. Top hero links are `48px` high with `16–20px` horizontal padding and `8–12px` corner radius. Controls use real buttons or anchors and visible labels. Header bar should remain around `60–68px` desktop and `56–64px` mobile.
- Use an arc, clipped quadrilateral or large circle as at most two shapes in a portrait well, built with CSS `border-radius`, `clip-path` or pseudo-elements. Put ink rules, blocks and flat coloured planes behind the silhouette. Keep the eye line and lettering intact. Avoid visual noise, tiny floating decoration, generic cards with glass effects, a pinboard collage, emoji, SVG illustrations and strobing pink. Use real rank numbers, section labels and data. Avoid extra decorative numbering or repeated headlines.
- Keep pink and blue as reinforcement for the literal group labels. Use colour with labels and a zero baseline for data. Check body contrast at 4.5:1, large type at 3:1, and informative visual controls and indicators at 3:1 where applicable. Keep legal and source links readable. See [WCAG 2.2](https://www.w3.org/TR/WCAG22/).

### Loop and handoff

Build an unanimated shell, compare desktop and mobile screenshots, then adjust type, shape scale, spacing and crop on the actual names rather than using placeholder lengths. Check `320`, `390`, `768`, `1024` and `1440` pixels. **Pass** when both leaders and key context are immediately visible on desktop, the three anchors work on small screens, and every heading and control is readable across the full range. Open [Stage 03](03_rankings_and_player_evidence.md).
