# Veriformis Independent Product Roadmap

**Status:** Authoritative roadmap for new product work

**Per-phase execution state:**
[`dev/active/independent-product/program.json`](../../dev/active/independent-product/program.json)
(Phases 0–2 completed 2026-08-11). Per-phase "Current evidence" blocks record
facts at the implementation baseline below, not live status; the program
ledger is the execution authority.

**Created:** 2026-08-11

**Implementation baseline:** `7d116e9c09fb4c64f38b2db2572f820a83c53dba`,
version `0.1.0` development alpha

**Supersedes for future work:** [2026-07-29 build roadmap](2026-07-29-veriformis-roadmap.md)
and [2026-08-06 private workbench plan](2026-08-06-private-beta-workbench.md).
Those documents remain historical implementation evidence.

**Evidence baseline:** [Independent Product Analysis](../analysis/2026-08-11-independent-product-analysis.md)

## 1. Final product goal

Veriformis is an independent, local-first dataset compiler and dataset
interchange workbench. It accepts heterogeneous source documents and existing
dataset rows, makes every supported transformation explicit, helps the user
select a truthful training goal, constructs or normalizes training records,
curates and leakage-safely splits them, validates the exact result, seals a
reproducible canonical artifact, and exports verified training-ready datasets
for multiple useful containers and named training systems.

The final product must work without Aptus installed, available, configured,
named in the primary workflow, or included in release evidence. Aptus is one
optional downstream integration. The same rule applies to every trainer:
Veriformis owns the dataset; trainer profiles adapt a verified dataset but do
not define the compiler core.

The product does not promise that arbitrary source material can truthfully
become any training task. It does not train models, select a model on the
user's behalf, or guarantee model improvement. It makes supported dataset
preparation understandable, reproducible, inspectable, and portable.

## 2. Final acceptance definition

The independent product is complete only when a user can perform this workflow
through both CLI and Mac workbench, with the same domain contracts:

1. Install Veriformis on a supported clean machine without Aptus.
2. Add a supported mix of documents, structured sources, or existing dataset
   rows and receive explicit accept, degradation, mapping, or refusal results.
3. Choose a training family and objective in plain language; Veriformis never
   infers a materially ambiguous goal without confirmation.
4. Preview recovered content, mapped fields, sample training rows, exclusions,
   split facts, and loss/masking semantics before publication.
5. Compile through construction or normalization, curation, split, formatting,
   exact validation, seal, and independent verification.
6. Export the verified result in a generic supported container or a versioned
   named consumer profile.
7. Verify the export receipt and reproduce the same semantic dataset and
   deterministic files from the same sources, configuration, and tool/profile
   versions.
8. Receive actionable diagnostics for unsupported input, invalid rows,
   lossy mappings, incompatible goals, profile drift, cancellation, or
   tampering.
9. Process the declared supported corpus tiers within measured resource and
   reliability limits.
10. Complete the entire golden workflow with no Aptus dependency. Optional
    Aptus compatibility is proven only by its own integration suite.

## 3. Product invariants

Every phase must preserve these rules:

1. **Standalone first.** Core install, compile, verify, export, UI, docs, and
   release gates contain no required downstream trainer.
2. **One composition root.** `PipelineService` and its domain services own
   policy. CLI, MCP, GUI, and integrations are adapters.
3. **Goal before format.** Training meaning and loss boundaries are selected
   before physical container or consumer profile.
4. **Canonical before convenient.** The verified Veriformis bundle is the
   source of truth. Exports are bound derivatives, never an alternate hidden
   pipeline.
5. **Nothing silent.** Parse loss, mapping loss, cleaning, construction,
   filtering, deduplication, balancing, split assignment, template rendering,
   and export adaptation are inspectable.
6. **No invented supervision.** Deterministic compilation may only emit targets
   grounded in source evidence or named deterministic derivations. Generated
   targets use a separately governed path.
7. **Fail closed.** Unsupported semantics, ambiguous mappings, stale state,
   unexpected files, and failed conformance prevent a supported claim.
8. **Offline default.** Core compilation and local export make no network call.
   Hub publication, remote generation, and hosted-trainer adapters are
   explicit opt-ins.
9. **Evidence over popularity.** A format or profile is supported only after
   official-contract research, fixtures, negative tests, and conformance
   evidence.
10. **Version everything that changes meaning.** Inputs, objectives, mappings,
    row schemas, profile behavior, templates, validators, receipts, and
    migrations are versioned.

## 4. Product model

The user-visible model has four separate axes. UI and APIs must not collapse
them into a single “format” field.

| Axis | Purpose | Examples | Authority |
| --- | --- | --- | --- |
| Training family and objective | States what is learned and which values are targets | Continued pretraining, prompt/completion SFT, conversational SFT, structured extraction; preference learning later | Versioned objective/recipe contract |
| Semantic row schema | States field roles without trainer naming | `text`, `prompt_completion`, `instruction_output`, `messages`; preference schemas later | Versioned row contract |
| Physical container | Stores rows, partitions, metadata, and sidecars | Veriformis bundle, JSONL, JSON, constrained CSV, Parquet, Arrow/HF dataset | Versioned export plan |
| Consumer profile | Applies a named trainer's filenames, mappings, template/masking rules, and sidecars | TRL, MLX-LM, Axolotl, LLaMA-Factory, Unsloth, Aptus | Versioned profile + conformance suite |

Pre-tokenized rows are both tokenizer/model-bound and loss-policy-bound. They
must be emitted only by an explicit consumer/model profile that records the
tokenizer identity and immutable revision, template, maximum length,
truncation, packing, label/mask construction, and special-token policy. They
are not a generic format.

## 5. Format and profile admission gate

Candidate inputs, containers, and trainer profiles do not become commitments
merely by appearing in this roadmap. Each must pass all of the following:

1. A named user workflow and representative retained corpus.
2. A primary specification or official consumer document with reviewed date
   and supported version range.
3. An explicit mapping from Veriformis semantic rows to the destination,
   including missing, null, nested, role, template, and masking behavior.
4. A documented loss and refusal model.
5. Deterministic golden fixtures, malformed inputs, boundary cases, and
   property tests where appropriate.
