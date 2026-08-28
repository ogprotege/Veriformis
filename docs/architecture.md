# Architecture

**Last reviewed:** 2026-08-27 (independent-product Phase 16.7 compatibility kit)

**Next review:** Any service-boundary or architecture change

Veriformis `0.1.0` is a Python 3.11+ modular monolith with a typed
composition root, `veriformis.pipeline.PipelineService`, and multiple thin
adapters: the `veriformis` CLI, constrained local MCP (`veriformis.mcp`), and
the SwiftUI workbench under `macos/` (CLI shell). Domain modules own strict
persisted contracts and pure transformations; adapters must not reimplement
stage policy. Workspace state is content-addressed and replay-gated.

This hub holds the pipeline at a glance, the module map, and the operational
layouts; the overview and four citation-backed deep dives live under
[architecture/](architecture/README.md).

## Pipeline at a glance

```mermaid
flowchart LR
    subgraph documentSource["Document-source stages (revision v3)"]
        P[parse] --> C[clean] --> K[chunk] --> N[construct] --> U[curate] --> X[split] --> F[format] --> V[validate] --> L[seal]
    end
    raw["raw bytes"] --> P
    L --> B["six-file bundle"]
    W["workspace: content-addressed revisions, atomic HEAD"] -. "commit + replay" .-> documentSource
```

Dataset-row workspaces (revision v4) skip `clean`, `chunk`, and `construct`:
`parse --mode dataset-row` → `map` → `curate` → `split` → `format` →
`validate` → `seal`. Both paths publish the same six-file bundle.

Clean corpus state is intermediate unless `full_text` selects it as the exact
training target; other objectives derive explicit context and target fields.

## Module map

