# Stage 01 · Source and prepare all 19 player portraits

## Agent prompt

Use the verified IDs from [Stage 00](00_evidence_contract.md). Source an authentic, high-quality still photo for each player, with an exact name and a documented provenance. Build a coherent set of cricket portraits with the same silhouette treatment, quality and visual weight. Select alternate photos when they better fit the crop and have a clearer reuse basis.

### Source by the 2026 reference squad

Use these mappings to locate historical photographs. For external candidates, the source club is the 2026 photo context. It is unrelated to the forecast rank or the availability of the player for 2027. Open the official source page and confirm the identity and photo season. Prefer a team or league media pack with a usable reuse statement, then licensed or expressly authorized photos, or an authorized original supplied by the user. The official profile may confirm identity even when its photo has a different reuse status. Start at the [IPL teams directory](https://www.iplt20.com/teams), the [RR squad](https://www.rajasthanroyals.com/rr-players), the [Gujarat Titans squad](https://www.gujarattitansipl.com/players), and the [IPL auction archive](https://www.iplt20.com/auction/2026/teams).

| 2026 reference squad | Canonical identities |
| --- | --- |
| Rajasthan Royals | 50284 Vaibhav Sooryavanshi, 8182 Donovan Ferreira, 6423 Riyan Parag, 152 Ravindra Jadeja |
| Lucknow Super Giants | 4736 Josh Inglis, 1566 Mohammed Shami |
| Delhi Capitals | 8238 Sameer Rizvi, 19714 Abishek Porel, 4641 Lungi Ngidi |
| Punjab Kings | 8654 Cooper Connolly, 7216 Prabhsimran Singh |
| Gujarat Titans | 5944 Mohammed Siraj, 2633 Jason Holder |
| Kolkata Knight Riders | 8530 Kartik Tyagi |
| Royal Challengers Bengaluru | 7544 Venkatesh Iyer, 4219 Krunal Pandya, 7327 Rasikh Salam |
| Mumbai Indians | 2320 Trent Boult |
| Chennai Super Kings | 27964 Anshul Kamboj |

Verify full names and aliases with both a photo caption or an individual profile and the internal identity. Common search variants include Abhishek Porel, Rasikh Dar or Rasikh Salam Dar, Mohd or Mohammad Siraj, and Vaibhav Suryavanshi. The alias is a sourcing clue. Correct facial identity and official context remain required.

### Art direction

1. Prioritize a sharp, unobstructed face and an authentic kit. Featured photos of Vaibhav and Siraj may use an expressive action or media-day pose with clear eyes and a clean upper torso. Ranks 2–10 use consistent upper-body proportion. Reject blurry thumbnails, heavy watermarks, harsh crops across a face, and other players overlapping the required subject. Keep logos and original kit as shown in the photograph. Never recolour a kit to imply an RR signing.
2. Use a transparent master where available. Where authorized, produce a clean alpha cutout using a suitable asset editor and inspect hair, helmet, jersey edges and apparel against both light and dark backgrounds. Keep face, skin texture and proportions authentic. Preserve 8–12% transparent padding for the paper edge. Record a per-player focal point and scale to align eyes to a shared band at roughly 30–36% of the crop. Confirm at the actual container sizes.
3. Make a continuous warm-white silhouette stroke `#FFF8ED`, about 5–7 CSS px on leader portraits and 3–4 px on standard portraits at their intended render sizes. Prefer a raster matte from the alpha when CSS produces a scalloped or uneven edge. Use a separate flat paper shadow with one consistent direction. Keep the outer edge legible against geometry, including cream backgrounds. Use a very soft dark edge only where needed. Inspect 2×. Use no SVG masks or art, generated faces, avatar icons, stock body substitutions or text overlays on the face.
4. Use optimized transparent raster output. Export `320w` and `640w` standard variants, `480w`, `800w` and optionally `1200w` for leaders, with local WebP and an appropriate fallback where required. Size caps are in Stage 05. Keep one image family per canonical ID and reuse Jadeja's two displayed variants from that same family. Test historical kit tone and paper edge on pink and blue tiles.
5. Produce a contact sheet with all 19 cutouts, their canonical names and IDs. Review faces at thumbnail and large size. Maintain a source record per ID with publisher, exact page URL, permitted asset URL or supplied filename, credit, photo context/date, access date, rights basis, intended audience, crop notes, output filenames and review status. Render appropriate credits from approved metadata. Keep unchecked masters and staging assets outside the public build.
6. If a candidate lacks a verified, suitable asset for the target audience, check the next authorized source. During staging only, leave the geometric image well and name visible with a plain “Photo pending” label. Continue Stage 02 in parallel when the visual system can be checked with the approved assets. Report the unresolved name and return here before calling the complete handoff finished.

### Loop and handoff

Source, confirm, compare crops, build the cutouts, inspect the contact sheet, spot-check real render sizes and repair until the quality is consistent. **Pass** when the manifest references 19 unique face-verified photographs, the credits and intended use are accounted for, and all 20 role displays share their proper identity. Open [Stage 02](02_visual_system.md).
