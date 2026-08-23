# Phase 7 Execution Plan

**Status:** Complete

**Last updated:** 2026-08-23

**Authority:** [Independent Product Roadmap](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md) Phase 7; [program.json](../program.json); Phase 5.5 decision that production import is not the test-only round-trip fixture.

**Predecessor:** Phase 6 closeout merged as PR #67 at
`6995d17bef0d09f235b1c464e947c38c63dd313d` after all 14 GitHub checks passed,
then stamped complete as PR #69 at
`6c4694c2e1c523156cd7c8f34c12f258a3ce0b01`. Clean local `main` equals
`origin/main` there.

Each numbered roadmap work item is one sequential pull request on branch
`phase7/0N-<slug>` titled `Phase 7.N: <imperative>`. A pull request must pass
its focused and required repository gates, pass every GitHub check, merge, and
leave clean local `main` equal to `origin/main` before the next item begins.

The plan below is the roadmap's ten work items, each widened where the current
tree makes the roadmap sentence thinner than the repository requires. Closeout
is folded into 7.10, matching Phase 6 rather than adding an eleventh PR.

## Goal

Normalize datasets that already contain training rows into the current semantic row schemas, with explicit confirmed mappings, field-level provenance, honest partition policy, and the same seal → generic-export path as constructed datasets.

## Architecture

Dataset-row import is a second compiler path, not a new parser suffix and not a reuse of document recovery. Today's `.csv` / `.json` / `.jsonl` ingest (`src/veriformis/parsers/structured.py`) flattens structured files into IR tables or path-labeled paragraphs, then construction invents records from those spans. That path stays as **document-source** mode. **Dataset-row** mode captures exact records, applies a versioned mapping plan, and emits imported records that lower to unchanged `ProductRow` v1 payloads.

`PipelineService` remains the only composition root. CLI, MCP, and the Mac bridge are adapters. Phase 5.5's `_reload_*` helpers stay test-only; production import must not call them.

## Standing constraints

- Document-source compilation remains the default and must stay byte-compatible. Dataset-row mode is opt-in. Suffix alone never selects import.
- Do not call `parse_csv_file` / `parse_json_file` / `parse_jsonl_file` for mapping. Recovery trims cells, drops blank rows, pads ragged rows, and flattens JSON; Phase 5.3 already rejected that parser as round-trip evidence.
- No sixth `TrainingObjective`, no fifth row schema, no preference / tool-call / multimodal family, no Parquet / Arrow (Phase 9), no executable mapping code, no LLM, no network.
- Imported `messages` must satisfy Finished Dataset v1: exactly two turns, roles `user` then `assistant`, nonempty content. Arbitrary chat logs fail closed (Phase 17).
- Constrained CSV cannot represent `messages`. Import refuses nested CSV the same way export does.
- Product fields remain nonempty exact strings. Default coercion is refuse. Any coercion, missing-value fill, or invalid-row rule is an explicit versioned mapping step with recorded evidence.
- Constructors do not run on imported rows. The operator still selects an existing Phase 6 goal and representation so the loss policy and catalog non-claims stay attached to the dataset; mapping fills the representation's fields.
- `ProductRow` v1, generic export selectors, and verified-export receipts stay unchanged. Import produces canonical bundles; export remains a derivative.
- Never silently resplit. Until 7.7, imported partition columns are ignored and the existing leakage-safe splitter runs as **replaced** membership, with that policy recorded on the plan.
- Defaults, detectors, and templates are versioned packaged data, never duplicated CLI / MCP / Swift constants.
- Preview, detect, and preflight never mutate a workspace, call a renderer, or write a destination.
- Python, CLI, MCP, and the CLI-backed Mac bridge must agree on mapping-plan identity, record identity, row-set identity, and partition membership.

## Key decisions (lock at 7.1)