6. Round-trip validation when the format permits it.
7. Actual consumer-loader or schema conformance in an isolated integration
   environment.
8. Dependency, license, security, maintenance, versioning, and deprecation
   decisions.
9. Documentation that distinguishes current support from candidates.

If a consumer has no stable machine-checkable contract, the profile remains
experimental and version-pinned rather than becoming a general compatibility
claim.

## 6. Delivery milestones

| Milestone | Required phases | Outcome |
| --- | --- | --- |
| A — Independent foundation | 0–3 | Product authority, defaults, reliability, and semantic model are trainer-neutral |
| B — Standalone useful beta | 4–7 | Verified generic exports, goal-first workflows, and existing-dataset mapping work without Aptus |
| C — Interchange beta | 8–11 | First trainer profiles, columnar outputs, expanded evidence-gated profiles, and hardened collection ingest |
| D — Quality and scale candidate | 12–16 | Evidence-qualified OCR, decision support, review, benchmarked scale, and extension boundary |
| E — Product release candidate | 17–19 | Governed advanced data, cohesive workbench, and automation/publishing boundary |
| F — Stable independent product | 20 | Version 1.0 support matrix and maintenance policy pass |

No date is assigned until Phase 0 records capacity and a phase-sized delivery
estimate. Unmeasured calendar promises would not be evidence-based.

---

## Phase 0 — Establish authority, baseline, and decision records

**Goal:** Make current truth and the independent destination unambiguous before
behavior changes.

**Current evidence (at baseline `7d116e9`; phase completed — see program
ledger):** The current-status and documentation index still report
private workbench Phases 0–1 even though the Phase 2 plan says implemented.
The old roadmap makes Aptus part of integration and public-release gates. The
repository remains version `0.1.0` development alpha.

**Work:**

1. Adopt this roadmap as the future-work authority and mark the two older
   roadmaps historical without deleting their evidence.
2. Refresh current status from source and tests, including workbench Phase 2,
   current `main`, supported inputs, output limits, default Aptus behavior,
   and known Finder/UI defects.
3. Create an architecture-decision record set for the four-axis product model,
   canonical bundle/export relationship, standalone defaults, optional
   dependency policy, and compatibility claim levels.
4. Create machine-readable support registries for implemented, experimental,
   planned, deprecated, and unsupported inputs, semantic rows, containers,
   and consumer profiles.
5. Record baseline verification commands and retained results for lock, lint,
   Python tests, Swift tests, parity, install smoke, golden compile, and bundle
   verification.
6. Inventory representative owner corpora without committing private content;
   retain sanitized structural fixtures and frequency facts needed to rank
   future format work.
7. Create a phase evidence template covering contract, implementation, tests,
   performance, security, docs, migration, and release effects.

**Deliverables:** Updated authority links, baseline evidence pack, support
registry v1, decision-record index, sanitized corpus matrix, and known-gap
register.

**Exit evidence:** Every current capability claim resolves to source and a
passing test or is labeled unverified; every planned capability is labeled
planned; no current document identifies Aptus as the product's required
destination.

**Non-goals:** New runtime features or maturity-label changes.

## Phase 1 — Enforce standalone independence

**Goal:** Make the default product behavior and required release path fully
independent of Aptus.

**Current evidence (at baseline `7d116e9`; phase completed — see program
ledger):** CLI `seal`, MCP `seal`, and the workbench currently default
to emitting an Aptus handoff. Workbench copy recommends Aptus-friendly
objectives. Existing `PipelineService.seal` itself is neutral.

**Work:**

1. Change CLI seal default to canonical bundle only. Retain an explicit Aptus
   integration command or opt-in flag with a deprecation path for the old
   default.
2. Change MCP and workbench defaults to no Aptus artifact. Move Aptus controls,
   history fields, and copy under an Integrations area.
3. Remove Aptus-specific advice from Home, primary result, onboarding, product
   contract, beta limitations, install, and generic release paths.
4. Split core and optional-integration test markers/jobs. Core tests must run in
   an environment where no Aptus package or repository exists.
5. Replace golden release success with standalone seal plus external-digest
   verify. Keep Aptus handoff verification as a separate non-blocking profile
   job unless an Aptus-specific release is being made.
6. Audit imports so no core, parser, construction, dataset, bundle, export,
   CLI-startup, or workbench-launch path imports Aptus adapter code unless the
   integration is invoked.
7. Define compatibility wording: “Veriformis export profile X passed against
   consumer version Y,” never “Veriformis requires X.”

**Deliverables:** Trainer-neutral default product, optional Aptus adapter,
standalone install/compile evidence, and migration notes for scripts that
relied on the previous default.

**Exit evidence:** A clean environment with only the Veriformis package can run
the full golden pipeline, verify the bundle, launch the workbench, and pass all
core tests. No required artifact, screen, or release gate mentions Aptus.

**Non-goals:** Removing the working Aptus adapter or claiming compatibility
beyond its separately tested versions.

## Phase 2 — Close known reliability and artifact-boundary defects

**Goal:** Stabilize the existing independent compile path before adding output
formats.

**Current evidence (at baseline `7d116e9`; phase completed — see program
ledger):** The main-actor workbench calls synchronous
`waitUntilExit()`. Finder has added `.DS_Store` inside a retained `.vfbundle`,
violating the strict closed file set. Phase 2 workbench functionality is
implemented but status documentation is stale.

**Work:**

1. Move subprocess execution and pipe draining off the main actor; keep model
   mutations isolated on the main actor.
2. Add cancellation, process termination escalation, cancellation receipts,
   bounded log handling, and safe partial-workspace recovery.
3. Test high-volume stdout/stderr, cancellation at every stage, app quit during
   compile, missing CLI, full disk, permission failure, and non-UTF-8 process
   output behavior.
4. Decide the distributable `.vfbundle` boundary through an ADR backed by Mac,
   Linux, and verifier tests. Candidate solutions are a deterministic immutable
   archive or a registered package directory whose mutation rules are proven.
5. Preserve the internal directory bundle contract unless a versioned bundle
   migration is justified. Do not weaken verification to ignore arbitrary
   unexpected files.
6. Add copy/reveal/export actions that operate on verified artifacts and never
   mutate the canonical bundle.
