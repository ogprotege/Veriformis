# Veriformis Build Roadmap

**Status:** Authoritative post-M1 roadmap when merged into `main`

**Created:** 2026-07-29

**Applies after:** The documentation-baseline pull request is merged

**Current implementation:** M1 core at version `0.1.0`

## Product objective

Veriformis owns the complete transformation from heterogeneous raw sources to finished, training-ready datasets. It ingests, reconstructs, cleans, normalizes, constructs records, curates, balances, splits, formats, validates, and seals the result. A cleaned corpus is an internal compiler state and can also be a selected full-sequence training objective. It is not the limit of the product.

The next implementation work begins only after the documentation pull request containing this roadmap has been reviewed and merged. That merge establishes the product contract against which Group 1 will be implemented.

## Version boundary

Steps 1 through 24 build and deliver the deterministic product. The dataset pipeline makes no LLM calls and performs no remote model generation through Group 7. Step 25 is optional future work, is not part of deterministic v1, and is not a prerequisite for Step 26 or public release. It requires a separate owner-approved implementation plan before Group 8 may begin. A deterministic public release may proceed from Group 7 directly to Group 9 while Step 25 remains deferred.

## Complete numbered sequence

1. **Product and acceptance contract.** Translate the product-level contract into exact, versioned guarantees, supported training objectives, and executable M1.1 acceptance fixtures.
2. **Regression tests.** Pin every confirmed identity, provenance, cleaning, validation, and sealing failure before changing implementation behavior.
3. **Transactional workspace.** Introduce versioned `WorkspaceRevision` state, atomic stage commits, stale-stage invalidation, and safe recovery.
4. **Source-scoped identities.** Make source, artifact, transform, chunk, candidate, record, and split identities deterministic and collision-resistant.
5. **IR, diagnostics, and source evidence.** Strengthen the canonical IR, record parser loss explicitly, and create immutable source-range evidence.
6. **Replayable cleaning plans.** Make preview and application consume the same source-scoped edit plan while preserving structure and recording every change.
7. **Training objectives and recipes.** Introduce versioned `TrainingObjective` and `DatasetRecipe` contracts.
8. **Construction passes and evidence.** Introduce ordered `ConstructionPass` operations and field-level `SourceEvidence` bindings.
9. **Record lifecycle.** Define `ConstructionPass -> CandidateRecord -> immutable DatasetRecord`, including rejection and optional review evidence.
10. **Deterministic constructors.** Build truthful raw-source constructors for full-text, continuation, reconstruction, transformation, and structured-field objectives.
11. **Curation and quality.** Add deduplication, filtering, contradiction checks, coverage accounting, balancing, and explicit rejection reasons.
12. **Leakage-safe splitting.** Create authoritative deterministic train and evaluation assignments with leakage groups and an assignment digest.
13. **Construction and serialization separation.** Make serializers lower accepted records without inventing the training objective.
14. **Aptus-native output records.** Emit supported `text`, prompt-completion, instruction-output, and structured `messages` rows with provenance metadata.
15. **Exact dataset validation.** Validate recipe semantics, evidence, records, curation results, split assignment, schema, encoding, and compatibility as one snapshot.
16. **Atomic sealing and verification.** Seal a normalized closed file set atomically and provide independent bundle verification with an external digest or attestation.
17. **Pipeline service.** Move complete orchestration into a typed, surface-neutral `PipelineService`.
18. **Thin CLI adapter.** Make the CLI translate arguments and results without owning pipeline state or policy.
19. **Dual-objective M1.1 acceptance.** From one raw multi-source corpus, produce both a full-text dataset and a source-derived supervised dataset through API and CLI.
20. **Full declared ingest.** Add digitally born PDF, HTML, CSV, JSON, and JSONL with explicit extraction-loss diagnostics and named OCR refusal.
21. **Expanded deterministic recipe library.** Add more source-grounded builders, curation policies, statistics, balancing controls, and repeatable YAML pipelines.
22. **MCP automation.** Expose the same recipe, preview, construction, validation, sealing, and verification operations through a constrained local MCP adapter.
23. **Versioned Aptus handoff.** Define and verify the shared bundle descriptor, row semantics, masking expectations, sealed splits, evidence metadata, and backend capabilities.
24. **SwiftUI dataset workbench.** Deliver the complete workflow as a Mac application with source, cleaning, construction, curation, split, validation, and seal views.
25. **Governed model-assisted construction.** Under a separate owner-approved plan, add an optional `GeneratorPass` for source-grounded QA, dialogue, classification, and transformation candidates with complete generation lineage and policy gates. This is not part of deterministic v1 and is not a public-release prerequisite.
26. **Public release gates.** Complete documentation, supported-platform CI, dependency and artifact evidence, packaging, signing, notarization, migration tests, and release verification.

