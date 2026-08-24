# Current Implementation Status

**Product version:** `0.1.0`

**Maturity:** Development alpha

**Implementation state:** Groups 1–7 complete; Group 9 automated release gates
and beta-prep on `main`; private beta Mac workbench Phases 0–2 on `main`
(maturity remains development alpha; public Mac readiness still owner-gated);
independent-product Phase 3 completed with taxonomy discovery, public
vocabulary cleanup, and persisted-v1 compatibility proof;
independent-product Phase 4 verified export foundation completed with its
typed internal service boundary, descriptor-anchored source view, and strict
versioned persisted export models, plus trusted-by-default source admission
with explicit lower-trust policy, read-only source-derived plan population, and
normalized semantic membership enforcement, internal exact-byte atomic
publication and independent closed-tree verification, private two-render
exact-byte and semantic-content conformance with staged descriptor replay, and
strict initially production-empty export surfaces through Python, CLI, MCP,
and Mac, plus the consolidated adversarial closeout harness; independent-
product Phase 5.1–5.3 implement and admit `split-jsonl-directory`, canonical
`json`, and `constrained-csv` v1 as the first three production generic
exports, without a consumer or trainer profile; independent-product Phase 5.4's
optional receipt-anchored deterministic `.vfexport.zip` post-export transport
merged as PR #56 without adding a fourth renderer, MCP operation, or Mac UI
action; Phase 5.5's test-only consolidated semantic round-trip evidence merged
as PR #57 at `c72b8e9ec7bc2746d74404226aa086d497e15db1`; Phase 5.6's exact bounded
dry-run preview merged as PR #58 at
`cd017941090c7352cb1d10f9a383042b954d4f2e`; and Phase 5.7 publishes the
generic-export operator guide and completes Phase 5 reconciliation without a
runtime, taxonomy, support, consumer-profile, or trainer claim change, merged
as PR #59 at `65cbd471e96d83f8dd65e2cda60e90f64a916e2b`;
independent-product Phase 6 complete, with items 6.1–6.7 merged sequentially
as PR #60 through PR #65 and PR #67 at
`6995d17bef0d09f235b1c464e947c38c63dd313d`; independent-product Phase 7 is
complete (existing-dataset import and mapping). Items 7.1–7.10 merged as PR
#71 through PR #80 at `b7bb7f0c2046fba87fd7c9da12f7d2ccb5c2c88f` after all
14 GitHub checks passed. Phase 8 consumer profiles are complete: TRL SFT and
MLX-LM LoRA are implemented optional adapters with official-schema harnesses
and dataset-only launch sidecars. The exporter does not launch training.
Phase 9 columnar containers are complete: Parquet v1, Arrow IPC v1, and
local Hugging Face DatasetDict v1 are implemented `semantic_content_only`
generic exports with semantic fingerprints, library-reload harnesses, and
dataset-row mapping for Parquet and Arrow. Suffix does not switch modes.
Extra `columnar` stays empty. There is no Hub upload.

**Review date:** 2026-08-24 (independent-product Phase 9 closeout)

**Next review:** Beta label cut, public-ready checklist, or any contract
change. Do not start Phase 10 or 13 from this packet.

This document is the current source of truth for implemented `0.1.0`
capability claims.

## Executive status

Veriformis is a local-first, offline dataset compiler from supported raw
sources to a closed, independently verifiable training-dataset bundle:

```text
document-source (default):
parse -> clean -> chunk -> construct -> curate -> split
      -> format -> validate -> seal -> verify -> package -> package-verify

dataset-row (opt-in):
parse --mode dataset-row -> map -> curate -> split
      -> format -> validate -> seal -> verify -> package -> package-verify
```

**Groups 1–3** deliver integrity, construction, and the finished-dataset
lifecycle (curation, leakage-safe split, product rows, 17-gate validation,
atomic six-file seal, independent verification).

**Group 4** delivers the typed `PipelineService` composition root, thin CLI
adapter, and dual-objective M1.1 API/CLI acceptance.

**Group 5** expands declared ingest (HTML, digitally-born PDF, CSV, JSON,
JSONL), named OCR refusal, the recipe library, statistics, and YAML pipelines.

**Group 6** adds the constrained local MCP adapter and versioned Aptus handoff
v1 with fail-closed consumer verification.

**Group 7** adds the SwiftUI workbench under `macos/`, a thin shell over the
same CLI so digests match terminal runs. **Private beta workbench Phases 0–2**
extend that surface: dogfood punch list; KISS sidebar (Home / Compile /
History / Settings); run sheet with progress % and live log; history
persistence; settings for CLI and default output; failure details; digest copy;
artifact reveal; and rerun. Independent-product Phase 2 adds asynchronous
bounded process execution, accountable cancellation and quit recovery, and an
externally verified deterministic transport archive. Launch with
`./script/build_and_run.sh`. Operator install:
[install.md](install.md). Vision/plan:
[plans/2026-08-06-private-beta-workbench.md](plans/2026-08-06-private-beta-workbench.md).

**Group 9 (automated subset)** expands CI to a Python 3.11–3.13 matrix plus
macOS Python 3.12, lockfile check, wheel install smoke, golden-corpus compile,
release scripts under `scripts/release/`, and [docs/release.md](release.md).
Independent-product Phase 1 makes those required gates standalone: installed
wheel origin, both objectives, default canonical seal, and
`external_digest` verification. Aptus adapter self-conformance runs as a
separate non-blocking job.
**Beta-prep** on `main` adds [beta-limitations.md](beta-limitations.md) and
retained clean-path evidence under
`dev/active/group-9-public-release/evidence/`. Maturity remains **alpha** until
a deliberate beta label cut. Signed and notarized Mac distribution remains an
owner-executed checklist for any public Mac app claim.

The historical Group 9 handoff coupling is no longer the product boundary.
Aptus is an optional consumer integration: CLI, MCP, and workbench defaults do
not write its sibling, and required release gates do not invoke its adapter.

Raw source material remains the product entry. Clean corpus state is an
accountable intermediate, except when a `full_text` recipe explicitly selects
the retained text as its target.

Green automated gates do **not** alone claim beta or public release readiness.
Non-claims and operator limits live in [beta-limitations.md](beta-limitations.md).
A public-ready claim still requires the full checklist in
[docs/release.md](release.md), including owner Mac signing, notarization,
clean-Mac install, and recorded evidence when shipping a Mac app.

## Independent-program tracking

Phase 0 of the independent product roadmap is `completed`. It delivered the
tracking and claim-control foundation:

- `dev/active/independent-product/program.json` records every Phase 0–20 state,
  dependency, packet, and next gate;
- `docs/governance/support-registry.json` records current, planned, candidate,
  and explicitly unsupported capabilities;
