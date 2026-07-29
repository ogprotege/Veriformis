# Group 2 Dataset Construction Code Review

**Last Updated:** 2026-07-29

**Review scope:** The complete uncommitted Group 2 diff from `origin/main`, plus
the existing integrity, evidence, chunking, workspace, and product contracts.

**Disposition:** Final independent re-review complete. All original High,
Important, and Advisory findings are resolved. No new Critical, High, or
Important finding was found. Group 2 is ready to close from the code
architecture review scope.

## Executive Summary

The Group 2 implementation now satisfies the reviewed integrity boundary. It
constructs from verified parse, clean, and chunk state. It keeps curation,
split assignment, row lowering, whole-dataset validation, and sealing in Group
3. The workspace migration is explicit, construction commits use two exact
outputs, and semantic replay occurs before `HEAD` promotion.

The repaired implementation proves complete section boundaries from cleaned
IR, freshly validates public construction inputs, preserves present JSON scalar
values, enforces safe promotion and typed identity failures, and covers all five
objectives through the required exit matrix. The original findings remain below
as an audit record and are superseded by the repair verification.

## Repair Verification (2026-07-29)

### Outcome

All eight original findings are resolved: H1, H2, I1 through I5, and A1. The
re-review found no regression and no new Critical, High, or Important issue.

| Finding | Status | Exact repair evidence |
| --- | --- | --- |
| H1, complete section semantics | Resolved | `src/veriformis/construction/constructors.py:444-717` derives heading-delimited units from cleaned IR, requires complete block coverage at lines 484-539, binds every contributing chunk, and diagnoses an unprovable whole section. `tests/construction/test_constructors.py:160-298` covers oversized sections, an incomplete prefix, repeated headings, and nested boundaries. |
| H2, unchecked `ConstructionInputs` | Resolved | `src/veriformis/construction/pipeline.py:259-265` routes construction through checked values. Lines 359-411 rebuild and validate both recipe and inputs from strict JSON before execution. `tests/construction/test_input_lifecycle_boundaries.py:66-191` covers forged sources, chunks, transforms, IR bytes, reviews, schema versions, and both construct and replay boundaries. |
| I1, present null scalar | Resolved | `src/veriformis/construction/constructors.py:867-925` distinguishes optional absent object values from present list members and retains `None`, `False`, and `0`. `tests/construction/test_constructors.py:427-512` proves `null`, `false`, and `0` output plus exact IR tamper rejection. |
| I2, unsafe record promotion | Resolved | `src/veriformis/construction/models.py:724-760` strictly revalidates candidate and decision, then builds only from checked values. `tests/construction/test_input_lifecycle_boundaries.py:260-321` rejects forged status, reasons, review, candidate ID, and decision ID. |
| I3, duplicate pass error | Resolved | `src/veriformis/construction/models.py:374-383` checks duplicate pass IDs before sequence shape. The loader preserves `DuplicateIdentityError` at lines 1036-1044. `tests/construction/test_input_lifecycle_boundaries.py:324-363` proves `duplicate-identity` at factory and persisted-loader boundaries. |
| I4, CLI machine code | Resolved | `src/veriformis/cli.py:977-1041` routes unsupported objectives, unknown schemas, incompatible schemas, and invalid recipes through `ConstructionError`. `tests/construction/test_cli_construct.py:227-246` proves `error[construction-invalid]` and unchanged `HEAD` for each case. |
| I5, five-objective matrix | Resolved | `tests/construction/test_objective_exit_matrix.py:306-497` parameterizes all five objectives across positive multi-source construction, deterministic repeat and input reordering, exact replay, meaningful non-output, serialized tamper, and replay omission. Lines 412-497 additionally prove exact composed and decomposed Unicode, Greek, and CJK preservation plus deterministic replay for every objective. |
| A1, mutable identity maps | Resolved | `src/veriformis/construction/models.py:86-102` exposes both identity-defining registries through `MappingProxyType` with immutable tuple or string values. `tests/construction/test_input_lifecycle_boundaries.py:366-376` proves mutation fails. |

### Additional boundary checks

