import React, { useState } from "react";

// Known player portraits available in /portraits/
const KNOWN_PORTRAITS = new Set<number>([
  47, 152, 360, 781, 818, 830, 1566, 2320, 2633, 2933,
  3298, 3628, 3644, 3647, 4219, 4260, 4641, 4722, 4736, 5039,
  5944, 6256, 6288, 6423, 7216, 7327, 7544, 7897, 8182, 8238,
  8530, 8654, 19714, 27964, 50284,
]);

/**
 * Generate lightweight inline SVG avatar for non-shortlisted candidates
 * Uses Rajasthan Royals brand palette (Royal Navy + Warm Paper)
 */
function getSvgAvatarUri(name: string): string {
  const initials = name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><rect width="64" height="64" rx="32" fill="#20172F"/><text x="50%" y="54%" dominant-baseline="middle" text-anchor="middle" fill="#FFF8ED" font-family="system-ui, -apple-system, sans-serif" font-weight="700" font-size="22">${initials}</text></svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

interface PlayerThumbnailProps {
  playerId: string | number;
  name: string;
  size?: number;
  className?: string;
}

export const PlayerThumbnail: React.FC<PlayerThumbnailProps> = ({
  playerId,
  name,
  size = 42,
  className = "",
}) => {
  const [imgError, setImgError] = useState(false);
  const [usePng, setUsePng] = useState(false);

  const numericId = Number(playerId);
  const hasKnownPortrait = KNOWN_PORTRAITS.has(numericId);

  // If player does not have a processed headshot or image failed to load, use branded SVG avatar
  const isUsingFallback = !hasKnownPortrait || imgError;

  const src = isUsingFallback
    ? getSvgAvatarUri(name)
    : usePng
    ? `/portraits/${numericId}_320w.png`
    : `/portraits/${numericId}_320w.webp`;

  return (
    <div
      className={`raw-player-thumb-frame ${className}`}
      style={{
        width: `${size}px`,
        height: `${size}px`,
        minWidth: `${size}px`,
        minHeight: `${size}px`,
      }}
      aria-hidden="true"
    >
      <img
        src={src}
        alt=""
        className="raw-player-thumb-img"
        loading="eager"
        decoding="async"
        width={size}
        height={size}
        onError={() => {
          if (!isUsingFallback && !usePng) {
            setUsePng(true);
          } else {
            setImgError(true);
          }
        }}
      />
    </div>
  );
};