- `docs/evidence/index.json` distinguishes source, test, local-run, retained,
  external-primary, and planned evidence;
- the completed Phase 0 packet records the checklist, append-only progress,
  decisions, risks, evidence, and closeout; and
- `scripts/check_project_tracking.py`, exercised by pytest, compares the
  roadmap, program ledger, WIP table, support registry, package/parser/recipe/
  row/bundle constants, all three handoff defaults, and adapter import
  isolation.

The phase also delivered accepted product-boundary ADRs, a privacy-preserving
corpus/workflow-demand matrix, and semantic reconciliation of active
architecture, contracts, status, release-boundary, and workbench documents.
Tracked fixture counts are reproducible; the local retained-output observation
is explicitly non-portable. Representative owner-corpus composition, trainer
frequency, exact container demand, and scale targets remain evidence gaps and
are not replaced with ecosystem assumptions. The completed packet records the
final gates and limitations. Phase 1 completed standalone runtime and release
defaults. Its completed packet pins default artifact absence,
adapter import isolation, clean installed-wheel compilation, neutral release
evidence, and workbench operation as measured acceptance gates.
Phase 2 completed the reliability and artifact-boundary gate. Its packet records
bounded asynchronous process execution, accountable cancellation and quit
recovery, deterministic no-replace transport packaging, archive re-verification,
and standalone Mac and Linux evidence.
The pre-Phase-3 defect-closure packet and Phase 3 are completed on `main`.
Phase 3 delivered the versioned taxonomy contract, shared
compile-compatibility checks, and read-only discovery through
`PipelineService`, CLI, MCP, and CLI-backed workbench help. Ambiguous public
taxonomy wording is reconciled without changing persisted stage IDs; the
taxonomy golden and persisted-v1 workspace/bundle compatibility proofs pass.
Phase 4, verified export foundation, is complete. Its opening slice adds a
typed internal `ExportService`, owned by `PipelineService`, and a
descriptor-anchored verified source view that returns the already checked
manifest, validation report, row set, and verification result from one pass.
Its second slice defines strict v1 plan, profile, dependency, membership,
file-binding, receipt, and verification models with canonical identity replay.
Its third slice makes export-source admission require a retained manifest
digest by default and permits self-consistent trust only through an explicit
lower-trust policy. Its fourth slice adds read-only plan population. It derives
all source identities, the one objective, source scope, and the complete source
membership baseline from the immutable verified view; callers provide only
strict profile, dependency, and output-file planning evidence. Its fifth slice
fresh-reconstructs normalized candidate semantic rows and provenance, requires
the exact planned row-set identity, and compares the complete candidate
membership projection with the source baseline. Items 4.1–4.5 are merged at
`1675c1a22830d506bdf27e45150170befc984bdf`. Its sixth slice implements a
Python-composition-only `portable_exact_bytes` publisher. It re-verifies the
source and complete plan, checks the renderer's normalized semantic membership
and exact bytes, writes a canonical receipt in private descriptor-anchored
staging, independently verifies the closed tree, and performs one atomic
no-replace promotion with explicit cancellation and visible-outcome reporting;
it merged as PR #48 at
`3da0a7f4f8243a1e3a7390e6969c2ee67d7c65af`. The seventh slice invokes
the private conformance renderer twice from independent strict plan and row-set
reloads. Exact profiles require identical normalized byte trees. Semantic-only
profiles permit different physical bytes but require equal profile-versioned
canonical semantic preimages, complete plan-equal reconstructed membership,
service-computed digests, and descriptor-reread staged replay before promotion.
It merged as PR #49 at `6c3f0aff2e35edaa7920a0964270c410bf53f47b`. The eighth
slice adds a private, immutable, production-empty implementation
catalog and typed discovery, destination-free dry run, self-described inspect,
operator-confirmed no-replace execute, and source-bound verify operations.
`PipelineService`, CLI, MCP, and the CLI-backed Mac bridge share one strict
canonical protocol and frozen evidence fixture. The default service has no
renderer or semantic replayer. Python publicly exports only the cancellation
callback, runtime publication outcome, and visible-partial exception needed to
use execution honestly; publication hooks remain private. The eighth slice
merged as PR #50 at `fb0a13d7cab1e456b6ff3b3dc6ebab13b9898edb`, with review
corrections in PR #51 at `d91542fe12c5a492de578ad060836a7d65999e42`. The ninth
slice consolidates contract, tamper, path, link, source-trust, complete
membership-mutation, race, cancellation, and visible-partial closeout evidence.
The ten v1 schemas record the
profile claim and one published instance, not a rerender transcript. Generic
export containers and planned trainer-specific profiles remain unimplemented.

That last statement records the Phase 4 exit boundary. Phase 5.1 now ships one
production implementation: `split-jsonl-directory` version 1, exact-byte
deterministic, with all four current row schemas, no consumer profile, and no
trainer-compatibility claim. Its default closed tree is:

```text
README.md
data/evaluation.jsonl
data/train.jsonl
export-receipt.json
metadata/dataset-card.json
metadata/row-provenance.jsonl
```

Historical request v1 remains exact and selects `train` and `evaluation`
partition filenames with aligned provenance included. Configured dry run,
execute, and source-bound verify use additive request v2 and must carry the
complete canonical `veriformis.split-jsonl-options/v1` object; it can change
only the two safe filename stems and whether provenance is included. Omitting
provenance removes only `metadata/row-provenance.jsonl`. The exported payload
rows, order, objective, curation result, split assignment, and authoritative
train/evaluation membership remain unchanged.

Phase 5.2 adds canonical `json` version 1 with the same exact-byte, all-schema,
consumer-neutral boundary. Its fixed closed tree is:

```text
README.md
dataset.json
export-receipt.json
metadata/row-provenance.json
```

`dataset.json` carries explicit schema, objective, loss-policy, row-set,
split-result, partition-order, and row-count metadata plus payload-only
`train` and `evaluation` arrays. The separate mandatory provenance object
contains the complete train-then-evaluation Finished Dataset v1 sequence.
`dataset.json` alone bears complete membership scope. Canonical JSON uses
historical request v1 and has no options; configured request v2 fails before
source or destination access. Item 5.2 merged as PR #54 at
`f6a5d45f01e0b3117c259271bc59f3599a89dbb6`.

Phase 5.3, merged as PR #55, adds `constrained-csv` version 1 for the flat `text`,
`prompt_completion`, and `instruction_output` row schemas. Its fixed tree is:

```text
README.md
data/evaluation.csv
data/train.csv
export-receipt.json
metadata/dataset-card.json
metadata/row-provenance.jsonl
```

