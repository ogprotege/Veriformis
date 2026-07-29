# Group 2 Dataset Construction Implementation Plan

**Status:** Complete

**Roadmap scope:** Steps 7 through 10

**Contract:** [Dataset Construction Contract v1](../../../docs/contracts/dataset-construction-v1.md)

**Starting point:** M1 core plus the merged Group 1 integrity foundation

**Last reviewed:** 2026-07-29

**Next review:** Any contract change or Group 3 integration with construction records

## Outcome

Build the deterministic construction core that turns verified cleaned source
state into evidence-bearing candidates and immutable accepted records under a
versioned recipe. The work stops before Group 3 curation, splitting,
serialization, exact validation, and sealing.

## Fixed decisions

- Keep the raw-source-to-finished-dataset product doctrine. Cleaned text is an
  intermediate state or an explicit `full_text` objective.
- Support exactly five deterministic objectives: `full_text`, `continuation`,
  `section_reconstruction`, `before_after_transformation`, and
  `structured_field`.
- Make no LLM or network calls. Do not add a summary objective.
- Use product row-schema names `text`, `prompt_completion`,
  `instruction_output`, and `messages`. Legacy `completion`, `instruction`, and
  `chat` names are not recipe contracts.
- Reuse `SourceEvidence` for visible text. Add separate `IRFieldEvidence` for
  values present only in strict IR.
- Persist construction through workspace revision schema v2 and an atomic
  `construct` stage. The workspace layout remains schema v1.
- Expose exactly `recipe` and `result` from construct. Candidate, decision,
  review, evidence, and record collections live inside `ConstructionResult`.
- Preserve Group 3 boundaries. Group 2 records later policy declarations but
  never reports them as executed.

## Ordered implementation

### 1. Pin contracts and failures

1. Add public contract, schema, producer, objective, row-schema, and error-code
   constants.
2. Add strict schema tests for missing fields, unknown fields, wrong types,
   unsupported versions, Unicode preservation, identity tampering, and duplicate
   IDs.
3. Pin negative semantic tests for fabricated evidence, copied-text summary
   claims, empty targets, invalid continuation boundaries, missing section
   structure, unreplayable transformations, and unbound structured leaves.

**Exit:** Contract constants, fixtures, and documentation agree before runtime
behavior changes.

### 2. Introduce workspace revision schema v2

1. Add `construct` after `chunk` with `parse`, `clean`, and `chunk` as its
   upstream dependencies.
2. Add an explicit v1 to v2 migration with version-aware historical loading.
3. Preserve every v1 source, artifact, and legacy stage fact unchanged,
   including complete, failed, stale, and absent states.
4. Add only `construct` as absent. Keep legacy format, validation, and seal
   states exactly as they were.
5. Test interruption before commit, stale-parent conflict, idempotence, corrupt
   v1 refusal, historical verification, and rollback behavior.

**Exit:** Migration either atomically exposes one valid revision-schema-v2 head
that differs only by the absent construct state, or leaves the verified v1 head
current.

### 3. Implement construction models and identity

1. Add strict immutable models and serialization for `TrainingObjective`,
   `DatasetRecipe`, `ConstructionPass`, `IRFieldEvidence`, evidence-bound
   `RecordField` values, candidates, promotion decisions, reviews, dataset
   records, diagnostics, and construction results.
2. Derive every identity from exact canonical semantic content.
3. Recompute identities and cross-references on load. Require canonical artifact
   bytes for persisted recipe and result loaders.
4. Keep audit timestamps and revision IDs outside portable semantic identities.

**Exit:** Every model round-trips exactly and rejects malformed, stale,
cross-source, or identity-inconsistent data.

### 4. Add field-level evidence

1. Bind every constructed text field to existing reconstructible
   `SourceEvidence` plus any ordered derivation.
2. Implement `IRFieldEvidence` resolution against immutable strict IR artifacts.
3. Require one verified evidence value for every constructed `RecordField` and
   exact equality between each field value and its evidence output digest.
4. Cover link targets, image sources or titles, and other selected IR-only
   metadata with positive and tamper tests.
5. Keep `structured_field` disabled until its complete selected field set has
   verifiable evidence.

**Exit:** No constructed field can survive with missing, mismatched, fabricated,
or cross-source evidence.

### 5. Implement recipe and pass execution

1. Validate exact `source_ids`, `cleaning_config_digest`, segmentation, ordered
   pass sequences, deferred curation and split literals, objective fields,
   row-schema declaration, required gates, and review policy.
2. Execute passes in stable source and unit order.
3. Record one typed construction diagnostic for each zero-output input fact.
4. Prevent access to clock, randomness, network, undeclared environment, and
   undeclared filesystem state.
5. Bind constructor identity, version, configuration, inputs, outputs, and
   checks into each candidate.

**Exit:** Reordering or changing any semantic pass input changes the appropriate
identity, while identical inputs reproduce byte-identical semantic outputs.

