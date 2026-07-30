# Veriformis Work in Progress

**Status:** Active, non-authoritative working inventory

**Implementation baseline reviewed:** `ff938ac` on `origin/main`, after the
Group 3 merge

**Product version:** `0.1.0` development alpha

**Last reviewed:** 2026-07-30

**Next review:** Any merged implementation group, contract or roadmap change,
or listed-item status change

> **Authority:** This file is a convenience tracker. It does not define product
> truth. [Current implementation status](docs/current-status.md) controls
> present capability claims. The
> [build roadmap](docs/plans/2026-07-29-veriformis-roadmap.md) controls work
> order and exit gates. The applicable versioned contract controls guarantees
> within its scope. If this file conflicts with those sources, the canonical
> source controls. Test totals and verification results are dated snapshots.

## Product target

Veriformis owns the difficult path from heterogeneous raw source material to a
finished, integrity-bearing training dataset:

```text
raw source capture
  -> canonical recovery -> cleaning -> chunking -> construction
  -> curation -> leakage-safe splitting -> product rows
  -> exact validation -> atomic seal -> independent verification
```

Canonical IR and cleaned text are accountable intermediate states. A
`full_text` recipe may select cleaned text as exact target content. It becomes
a finished dataset only after construction, curation, splitting, formatting,
validation, sealing, and verification. The deterministic pipeline remains
local, offline, and free of LLM generation.

## Current boundary

- [x] M1 core is implemented.
- [x] Groups 1 through 3 are implemented and merged.
- [x] Steps 1 through 16 are complete.
- [ ] Steps 17 through 26 remain.
- [ ] Group 4 is the next required group.
- [ ] M1.1 is not complete.
- [ ] Public release gates are not complete.

The current stage-command runtime is:

```text
parse -> clean -> chunk -> construct -> curate -> split
      -> format -> validate -> seal -> verify
```

## Completed and verified

### Group 1: Integrity foundation

**Status:** Complete

- [x] 1. Product and acceptance contract
- [x] 2. Regression tests
- [x] 3. Transactional workspace
- [x] 4. Source-scoped identities
- [x] 5. IR, diagnostics, and source evidence
- [x] 6. Replayable cleaning plans

**Delivered:** Immutable workspace revisions, atomic commits, stale-stage
invalidation, deterministic identities, explicit parser loss, source-grounded
evidence, and one cleaning plan shared by preview and application.

**Evidence:** [Integrity Contract v1](docs/contracts/integrity-v1.md),
[current status](docs/current-status.md), and the
[Group 1 architecture review](dev/active/group-1-integrity-foundation/architecture-review.md).

### Group 2: Dataset construction core

**Status:** Complete

- [x] 7. Training objectives and recipes
- [x] 8. Construction passes and evidence
- [x] 9. Record lifecycle
- [x] 10. Deterministic constructors

**Delivered:** Five deterministic objectives, versioned recipes, ordered
passes, field-level evidence, auditable decisions, immutable accepted records,
and exact construction replay.

**Evidence:**
[Dataset Construction Contract v1](docs/contracts/dataset-construction-v1.md),
the [Group 2 plan](dev/active/group-2-dataset-construction/plan.md), and the
[Group 2 code review](dev/active/group-2-dataset-construction/group-2-dataset-construction-code-review.md).

### Group 3: Finished-dataset pipeline

**Status:** Complete

- [x] 11. Curation and quality
- [x] 12. Leakage-safe splitting
- [x] 13. Construction and serialization separation
- [x] 14. Contract product rows
- [x] 15. Exact dataset validation
- [x] 16. Atomic sealing and verification

**Delivered:** Deterministic curation, explicit coverage, transitive leakage
groups, authoritative train and evaluation assignments, four product row
schemas, aligned provenance, 17 validation gates, atomic six-file bundles, and
independent verification.

**Evidence:** [Finished Dataset Contract v1](docs/contracts/finished-dataset-v1.md),
the [Group 3 plan](dev/active/group-3-finished-dataset/plan.md), and the
[Group 3 code review](dev/active/group-3-finished-dataset/group-3-finished-dataset-code-review.md).

## Next required work: Group 4

### Group 4: M1.1 completion

**Status:** Next

- [ ] 17. Pipeline service
  - Move complete orchestration into a typed, surface-neutral
    `PipelineService`.
  - Keep pipeline state and policy out of interface adapters.
- [ ] 18. Thin CLI adapter
  - Make CLI commands translate inputs, service results, and failures.
  - Preserve current command behavior and fail-closed guarantees.
