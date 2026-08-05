# Group 7 SwiftUI Dataset Workbench Plan

**Status:** Complete

**Roadmap scope:** Step 24

## Outcome

A local macOS SwiftUI workbench lets a user complete
raw-source → sealed-bundle (+ Aptus handoff) without the terminal, producing
the same canonical digests as the CLI.

## Fixed decisions

1. **Composition root remains Python.** The app is a thin adapter that invokes
   the installed `veriformis` CLI (or `uv run veriformis` in development).
2. **No second pipeline.** Stage policy stays in `PipelineService`; Swift never
   reimplements clean/construct/seal rules.
3. **Workbench flow** mirrors the stage graph: add sources → configure → run
   ordered stages → show logs → surface bundle path, manifest SHA-256, handoff.
4. **Parity proof:** the same stage command sequence used by the workbench must
   match a pure CLI run on identical inputs (assignment/content digests).
5. **Sandbox:** app uses user-selected folders; development may call repo-local
   `uv run veriformis`.

## Exit gate

A user can complete the raw-source-to-sealed-dataset workflow without the
terminal, and the application produces the same canonical result as the CLI.