## Grouped execution order

### Documentation prerequisite

The documentation-baseline pull request must be merged before Group 1 begins. No numbered implementation step starts on the documentation branch.

### Group 1: Integrity foundation

**Steps 1 through 6**

1. Product and acceptance contract
2. Regression tests
3. Transactional workspace
4. Source-scoped identities
5. IR, diagnostics, and source evidence
6. Replayable cleaning plans

**Exit gate:** The new contracts are documented, the regression suite passes, and each confirmed defect remains pinned by a test that fails without its repair. Multi-source workspace revisions are atomic, identities are source-scoped and collision-resistant, duplicate identities are rejected, parser loss is explicit, provenance resolves to immutable source evidence, and cleaning preview equals application.

### Group 2: Dataset construction core

**Steps 7 through 10**

7. Training objectives and recipes
8. Construction passes and evidence
9. Record lifecycle
10. Deterministic constructors

**Exit gate:** Raw sources can produce evidence-bearing candidate records under versioned recipes. Accepted candidates become immutable dataset records, and every constructed field has a truthful deterministic derivation.

### Group 3: Finished-dataset pipeline

**Steps 11 through 16**

11. Curation and quality
12. Leakage-safe splitting
13. Construction and serialization separation
14. Aptus-native output records
15. Exact dataset validation
16. Atomic sealing and verification

**Exit gate:** Veriformis owns the finished dataset. Curation decisions are explicit, related records cannot leak across splits, serializers preserve the selected objective, validation is bound to the exact artifacts, and tampering or stale state prevents sealing.

### Group 4: M1.1 completion

**Steps 17 through 19**

17. Pipeline service
18. Thin CLI adapter
19. Dual-objective M1.1 acceptance

**Exit gate:** The same raw corpus produces both required dataset objectives through the Python API and CLI with identical canonical digests, evidence graphs, split assignments, validation facts, and verified bundles. Nothing after Group 4 begins until this gate passes.

### Group 5: Input and recipe expansion

**Steps 20 through 21**

20. Full declared ingest
21. Expanded deterministic recipe library

**Exit gate:** Every declared v1 input either compiles with explicit coverage evidence or fails with a named limitation. Multiple deterministic recipes produce measurable, repeatable datasets from the supported formats.

### Group 6: Integrations

**Steps 22 through 23**

22. MCP automation
23. Versioned Aptus handoff

**Exit gate:** Python, CLI, and MCP produce identical results. Aptus consumes sealed partitions or exactly reproduces and verifies their assignment digest while preserving row semantics and provenance metadata.

### Group 7: macOS product

**Step 24**

24. SwiftUI dataset workbench

**Exit gate:** A user can complete the raw-source-to-sealed-dataset workflow without the terminal, and the application produces the same canonical result as the CLI.

### Group 8: Advanced construction

**Step 25**

25. Governed model-assisted construction

Group 8 requires separate owner approval. It may remain deferred while the deterministic product advances to Group 9.

**Exit gate:** Generated candidates retain model, prompt, parameter, source-evidence, output, quality, and review lineage. They pass through the same curation, split, validation, and sealing contracts as deterministic candidates.

### Group 9: Public release

**Step 26**

26. Public release gates

**Exit gate:** A clean supported Mac can install the signed and notarized product, compile the golden raw corpus, verify the final bundles, and hand them to a compatible Aptus release with independently recorded evidence.

## Ordering rules

- Complete Groups 1 through 7 in order unless this document is revised through review.
- Do not begin a later required group while an earlier required exit gate is incomplete. Group 8 follows its explicit optional-work exception below.
- Add tests and documentation within every group rather than postponing them to Step 26.
- Preserve the deterministic and offline dataset-pipeline boundary through Group 7 and in any deterministic release.
- Group 8 is an optional future branch. Group 9 may follow Group 7 directly when Step 25 is deferred.
- Begin Step 25 only under a separate owner-approved plan. It must not weaken deterministic compilation or provenance guarantees.
- Record build, publication, installation, signing, notarization, and downstream compatibility as separate release states.

## Related documentation

- [Product contract](../product-contract.md)
- [Current implementation status](../current-status.md)
- [Architecture](../architecture.md)
- [Completed M1 implementation plan](../superpowers/plans/2026-07-28-veriformis-m1.md)
