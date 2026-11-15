/**
 * Strict TypeScript types for the SupeRR Selector Season 2 evidence bundle.
 */

export type RoleType = "batting" | "bowling";

export type RouteCategory = "RR_SQUAD_DECISION" | "AUCTION_CONDITIONAL";

export interface SourceCitation {
  rel_path: string;
  evaluator_title: string;
  date: string;
  approved_use: string;
  sha256: string;
  size_bytes: number;
}

export interface PlayerIdentity {
  player_id: number;
  canonical_name: string;
  display_name: string;
  known_aliases: string[];
  roles_appeared: RoleType[];
  is_dual_role: boolean;
  portrait_key: string;
  verified_spelling_notes: string;
}

export interface RankingMetrics {
  unit: string;
  observed_pressure_runs_per_12: number;
  observed_ordinary_runs_per_12: number;
  signed_uplift_runs_per_12: number;
  predicted_composite_impact: number;
  model_ranking_priority: number;
  hp_balls: number;
  ordinary_balls: number;
  pressure_fixtures_count: number;
  loo_omission_min: number | null;
  loo_omission_max: number | null;
  loo_available: boolean;
}

export interface PlayerStability {
  selection_frequency: number;
  resamples_total: number;
  frequency_display: string;
}

export interface RankingItemCitations {
  canonical_rank_source: string;
  evidence_context_source: string;
  stability_source: string;
  unstop_label_source: string;
}

export interface RankingRecord {
  role: RoleType;
  rank: number;
  player_id: number;
  player_name: string;
  verified_unstop_label: string;
  deployment: string;
  route: string;
  route_category: RouteCategory;
  rr_fit_and_risk: string;
  metrics: RankingMetrics;
  stability: PlayerStability;
  citations: RankingItemCitations;
}

export interface ModellingWindowsBreakdown {
  forward_2024_2025: number;
  retrospective_2026: number;
  auction_replays: number;
  windows_list: string[];
}

export interface WholeListConcordance {
  batting: string;
  bowling: string;
  interpretation: string;
}

export interface VerifiedQuantities {
  rebuild_sources_count: number;
  rebuild_sources: string[];
  recipes_count: number;
  recipes: string[];
  roles_count: number;
  roles: RoleType[];
  windows_per_role_per_source: number;
  windows_breakdown: ModellingWindowsBreakdown;
  comparison_rows_total: number;
  fixture_resamples_draws: number;
  whole_list_concordance_draws: WholeListConcordance;
  eligible_player_pools: {
    batting: number;
    bowling: number;
  };
  median_stability: {
    batting: number;
    bowling: number;
  };
}

export interface DataFunnel {
  raw_deliveries: number;
  cohort_eligible_deliveries: number;
  ranking_eligible_deliveries: number;
  total_fixtures: number;
  excluded_fixtures: number;
  eligible_fixtures: number;
  ranking_eligible_fixtures: number;
  chronological_folds: Record<string, any>;
}

export interface ProjectStory {
  calendar_span: string;
  earliest_verifiable_record: string;
  final_audit_signoff: string;
  verification_milestone: {
    full_suite_tests: number;
    targeted_post_repair_tests: number;
    test_note: string;
  };
  training_duration_status: string;
  independent_fit_count_status: string;
}

export interface ModellingOverview {
  title: string;
  as_of_date: string;
  evaluation_origin: string;
  verified_quantities: VerifiedQuantities;
  data_funnel: DataFunnel;
  project_story: ProjectStory;
}

export interface EvidenceBundle {
  metadata: {
    schema_version: string;
    generated_at: string;
    generator: string;
    evaluator_cutoff: string;
    recommendation_scope: string;
  };
  sources: Record<string, SourceCitation>;
  modelling_overview: ModellingOverview;
  identities: Record<string, PlayerIdentity>;
  rankings: RankingRecord[];
}

export interface PortraitVariant {
  width: number;
  height: number;
  webp: string;
  webp_bytes: number;
  png: string;
  png_bytes: number;
}

export interface PortraitManifestRecord {
  player_id: number;
  name: string;
  display_name: string;
  role: string;
  rank: number;
  is_leader: boolean;
  squad_2026: string;
  cdn_asset: string;
  page_url: string;
  alt_page_url?: string;
  publisher: string;
  credit: string;
  photo_context: string;
  access_date: string;
  rights_basis: string;
  intended_audience: string;
  crop_notes: string;
  master_dimensions: [number, number] | number[];
  eye_line_pct: number;
  silhouette_stroke_token: string;
  silhouette_stroke_css_px: number;
  paper_shadow: string;
  review_status: string;
  variants: Record<string, PortraitVariant>;
}
