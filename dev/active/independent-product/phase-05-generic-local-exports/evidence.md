# Phase 5 Evidence

**Status:** In progress — item 5.1 local evidence complete

**Opened:** 2026-08-21

## Predecessor evidence

Phase 4 completed at `a76e0fe3185b0e317cd453b9c28a1d2054e617dd`.
Its [closeout](../phase-04-verified-export-foundation/closeout.md) records the
verified export foundation and its adversarial exit proof. Phase 5 reuses that
foundation; it does not restate Phase 4 evidence as proof of a shipped generic
container.

## Source-verified starting facts

| Fact | Grade | Source |
| --- | --- | --- |
| The roadmap authorizes split JSONL as the first Phase 5 implementation candidate for all current row schemas | `source-verified` | Independent product roadmap, Phase 5 |
| Generic derivatives must remain downstream of the canonical verified bundle | `source-verified` | ADR-0004 and Verified Export Contract v1 |
| Safe publication, receipt replay, membership equality, and independent verification are available from Phase 4 | `source-verified` | Phase 4 packet and verified-export sources |
| At baseline `a76e0fe`, production discovery contains no renderer/replayer and generic containers remain planned | `source-verified` | Phase 4 closeout, support registry, and implementation catalog at the opening baseline |
| The existing deterministic archive transport is the only archive contract Phase 5 may integrate | `source-verified` | ADR-0005 and roadmap work item 5.4 |

## Required item 5.1 evidence

- [x] Strict configuration/profile parsing and durable identity fixtures.
- [x] Exact semantic row and logical-partition preservation for every current
      row schema.
- [x] Safe configurable filename, collision, traversal, Unicode/case-alias,
      and reserved-name refusal.
- [x] Optional provenance alignment, omission, mutation, and tamper proof.
- [x] Deterministic README/data-card and closed destination-tree proof.
- [x] Receipt, unexpected-file, source-digest, membership, and output-tamper
      failure evidence.
- [x] Discovery, dry-run, inspect, execute, and verify parity across Python,
      CLI, MCP, and the CLI-backed Mac bridge.
- [x] Import round-trip or equivalent semantic replay proving identical rows
      and partitions.
- [x] Required focused, full, release, tracking, lint, parity, Mac, and diff
      gates recorded with exact observed results.
- [x] Capability/support, current-status, evidence-index, and packet records
      reconciled after the behavior is proved.

## Required phase exit evidence

- [ ] Every supported row schema round-trips through every compatible generic
      container with identical semantic rows and logical partitions.
- [ ] Tampering fails verification for every supported container.
- [ ] Nested CSV is refused before publication with an actionable alternative.
- [ ] Generic export-pack archives reuse the existing deterministic transport
      and verifier.
- [ ] Dry-run sample rows and destination trees match execution.
- [ ] Operator guidance separates container choice, training objective, and
      consumer compatibility.

## Observed results

The opening record above remains historical. The following results were
observed locally on the Phase 5.1 working tree based on
`a76e0fe3185b0e317cd453b9c28a1d2054e617dd`; raw runner logs were not retained.

| Evidence | Result | Grade | Limitation |
| --- | --- | --- | --- |
| Dedicated split JSONL contract | 45 passed | `recorded-local` | Container-specific fixtures, not the later Phase 5.5 consolidated matrix |
| Export/taxonomy/verified-contract integration | 288 passed at the focused gate | `recorded-local` | Later full run is the complete repository count |
| Full Python | 1,039 passed; one expected durability-warning regression warning | `recorded-local` | Local Python 3.12; CI supplies the matrix |
| Standalone release | 1,027 passed, 1 deselected; clean wheel and both golden compile/transport flows passed | `recorded-local` | Optional Aptus integration remains separate |
| macOS XCTest | 56 passed | `recorded-local` | Local unsigned Debug test build |
| CLI/workbench parity | PASS | `recorded-local` | Temporary artifacts were not retained |
| Governance and structure | Tracking, lock, Ruff, 15 JSON, 10 shell, 387 changed-document local links, and diff checks passed | `recorded-local` | Counts describe this working tree |

The evidence proves the admitted JSONL container, exact membership and
round-trip preservation, deterministic bytes, safe configuration, and shared
surface behavior. It does not claim JSON, CSV, export-pack archives, shared
Phase 5.5 fixtures, dry-run sample previews, trainer compatibility, scale, or
Phase 5 completion.
