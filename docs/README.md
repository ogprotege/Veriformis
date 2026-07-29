# Veriformis Documentation

This documentation describes the development-alpha implementation and the reviewed path from M1 to a release-ready product.

## Start here

1. Read the repository [README](../README.md) for the product goal, setup, and current completion quickstart.
2. Read [Current implementation status](current-status.md) before evaluating datasets or bundles.
3. Read the [product contract](product-contract.md) for the end-to-end raw-source-to-finished-dataset promise.
4. Use the [authoritative build roadmap](plans/2026-07-29-veriformis-roadmap.md) for all post-M1 implementation order and exit gates.

## Active documentation

| Document | Purpose | Authority |
| --- | --- | --- |
| [README](../README.md) | Product introduction, setup, quickstart, and major warnings | Current 0.1.0 entry point |
| [Current implementation status](current-status.md) | Exact implemented capabilities, known limitations, and phase boundary | Current source truth at the audited M1 baseline |
| [Product contract](product-contract.md) | End-to-end ownership, integrity guarantees, and explicit non-claims | Product authority |
| [Architecture](architecture.md) | Current module and artifact flow plus the labeled target architecture | Current and planned architecture reference |
| [CLI reference](cli.md) | Current commands, options, artifacts, and failure boundaries | Current 0.1.0 CLI reference |
| [Development guide](development.md) | Setup, checks, test map, CI scope, and engineering constraints | Current contributor guide |
| [Build roadmap](plans/2026-07-29-veriformis-roadmap.md) | Numbered implementation sequence, execution groups, and exit gates | Authoritative post-M1 roadmap |
| [Contributing](../CONTRIBUTING.md) | Contribution standards and pull request checklist | Contribution policy |

## Historical implementation records

The existing dated design specification and completed M1 implementation plan remain useful history. They predate this documentation baseline and are not sufficient descriptions of current behavior by themselves.

- [Initial design specification](superpowers/specs/2026-07-28-veriformis-design.md)
- [Completed M1 implementation plan](superpowers/plans/2026-07-28-veriformis-m1.md)

When a historical document conflicts with `current-status.md`, the current-status document controls claims about implemented 0.1.0 behavior. The roadmap controls future implementation order.

## Status vocabulary

- **Implemented:** Present in the audited 0.1.0 source and tests.
- **M1.1:** Required for the next trustworthy raw-source-to-finished-dataset vertical slice.
- **Later:** Approved direction after M1.1, but not implemented.
- **Unsupported:** Not available in the current product. Some unsupported features may also remain outside the planned product boundary.

## Documentation rules

- Separate implemented behavior from planned behavior.
- State evidence limits alongside integrity claims.
- Do not describe build success as release readiness.
- Do not call a dataset Aptus-compatible without schema, masking, metadata, split, and backend evidence.
- Keep legacy reference material separate from active product documentation.
- Keep confidential source lineage unnamed.
- Update documentation and tests within the same implementation group.

## Planned documentation additions

The roadmap calls for further reviewed documentation as implementation advances:

- workspace, record, split, manifest, and bundle schemas;
- stable Python API reference after `PipelineService` exists;
- Aptus integration contract;
- security, release, and migration guidance; and
- troubleshooting and verification procedures.

These documents must describe implemented behavior only when their corresponding exit gates pass.
