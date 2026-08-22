# Veriformis Deterministic Archive Transport v1

**Status:** Implemented companion contract

**Last reviewed:** 2026-08-22 (Phase 5.4 export-pack profile)

This single contract defines two profile-scoped deterministic ZIP wrappers:

- `deterministic-vfbundle-zip-v1` for a Finished Dataset Contract v1
  `minimal-v1` bundle; and
- `deterministic-export-pack-zip-v1` for one already-published, receipt-bound
  generic export directory.

Neither profile defines a new dataset, semantic export renderer, row schema,
partition, consumer profile, or trainer export. Their content anchors differ,
but both use the same deterministic ZIP codec and no-replace publication
implementation.

## `deterministic-vfbundle-zip-v1`

## Preconditions

Packaging MUST receive a separately retained expected manifest SHA-256. Before
writing output it MUST verify the source canonical bundle with that digest and
obtain `external_digest` grade. An unexpected source member, including
`.DS_Store`, MUST fail; a packager MUST NOT clean or normalize the source.

## Canonical archive

The target name ends in `.vfbundle.zip`. The ZIP has no archive comment and
contains exactly these regular-file members in bytewise sorted order:

```text
attestation.json
data/evaluation.jsonl
data/train.jsonl
manifest.json
metadata/row-provenance.jsonl
validation.json
```

Every member uses ZIP stored encoding, the DOS epoch `1980-01-01 00:00:00`,
Unix regular-file mode `0444`, no member comment, and no uncontrolled extra
metadata. ZIP64-capable headers are used so the encoding rule does not change
at the ordinary 32-bit size boundary. Identical source bytes MUST produce
identical archive bytes.

## Verification

The verifier MUST reject a non-regular archive path, comments, encryption,
compression, noncanonical metadata, duplicates, directories, missing or extra
members, unsafe names, declared-size disagreement, CRC/read failure,
noncanonical ZIP bytes, and every failure raised by the canonical bundle
verifier. It reconstructs only the six fixed destinations in a private
temporary directory; it never extracts caller-provided names directly.

Success requires the reconstructed bundle to verify at `external_digest` with
the caller-supplied manifest SHA-256. The result reports both that manifest
digest and the SHA-256 of the complete archive bytes.

## Publication

Publication MUST stage and verify the complete archive before making the target
visible and MUST refuse an existing target. Disk and permission failures MUST
not leave a partial target. The destination parent remains an
integrity-controlled namespace under the same local-filesystem assumptions as
canonical bundle publication.

## `deterministic-export-pack-zip-v1`

This profile is the Phase 5.4 application of the same archive envelope. It is
an optional post-export transport. It is not a fourth export selector, an
export request option, or an alternate interpretation of the directory-valued
`destination_root` used by the Verified Export Contract v1.

### External receipt anchor

Packaging and verification MUST receive a separately retained SHA-256 of the
canonical `export-receipt.json` bytes. The implementation MUST validate that
digest before source or destination access where the value can be rejected
syntactically. It MUST NOT derive external authority from the receipt carried
inside the directory or archive.

The canonical receipt embeds the complete `ExportPlan` and binds every planned
destination file. Matching its external digest therefore binds the plan ID,
receipt ID, source facts, logical membership projection, complete declared
path set, file roles, sizes, and digests. Packaging MUST preserve the embedded
source trust grade and MUST NOT describe a `self_consistent` source as
`external_digest` merely because the export receipt or archive is externally
anchored.

The profile initially admits only `portable_exact_bytes` export plans. A
`semantic_content_only` plan MUST fail until its exact implementation-bound
semantic replayer is available to the archive verifier.

### Canonical export-pack archive

The target name ends in `.vfexport.zip`. The archive has no wrapper directory
and contains exactly these regular files in exact bytewise-sorted path order:

1. canonical `export-receipt.json`; and
2. every path bound by the receipt's complete `files` sequence.

There are no directory entries or additional metadata members. Receipt paths
remain subject to the Verified Export v1 portable-path, depth, collision, and
closed-tree rules. Absolute paths, traversal, dot components, backslashes,
reserved names, controls, Unicode/case aliases, duplicates, links, and special
files fail closed.

Every member uses the same deterministic envelope as the bundle profile: ZIP
stored encoding, DOS epoch `1980-01-01 00:00:00`, Unix regular-file mode
`0444`, empty member and archive comments, no uncontrolled extra metadata, and
ZIP64-capable headers. Exact non-ASCII paths use the one canonical UTF-8 ZIP
encoding emitted by the shared codec. Complete archive-byte equality with a
fresh canonical rerender is required, so alternate flag, header, metadata, or
trailing-byte spellings fail even when a permissive ZIP reader could decode
them.

Identical closed export bytes MUST produce identical archive bytes regardless
of source directory name, filesystem mode, modification time, enumeration
order, or archive destination.

### Export-pack verification

The verifier MUST reject a non-regular archive, a non-ZIP or truncated value,
archive or member comments, encryption, compression, noncanonical metadata,
duplicates, directories, missing or unexpected members, unsafe or colliding
paths, wrapper directories, size disagreement, CRC/read failure, receipt
digest mismatch, receipt/file disagreement, and noncanonical complete archive
bytes.

Verification reads and strictly loads the bounded canonical receipt before it
derives the expected member set. It reconstructs only those validated member
paths in a private directory and invokes the existing expected-plan export
directory verifier. It MUST NOT call a general extraction operation over
caller-supplied names. Stored-only encoding prevents decompression-ratio
amplification; member bytes are streamed rather than retained as one complete
archive-sized value.

The verifier opens the archive once through a no-follow regular-file
descriptor and retains that descriptor through ZIP reading, canonical-byte
comparison, digesting, and sizing. It then requires the caller-visible path to
still name that same inode. Path replacement or observed file-status change
during verification fails closed rather than mixing facts from two archives.

Success returns runtime transport evidence containing the archive path,
SHA-256, byte size, external receipt SHA-256, embedded export plan and
receipt IDs, output content root, source trust grade, member count, and any
post-visibility durability warning. These are not a new persisted export
schema. The archive SHA-256 identifies the wrapper bytes; it is not a source
trust anchor, signature, or authenticity claim.

### Export-pack publication and command selection

The packager first descriptor-inspects the closed source directory under the
external receipt digest. The archive target MUST be outside that source tree.
It then writes, syncs, reopens, reconstructs, verifies, and canonically
rerenders a sibling staging file before one no-replace publication. An existing
target of any kind is never replaced. Failure before visibility leaves no
target; cleanup or parent-sync failure after visibility is an advisory
durability warning and MUST NOT turn successful publication into failure.

The existing `package` and `package-verify` command family selects exactly one
transport profile by its explicit anchor:

- `--manifest-sha256` selects `deterministic-vfbundle-zip-v1`; or
- `--export-receipt-sha256` selects
  `deterministic-export-pack-zip-v1`.

Both or neither MUST fail before reading a source or touching a destination.
No filename-suffix inference may silently switch profiles. Existing bundle
command arguments, six-member bytes, manifest anchoring, and verification
behavior remain unchanged.
