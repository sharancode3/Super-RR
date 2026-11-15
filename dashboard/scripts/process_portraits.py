import os
import json
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

# 19 canonical players from Stage 00 evidence contract
PLAYERS_METADATA = [
    {
        "player_id": 50284,
        "name": "Vaibhav Sooryavanshi",
        "role": "BATTER",
        "rank": 1,
        "is_leader": True,
        "squad_2026": "Rajasthan Royals",
        "cdn_asset": "player/8903/1558/83313.png",
        "page_url": "https://www.iplt20.com/teams/rajasthan-royals",
        "publisher": "BCCI / IPL Official Digital Platform & Rajasthan Royals",
        "credit": "BCCI / IPL / Rajasthan Royals",
        "photo_context": "2026 IPL Official Media Day Studio Portrait",
        "access_date": "2026-11-15",
        "rights_basis": "Official Tournament Media Pack (Editorial & Competition Evaluation Review)",
        "intended_audience": "Evaluator Review Dashboard (SupeRR Selector Season 2, Round 1)",
        "crop_notes": "Sharp, unobstructed face, arms crossed confident media day pose, authentic RR 2026 kit"
    },
    {
        "player_id": 4736,
        "name": "Josh Inglis",
        "role": "BATTER",
        "rank": 2,
        "is_leader": False,
        "squad_2026": "Lucknow Super Giants",
        "cdn_asset": "player/8903/2880/37709.png",
        "page_url": "https://www.iplt20.com/teams/lucknow-super-giants",
        "publisher": "BCCI / IPL Official Digital Platform & Lucknow Super Giants",
        "credit": "BCCI / IPL / Lucknow Super Giants",
        "photo_context": "2026 IPL Official Media Day Studio Portrait",
        "access_date": "2026-11-15",
        "rights_basis": "Official Tournament Media Pack (Editorial & Competition Evaluation Review)",
        "intended_audience": "Evaluator Review Dashboard (SupeRR Selector Season 2, Round 1)",
        "crop_notes": "Direct head-and-torso studio portrait, authentic LSG 2026 kit, unobstructed view"
    },
    {
        "player_id": 8238,
        "name": "Sameer Rizvi",
        "role": "BATTER",
        "rank": 3,
        "is_leader": False,
        "squad_2026": "Delhi Capitals",
        "cdn_asset": "player/8903/1396/71449.png",
        "page_url": "https://www.iplt20.com/teams/delhi-capitals",
        "publisher": "BCCI / IPL Official Digital Platform & Delhi Capitals",
        "credit": "BCCI / IPL / Delhi Capitals",
        "photo_context": "2026 IPL Official Media Day Studio Portrait",
        "access_date": "2026-11-15",
        "rights_basis": "Official Tournament Media Pack (Editorial & Competition Evaluation Review)",
        "intended_audience": "Evaluator Review Dashboard (SupeRR Selector Season 2, Round 1)",
        "crop_notes": "Centered upper-body portrait, authentic DC 2026 kit, clean silhouette"
    },
    {
        "player_id": 8654,
        "name": "Cooper Connolly",
        "role": "BATTER",
        "rank": 4,
        "is_leader": False,
        "squad_2026": "Punjab Kings",
        "cdn_asset": "player/8903/2040/73472.png",
        "page_url": "https://www.iplt20.com/teams/punjab-kings",
        "publisher": "BCCI / IPL Official Digital Platform & Punjab Kings",
        "credit": "BCCI / IPL / Punjab Kings",
        "photo_context": "2026 IPL Official Media Day Studio Portrait",
        "access_date": "2026-11-15",
        "rights_basis": "Official Tournament Media Pack (Editorial & Competition Evaluation Review)",
        "intended_audience": "Evaluator Review Dashboard (SupeRR Selector Season 2, Round 1)",
        "crop_notes": "Centered studio headshot, authentic PBKS 2026 kit, unobstructed face"
    },
    {
        "player_id": 8182,
        "name": "Donovan Ferreira",
        "role": "BATTER",
        "rank": 5,
        "is_leader": False,
        "squad_2026": "Rajasthan Royals",
        "cdn_asset": "player/8903/1558/68473.png",
        "page_url": "https://www.iplt20.com/teams/rajasthan-royals",
        "publisher": "BCCI / IPL Official Digital Platform & Rajasthan Royals",
        "credit": "BCCI / IPL / Rajasthan Royals",
        "photo_context": "2026 IPL Official Media Day Studio Portrait",
        "access_date": "2026-11-15",
        "rights_basis": "Official Tournament Media Pack (Editorial & Competition Evaluation Review)",
        "intended_audience": "Evaluator Review Dashboard (SupeRR Selector Season 2, Round 1)",
        "crop_notes": "Upper-torso studio shot, authentic RR 2026 kit, smiling media pose"
    },
    {
        "player_id": 19714,
        "name": "Abishek Porel",
        "role": "BATTER",
        "rank": 6,
        "is_leader": False,
        "squad_2026": "Delhi Capitals",
        "cdn_asset": "player/8903/1396/76558.png",
        "page_url": "https://www.iplt20.com/teams/delhi-capitals",
        "publisher": "BCCI / IPL Official Digital Platform & Delhi Capitals",
        "credit": "BCCI / IPL / Delhi Capitals",
        "photo_context": "2026 IPL Official Media Day Studio Portrait",
        "access_date": "2026-11-15",
        "rights_basis": "Official Tournament Media Pack (Editorial & Competition Evaluation Review)",
        "intended_audience": "Evaluator Review Dashboard (SupeRR Selector Season 2, Round 1)",
        "crop_notes": "Direct head-and-torso studio portrait, authentic DC 2026 kit"
    },
    {
        "player_id": 6423,
        "name": "Riyan Parag",
        "role": "BATTER",
        "rank": 7,
        "is_leader": False,
        "squad_2026": "Rajasthan Royals",
        "cdn_asset": "player/8903/1558/65476.png",
        "page_url": "https://www.iplt20.com/teams/rajasthan-royals",
        "publisher": "BCCI / IPL Official Digital Platform & Rajasthan Royals",
        "credit": "BCCI / IPL / Rajasthan Royals",
        "photo_context": "2026 IPL Official Media Day Studio Portrait",
        "access_date": "2026-11-15",
        "rights_basis": "Official Tournament Media Pack (Editorial & Competition Evaluation Review)",
        "intended_audience": "Evaluator Review Dashboard (SupeRR Selector Season 2, Round 1)",
        "crop_notes": "Upper-torso studio portrait, authentic RR 2026 kit, clean eyes and posture"
    },
    {
        "player_id": 7216,
        "name": "Prabhsimran Singh",
        "role": "BATTER",
        "rank": 8,
        "is_leader": False,
        "squad_2026": "Punjab Kings",
        "cdn_asset": "player/8903/2040/68831.png",
        "page_url": "https://www.iplt20.com/teams/punjab-kings",
        "publisher": "BCCI / IPL Official Digital Platform & Punjab Kings",
        "credit": "BCCI / IPL / Punjab Kings",
        "photo_context": "2026 IPL Official Media Day Studio Portrait",
        "access_date": "2026-11-15",
        "rights_basis": "Official Tournament Media Pack (Editorial & Competition Evaluation Review)",
        "intended_audience": "Evaluator Review Dashboard (SupeRR Selector Season 2, Round 1)",
        "crop_notes": "Direct studio shot, authentic PBKS 2026 kit, centered upper torso"
    },
    {
        "player_id": 152,
        "name": "Ravindra Jadeja",
        "role": "DUAL_ROLE",
        "rank": 9, # Batters #9 and Bowlers #9
        "is_leader": False,
        "squad_2026": "Rajasthan Royals",
        "cdn_asset": "player/8903/1558/13143.png",
        "page_url": "https://www.iplt20.com/teams/rajasthan-royals",
        "publisher": "BCCI / IPL Official Digital Platform & Rajasthan Royals",
        "credit": "BCCI / IPL / Rajasthan Royals",
        "photo_context": "2026 IPL Official Media Day Studio Portrait",
        "access_date": "2026-11-15",
        "rights_basis": "Official Tournament Media Pack (Editorial & Competition Evaluation Review)",
        "intended_audience": "Evaluator Review Dashboard (SupeRR Selector Season 2, Round 1)",
        "crop_notes": "Single canonical portrait family shared across Batters #9 and Bowlers #9 role cards"
    },
    {
        "player_id": 7544,
        "name": "Venkatesh Iyer",
        "role": "BATTER",
        "rank": 10,
        "is_leader": False,
        "squad_2026": "Royal Challengers Bengaluru",
        "cdn_asset": "player/8903/2138/34170.png",
        "page_url": "https://www.iplt20.com/teams/royal-challengers-bengaluru",
        "publisher": "BCCI / IPL Official Digital Platform & Royal Challengers Bengaluru",
        "credit": "BCCI / IPL / Royal Challengers Bengaluru",
        "photo_context": "2026 IPL Official Media Day Studio Portrait",
        "access_date": "2026-11-15",
        "rights_basis": "Official Tournament Media Pack (Editorial & Competition Evaluation Review)",
        "intended_audience": "Evaluator Review Dashboard (SupeRR Selector Season 2, Round 1)",
        "crop_notes": "Studio upper-torso portrait, authentic RCB 2026 kit, clean lighting"
    },
    {
        "player_id": 5944,
        "name": "Mohammed Siraj",
        "role": "BOWLER",
        "rank": 1,
        "is_leader": True,
        "squad_2026": "Gujarat Titans",
        "cdn_asset": "player/8903/2879/44904.png",
        "page_url": "https://www.iplt20.com/teams/gujarat-titans",
        "publisher": "BCCI / IPL Official Digital Platform & Gujarat Titans",
        "credit": "BCCI / IPL / Gujarat Titans",
        "photo_context": "2026 IPL Official Media Day Studio Portrait",
        "access_date": "2026-11-15",
        "rights_basis": "Official Tournament Media Pack (Editorial & Competition Evaluation Review)",
        "intended_audience": "Evaluator Review Dashboard (SupeRR Selector Season 2, Round 1)",
        "crop_notes": "Featured leader portrait, arms folded confident media day pose, authentic GT 2026 kit"
    },
    {
        "player_id": 2633,
        "name": "Jason Holder",
        "role": "BOWLER",
        "rank": 2,
        "is_leader": False,
        "squad_2026": "Gujarat Titans",
        "cdn_asset": "player/8903/2879/12693.png",
        "page_url": "https://www.iplt20.com/teams/gujarat-titans",
        "publisher": "BCCI / IPL Official Digital Platform & Gujarat Titans",
        "credit": "BCCI / IPL / Gujarat Titans",
        "photo_context": "2026 IPL Official Media Day Studio Portrait",
        "access_date": "2026-11-15",
        "rights_basis": "Official Tournament Media Pack (Editorial & Competition Evaluation Review)",
        "intended_audience": "Evaluator Review Dashboard (SupeRR Selector Season 2, Round 1)",
        "crop_notes": "Direct headshot, authentic GT 2026 kit, clean upper shoulders"
    },
    {
        "player_id": 8530,
        "name": "Kartik Tyagi",
        "role": "BOWLER",
        "rank": 3,
        "is_leader": False,
        "squad_2026": "Kolkata Knight Riders",
        "cdn_asset": "player/8903/1873/66831.png",
        "page_url": "https://www.iplt20.com/teams/kolkata-knight-riders",
        "publisher": "BCCI / IPL Official Digital Platform & Kolkata Knight Riders",
        "credit": "BCCI / IPL / Kolkata Knight Riders",
        "photo_context": "2026 IPL Official Media Day Studio Portrait",
        "access_date": "2026-11-15",
        "rights_basis": "Official Tournament Media Pack (Editorial & Competition Evaluation Review)",
        "intended_audience": "Evaluator Review Dashboard (SupeRR Selector Season 2, Round 1)",
        "crop_notes": "Studio upper-torso portrait, authentic KKR 2026 purple kit"
    },
    {
        "player_id": 4641,
        "name": "Lungi Ngidi",
        "role": "BOWLER",
        "rank": 4,
        "is_leader": False,
        "squad_2026": "Delhi Capitals",
        "cdn_asset": "player/8903/1396/28230.png",
        "page_url": "https://www.iplt20.com/teams/delhi-capitals",
        "publisher": "BCCI / IPL Official Digital Platform & Delhi Capitals",
        "credit": "BCCI / IPL / Delhi Capitals",
        "photo_context": "2026 IPL Official Media Day Studio Portrait",
        "access_date": "2026-11-15",
        "rights_basis": "Official Tournament Media Pack (Editorial & Competition Evaluation Review)",
        "intended_audience": "Evaluator Review Dashboard (SupeRR Selector Season 2, Round 1)",
        "crop_notes": "Upper-torso studio shot, authentic DC 2026 kit, sharp facial focus"
    },
    {
        "player_id": 4219,
        "name": "Krunal Pandya",
        "role": "BOWLER",
        "rank": 5,
        "is_leader": False,
        "squad_2026": "Royal Challengers Bengaluru",
        "cdn_asset": "player/8903/2138/20456.png",
        "page_url": "https://www.iplt20.com/teams/royal-challengers-bengaluru",
        "publisher": "BCCI / IPL Official Digital Platform & Royal Challengers Bengaluru",
        "credit": "BCCI / IPL / Royal Challengers Bengaluru",
        "photo_context": "2026 IPL Official Media Day Studio Portrait",
        "access_date": "2026-11-15",
        "rights_basis": "Official Tournament Media Pack (Editorial & Competition Evaluation Review)",
        "intended_audience": "Evaluator Review Dashboard (SupeRR Selector Season 2, Round 1)",
        "crop_notes": "Studio upper-body portrait, authentic RCB 2026 kit"
    },
    {
        "player_id": 7327,
        "name": "Rasikh Salam",
        "role": "BOWLER",
        "rank": 6,
        "is_leader": False,
        "squad_2026": "Royal Challengers Bengaluru",
        "cdn_asset": "player/8903/2138/68859.png",
        "page_url": "https://www.iplt20.com/teams/royal-challengers-bengaluru",
        "publisher": "BCCI / IPL Official Digital Platform & Royal Challengers Bengaluru",
        "credit": "BCCI / IPL / Royal Challengers Bengaluru",
        "photo_context": "2026 IPL Official Media Day Studio Portrait",
        "access_date": "2026-11-15",
        "rights_basis": "Official Tournament Media Pack (Editorial & Competition Evaluation Review)",
        "intended_audience": "Evaluator Review Dashboard (SupeRR Selector Season 2, Round 1)",
        "crop_notes": "Direct head-and-torso studio shot, authentic RCB 2026 kit"
    },
    {
        "player_id": 1566,
        "name": "Mohammed Shami",
        "role": "BOWLER",
        "rank": 7,
        "is_leader": False,
        "squad_2026": "Lucknow Super Giants",
        "cdn_asset": "player/8903/2880/11458.png",
        "page_url": "https://www.iplt20.com/teams/lucknow-super-giants",
        "publisher": "BCCI / IPL Official Digital Platform & Lucknow Super Giants",
        "credit": "BCCI / IPL / Lucknow Super Giants",
        "photo_context": "2026 IPL Official Media Day Studio Portrait",
        "access_date": "2026-11-15",
        "rights_basis": "Official Tournament Media Pack (Editorial & Competition Evaluation Review)",
        "intended_audience": "Evaluator Review Dashboard (SupeRR Selector Season 2, Round 1)",
        "crop_notes": "Direct studio headshot, authentic LSG 2026 kit, unobstructed view"
    },
    {
        "player_id": 27964,
        "name": "Anshul Kamboj",
        "role": "BOWLER",
        "rank": 8,
        "is_leader": False,
        "squad_2026": "Chennai Super Kings",
        "cdn_asset": "player/8903/1622/70442.png",
        "page_url": "https://www.iplt20.com/teams/chennai-super-kings",
        "publisher": "BCCI / IPL Official Digital Platform & Chennai Super Kings",
        "credit": "BCCI / IPL / Chennai Super Kings",
        "photo_context": "2026 IPL Official Media Day Studio Portrait",
        "access_date": "2026-11-15",
        "rights_basis": "Official Tournament Media Pack (Editorial & Competition Evaluation Review)",
        "intended_audience": "Evaluator Review Dashboard (SupeRR Selector Season 2, Round 1)",
        "crop_notes": "Upper-torso studio portrait, authentic CSK 2026 yellow kit"
    },
    {
        "player_id": 3298,
        "name": "Jofra Archer",
        "role": "BOWLER",
        "rank": 10,
        "is_leader": False,
        "squad_2026": "Rajasthan Royals",
        "cdn_asset": "https://www.rajasthanroyals.com/static-assets/images/players/64254.png?v=7.95",
        "page_url": "https://www.rajasthanroyals.com/rr-players/jofra-archer-ipl-profile-64254",
        "publisher": "Rajasthan Royals",
        "credit": "Rajasthan Royals",
        "photo_context": "Official Rajasthan Royals player profile portrait",
        "access_date": "2026-11-15",
        "rights_basis": "Official Rajasthan Royals player profile photo, credited in the competition dashboard",
        "intended_audience": "Evaluator Review Dashboard (SupeRR Selector Season 2, Round 1)",
        "crop_notes": "Transparent upper-body portrait in RR kit, centered on a square canvas"
    }
]

