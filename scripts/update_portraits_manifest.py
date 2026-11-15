"""Refresh Archer's verified portrait with `python -m scripts.update_portraits_manifest`."""

import json
from pathlib import Path

from PIL import Image

from dashboard.scripts.process_portraits import PLAYERS_METADATA, apply_paper_stroke_and_shadow


def main():
    root = Path(__file__).resolve().parents[1]
    player_id = 3298
    meta = next(player for player in PLAYERS_METADATA if player["player_id"] == player_id)

    with Image.open(root / "scratch/raw_downloads/3298.png") as source:
        portrait = source.convert("RGBA")
    if portrait.getchannel("A").getextrema() != (0, 255):
        raise ValueError("Use the transparent portrait from Archer's official Rajasthan Royals profile")

    master_size = 1024
    top_margin = 40
    height = master_size - top_margin
    width = round(portrait.width * height / portrait.height)
    portrait = portrait.resize((width, height), Image.Resampling.LANCZOS)
    master = Image.new("RGBA", (master_size, master_size))
    master.alpha_composite(portrait, ((master_size - width) // 2, top_margin))
    master.save(root / "scratch/portraits_master/3298.png", optimize=True)

    stroked = apply_paper_stroke_and_shadow(master, is_leader=False)
    output_dir = root / "dashboard/public/portraits"
    variants = {}
    for size in (320, 640):
        variant = stroked.resize((size, size), Image.Resampling.LANCZOS)
        filename = f"{player_id}_{size}w"
        png = output_dir / f"{filename}.png"
        webp = output_dir / f"{filename}.webp"
        variant.save(png, optimize=True)
        variant.save(webp, quality=88, method=6)
        variants[f"{size}w"] = {
            "width": size,
            "height": size,
            "webp": f"/portraits/{webp.name}",
            "webp_bytes": webp.stat().st_size,
            "png": f"/portraits/{png.name}",
            "png_bytes": png.stat().st_size,
        }

    manifest_path = root / "dashboard/src/data/portraits_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = next(player for player in manifest if player["player_id"] == player_id)
    entry.update(meta, master_dimensions=list(master.size), variants=variants)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