The codec is UTF-8 without a BOM, quotes every header and field, doubles
embedded quotes, uses commas and LF records with a final LF, and preserves
embedded line endings and exact Unicode inside fields. Ordered headers are
frozen per schema. Provenance is mandatory and aligned train then evaluation.
Historical request v1 selects the fixed tree; configured request v2 fails
before source or destination access. Nested `messages` is refused with a split
JSONL or canonical JSON alternative. The derivative changes no row or logical
partition and claims neither trainer nor spreadsheet compatibility. All new
trainer-specific profiles remain unimplemented.

Phase 5.4's `deterministic-export-pack-zip-v1` transport merged as PR #56 at
`499d61fa2e7dd12edb5808c6bd9d0e0ab6b738c8`. It remains an optional
receipt-anchored post-export wrapper around one unchanged published directory,
not a fourth semantic renderer or a source-bound verification path.

Phase 5.5 merged as PR #57 at
`c72b8e9ec7bc2746d74404226aa086d497e15db1`. One frozen
ordinary-file fixture closes the discovery-derived matrix at eleven compatible
container/schema pairs: all four current rows for split JSONL and canonical
JSON, and the three flat rows for constrained CSV. Every pairing reloads the
identical ordered train and evaluation payloads, complete provenance, and
source `RowSet`; one canonical semantic tamper per container fails, and the
twelfth current pairing retains constrained CSV's actionable pre-publication
`messages` refusal. This adds no product importer, semantic replayer, API,
taxonomy or support promotion, trainer claim, or new runtime behavior.

Phase 5.6 adds one runtime-only exact preview to the existing dry-run
operation. Dry-run response v2 contains exactly the unchanged plan summary and
a preview: ordinal zero from each non-empty partition in train-then-evaluation
order, exact payload digest and UTF-8 JSON byte size, and the sorted relative
plan-derived destination tree plus `export-receipt.json`. Payloads above
65,536 bytes or unable to fit the 256 KiB response are omitted whole with a
closed reason, never truncated. ASCII-safe wire JSON decodes to exact source
values. Preview construction invokes no renderer and accesses no destination.
The ten persisted export models, request v1/v2, discovery v1, production
selectors, taxonomy, and support state remain unchanged; response v1 remains
exact for non-dry-run operations. Item 5.6 passed all 14 GitHub checks and
merged as PR #58 at `cd017941090c7352cb1d10f9a383042b954d4f2e`.

Phase 5.7 adds the [generic export operator guide](generic-exports.md). It
explains when to choose split JSONL, canonical JSON, or constrained CSV while
keeping the already-bound training objective and row schema separate from
physical container and consumer compatibility. It adds no runtime operation,
importer, renderer, persisted schema, taxonomy entry, support promotion,
consumer profile, or trainer claim. With that guidance and the reconciled
packet/evidence/governance records, independent-product Phase 5 is complete.
Item 5.7 merged as PR #59 at `65cbd471e96d83f8dd65e2cda60e90f64a916e2b`.

Phase 6.1 adds the packaged `veriformis.goal-catalog/v1` data: five
plain-language goals bound one-to-one to the existing objectives and named
recipes, and four representations bound to the existing row schemas and loss
policies, discoverable read-only and byte-identically through Python, CLI
`goals`, MCP `goals`, and the Mac bridge. It merged as PR #60 at
`7316d94faf2d6c23b7abb6fe200f154da47d398c` after all 14 GitHub checks
passed. Phase 6.2 extends each goal with required source evidence, its
missing-evidence diagnostics, target construction, supervision boundary,
curation defaults, review policy, and closed non-claims; binds each
representation to its compatible generic exports; and adds `input_family`
as the seventh taxonomy axis (eight implemented recovery families plus
`ocr-image` explicitly unsupported) under ADR-0008; it merged as PR #61 at
`81becfa676fd9111868b8d4b62549218a644d3e2` after all 14 GitHub checks passed.
Phase 6.3 adds the runtime-only
`veriformis.goal-preview/v1` response through `PipelineService.preview_goal`,
CLI `goal-preview`, MCP `goal_preview`, the Swift bridge, and a workbench
preview screen: per accepted record, the exact recovered source evidence and
derivation lineage, context and target fields, the row exactly as `format`
lowers it, the exact supervised span with its loss policy, and the curation
decision and excluded records with reason codes, bounded like the Phase 5.6
export preview; it merged as PR #62 at
`9cbab117e47cde6bd8850d67f0d363e03f0660ce`. Phase 6.4 adds
`veriformis.recipe-preset/v1`: packaged versioned data that is
the single source of every recipe default and of one safe preset per goal;
`chunk`, `construct`, and `curate` on Python, CLI, MCP, and YAML select by
`--goal`/`--preset` with explicit overrides only, the recipe library is on the
execution path so every selection yields one `recipe_id`, the workbench offers
a plain-language goal picker with an Advanced disclosure and holds no recipe
constant, and the tracking checker refuses recipe default literals; it merged
as PR #63 at `abdd630e25e83ebf346316319caec892f4d64886`. Phase 6.5 adds the
bounded runtime-only `veriformis.compile-preflight/v1` response over raw source
paths: one immutable capture is replayed through the production parser,
selected cleaning, segmentation, named construction, global curation, and
leakage-group split entirely in memory. Python, CLI, MCP, and the Mac panel
share the exact report, and real construction shares its goal/input-family
gate. No workspace, renderer, or destination is created or accessed; it merged
as PR #64 at `b2e28b3dcfe48cd28ec74d8d8eaed12049f72d2d`. Phase 6.6 freezes
the discovery-closed 74-cell raw-source-to-verified-bundle matrix: Python,
CLI, MCP, YAML, and the real Mac CLI bridge agree on recipe, row-set,
manifest, supervision, and exact exclusion identities through seal and
external-digest verify; it merged as PR #65 at
`7b93a32a5a9b18e5bc9c032750f467c4d9c43ea5`. Phase 6.7 adds per-goal
instruction templates as the only default instruction literals, admits an
operator instruction only after a deterministic truthfulness check, proves
`messages` user turns are exact context, judges usability criteria U1–U6,
and writes the Phase 6 closeout; it merged as PR #67 at
`6995d17bef0d09f235b1c464e947c38c63dd313d` after all 14 GitHub checks
passed. Independent-product Phase 6 is complete. Independent-product Phase 7 is
complete: existing JSONL, JSON, and compatible CSV rows import under
confirmed mapping plans, seal through ordinary `ProductRow` v1, and use the
same generic exports. None of these items adds an objective, row schema,
persisted schema, trainer claim, or consumer profile.

## Implemented interfaces

The installed console entry point is `veriformis`.

