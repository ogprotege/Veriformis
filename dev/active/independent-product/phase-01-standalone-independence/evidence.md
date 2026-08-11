# Phase 1 Evidence

**Evidence status:** Complete recorded-local and test-verified closeout

**Predecessor:** [Phase 0 closeout](../phase-00-foundation/closeout.md)

## Source-verified starting facts

| Fact | Evidence | Limitation |
| --- | --- | --- |
| Compiler service seal is trainer-neutral | `src/veriformis/pipeline/service.py` | Does not prove adapter defaults |
| CLI seal default is currently handoff-on | `src/veriformis/cli.py` | Must change in Phase 1 |
| MCP seal default and module import are handoff-coupled | `src/veriformis/mcp/server.py` | Explicit tools remain supported |
| Workbench default and legacy fallback are true | `macos/Sources/ViewModels/WorkbenchViewModel.swift` | Existing explicit true history must remain true |
| Workbench opt-in depends on the old CLI default | `macos/Sources/Services/VeriformisCLI.swift` | Must invert to an explicit positive flag |
| Core golden/parity scripts read the handoff | `scripts/release/golden_compile.sh`, `macos/scripts/parity_check.sh` | Must become canonical-bundle-only |
| Package declares no Aptus runtime dependency | `pyproject.toml` | Installed-wheel proof remains required |
| `aptus-row-shape` is a persisted validation gate ID | `src/veriformis/contracts.py`, `src/veriformis/datasets/validation.py` | Name is legacy debt, not an adapter import |

## Required final evidence

- Core and optional integration test selections.
- Default artifact-absence and import-isolation regressions.
- Clean installed-wheel full compile/seal/external-digest verification.
- Trainer-neutral golden and parity logs.
- Swift tests, macOS build, and launch/bootstrap proof.
- Explicit Aptus opt-in descriptor self-conformance proof.
- Tracking, documentation, local links, and diff checks.

Exact results and evidence grades are appended only after observation.

## Observed integrated results — 2026-08-11

| Gate | Result | Grade / limitation |
| --- | --- | --- |
| Lock, tracker, Ruff, shell syntax | Pass | Recorded local; tracker also checks all three false defaults and import isolation |
| Focused runtime/release/MCP/adapter tests | 12 passed | Test-verified |
| Required core Python selection | 662 passed, 1 deselected; `tests/handoff` not collected | Test-verified; current machine/Python environment only |
| Optional integration selection | 4 passed, 662 deselected | Adapter self-conformance only; no live Aptus build |
| Standalone golden | `full_text` and `continuation` passed default seal, sibling absence, and `external_digest` verify | Recorded local; temporary bundles removed by script |
| Optional integration script | Explicit continuation descriptor accepted at `external_digest` | Recorded local; adapter self-conformance only |
| Clean wheel | Isolated Python 3.12 wheel origin under temporary `site-packages`; installed package inventory contained no external `aptus`; both installed-CLI golden objectives passed | Recorded local; first sandbox attempt was permission-denied, approved rerun passed |
| Workbench parity | Canonical manifest, bundle/content roots, snapshot/report IDs, and full file bindings matched; sibling absent | Recorded local |
| Swift target | 14 tests passed | Recorded local Xcode run; local signing only |
| Workbench launch | Checked-in project built; new PID confirmed with explicit `.venv/bin/veriformis` 0.1.0; process cleaned up | Recorded local; not Developer ID signing, notarization, or clean-Mac evidence |
| Final governance/docs | Tracker, Ruff, CI YAML boundary assertion, stale-claim scan, 418 local Markdown targets, shell syntax, and diff check passed | Recorded local; no external-link crawler or Mermaid renderer |

The validation transcript still displays `aptus-row-shape`. Source and
contract review establish that this is the persisted generic row-shape gate
ID, not an adapter import or release dependency. It remains open migration
debt rather than being renamed incompatibly in Phase 1.