| Decision | Recommendation | Why |
| --- | --- | --- |
| Compiler path, not taxonomy axis | Input **mode** is a workspace/project attribute (`document-source`, `dataset-row`, `mixed`). Do not add an eighth taxonomy axis. ADR-0010. | Taxonomy already has seven axes. Mode chooses the stage graph, not what is learned. Support registry already has `implemented_modes` / `planned_modes`. |
| Workspace revision | Dataset-row workspaces are revision **v4** with stages `parse` (row-source capture) → `map` → `curate` → `split` → `format` → `validate` → `seal`. Document-source stays revision v3. `upgrade-workspace` does not convert a document workspace into an import workspace. | Same pattern as v2 (`construct`) and v3 (`curate`/`split`). Clean/chunk/construct are document stages; faking them would invent chunks. |
| Record type | New `veriformis.imported-record/v1`. Do not widen `veriformis.dataset-record/v1` (exact field set, requires `chunk_ids`). Format lowers imported records to the same `ProductRow` v1. | Construction contract forbids empty chunks; synthetic chunks would be a lie. |
| Field evidence | New `kind: mapped_value` evidence: source file, row/index, field/path, original-value digest, mapping-rule id, output SHA-256. Extend the field-evidence discriminator without rewriting source-text or IR evidence. | Roadmap item 5; matches `IRFieldEvidence` / `SourceTextEvidence` shape. |
| Goal on import | Operator selects an existing catalog goal and compatible representation. Mapping must populate exactly that representation's payload keys. Constructors are skipped. | Keeps one loss policy and one catalog of non-claims. Avoids a sixth objective. |
| Mixed mode | 7.1 names it and **refuses** execution. 7.7 admits mixed projects once both provenances and partition policy exist, keeping construction and imported-row lineage distinct. | Cannot mix until mapping and membership policy exist. |
| Physical inputs | JSONL is the proving container in 7.3. Generic JSON and compatible CSV are admitted in 7.8. Parquet/Arrow wait for Phase 9. | Matches roadmap item 8; CSV dialect is the dangerous case and deserves its own gates. |
| Mac depth | Thin CLI-backed detect / confirm / preview / reject-export. No spreadsheet mapping editor. Phase 18 owns the complete workbench. | Same bound as Phase 6.7's thin export delegates versus Phase 18. |
| Closeout | Folded into 7.10 with mapping templates. | Phase 6 precedent (closeout in the last roadmap item). |

## New composition boundary

```text
dataset-row mode
  captured row-source files
    -> strict row-source admission (no recovery normalization)
    -> versioned MappingPlan (confirmed)
    -> ImportedRecord values with mapped_value evidence
    -> FinishedDatasetPlan v1 (origin recorded)
    -> curation and coverage ledger
    -> split under explicit membership policy
    -> ProductRow v1 lowering (unchanged payload contract)
    -> exact validation, seal, verify
    -> existing generic export
```

Document-source mode is unchanged:

```text
parse -> clean -> chunk -> construct -> curate -> split -> format -> validate -> seal
```

## Likely files (created across the phase)

- Create: `src/veriformis/mapping/` (`__init__.py`, `models.py`, `capture.py`, `detect.py`, `execute.py`, `preview.py`, `reject.py`, `templates.py`, packaged JSON for detectors and templates)
- Create: `docs/contracts/row-mapping-v1.md`
- Create: `docs/adr/0010-input-mode-as-compiler-path.md`
- Create: `docs/adr/0011-imported-records-and-mapping-evidence.md`
- Create: `tests/mapping/` and `tests/regressions/fixtures/phase7/`
- Create at 7.1 only: `dev/active/independent-product/phase-07-existing-dataset-import/` packet
- Modify: `src/veriformis/pipeline/service.py`, `cli.py`, `mcp/server.py`, `workspace.py`, `errors.py`, `taxonomy.py` (discovery of modes, not a new axis), `datasets/serialization.py` (lower imported records), `datasets/curation.py`, `datasets/splitting.py`, `datasets/plan.py`
- Modify: Mac `VeriformisCLI.swift`, `WorkbenchViewModel.swift`, compile/result views (thin mode + mapping confirm/preview)
- Modify: support registry `planned_modes` → `implemented_modes` only when that mode actually executes; `gap-existing-dataset-row-mapping` closes at 7.10
- Do not modify: `src/veriformis/parsers/structured.py` behavior for document mode; Phase 5.5 `tests/exports/test_semantic_round_trip.py` production status

---

## Checklist

### 7.1 Name input modes and open the packet

**Branch:** `phase7/01-input-modes`  
**Title:** `Phase 7.1: Name input modes and open the import packet`