- `section_reconstruction` requires `structure` segmentation and a
  `cleaned-document-ir` artifact. A parsed-only artifact produces a typed
  `section-structure-unavailable` diagnostic instead of a record.
- Section evidence replays the complete body value and carries every
  contributing chunk ID. Supplying only the first chunk of an oversized
  section produces no candidate or record.
- Present `null`, `false`, and `0` structured values remain distinct from an
  absent optional object field.
- A required rejected review produces an auditable `rejected` decision with
  `review-rejected`, preserves the candidate, creates no `DatasetRecord`, and
  reproduces under exact replay. This is proved at
  `tests/construction/test_objective_exit_matrix.py:412-450`.
- Group 2 still stops at evidence-bearing accepted records. It does not claim
  curation, split assignment, row serialization, whole-dataset validation, or
  sealing.

### Read-only verification

The final repaired tree passed:

```text
uv lock --check
uv run ruff check src tests
uv run pytest -q
git diff --check
```

Observed result:

```text
457 passed, 8 xfailed
```

The focused repair and exit-matrix run passed:

```text
52 passed
```

Running `uv run pytest -q --runxfail tests/known_gaps` produced exactly the
same eight expected later-step failures. None is a Group 2-only defect.

## Initial Critical Findings

None.

## Initial High Findings

### H1. A size-split source section can be accepted as a complete section

**Evidence:**

- `src/veriformis/chunkers/strategies.py:367-407` may divide one heading section
  into several structure chunks when its blocks exceed `max_size`.
- `src/veriformis/construction/constructors.py:423-498` examines each chunk in
  isolation. Any first chunk beginning with `heading + "\n\n"` becomes an
  accepted candidate. Later chunks from the same heading path become
  `section-structure-unavailable` diagnostics.
- The contract at `docs/contracts/dataset-construction-v1.md:167-178` says the
  heading identifies the exact source section whose body is the target.

**Observed reproduction:** A source containing heading `H`, a 20-character `A`
paragraph, and a 20-character `B` paragraph was structure-chunked with size 25.
The chunks were:

```text
(1, "H\n\nAAAAAAAAAAAAAAAAAAAA", ["H"], (0, 1))
(2, "BBBBBBBBBBBBBBBBBBBB", ["H"], (2,))
```

Construction accepted this record and diagnosed only the second chunk:

```text
records [["H", "AAAAAAAAAAAAAAAAAAAA"]]
diagnostics [("section-structure-unavailable", <second chunk ID>)]
```

The accepted `section` omits the `B` paragraph. Its bytes have valid evidence,
but its semantic claim is false.

**Required correction:** Construct from a complete, source-grounded section
unit rather than one chunk. Join all chunks belonging to the same actual
section with replayable evidence and bind every contributing chunk ID. If v1
cannot prove the whole section boundary, reject or diagnose the entire section.
Never accept its first fragment as the section. Add cases for oversized
sections, repeated heading text, nested headings, and multi-chunk evidence.

### H2. `construct_dataset` trusts an unchecked `ConstructionInputs` instance

**Evidence:**

- `src/veriformis/construction/pipeline.py:140-189` contains the necessary
  source, chunk, transform, artifact, and review checks.
- `src/veriformis/construction/pipeline.py:255-324` accepts a
  `ConstructionInputs` instance and immediately executes it.
- `src/veriformis/construction/pipeline.py:346-382` deliberately revalidates the
  recipe against unchecked model copies, but does not revalidate the input
  model. Its remaining checks do not recompute chunk or IR artifact identities.
- `validate_construction_result` calls the same unchecked replay path at
  `src/veriformis/construction/pipeline.py:327-343`.

**Observed reproduction:** Starting with a valid structured-field fixture, the
IR JSON was copied and its link target changed from the real value to
`https://forged.test`. An unchecked `IRArtifactInput.model_copy` retained the
original `artifact_id`. An unchecked top-level `ConstructionInputs.model_copy`
then installed that artifact. `construct_dataset` accepted the target:

```text
accepted https://forged.test
artifact_id_unchanged True
evidence_document_digest_matches_original False
```

