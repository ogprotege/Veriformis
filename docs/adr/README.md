# Architecture Decision Records

**Status:** Active index

**Last reviewed:** 2026-08-24 (independent-product Phase 10.1 packet)

**Next review:** Every material architecture or product-boundary decision

ADRs record durable decisions and their evidence. They explain why a decision
was accepted, what it does not prove, and which events require review. They are
not substitutes for implementation or tests.

## Status values

- **Proposed:** Under review; not binding implementation policy.
- **Accepted:** Current decision.
- **Superseded:** Replaced by a linked later ADR; retained as history.
- **Deprecated:** Still observable but should not be used for new work.
- **Rejected:** Considered and explicitly declined.

## Index

| ADR | Decision | Status | Review trigger |
| --- | --- | --- | --- |
| [0001](0001-tracking-authority-and-evidence.md) | Tracking authority and evidence grades | Accepted | Governance schema or completion-policy change |
| [0002](0002-standalone-product-boundary.md) | Standalone Veriformis product boundary | Accepted | Any proposal to require a downstream trainer |
| [0003](0003-four-axis-dataset-model.md) | Four-axis dataset model | Accepted | Persisted taxonomy or loss-policy design |
| [0004](0004-canonical-bundle-derived-exports.md) | Canonical bundle and derived exports | Accepted | Export contract or bundle-profile implementation |
| [0005](0005-deterministic-bundle-transport.md) | Deterministic immutable bundle transport | Accepted | Bundle profile, packaging, compression, or trust-envelope change |
| [0006](0006-receipt-anchored-export-pack-transport.md) | Receipt-anchored deterministic export-pack transport | Accepted | Export receipt, archive profile, packaging, or trust-envelope change |
| [0007](0007-goal-first-catalog-as-versioned-data.md) | Goal-first catalog and presets as versioned data over existing objectives | Accepted | Objective, row-schema, loss-policy, or representation change; Phase 6.4 preset freeze; Phase 17 or 18 |
| [0008](0008-input-family-taxonomy-axis.md) | Input family as the seventh taxonomy axis | Accepted | New parser kind or suffix; Phase 11 input qualification; Phase 12 OCR |
| 0009 | Not issued | — | Number skipped; 0010 follows 0008 |
| [0010](0010-input-mode-as-compiler-path.md) | Input mode as a compiler path | Accepted | Any new compiler path beyond document-source, dataset-row, and mixed |
| [0011](0011-imported-records-and-mapping-evidence.md) | Imported records and mapped-value evidence | Accepted | Any new field-evidence kind, membership policy, or admitted row container |
| [0012](0012-consumer-profile-as-optional-adapter.md) | Consumer profile as optional adapter over a verified bundle | Accepted | Item 8.3 TRL execution; item 8.4 MLX-LM execution; any required trainer extra |
| [0013](0013-columnar-containers-as-optional-generic-exports.md) | Columnar containers as optional generic exports | Accepted | Item 9.4 Parquet execution; item 9.5 Arrow execution; item 9.6 Hugging Face Dataset execution; any required PyArrow extra |
| [0014](0014-independently-admitted-consumer-profiles.md) | Independently admitted Phase 10 consumer profiles | Accepted | Item 10.2 admission pins; any required trainer extra; Aptus profile migration |

## ADR template

Each ADR contains:

1. Status, date, and deciders.
2. Context and evidence.
3. Decision.
4. Consequences and limitations.
5. Alternatives considered.
6. Verification and review triggers.

New ADRs use a zero-padded sequential number. An accepted ADR is changed only
to clarify non-semantic metadata or add evidence; a changed decision receives a
new ADR that supersedes the old one.