| Command | Implemented behavior | Revision outputs or external result |
| --- | --- | --- |
| `parse paths... -o WORKSPACE` | Captures raw bytes and parses supported paths in one transaction | `registry`; per-source `raw`, `canonical`, `document`, and `diagnostics` |
| `clean WORKSPACE` | Plans, replays, and commits deterministic cleaning for every source | `transforms`; per-source `document`, `cleaning-plan`, and `block-derivations` |
| `chunk WORKSPACE` | Runs one of five evidence-bearing chunk strategies | `chunks` |
| `upgrade-workspace WORKSPACE` | Migrates a verified revision-v1 or revision-v2 workspace through every supported migration | One new migration revision per required schema step, or no change when current |
| `construct WORKSPACE (--goal GOAL \| --preset PRESET \| --objective OBJECTIVE)` | Resolves the selection and explicit overrides through the versioned preset data, builds the recipe through the named recipe library, and constructs candidates, decisions, diagnostics, and immutable accepted records for one exact source set | `recipe`, `result` |
| `parse PATH... -o WORKSPACE --mode dataset-row` | Captures UTF-8 JSONL, JSON, compatible CSV, Parquet, or Arrow IPC row sources into workspace revision v4; does not recover document IR; suffix does not switch document-source | `registry`, per-source `raw` and `row-source` |
| `map WORKSPACE --goal GOAL --representation REPRESENTATION --plan PLAN.json` | Applies a confirmed mapping-plan/v1 to captured objects and commits imported records with `mapped_value` evidence | `plan`, `recipe`, `result` |
| `curate WORKSPACE` | Fixes the complete finished plan and applies ordered deterministic curation | `plan`, `result` |
| `split WORKSPACE` | Assigns complete transitive leakage groups to train and evaluation | `result` |
| `format WORKSPACE` | Lowers included records into the row schema bound by the plan | `row-set`, `train`, `evaluation`, `provenance` |
| `validate WORKSPACE` | Replays all semantics and validates one exact byte snapshot through 17 gates | `snapshot`, `report` |
| `seal WORKSPACE -o BUNDLE` | Revalidates, atomically publishes, independently verifies, and receipts a finished bundle; writes only the canonical bundle by default | External six-file bundle; `manifest`, `attestation`; optional explicit `*.aptus-handoff.json` |
| `verify BUNDLE` | Verifies the closed bundle without workspace access | Terminal verification result |
| `package BUNDLE -o ARCHIVE --manifest-sha256 DIGEST` | Externally verifies and deterministically publishes the canonical six-file bundle as a no-replace transport archive | `*.vfbundle.zip`; archive and manifest digests |
| `package EXPORT -o ARCHIVE --export-receipt-sha256 DIGEST` | Descriptor-inspects one closed generic export and deterministically publishes its externally receipt-anchored tree without rerendering | `*.vfexport.zip`; archive, receipt, plan, content-root, and retained source-trust facts |
| `package-verify ARCHIVE --export-receipt-sha256 DIGEST` | Reconstructs only receipt-validated export paths, verifies the unchanged inner plan/receipt/file bindings, and proves canonical archive bytes | Receipt-anchored transport result; not source-bound export verification |
| `package-verify ARCHIVE --manifest-sha256 DIGEST` | Reconstructs and externally verifies the canonical bundle, then proves canonical archive bytes | Terminal verification result |
| `taxonomy` | Prints the implemented training family, objective, semantic-row, physical-container, consumer-profile, loss-policy, and input-family registry as JSON | Read-only terminal output |
| `goals` | Prints the packaged plain-language goal catalog (`veriformis.goal-catalog/v1`): five goals bound one-to-one to the existing objectives and named recipes, four representations bound to the existing row schemas and loss policies | Read-only terminal output, byte-identical to MCP `goals` and the packaged data |
| `presets` | Prints the packaged recipe presets and recipe-wide defaults (`veriformis.recipe-preset/v1`) that every surface executes | Read-only terminal output, byte-identical to MCP `presets` and the packaged data |
| `modes` | Prints compiler-path input modes (`veriformis.input-mode-discovery/v1`): `document-source`, `dataset-row`, and `mixed` executable. Mixed parse of documents and JSONL together refuses so construction and imported-row provenance stay distinct. | Read-only terminal output, byte-identical to MCP `modes` and the packaged data |
| `mapping-contracts` | Prints row-mapping contract discovery (`veriformis.mapping-contract-discovery/v1`) | Read-only terminal output, byte-identical to MCP `mapping_contracts` |
| `profile-admissions` | Prints implemented TRL and MLX-LM admission pins (`veriformis.profile-admission-discovery/v1`) | Read-only terminal output, byte-identical to MCP `profile_admissions`; does not launch training |
| `columnar-schemas` | Prints packaged Arrow and Hugging Face feature pins (`veriformis.columnar-schema-discovery/v1`) | Read-only terminal output, byte-identical to MCP `columnar_schemas`; does not emit files or import PyArrow |
| `mapping-templates` | Prints packaged mapping templates (`veriformis.mapping-template-discovery/v1`) | Read-only terminal output, byte-identical to MCP `mapping_templates` |
| `mapping-detect PATH` | Proposes mapping-plan/v1 objects for one JSONL, JSON, compatible CSV, Parquet, or Arrow file, including a confirmation digest; never writes a workspace | Runtime-only `veriformis.mapping-detect/v1` JSON; exit `2` when no detector matches |
| `mapping-preview PATH --plan PLAN.json` | Walks the full captured file and reports per-row accept/reject samples without writing a workspace | Runtime-only `veriformis.mapping-preview/v1` JSON; 64 KiB sample / 256 KiB response bounds |
| `mapping-rejections PATH --plan PLAN.json --output DIR` | Writes a content-addressed mapping rejection report beside a directory; `map` also writes one beside the workspace | `veriformis.mapping-rejection-report/v1` JSON; not a verified export |
| `preflight PATH...` | Resolves a goal/preset/representation and explicit overrides, captures every regular source once, and predicts parser/family eligibility, construction evidence, curation exclusions and coverage, and required splitting | Bounded runtime-only `veriformis.compile-preflight/v1` JSON; exit `0` when admitted or `2` for a complete negative verdict; no workspace write |
| `goal-preview WORKSPACE` | Shows, per accepted record, the recovered source evidence, context and target, the row exactly as `format` lowers it, the exact supervised span and loss policy, and curation decisions with reason codes; bounded and ASCII-safe | Runtime-only `veriformis.goal-preview/v1` JSON; no workspace write |
| `export discover` | Lists executable verified-export implementations from the private service catalog | Canonical discovery response containing `arrow`, `constrained-csv`, `hugging-face-dataset`, `json`, `parquet`, `split-jsonl-directory` v1, and TRL / MLX-LM adapters |
| `export dry-run --request-json JSON` | Verifies the selected source and derives the exact export plan plus ordinal-zero non-empty-partition samples and normalized plan-derived tree without renderer or destination access; request v1 selects all three containers, while request v2 configures only split JSONL | Canonical response v2 with result exactly `plan` and runtime-only `preview` |
| `export inspect --request-json JSON` | Checks a destination's self-described receipt and closed physical tree without asserting source authority | Canonical `self_described_physical` response |
| `export execute --request-json JSON` | Re-derives and atomically publishes the operator-confirmed no-replace plan | Canonical receipt and verification response, or explicit cancellation/visible-partial status |
| `export-verify --request-json JSON` | Re-verifies source authority, re-derives the confirmed plan, and independently verifies the destination | Canonical source-bound verification response |
| `preview PATH` | Plans and replays cleaning without writes | Terminal output only |
| `run PIPELINE.yaml` | Executes a versioned YAML pipeline through `PipelineService` | Workspace stages and optional sealed bundle |
| `list-recipes` | Lists named deterministic recipe library identifiers | Terminal output only |
| `mcp` | Runs the constrained local MCP adapter on stdio | MCP tool surface over `PipelineService` |
| `handoff BUNDLE --manifest-sha256 DIGEST` | Builds the versioned Aptus handoff sibling descriptor | `*.aptus-handoff.json` |
| `handoff-verify HANDOFF --bundle BUNDLE` | Fail-closed consumer check of handoff against sealed bundle | Terminal verification result |
| `version` | Prints the package version | Terminal output only |

