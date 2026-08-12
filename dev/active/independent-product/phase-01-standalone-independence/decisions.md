# Phase 1 Decision Index

**Status:** Active

| Decision | State | Basis |
| --- | --- | --- |
| Canonical seal emits only the six-file Veriformis bundle by default | Accepted | [ADR-0002](../../../../docs/adr/0002-standalone-product-boundary.md) |
| Aptus handoff remains an explicit optional sibling integration | Accepted | ADR-0002 and current adapter tests |
| Canonical bundle correctness is independent of every consumer profile | Accepted | [ADR-0004](../../../../docs/adr/0004-canonical-bundle-derived-exports.md) |
| Preserve the persisted `aptus-row-shape` gate ID in Phase 1 | Accepted | Renaming changes plan/report identities and requires a versioned migration |
| Core and optional integration tests/evidence are separately selectable | Accepted | Core release readiness cannot depend on an optional consumer profile |
| Compatibility wording requires a named profile/version and external evidence | Accepted | Project tracking claim discipline |

No new export format, consumer profile, or maturity claim is authorized by
this phase.