A foundation kernel (`errors.py`, `contracts.py`, `identity.py`,
`diagnostics.py`, `sources.py`, `evidence.py`) holds the shared exception
taxonomy, schema and gate registries, canonical-JSON identity substrate, and
provenance model. Above it sit `ir/` (the canonical document model) and six
stage packages in pipeline order — `parsers/`, `rules/`, `chunkers/`,
`construction/`, `datasets/`, `bundle/` — flanked by axial modules:
`workspace.py` (revision kernel); `pipeline/` (`PipelineService`); `recipes/`;
`exports/` (consumer-neutral verified-derivative composition boundary);
`handoff/`; `mcp/`; `goals/`; `mapping/` (compiler-path modes, capture,
confirmed mapping, templates); `profiles/` (implemented TRL, MLX-LM, Axolotl, LLaMA-Factory, and Aptus admission
pins and adapters); `ocr/` (Tesseract 5 identity pin, optional subprocess provider, empty
extra `ocr`; default parse still refuses image-only PDF);
`quality/` (versioned quality report; facts stay separate from policy
and recommendations; not enforcing);
`review/` (queues, corrections as new identities, named-seed sampling,
packet exchange, required-review seal blocking, auditable supersession);
`extensions/` (internal protocol, built-in-only registry, read-only declarations; `.txt` and generic `split-jsonl-directory` selected through the protocol; no loader);
and `cli.py` (Typer adapter).
Phase 4 establishes the
typed export service, descriptor-anchored verified source view, strict
persisted export models, fail-closed source-trust admission, and read-only
source-derived plan population and normalized semantic membership enforcement,
plus internal exact-byte atomic publication and independent closed-tree
verification. Phase 4.7 adds private two-render evidence: exact profiles compare
normalized byte trees, while semantic profiles compare versioned canonical
preimages and reconstructed membership and replay descriptor-reread staged
bytes. Phase 4.8 adds an initially production-empty private implementation
catalog and thin `PipelineService`, CLI, MCP, and CLI-backed Mac operations for
discovery, dry run, self-described inspect, execute, and source-bound verify.
Phase 5.1–5.3 install the catalog's first three production exact-byte renderers,
`split-jsonl-directory`, canonical `json`, and `constrained-csv` v1. They copy
authoritative semantic partitions without changing rows or membership and add only
deterministic evidence sidecars; none has a consumer profile or trainer-
compatibility claim. Constrained CSV admits only the three flat row schemas;
nested `messages` is refused with a JSON alternative. No production semantic
replayer ships. Phase 5.4, merged as PR #56 at
`499d61fa2e7dd12edb5808c6bd9d0e0ab6b738c8`, adds no renderer:
`exports/archive.py` wraps one unchanged published export directory as receipt-anchored
`.vfexport.zip` using the deterministic codec shared in
`_archive_transport.py`. `PipelineService.package` selects this profile only
through the explicit receipt-digest argument. Export discovery and the
MCP/Mac surfaces remain unchanged. Phase 6.1 adds `goals/`: the packaged
versioned goal catalog (`catalog-v1.json`) with strict models that resolve
every plain-language goal to exactly one existing objective and named recipe,
and every representation to one existing row schema and loss policy; the
service, CLI, MCP, and Mac bridge expose it read-only and byte-identically.
Phase 6.2 adds per-goal contracts and the seventh taxonomy axis
`input_family`; Phase 6.3 adds `goals/preview.py`, a runtime-only read-only
view over a constructed workspace that renders each record through the same
row-lowering function `format` uses and derives the exact supervised span
from the objective field roles and taxonomy loss policy. Phase 6.4 adds
`goals/presets.py` and `presets-v1.json`: the single versioned source of every
recipe default and of each goal's safe preset, resolved through one function by
the service, CLI, MCP, YAML runner, recipe library, and workbench, with the
tracking checker refusing any recipe default literal in those surfaces.
Phase 6.5 adds `goals/preflight.py`, a bounded runtime-only probe that captures
each raw source once and composes the production parser, cleaning replay,
chunking, named construction, global curation, and split functions in memory.
The service, CLI, MCP, and Mac workbench share its exact response, while real
construction shares the same goal/input-family gate so preflight and compile
cannot disagree about source eligibility. It creates no workspace and accesses
no renderer or destination. Phase 6.6 freezes the discovery-closed acceptance
matrix over every eligible goal, input family, and compatible representation.
Phase 6.7 stores one static instruction template and unique task phrase per
goal in the catalog; omitted `instruction-and-output` instructions resolve to
that template, and a supplied instruction is admitted only after the
deterministic truthfulness check.
Phase 7 adds `mapping/` as the dataset-row compiler path: modes
`document-source`, `dataset-row`, and `mixed`; confirmed mapping into the four
semantic rows; workspace revision v4 with stage `map`; JSON/CSV capture;
rejection reports; and packaged mapping templates. Mode is not a taxonomy
axis. Imported fields carry `mapped_value` evidence and seal through ordinary
`ProductRow` v1.
Phase 8 records that a consumer profile is an optional adapter over that
bundle (ADR-0012, ADR-0014). `profiles/` holds implemented TRL, MLX-LM, Axolotl, LLaMA-Factory, and Aptus admission
pins and adapters with empty extras. Generic export selectors stay
`consumer_id` null. Taxonomy lists `trl`, `mlx-lm`, `axolotl`,
`llama-factory`, and `aptus` as implemented. `unsloth` remains candidate.
Phase 9.2 packages Arrow and Hugging Face feature pins in
`exports/columnar_schemas-v1.json`. Phase 9.3 packages semantic
fingerprints in `exports/columnar_fingerprint-v1.json` as
`semantic_content_only` over ordered product payloads. Extra `columnar`
stays empty. Parquet, Arrow IPC, and local Hugging Face DatasetDict v1
are implemented generic containers. Extra `columnar` stays empty. There
is no Hub upload.
The macOS workbench lives
outside the Python package under `macos/`. Retained legacy packages
(`serializers/`, `validate/`) have no production callers.

Deep dives: [Layers](architecture/layers.md) — stack and isolation;
[Dependencies](architecture/dependencies.md) — fan-in and containment;
[Data flow](architecture/data-flow.md) — shapes and provenance;
[Entry points](architecture/entry-points.md) — commands, transactions.

## Transactional workspace

Physical layout (workspace layout schema 1):

```text
workspace/
├── workspace.json
├── HEAD
├── LOCK
├── objects/
│   └── sha256/<prefix>/<digest>
├── revisions/
│   └── <revision-id>/revision.json
└── .txn/
```

- Active workspaces use revision schema 3. `HEAD` is the only mutable commit
  pointer; commits hold an exclusive `LOCK`, require the expected parent, and
  leave the prior revision current if interrupted pre-commit.
- Opening a workspace re-verifies every revision in the active parent chain
  and re-hashes every referenced object; altered bytes fail closed.
- If `HEAD` changes but the final directory sync fails, the API returns the
  visible revision with a durability warning rather than reporting rollback.
