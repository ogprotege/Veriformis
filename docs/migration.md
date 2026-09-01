# Veriformis Migration Guide

**Status:** Operator guide for supported persisted versions in development
alpha `0.1.0`

**Last reviewed:** 2026-08-31 (independent-product Phase 20.3)

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
