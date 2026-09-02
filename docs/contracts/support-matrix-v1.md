# Support Matrix Contract v1

**Contract ID:** `veriformis.support-matrix`

**Contract version:** `1`

**Schema:** `veriformis.support-matrix/v1`

**Status:** Frozen CLI-first capability pin in independent-product Phase 20.2.
Loading the pin is not a version bump. Product version remains `0.1.0`
development alpha. Item 20.10 retained that version.

**Last reviewed:** 2026-09-02

**Authority:** [Independent Product Roadmap](../plans/2026-08-11-veriformis-independent-product-roadmap.md) Phase 20.

## Purpose

Name the 1.0 support matrix from evidence that already passed. Freeze only
implemented capabilities. Exclude unsupported candidates rather than weakly
claiming them. Honest 1.0 is CLI-first independent core.

## Catalog

The packaged JSON is canonical. Python `PipelineService.discover_support_matrix`,
CLI `support-matrix`, and MCP `support_matrix` emit the same object.

| Axis | Frozen claim |
| --- | --- |
| Product version | `0.1.0` retained at 20.10 |
| Maturity | `development-alpha` retained at 20.10 |
| Claim | `cli-first-independent-core` |
| Python | 3.11, 3.12, 3.13 |
| CI hosts | Ubuntu 3.11–3.13 and macOS 3.12 |
| Mac workbench | local-dev thin CLI adapter |
| Public signed Mac | `false` (unsigned Debug GitHub `xcodebuild` does not change this) |
| Core surfaces | Python `PipelineService`, Typer CLI, local MCP |
| Aptus | not required |
| Corpus tiers | empty |
| Quality-report command | preview CLI; not a gate |

Inputs, goals, rows, containers, and optional profiles copy the live support
registry and taxonomy. Optional extras stay empty. A profile failure does not
block the independent core.

## Exclusions

- `hub-execute` — ADR-0020 Decision A
- `public-signed-mac` — Group 9 owner remainder; skip unless 20.6 has evidence
- `generator` — ADR-0018 Decision A
- `plugin-loader` — ADR-0017 Decision A
- `unsloth-execute` — candidate, not executable
- `default-parse-ocr-image` — default parse still refuses image-only PDF
- `published-corpus-tiers` — scale-support tiers stay empty
- `hosted-training` — the exporter does not train
- `required-trainer-extras` — extras stay empty

Unknown fields fail closed.

## Non-goals

A 1.0.0 version tag. Public signed/notarized Mac. Hub upload. A generator.
An untrusted plugin loader. Required trainer extras. A published corpus SLA.