### 6. Implement the record lifecycle

1. Emit append-only candidates with the objective's exact ordered fields and
   embedded evidence.
2. Emit separate deterministic `accepted`, `rejected`, or `pending_review`
   decisions with typed reasons.
3. Verify required review evidence without changing candidate identity.
4. Promote only accepted candidates into immutable DatasetRecords with unchanged
   fields, evidence, and lineage.
5. Preserve every rejected or pending candidate inside the result.

**Exit:** Required review blocks promotion, deterministic no-review recipes can
promote when their construction gates pass, and no state transition mutates a
prior object.

### 7. Implement all deterministic constructors

1. `full_text`: construct complete evidence-bearing retained sequences.
2. `continuation`: construct ordered source prefix and suffix pairs with exact
   boundary evidence.
3. `section_reconstruction`: construct exact heading-to-section-body targets.
4. `before_after_transformation`: construct replayable before and after pairs
   from recorded transforms.
5. `structured_field`: construct explicit IR-field mappings only after field
   evidence coverage passes.

Each constructor receives positive, rejection, multi-source, Unicode, tamper,
and replay tests.

**Exit:** Every objective meets its field truth conditions, and unsupported
semantic claims fail closed.

### 8. Commit the transactional construct stage

Use exactly this configuration:

```json
{
  "schema_version": "veriformis.construction-stage/v1",
  "recipe_id": "rcp-v1-...",
  "selected_source_ids": ["src-v1-..."]
}
```

Commit exactly:

| Key | Kind | Producer | Version |
| --- | --- | --- | --- |
| `recipe` | `dataset-recipe` | `veriformis.construction.recipe` | `1` |
| `result` | `construction-result` | `veriformis.construction.result` | `1` |

Both artifacts use the complete selected-source scope and full configuration
digest. Before `HEAD` promotion, replay and cross-validate the recipe, inputs,
passes, evidence, candidates, decisions, review evidence, dataset records,
artifact metadata, and result digest.

Construct has no downstream legacy stage in Group 2. Its commit leaves current
format, validation, and seal facts unchanged. Step 13 changes formatting to
consume construction records.

**Exit:** An integrity failure leaves the prior head current. A successful
commit exposes only the two declared construction outputs and does not rewrite
unaffected legacy stages.

### 9. Close Group 2

1. Run the existing acceptance corpus through multi-source construction.
2. Prove deterministic candidate, record, and result identities across repeated
   semantic runs.
3. Confirm every Group 2-only expected failure has become an ordinary passing
   test. Keep joint Step 8 and 15 or Step 10 and 13 cases marked honestly when
   their later half remains unimplemented.
4. Update active current-status, architecture, CLI, development, README,
   contributing, documentation-index, product-contract, and roadmap claims.
5. Record an independent architecture review and the exact Group 3 handoff.

**Exit:** Every item in the contract's Group 2 exit gate passes.

## Acceptance matrix

| Area | Required proof |
| --- | --- |
| Versioning | Strict schema rejection and version-aware loaders |
| Identity | Recomputed IDs, duplicate rejection, Unicode preservation, multi-source scope |
| Migration | Atomic revision v1 to v2 conversion, exact legacy-fact preservation, interruption recovery, immutable history |
| Evidence | Exact SourceEvidence replay and IRFieldEvidence resolution per RecordField |
| Recipes | Exact objective, policy, row-schema, pass order, and source-selection binding |
| Lifecycle | Append-only candidates, auditable decisions, review enforcement, immutable records |
| Constructors | Five truthful deterministic objectives and negative semantic cases |
| Replay | Stable candidate, record, result, and artifact digests |
| Transaction | Exact config, two output keys, producer metadata, full digest and source scope |
| Boundary | No LLM, summary objective, curation claim, split claim, row-emission claim, or seal claim |

## Exact deferrals

- Step 11: comprehensive curation and quality policy.
- Step 12: leakage-safe split assignment and assignment digest.
- Step 13: serializers consuming accepted records.
- Step 14: emitted Aptus-native rows and masking metadata.
- Step 15: exact whole-dataset validation.
- Step 16: atomic closed-set seal and independent verification.
- Steps 17 through 19: `PipelineService`, thin CLI, and dual-objective M1.1
  completion.
- Step 20: broader input adapters.
- Step 25: separately approved model-assisted construction.

## Required verification

```text
uv lock --check
uv run ruff check src tests
uv run pytest -q
git diff --check
```

Focused suites must also cover contracts, migration, evidence, construction,
lifecycle, constructors, workspace invalidation, and deterministic replay.

## Closeout evidence

Group 2 closed on 2026-07-29 after independent architecture re-review resolved
all two High, five Important, and one Advisory findings. The final repository
gate passed with 457 tests and eight strict expected failures assigned to
roadmap Steps 13 through 16. Running the known-gap suite with expected failures
disabled reproduced exactly those eight later-step failures and no Group 2
defect.