- [ ] Confirm the predecessor gate: Phase 6 completed, `HEAD == origin/main`.
- [ ] Create the standard Phase 7 packet `dev/active/independent-product/phase-07-existing-dataset-import/` (`README.md`, `plan.md`, `progress.md`, `decisions.md`, `risks.md`, `evidence.md`, `closeout.md`). Mark Phase 7 `in_progress` in `program.json` with `started_on` and a next-gate naming 7.1. Reconcile `WIP.md`, `docs/current-status.md`, `docs/product-contract.md`, `docs/README.md`, `README.md`, `docs/cli.md`, `docs/install.md`, `docs/governance/README.md`, `docs/governance/project-tracking.md`, `docs/governance/documentation-debt.md`, `docs/governance/health-report.md`, the program `README.md`, and `CLAUDE.md`. Cite the Phase 6 closeout merge.
- [ ] Publish ADR-0010: input mode is a compiler path (`document-source`, `dataset-row`, `mixed`), not an eighth taxonomy axis and not a collapsed “format”.
- [ ] Freeze mode identifiers in versioned data consumed by discovery. Document-source remains the only executable mode. `dataset-row` and `mixed` are discoverable and **refuse execution** with an actionable reason that names the later item.
- [ ] Default CLI / MCP / Mac compile stays document-source with no new required flag. An explicit `--mode dataset-row` (and Mac equivalent) fails closed until 7.3.
- [ ] Bind `scripts/check_project_tracking.py` so a mode cannot be advertised in `support-registry.json` as implemented until a surface actually runs it.
- [ ] Predeclare the usability criteria below before any mapper or preview work begins.
- [ ] Record focused, tracking, lint, structured-JSON, and diff evidence. Do not claim import support.

### 7.2 Freeze row-source and mapping contracts

**Branch:** `phase7/02-mapping-contracts`  
**Title:** `Phase 7.2: Freeze row-source and mapping contracts`

- [ ] Publish `docs/contracts/row-mapping-v1.md` and ADR-0011 (imported records and `mapped_value` evidence).
- [ ] Freeze strict Pydantic models (exact field sets, identity recomputed on load, extra=forbid):
  - `veriformis.row-source/v1` — file identity, container kind (`jsonl` now; `json` / `csv` reserved), record count, byte digest
  - `veriformis.field-mapping/v1` — source path (column name or JSON pointer), target payload key, optional explicit coercion/missing/invalid rule ids
  - `veriformis.mapping-plan/v1` — target goal, representation/row schema, ordered field mappings, confirmation digest, membership policy placeholder (`replaced` only in this item)
  - `veriformis.imported-record/v1` — record identity, source id, row index, mapping-plan id, goal/recipe/objective ids (catalog-bound, constructors not run), fields with `mapped_value` evidence
  - missing-value, invalid-row, and review contracts as closed vocabularies
- [ ] Add `MappingError` / `RowSourceError` to `src/veriformis/errors.py` and surface exception tuples.
- [ ] Expose read-only contract discovery through `PipelineService`, CLI, and MCP. No file IO, no workspace mutation.
- [ ] Prove unknown fields, missing fields, identity mismatch, and unsupported container kinds fail closed.
- [ ] Do not implement capture or mapping execution yet.

### 7.3 Map JSONL into the four semantic rows

**Branch:** `phase7/03-jsonl-row-mapping`  
**Title:** `Phase 7.3: Map JSONL rows into current semantic schemas`

Roadmap items 3 and 5 begin here: mapping execution includes field provenance from the first accepted field. JSONL is the only admitted physical container.

- [ ] Implement `src/veriformis/mapping/capture.py` for UTF-8 JSONL: one JSON object per nonempty line, exact bytes, no flattening, no dropping of valid empty-string fields (invalid/missing handled later by mapping rules). Refuse invalid UTF-8, invalid lines, and empty files.
- [ ] Implement `src/veriformis/mapping/execute.py`: apply a confirmed `mapping-plan/v1` into `text`, `prompt_completion`, `instruction_output`, or `messages` payload keys exactly as `_payload_contract` requires.
- [ ] Every accepted field carries `mapped_value` evidence: file, 1-based line/record index, JSON pointer, original-value SHA-256, mapping-rule id, output SHA-256. Replay must reconstruct the same output digest from the captured bytes and plan.
- [ ] Add workspace revision v4 and stage `map`. `PipelineService.map_rows` commits it. Dataset-row `parse` stores row-source captures, not IR documents. Document-source v3 workspaces reject `map`; v4 workspaces reject `clean` / `chunk` / `construct`.
- [ ] Wire CLI `map` and MCP `map_rows`. Goal + representation are required. Constructors, cleaning, and chunking are not invoked.
- [ ] Curation, split (still **replaced** / leakage-safe), format, validate, and seal consume imported records and emit ordinary `ProductRow` v1 + aligned provenance. Provenance lists mapping ids instead of inventing chunk ids.
- [ ] Positive fixtures: one JSONL per schema, including Unicode and nested `messages` two-turn objects. Negative: extra keys not mapped (warn or refuse per plan), missing required keys, empty required strings, three-turn messages, constructor-path files fed to map, map on a v3 workspace.
- [ ] Python / CLI / MCP parity on mapping-plan id, imported-record ids, row-set id, and manifest digest for the four JSONL fixtures.
- [ ] Do not admit JSON object files, CSV, mixed mode, detectors, or partition-column honor yet.

