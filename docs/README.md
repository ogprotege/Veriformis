# Veriformis Documentation

This documentation describes the development-alpha compiler from raw source
capture through a verified finished-dataset bundle, plus local automation and
the private beta Mac workbench (Groups 1–7 product path, Group 9 automated
gates, workbench Phases 0–2).

**Last reviewed:** 2026-08-21 (independent-product Phase 4.5 semantic membership)

**Next review:** Phase 4 atomic publication; beta label cut, public-ready
checklist, or any contract change

## Start here

1. [README](../README.md) — product goal, install, quickstart.
2. [Current implementation status](current-status.md) — exact alpha boundary and evidence.
3. [Install guide](install.md) — standard local CLI + workbench launch.
4. [Product contract](product-contract.md) — ownership and non-claims.
5. [Beta limitations](beta-limitations.md) — hard non-claims before any beta invite.
6. [Independent product analysis](analysis/2026-08-11-independent-product-analysis.md) — evidence and architectural correction.
7. [Independent product roadmap](plans/2026-08-11-veriformis-independent-product-roadmap.md) — authoritative future work and exit gates.
8. [Project tracking and evidence](governance/README.md) — live phase, claim, ADR, evidence, and completion controls.
9. [Release guide](release.md) — current CI gates and owner Mac packaging checklist.

## Reading paths

- **New contributor:** [README](../README.md) → [current status](current-status.md)
  → [project tracking](governance/project-tracking.md) →
  [development guide](development.md) → [architecture hub](architecture.md).
- **CLI operator:** [install.md](install.md) → [CLI reference](cli.md)
  → [Finished Dataset Contract v1](contracts/finished-dataset-v1.md).
- **Optional Aptus integration:** [Aptus Handoff Contract v1](contracts/aptus-handoff-v1.md).
- **Verified derivatives:** [Verified Export Contract v1](contracts/verified-export-v1.md).
- **Workbench operator:** [install.md](install.md) →
  [macOS workbench](../macos/README.md) →
  [private beta plan](plans/2026-08-06-private-beta-workbench.md).
- **Contract reviewer:** [product contract](product-contract.md), then Integrity,
  Dataset Construction, Finished Dataset, Dataset Taxonomy, Verified Export,
  Bundle Transport,
  and Aptus Handoff contracts plus the [ADR index](adr/README.md), with
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
| [Bundle Transport Contract v1](contracts/bundle-transport-v1.md) | Deterministic `.vfbundle.zip` transport and archive verification | Implemented contract |
| [Aptus Handoff Contract v1](contracts/aptus-handoff-v1.md) | Sibling handoff descriptor and consumer checks | Implemented contract |
| [Dataset Taxonomy Contract v1](contracts/taxonomy-v1.md) | Families, rows, containers, profiles, and loss policies | Implemented contract |
| [Verified Export Contract v1](contracts/verified-export-v1.md) | Consumer-neutral derivative plans, receipts, and verification evidence | Models and source admission implemented; execution in progress |
| [ADR index](adr/README.md) | Accepted product-boundary and transport decisions (0001–0005) | Decision records |
| [Architecture hub](architecture.md) | Module, workspace, artifact, and bundle flow | Current architecture |
| [Architecture tree](architecture/README.md) | Layers, dependencies, data flow, entry points | Architecture detail |
| [CLI reference](cli.md) | Commands, options, artifacts, failures | Current CLI reference |
| [Development guide](development.md) | Setup, checks, tests, engineering constraints | Contributor guide |
| [Install guide](install.md) | Standard local CLI + Debug workbench install | Operator setup (private beta) |
| [Release guide](release.md) | CI gates, install smoke, golden path, Mac packaging checklist | Public-release procedure |
| [Beta limitations](beta-limitations.md) | Hard non-claims and operator limits for any future beta cut | Limitations register (maturity still alpha) |
| [macOS workbench](../macos/README.md) | SwiftUI workbench build, launch, parity | Workbench operator guide |
| [Independent product analysis](analysis/2026-08-11-independent-product-analysis.md) | Evidence for the trainer-neutral product direction | Analysis baseline |
| [Independent product roadmap](plans/2026-08-11-veriformis-independent-product-roadmap.md) | Standalone product phases, dependencies, and exit gates | **Authoritative future work order** |
| [Project governance](governance/README.md) | Program ledger, support registry, evidence, ADRs, and completion policy | Active tracking authority |
| [Program ledger](../dev/active/independent-product/program.json) | Phase 0–20 states, dependencies, and next gates | Machine execution state |
| [Phase 0 packet](../dev/active/independent-product/phase-00-foundation/README.md) | Foundation plan, progress, decisions, risks, evidence, and closeout | Completed implementation record |
| [Phase 1 packet](../dev/active/independent-product/phase-01-standalone-independence/README.md) | Standalone-independence packet and closeout | Completed implementation record |
| [Phase 2 packet](../dev/active/independent-product/phase-02-reliability-artifact-boundary/README.md) | Reliability and artifact-boundary packet and closeout | Completed implementation record |
| [Phase 3 packet](../dev/active/independent-product/phase-03-taxonomy/README.md) | Taxonomy contract, registry, discovery, and compatibility closeout | Completed implementation record |
| [Historical build roadmap](plans/2026-07-29-veriformis-roadmap.md) | Implemented Groups 1–7 and release-gate history | Historical evidence |
| [Historical private beta workbench vision](plans/2026-08-06-private-beta-workbench.md) | Implemented private workbench Phases 0–2 | Historical evidence |
| [Phase 1 workbench design](../dev/active/private-beta-workbench/phase-1-design.md) | Sidebar, run sheet, history, settings | Phase 1 design (implemented on `main`) |
| [Contributing](../CONTRIBUTING.md) | PR checklist and standards | Contribution policy |

## Working inventory

Root [WIP.md](../WIP.md) is a reviewed convenience checklist. It never overrides
current status, the support registry, program ledger, roadmap, or a versioned
contract. Pytest checks its independent-program table against the ledger.

## Implementation vocabulary

| Term | Meaning |
| --- | --- |
| **Implemented** | Present in current source and ordinary passing tests |
| **Groups 1–3** | Integrity, construction, finished-dataset stage runtime (Steps 1–16) |
| **Group 4** | `PipelineService`, thin CLI, dual-objective M1.1 (Steps 17–19) |
| **Group 5** | Expanded ingest + recipe library / YAML (Steps 20–21) |
| **Group 6** | MCP + Aptus handoff v1 (Steps 22–23) |
| **Group 7** | SwiftUI workbench (Step 24); private beta Phases 0–2 on `main` |
| **Group 8** | Optional model-assisted construction (Step 25; owner-gated) |
| **Group 9** | Public release gates (Step 26; automated subset landed; owner Mac remainder for public-ready) |
| **Private beta workbench** | Owner Mac GUI over CLI; Phases 0–2 implemented |
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
- Update the active phase packet, program ledger, support registry, WIP, and
  evidence records when tracked truth changes.

## Documentation debt (remaining)

- Owner notarization evidence notes and any security hardening follow-ups
  after signed Mac distribution.
- Architecture deep-dives should prefer stable symbols and file ownership over
  fragile line-number citations.
- Mermaid diagrams are hand-reviewed; not machine-rendered in CI.
- The complete active debt list is maintained in
  [documentation debt](governance/documentation-debt.md).
