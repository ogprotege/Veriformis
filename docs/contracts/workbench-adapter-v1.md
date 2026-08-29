# Workbench Adapter Contract v1

**Contract ID:** `veriformis.workbench-adapter`

**Contract version:** `1`

**Schema:** `veriformis.workbench-adapter/v1`

**Status:** Schema pin through independent-product Phase 18.2. Loading a pin
is not a screen execute. ADR-0019 Decision A: Swift is a process adapter;
`PipelineService` owns policy. Item 18.4 licensed dataset-row mapping on
Compile. Item 18.7 licensed Exports over existing wrap commands. Item
18.8 licensed Review over existing wrap commands.

**Last reviewed:** 2026-08-28

**Authority:** [Independent Product Roadmap](../plans/2026-08-11-veriformis-independent-product-roadmap.md) Phase 18; [ADR-0019](../adr/0019-thin-workbench-adapter.md).

## Purpose

Name one CLI packet a Mac screen may wrap so later items can add UI without
rebuilding taxonomy, recipes, mapping, review, or export in Swift. A pin is
metadata. It is not an execute, not a second catalog, and not a public
plugin API.

## Commands

A wrap command is one existing CLI operation. Unknown commands fail closed
and name the admitted set. `mcp`, `run`, `handoff`, `generator`, and
`install-extension` are not wrap commands.

Admitted commands include document-source compile stages, goal and preset
discovery, preflight and goal preview, mapping packets, export packets, and
review packets. Naming export or review here does not ship those screens.

## Surfaces

| Surface | Role |
| --- | --- |
| `discover` | Read-only catalog or descriptor load |
| `preview` | Runtime-only probe; no destination write |
| `execute` | Stage, map, export, or review submit through the existing packet |

## Pin

`veriformis.workbench-adapter/v1` is one frozen object:

| Field | Rule |
| --- | --- |
| `contract_id` | `veriformis.workbench-adapter` |
| `contract_version` | `1` |
| `schema_id` | `veriformis.workbench-adapter/v1` |
| `command` | One admitted wrap command |
| `surface` | `discover`, `preview`, or `execute` |
| `request_schema_id` | Versioned `veriformis.* /vN` schema id |
| `response_schema_id` | Versioned `veriformis.* /vN` schema id |
| `policy_owner` | `pipeline-service` |
| `adapter_kind` | `process-cli` |
| `catalog_source` | `shared-service` |
| `fail_closed_on` | Exactly `cancelled`, `schema-invalid`, `truncated`, sorted |
| `generation_allowed` | `false`. True is refused under ADR-0018 Decision A. |
| `plugin_install_allowed` | `false`. True is refused under ADR-0017 Decision A. |
| `may_invent_review_policy` | `false` |
| `may_invent_trainer_policy` | `false` |
| `may_invent_family_policy` | `false` |
| `review_policy_default` | `none` |
| `adapter_id` | `derive_id("wba", …)` over the payload excluding `adapter_id` |

Unknown fields fail closed. Missing or unknown contract versions fail closed
and name the requested version and the supported version
`1` (`veriformis.workbench-adapter/v1`).

## Limitations

- `no-execute`
- `no-second-catalog`
- `no-swift-policy`
- `no-plugin-ui`
- `no-generator-ui`
- `no-invented-review-policy`
- `no-invented-trainer-policy`
- `no-invented-family-policy`

## Non-goals

A Swift taxonomy, recipe, mapping, review, or export catalog. Required
review on every recipe. Required Aptus. Family-to-trainer chrome. A
compile-path generator. A public plugin API. Dataset-project code
execution. Review, Exports, or dataset-row screens in this item. Phase 19
publication.
