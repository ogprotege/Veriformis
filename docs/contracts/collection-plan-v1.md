# Collection Plan Contract v1

**Contract ID:** `veriformis.collection-plan`

**Contract version:** `1`

**Schema:** `veriformis.collection-plan/v1`

**Status:** Implemented through independent-product Phase 11.

**Last reviewed:** 2026-08-25

## Purpose

Name the exact files a parse will capture from a mixed list of files and
directories, before any parser runs. Collection is membership. Capture still
pins regular files. Parsing still dispatches on suffix.

## Closed vocabularies

| Field | v1 values |
| --- | --- |
| Member status | `accepted`, `degraded`, `refused`, `duplicate`, `ignored` |
| Unsupported policy | `ignore`, `refuse` |
| Follow symlinks | `false` only |

Default limits: `max_files` 10000, `max_bytes` 512 MiB, `max_visited` 50000.

Default include: declared v1 suffixes for document-source; dataset-row
suffixes for `--mode dataset-row`; the union for mixed mode.

## Plan identity

`plan_id` is the canonical digest of schema, source root, settings, accepted
suffixes, sorted members, and counts. Extra fields fail closed.

## Member reasons

| Reason | Status |
| --- | --- |
| `hidden` | ignored |
| `unsupported-suffix` | ignored, or collection refusal when policy is `refuse` |
| `excluded-by-glob` | ignored |
| `package-directory` | ignored (not recursed) |
| `directory-not-recursed` | ignored |
| `symlink` | refused |
| `not-a-regular-file` | refused |
| `duplicate-bytes:<logical>` | duplicate |

## Non-goals

MIME sniffing. Archive expansion. Following links. Truncation at limits. OCR.
New suffixes without an admission record.

## Surfaces

`PipelineService.collect`, CLI `veriformis collect`, MCP `collect`, and
automatic expansion inside `parse` and compile `preflight`. The Mac workbench
passes files and directories through; it does not walk them.
