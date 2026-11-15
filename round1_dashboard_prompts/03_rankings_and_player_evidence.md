# Stage 03 · Implement both ranked boards

## Agent prompt

Use the exact recommendation records from [Stage 00](00_evidence_contract.md), the photo manifest from [Stage 01](01_portrait_library.md) and the component rules from [Stage 02](02_visual_system.md). Use one shared role-card system. Rank-one cards can enlarge the photo and give slightly more visible copy while preserving the same schema and order. Implement real content first and wire motion in Stage 05.

### Reference order for automated checks

| Rank | Batters | Bowlers |
| ---: | --- | --- |
| 1 | Vaibhav Sooryavanshi | Mohammed Siraj |
| 2 | Josh Inglis | Jason Holder |
| 3 | Sameer Rizvi | Kartik Tyagi |
| 4 | Cooper Connolly | Lungi Ngidi |
| 5 | Donovan Ferreira | Krunal Pandya |
| 6 | Abishek Porel | Rasikh Salam |
| 7 | Riyan Parag | Trent Boult |
| 8 | Prabhsimran Singh | Mohammed Shami |
| 9 | Ravindra Jadeja | Anshul Kamboj |
| 10 | Venkatesh Iyer | Ravindra Jadeja |

The table is an acceptance fixture. Read the UI data from the canonical bundle. Produce two semantic ordered lists, each with exactly ten entries and stable anchors such as `#batting-vaibhav-sooryavanshi` and `#bowling-mohammed-siraj`. Keep the two Jadeja anchors role-specific and cross-link them inside the expanded evidence. Read role and phase from the data. Translate tokens into plain terms such as “Powerplay batting”, “Middle-order batting”, “Finisher”, “New-ball bowling”, “Middle-overs pace”, “Death bowling” and “Spin”. Check labels against evidence when a player contributed in more than one phase. Kamboj has powerplay deployment in the model and recorded recent death-over evidence. Both can be shown with their context visible.

### Card anatomy and controls

1. Show the actual rank, portrait, player name and deployment. Include a short RR fit sentence or legible route label. Distinguish “RR squad decision” and “Conditional auction target” with words and a shared explanation. Historic kit is photograph context.
2. Make the primary compact evidence either observed pressure impact with its legal-ball sample or a verified forecast labelled “Forecast impact”. Use a consistent hierarchy across all role cards. Show “Top-10 stability” rounded to one decimal place. Vaibhav is 95.8% and Siraj is 89.4% from the specified audit. Provide a plain explanation within reading distance. The percentage is inclusion across 1,000 whole-match resamples with the audited method and candidate pools.
3. Use a keyboard-accessible control labelled “Player evidence”, with contextual accessible naming. An expandable section or a native disclosure keeps the comparison simple. Opening it reveals ordinary and pressure impact side by side with exposure, signed difference, affected fixtures, forecast impact, match-omission range if available, stability and a short fit/caution note. Mark both observed bars with “run equivalents per 12 legal balls”, a zero baseline and direct numeric labels. Use a common domain within a comparable discipline view or show numeric pairs without bars. A negative value needs a minus sign and left-of-zero treatment. Preserve neutral zero and the missing state. If tooltips add value, expose their contents on focus or tap too. Keep key evidence in text.
4. Explain direction cleanly. Positive impact in each discipline represents favourable performance relative to similar match contexts. Uplift is observed pressure impact minus the same player's ordinary impact. Match-omission ranges are sensitivity checks. Rank also reflects the model's forecast, evidence volume and role coverage. A player can have positive impact under pressure with a lower pressure value than their own usual level. Exact stats belong in the expandable panel, where full names and units fit.
5. Put photo credits in the shared index, or directly with the assets if the reuse terms require individual attribution. As appropriate, use empty alternative text for a redundant portrait next to its labelled name. For an image serving as the accessible name, describe the identity. Preserve focus after expanding, closing or following a role cross-link. Keep links above decorative geometry layers.
6. Keep the recommended ranking order fixed when a reader opens several players or changes an evidence view. Any comparison control preserves visible names, disciplines and ranks. Scenario alternatives belong in Stage 04. Avoid dragging, carousel-only access and sorting by a single raw statistic.

### Loop and handoff

Render all entries. Compare DOM order and image IDs against the acceptance fixture, check both Jadeja computations and the Vaibhav and Siraj values, then manually verify one small sample, one negative rate and one absent interval. Test tabs, keyboard activation and anchor focus. **Pass** when all 20 role cards match their exact audit rows, 19 assets appear correctly, and evidence is readable without hover and without reordering any entry. Open [Stage 04](04_methodology_and_project_story.md).
