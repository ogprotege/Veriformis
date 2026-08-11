# Aptus Handoff Contract v1

**Contract ID:** `veriformis.aptus-handoff`

**Contract version:** `1`

**Schema version:** `veriformis.aptus-handoff/v1`

**Roadmap scope:** Step 23

**Implementation status:** Implemented

**Last reviewed:** 2026-08-11 (optional-integration boundary clarified)

## Purpose

This contract defines an optional sibling descriptor that lets Aptus consume a
sealed Veriformis finished bundle without rewriting partitions or inventing
split policy. Veriformis installation, compilation, sealing, independent bundle
verification, and workbench operation do not require Aptus or this descriptor.

The closed `minimal-v1` six-file bundle is unchanged. The handoff is written
beside the bundle as:

```text
name.vfbundle
name.vfbundle.aptus-handoff.json
```

The descriptor is an integration artifact, not a seventh bundle file, a
canonical downstream requirement, or evidence that every trainer accepts the
bundle. Core verification remains governed by the Finished Dataset Contract.

## Required verification

A consumer MUST:

1. verify the bundle at `external_digest` using `manifest_sha256`;
2. re-hash `data/train.jsonl`, `data/evaluation.jsonl`,
   `metadata/row-provenance.jsonl`, and `validation.json` against the handoff;
3. validate every product row against the declared `row_schema`;
4. recompute the portable assignment projection digest from sealed provenance
   and match `assignment_digest`;
5. honor `backend_capabilities` (current MLX rejects plain `text` rows).

## Portable assignment digest

```text
schema_version: veriformis.aptus-assignment-projection/v1
assignments: ordered by record_id of
  {record_id, partition, assignment_id, leakage_group_id}
```

This projection is sealed-provenance-only so consumers do not need workspace
state to recompute the digest.

## Masking expectations

| row_schema | supervised boundary |
| --- | --- |
| `text` | full-sequence |
| `prompt_completion` | completion-only |
| `instruction_output` | output-only |
| `messages` | final-assistant-suffix |

## Backend capability defaults (v1)

- accepts: `prompt_completion`, `instruction_output`, `messages`
- rejects: `text`
- requires external digest: true
- enforces assignment digest: true
