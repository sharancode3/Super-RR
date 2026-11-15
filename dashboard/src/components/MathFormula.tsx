import React, { useMemo } from "react";
import katex from "katex";

interface MathFormulaProps {
  math: string;
  displayMode?: boolean;
  className?: string;
  ariaLabel?: string;
}

export const MathFormula: React.FC<MathFormulaProps> = ({
  math,
  displayMode = false,
  className = "",
  ariaLabel,
}) => {
  const html = useMemo(() => {
    try {
      return katex.renderToString(math, {
        displayMode,
        throwOnError: false,
        strict: false,
      });
    } catch (e) {
      console.error("KaTeX rendering error:", e);
      return `<code class="math-fallback">${math}</code>`;
    }
  }, [math, displayMode]);

  return displayMode ? (
    <div
      className={`katex-math-display ${className}`}
      aria-label={ariaLabel || math}
      role="math"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  ) : (
    <span
      className={`katex-math-inline ${className}`}
      aria-label={ariaLabel || math}
      role="math"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
};