### 7.4 Propose mappings and require confirmation

**Branch:** `phase7/04-mapping-detection`  
**Title:** `Phase 7.4: Propose mappings and require confirmation`

- [ ] Freeze detector data as packaged versioned JSON (not Swift/CLI constants). First detectors: flat `text`; `prompt`/`completion`; Alpaca-style `instruction`/`input`/`output`; two-turn `messages` / `user`+`assistant`; Veriformis split-JSONL payload shape (proposal only, still not the Phase 5.5 loader).
- [ ] `PipelineService.detect_mapping` is runtime-only: reads the file, returns zero or more proposed `mapping-plan/v1` objects plus a closed reason when it refuses to guess.
- [ ] If more than one semantic interpretation is possible, execution requires an explicit confirmation digest of the chosen plan. Zero proposals refuse. One unique proposal still requires confirmation before `map` mutates a workspace (fail closed on unconfirmed plans).
- [ ] CLI `mapping-detect`, MCP `mapping_detect`, Mac: show proposal(s) and record confirmation. No auto-publish.
- [ ] Ambiguous fixture: a file that could be `text` or `prompt_completion` must not map without confirmation. Detector must not invent a summary/translation/Q&A interpretation.

### 7.5 Bind mapping provenance and replay

**Branch:** `phase7/05-mapping-provenance`  
**Title:** `Phase 7.5: Bind mapping provenance and replay`

7.3 shipped evidence on fields. This item makes that evidence the identity of the request and the audit trail.

- [ ] Include mapping-plan digest, catalog SHA, goal, representation, and every mapping-rule id in recipe / finished-plan identity so a silent mapping edit cannot reuse a prior seal.
- [ ] Tamper suite: alter source bytes, swap a column/path, change one original-value digest, drop evidence, reorder mappings, or reuse a confirmation digest against a different file — all fail closed before seal.
- [ ] Independent replay from captured row-source + mapping plan reconstructs identical imported-record ids and field values.
- [ ] Aligned row provenance for exported/sealed rows names file, index, path, and mapping rule; it does not claim construction chunks.
- [ ] Update `docs/contracts/row-mapping-v1.md` and Finished Dataset provenance language so imported origin is explicit without changing `ProductRow` v1.

### 7.6 Preview and sample the full file

**Branch:** `phase7/06-mapping-preview`  
**Title:** `Phase 7.6: Preview mapping across the full file`

- [ ] `PipelineService.preview_mapping` returns runtime-only `veriformis.mapping-preview/v1`: proposed or confirmed mapping, per-row accept/reject with reason codes, exact mapped payload samples, and counts. It must walk the **full file**, not only the first N rows, and must include malformed and rare shapes in the rejection side (bounded like Phase 5.6: 64 KiB per payload, 256 KiB response, whole-value omission with an exact reason, ASCII-safe transport).
- [ ] Never mutate a workspace, never write a destination, never call a renderer or constructor.
- [ ] CLI `mapping-preview`, MCP `mapping_preview`, Mac preview panel. Show rejects, not only happy rows.
- [ ] Prove a file whose first rows are well-formed and whose later rows are ragged/malformed reports those later rows. Prove Python / CLI / MCP / Mac-bridge JSON agreement.

### 7.7 Define imported partition policy and admit mixed projects

**Branch:** `phase7/07-partition-policy`  
**Title:** `Phase 7.7: Honor, advise, or replace imported partitions`