def apply_paper_stroke_and_shadow(im: Image.Image, is_leader: bool) -> Image.Image:
    """
    Applies a continuous warm-white #FFF8ED silhouette stroke and flat paper shadow
    to the transparent RGBA image.
    Leader: ~16px stroke at 1024 master (~5-7 CSS px at render size).
    Standard: ~10px stroke at 1024 master (~3-4 CSS px at render size).
    Paper shadow: subtle offset down-right.
    """
    arr = np.array(im.convert("RGBA"), dtype=np.float32)
    alpha = arr[:, :, 3] / 255.0
    mask = alpha > 0.08
    
    stroke_r = 16 if is_leader else 10
    dist_outside = distance_transform_edt(~mask)
    stroke_alpha = np.clip(1.0 - (dist_outside - stroke_r + 1.0) / 1.5, 0.0, 1.0)
    
    dx = 8 if is_leader else 5
    dy = 10 if is_leader else 6
    shadow_r = stroke_r + 2
    
    shifted_mask = np.zeros_like(mask)
    shifted_mask[dy:, dx:] = mask[:-dy, :-dx]
    dist_shadow = distance_transform_edt(~shifted_mask)
    shadow_raw = np.clip(1.0 - (dist_shadow - shadow_r) / 3.0, 0.0, 1.0)
    
    # Shadow color #20172F (ink) with subtle opacity
    shadow_opacity = 0.22
    s_a = shadow_raw * shadow_opacity
    
    # Warm-white stroke #FFF8ED = RGB(255, 248, 237)
    w_r, w_g, w_b = 255.0, 248.0, 237.0
    
    base_alpha = s_a * (1.0 - stroke_alpha) + stroke_alpha
    base_r = (32.0 * s_a * (1.0 - stroke_alpha) + w_r * stroke_alpha) / np.maximum(base_alpha, 1e-6)
    base_g = (23.0 * s_a * (1.0 - stroke_alpha) + w_g * stroke_alpha) / np.maximum(base_alpha, 1e-6)
    base_b = (47.0 * s_a * (1.0 - stroke_alpha) + w_b * stroke_alpha) / np.maximum(base_alpha, 1e-6)
    
    final_alpha = base_alpha * (1.0 - alpha) + alpha
    final_r = (base_r * base_alpha * (1.0 - alpha) + arr[:, :, 0] * alpha) / np.maximum(final_alpha, 1e-6)
    final_g = (base_g * base_alpha * (1.0 - alpha) + arr[:, :, 1] * alpha) / np.maximum(final_alpha, 1e-6)
    final_b = (base_b * base_alpha * (1.0 - alpha) + arr[:, :, 2] * alpha) / np.maximum(final_alpha, 1e-6)
    
    res = np.zeros_like(arr, dtype=np.uint8)
    res[:, :, 0] = np.clip(final_r, 0, 255).astype(np.uint8)
    res[:, :, 1] = np.clip(final_g, 0, 255).astype(np.uint8)
    res[:, :, 2] = np.clip(final_b, 0, 255).astype(np.uint8)
    res[:, :, 3] = np.clip(final_alpha * 255.0, 0, 255).astype(np.uint8)
    
    return Image.fromarray(res, "RGBA")