7. Refresh Phase 2 status and retained GUI evidence.

**Deliverables:** Responsive workbench, cancellation semantics, immutable
distribution decision, and Finder-safe artifact workflow.

**Exit evidence:** UI interaction and progress updates remain responsive during
a long-running fixture; cancellation and interruption tests pass; a bundle
round-tripped through Finder and the selected distribution form still verifies
with the retained external digest.

**Non-goals:** New training objectives or output containers.

## Phase 3 — Formalize the goal, schema, container, and profile taxonomy

**Goal:** Give every later input and output feature a truthful semantic home.

**Current evidence:** `TrainingObjective` is already separate from row schema,
but the user workflow and docs still mix objective, JSONL, bundle, and Aptus
compatibility. Official trainer documentation distinguishes semantic dataset
types, representations, templates, and masking.

**Work:**

1. Define versioned `TrainingFamily`, objective, semantic row, physical
   container, consumer-profile, and loss-policy concepts. Reuse existing
   contracts where compatible; migrate rather than reinterpret when not.
2. Review current `full_text`, continuation, section reconstruction,
   before/after, and structured-field names against their actual learning
   semantics. Record any UI aliases separately from persisted identifiers.
3. Define supported current training families conservatively: source-grounded
   language modeling/continued pretraining and supervised fine-tuning forms.
4. Define future-only families—preference/ranking, classification with explicit
   labels, tool use, multimodal, stepwise supervision, and pre-tokenized
   training—without advertising them as implemented.
5. Define an exact loss/masking description for every semantic row schema.
   Consumer profiles may further constrain but may not silently alter it.
6. Add compatibility matrices and validation errors for impossible
   objective/schema/profile combinations.
7. Expose the taxonomy through `PipelineService`, CLI discovery commands, MCP
   resources/tools, and workbench help from one registry.
8. Add schema/version migration tests and golden round trips.

**Deliverables:** Product taxonomy contract, support matrix, compatibility
registry, discovery API, UI vocabulary, and migrations.

**Exit evidence:** No public API or screen uses “format” where it could mean
more than one axis; every implemented recipe and row schema has one explicit
training and loss interpretation; invalid combinations fail before compile.

**Non-goals:** Preference or generated-data implementation.

## Phase 4 — Build the verified export foundation

**Goal:** Create a consumer-neutral way to derive portable outputs from the
canonical verified bundle.

**Dependencies:** Phases 1–3.

**Work:**

1. Add a typed export service under the Python composition root. CLI, MCP, and
   GUI call it rather than copying or rewriting files themselves.
2. Define versioned export plan, container profile, consumer profile,
   destination file binding, export receipt, and export verification models.
   Exact schema identifiers are finalized through contract review in this
   phase.
3. Require a verified bundle and retained expected manifest digest for a
   trusted export. Record lower trust explicitly if self-consistent input is
   intentionally allowed.
4. Bind source bundle identity and manifest digest, split assignment, row
   schema, export/profile versions, dependencies, all output file paths,
   media types, sizes, row counts, and SHA-256 values.
5. Forbid exporters from constructing targets, curating, balancing, resplitting,
   or changing record membership. Any intentional filtering requires a new
   compiled dataset plan, not an export flag.
6. Make destination writes atomic, no-overwrite by default, path-safe,
   cancelable, and independently verifiable.
7. Define deterministic-byte claims per container. If a library cannot produce
   portable deterministic bytes, bind and verify semantic content separately
   and state the evidence limit.
8. Add export discovery, dry run, overwrite policy, inspect, and verify APIs.
9. Add contract, property, tamper, path traversal, race, and partial-publication
   tests.

**Deliverables:** Export service and contracts, `veriformis export`,
`veriformis export-verify`, inspection APIs, and test harness.

**Exit evidence:** A generic test exporter creates an atomic, receipt-bound
derivative; tampering, unexpected files, source-digest mismatch, and partial
publication fail verification; all surfaces produce identical plans and
digests.

**Non-goals:** Specific external trainer compatibility.

## Phase 5 — Ship lossless generic local exports

**Goal:** Make the compiled dataset directly usable outside `.vfbundle` without
choosing a trainer.

**Dependencies:** Phase 4.

**Initial support candidates with current evidence:**

| Container | Semantic rows | Rule |
| --- | --- | --- |
| Split JSONL directory | All current row schemas | Exact canonical row bytes where destination contract permits |
| Split or dataset JSON | All current row schemas | Canonical arrays/objects with explicit partition structure |
| CSV | Flat `text`, prompt/completion, instruction/input/output only | Nested messages fail closed unless a later explicit encoding profile is approved |
| Deterministic archive | Export pack or bundle distribution | Exact file set, normalized paths/metadata, verifier required |

**Work:**

1. Implement generic split JSONL export with configurable but safe partition
   names, optional aligned provenance, README/data card, and receipt.
2. Implement canonical JSON export with explicit split and schema metadata.
3. Implement CSV only for mappings that remain structurally lossless. Define
   quoting, encoding, newline, null, empty-string, and Unicode rules. Refuse
   nested values by default.
4. Integrate the deterministic archive transport that Phase 2 already shipped
   (ADR 0005, [bundle transport contract](../contracts/bundle-transport-v1.md),
   `veriformis package` / `package-verify`) into the export plan and receipt
   model. The remaining new scope is deterministic archiving of generic export
   packs; do not design a second bundle-archive format.
5. Add import-round-trip fixtures to prove semantic preservation.
6. Expose exact sample rows and destination tree in dry-run preview.
7. Document when to use JSONL, JSON, or CSV and why they do not determine the
   training objective.

**Deliverables:** First standalone export menu/API, generic export receipts,
round-trip fixtures, and user guide.

**Exit evidence:** Every supported current row schema exports to all compatible
generic containers, reloads to identical semantic rows and partitions, and
detects tampering. Unsupported nested CSV fails before publication with an
actionable alternative.

**Non-goals:** Calling a generic JSONL file automatically compatible with every
trainer.

## Phase 6 — Deliver goal-first recipes and previews

**Goal:** Let users describe what they are trying to teach rather than reverse
engineering objectives and row schemas.

**Current evidence:** Five deterministic named recipes exist, but defaults are
developer-oriented and the workbench offers only limited objective controls.

