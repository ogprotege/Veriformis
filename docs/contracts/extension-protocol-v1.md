# Extension Protocol Contract v1

**Contract ID:** `veriformis.extension-protocol`

**Contract version:** `1`

**Schema:** `veriformis.extension-protocol/v1`

**Status:** Schema pin through independent-product Phase 16.8. Built-in
declarations are read-only discovery over the internal registry. `.txt`
and generic `split-jsonl-directory` are selected through the protocol;
other suffixes, containers, and consumer profiles keep their existing
paths. Compatibility goldens live in a test-only kit. ADR-0017 Decision A
forbids an untrusted loader. The contract does not load third-party code
and is not a public plugin API.

**Last reviewed:** 2026-08-27

**Authority:** [Independent Product Roadmap](../plans/2026-08-11-veriformis-independent-product-roadmap.md) Phase 16.

## Purpose

Name one built-in or third-party capability as a closed declaration so later
internal registries can select it without inventing a second policy engine.
A declaration is metadata. It is not executable binding, not a loader, and
not an admission of a new parser, family, container, or profile.

## Kinds

| Kind | Role in v1 |
| --- | --- |
| `source-parser` | Suffix-dispatched source recovery |
| `row-mapper` | Dataset-row compiler mapping |
| `deterministic-constructor` | Objective constructor |
| `quality-check` | Preview-only quality detector or gate |
| `container-exporter` | Verified export container |
| `consumer-profile` | Optional adapter selected by `consumer_id` |

Unknown kinds fail closed. Errors list the admitted kinds.

## Origin and lifecycle

| Field | v1 values |
| --- | --- |
| Origin | `builtin`, `third_party` |
| Lifecycle | `experimental`, `supported`, `deprecated`, `removed`, `migrated` |

`third_party` is a declared origin, not an implemented loader. Item 16.3
keeps the registry built-in-only. Public plugins wait for item 16.8.

## Declaration

`veriformis.extension-protocol/v1` is one frozen object:

| Field | Rule |
| --- | --- |
| `contract_id` | `veriformis.extension-protocol` |
| `contract_version` | `1` |
| `schema_id` | `veriformis.extension-protocol/v1` |
| `kind` | One of the six kinds |
| `origin` | `builtin` or `third_party` |
| `lifecycle` | One of the five lifecycle tokens |
| `extra` | `null` or a lowercase extra token |
| `requirements` | Offline, no network, no LLM generation, profile `offline-deterministic-v1` |
| `diagnostic_ids` | Sorted unique lowercase tokens |
| `fixture_ids` | Sorted unique lowercase tokens |
| `discovery.selector` | Lowercase hyphenated token |
| `discovery.title` | Non-empty exact string |
| `discovery.consumer_id` | Required for `consumer-profile`; forbidden otherwise |
| `declaration_id` | `derive_id("exd", …)` over the payload excluding `declaration_id` |

Unknown fields fail closed. Missing or unknown contract versions fail closed
and name the requested version and the supported version
`1` (`veriformis.extension-protocol/v1`).

## Limitations

- `internal-only`
- `no-loader`
- `no-public-plugin-api`
- `no-in-process-project-plugins`
- `no-mac-plugin-ui`
- `no-new-families`
- `taxonomy-is-not-the-registry`

## Non-goals

A public plugin API. Entry-point discovery. A workspace `plugins/` path.
Dispatch changes. A second export catalog. An eighth taxonomy axis. Mac
extension UI. Phase 17 semantic families. In-process Python from a dataset
project.
