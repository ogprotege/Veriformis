# Phase 1 — Standalone Independence

**Status:** Completed

**Started:** 2026-08-11

**Roadmap phase:** [Phase 1](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md#phase-1--enforce-standalone-independence)

## Purpose

Make canonical Veriformis operation independent by default. Ordinary CLI,
MCP, and workbench sealing must produce only the verified Veriformis bundle;
core install, compile, verification, parity, and release gates must not load,
create, or require the Aptus adapter. The implemented Aptus handoff remains an
explicit optional integration.

## Packet contents

| File | Role |
| --- | --- |
| [plan.md](plan.md) | Ordered implementation and closeout gates |
| [progress.md](progress.md) | Append-only dated execution log |
| [decisions.md](decisions.md) | Phase decisions and protected compatibility boundaries |
| [risks.md](risks.md) | Active risks and controls |
| [evidence.md](evidence.md) | Acceptance evidence and limitations |
| [closeout.md](closeout.md) | Exit-gate judgment |

## Outcome

CLI, MCP, and workbench sealing are standalone by default, and their normal
startup/seal paths do not import the optional adapter. Required test, golden,
clean-wheel, parity, and workbench gates are canonical-bundle-only. Explicit
Aptus adapter construction and self-conformance remain separately invocable.
See [closeout.md](closeout.md) for the measured exit-gate judgment.