**Work:**

1. Build a goal catalog for currently truthful source-grounded workflows:
   retained text/language modeling, continuation, section recovery,
   deterministic before/after transformation, structured extraction, and
   supervised instruction or conversation representations where the source
   actually supplies both context and target.
2. For each goal, document required input evidence, target construction,
   compatible rows, supervision boundary, curation defaults, review policy,
   suitable generic exports, and explicit non-claims.
3. Add goal-specific preview: recovered source, record derivation, context and
   target highlighting, rendered row, masked/supervised region, and exclusion
   reasons.
4. Add recipe configuration schemas with safe named presets and an advanced
   editor. Defaults are versioned data, not duplicated CLI/Swift constants.
5. Add a compile preflight that reports source eligibility and expected
   limitations before costly stages.
6. Add fixture suites for each goal across each compatible input family and
   row schema.
7. Validate that prompt templates or static instructions do not misrepresent a
   source-derived task.

**Deliverables:** Goal catalog, versioned presets, preflight, row/loss preview,
and cross-format acceptance fixtures.

**Exit evidence:** A non-developer can select each supported goal from plain
language and inspect exactly what receives training loss; all surfaces resolve
to the same recipe identifiers and outputs.

**Non-goals:** Automatically deciding whether fine-tuning is the right solution
or inventing question/answer pairs.

## Phase 7 — Add first-class existing-dataset import and mapping

**Goal:** Normalize and convert datasets that already contain training rows,
not only construct rows from documents.

**Current evidence:** CSV, JSON, and JSONL are supported as structured source
material, but there is no first-class row-mapping contract for existing
training datasets.

**Work:**

1. Add explicit input modes: document sources, dataset rows, and mixed projects.
   Mixed mode must keep construction and imported-row provenance distinct.
2. Define versioned row-source, mapping, role, nested-path, type coercion,
   missing-value, invalid-row, and review contracts.
3. Support explicit mappings into current semantic rows: `text`,
   `prompt_completion`, `instruction_output`, and `messages`.
4. Detect common shapes only to propose a mapping. Require confirmation when
   more than one semantic interpretation is possible.
5. Preserve file, row/index, field/path, original-value digest, mapping rule,
   and validation evidence for every accepted field.
6. Add preview and sampling across the full file, including malformed and rare
   shapes rather than only the first rows.
7. Define whether imported train/evaluation/test membership is authoritative,
   advisory, or replaced. Never silently resplit. Imported partitions that
   violate leakage policy must fail or require an explicit new plan.
8. Support generic JSONL, JSON, and compatible CSV inputs first. Add Parquet
   and Arrow in Phase 9, which extends these mapping flows.
9. Add row-level rejection exports so users can correct source data without
   losing the audit trail.
10. Add schema mapping templates as shareable, versioned project artifacts.

**Deliverables:** Dataset import mode, mapping editor/API, provenance-bound row
normalization, rejection report, and import/export round trips.

**Exit evidence:** Representative text, prompt/completion,
instruction/input/output, and message datasets can be imported under explicit
mappings, validated, sealed, generically exported, and semantically round
tripped. Ambiguous or lossy mappings do not auto-publish.

**Non-goals:** Preference, tool-call, multimodal, or arbitrary executable
mapping code.

## Phase 8 — Implement the first consumer profiles

**Goal:** Prove the profile architecture against two materially different,
well-documented training systems.

**Candidate selection:** TRL provides broad semantic dataset contracts;
MLX-LM is directly relevant to local Mac training. Both have official public
documentation. Final profile versions are pinned during this phase.

**Work:**

1. Implement a TRL profile for only the semantic types proven by current
   Veriformis rows. Emit Dataset/DatasetDict-compatible local data and profile
   metadata without claiming unsupported preference or stepwise types.
2. Implement an MLX-LM profile with required `train.jsonl`, optional
   `valid.jsonl`/`test.jsonl`, supported row shapes, and explicit masking or
   completion behavior.
3. Pin tested consumer version ranges and record official documentation review
   dates.
4. Build conformance harnesses that load the produced artifacts through the
   actual consumer loader or its authoritative schema path in isolated
   optional environments.
5. Test partition naming, empty validation policy, Unicode, nested messages,
   system roles, multiple assistant turns, and incompatible schemas.
6. Generate profile-specific config fragments or launch instructions as
   sidecars; do not launch training in the exporter.
7. Make profile discovery explain exactly which goals and rows are accepted,
   transformed, or rejected.

**Deliverables:** Versioned TRL and MLX-LM profiles, conformance CI jobs,
fixtures, sidecars, and compatibility statements.

**Exit evidence:** Each profile's golden dataset loads successfully in its
pinned consumer; deliberately incompatible rows fail in Veriformis before the
consumer sees them; the same canonical bundle can export to both profiles
without changing membership or targets.

**Non-goals:** Generic “works with Hugging Face” or “works with every MLX-LM
version” claims.

## Phase 9 — Add columnar and Hugging Face dataset containers

**Goal:** Support efficient interoperable containers for larger and nested
datasets while keeping optional dependencies isolated.

**Evidence:** Official Hugging Face Datasets documentation supports JSON/JSONL,
CSV, Parquet, Arrow, and text; its Parquet documentation describes columnar,
compressed, split-file behavior. LLaMA-Factory also documents Parquet and Arrow
file inputs.

**Work:**

1. Add a `columnar` optional dependency extra with reviewed, pinned-compatible
   PyArrow/Hugging Face dependencies. Base compile remains functional without
   it.
2. Define exact Arrow schemas for every supported semantic row, including
   nested messages and stable field ordering/types.
3. Implement deterministic semantic Parquet export with configurable shard
   size/compression only where the resulting evidence claim is understood.
4. Implement Arrow and local Hugging Face Dataset/DatasetDict export with split
   preservation, features schema, and metadata/data-card output.
5. Define semantic fingerprints independent of library-specific metadata that
   may vary across versions, while binding exact emitted bytes in each receipt.
6. Add Parquet/Arrow import to Phase 7 mapping flows.
7. Test large values, nested roles, null refusal, Unicode, shard boundaries,
   empty allowed splits, schema evolution, and actual library reload.
