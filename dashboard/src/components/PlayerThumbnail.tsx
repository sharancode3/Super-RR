import React, { useState } from "react";

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

  // Compute initials for SVG fallback avatar
  const initials = name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");

  const src = usePng
    ? `/portraits/${playerId}_320w.png`
    : `/portraits/${playerId}_320w.webp`;

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
      {!imgError ? (
        <img
          src={src}
          alt=""
          className="raw-player-thumb-img"
          loading="eager"
          decoding="async"
          width={size}
          height={size}
          onError={() => {
            if (!usePng) {
              setUsePng(true);
            } else {
              setImgError(true);
            }
          }}
        />
      ) : (
        <div className="raw-player-thumb-fallback">
          <svg
            className="raw-player-fallback-svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
          {initials && <span className="raw-player-fallback-initials">{initials}</span>}
        </div>
      )}
    </div>
  );
};