Surfaces over the same composition root:

| Surface | Location | Role |
| --- | --- | --- |
| Python API | `veriformis.pipeline.PipelineService` | Typed stage orchestration, read-only taxonomy, goal-catalog, implemented profile-admission, and columnar-schema discovery, raw-source compile preflight, read-only goal preview, and verified-export discovery/dry-run/inspect/execute/verify operations |
| CLI | `veriformis` / `veriformis.cli` | Thin Typer adapter, including taxonomy, goal-catalog, implemented profile-admission, and columnar-schema JSON, compile preflight, and canonical verified-export responses |
| Recipes / YAML | `veriformis.recipes` | Named recipes, statistics, pipeline runner |
| MCP | `veriformis.mcp` / `veriformis mcp` | Constrained local automation over the same taxonomy, goal-catalog, implemented profile-admission, columnar-schema, compile-preflight, and verified-export service operations |
| Optional Aptus adapter | `veriformis.handoff` | Explicit sibling descriptor + consumer verify; not imported by default seal surfaces |
| macOS workbench | `macos/` | SwiftUI thin CLI adapter with bounded async execution, accountable cancellation, verified transport output, CLI-backed taxonomy help, strict goal-catalog, pre-workspace compile-preflight, and post-compile goal-preview screens, and a strict canonical verified-export bridge |

## Workspace and identity status

The physical workspace layout remains schema 1. Active workspaces use revision
schema 3 and contain `workspace.json`, `HEAD`, `LOCK`, immutable revision
manifests, content-addressed objects, and a transaction directory. `HEAD`
selects the current revision. A successful stage becomes visible through one
atomic pointer replacement.

Revision schema 3 uses these stages and direct dependencies:

| Stage | Direct dependencies |
| --- | --- |
| `parse` | none |
| `clean` | `parse` |
| `chunk` | `clean` |
| `construct` | `parse`, `clean`, `chunk` |
| `curate` | `construct` |
| `split` | `construct`, `curate` |
| `format` | `construct`, `curate`, `split` |
| `validate` | `parse`, `clean`, `chunk`, `construct`, `curate`, `split`, `format` |
| `seal` | `parse`, `clean`, `chunk`, `construct`, `curate`, `split`, `format`, `validate` |

Rerunning a stage invalidates every descendant. Older states remain available
only through immutable historical revisions. Group 3 stage configurations and
artifacts bind the same `plan_id`.

Opening a workspace verifies the complete parent chain and every referenced
object digest. Commits check an expected parent revision under an exclusive
lock. A stale writer fails with `workspace-revision-conflict`. If `HEAD`
becomes visible but final directory sync fails, the command reports the visible
commit with `warning[commit-durability]` instead of claiming rollback.

`upgrade-workspace` supports revision v1 to v2 and v2 to v3. The v2 to v3
migration preserves verified parse, clean, chunk, and construct state. It adds
absent curate and split stages and resets legacy format, validate, and seal
state to absent. Historical objects and revisions remain intact. Legacy chunk
rows and saved gate flags never become Group 3 evidence.

Source IDs bind normalized logical paths and raw digests. Artifact IDs also
bind content, producer, configuration, and source scope. Cleaning, evidence,
chunks, construction, curation, splitting, rows, validation, and bundle values
use deterministic domain-separated identities. Same-basename sources and
distinct logical sources with identical bytes remain distinct.

Persisted artifact JSON and durable identity payloads preserve exact Unicode
strings and key sequences. NFC normalization applies only to locator fields
whose contract defines it, currently logical source paths. Revision IDs remain
audit identities that can differ across equivalent histories. Portable state
and artifact identities carry semantic reproducibility.

## Supported inputs and recovery

| Input | Current behavior |
| --- | --- |
| `.txt` | UTF-8 blank-line paragraph parsing with canonical-stream spans and separator-normalization diagnostics |
| `.md`, `.markdown` | Markdown parsing into canonical IR with located diagnostics for HTML, Pandoc metadata, and unsupported tokens |
| `.docx` | Body and note parsing with OOXML-located diagnostics for unsupported constructs, normalization, unresolved notes, and unavailable page provenance |
| `.html`, `.htm` | Deterministic `lxml` body extraction; scripts/styles omitted with diagnostics |
| `.pdf` | Digitally-born PDF text-layer extraction via `pypdfium2`; page headings; empty text layer refuses with named OCR limitation |
| `.csv` | UTF-8 rectangular table recovery with fixed excel dialect and explicit padding diagnostics |
| `.json`, `.jsonl` | UTF-8 structured path projection into evidence-bearing paragraphs |
| `.py`, `.js`, `.ts`, `.java`, `.c`, `.cpp`, `.go`, `.rs`, `.rb`, `.sh` | UTF-8 text captured as one language-tagged code block |

Every parser returns a `ParseReport`, which may be empty. Its status,
diagnostics, locations, IDs, and digest are persisted. OCR remains unsupported
and is refused by name on empty-text PDFs.

The canonical visible-text projection preserves image alt text, citations, and
footnote and endnote references. Note bodies share the canonical artifact but
retain distinct `footnote:<id>` and `endnote:<id>` evidence regions. Metadata
that exists only in IR can use strict `IRFieldEvidence`.