8. Benchmark JSONL versus columnar output before documenting performance or
   storage recommendations.

**Deliverables:** Parquet, Arrow, and local HF dataset import/export; optional
dependency split; schemas; receipts; and benchmarks.

**Exit evidence:** All current compatible row schemas round-trip through each
container with identical semantic fingerprints and partitions; base-package
tests pass without columnar dependencies; version-drift tests fail clearly.

**Non-goals:** Hub upload or claiming byte-for-byte stability across arbitrary
third-party library versions.

## Phase 10 — Expand consumer profiles under evidence gates

**Goal:** Add high-value training-system profiles without coupling the product
to any one ecosystem.

**Candidates with current official evidence:** Axolotl, LLaMA-Factory,
Unsloth, and Aptus. A hosted OpenAI profile may be researched separately but
must preserve the offline-default and opt-in network boundary.

**Work for every admitted profile:**

1. Complete the section 5 admission-gate record and pin a tested consumer
   version.
2. Map supported goals and semantic rows to filenames, column/role mappings,
   sidecars, templates, masking, empty-split rules, and loader configuration.
3. Refuse unsupported preference, tools, multimodal, reasoning, or ranking
   fields until the core semantic contracts support them.
4. Load golden exports through the real consumer's supported loader path.
5. Add compatibility status and last-tested version to machine-readable
   discovery and generated data cards.
6. Isolate consumer dependencies and config generators from the core install.
7. Move the existing Aptus handoff under this common profile lifecycle. Retain
   its external-digest and assignment checks, but remove special product
   authority.
8. Add an explicit deprecation policy when upstream contracts drift.

**Deliverables:** Only the profiles that pass admission and conformance,
profile registry UI, config sidecars, compatibility reports, and optional
Aptus profile migration.

**Exit evidence:** Each advertised profile passes its own pinned consumer
suite. Failure of or absence of any consumer integration does not break core
compile, generic export, or another profile.

**Non-goals:** A fixed promise that all candidates must ship or remain supported
forever.

## Phase 11 — Harden collection ingest and qualify additional formats

**Goal:** Make heterogeneous input practical at project scale without claiming
unsupported “any format” behavior.

**Current evidence:** Single-file dispatch supports a defined suffix set. The
workbench can collect multiple files, but collection policy and safety are not
a first-class contract.

**Work:**

1. Add a collection plan for files and directories: recursion, include/exclude,
   hidden files, symlinks, package contents, logical roots, ordering, duplicate
   bytes, maximum files/bytes, and unsupported-file policy.
2. Add preflight inventory with accepted, degraded, refused, duplicate, and
   ignored counts before parsing.
3. Add safe archive expansion only if retained corpus evidence justifies it;
   defend against path traversal, links, bombs, extreme ratios, duplicate
   names, Unicode path collisions, and nested limits.
4. Build per-parser adversarial, malformed, oversized, and fuzz corpora.
5. Isolate crash-prone or high-risk parser execution if risk analysis shows a
   process boundary is needed.
6. Record parser versions and recovery quality facts in portable evidence.
7. Use the Phase 0 corpus matrix and support requests to rank new formats.
   EPUB, spreadsheets, presentations, emails, notebooks, XML, subtitle, or
   additional code suffixes remain candidates until each passes the admission
   gate.
8. Add format-specific structure and loss contracts before implementation.

**Deliverables:** Collection contract, batch preflight, safety limits, parser
hardening suite, input admission records, and only evidence-qualified new
formats.

**Exit evidence:** A mixed directory fixture produces a deterministic inventory
and source order across supported platforms; malicious collection fixtures
fail safely; documentation exactly matches dispatch and tests.

**Non-goals:** Blind recursive ingestion or universal MIME sniffing.

## Phase 12 — Add optional local OCR with accountable recovery

**Goal:** Recover image-only and mixed PDFs without weakening source evidence.

**Dependencies:** Phase 11 parser hardening. Work items 1–2 of this phase
produce the OCR evaluation evidence and the owner-approved OCR ADR; work
items 3–8 may begin only after that ADR is accepted, or the phase is
deferred under work item 2.

**Work:**

1. Compare candidate local OCR engines on a retained, license-safe corpus
   covering languages, scans, mixed text/images, rotation, tables, handwriting
   exclusions, and degraded pages. Record accuracy proxies, runtime, memory,
   platform support, model size, licensing, and offline behavior.
2. Select an optional engine or defer the phase if none satisfies the gate.
3. Define OCR engine/model/language/version identities, page/image digests,
   coordinates, confidence/quality facts, preprocessing transforms, and
   deterministic limitations.
4. Distinguish digital extraction, OCR recovery, and merged recovery at page
   and field level. Never silently replace recoverable digital text with OCR.
5. Add thresholds that warn, require review, or refuse rather than deleting
   low-confidence content.
6. Add page/image previews and correction/review hooks.
7. Isolate dependencies under an `ocr` extra and keep core installation
   unchanged.
8. Test no-network execution, missing model data, multilingual selection,
   corrupt images, resource limits, and exact provenance replay.

**Deliverables:** OCR evaluation report and, only if accepted, optional local
OCR parser path, provenance contract, UI review, and fixtures.

**Exit evidence:** The retained OCR corpus meets thresholds chosen and recorded
before final implementation acceptance; every emitted character is marked by
recovery path and page evidence; low-quality cases warn or fail according to
policy.

**Non-goals:** Guaranteeing perfect OCR, handwriting recognition, or silent
cloud OCR.

## Phase 13 — Build dataset quality intelligence

**Goal:** Help users decide whether the correct compiled artifact is also a
suitable training dataset.

**Current evidence:** Exact deduplication, minimum targets, conflict quarantine,
source coverage, balancing controls, leakage groups, split statistics, and 17
validation gates exist. Broader decision-support metrics do not.

**Work:**

1. Define a versioned quality report with facts separated from policy
   decisions and recommendations.
2. Report source, objective, row, role/label, target-length, context-length,
   language where evidence-qualified, exclusion, split, and coverage
   distributions.
3. Add near-duplicate detection under a named, versioned algorithm with
   inspectable clusters and threshold previews. Do not call it semantic
   identity or silently delete rows.
