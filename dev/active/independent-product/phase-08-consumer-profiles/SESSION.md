# Phase 8 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-08-23

**Local branch:** `phase8/06-profile-sidecars` from `main`

**Predecessor:** Item 8.5 merged as PR #86 at
`0797308ad440e7eec4d0a075099b7e2513ee9754` after all 16 GitHub checks
passed. Local `main` equals `origin/main`.

**Completed:** 8.1 PR #82, 8.2 PR #83, 8.3 PR #84, 8.4 PR #85, 8.5 PR #86

**Current item:** 8.6 Ship config sidecars

**Not started:** 8.7 discovery truthfulness and Phase 8 closeout. Do not
start Phase 9, 10, or 13.

**8.6 design:** Emit profile-specific launch JSON beside each export
(`metadata/trl-sft-launch.json`, `metadata/mlx-lm-lora-launch.json`).
Dataset paths and documented flags only. `launches_training` is false.
No model selection, no hyperparameters, no subprocess. Taxonomy remains
planned.
