# Phase 8 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-08-23

**Local branch:** `phase8/03-trl-profile`

**Predecessor:** Item 8.2 merged as PR #83 at
`7351904e58c67c925a3a878af350335620306260`. Local `main` equals `origin/main`
there.

**Completed:** 8.1 (PR #82), 8.2 (PR #83)

**Current item:** 8.3 Emit the TRL profile (implementation on branch; gates
next)

**Not started:** 8.4 MLX-LM emit, 8.5 harness, 8.6 sidecars, 8.7 closeout.
Do not start Phase 9, 10, or 13.

**Standing rules:** Core never imports trainer libraries. Generic exports stay
`consumer_profile: null`. `mlx-lm` stays planned until 8.4. The exporter does
not train.