- [ ] Freeze membership policy as a required mapping-plan field: `authoritative` | `advisory` | `replaced`. No default that reads a `split` column silently. Until the operator sets this field, keep `replaced`.
- [ ] `authoritative`: imported train/evaluation/test labels become Finished Dataset partitions. Only `train` and `evaluation` are v1 partitions; `test` or other names fail closed unless mapped explicitly onto those two. Leakage-policy violations (same leakage group in both partitions, overlapping exact records) fail or require an **explicit new plan** (`replaced` plus a recorded reason). Never silently resplit over authoritative labels.
- [ ] `advisory`: labels are diagnostics only; the leakage-safe splitter assigns membership. Advisory labels that disagree with the assignment are reported, not applied.
- [ ] `replaced`: ignore imported labels; existing `transitive-leakage-prefix-v1` runs. This remains the fail-closed choice.
- [ ] Admit **mixed** mode: one workspace may contain document-source constructed records and dataset-row imported records. Provenance stays distinct (chunk evidence vs mapped_value evidence). Joint curation and split use a single leakage graph over source identities. Mixing without `--mode mixed` still fails.
- [ ] Tests: authoritative happy path; authoritative leakage overlap refuses; advisory disagreement reported; replaced ignores labels; silent absence of policy refuses; mixed distinct provenance; mixed leakage across a document and an imported row that share source bytes.

### 7.8 Admit JSON and compatible CSV, then round-trip

**Branch:** `phase7/08-json-csv-roundtrip`  
**Title:** `Phase 7.8: Admit JSON and CSV import and prove round trips`

- [x] JSON: one object with a declared records array, or a top-level array of objects. Nested paths via JSON pointer. Refuse non-object records and the document-mode flattened projection.
- [x] CSV: mapping-grade reader, not `parsers/structured.py`. Declared dialect on the mapping plan (header required, comma, UTF-8, no silent trim/pad). Ragged rows are invalid-row events, not padded cells. Compatible with the three flat schemas only. Refuse `messages` with the same actionable alternative as constrained-CSV export (`split-jsonl-directory` or `json`).
- [x] Do not treat Veriformis constrained-CSV export dialect as the only admissible CSV; do treat it as a detector proposal.
- [x] Round-trip matrix: for every admitted pair (JSONL × 4 schemas, JSON × 4, CSV × 3 flat), map → curate → split (replaced or authoritative as pinned) → seal → generic export of the matching container → semantic equality of payloads and partitions. This uses production mapping + existing export, not Phase 5.5's test loaders.
- [x] Negative: CSV+`messages`, nested CSV, JSON scalar file, document-mode compile of the same bytes still produces a different (construction) artifact — modes must not collapse.

### 7.9 Export row-level rejections

**Branch:** `phase7/09-rejection-export`  
**Title:** `Phase 7.9: Export row-level mapping rejections`

- [x] Versioned rejection report `veriformis.mapping-rejection-report/v1`: every rejected row's index, source path, closed reason code, original-value digest, mapping-plan id. Deterministic order.
- [x] CLI/MCP/Python write the report as a project artifact beside the workspace, not as a trainer container and not as a verified export. Mac can reveal the path through the CLI bridge.
- [x] Operators can correct the source file and rematch by digest/index without losing the prior audit trail (previous report remains content-addressed).
- [x] Prove: accepted rows still seal; rejected rows never appear in `RowSet`; tampering with the report does not change the sealed bundle; a corrected source produces a new plan id.

### 7.10 Ship mapping templates and close Phase 7

**Branch:** `phase7/10-templates-closeout`  
**Title:** `Phase 7.10: Add mapping templates and close Phase 7`

- [x] Packaged versioned mapping templates (`veriformis.mapping-template/v1`) as shareable project artifacts: named, digest-bound, covering the detectors' unique shapes. Surfaces load them through discovery, not constants.
- [x] Operator guide: when to use document-source vs dataset-row vs mixed; how confirmation works; partition policy; CSV vs JSONL; what import does not claim (trainers, Parquet, multi-turn, construction).
- [x] Judge U1–U7 with current-tree evidence (full mapping suite, round-trip matrix, Mac runtime tests for detect/confirm/preview).
- [x] Promote support registry: `existing-dataset-row-mapping` and `mixed-document-and-dataset-project` become implemented only if their gates passed; close `gap-existing-dataset-row-mapping` or leave it open with an explicit remaining bound.
- [x] Reconcile contracts, ADRs, evidence index, status, WIP, CLI docs, architecture, CLAUDE.md, packet `closeout.md`. Mark Phase 7 `completed`. Do not start Phase 8, 9, or 13.

## Predeclared usability criteria

Declare these in the packet at 7.1, before mapper UI exists.

