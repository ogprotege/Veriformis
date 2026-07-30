# Veriformis Documentation

This documentation describes the development-alpha compiler from raw source
capture through a verified finished-dataset bundle.

**Last reviewed:** 2026-07-29 after Group 3 completion

**Next review:** The first Group 4 service change or any contract change,
whichever comes first

## Start here

1. Read the repository [README](../README.md) for the product goal, setup, and
   raw-source quickstart.
2. Read [Current implementation status](current-status.md) for the exact alpha
   boundary and completed Group 3 evidence.
3. Read the [product contract](product-contract.md) for the complete ownership
   boundary.
4. Read [Integrity Contract v1](contracts/integrity-v1.md) for Group 1.
5. Read [Dataset Construction Contract v1](contracts/dataset-construction-v1.md)
   for Group 2.
6. Read [Finished Dataset Contract v1](contracts/finished-dataset-v1.md) for the
   implemented Group 3 curation, split, row, validation, seal, and verification
   contracts.
7. Use the [authoritative build roadmap](plans/2026-07-29-veriformis-roadmap.md)
   for the remaining Group 4 and later work.

## Active documentation

| Document | Purpose | Authority |
| --- | --- | --- |
| [README](../README.md) | Product introduction, setup, raw-source quickstart, and major warnings | Current `0.1.0` entry point |
| [Current implementation status](current-status.md) | Exact capabilities, limitations, verification evidence, and phase boundary | Current source truth after Group 3 completion |
| [Product contract](product-contract.md) | End-to-end ownership, integrity guarantees, and non-claims | Product authority |
| [Integrity Contract v1](contracts/integrity-v1.md) | Group 1 workspace, identity, evidence, and cleaning guarantees | Implemented contract |
| [Dataset Construction Contract v1](contracts/dataset-construction-v1.md) | Group 2 objectives, recipes, evidence, lifecycle, and replay guarantees | Implemented contract |
| [Finished Dataset Contract v1](contracts/finished-dataset-v1.md) | Group 3 curation, leakage splitting, product rows, exact validation, minimal bundle, seal, and verification | Implemented contract |
| [Architecture](architecture.md) | Current module, workspace, artifact, and bundle flow | Current architecture reference |
| [CLI reference](cli.md) | Current commands, options, artifacts, and failure boundaries | Current `0.1.0` CLI reference |
| [Development guide](development.md) | Setup, checks, test map, CI scope, and engineering constraints | Current contributor guide |
| [Build roadmap](plans/2026-07-29-veriformis-roadmap.md) | Numbered implementation sequence, groups, and exit gates | Authoritative implementation order |
| [Contributing](../CONTRIBUTING.md) | Contribution standards and pull request checklist | Contribution policy |

## Historical implementation records

The dated design specification and completed M1 plan preserve product and
implementation history. Their status notes identify later implementation, but
their original decisions remain historical.

- [Initial design specification](superpowers/specs/2026-07-28-veriformis-design.md)
- [Completed M1 implementation plan](superpowers/plans/2026-07-28-veriformis-m1.md)

When a historical document conflicts with `current-status.md`, the current
status document controls present behavior. The roadmap controls future order.

## Status vocabulary

- **Implemented:** Present in current source and ordinary passing tests.
- **Groups 1 through 3:** The integrity, construction, and finished-dataset
  stage-command runtime for Steps 1 through 16.
- **Group 3 Complete:** Runtime, repository checks, raw-source demonstration,
  and independent architecture and security review satisfy the Group 3 gate.
- **Group 4:** `PipelineService`, a thin CLI, and dual-objective M1.1 API and CLI
  acceptance.
- **Later:** Approved direction after M1.1, but not implemented.
- **Unsupported:** Not available in the current product.

## Documentation rules

- Separate implemented behavior from planned behavior.
- Keep raw source material as the product entry point.
- Treat clean corpus state as intermediate unless `full_text` selects it.
- State evidence limits beside integrity claims.
- Distinguish exact persisted bytes, portable semantic digests, and historical
  revision IDs.
- Do not describe a green build as release readiness.
- Do not call a bundle externally trusted without a retained expected manifest
  digest.
- Describe Group 3 Aptus support as row-shape validation only.
- Keep historical reference material separate from active guidance.
- Update documentation and tests in the same implementation group.

## Documentation debt

These documents remain intentionally deferred with their owning work:

- stable Python API reference after `PipelineService` exists;
- dual-objective M1.1 API and CLI acceptance procedure;
- versioned Aptus bundle handoff and backend partition enforcement;
- expanded input, security, release, and migration guidance; and
- troubleshooting for the future supported release surface.
