import React, { useEffect } from "react";
import { YouTubeIcon, ExternalLinkIcon } from "./Icons";

interface VideoModalProps {
  videoId?: string;
  onClose: () => void;
}

export const VideoModal: React.FC<VideoModalProps> = ({
  videoId = "FmjD06lF-wo",
  onClose,
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = prevOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose]);

  return (
    <div
      className="video-modal-backdrop"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="video-modal-title"
    >
      <div
        className="video-modal-container"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="video-modal-header">
          <div className="video-modal-header-left">
            <span className="video-modal-badge">
              <YouTubeIcon size={18} className="video-modal-yt-icon" />
              <span>Share Your Journey</span>
            </span>
            <h2 id="video-modal-title" className="video-modal-title">
              Rajasthan Royals · SupeRR Selector Walkthrough
            </h2>
          </div>
          <button
            type="button"
            className="video-modal-close-btn"
            onClick={onClose}
            aria-label="Close video player"
            title="Close video (Esc)"
          >
            ×
          </button>
        </div>

        <div className="video-modal-player-wrap">
          <iframe
            src={`https://www.youtube-nocookie.com/embed/${videoId}?autoplay=1&rel=0&modestbranding=1`}
            title="Rajasthan Royals SupeRR Selector Walkthrough by Sharan"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            allowFullScreen
            className="video-modal-iframe"
          />
        </div>

        <div className="video-modal-footer">
          <div className="video-modal-summary">
            60-second analytics walkthrough by Sharan S explaining pre-ball pressure leverage, forward-chaining backtesting, and the Jofra Archer selection audit.
          </div>
          <a
            href={`https://youtu.be/${videoId}`}
            target="_blank"
            rel="noopener noreferrer"
            className="video-modal-yt-link"
            title="Open video on YouTube in a new tab"
          >
            <span>Watch on YouTube</span>
            <ExternalLinkIcon size={14} />
          </a>
        </div>
      </div>
    </div>
  );
};