## Cleaning and source evidence

Current cleaning rules are `page-numbers`, `headers-footers`, `whitespace`,
`urls`, `emails`, `special-chars`, `lowercase`, and one custom removal regular
expression. With no explicit selection, the CLI applies `page-numbers` and
`whitespace`. A rule that would remove more than 30 percent of its target is
skipped and reported.

Each clean run creates a source-scoped `CleaningPlan` with exact configuration,
operations, allowed paths, source locations, before and after digests,
character and UTF-8 byte counts, warnings, and a portable parse-input digest.
Clean replays the plan before commit. Preview uses the same planner and replay
engine and writes nothing.

Every emitted chunk stores `SourceEvidence`. Evidence binds canonical ranges
and ordered edit, slice, or join derivations. It verifies source and artifact
identity, range bounds, each derivation, and final text. Sentence and
transformed chunks have no provenance bypass.

## Dataset construction

Group 2 implements five exact objective field contracts:

| Objective | Fields |
| --- | --- |
| `full_text` | `text` |
| `continuation` | `prompt`, `completion` |
| `section_reconstruction` | `heading`, `section` |
| `before_after_transformation` | `before`, `after` |
| `structured_field` | `input`, `fields` |

There is no deterministic summary objective and construction makes no LLM
call. Ineligible source units produce typed diagnostics instead of invented
content.

A `DatasetRecipe` binds one objective, an exact source set, cleaning and
segmentation identities, ordered constructor passes, review policy, required
construction gates, and one target row schema. Each candidate retains exact
recipe, pass, source, chunk, transform, and field-evidence lineage. One
`PromotionDecision` covers each candidate. Required-review recipes cannot
promote a candidate without separate `ReviewEvidence`.

Construct commits canonical `recipe` and `result` artifacts. Before `HEAD`
advances, the workspace reconstructs every selected source, clean, chunk,
transform, and IR input and compares the result with a fresh deterministic
replay.

## Curation and coverage

`curate` creates the complete `FinishedDatasetPlan` and applies this fixed
order:

1. minimum target-character filtering;
2. source-scoped conflict quarantine;
3. exact objective-and-field deduplication;
4. optional deterministic primary-source cap; and
5. selected-source coverage closure.

Each Group 2 record receives exactly one included, excluded, or quarantined
decision. Exact duplicates retain the minimum record ID as representative.
Conflict classes quarantine every member when an identical context and exact
source scope has distinct targets. Balance mode is `none` or
`primary-source-cap`.

Coverage accounts for candidates, records, statuses, and contributions for
every selected source, including multi-source records. The blocker codes are
`no-constructed-candidates`, `no-dataset-records`, and
`no-included-contribution`. Blockers remain inspectable but prevent a passing
finished-dataset validation.

## Leakage-safe splitting

`split` admits only curation-included representatives. It connects records
through shared source IDs, equal raw-source digests, multi-source joins, and
inherited exact-dedup-family relations. Complete transitive components become
indivisible leakage groups.

Assignment uses the plan seed and evaluation ratio. It orders groups
deterministically and selects one bounded prefix closest to the requested
evaluation record count. No group crosses a partition. Evaluation is required
by default. Fewer than two leakage groups fails with `split-invalid` unless the
plan explicitly allows an empty evaluation partition.

## Product rows and provenance

Serialization consumes the exact plan, construction result, curation result,
and split result. It lowers one included record into one row. It does not read
chunks as substitute records, reopen curation, resplit, or invent an objective
or target.

| Row schema | Exact payload shape |
| --- | --- |
| `text` | `{"text":"<target>"}` |
| `prompt_completion` | `{"prompt":"<context>","completion":"<target>"}` |
| `instruction_output` | `{"instruction":"<plan literal>","input":"<context>","output":"<target>"}` |
| `messages` | Two turns with exact source context as user and exact target as final assistant |

Only `full_text` may use `text`. Only `instruction_output` uses the non-empty
instruction literal fixed during `curate` (the catalog template, or a
truthful operator instruction). Structured `messages` remain
structured. Rendered model-family chat is not a sealed product row.

Train and evaluation JSONL contain only the chosen schema keys. One combined
provenance stream binds each row to its record, recipe, objective, pass,
sources, chunks, transforms, evidence, curation decision, leakage group,
assignment, partition ordinal, and exact payload digest. Partition rows are
ordered by record ID. Combined row and provenance order is train first, then
evaluation.

## Exact validation

Validation binds exact upstream artifact IDs and digests, source scope, plan,
row set, three emitted JSONL byte streams, canonical bundle paths, and validator
versions into one immutable `DatasetSnapshot`.

All 17 gates report in this exact order:

1. `construction-replay`
2. `record-lifecycle`
3. `curation`
4. `deduplication`
5. `quality`
6. `balance`
7. `coverage`
8. `split`
9. `leakage`
10. `row-binding`
11. `objective`
12. `schema`
13. `encoding`
14. `masking`
15. `partition-nonempty`
16. `aptus-row-shape`
17. `snapshot`

A valid failing report persists with failed stage status and retains all
findings. Unreadable critical input blocks dependent gates rather than
producing false passes. A failed or stale report cannot satisfy seal.

The `aptus-row-shape` validation gate proves generic product-row shape only.
Its name is a persisted v1 report identifier retained for compatibility; it
imports no Aptus code. Renaming it requires a versioned migration. Group 6 adds
an optional sibling descriptor and consumer verification for sealed partitions
and assignment projection. Repository checks prove adapter self-conformance,
not live Aptus release compatibility. Training remains outside this repository.

## Bundle and verification boundary

The `minimal-v1` bundle contains exactly:

```text
name.vfbundle/
├── data/train.jsonl
├── data/evaluation.jsonl
├── metadata/row-provenance.jsonl
├── validation.json
├── manifest.json
└── attestation.json
```

Seal reloads one verified workspace revision, rebuilds and revalidates its
exact snapshot, copies the already validated payload bytes into a private
temporary sibling, writes the deterministic manifest and attestation, syncs
the files and directories, runs the independent verifier, rechecks the
expected workspace revision, and atomically promotes the directory without
overwriting an existing destination. A retry may attach receipts to an exact
prior publication only after external-digest verification, byte comparison,
and revalidation.

The manifest has no self-hash. `attestation.json` binds the exact manifest
SHA-256 and content root. Because both files are co-located, an unanchored
bundle receives only `self_consistent`. Supplying the expected manifest digest
from a separate trusted channel permits `external_digest`.

