# Phase 8 crash-recovery notes

Overwrite this file as the current item changes. `progress.md` remains
append-only history.

**Updated:** 2026-08-23

**Local branch:** `phase8/02-admission-pins`

**Predecessor:** Item 8.1 merged as PR #82 at
`799d56f` (`Merge pull request #82 from ogprotege/phase8/01-profile-packet`).
Clean `main` at that SHA equals `origin/main`.

**Current item:** 8.2 Pin TRL and MLX-LM admission records

**Not started:** 8.3 TRL emit, 8.4 MLX-LM emit, 8.5 harness, 8.6 sidecars,
8.7 discovery truthfulness and closeout. Do not start Phase 9, 10, or 13.

**8.2 remaining:** PR titled `Phase 8.2: Pin TRL and MLX-LM admission records`,
wait for all 14 GitHub checks, merge, `git checkout main && git pull --ff-only`.
Local gates passed: 1970 pytest, tracking, Ruff, lock, JSON, diff.

**Standing rules:** Core never imports trainer libraries. Generic exports stay
`consumer_profile: null`. `trl` / `mlx-lm` stay planned and non-executable
until 8.3 / 8.4. Empty extras only; real packages arrive in 8.5.
