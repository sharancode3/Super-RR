/**
 * Shared IntersectionObserver hook for Stage 05 motion system.
 * Handles card entry reveals, deep-link jumps, keyboard focus, and prefers-reduced-motion.
 */

import { useEffect } from "react";

export function useRevealObserver() {
  useEffect(() => {
    // Check if user prefers reduced motion
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");

    const revealAll = () => {
      document.querySelectorAll("[data-reveal]").forEach((el) => {
        el.setAttribute("data-reveal", "revealed");
      });
    };

    if (mediaQuery.matches || typeof IntersectionObserver === "undefined") {
      revealAll();
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.setAttribute("data-reveal", "revealed");
            observer.unobserve(entry.target);
          }
        });
      },
      {
        threshold: 0.16,
        rootMargin: "0px 0px -40px 0px",
      }
    );

    const elements = document.querySelectorAll("[data-reveal]");
    elements.forEach((el) => {
      // Immediate reveal on keyboard focus
      el.addEventListener(
        "focusin",
        () => {
          el.setAttribute("data-reveal", "revealed");
          observer.unobserve(el);
        },
        { once: true }
      );

      observer.observe(el);
    });

    // Handle deep-link anchor entry immediately
    if (window.location.hash) {
      try {
        const target = document.querySelector(window.location.hash);
        if (target) {
          const card =
            target.getAttribute("data-reveal") !== null
              ? target
              : target.querySelector("[data-reveal]");
          if (card) {
            card.setAttribute("data-reveal", "revealed");
            observer.unobserve(card);
          }
        }
      } catch {
        // invalid selector safety
      }
    }

    // Dynamic OS reduced-motion change listener
    const handleMotionChange = (e: MediaQueryListEvent) => {
      if (e.matches) {
        revealAll();
        observer.disconnect();
      }
    };
    mediaQuery.addEventListener("change", handleMotionChange);

    return () => {
      observer.disconnect();
      mediaQuery.removeEventListener("change", handleMotionChange);
    };
  }, []);
}
