# Stage 00 · Reconcile the current build and freeze the baseline

## Agent prompt

Start after the current implementation pass. Read [START](START.md), the current source and `dashboard/BUILD_CHECKPOINT.md` and `dashboard/RELEASE_REVIEW.md`. Check what the existing work has already solved. Preserve pending changes. Use the workspace's supported snapshot tools to record state and do focused changes.

1. Check which port is running the dev build or a production preview. Record the visible or served bundle version and compare live data with `dashboard/src/data/evidence.json`, the Vite configuration and build output. Check all three destinations or the existing equivalents. Record current portrait alignment, derived-data discrepancies and remaining emoji surfaces. Use the active build to confirm a fix. A working root URL can serve an older bundle.
2. Verify file versions and join keys from:
   - `artifacts_rr_retrain_audit_20261115/recommended_rankings.csv`, `player_evidence.csv`, `retraining_comparison.csv`, `retraining_audit.json` and `DATA_AND_TRAINING_AUDIT.md`.
   - `artifacts_rr_scenario_review_20261115/scenario_review_rankings_with_stability.csv`, `updated_stability.json`, `auction_recruitment_pool.csv`, `same_role_comparisons.csv`, the scenario outputs and `SCENARIO_REVIEW.md`.
   - The original and revised competition packs and `scratch/rr_rebuild_recorded_20261115` audit manifests, scorecard checks, thresholds, chronological split and verified delivery impact ledger. Compare only derived approved aggregates in the website.
3. Record the exact two ranked top tens, canonical IDs, model recipe, ledger hash, effective forecast cutoff and public audit date. Check the distinction between the 15 November 2026 audit date and the backend's as-of cutoff. Verify Jadeja's ID 152 has both role rows. Confirm 20 RR list entries across 19 people and current model evidence. For a later layout, if the working agent has already built a raw view, verify it against Stage 01 rather than assuming correctness from its title.
4. Open a short correction log from concrete prior findings. The final data uses the retained models, while the methodology text used Challenger D and Ablation B0 from older runs. The worked RCB–MI example labelled Match 25 and target 182. The official Match 54 target was 167. The displayed max-swing formula differs from the backend. Some model comparison metric rows mix windows. The checkpoint contains example numbers from older outputs and should be corrected or dated. The Josh Inglis example listed 98 ordinary balls while the final CSV has 118 ordinary balls and 24 pressure balls. Recheck each finding in the latest build before changing it. Remove any claim of counts or dates whose source is unclear from the live story.
5. Freeze reproductions of the current approved selection. Count actual evaluated windows, model recipes, named training events and evidence rows. Verify duration claims only when a measured duration exists. Historical source packs and outputs stay immutable. Do not use a rebuilt or edited checkpoint as proof that unverified claims were ever true.

### Loop and handoff

Repeat the source and preview checks after resolving disagreements. **Pass** with a reproducible base snapshot, a source-to-field map, a list of issues still present, and a record of useful existing agent changes to preserve. Open [Stage 01](01_model_rankings_to_rr.md).