The result therefore says that the changed bytes belong to the original
immutable artifact identity. Exact result replay also trusts the same input and
does not repair this boundary.

**Required correction:** At both public construction and replay entry points,
create and use a freshly validated `ConstructionInputs` value before inspecting
any field. The revalidation must rerun `_validate_source`, `chunk_to_dict`,
transform validation, IR artifact content and identity validation, review
validation, duplicate checks, and the input schema version. Add unsafe-copy and
`model_construct` regressions for every input collection, with a focused test
that changed IR bytes cannot retain an old artifact ID.

## Initial Important Findings

### I1. A selected null IR scalar is silently omitted

**Evidence:**

- `src/veriformis/construction/evidence.py:30-32` includes `None` in the v1 JSON
  scalar type, and `src/veriformis/construction/evidence.py:245-251` can encode
  it deterministically as `null`.
- `src/veriformis/ir/nodes.py:159-168` permits `None` as a table alignment.
- `src/veriformis/construction/constructors.py:631-640` selects table
  `alignments` for structured-field construction.
- `src/veriformis/construction/constructors.py:662-677` drops every `None` list
  item without a candidate or diagnostic.

**Observed reproduction:** A two-column table with alignments `[None, "right"]`
produced this output:

```text
structured targets ["right"]
diagnostics []
```

The explicit scalar at `alignments/0` vanished silently.

**Required correction:** Treat a present `None` list element as a selected JSON
scalar and emit the existing `json-scalar-v1` value `null`, or emit a typed
diagnostic that names its pointer. Keep optional object fields that semantically
mean "absent" distinct from present list entries. Add positive and tamper tests
for `null`, `false`, and `0`.

### I2. `DatasetRecord.promote` can promote a forged decision object

**Evidence:** `src/veriformis/construction/models.py:716-736` checks only the
decision's current `status` and `candidate_id`. It does not revalidate the
decision ID, reasons, or embedded review before using `decision_id` in a new
record.

**Observed reproduction:** A valid pending-review decision was copied with only
`status="accepted"`. Its ID and `("review-required",)` reason remained those of
the pending decision. `DatasetRecord.promote` nevertheless returned a record
bound to that pending decision ID.

```text
pending_review ("review-required",)
accepted ("review-required",) same_decision_id=True
record promoted
```

Full result validation later rejects the inconsistency, but the exported
lifecycle factory itself violates its promotion contract.

**Required correction:** Strictly revalidate both candidate and decision before
promotion, then require an identity-valid accepted decision whose candidate ID
matches. Use the validated values to build the record. Add regressions for
unsafe status, reason, review, candidate-ID, and decision-ID copies.

### I3. Duplicate construction passes lose the required error code

**Evidence:** In `src/veriformis/construction/models.py:368-375`, contiguous
sequence validation runs before duplicate `pass_id` detection. Two identical
pass objects therefore fail on sequence order before the duplicate identity is
examined.

**Observed reproduction:** A recipe containing `(pass_one, pass_one)` raised a
Pydantic `ValidationError` from `DatasetRecipe.create`. Loading the equivalent
persisted value is wrapped as `construction-invalid`, not
`duplicate-identity`. This conflicts with
`docs/contracts/dataset-construction-v1.md:139-142`.

**Required correction:** Detect duplicate durable pass IDs before sequence
shape validation. Preserve `DuplicateIdentityError` through both the factory
and persisted loader. Add direct and byte-loader regressions.

### I4. The construct CLI bypasses the documented construction error code

**Evidence:**

- `src/veriformis/cli.py:976-995` prints untyped messages and exits before the
  typed-error boundary for unsupported objectives and row schemas.
- `src/veriformis/cli.py:1019-1032` can raise an unwrapped Pydantic validation
  error for a known but incompatible objective and row-schema combination.
- `docs/contracts/dataset-construction-v1.md:530-548` assigns contract, schema,
  objective-shape, and recipe failures to `construction-invalid`.

**Observed reproduction:** Running a prepared workspace with
`--objective full_text --target-row-schema messages` produced:

