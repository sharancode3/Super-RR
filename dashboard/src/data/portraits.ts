import type { PortraitManifestRecord, PortraitVariant } from "./types";
import rawManifest from "./portraits_manifest.json";

export const portraitsManifest: PortraitManifestRecord[] = rawManifest as unknown as PortraitManifestRecord[];

export const portraitsById: Record<number, PortraitManifestRecord> = {};
for (const p of portraitsManifest) {
  portraitsById[p.player_id] = p;
}

/**
 * Returns the best matching WebP portrait source URL for a player.
 * Defaults to 320w for standard tiles, or 640w/800w for leaders.
 */
export function getPortraitSrc(
  playerId: number,
  preferredWidth: 320 | 480 | 640 | 800 | 1200 = 320
): string {
  const p = portraitsById[playerId];
  if (!p) {
    return "/portraits/placeholder.png";
  }
  const key = `${preferredWidth}w`;
  if (p.variants[key]) {
    return p.variants[key].webp;
  }
  // Fallback to highest or standard width
  if (p.variants["640w"]) return p.variants["640w"].webp;
  if (p.variants["320w"]) return p.variants["320w"].webp;
  return Object.values(p.variants)[0]?.webp || "";
}

/**
 * Returns a responsive srcset string of WebP variants for the given player ID.
 */
export function getPortraitSrcSet(playerId: number): string {
  const p = portraitsById[playerId];
  if (!p) return "";
  return Object.entries(p.variants)
    .map(([_, v]: [string, PortraitVariant]) => `${v.webp} ${v.width}w`)
    .join(", ");
}

/**
 * Returns a responsive fallback srcset string of PNG variants.
 */
export function getPortraitPngSrcSet(playerId: number): string {
  const p = portraitsById[playerId];
  if (!p) return "";
  return Object.entries(p.variants)
    .map(([_, v]: [string, PortraitVariant]) => `${v.png} ${v.width}w`)
    .join(", ");
}

/**
 * Returns the photo credit citation for the given player.
 */
export function getPortraitCredit(playerId: number): string {
  return portraitsById[playerId]?.credit || "BCCI / IPL";
}
