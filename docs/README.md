# Veriformis Documentation

This documentation describes the development-alpha compiler from raw source
capture through a verified finished-dataset bundle, plus local automation and
workbench surfaces built in Groups 1 through 7.

**Last reviewed:** 2026-08-06 after PR #16 (beta-prep) merge to `main`

**Next review:** Deliberate beta label cut, public-ready checklist, or any contract change

## Start here

1. Read the repository [README](../README.md) for product goal, setup, and
   quickstart.
2. Read [Current implementation status](current-status.md) for the exact alpha
   boundary (Groups 1–7 plus Group 9 automated gates) and verification evidence.
3. Read the [product contract](product-contract.md) for ownership and non-claims.
4. Use the [authoritative build roadmap](plans/2026-07-29-veriformis-roadmap.md)
   for remaining Group 9 owner Mac evidence and optional Group 8 work.
5. Use [Release guide](release.md) for CI gates, golden compile, and Mac packaging.
6. Read [Beta limitations](beta-limitations.md) before any beta or external invite.

## Reading paths

- **New contributor:** [README](../README.md) → [current status](current-status.md)
  → [development guide](development.md) → [architecture hub](architecture.md).
- **CLI operator:** [README](../README.md) quickstart → [CLI reference](cli.md)
  → [Finished Dataset Contract v1](contracts/finished-dataset-v1.md) for bundles
  → [Aptus Handoff Contract v1](contracts/aptus-handoff-v1.md) for handoff.
- **Workbench operator:** [macOS workbench README](../macos/README.md).
- **Contract reviewer:** [product contract](product-contract.md), then Integrity,
  Dataset Construction, Finished Dataset, and Aptus Handoff contracts, with
  [current status](current-status.md) for evidence.

## Active documentation

| Document | Purpose | Authority |
| --- | --- | --- |
| [README](../README.md) | Product introduction, setup, quickstart | Current `0.1.0` entry point |
| [Current implementation status](current-status.md) | Exact capabilities, limitations, evidence, phase boundary | **Current source of truth** for capability claims |
| [Product contract](product-contract.md) | End-to-end ownership, integrity guarantees, non-claims | Product authority |
| [Integrity Contract v1](contracts/integrity-v1.md) | Workspace, identity, evidence, cleaning | Implemented contract |
| [Dataset Construction Contract v1](contracts/dataset-construction-v1.md) | Objectives, recipes, evidence, lifecycle | Implemented contract |
| [Finished Dataset Contract v1](contracts/finished-dataset-v1.md) | Curation, split, rows, validation, seal, verify | Implemented contract |
| [Aptus Handoff Contract v1](contracts/aptus-handoff-v1.md) | Sibling handoff descriptor and consumer checks | Implemented contract |
| [Architecture hub](architecture.md) | Module, workspace, artifact, and bundle flow | Current architecture |
| [Architecture tree](architecture/README.md) | Layers, dependencies, data flow, entry points | Architecture detail |
| [CLI reference](cli.md) | Commands, options, artifacts, failures | Current CLI reference |
| [Development guide](development.md) | Setup, checks, tests, engineering constraints | Contributor guide |
| [Release guide](release.md) | CI gates, install smoke, golden path, Mac packaging checklist | Public-release procedure |
| [Beta limitations](beta-limitations.md) | Hard non-claims and operator limits for any future beta cut | Limitations register (maturity still alpha) |
| [macOS workbench](../macos/README.md) | SwiftUI workbench build and parity | Workbench operator guide |
| [Build roadmap](plans/2026-07-29-veriformis-roadmap.md) | Numbered sequence, groups, exit gates | Authoritative work order |
| [Private beta workbench vision](plans/2026-08-06-private-beta-workbench.md) | Compile framing, KISS UI, phases 0–4 | Owner private-beta plan (not public claim) |
| [Contributing](../CONTRIBUTING.md) | PR checklist and standards | Contribution policy |

## Working inventory

Root [WIP.md](../WIP.md) is a reviewed convenience checklist. It never overrides
current status, the roadmap, or a versioned contract.

## Implementation vocabulary

| Term | Meaning |
| --- | --- |
| **Implemented** | Present in current source and ordinary passing tests |
| **Groups 1–3** | Integrity, construction, finished-dataset stage runtime (Steps 1–16) |
| **Group 4** | `PipelineService`, thin CLI, dual-objective M1.1 (Steps 17–19) |
| **Group 5** | Expanded ingest + recipe library / YAML (Steps 20–21) |
| **Group 6** | MCP + Aptus handoff v1 (Steps 22–23) |
| **Group 7** | SwiftUI workbench (Step 24) |
| **Group 8** | Optional model-assisted construction (Step 25; owner-gated) |
| **Group 9** | Public release gates (Step 26; automated subset landed; owner Mac remainder for public-ready) |
| **Unsupported** | Not available (for example OCR) |

## Historical records

Dated design specs and completed plans are historical. Their status sections
may note later completion; they do not redefine current capability.

- [Initial design specification](superpowers/specs/2026-07-28-veriformis-design.md)
- [Completed M1 implementation plan](superpowers/plans/2026-07-28-veriformis-m1.md)

When historical prose conflicts with `current-status.md`, **current status
controls**.

## Documentation rules

- Separate implemented behavior from planned behavior.
- Keep raw source as the product entry; clean state is intermediate unless
  `full_text` selects it.
- State evidence limits beside integrity claims.
- Do not describe a green build as release readiness.
- Do not call a bundle externally trusted without a retained expected manifest
  digest.
- Update documentation and tests in the same implementation group.

## Documentation debt (remaining)

- Owner notarization evidence notes and any security hardening follow-ups
  after signed Mac distribution.
- Architecture deep-dive `file:line` citations should be re-verified when
  entry-point line numbers drift.
- Mermaid diagrams are hand-reviewed; not machine-rendered in CI.
