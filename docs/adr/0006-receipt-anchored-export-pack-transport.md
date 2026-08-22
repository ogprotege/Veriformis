# ADR-0006 — Receipt-Anchored Export-Pack Transport

**Status:** Accepted

**Date:** 2026-08-22

**Decider:** Repository owner direction

## Context and evidence

Phase 5.1–5.3 publish generic exports as closed directories. Each directory
contains canonical `export-receipt.json`; that receipt embeds the complete
`ExportPlan` and binds every other member by path, role, byte size, digest,
record count, and membership scope. The existing Phase 2 transport in ADR-0005
already supplies deterministic stored ZIP bytes, canonical metadata,
verification before visibility, and no-replace publication for `minimal-v1`.

The Phase 5 roadmap requires generic export packs to reuse that transport and
forbids a second bundle-transport contract. ADR-0005 nevertheless has a
deliberately narrower decision: `.vfbundle.zip`, six fixed members, and an
externally retained bundle-manifest digest. Reinterpreting that identifier or
its manifest anchor for generic exports would change an accepted decision.

## Decision

Veriformis adds `deterministic-export-pack-zip-v1` as an optional transport of
one already-published generic export directory.

- The target suffix is `.vfexport.zip`.
- The archive contains exactly canonical `export-receipt.json` and every path
  in that receipt's `files` sequence, sorted by exact relative path, with no
  wrapper or directory members.
- Packaging and verification require a separately retained SHA-256 of the
  canonical `export-receipt.json` bytes. A co-located receipt is never its own
  external anchor.
- The archive uses the same deterministic ZIP codec and publication machinery
  as ADR-0005: stored entries, fixed DOS epoch, regular-file mode `0444`, no
  comments or uncontrolled extras, ZIP64-capable encoding, complete canonical
  rerender comparison, staged verification, and no-replace publication.
- The archive verifier reconstructs only strict receipt-validated paths in a
  private directory and reuses the existing export-directory verifier. It
  never calls general ZIP extraction on caller-controlled names.
- The external receipt digest anchors the embedded receipt, its complete plan,
  and its complete declared file set. The separately reported archive digest
  identifies transport bytes only.
- Packaging preserves the source trust grade recorded in the embedded plan. It
  does not upgrade `self_consistent` evidence to `external_digest`.

The archive is a post-export transport, not a fourth renderer, request option,
consumer profile, trainer format, or alternate `destination_root`. Export
discovery remains `split-jsonl-directory`, `json`, and `constrained-csv` v1.
All ten persisted verified-export v1 models and their identities remain
unchanged. The outer archive digest and durability warning are runtime facts;
placing them inside the archived receipt would create a self-reference.

The existing `package` and `package-verify` command family selects its profile
by exactly one explicit external anchor. `--manifest-sha256` retains the
ADR-0005 bundle behavior; `--export-receipt-sha256` selects this export-pack
profile. Supplying both or neither fails before source or destination access.

## Consequences and limitations

An operator can move one immutable byte-identifiable file while retaining the
same inner plan, receipt, rows, order, partitions, and content-root identity as
the directory export. The ordinary directory remains the directly usable
generic export and is not deleted or rewritten by packaging.

The external receipt digest proves that archive contents match the retained
export receipt. It is not a signature, notarization, source-authenticity claim,
or replacement for source-bound `export verify`. Source-bound verification
still requires the original verified source and rederived expected plan.
V1 supports the currently shipped `portable_exact_bytes` export profiles. A
future semantic-only profile requires its exact profile-bound semantic
replayer before transport admission.

Stored encoding prevents decompression amplification; verification streams
members and bounds retained receipt bytes. Archive size still duplicates the
export on disk, and disk exhaustion remains a normal reported I/O failure.
Signing, encryption, compression, remote publication, force overwrite, and a
Mac-specific package UI remain outside this decision.

## Alternatives considered

- **Add archive fields to `ExportPlan` or `ExportReceipt` v1:** Rejected. Those
  schemas are exact-fielded, and an in-archive digest would be circular.
- **Treat a ZIP path as export `destination_root`:** Rejected. The published
  export contract is a closed directory and its strict surfaces say so.
- **Add a fourth archive renderer:** Rejected. Transport does not change row or
  container semantics and must not multiply export selectors.
- **Reuse `deterministic-vfbundle-zip-v1`:** Rejected. That identifier means the
  fixed six-file, manifest-anchored bundle wrapper.
- **Create another archive contract or codec:** Rejected. Both profiles share
  the single deterministic archive envelope and publication implementation.

## Verification and review triggers

Admission requires legacy `.vfbundle.zip` byte compatibility; deterministic
export archives across all three current generic containers; strict receipt,
member, metadata, path, CRC, canonical-byte, tamper, anchor, no-replace, and
failure-cleanup tests; and unchanged export plan/receipt identities.

Review this decision if a semantic-only export is admitted, compression or
encryption is proposed, archive resource limits change, ZIP64 behavior changes,
the receipt boundary changes, remote authenticity is introduced, or generic
packaging becomes part of the export request protocol.