- [ ] 19. Dual-objective M1.1 acceptance
  - Compile one raw multi-source corpus into a full-text dataset.
  - Compile the same corpus into a source-derived supervised dataset.
  - Exercise both objectives through the Python API and CLI.
  - Prove identical canonical digests, evidence graphs, split assignments,
    validation facts, and verified bundles across both surfaces.

**Exit gate:** The same raw corpus produces both required dataset objectives
through the Python API and CLI with identical canonical digests, evidence
graphs, split assignments, validation facts, and verified bundles. Nothing
after Group 4 begins until this gate passes.

**Execution checklist:**

1. Write and approve the Group 4 implementation plan.
2. Pin service, CLI-parity, and dual-objective acceptance tests first.
3. Implement `PipelineService` without weakening existing contracts.
4. Refactor the CLI into a thin adapter over the service.
5. Run both objectives from raw sources through verified bundles.
6. Complete repository checks and documentation. Run independent review as a
   non-gating quality check unless the Group 4 plan adds it to the gate.

## Later roadmap work

### Group 5: Input and recipe expansion

- [ ] 20. Full declared ingest
  - Add digitally born PDF, HTML, CSV, JSON, and JSONL.
  - Record explicit extraction-loss diagnostics.
  - Refuse OCR with a named limitation.
- [ ] 21. Expanded deterministic recipe library
  - Add source-grounded builders, curation policies, statistics, and balancing.
  - Add repeatable YAML pipelines.

**Exit gate:** Every declared v1 input either compiles with explicit coverage
evidence or fails with a named limitation. Multiple deterministic recipes
produce measurable, repeatable datasets from the supported formats.

### Group 6: Integrations

- [ ] 22. MCP automation
  - Expose recipe, preview, construction, validation, sealing, and verification
    through a constrained local MCP adapter.
- [ ] 23. Versioned Aptus handoff
  - Define the shared bundle descriptor and row semantics.
  - Bind masking expectations, sealed splits, evidence, and backend capability.
  - Prove Aptus consumes authoritative partitions or reproduces their digest.

**Exit gate:** Python, CLI, and MCP produce identical results. Aptus consumes
sealed partitions or exactly reproduces and verifies their assignment digest
while preserving row semantics and provenance metadata.

### Group 7: macOS product

- [ ] 24. SwiftUI dataset workbench
  - Provide source, cleaning, construction, curation, split, validation, and
    seal views.
  - Produce the same canonical result as the CLI.

**Exit gate:** A user can complete the raw-source-to-sealed-dataset workflow
without the terminal, and the application produces the same canonical result
as the CLI.

## Optional work requiring owner approval

### Group 8: Advanced construction

- [ ] 25. Governed model-assisted construction
  - Add an optional `GeneratorPass` for source-grounded QA, dialogue,
    classification, and transformation candidates.
  - Add complete generation lineage and policy gates.

This step requires a separate owner-approved plan. It is not part of
deterministic v1 and does not block Group 9. If approved, every generated
candidate must retain model, prompt, parameters, source evidence, output,
quality, and review lineage. It must pass through the existing finished-dataset
contracts.

**Exit gate:** Generated candidates retain model, prompt, parameter,
source-evidence, output, quality, and review lineage. They pass through the same
curation, split, validation, and sealing contracts as deterministic candidates.

## Final required work

### Group 9: Public release

- [ ] 26. Public release gates
  - Complete documentation and supported-platform CI.
  - Complete dependency review and artifact evidence.
  - Complete package installation and migration verification.
  - Complete macOS packaging, signing, notarization, and release verification.
  - Verify the golden raw corpus and compatible Aptus handoff on a clean Mac.

**Exit gate:** A clean supported Mac can install the signed and notarized
product, compile the golden raw corpus, verify the final bundles, and hand them
to a compatible Aptus release with independently recorded evidence.

## Execution order and dependencies

- Complete required Groups 1 through 7 in order.
- Do not start a later required group before the earlier exit gate passes.
- Add tests and documentation within every group.
- Preserve deterministic and offline dataset compilation through Group 7.
- When Step 25 is deferred, proceed from Group 7 directly to Group 9.
- When Step 25 is approved, proceed from Group 7 through Group 8 to Group 9.
- Do not let Step 25 weaken deterministic compilation or provenance guarantees.
- Track build, publication, installation, signing, notarization, and downstream
  compatibility as separate release states.

## Nonblocking follow-up debt

The Group 1 review recorded two Important architecture deferrals. They do not
reopen the Group 1 gate, but their stated trigger conditions still apply.

- [ ] Bound memory use and deduplicate integrity work before advertising
  large-corpus support.
- [ ] Make parser, rule, and chunker replay version-addressable before changing
  persisted producer behavior.

The Group 3 review recorded three minor maintenance items. They do not reopen
the Group 3 gate.