4. Add leakage checks across imported partitions and optional external
   evaluation/reference corpora bound by digest.
5. Add tokenizer-bound token-length and truncation simulations only when a
   profile supplies an exact tokenizer revision and policy.
6. Add optional detectors for likely PII, secrets, unsafe content, or license
   policy signals. Treat results as findings with false-positive/negative
   limitations, not certification.
7. Add split-comparability, imbalance, rare-shape, malformed-role, and empty
   target/context findings.
8. Make every quality gate configurable, versioned, previewable, and recorded
   in the plan and validation snapshot.
9. Build calibrated labeled fixtures for each heuristic before allowing it to
   block seal.

**Deliverables:** Quality report, dashboard/CLI report, named heuristics,
cluster review, optional policy gates, and calibration evidence.

**Exit evidence:** Reports reproduce from bound inputs; all blocking heuristics
have predeclared thresholds and labeled-fixture performance; findings link to
source/row evidence and can be reviewed.

**Non-goals:** Guaranteeing privacy, copyright status, safety, absence of
contamination, or downstream model quality.

## Phase 14 — Deliver human review and correction workflows

**Goal:** Make ambiguous recovery, mapping, curation, and quality decisions
resolvable without editing content-addressed files by hand.

**Work:**

1. Define reviewer identity/reference, review queue, assignment, verdict,
   rationale, correction, waiver, and supersession contracts.
2. Support review queues for parser degradation, OCR, imported-row mapping,
   pending construction, conflicts, near-duplicate clusters, policy findings,
   and sample-based acceptance.
3. Implement corrections as explicit source-grounded transforms or new mapping
   revisions; never mutate accepted records in place.
4. Add sampling strategies with named deterministic seeds and complete
   population/selection evidence.
5. Build keyboard-efficient Mac review screens and equivalent CLI/API export
   and import for external review.
6. Prevent sealing when the active recipe or policy requires unresolved
   reviews.
7. Add inter-reviewer and supersession handling without claiming statistical
   meaning that has not been designed.

**Deliverables:** Review queues, correction plans, sampling, review exchange
format, GUI, and audit trail.

**Exit evidence:** Required-review fixtures cannot seal until resolved; every
correction replays from immutable inputs; old decisions remain auditable after
supersession.

**Non-goals:** Multi-tenant accounts or a cloud annotation platform.

## Phase 15 — Measure and engineer scale, streaming, and sharding

**Goal:** Replace unknown scale behavior with named, reproducible support
tiers and bounded-resource execution.

**Current evidence:** No retained corpus benchmark or public scale guarantee
exists. Exact targets must follow measurement.

**Work:**

1. Build deterministic benchmark corpora that vary file count, total bytes,
   record count, row length, nesting, PDF pages, duplicate rate, and output
   container.
2. Record baseline wall time, CPU, peak resident memory, disk amplification,
   object count, startup, cancellation, and resume on named hardware/software.
3. Publish supported corpus tiers and targets only after baseline review.
4. Profile hot paths and memory retention. Optimize measured bottlenecks rather
   than rewriting stages speculatively.
5. Introduce iterator/streaming APIs and external sorting where compatible with
   deterministic ordering, identity, curation, and leakage grouping.
6. Add incremental parse/clean reuse, bounded queues, backpressure, progress
   facts, checkpoint/resume, and explicit disk-space preflight.
7. Add deterministic JSONL/Parquet sharding with shard receipts and global
   semantic fingerprints.
8. Test crash recovery, cancellation, disk exhaustion, file descriptor limits,
   large individual records, and cross-platform reproducibility.
9. Keep small-corpus ergonomics and results unchanged unless a versioned
   migration is required.

**Deliverables:** Benchmark suite and reports, declared tiers, profiler
evidence, bounded-resource pipeline, shards, resume behavior, and regression
budgets.

**Exit evidence:** All declared tiers meet targets set before optimization
acceptance; benchmark regressions fail CI or release gates at documented
thresholds; semantic outputs match the non-streaming oracle on shared fixtures.

**Non-goals:** Claiming unlimited dataset size or distributed execution without
evidence.

## Phase 16 — Establish a safe extension architecture

**Goal:** Let the supported matrix grow without hard-coding every parser,
objective, validator, exporter, and consumer into central conditionals.

**Dependencies:** Stable contracts from the completed phases among 3–15;
deferred optional phases (for example Phase 12) are excluded, matching the
program ledger's dependency graph.

**Work:**

1. Extract internal typed registries/protocols for source parsers, row mappers,
   deterministic constructors, quality checks, container exporters, and
   consumer profiles.
2. Define capability declarations, contract versions, dependency extras,
   deterministic requirements, diagnostics, fixtures, and discovery metadata.
3. Keep built-ins and third-party plugins distinct. Begin with internal
   registries; approve external executable plugins only after threat modeling.
4. Define process isolation, permissions, network policy, resource limits,
   signing/trust, and crash containment before loading untrusted plugins.
5. Publish a compatibility test kit with golden source/row/export fixtures and
   negative cases.
6. Define lifecycle rules: experimental, supported, deprecated, removed, and
   migrated.
7. Ensure a missing or broken optional plugin cannot prevent core startup or
   corrupt a workspace.

**Deliverables:** Internal extension protocols, registry, test kit, lifecycle
policy, and—only if approved—sandboxed third-party plugin boundary.

**Exit evidence:** At least one built-in parser and one exporter are migrated
through the protocol with identical golden outputs; a broken optional extension
fails in isolation; compatibility errors name exact contract versions.

**Non-goals:** Arbitrary in-process Python execution from a dataset project.

## Phase 17 — Add governed advanced dataset families

**Goal:** Extend beyond deterministic source extraction only when the semantic
and evidence contracts are adequate.

**Candidates:** User-provided classification labels, preference pairs/rankings,
unpaired feedback, tool-call conversations, stepwise supervision, and optional
source-grounded generated candidates. Each is a separate admission decision.

**Work:**

1. Define semantic row and validation contracts for admitted labeled or
   preference data before adding consumer mappings.
2. Import user-provided labels, chosen/rejected pairs, rankings, tools, and
   feedback only with field-level provenance and explicit missing/invalid
   policies.