```text
error[invalid-data]: 1 validation error for DatasetRecipe
```

An unsupported objective prints `unknown objective` without any machine code.

**Required correction:** Route these failures through `ConstructionError` and
the normal `_echo_error` path, or define a separate documented CLI-usage error
contract and use it consistently. Add CLI tests for an unsupported objective,
unknown row schema, and incompatible known row schema.

### I5. The declared Group 2 constructor test matrix is incomplete

**Evidence:**

- The exit gate at `docs/contracts/dataset-construction-v1.md:595-607` requires
  positive, negative, tamper, multi-source, and replay tests for all five
  constructors.
- `tests/construction/test_constructors.py:25-246` covers useful positive cases,
  one section negative, missing IR, and empty structured strings. It does not
  provide the required matrix for each objective.
- `tests/construction/test_acceptance_corpus.py:27-118` exercises only
  `full_text` and `continuation` over the raw multi-source corpus.

The passing suite therefore does not establish the stated exit condition. In
particular, the split-section and null-scalar defects above sit outside the
current cases.

**Required correction:** Add a parameterized or clearly tabulated matrix that
proves each objective under positive, negative, tamper, multi-source, and exact
replay conditions. Include Unicode and deterministic repeat assertions where
the contract requires them. Keep the eight joint Group 3 gaps expected-failed
until their later owner steps are implemented.

## Initial Advisory Findings

### A1. Identity-defining public mappings are mutable process-global state

`OBJECTIVE_FIELD_CONTRACTS` and `BUILTIN_CONSTRUCTOR_IDS` are exported mutable
dictionaries at `src/veriformis/construction/models.py:85-101`. Objective,
pass, recipe, and candidate identities depend on their contents. Any importing
code can change the active v1 contract for the rest of the process.

**Suggested correction:** Keep private mutable implementation tables and expose
read-only mappings, such as `MappingProxyType`, or expose immutable tuples and
lookup helpers. Add one test proving callers cannot mutate the v1 schema.

## Initial Architecture Considerations

- Keep the current stage boundary. Group 2 should continue to stop at accepted
  construction records. It should not make the legacy formatter look
  construction-aware before Step 13.
- Keep canonical clean text as an intermediate except when a recipe explicitly
  chooses `full_text`.
- Preserve the current workspace v1-to-v2 migration shape. The reviewed code
  appends one v2 revision, preserves the six legacy stage facts, and adds only
  absent `construct`.
- Continue using contextual replay before `HEAD` promotion. Bare loaders can
  remain structural if public documentation keeps that distinction explicit.
- Treat every accepted objective name as a semantic assertion. Valid byte
  evidence is necessary, but it does not by itself prove that a fragment is a
  complete section or that an artifact ID identifies the supplied bytes.

## Initial Verification Observed

The following read-only checks passed against the reviewed snapshot:

```text
uv lock --check
uv run ruff check src tests
uv run pytest -q
git diff --check
```

Observed full-suite result:

```text
417 passed, 8 xfailed
```

Focused Group 2 result before the last documentation reconciliation:

```text
96 passed
```

Running the known gaps with `--runxfail` produced exactly eight failures. They
remain the declared Step 13 through Step 16 work, including the two joint
Step 8/15 and Step 10/13 cases.

The review also inspected:

- all changed and added Group 2 source files;
- the dataset-construction and integrity contracts;
- workspace revision loading, transition validation, migration, commit, and
  construct semantic replay;
- CLI source selection, input reconstruction, transactional artifact writes,
  and no-op behavior;
- all focused construction, contract, CLI, acceptance, and migration tests;
  and
- the exact Group 3 deferral language.

## Initial Next Steps (Completed)

These were the original repair requests. The repair verification above now
supersedes them.

1. Fix H1 and H2 before treating any Group 2 result as integrity-bearing.
2. Fix I1 through I4 and add focused regressions.
3. Complete I5's objective matrix and rerun every repository gate.
4. Reconcile capability documentation only after those tests pass.
5. Request one final independent review of the repaired diff before publishing
   the draft pull request.