- `upgrade-workspace` migrates revision v1 through v2 to v3 stepwise: v2 to
  v3 preserves parse, clean, chunk, and construct facts, adds curate and
  split as absent, and retires legacy format, validate, and seal state.

## Stage graph

Rerunning a stage invalidates all descendants.

| Stage | Direct dependencies | Logical output keys |
| --- | --- | --- |
| `parse` | none | `registry`; per-source `raw`, `canonical`, `document`, `diagnostics` |
| `clean` | `parse` | `transforms`; per-source `document`, `cleaning-plan`, `block-derivations` |
| `chunk` | `clean` | `chunks` |
| `construct` | `parse`, `clean`, `chunk` | `recipe`, `result` |
| `curate` | `construct` | `plan`, `result` |
| `split` | `construct`, `curate` | `result` |
| `format` | `construct`, `curate`, `split` | `row-set`, `train`, `evaluation`, `provenance` |
| `validate` | all of `parse`–`format` | `snapshot`, `report` |
| `seal` | all of `parse`–`validate` | `manifest`, `attestation` |

## Finished bundle layout

The exact `minimal-v1` file set (`.vfbundle` is conventional, not enforced):

```text
name.vfbundle/
├── data/train.jsonl
├── data/evaluation.jsonl
├── metadata/row-provenance.jsonl
├── validation.json
├── manifest.json
└── attestation.json
```

- Seal rebuilds the validation report, requires byte-semantic equality with
  the saved passing report, and publishes: staged in a private sibling
  directory, fsynced, independently verified, atomically renamed without
  overwrite.
- The manifest binds exact paths, roles, media types, sizes, digests, record
  counts, snapshot, validation report, and content root; it does not hash
  itself. The co-located attestation binds the exact manifest digest.
- Trust grades state the evidence limit: `self_consistent` proves internal
  agreement only; `external_digest` adds a matching expected manifest
  SHA-256 from a separate trusted channel. Without that retained digest a
  bundle is internally consistent, not externally authenticated.
- Publication assumes an integrity-controlled destination parent: the
  no-replace rename protects cooperating writers, not a hostile same-owner
  process renaming parent entries mid-rename (see the
  [contract](contracts/finished-dataset-v1.md)).
- Finder-facing transport uses a deterministic `.vfbundle.zip` containing
  those exact six paths. Packaging requires `external_digest` verification;
  archive verification reconstructs the strict directory and reuses the same
  canonical verifier. This is transport only, not a trainer export. See
  [ADR 0005](adr/0005-deterministic-bundle-transport.md).
- Phase 5.4's optional `.vfexport.zip` transport starts only after one generic
  export directory is published. It requires the separately retained SHA-256
  of canonical `export-receipt.json`, archives exactly that receipt and its
  complete bound files, and reuses the same deterministic ZIP codec and
  no-replace publication path. Its verifier is receipt-anchored, preserves the
  embedded source trust grade, and is not source-bound export verification.
  It adds no export selector, persisted receipt field, MCP operation, or Mac UI.
  See [ADR-0006](adr/0006-receipt-anchored-export-pack-transport.md).
- Phase 4 derivatives start from `ExportService`, which obtains manifest,
  validation, row-set, and verification facts in the bundle verifier's same
  descriptor-anchored pass. Export-source admission requires a retained
  expected manifest digest by default; lower self-consistent trust must be
  selected explicitly, and supplied evidence never falls back. Its read-only
  `create_plan` operation derives every source identity and the complete source
  membership baseline from that immutable pass; callers provide only profile,
  dependency, and file-plan evidence. `create_plan` is not a workspace stage,
  does not reopen source paths, and does not mutate `minimal-v1` or write
  destination content.
- Its read-only `validate_derivative_membership` operation fresh-reconstructs a
  candidate `RowSet` from normalized train/evaluation rows and aligned
  provenance, then requires exact planned row-set and complete projection
  equality. It does not inspect produced destination bytes.
- Its internal `publish` operation is reachable through Python composition and
  supports private exact-byte and semantic-content conformance. It re-verifies
  the source and plan, renders twice from independent strict inputs, validates
  normalized membership for both results, compares either complete byte trees
  or versioned canonical semantic preimages, and uses descriptor-anchored
  staging plus one atomic no-replace promotion. Semantic output is replayed from
  staged descriptors before verification.