3. Add leakage and split policies appropriate to shared prompts, responses,
   entities, conversations, and annotators.
4. Add review and quality metrics appropriate to each family.
5. For optional generation, require a separate provider/model adapter with
   model identity and immutable revision, prompt/system digests, parameters,
   supplied evidence, provider/runtime version, output, reproducibility limit,
   cost/network disclosure, and required review policy.
6. Keep generation off by default and outside deterministic release claims.
7. Add consumer profiles only after the semantic family passes its own core
   acceptance tests.
8. Do not implement multimodal targets until the canonical evidence and bundle
   model can bind non-text assets safely.

**Deliverables:** Only admitted advanced semantic contracts, import/review
flows, optional generator boundary, validation, and profile mappings.

**Exit evidence:** Every target or preference label resolves to user-provided
evidence, a declared deterministic derivation, or fully governed generation;
unsupported advanced forms fail closed; deterministic workflows remain
network-free and bit/semantically reproducible under their existing claims.

**Non-goals:** Treating synthetic data as source truth or making generated data
a prerequisite for the standalone product.

## Phase 18 — Complete the goal-first Mac workbench

**Goal:** Make the full independent workflow approachable without hiding
contracts or rebuilding them in Swift.

**Dependencies:** Stable discovery, export, mapping, quality, and review APIs.

**Work:**

1. Replace Aptus-centered compile copy with project creation organized around
   Sources, Goal, Review, Compile, Exports, History, and optional Integrations.
2. Support document, dataset-row, and mixed project modes with preflight
   inventory and mapping preview.
3. Provide progressive disclosure: plain-language safe defaults with inspectable
   advanced recipe, curation, split, profile, and validation settings.
4. Show sample source recovery, mapping, semantic row, supervised region,
   quality findings, exclusions, split facts, and export destination before
   publication.
5. Add generic and named-profile export flows that always display the source
   bundle and receipt relationship.
6. Add review queues, corrections, reruns, diff between revisions, and export
   verification.
7. Surface CLI/API equivalents for reproducibility and support.
8. Add accessibility, keyboard navigation, large-dataset virtualization,
   localization readiness, and error-recovery testing.
9. Keep subprocess and service calls asynchronous and cancelable.
10. Add UI tests for the final acceptance workflow and digest parity.

**Deliverables:** Cohesive independent workbench, onboarding, preview,
quality/review, export/profile UI, parity and UI tests.

**Exit evidence:** A first-time test user can complete the final workflow on a
clean Mac without Aptus or terminal intervention; artifacts and receipts match
the CLI golden path; usability findings meet predeclared acceptance criteria.

**Non-goals:** Implementing dataset policy in Swift or hiding evidence behind a
single opaque “make dataset” button.

## Phase 19 — Complete automation and optional publication boundaries

**Goal:** Support reproducible pipelines, CI, and opt-in sharing without turning
the local compiler into a required cloud service.

**Work:**

1. Extend versioned YAML/project specs to cover input mode, mappings, goal,
   recipe, curation, split, validation, export plans, and consumer profiles.
2. Provide schema generation, dry run, lockfile, environment inspection,
   deterministic exit codes, machine-readable diagnostics, and resume.
3. Bring MCP to parity for discovery, preflight, mapping, quality, review,
   export, and verification while retaining constrained local defaults.
4. Add CI examples that compile from retained fixtures and verify committed
   semantic fingerprints without storing private data.
5. Design optional Hugging Face Hub or other publication adapters as separate
   authenticated actions over a verified export. Require explicit repository,
   visibility, revision, metadata, credential source, dry run, and upload
   receipt.
6. Never embed credentials in workspaces, bundles, specs, logs, or receipts.
7. Add retry/idempotency, conflict, partial-upload, offline, and revocation
   behavior for network adapters.
8. Keep hosted training job launch outside core scope unless separately
   authorized and contracted.

**Deliverables:** Complete declarative automation, local MCP parity, CI
examples, and only approved opt-in publication adapters.

**Exit evidence:** A locked project spec reproduces the same semantic dataset
and verified exports on supported clean hosts; network publication is absent
from the default path and produces an auditable remote revision/receipt when
explicitly invoked.

**Non-goals:** Accounts, billing, telemetry, required cloud storage, or silent
upload.

## Phase 20 — Cut the stable independent 1.0 product

**Goal:** Release a supportable product whose claims are bounded by retained
evidence.

**Dependencies:** Required work from Phases 0–19; optional candidate formats,
profiles, OCR, generation, and publishing may remain excluded if their gates
do not pass.

**Work:**

1. Freeze the 1.0 support matrix for platforms, Python, macOS, inputs, goals,
   semantic rows, containers, profiles, corpus tiers, and optional extras.
2. Complete migration paths from all supported workspace, bundle, mapping,
   recipe, export, and profile versions.
3. Run dependency/license inventory, vulnerability review, parser threat model,
   secret scan, artifact reproducibility, and provenance review.
4. Run full clean-machine CLI and Mac workflows without Aptus; retain logs,
   manifests, expected digests, exports, receipts, and verification reports.
5. Build signed/notarized/stapled Mac artifacts if the public Mac app is in the
   1.0 matrix; verify Gatekeeper and Finder workflows on a clean Mac.
6. Build and inspect Python source/wheel artifacts, install them in supported
   environments, and run golden compiles with only declared dependencies.
7. Run every supported consumer profile against pinned consumer versions in
   isolated release jobs. Profile failure blocks that profile's support claim,
   not the independent core release unless included in the frozen matrix.
8. Publish full user, mapping, goal, export, profile, troubleshooting,
   security, privacy, migration, and support-lifecycle documentation.
9. Define semantic versioning, compatibility windows, upstream profile review
   cadence, deprecation notice, vulnerability response, and release rollback.
10. Make the maturity/version change only after the evidence index is complete
    and reviewed.

**Deliverables:** Veriformis 1.0 artifacts, frozen support matrix, retained
release evidence, migration guides, profile compatibility report, and support
policy.

**Exit evidence:** Every 1.0 claim links to a passing clean-machine,
contract/conformance, performance, security, or migration result; the primary
golden path contains no Aptus; unsupported candidates are explicitly excluded
rather than weakly claimed.

---

## 7. Cross-phase verification strategy

