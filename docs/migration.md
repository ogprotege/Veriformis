# Veriformis Migration Guide

**Status:** Operator guide for supported persisted versions in development
alpha `0.1.0`

**Last reviewed:** 2026-09-09 (post-20 defect closure: parser and chunker producer versions)

This page names every supported workspace, bundle, mapping, recipe, export,
and profile version and how it loads or upgrades. Unknown versions fail closed.
Do not hand-edit content-addressed objects or `HEAD`.

Version remains `0.1.0` until Phase 20.10. This guide is not a 1.0 version
claim.

## Workspace

Physical layout schema is **1**. Opening any other layout fails closed.

Revision schemas:

| Revision | Path | What `upgrade-workspace` does |
| --- | --- | --- |
| 1 | Document-source history before construct | Adds `construct` as absent (v2), then finished-dataset stages as absent (v3) |
| 2 | Group 2 construct workspaces | Preserves parse, clean, chunk, and construct; adds `curate` and `split` as absent; resets legacy `format`, `validate`, and `seal` because those artifacts are not finished-dataset evidence |
| 3 | Current document-source workspace | No-op. This is the finished-dataset graph through `seal`. |
| 4 | Current dataset-row workspace | No-op. Created by `parse --mode dataset-row`. Do not rewrite it to v3. |
| other | Unsupported | Fail closed. There is no silent jump. |

Each upgrade step is a complete, recoverable commit. An interrupted v1
upgrade may stop on v2; a retry resumes from that exact `HEAD`.

```bash
veriformis upgrade-workspace WORKSPACE
```

A current workspace prints `workspace already current at revision <id>`.
Legacy flat directories that contain `registry.json` and no layout metadata
are not migrated; they fail closed and must be recompiled.

### Parser and chunker producer versions

Every canonical text artifact binds the parser kind and its version, and
every chunk artifact binds its strategy's producer version. When a parser or
chunker changes what it produces, its version moves and workspaces parsed
under the earlier version no longer replay: opening still succeeds, but the
next stage that reconstructs from raw bytes fails closed with an identity or
replay mismatch instead of silently adopting the new recovery. That is the
designed outcome; the remedy is to `parse` again into a new workspace (or a
new revision) and rerun the tail. Sealed bundles are unaffected: verification
never re-parses.

The post-20 defect-closure packet moved these pins on 2026-09-09:

| Producer | From | To | What changed for new runs |
| --- | --- | --- | --- |
| `html` parser | `1.0.0` | `1.2.0` | Capture decoded before lxml (no Latin-1 guess; undecodable refuses); `<br>` and nested blocks become line breaks; `<pre>` whitespace kept; table/list flattening and omitted visible text diagnosed |
| `pdf` parser | `1.0.0` | `1.1.0` | No synthetic `Page N` headings; every paragraph span carries its page index; text-layer whitespace normalization diagnosed; unreadable pages and oversized page counts refuse |
| `docx` parser | `1.2.0` | `1.3.0` | Hardened XML parser for note parts; declared inflated-size and member-count caps; text inside drawings diagnosed as text loss; accepted moved text retained once |
| `csv`, `json`, `jsonl` parsers | `1.0.0` | `1.1.0` | CSV BOM removed and diagnosed; trimmed cells and omitted blank rows diagnosed; JSON refuses `NaN`/`Infinity` and duplicate keys; floats keep shortest round-trip form; string values and key order exact; JSONL frames on `\n` only |
| `json`, `jsonl` parsers | `1.1.0` | `1.1.1` | Exponent overflow such as `1e999` also refuses instead of projecting `inf` |
| `text` parser | `1.1.0` | `1.2.0` | Invalid UTF-8 refuses with `text.not-utf8`; leading BOM removed and diagnosed |
| `sentence` chunker | `1` | `2` | Unicode-aware sentence boundaries (closing quotes, non-ASCII capitals, caseless scripts, CJK terminators) |

Frozen fixtures that pin those identities (the Phase 6 goal acceptance
matrix and the Phase 16 compatibility kit) were regenerated through their
documented generators in the same change; sealed fixture bundles were not
touched because verification does not re-parse.

## Bundles and transports

| Artifact | Version | Load path |
| --- | --- | --- |
| Canonical six-file bundle | `minimal-v1` | `veriformis verify BUNDLE` |
| Deterministic bundle ZIP | `deterministic-vfbundle-zip-v1` | `package-verify --manifest-sha256` |
| Receipt-anchored export ZIP | `deterministic-export-pack-zip-v1` | `package-verify --export-receipt-sha256` |

Pre-taxonomy sealed `minimal-v1` bundles still verify. There is no bundle
schema rewrite. A tampered or unknown profile fails closed.

## Mapping

Confirmed mapping plans are `veriformis.mapping-plan/v1`. Unconfirmed plans
cannot compile. `mapped_value` remains the field evidence. There is no v0
plan importer.

Row-source capture uses the packaged mapping contracts, detectors, and
templates (`contracts-v1`, `detectors-v1`, `templates-v1`, `modes-v1`).
Unknown contract versions fail closed.

## Recipes and automation

| Document | Version | Load path |
| --- | --- | --- |
| Pipeline YAML/JSON | `veriformis.pipeline/v1` | `veriformis run` |
| Project spec | `veriformis.project-spec/v1` | `spec-dry-run`, `spec-run` |
| Project lock | `veriformis.project-lock/v1` | `spec-lock`, `spec-resume` |

`pipeline/v1` stays executable and byte-stable. Project spec is additive.
Loading a spec is not execute. Unknown keys fail closed. There is no
migration that teaches pipeline documents `mode`, `map`, or `export`.

## Exports

| Request | Version | Use |
| --- | --- | --- |
| Export surface request | `veriformis.export-surface-request/v1` | All implemented generic containers |
| Export surface request | `veriformis.export-surface-request/v2` | Split JSONL configured options only |
| Export surface response | `v1` / `v2` | `v2` is dry-run preview |

Container contracts stay at version 1: `split-jsonl-directory`, `json`,
`constrained-csv`, `parquet`, `arrow`, `hugging-face-dataset`. There is no
container rewrite. Hugging Face Dataset is a local container, not Hub
upload.

## Profiles

Implemented optional adapters load `veriformis.profile-admission-discovery/v1`
(`trl`, `mlx-lm`, `axolotl`, `llama-factory`, `aptus`). The Unsloth
candidate pin is not executable. Empty extras stay empty. There is no
profile version rewrite and no trainer launch.

## What this guide does not migrate

- Public signed or notarized Mac artifacts
- Hub execute or publication retry
- Generators, plugin loaders, or hosted training
- Quality-report commands
- Published corpus tiers
- Legacy Aptus row-shape gate IDs (DOC-007); the ID stays until a versioned
  report migration exists

See also [install.md](install.md), [release.md](release.md),
[Support Matrix v1](contracts/support-matrix-v1.md), and
[support-lifecycle.md](support-lifecycle.md).