The verifier needs no workspace. It rejects missing or extra files and
directories, unsafe or noncanonical paths, case or Unicode collisions,
symlinks, hard links, special files, digest mismatches, count mismatches, row
and provenance misalignment, invalid included decisions, conflict or duplicate
rows, source or group leakage inconsistency, incomplete source coverage,
row-set reconstruction mismatch, validation mismatch, and attestation mismatch.

Bundle publication and workspace receipt commit are separate atomic actions. A
rare failure after publication can leave the bundle visible while the receipt
does not commit. The CLI reports the visible path and manifest digest and does
not claim rollback.

## Remaining limitations

### Optional Aptus handoff is versioned; live trainer compatibility is unproven

Group 6 emits sibling `*.aptus-handoff.json` descriptors and a fail-closed
consumer check (`handoff-verify`) that proves external-digest verification,
partition digests, row schema, masking expectations, and assignment
projection digests. It does not invoke or identify a live external Aptus build;
any named-version compatibility claim requires separate retained evidence.

### Input and policy breadth remains limited

OCR remains unsupported. Curation supports deterministic minimum target
filtering, conflict quarantine, exact deduplication, coverage, and an optional
primary-source cap. Group 5 adds a named recipe library, deterministic
statistics, and versioned YAML pipelines executed only through
`PipelineService`.

### Public release readiness remains incomplete

Automated Group 9 gates are present (matrix CI, lock check, clean-wheel
installed-CLI smoke, standalone golden compile). Still incomplete for a
public-ready claim: type checking and coverage as hard gates, dependency audit,
signed/notarized Mac distribution, and clean-Mac installation under owner
credentials. Aptus evidence is required only for a separately named Aptus
compatibility claim.
See [docs/release.md](release.md).

## Phase boundary

| Status | Capability |
| --- | --- |
| Implemented M1 | Canonical IR, supported parsers, deterministic rules, five chunkers, initial projections, validation, bundle code, and stage CLI |
| Implemented Group 1 | Transactional workspace, source-scoped identities, diagnostics, immutable evidence, replayable cleaning plans, and regression coverage |
| Implemented Group 2 | Five objectives, strict recipes and passes, field evidence, candidate lifecycle, exact source selection, and construction replay |
| Implemented Group 3 | Curation, leakage-safe split, construction-aware rows, exact 17-gate validation, atomic six-file seal, and independent verification |
| Implemented Group 4 | `PipelineService`, thin CLI adapter, and dual-objective M1.1 API and CLI acceptance |
| Implemented Group 5 | HTML/PDF/CSV/JSON/JSONL ingest, OCR refusal, recipe library, statistics, YAML pipelines |
| Implemented Group 6 | Local MCP adapter, versioned Aptus handoff, consumer verification |
| Implemented Group 7 | SwiftUI workbench (CLI adapter) with digest parity |
| Implemented private beta workbench Phases 0–2 | Dogfood; KISS shell; failure detail; digest copy; artifact reveal; rerun |
| Implemented Group 9 + independent Phase 1 defaults | CI matrix, lock check, clean-wheel installed golden proof, standalone golden compile/verify, optional non-blocking Aptus adapter proof, release runbook |
| Implemented independent Phase 2 | Bounded async Mac process runner, cancellation/quit recovery receipts, deterministic no-replace transport, archive re-verification, Mac and Linux acceptance evidence |
| Implemented independent Phase 3 | Versioned taxonomy, shared compile compatibility, read-only discovery through `PipelineService.discover_taxonomy()`, `veriformis taxonomy`, MCP, and CLI-backed workbench help, axis-specific public copy, a display-only `Lower rows` stage alias, canonical taxonomy golden, and frozen pre-taxonomy workspace/bundle compatibility proof |
| Implemented independent Phase 4 | Verified-export contracts, source trust, source-derived plans, complete derivative membership, atomic publication, exact/semantic evidence limits, production-empty cross-surface operations, and adversarial closeout; no shipped renderer/replayer, production container, or support promotion |
| Implemented independent Phase 5.1 | Production `split-jsonl-directory` v1 exact-byte export, request-v1 defaults, strict configured request v2, canonical payload JSONL, deterministic README/data card, optional aligned provenance, receipt, and no trainer claim or membership change |
| Implemented independent Phase 5.2 | Production canonical `json` v1 exact-byte export, fixed dataset/provenance object tree, explicit split/schema metadata, mandatory aligned provenance, receipt, and no trainer claim or membership change |
| Implemented independent Phase 5.3 | Production `constrained-csv` v1 exact-byte export for the three flat row schemas, fixed quoted CSV/data-card/provenance tree, nested-`messages` refusal, receipt, and no trainer claim or membership change |
| Implemented independent Phase 5.4 | Optional `deterministic-export-pack-zip-v1` post-export transport with `.vfexport.zip`, an external canonical-receipt digest, exact receipt-bound members, shared deterministic ZIP/no-replace machinery, preserved source trust, and no fourth renderer, MCP operation, or Mac UI action; merged as PR #56 at `499d61fa2e7d` |
| Implemented and merged independent Phase 5.5 | Test-only consolidated ordinary-file semantic round-trip fixture covering all 11 compatible container/schema pairs, canonical semantic tamper for each container, and actionable pre-publication constrained-CSV/`messages` refusal; PR #57 at `c72b8e9ec7bc`; no importer, replayer, API, taxonomy, support, or trainer promotion |
| Implemented and merged independent Phase 5.6 | Runtime response-v2 dry-run preview: exact first row per non-empty partition, complete payloads through the 65,536-byte inclusion ceiling and whole-row omission above it or under response-budget pressure, ASCII-safe exact-value transport, and normalized plan-derived tree plus receipt; no renderer/destination access or persisted/support promotion; PR #58 at `cd017941090c` |
| Completed independent Phase 5.7 | [Generic export operator guidance](generic-exports.md) separates JSONL/JSON/CSV container choice from objective, row schema, and consumer compatibility; reconciled Phase 5 closeout with no runtime or support-state change |
| Completed independent Phase 6 | Goal catalog, contracts, preview, presets, preflight, acceptance matrix, instruction truthfulness; closeout PR #67 at `6995d17bef` |
| Completed independent Phase 7 | Existing-dataset import/mapping: modes, contracts, JSONL/JSON/CSV capture, confirmation, provenance, preview, partitions, rejections, templates; closeout PR #80 at `b7bb7f0c2046` after all 14 GitHub checks passed |
| Completed independent Phase 8 | TRL SFT and MLX-LM LoRA optional adapters, admission pins, official-schema harnesses, dataset-only launch sidecars, discovery truthfulness; items 8.1–8.6 merged as PR #82–#87 |
| Implemented beta-prep (docs/evidence) | Limitations register, install guide, clean-path pack; still alpha maturity |
| Completed independent Phase 9 | Parquet, Arrow IPC, and local Hugging Face DatasetDict v1 as implemented `semantic_content_only` generics; Arrow schema pins; semantic fingerprints; Phase 7 Parquet/Arrow mapping; optional library-reload CI; extra `columnar` remains empty |
| Authoritative active/future work | [Independent Product Roadmap](plans/2026-08-11-veriformis-independent-product-roadmap.md), with Phases 0–9 complete; Phase 10 remains planned |
| Owner-gated Group 9 remainder | Signed/notarized Mac install evidence; public-ready Mac app claim |
| Open product decision | Deliberate beta **label** cut (not automatic from green CI) |
| Later / optional | Group 8 model-assisted construction (owner plan) |
| Future opt-in | Governed source-grounded model assistance through a separately approved `GeneratorPass` |
| Public release | Full checklist in [docs/release.md](release.md) with retained evidence |
| Outside current product | OCR, model training, cloud accounts, multi-user service, billing, and telemetry |