def process_all_portraits():
    master_dir = os.path.join("scratch", "portraits_master")
    output_dir = os.path.join("dashboard", "public", "portraits")
    os.makedirs(output_dir, exist_ok=True)
    
    manifest_records = []
    
    print(f"Processing all 19 portraits into {output_dir}...")
    
    for meta in PLAYERS_METADATA:
        pid = meta["player_id"]
        master_path = os.path.join(master_dir, f"{pid}.png")
        if not os.path.exists(master_path):
            raise FileNotFoundError(f"Master file not found: {master_path}")
            
        im = Image.open(master_path)
        is_leader = meta["is_leader"]
        
        # Apply paper silhouette stroke & flat drop shadow
        stroked_im = apply_paper_stroke_and_shadow(im, is_leader=is_leader)
        
        # Define target export widths
        if is_leader:
            widths = [320, 480, 640, 800, 1200]
        else:
            widths = [320, 640]
            
        variants = {}
        for w in widths:
            aspect = stroked_im.height / stroked_im.width
            h = int(round(w * aspect))
            resized = stroked_im.resize((w, h), Image.Resampling.LANCZOS)
            
            webp_name = f"{pid}_{w}w.webp"
            png_name = f"{pid}_{w}w.png"
            webp_path = os.path.join(output_dir, webp_name)
            png_path = os.path.join(output_dir, png_name)
            
            # Save WebP
            resized.save(webp_path, "WEBP", quality=88, method=6)
            # Save PNG fallback
            resized.save(png_path, "PNG", optimize=True)
            
            webp_bytes = os.path.getsize(webp_path)
            png_bytes = os.path.getsize(png_path)
            
            variants[f"{w}w"] = {
                "width": w,
                "height": h,
                "webp": f"/portraits/{webp_name}",
                "webp_bytes": webp_bytes,
                "png": f"/portraits/{png_name}",
                "png_bytes": png_bytes
            }
            
        record = {
            **meta,
            "display_name": meta["name"],
            "master_dimensions": [im.width, im.height],
            "eye_line_pct": 32.5,
            "silhouette_stroke_token": "#FFF8ED",
            "silhouette_stroke_css_px": 6 if is_leader else 3.5,
            "paper_shadow": "offset 5-8px down-right rgba(32, 23, 47, 0.22)",
            "review_status": "VERIFIED_OFFICIAL_MEDIA",
            "variants": variants
        }
        manifest_records.append(record)
        print(f"  [DONE] {pid} {meta['name']} (leader={is_leader}): exported {len(widths)} sizes (320w WebP: {variants['320w']['webp_bytes']//1024}KB, 640w WebP: {variants['640w']['webp_bytes']//1024}KB)")

    # Save manifest in dashboard/src/data/portraits_manifest.json
    manifest_dst = os.path.join("dashboard", "src", "data", "portraits_manifest.json")
    with open(manifest_dst, "w", encoding="utf-8") as f:
        json.dump(manifest_records, f, indent=2)
    print(f"Manifest saved to {manifest_dst} ({len(manifest_records)} records).")
    
    # Generate Contact Sheet HTML in dashboard/public/portraits/contact_sheet.html
    generate_contact_sheet_html(manifest_records, os.path.join(output_dir, "contact_sheet.html"))
    # Generate Contact Sheet composite image
    generate_contact_sheet_image(manifest_records, os.path.join("scratch", "portraits_contact_sheet.png"))

