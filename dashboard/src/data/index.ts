import evidenceData from "./evidence.json";
import type { EvidenceBundle } from "./types";

export const evidence: EvidenceBundle = evidenceData as unknown as EvidenceBundle;
export * from "./portraits";
export type * from "./types";