| ID | Criterion | How it is judged |
| --- | --- | --- |
| U1 | Explicit mode | Document-source compiles without a new required flag; dataset-row requires an explicit mode; suffix `.jsonl` does not silently switch paths. A test pins both. |
| U2 | Confirmed mapping | Ambiguous files cannot map without a confirmation digest; unique detections still refuse unconfirmed `map`. |
| U3 | Full-file preview | Preview reports a malformed late row that first rows hide; rejects are visible. |
| U4 | Field provenance | Every accepted field has file, index, path, original digest, and mapping-rule id; replay matches. |
| U5 | Surface identity | Golden import fixtures yield identical mapping-plan, row-set, and manifest digests across Python, CLI, MCP, and the Mac bridge. |
| U6 | Honest partitions | No fixture with imported split labels is resealed under a different membership without an explicit policy field. |
| U7 | Round-trip | Every admitted container/schema pair maps, seals, exports, and reloads to identical semantic payloads and partitions. |

## Exit gate

Representative `text`, prompt/completion, instruction/input/output, and two-turn message datasets can be imported under explicit confirmed mappings, validated, sealed, generically exported, and semantically round-tripped. Ambiguous or lossy mappings do not auto-publish. Document-source compilation remains unchanged.

**Result:** Complete on local admission evidence. See [closeout.md](closeout.md).

## Non-goals

- Preference, ranking, tool-call, multimodal, or arbitrary chat-template rows.
- Executable or scripted mapping functions.
- Parquet, Arrow, or Hugging Face Dataset import (Phase 9 extends these flows).
- Using Phase 5.5 test loaders as a product importer.
- A sixth objective, a fifth row schema, or constructor reuse that pretends imported fields were built from document chunks.
- Quality heuristics, PII detectors, or near-duplicate gates (Phase 13).
- Consumer profiles (Phase 8) or Hub publication (Phase 19).
- A full Mac mapping spreadsheet (Phase 18).
- Changing document recovery in `parsers/structured.py`.

## Required gates per item (after 7.1)

Run focused mapping tests first, then the item's new suite, then:

```bash
uv run pytest -q --ignore=tests/handoff -m "not aptus_integration"
bash scripts/release/check_local.sh
uv run python scripts/check_project_tracking.py
uv lock --check
uv run ruff check .
git diff --check
```

From 7.3 onward also run Mac `build-for-testing` and, for 7.4/7.6/7.10, the real `xcodebuild test` walkthroughs. Do not quote incomplete matrix runs as passes.

---

## PR Plan

Linear DAG. Each PR depends only on the previous. Do not implement in parallel.

### PR 1: Name input modes and open the import packet

- **Description:** Open the Phase 7 packet, publish ADR-0010, freeze three mode identifiers, keep document-source as the only executable path, refuse dataset-row and mixed with actionable reasons, reconcile tracking documents.
- **Files/components affected:** `dev/active/independent-product/phase-07-existing-dataset-import/`, `dev/active/independent-product/program.json`, `dev/active/independent-product/README.md`, `WIP.md`, `CLAUDE.md`, `docs/adr/0010-input-mode-as-compiler-path.md`, `docs/adr/README.md`, `docs/current-status.md`, `docs/product-contract.md`, `docs/governance/*`, `src/veriformis/pipeline/service.py`, `src/veriformis/cli.py`, `docs/cli.md`, `scripts/check_project_tracking.py`, `docs/governance/support-registry.json`
- **Dependencies:** None (after Phase 6.7 merge)

### PR 2: Freeze row-source and mapping contracts

- **Description:** Strict models and contracts for row-source, field mapping, mapping plan, imported records, missing/invalid/review vocabularies, and discovery-only surfaces. No execution.
- **Files/components affected:** `src/veriformis/mapping/`, `src/veriformis/errors.py`, `docs/contracts/row-mapping-v1.md`, `docs/adr/0011-imported-records-and-mapping-evidence.md`, `src/veriformis/pipeline/service.py`, `src/veriformis/cli.py`, `src/veriformis/mcp/server.py`, `tests/mapping/`
- **Dependencies:** PR 1

### PR 3: Map JSONL rows into current semantic schemas