The implemented path remains offline and makes no LLM calls.

## Development and release evidence

Group 9 automated gates (local or CI):

```text
uv lock --check
uv run ruff check src tests
uv run pytest -q --ignore=tests/handoff -m "not aptus_integration and not profile_integration and not columnar_integration"
bash scripts/release/smoke_install.sh
bash scripts/release/golden_compile.sh
git diff --check
```

Selected permanent locks:

| Area | Evidence |
| --- | --- |
| Dual-objective M1.1 | `tests/pipeline/test_pipeline_service.py` |
| Declared input-type e2e | `tests/regressions/test_group5_declared_format_pipeline.py` |
| MCP / service parity | `tests/mcp/test_mcp_pipeline_parity.py` |
| Optional Aptus adapter | Marked `tests/handoff/test_aptus_handoff_v1.py`, `scripts/release/aptus_integration.sh`, [Aptus Handoff v1](contracts/aptus-handoff-v1.md) |
| Workbench CLI sequence | `macos/scripts/parity_check.sh`, `macos/scripts/standalone_workbench_smoke.sh`, `macos/Tests/`, `./script/build_and_run.sh` |
| Deterministic transport | `tests/bundle/test_finished_bundle.py`, `scripts/release/golden_compile.sh`, [bundle transport contract](contracts/bundle-transport-v1.md), [ADR 0005](adr/0005-deterministic-bundle-transport.md) |
| Taxonomy discovery | `tests/test_cli.py`, `tests/pipeline/test_pipeline_service.py`, `tests/mcp/test_mcp_pipeline_parity.py`, `macos/Tests/` |
| Split JSONL export | `tests/exports/test_split_jsonl.py`, `tests/exports/test_api.py`, `tests/contracts/test_verified_export_contract.py`, [Split JSONL Export v1](contracts/split-jsonl-export-v1.md) |
| Canonical JSON export | `tests/exports/test_canonical_json.py`, `tests/exports/test_api.py`, `tests/contracts/test_verified_export_contract.py`, [Canonical JSON Export v1](contracts/canonical-json-export-v1.md) |
| Constrained CSV export | `tests/exports/test_constrained_csv.py`, `tests/exports/test_api.py`, `tests/contracts/test_verified_export_contract.py`, [Constrained CSV Export v1](contracts/constrained-csv-export-v1.md) |
| Group 9 golden + scripts | `tests/regressions/test_group9_release_gates.py`, `scripts/release/`, [release guide](release.md) |
| Operator install | [install.md](install.md) |
| Beta limitations | [beta-limitations.md](beta-limitations.md) |
| Program tracking | `tests/regressions/test_project_tracking.py`, [tracking policy](governance/project-tracking.md) |
| Clean-path evidence pack | `dev/active/group-9-public-release/evidence/` |
| Private beta workbench plan | [plans/2026-08-06-private-beta-workbench.md](plans/2026-08-06-private-beta-workbench.md) |

Group 3 independent architecture and security review:
[Group 3 code review](../dev/active/group-3-finished-dataset/group-3-finished-dataset-code-review.md).

Version `0.1.0` remains a development **alpha**. A future beta cut requires the
checklist in [beta-limitations.md](beta-limitations.md). Public readiness still
requires [docs/release.md](release.md) with retained evidence.

## Next authority

On `main` at this review: Groups 1–7, Group 9 automated gates, beta-prep, and
private beta workbench Phases 0–2 are landed; maturity is still **alpha**.

Independent-product Phases 0–4 are complete, and Phase 5.1–5.3 supply the first
three supported generic derivative containers. The completed
[taxonomy packet](../dev/active/independent-product/phase-03-taxonomy/README.md)
records the contract, compile compatibility, cross-surface discovery, public
vocabulary cleanup, and persisted-v1 compatibility evidence. The completed
Phase 4 verified-export foundation is recorded in its
[closeout packet](../dev/active/independent-product/phase-04-verified-export-foundation/README.md).
Its strict cross-surface export API and adversarial closeout harness preserve
the boundary: private hooks are trusted conformance code, not an
untrusted plugin boundary, and semantic replay currently retains each complete
produced file in memory. The statically bounded fixture does not establish a
scalable public parser; any future shipped semantic profile must enforce
explicit resource limits. Phase 5.1–5.3 add production exact-byte split-JSONL,
canonical-JSON, and constrained-CSV renderers without adding a semantic
replayer. Shipped discovery lists `constrained-csv`, `json`, and
`split-jsonl-directory` v1 with no consumer profile. Split JSONL's v1 defaults
and strict v2 options change only derivative filenames and provenance
inclusion; canonical JSON and constrained CSV have fixed v1 trees and no
options. None changes dataset membership. Constrained CSV's supported-schema
subset excludes nested `messages`. Phase 5.4's post-export transport and Phase
5.5's test-only consolidated matrix are merged; the latter proves the eleven compatible
ordinary-file round trips and three container tamper failures without adding an
importer or replayer. Phase 5.6's runtime preview merged as PR #58 and changes
no persisted or support state. Phase 5.7's operator guide closes the phase
without changing that capability boundary. New trainer-specific profiles are
not current capabilities; the canonical and optional Aptus
profiles remain the implemented profile set. A deliberate beta label and
public Mac checklist remain separate decisions.

See the [generic export operator guide](generic-exports.md),
[Phase 5 closeout](../dev/active/independent-product/phase-05-generic-local-exports/closeout.md),
[independent product analysis](analysis/2026-08-11-independent-product-analysis.md),
[tracking and evidence policy](governance/project-tracking.md),
[historical private beta workbench plan](plans/2026-08-06-private-beta-workbench.md),
[install guide](install.md), [release guide](release.md),
[beta limitations](beta-limitations.md), and
[beta readiness audit](../dev/active/group-9-public-release/beta-readiness-audit.md).
