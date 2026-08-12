# Phase 1 Closeout

**Status:** Completed

**Last reviewed:** 2026-08-11

## Exit-gate judgment

Passed. A temporary environment containing an installed Veriformis wheel and
no external Aptus distribution compiled both golden objectives, default-sealed
canonical bundles with no sibling descriptors, and verified them at
`external_digest` through the installed CLI. CLI and MCP default startup/seal
paths are regression-locked against adapter import and artifact creation.

Required tests do not collect the adapter-only module and exclude the optional
marker. The optional selection and explicit descriptor script pass separately.
Canonical workbench parity, 14 Swift tests, and a fresh app build/launch with an
explicit Veriformis 0.1.0 CLI passed.

## Preserved limitations

- `aptus-row-shape` remains the persisted generic gate ID. Renaming requires a
  versioned report/identity migration and is tracked as DOC-007.
- Adapter checks are self-conformance evidence, not proof against a live named
  Aptus release.
- The app launch is local functional evidence, not Developer ID signing,
  notarization, or clean-Mac distribution evidence.
- The first clean-wheel attempt was sandbox-blocked at uv's managed Python
  directory; the approved unrestricted rerun passed.

## Final evidence

See [evidence.md](evidence.md) and the
[evidence index](../../../../docs/evidence/index.json). Phase 2 remains planned
until a new standard packet is created.
