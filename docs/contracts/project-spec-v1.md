# Project Spec Contract v1

**Contract ID:** `veriformis.project-spec`

**Contract version:** `1`

**Schema:** `veriformis.project-spec/v1`

**Status:** Schema pin. Loading a spec is not execute. Additive over
`veriformis.pipeline/v1`. Independent-product item 19.2.

**Last reviewed:** 2026-08-31

**Authority:** [Independent Product Roadmap](../plans/2026-08-11-veriformis-independent-product-roadmap.md) Phase 19.

## Purpose

Name one locked compile intent: compiler path, confirmed mapping when
required, goal, preset, optional export selection, and independently
admitted consumer profile. Existing `veriformis.pipeline/v1` documents
still run. This pin does not dry-run, lock, resume, upload, or add MCP
or CI surfaces.

## Closed vocabularies

| Field | v1 values |
| --- | --- |
| Mode | `document-source`, `dataset-row`, `mixed` (ADR-0010) |
| Export container | `split-jsonl-directory`, `json`, `constrained-csv`, `parquet`, `arrow`, `hugging-face-dataset` |
| Export overwrite | `refuse` |
| Generation | `false` |
| Plugin install | `false` |
| Publication | `false` |

## Pin

`veriformis.project-spec/v1` is one frozen object:

| Field | Rule |
| --- | --- |
| `contract_id` | `veriformis.project-spec` |
| `contract_version` | `1` |
| `schema_id` | `veriformis.project-spec/v1` |
| `mode` | One ADR-0010 compiler path |
| `goal_id` / `preset_id` | Optional; unknown ids fail closed |
| `mapping` | Required for `dataset-row` and `mixed`. Forbidden on `document-source`. Must name `mapping_plan_id` and `confirmation_digest`. Unconfirmed maps fail closed. `mapped_value` remains the evidence. |
| `pipeline` | Optional embedded `veriformis.pipeline/v1` object. Unknown pipeline keys fail closed. |
| `pipeline_ref` | Optional path. Cannot combine with `pipeline`. |
| `export` | Optional container, optional independently admitted profile, overwrite `refuse`. Destination is a later execute field. |
| `consumer_profile` | Optional; only independently admitted profiles |
| `generation_allowed` | `false` |
| `plugin_install_allowed` | `false` |
| `publication_allowed` | `false` |
| `spec_id` | `derive_id("psp", …)` over the payload excluding `spec_id` and null optional fields |

Unknown fields fail closed. Unknown versions fail closed and name the
requested version and the supported version `1`
(`veriformis.project-spec/v1`). Mixed fused document and row members
fail closed. Family goals cannot select a refusing trainer profile.

## Limitations

- `no-execute`
- `no-dry-run`
- `no-lockfile`
- `no-hub-upload`
- `no-resume`

Loading a spec is not execute. `veriformis.pipeline/v1` stays executable
and byte-stable.