- [ ] Deeply freeze or strongly type nested `ProductRow.payload` values.
- [ ] Consolidate duplicate closed-contract registries where typing permits.
- [ ] Split `WorkspaceTransaction._validate_stage_semantics` into private
  per-stage validators.

Additional product follow-ups remain unassigned within the numbered roadmap:

- [ ] Add CLI ingestion for completed `ReviewEvidence`. Today,
  `--require-review` leaves candidates pending.
- [ ] Define a retention profile for portable bundles that embed replay
  material. Closed-bundle verification remains workspace-independent, while
  full source replay remains available through workspace history.

## Documentation revamp

**Status:** In review as [PR #6](https://github.com/ogprotege/Veriformis/pull/6)
on `docs/architecture-revamp`; not yet merged to `main`.

What it is: a full documentation overhaul built on a citation-verified
architecture analysis of the current source. It changes documentation only; it
alters no numbered roadmap step, versioned contract, or exit gate.

Done on the branch:

- [x] Architecture deep-dive tree added under `docs/architecture/` (overview,
  layers, dependencies, data flow, entry points) with verified `file:line`
  citations and Mermaid diagrams.
- [x] `docs/architecture.md` rewritten as the architecture hub routing into
  the tree.
- [x] Root `README` and documentation index elevated: pipeline diagram,
  badges, audience reading paths, and a complete documentation map.
- [x] CLI reference and development guide re-verified against source,
  correcting the exit-status table, schema gating, seal failure typing, and
  chunk option constraints.
- [x] `current-status.md` re-verified against code and tests; no capability
  drift. Contracts drift-checked against the implementation; no drift found.
- [x] Review metadata (`Last reviewed` / `Next review`) aligned across the
  reference docs.

Remaining:

- [ ] Review and merge PR #6.
- [ ] Re-verify deep-dive `file:line` citations at the first Group 4 change.
- [ ] Machine-render Mermaid diagrams in CI (currently hand-reviewed).

## Deferred documentation

- [ ] Add the stable Python API reference after `PipelineService` exists.
- [ ] Add the dual-objective M1.1 API and CLI acceptance procedure.
- [ ] Add the versioned Aptus handoff and backend enforcement guidance.
- [ ] Add expanded input, security, release, and migration guidance.
- [ ] Add troubleshooting for the future supported release surface.

## Known current limitations

- Inputs are limited to text, Markdown, DOCX, and listed source-code formats.
- OCR is unsupported.
- There is no stable `PipelineService` or one-command `run` surface.
- There is no YAML pipeline, MCP adapter, or SwiftUI workbench.
- Aptus support validates current row shape only.
- Current Aptus MLX intake rejects plain `text` rows.
- The CLI cannot submit completed human review evidence.
- The minimal bundle omits raw sources and complete replay artifacts.
- External trust requires a manifest digest retained outside the bundle.
- Model-assisted construction remains optional and unapproved.
- CI and packaging do not yet establish public release readiness.

## Verification snapshot

The Group 3 closeout and this baseline review recorded:

```text
uv lock --check             passed
uv run ruff check src tests passed
uv run pytest -q            606 passed
git diff --check            passed
```

A supported two-source raw-input demonstration reached a sealed bundle and
`external_digest` verification. The independent review found no unresolved
Critical, High, or Important defect.

On 2026-07-30 the documentation branch re-ran `uv run pytest -q` (606 passed)
plus link and diagram-fence checks across the revamped documentation; the
pre-push hook repeated the suite green on both documentation commits.

Rerun these checks before calling this snapshot current.

## Maintenance rules

1. Check an item only after its implementation and exit gate merge to `main`.
2. Update this file in the same change that alters a listed status.
3. Keep completed items visible. They preserve execution history.
4. Do not duplicate contract details that belong in a versioned contract.
5. Keep Group 8 separate until the owner approves its implementation plan.
6. Treat Group 4 as the only next required group.
7. Preserve deterministic and offline operation through Group 7.
8. Keep the retained manifest digest and integrity-controlled publication
   parent requirements visible in every future sealing surface.

## Canonical references

- [Current implementation status](docs/current-status.md)
- [Authoritative build roadmap](docs/plans/2026-07-29-veriformis-roadmap.md)
- [Product contract](docs/product-contract.md)
- [Integrity Contract v1](docs/contracts/integrity-v1.md)
- [Dataset Construction Contract v1](docs/contracts/dataset-construction-v1.md)
- [Finished Dataset Contract v1](docs/contracts/finished-dataset-v1.md)
- [Architecture](docs/architecture.md)
- [Architecture tree](docs/architecture/README.md)
- [CLI reference](docs/cli.md)
- [Development guide](docs/development.md)