Every phase is incomplete until proportional evidence exists at all affected
layers:

| Layer | Required evidence |
| --- | --- |
| Contracts | Strict loaders, unknown/missing field refusal, identity replay, version/migration tests |
| Unit | Pure mapping, validation, serialization, diagnostics, and error behavior |
| Property | Determinism, ordering, Unicode, path, round-trip, and tamper invariants |
| Golden | Representative supported inputs to verified bundle and export receipts |
| Negative | Malformed, ambiguous, unsupported, lossy, stale, interrupted, and adversarial fixtures |
| Parity | Python service, CLI, MCP, and workbench resolve to identical plans and semantic outputs |
| Consumer | Produced packs load through pinned official consumer paths |
| Performance | Named corpus/hardware, peak memory, throughput, disk, cancellation, and regression budget |
| Security | Untrusted path/input handling, dependency and network boundary, secret and artifact review |
| Usability | Predeclared task completion and comprehension criteria for goal/mapping/export workflows |
| Release | Clean-machine install, compile, verify, export, migration, and artifact inspection |

Test totals are evidence snapshots, not goals. New phases must add the tests
that prove their contracts without treating a larger count as quality by
itself.

## 8. Documentation and claim discipline

At every merge:

1. `current-status.md` states only implemented and passing behavior.
2. The support registry is generated or checked against actual dispatch,
   objective, row, container, and profile registries.
3. User docs name trust grade, loss behavior, and last-tested consumer versions
   next to compatibility claims.
4. This roadmap tracks planned work; it never becomes proof of implementation.
5. Historical plans remain records but cannot override current status or this
   execution order.
6. External official documentation review dates are recorded because trainer
   contracts can change.
7. No “any format,” “lossless,” “production-ready,” “private,” “safe,” or
   “compatible” claim appears without its bounded definition and evidence.

## 9. Dependency and ordering rules

1. Phases 0–4 are sequential and form the architectural critical path.
2. Phase 5 and Phase 6 may proceed in parallel only after Phase 4 contracts are
   stable; Phase 7 depends on both.
3. Phase 8 depends on generic export and taxonomy, not columnar output.
4. Phase 9 depends on the export foundation and optional-dependency policy.
5. Each Phase 10 profile is independently admitted and may ship separately.
6. Phase 11 precedes OCR and broad format expansion.
7. Phase 13 quality facts precede Phase 14 review gates that act on them.
8. Phase 15 measures before setting scale targets or accepting optimizations.
9. Phase 16 follows stable internal contracts; premature public plugin APIs are
   prohibited.
10. Phase 17 advanced semantics cannot be smuggled into generic exporters or
    consumer profiles.
11. Phase 18 may incrementally expose completed capabilities, but it cannot
    invent surface-only policy.
12. Phase 20 freezes only the subset whose prior gates passed. Optional work
    may be deferred without weakening the independent core.

## 10. Risk register

| Risk | Evidence or cause | Control |
| --- | --- | --- |
| Aptus remains de facto product center | Current defaults and release copy | Phase 1 standalone defaults and release job |
| “Format” hides training semantics | Ecosystems reuse JSONL for different tasks/loss | Phase 3 taxonomy and compatibility validation |
| Exporters become a second pipeline | Convenience pressure | Verified-bundle-only export contract; no membership mutation |
| Upstream trainer formats drift | Current external projects evolve | Version-pinned profiles, review dates, conformance CI, deprecation |
| Optional features bloat install | Current base already includes MCP/PDF/YAML | Extras, lazy discovery, core-no-extra CI |
| Finder mutates strict bundles | Retained `.DS_Store` evidence | Phase 2 immutable/package boundary; never ignore unknown files silently |
| UI freezes or loses process output | Synchronous `waitUntilExit()` on main-actor path | Background process actor, cancellation and volume tests |
| Existing dataset mapping invents meaning | Ambiguous columns/roles | Preview-only detection, explicit confirmation, row provenance |
| OCR injects bad targets | No OCR quality contract today | Evaluated optional engine, page evidence, thresholds/review |
| Quality heuristics overclaim | False positives/negatives | Versioned findings, labeled calibration, human inspection |
| Scale rewrite breaks determinism | In-memory architecture and no benchmark | Measure first; oracle comparison; semantic fingerprints |
| Plugins execute untrusted code | Extensibility pressure | Internal registries first; threat model and isolation before public plugins |
| Generated data appears authoritative | Model output uncertainty | Separate governed family, lineage, required review, offline core unchanged |
| Roadmap scope becomes endless | Many candidate formats/trainers | Admission gates, frozen milestone matrices, optional deferral |

## 11. Explicit exclusions from the committed path

The roadmap does not commit to HDF5, WARC, every office format, every trainer,
multimodal training, cloud collaboration, model training, job orchestration,
accounts, billing, telemetry, or distributed execution. Any may be researched
later, but none is supported without the admission and phase evidence required
above. This protects the core goal: a trustworthy independent tool that turns
real source material and existing rows into useful, verifiable training
datasets.

## 12. Immediate execution packet

Implementation should begin with one bounded packet covering Phases 0–2:

1. Refresh authority and current status at the analyzed baseline.
2. Add standalone golden release evidence and split optional integration tests.
3. Change Aptus defaults to explicit opt-in across CLI, MCP, and Mac.
4. Move all primary UI/documentation language to trainer-neutral terms.
5. Repair subprocess concurrency and cancellation.
6. Decide and prove the Finder-safe bundle distribution boundary.
7. Rerun lock, lint, Python, Swift, parity, install, golden standalone seal, and
   external-digest verification gates.

Only after that packet passes should Phase 3 contract design begin. This keeps
the first implementation step small enough to review while directly restoring
the product's intended independent identity.

## Related authority

- [Independent Product Analysis](../analysis/2026-08-11-independent-product-analysis.md)
- [Product Contract](../product-contract.md)
- [Current Implementation Status](../current-status.md)
- [Architecture](../architecture.md)
- [Dataset Construction Contract v1](../contracts/dataset-construction-v1.md)
- [Finished Dataset Contract v1](../contracts/finished-dataset-v1.md)
- [Beta Limitations](../beta-limitations.md)
- [Release Guide](../release.md)