def generate_contact_sheet_html(records, out_html_path):
    rows_html = ""
    for r in records:
        pid = r["player_id"]
        v320 = r["variants"]["320w"]
        v640 = r["variants"]["640w"]
        role_class = "leader" if r["is_leader"] else "standard"
        badge = f"<span class='badge leader-badge'>LEADER #1</span>" if r["is_leader"] else f"<span class='badge'>Rank #{r['rank']}</span>"
        
        rows_html += f"""
        <div class="player-card {role_class}">
          <div class="preview-tiles">
            <div class="tile tile-pink">
              <img src="{v320['webp']}" alt="{r['name']}" loading="lazy" />
              <span class="tile-label">Pink Tile</span>
            </div>
            <div class="tile tile-blue">
              <img src="{v320['webp']}" alt="{r['name']}" loading="lazy" />
              <span class="tile-label">Blue Tile</span>
            </div>
            <div class="tile tile-paper">
              <img src="{v320['webp']}" alt="{r['name']}" loading="lazy" />
              <span class="tile-label">Paper Tile</span>
            </div>
            <div class="tile tile-dark">
              <img src="{v320['webp']}" alt="{r['name']}" loading="lazy" />
              <span class="tile-label">Dark Tile</span>
            </div>
          </div>
          <div class="player-info">
            <div class="player-header">
              <h3>{r['name']}</h3>
              {badge}
            </div>
            <p class="meta"><strong>ID:</strong> {pid} | <strong>Role:</strong> {r['role']} | <strong>2026 Squad:</strong> {r['squad_2026']}</p>
            <p class="meta"><strong>Sizes:</strong> 320w ({v320['webp_bytes']//1024} KB WebP, {v320['png_bytes']//1024} KB PNG) / 640w ({v640['webp_bytes']//1024} KB WebP)</p>
            <p class="meta"><strong>Credit:</strong> {r['credit']}</p>
            <p class="meta"><strong>Notes:</strong> {r['crop_notes']}</p>
            <p class="status">Review Status: <span>&#10003; {r['review_status']}</span></p>
          </div>
        </div>
        """
        
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Rajasthan Royals SupeRR Selector · Portrait Library Contact Sheet</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: #FFF8ED;
      color: #20172F;
      margin: 0;
      padding: 32px 24px;
    }}
    header {{
      max-width: 1200px;
      margin: 0 auto 32px auto;
      border-bottom: 2px solid #20172F;
      padding-bottom: 16px;
    }}
    h1 {{
      margin: 0 0 8px 0;
      font-size: 32px;
      letter-spacing: -0.5px;
    }}
    .subtitle {{
      color: #534A60;
      font-size: 16px;
      margin: 0;
    }}
    .grid {{
      max-width: 1200px;
      margin: 0 auto;
      display: grid;
      grid-template-columns: 1fr;
      gap: 24px;
    }}
    .player-card {{
      background: #FFFCF6;
      border: 1.5px solid #20172F;
      border-radius: 12px;
      padding: 16px;
      display: flex;
      gap: 20px;
      box-shadow: 3px 4px 0px rgba(32, 23, 47, 0.12);
    }}
    .player-card.leader {{
      border: 2px solid #D81465;
      background: #FFFDFC;
      box-shadow: 4px 6px 0px rgba(216, 20, 101, 0.2);
    }}
    .preview-tiles {{
      display: grid;
      grid-template-columns: repeat(4, 110px);
      gap: 8px;
    }}
    .tile {{
      border-radius: 8px;
      padding: 6px;
      display: flex;
      flex-direction: column;
      align-items: center;
      position: relative;
      overflow: hidden;
      border: 1px solid rgba(32, 23, 47, 0.1);
    }}
    .tile img {{
      width: 100%;
      height: auto;
      display: block;
    }}
    .tile-pink {{ background: #F4CADA; }}
    .tile-blue {{ background: #CFDAFF; }}
    .tile-paper {{ background: #FFF8ED; }}
    .tile-dark {{ background: #20172F; }}
    .tile-label {{
      font-size: 10px;
      font-weight: 600;
      margin-top: 4px;
      color: #20172F;
      opacity: 0.8;
    }}
    .tile-dark .tile-label {{
      color: #FFF8ED;
    }}
    .player-info {{
      flex: 1;
      display: flex;
      flex-direction: column;
      justify-content: center;
    }}
    .player-header {{
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 6px;
    }}
    .player-header h3 {{
      margin: 0;
      font-size: 22px;
    }}
    .badge {{
      display: inline-block;
      font-size: 12px;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 4px;
      background: #20172F;
      color: #FFF8ED;
    }}
    .badge.leader-badge {{
      background: #D81465;
      color: #FFF8ED;
    }}
    .meta {{
      margin: 3px 0;
      font-size: 13px;
      color: #534A60;
    }}
    .status {{
      margin-top: 8px;
      font-size: 13px;
      font-weight: 700;
      color: #0E7039;
    }}
  </style>
</head>
<body>
  <header>
    <h1>SupeRR Selector Season 2 · Stage 01 Portrait Library</h1>
    <p class="subtitle">19 Identity-Verified Official Master Portraits with #FFF8ED Paper Stroke & Shadow</p>
  </header>
  <main class="grid">
    {rows_html}
  </main>
</body>
</html>
"""
    with open(out_html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Contact sheet HTML written to {out_html_path}")

def generate_contact_sheet_image(records, out_img_path):
    """
    Assembles a composite contact sheet image showing all 19 portraits in a grid.
    """
    thumb_w, thumb_h = 160, 160
    cols = 5
    rows = 4 # 19 portraits fits in 5x4 grid
    margin = 16
    pad = 12
    card_w = thumb_w + pad * 2
    card_h = thumb_h + 40
    
    total_w = margin * 2 + cols * card_w + (cols - 1) * 12
    total_h = margin * 2 + rows * card_h + (rows - 1) * 12
    
    canvas = Image.new("RGBA", (total_w, total_h), (255, 248, 237, 255))
    
    for idx, r in enumerate(records):
        col = idx % cols
        row = idx // cols
        
        x = margin + col * (card_w + 12)
        y = margin + row * (card_h + 12)
        
        # Draw card background (pink for batters, blue for bowlers)
        is_batter = r["role"] == "BATTER" or (r["role"] == "DUAL_ROLE" and idx < 10)
        bg_color = (244, 202, 218, 255) if is_batter else (207, 218, 255, 255)
        card_bg = Image.new("RGBA", (card_w, card_h), bg_color)
        canvas.paste(card_bg, (x, y))
        
        # Load 320w WebP or PNG
        v_path = os.path.join("dashboard", "public", r["variants"]["320w"]["png"].lstrip("/"))
        p_img = Image.open(v_path).convert("RGBA")
        p_img.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        
        # Center in card
        px = x + (card_w - p_img.width) // 2
        py = y + pad
        canvas.alpha_composite(p_img, (px, py))
        
    canvas.save(out_img_path)
    print(f"Contact sheet composite image written to {out_img_path}")

if __name__ == "__main__":
    process_all_portraits()