- **Description:** Row-source capture and mapping execution for JSONL into the four current schemas, workspace revision v4 with `map` stage, field `mapped_value` evidence, seal path through unchanged ProductRow v1. Partition policy fixed to `replaced`.
- **Files/components affected:** `src/veriformis/mapping/capture.py`, `src/veriformis/mapping/execute.py`, `src/veriformis/workspace.py`, `src/veriformis/pipeline/service.py`, `src/veriformis/datasets/curation.py`, `src/veriformis/datasets/splitting.py`, `src/veriformis/datasets/serialization.py`, `src/veriformis/datasets/plan.py`, `src/veriformis/cli.py`, `src/veriformis/mcp/server.py`, `tests/mapping/`, `tests/regressions/fixtures/phase7/`
- **Dependencies:** PR 2

### PR 4: Propose mappings and require confirmation

- **Description:** Versioned detectors propose mapping plans. Multiple interpretations and even unique proposals require confirmation before `map`. Runtime-only detect surfaces on CLI, MCP, and Mac bridge.
- **Files/components affected:** `src/veriformis/mapping/detect.py`, packaged detector JSON, `src/veriformis/pipeline/service.py`, `src/veriformis/cli.py`, `src/veriformis/mcp/server.py`, `macos/Sources/Services/VeriformisCLI.swift`, `macos/Sources/ViewModels/WorkbenchViewModel.swift`, `macos/Sources/Views/CompileView.swift`, `macos/Tests/`
- **Dependencies:** PR 3

### PR 5: Bind mapping provenance and replay

- **Description:** Put mapping-plan and rule digests in request identity; adversarial tamper and independent replay; imported origin in sealed provenance without changing ProductRow v1.
- **Files/components affected:** `src/veriformis/mapping/`, `src/veriformis/datasets/plan.py`, `src/veriformis/datasets/serialization.py`, `docs/contracts/row-mapping-v1.md`, `docs/contracts/finished-dataset-v1.md`, `tests/mapping/`
- **Dependencies:** PR 4

### PR 6: Preview mapping across the full file

- **Description:** Runtime-only full-file mapping preview with accept/reject samples, Phase 5.6 bounds, CLI/MCP/Mac parity. No mutation.
- **Files/components affected:** `src/veriformis/mapping/preview.py`, `src/veriformis/pipeline/service.py`, `src/veriformis/cli.py`, `src/veriformis/mcp/server.py`, Mac preview view/view-model/tests
- **Dependencies:** PR 5

### PR 7: Honor, advise, or replace imported partitions

- **Description:** Required membership policy `authoritative` | `advisory` | `replaced`; no silent resplit; leakage failures; admit mixed mode with distinct provenances.
- **Files/components affected:** `src/veriformis/mapping/models.py`, `src/veriformis/datasets/splitting.py`, `src/veriformis/datasets/plan.py`, `src/veriformis/workspace.py`, `src/veriformis/pipeline/service.py`, tests for partition and mixed fixtures
- **Dependencies:** PR 6

### PR 8: Admit JSON and CSV import and prove round trips

- **Description:** Generic JSON and compatible CSV capture; refuse nested CSV/`messages`; production map → seal → generic export round-trip matrix for all admitted pairs.
- **Files/components affected:** `src/veriformis/mapping/capture.py`, CSV dialect on mapping plan, `tests/regressions/fixtures/phase7/`, `tests/regressions/test_phase7_import_round_trip.py`, export tests remaining test-only for Phase 5.5
- **Dependencies:** PR 7

### PR 9: Export row-level mapping rejections

- **Description:** Deterministic rejection-report artifact so operators can correct sources without losing the audit trail. Not a trainer export.
- **Files/components affected:** `src/veriformis/mapping/reject.py`, `src/veriformis/pipeline/service.py`, `src/veriformis/cli.py`, `src/veriformis/mcp/server.py`, tests
- **Dependencies:** PR 8

### PR 10: Add mapping templates and close Phase 7

- **Description:** Versioned shareable mapping templates, operator guide, U1–U7 judgment, support-registry promotion, packet closeout. Do not start later phases.
- **Files/components affected:** `src/veriformis/mapping/templates.py`, `docs/` operator guide, packet `closeout.md` / `evidence.md` / `progress.md`, `program.json`, `WIP.md`, `docs/current-status.md`, `docs/governance/support-registry.json`, `docs/evidence/index.json`
- **Dependencies:** PR 9

## What this plan is not

- Not permission to begin Phase 7 while 6.7 is unmerged.
- Not a packet, ADR, or contract until 7.1 / 7.2 write those files.
- Not a claim that import, mixed mode, or mapping templates exist.
