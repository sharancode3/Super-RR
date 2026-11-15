/**
 * Data formatters, translations, and anchor generators for SupeRR Selector Season 2
 * Following Stage 03 evidence contract and acceptance specifications.
 */

import type { RoleType } from "./types";

/**
 * Generate stable DOM anchor ID for players
 * e.g. "batting-vaibhav-sooryavanshi" or "bowling-mohammed-siraj"
 */
export function getAnchorId(role: RoleType, name: string): string {
  const slug = name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  return `${role}-${slug}`;
}

/**
 * Translate internal tactical phase tokens into plain, readable cricket terms
 * Stage 03 requirement:
 * - POWERPLAY (batting) -> "Powerplay batting"
 * - MIDDLE (batting) -> "Middle-order batting"
 * - FINISHER (batting) -> "Finisher"
 * - POWERPLAY (bowling) -> "New-ball bowling" (with Kamboj special death context)
 * - MIDDLE (bowling) -> "Middle-overs pace"
 * - DEATH (bowling) -> "Death bowling"
 * - SPIN (bowling) -> "Spin"
 */
export function getDeploymentLabel(
  role: RoleType,
  deployment: string,
  playerId: number
): { primary: string; secondaryBadge?: string } {
  if (role === "batting") {
    switch (deployment.toUpperCase()) {
      case "POWERPLAY":
        return { primary: "Powerplay batting" };
      case "MIDDLE":
        return { primary: "Middle-order batting" };
      case "FINISHER":
        return { primary: "Finisher" };
      default:
        return { primary: deployment };
    }
  } else {
    // bowling
    switch (deployment.toUpperCase()) {
      case "POWERPLAY":
        if (playerId === 27964) {
          // Anshul Kamboj
          return {
            primary: "New-ball bowling",
            secondaryBadge: "Recorded death-over evidence (42 balls)",
          };
        }
        return { primary: "New-ball bowling" };
      case "MIDDLE":
        return { primary: "Middle-overs pace" };
      case "DEATH":
        return { primary: "Death bowling" };
      case "SPIN":
        return { primary: "Spin" };
      default:
        return { primary: deployment };
    }
  }
}

/**
 * Route labels and detailed explanations
 * Distinguishes "RR squad decision" vs "Conditional auction target"
 */
export function getRouteInfo(routeCategory: string): {
  label: string;
  pillClass: string;
  description: string;
  longExplanation: string;
} {
  if (routeCategory === "RR_SQUAD_DECISION") {
    return {
      label: "RR squad decision",
      pillClass: "route-squad",
      description: "RR roster asset or franchise option for IPL 2027",
      longExplanation:
        "Retained Rajasthan Royals squad member or internal franchise decision for the IPL 2027 cycle.",
    };
  }
  return {
    label: "Conditional auction target",
    pillClass: "route-auction",
    description: "External target; pursue if released to auction",
    longExplanation:
      "External player from another franchise; conditional target to pursue if entered into the IPL 2027 auction pool.",
  };
}

/**
 * Format signed run equivalents with explicit + or - sign
 */
export function formatSignedRun(val: number, decimals: number = 2): string {
  if (val > 0) return `+${val.toFixed(decimals)}`;
  if (val < 0) return val.toFixed(decimals); // already has -
  return `0.${"0".repeat(decimals)}`;
}

/**
 * Format leave-one-out (LOO) omission sensitivity interval
 */
export function formatLOORange(
  min: number | null,
  max: number | null,
  decimals: number = 2
): {
  display: string;
  isAvailable: boolean;
  tooltip: string;
} {
  if (min !== null && max !== null) {
    return {
      display: `[${formatSignedRun(min, decimals)} to ${formatSignedRun(max, decimals)}]`,
      isAvailable: true,
      tooltip:
        "Leave-one-out sensitivity: observed pressure impact range when removing each pressure fixture one by one.",
    };
  }
  return {
    display: "n/a (1 match)",
    isAvailable: false,
    tooltip:
      "Single pressure fixture recorded; leave-one-out omission bounds omitted per evaluation protocol.",
  };
}

/**
 * Format selection stability percentage
 */
export function formatStability(freq: number): {
  percentage: string;
  ratio: string;
  explanation: string;
} {
  const pct = (freq * 100).toFixed(1);
  const count = Math.round(freq * 1000);
  return {
    percentage: `${pct}%`,
    ratio: `${count}/1,000 draws`,
    explanation:
      "Inclusion across 1,000 whole-match cluster bootstrap resamples using the audited model and candidate pools.",
  };
}

/**
 * Cross-role linking helper for Ravindra Jadeja (Player ID 152)
 */
export function getCrossDisciplineLink(
  role: RoleType,
  playerId: number
): {
  targetAnchor: string;
  linkText: string;
  badgeText: string;
} | null {
  if (playerId !== 152) return null;

  if (role === "batting") {
    return {
      targetAnchor: "#bowling-ravindra-jadeja",
      linkText: "Dual-discipline candidate: also ranked #10 in Bowlers (Spin) →",
      badgeText: "Also Bowler #10",
    };
  } else {
    return {
      targetAnchor: "#batting-ravindra-jadeja",
      linkText: "Dual-discipline candidate: also ranked #9 in Batters (Finisher) →",
      badgeText: "Also Batter #9",
    };
  }
}