- Phase 4.8 adds an exports-owned private implementation catalog plus strict
  discovery, dry run, self-described inspect, operator-confirmed execute, and
  source-bound verify operations through `PipelineService`, CLI, MCP, and the
  CLI-backed Mac bridge. Execute reaches the same internal publisher; adapters
  do not implement filesystem policy. At the Phase 4 exit the production
  catalog is empty. Phase 5.1 adds the exact-byte `split-jsonl-directory` v1
  implementation. Its request-v1 defaults write
  canonical `data/train.jsonl`, `data/evaluation.jsonl`, aligned provenance, a
  deterministic README/data card, and the receipt. Configured request v2 must
  provide the complete `veriformis.split-jsonl-options/v1` object and may only
  change the two safe filename stems or omit provenance. Those layout choices
  do not mutate rows, ordering, curation, split policy, or membership. Phase
  5.2 adds canonical `json` v1: request v1 selects a fixed tree containing one
  explicit split/schema-bearing `dataset.json`, mandatory separately aligned
  provenance, deterministic README, and receipt; request v2 is refused. The
  Phase 5.3's `constrained-csv` v1 renderer uses request v1 only and writes fixed,
  fully quoted train/evaluation CSV files, a dataset card, mandatory aligned
  provenance, README, and receipt. Its exact ordered headers support `text`,
  `prompt_completion`, and `instruction_output`; nested `messages` and request
  v2 fail before publication with an actionable JSON alternative. The
  default service still has no semantic replayer and discovery advertises no
  consumer or trainer profile.
- Phase 5.4, merged as PR #56 at
  `499d61fa2e7dd12edb5808c6bd9d0e0ab6b738c8`, leaves that export catalog
  unchanged. The existing
  `package` / `package-verify` family selects bundle or export-pack transport
  through exactly one manifest- or export-receipt-digest anchor. The export
  branch validates the already-published closed directory, writes canonical
  `.vfexport.zip` bytes through the shared archive codec, verifies staged bytes,
  and publishes without replacement. Its runtime archive facts do not alter
  the inner plan, receipt, verification, rows, or membership.
- Phase 5.5 changes no runtime edge. Its merged test-only fixture
  reloads ordinary files for all eleven compatible current container/schema
  pairs to the exact ordered partitions, provenance, and source `RowSet`, and
  checks one semantic tamper per container plus constrained CSV's actionable
  `messages` refusal. It adds no importer, replayer, API, taxonomy, support, or
  trainer boundary. Phase 5.5 merged as PR #57 at
  `c72b8e9ec7bc2746d74404226aa086d497e15db1`.
- Phase 5.6 adds one runtime-only edge inside the existing dry-run operation:
  the same admitted `RowSet` and immutable plan yield exact ordinal-zero
  non-empty-partition samples and a sorted relative plan-derived tree plus
  `export-receipt.json`. Response v2 is ASCII-safe and bounded through whole-
  row omission. Preview construction does not invoke a renderer or access a
  destination; it adds no persistence, catalog, taxonomy, support, consumer,
  trainer, MCP-operation, or Mac-UI edge. It merged as PR #58 at
  `cd017941090c7352cb1d10f9a383042b954d4f2e`.
- Phase 5.7 changes no architecture edge. Its
  [operator guide](generic-exports.md) documents how to choose an existing
  container without changing the bound objective, row schema, or consumer
  compatibility, and the completed packet reconciles Phase 5 records. It
  merged as PR #59 at `65cbd471e96d83f8dd65e2cda60e90f64a916e2b`.

## Related documentation

- [Product contract](product-contract.md)
- [Integrity Contract v1](contracts/integrity-v1.md)
- [Dataset Construction Contract v1](contracts/dataset-construction-v1.md)
- [Finished Dataset Contract v1](contracts/finished-dataset-v1.md)
- [Deterministic Archive Transport v1](contracts/bundle-transport-v1.md)
- [Generic Export Operator Guide](generic-exports.md)
- [Split JSONL Export v1](contracts/split-jsonl-export-v1.md)
- [Canonical JSON Export v1](contracts/canonical-json-export-v1.md)
- [Constrained CSV Export v1](contracts/constrained-csv-export-v1.md)
- [Verified Export Contract v1](contracts/verified-export-v1.md)
- [Current implementation status](current-status.md)
- [CLI reference](cli.md)
- [Development guide](development.md)
- [Independent product roadmap](plans/2026-08-11-veriformis-independent-product-roadmap.md)
