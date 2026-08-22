# Veriformis

**Local-first dataset compiler: raw documents to validated, provenance-sealed fine-tuning bundles.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![uv-managed](https://img.shields.io/badge/uv-managed-orange.svg)](https://docs.astral.sh/uv/)

Veriformis is a local-first compiler that turns heterogeneous raw source
material into a curated, split, validated, and sealed training dataset. It owns
the difficult path from source capture through the finished bundle. Cleaned
text is an accountable intermediate state, except when a `full_text` recipe
explicitly selects it as training content.

> **Development alpha (`0.1.0`):** M1 core, roadmap Groups 1–7, Group 9
> automated release gates, beta-prep docs, and a **private beta Mac workbench**
> (Phases 0–2: KISS shell and debugger tools over the CLI), plus completed
> independent-product Phases 0–4, plus Phase 5.1–5.2's supported generic
> `split-jsonl-directory` and canonical `json` v1 exports. This is **not** a public
> beta or production
> label. Limits: [docs/beta-limitations.md](docs/beta-limitations.md).
> Install: [docs/install.md](docs/install.md). Status:
> [docs/current-status.md](docs/current-status.md).

## What works today

The active compiler path runs nine stage-gated stages from raw files to a
sealed bundle, verified by a separate command:

```mermaid
flowchart LR
    raw[Raw files] --> parse[parse] --> clean[clean] --> chunk[chunk]
    chunk --> construct[construct] --> curate[curate] --> split[split]
    split --> format[format] --> validate[validate] --> seal[seal]
    seal --> bundle[Sealed .vfbundle] --> verify[verify]
    verify --> package[deterministic .vfbundle.zip] --> packageVerify[package-verify]
```

Version `0.1.0` provides:

- local parsing for plain text, Markdown, DOCX, HTML, digitally-born PDF, CSV,
  JSON, JSONL, and selected source-code files;
- immutable workspace revisions with atomic commits and stale-stage invalidation;
- source-scoped identities for sources, artifacts, transforms, chunks, and revisions;
- strict canonical IR, parser diagnostics, source evidence, and replayable cleaning plans;
- paragraph, fixed, sliding, sentence, and structure-aware chunking;
- five deterministic training objectives: `full_text`, `continuation`,
  `section_reconstruction`, `before_after_transformation`, and
  `structured_field`;
- a versioned six-axis dataset taxonomy, shared compile-compatibility policy,
  and read-only discovery through `PipelineService`, CLI, MCP, and workbench
  help;
- field-level evidence, candidate decisions, optional review evidence, and
  immutable accepted records;
- deterministic curation with target-length filtering, conflict quarantine,
  exact deduplication, optional primary-source caps, and coverage accounting;
- authoritative train and evaluation assignment by complete transitive leakage groups;
- deterministic, externally anchored `.vfbundle.zip` transport that preserves
  the strict six-file canonical bundle without becoming a trainer export;
- a verified `split-jsonl-directory` v1 derivative with canonical train and
  evaluation JSONL, a deterministic README and data card, an export receipt,
  and aligned provenance by default;
- a verified canonical `json` v1 derivative with explicit train/evaluation
  arrays and schema metadata, mandatory aligned provenance, and an export
  receipt;
- one-to-one lowering into `text`, `prompt_completion`,
  `instruction_output`, or structured `messages` rows;
- payload-only partition JSONL plus an aligned provenance stream;
- exact-snapshot validation through 17 ordered gates;
- an atomic six-file `minimal-v1` bundle with closed-set verification; and
- `self_consistent` verification, or `external_digest` verification when the
  caller supplies the manifest SHA-256 retained outside the bundle.

The pipeline makes no LLM calls and sends no document to a network service.

## macOS workbench (private beta)

A SwiftUI adapter lives under [`macos/`](macos/README.md). It **compiles**
sources into a sealed `.vfbundle` and verified Finder-safe `.vfbundle.zip` by
shelling the same `veriformis` CLI as the terminal. It keeps process work off
the main actor, bounds displayed/output retention, supports accountable
cancellation, and records manifest and transport digests in history.

```bash
# From the repo (preferred private-beta launch):
uv sync
./script/build_and_run.sh
```

See [docs/install.md](docs/install.md), [macos/README.md](macos/README.md), and
the [private beta workbench plan](docs/plans/2026-08-06-private-beta-workbench.md).

## Supported inputs

| Category | Extensions |
| --- | --- |
| Text | `.txt` |
| Markdown | `.md`, `.markdown` |
| Word | `.docx` |
| Web | `.html`, `.htm` |
| Digitally-born PDF | `.pdf` (image-only/OCR input fails closed) |
| Structured data | `.csv`, `.json`, `.jsonl` |
| Source code | `.py`, `.js`, `.ts`, `.java`, `.c`, `.cpp`, `.go`, `.rs`, `.rb`, `.sh` |

Other extensions fail with an `unsupported-input` error.

## Install (CLI — standard local path)

Full operator guide: **[docs/install.md](docs/install.md)**.

```bash
git clone https://github.com/ogprotege/Veriformis.git
cd Veriformis
uv sync                         # creates .venv/bin/veriformis
uv run veriformis version       # expect 0.1.0
uv run veriformis --help        # full command list
```

Optional: put the CLI on PATH for this checkout:

```bash
export PATH="$PWD/.venv/bin:$PATH"
veriformis version
```

Mac workbench (Debug, private beta): `./script/build_and_run.sh`
(see [docs/install.md](docs/install.md) and [macos/README.md](macos/README.md)).

### Development / contributor setup

```bash
uv sync --extra test
uv run ruff check src tests
uv run pytest -q --ignore=tests/handoff -m "not aptus_integration"
```

Optional Aptus adapter self-conformance is invoked separately with
`uv run pytest -q -m aptus_integration`.

## Raw source to verified bundle

The GUI runs this same stage sequence. Use at least two independent sources when
you need a non-empty evaluation partition under default split rules:

```bash
uv run veriformis parse source-a.txt source-b.txt -o build/workspace
uv run veriformis clean build/workspace
uv run veriformis chunk build/workspace --strategy paragraph
uv run veriformis construct build/workspace --objective full_text
uv run veriformis curate build/workspace
uv run veriformis split build/workspace
uv run veriformis format build/workspace
uv run veriformis validate build/workspace
uv run veriformis seal build/workspace -o build/example.vfbundle
uv run veriformis verify build/example.vfbundle
```

`seal` prints the manifest SHA-256. Retain it outside the bundle when an
independent trust anchor matters, then verify with:

```bash
uv run veriformis verify build/example.vfbundle \
  --manifest-sha256 EXPECTED_MANIFEST_SHA256
uv run veriformis package build/example.vfbundle \
  -o build/example.vfbundle.zip \
  --manifest-sha256 EXPECTED_MANIFEST_SHA256
uv run veriformis package-verify build/example.vfbundle.zip \
  --manifest-sha256 EXPECTED_MANIFEST_SHA256
```

Without the external digest, verification correctly reports
`self_consistent`. With a matching digest, it reports `external_digest`.

Default `seal` writes only the canonical six-file bundle. Optional consumer
artifacts require an explicit flag or command; for the Aptus adapter, use
`seal ... --aptus-handoff` or `handoff` after sealing. CLI/MCP/workbench startup
and required release gates do not require Aptus.

For a corpus with only one leakage group, the default split cannot create both
partitions. Pass `--allow-empty-evaluation` to `curate` only when an empty
evaluation partition is intentional.

For a supervised recipe, choose its objective and target row schema during
construction. For example:

```bash
uv run veriformis construct build/workspace \
  --objective continuation \
  --target-row-schema messages
```

The later commands infer the row schema from the bound recipe and plan. They do
not accept a second row-schema selector that could contradict it. Only
`instruction_output` requires `curate --instruction TEXT`.

## Finished bundle

A successful Group 3 seal writes exactly:

```text
example.vfbundle/
├── data/train.jsonl
├── data/evaluation.jsonl
├── metadata/row-provenance.jsonl
├── validation.json
├── manifest.json
└── attestation.json
```

The payload files contain only the selected training schema. Provenance remains
in its aligned metadata stream. The co-located attestation proves internal
agreement, not external authenticity. The optional expected manifest digest
provides the external binding.

Group 3 includes the legacy-named `aptus-row-shape` validation gate; despite
its persisted identifier, it validates the implemented generic row shape and
does not prove compatibility with an Aptus release. Group 6 adds an optional
versioned sibling Aptus handoff (`*.aptus-handoff.json`) and
`handoff-verify` consumer checks. Training execution remains outside
Veriformis. The handoff records that its current policy rejects plain `text`
rows; it does not define core dataset correctness or release readiness.

## Workspace integrity

The physical workspace layout remains schema 1. Active revisions use schema 3
and the full stage graph. `HEAD` selects one immutable revision, and that
revision maps logical outputs to content-addressed objects under
`objects/sha256/`.

Use `upgrade-workspace` to migrate a verified revision-v1 or revision-v2
workspace through every supported migration. The v2 to v3 migration preserves
parse, clean, chunk, and construct history. It retires legacy downstream state
instead of reinterpreting chunk projections as finished-dataset evidence.

Persisted artifact JSON and durable identity payloads preserve exact Unicode
strings and object-key sequences. NFC normalization applies only to explicit
locator fields whose contracts define that equivalence, currently logical
source paths.

## Current boundary

On `main` today: **Groups 1–7**, **Group 9 automated gates**, **beta-prep**,
**private beta workbench Phases 0–2**, **independent-product Phases 0–4**, and
**independent-product Phase 5.1–5.2**.
The completed Phase 4 verified-export foundation adds a
typed internal `ExportService` boundary and descriptor-anchored inspection of
an already verified finished bundle. Its second slice defines strict,
versioned export plan, profile, membership, file-binding, receipt, and
verification models. Its third slice enforces trusted-by-default export-source
admission and explicit lower self-consistent trust. Its fourth slice adds
read-only `create_plan`: source identities and the complete source membership
baseline are derived from one admitted bundle view, while callers provide only
strict profile, dependency, and file-plan evidence. Its fifth slice fresh-
reconstructs normalized candidate semantic rows and provenance and requires
their row-set and complete membership projection to match that baseline. The
sixth slice adds internal exact-byte atomic publication and independent closed-
tree verification. The seventh adds private two-
render conformance: exact profiles require identical
normalized byte trees, while semantic-only profiles require equal versioned
canonical semantic preimages, complete reconstructed membership, service-
computed digests, and descriptor-reread staged replay. Phase 4.8 adds strict
discovery, dry-run, inspect, execute, and source-bound verify operations through
`PipelineService`, CLI, MCP, and a CLI-backed Mac bridge; it merged as PR #50 at
`fb0a13d7cab1e456b6ff3b3dc6ebab13b9898edb`, with review corrections in PR #51
at `d91542fe12c5a492de578ad060836a7d65999e42`. Phase 4.9 completes the
adversarial harness and closeout reconciliation.
That empty catalog is a completed Phase 4 fact. Phase 5.1–5.2 install two
production exact-byte renderers: `split-jsonl-directory` v1 and canonical
`json` v1, both with no consumer profile or trainer-compatibility claim.
Historical request v1 remains unchanged: it selects split JSONL's `train` /
`evaluation` filenames with aligned provenance and the canonical JSON fixed
tree. Request v2 applies only to split JSONL and requires the complete
`veriformis.split-jsonl-options/v1` object to change those safe filename stems
or omit provenance; canonical JSON refuses configured requests. No request
changes source rows, ordering, partition membership, curation, or split policy.
The ten persisted verified-export v1 schemas, discovery v1, response v1, and
existing `ExportService.publish` call signature remain unchanged. CSV and
every new trainer-specific profile remain later Phase 5 work.
Maturity remains development **alpha** (not a
public beta label). A future beta cut must follow
[docs/beta-limitations.md](docs/beta-limitations.md). **Public Mac app** claims
need owner signing/notarization per [docs/release.md](docs/release.md).
**Group 8** model-assisted construction is optional and owner-gated.

## Documentation

The [documentation index](docs/README.md) defines document authority and
reading paths. The map:

- **Product and status**
  - [Product contract](docs/product-contract.md) — ownership boundary and non-claims
  - [Current implementation status](docs/current-status.md) — exact alpha boundary
  - [Work in progress](WIP.md) — non-authoritative tracker
- **Architecture**
  - [Architecture hub](docs/architecture.md)
  - [Architecture tree](docs/architecture/README.md)
- **Contracts**
  - [Integrity Contract v1](docs/contracts/integrity-v1.md)
  - [Dataset Construction Contract v1](docs/contracts/dataset-construction-v1.md)
  - [Finished Dataset Contract v1](docs/contracts/finished-dataset-v1.md)
  - [Dataset Taxonomy Contract v1](docs/contracts/taxonomy-v1.md)
  - [Verified Export Contract v1](docs/contracts/verified-export-v1.md)
  - [Split JSONL Export Contract v1](docs/contracts/split-jsonl-export-v1.md)
  - [Canonical JSON Export Contract v1](docs/contracts/canonical-json-export-v1.md)
  - [Aptus Handoff Contract v1](docs/contracts/aptus-handoff-v1.md)
- **Reference and plans**
  - [Install guide](docs/install.md)
  - [CLI reference](docs/cli.md)
  - [Development guide](docs/development.md)
  - [Release guide](docs/release.md)
  - [Beta limitations](docs/beta-limitations.md)
  - [macOS workbench](macos/README.md)
  - [Independent product analysis](docs/analysis/2026-08-11-independent-product-analysis.md)
  - [Authoritative independent product roadmap](docs/plans/2026-08-11-veriformis-independent-product-roadmap.md)
  - [Project tracking and evidence system](docs/governance/README.md)
  - [Completed Phase 0 packet](dev/active/independent-product/phase-00-foundation/README.md)
  - [Completed Phase 1 packet](dev/active/independent-product/phase-01-standalone-independence/README.md)
  - [Completed Phase 2 packet](dev/active/independent-product/phase-02-reliability-artifact-boundary/README.md)
  - [Completed Phase 3 packet](dev/active/independent-product/phase-03-taxonomy/README.md)
  - [Completed Phase 4 packet](dev/active/independent-product/phase-04-verified-export-foundation/README.md)
  - [Active Phase 5 packet](dev/active/independent-product/phase-05-generic-local-exports/README.md)
  - [Historical private beta workbench plan](docs/plans/2026-08-06-private-beta-workbench.md)
  - [Historical build roadmap](docs/plans/2026-07-29-veriformis-roadmap.md)
  - [Contributing](CONTRIBUTING.md)

## Development checks

```bash
uv lock --check
uv run ruff check src tests
uv run pytest -q --ignore=tests/handoff -m "not aptus_integration"
git diff --check
```

CI on `main` runs a Python 3.11–3.13 matrix (Ubuntu) plus Python 3.12 on
macOS, `uv lock --check`, Ruff, core pytest, clean-wheel installed-CLI smoke,
and standalone golden-corpus compile. Aptus adapter checks are separate and
non-blocking. Local totals grow over time — re-run the commands for current
counts. Type-check, coverage thresholds, dependency audit, and signed/notarized
Mac distribution are not automated release claims; see
[docs/release.md](docs/release.md) and
[docs/beta-limitations.md](docs/beta-limitations.md).

## License

Veriformis is provided under the [MIT License](LICENSE).
