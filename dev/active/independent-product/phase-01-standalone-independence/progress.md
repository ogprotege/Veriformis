# Phase 1 Progress Log

This file is append-only by dated entry. Corrections are recorded in later
entries rather than deleting the earlier account.

## 2026-08-11 — Phase 1 started

**Status:** In progress

**Predecessor:** Phase 0 completed with synchronized program state and passing
closeout gates.

**Evidence reviewed:** `PipelineService.seal` and YAML execution are neutral.
CLI and MCP seal defaults are true; MCP imports the adapter at module load;
workbench default and legacy fallback are true; workbench opt-in currently
relies on the CLI's old default; golden and parity gates require the sibling
handoff; active docs record that historical coupling.

**Acceptance policy:** Tests and release scripts must distinguish required core
evidence from optional integration evidence. A passing descriptor
self-conformance test is not described as compatibility with a named Aptus
binary.

**Next action:** Add failing/default-boundary regressions, then change the
interface defaults and release evidence without altering the trainer-neutral
compiler service.

## 2026-08-11 — Standalone implementation integrated

**Status:** In progress

CLI and MCP seal defaults are false and import the adapter only on explicit
use. The workbench default and missing-field history fallback are false; an
explicit stored true remains true and emits `--aptus-handoff`. Optional UI and
result/history output are grouped under Integrations.

Required CI and local pytest commands now ignore the adapter-only test module
before collection and exclude the optional marker. Golden, install-smoke, and
parity paths use only canonical bundle facts and assert sibling absence. The
explicit Aptus script/job is non-blocking and described as adapter
self-conformance, not live-version compatibility.

## 2026-08-11 — Integrated acceptance observed

**Status:** Closeout pending final drift checks

Observed passes: lock and project tracking; Ruff; 12 focused tests; 662 core
tests with one marked MCP test deselected and the adapter-only directory not
collected; four optional-integration tests; standalone golden for `full_text`
and `continuation`; optional descriptor self-conformance; canonical workbench
parity; isolated-wheel install and both installed-CLI golden objectives; 14
Swift tests; and fresh workbench build/launch using the explicit Veriformis
0.1.0 CLI.

The first sandboxed clean-wheel run could not write uv's managed Python
temporary directory. The approved unrestricted rerun passed; this was an
execution-environment restriction, not a product failure. Final link, tracking,
documentation-drift, and diff checks remain before the completion transition.

## 2026-08-11 — Phase 1 completed

**Status:** Completed

Final tracking, Ruff, CI-boundary parse, stale-claim scan, 418-target active
local Markdown link check, and `git diff --check` passed. The program ledger,
WIP mirror, support/evidence registries, documentation debt/health records, and
closeout judgment were synchronized. Phase 2 remains planned and requires its
own standard packet before work begins.
