# Phase 8 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-08-23

**Local branch:** about to create `phase8/05-conformance-harness` from `main`

**Predecessor:** Item 8.4 merged as PR #85 at
`056a0754f162242b1eddc0fda447bdac51cf9f0c`. Local `main` equals `origin/main`.

**Completed:** 8.1 PR #82, 8.2 PR #83, 8.3 PR #84, 8.4 PR #85

**Current item:** 8.5 Isolated conformance harnesses

**Not started:** 8.6 sidecars, 8.7 closeout. Do not start Phase 9, 10, or 13.

**8.5 design:** Core tests exercise the official TRL/MLX-LM *schema path*
(column names, filenames, Dataset.from_list-compatible dicts) without
installing torch/mlx. Optional `profile_integration` tests skip unless the
extra is installed. Optional CI job is `continue-on-error` like Aptus.
Extras stay empty lists so `uv lock` does not pull trainer wheels into core.
