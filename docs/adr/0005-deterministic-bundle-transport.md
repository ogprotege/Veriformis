# ADR 0005: Deterministic immutable bundle transport

**Status:** Accepted

**Date:** 2026-08-11

**Deciders:** Veriformis product owner and implementation agent

## Context and evidence

The canonical `minimal-v1` product is a strict six-file directory. Its verifier
correctly rejects `.DS_Store` and every other undeclared member. Retained local
evidence shows Finder inserted `.DS_Store` into a browsed `.vfbundle` directory;
weakening that check would erase the closed-set integrity boundary.

Two transport approaches were evaluated:

1. A registered macOS package directory. The current app has no
   `CFBundleDocumentTypes` or exported `.vfbundle` UTI in
   `macos/Resources/Info.plist`. Registration would improve Finder presentation
   only on macOS. The value would remain an ordinary mutable directory to the
   Python verifier and on Linux, so registration alone cannot provide an
   immutable, cross-platform byte boundary.
2. A deterministic ZIP containing the exact six canonical members. The Python
   standard library reads it on macOS and Linux. Fixed order, stored encoding,
   timestamp, permissions, and metadata produce identical bytes from identical
   canonical bundles. Tests reconstruct the directory and run the existing
   verifier with the externally retained manifest digest.

The test suite also demonstrates failure for unexpected or duplicate members,
traversal names, link metadata, changed payload bytes, changed ZIP encoding,
wrong external digests, `.DS_Store` in the source bundle, full-disk errors, and
permission errors.

## Decision

Veriformis uses `name.vfbundle.zip` as the Finder-safe transport for a canonical
`minimal-v1` bundle.

- The canonical dataset remains the strict directory; its contract and verifier
  are unchanged.
- `veriformis package` requires an externally retained manifest SHA-256 and
  refuses a source bundle that does not verify at `external_digest` grade.
- The archive contains the six bundle files at their canonical relative paths,
  with no wrapper directory and no additional metadata member.
- Publication is no-replace. The archive is re-opened, reconstructed, verified,
  and checked for canonical deterministic ZIP bytes before publication.
- `veriformis package-verify` requires the same external manifest digest. It
  never treats a co-located archive value as an external trust anchor.
- Finder-facing workbench actions reveal the immutable transport archive rather
  than inviting browsing inside the canonical directory.

The transport is not a trainer export, does not change rows or partitions, and
does not satisfy the later generic-export contract.

## Consequences and limitations

Users must retain the manifest SHA-256 separately; the archive SHA-256 is an
additional transport identity, not a replacement trust anchor. ZIP storage is
uncompressed in v1 so canonical bytes and streaming behavior remain simple and
fully specified. Packaging duplicates the six file bytes on disk. Signing,
notarization, encrypted archives, trainer formats, remote publication, and
archive-level authenticity are outside this decision.

## Alternatives considered

- **Ignore `.DS_Store`: rejected.** It would make a closed verifier silently
  accept undeclared content.
- **Registered package directory: rejected for the integrity boundary.** It is
  platform-specific presentation and remains mutable directory storage.
- **Compressed ZIP: deferred.** Compressor versions and settings add a
  reproducibility surface with no Phase 2 requirement.
- **Tar or disk image: rejected for v1.** Neither improves the required Python,
  macOS, and Linux workflow enough to justify another parser and attack surface.

## Verification and review triggers

Evidence lives in `tests/bundle/test_finished_bundle.py`, `tests/test_cli.py`,
`scripts/release/golden_compile.sh`, and the Phase 2 packet. Review this decision
if `minimal-v1` changes, a registered package becomes cross-platform contract
state, compression is proposed, archives exceed ZIP64 limits, or signing and
remote distribution introduce a different trust envelope.
