# Veriformis Deterministic Bundle Transport v1

**Status:** Implemented companion contract

**Last reviewed:** 2026-08-11

This contract defines a transport wrapper for a Finished Dataset Contract v1
`minimal-v1` bundle. It does not define a new dataset, bundle profile, row
schema, partition, or trainer export.

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
