# Progress

Append-only dated execution log.

## 2026-09-09

- Opened the packet from the full-repository audit of `main` at `5d617f8`.
- Baseline on this host: `uv lock --check`, `ruff`, tracking checker, and
  `git diff --check` pass; core pytest `2701 passed, 5 skipped, 17 deselected`
  in 15m03s (documented figure was ~90s).
- Verified directly before opening: D-01 (wheel omits `scale/support-v1.json`),
  D-02 (`café` → `cafÃ©` with `encoding=None`), D-03 (`splitlines()` in two
  JSONL framers), D-04 (Swift writes the plan into the CLI workspace before
  `parse`), D-05 (descriptor-declared capabilities), D-06 (`_seal_imported`
  has no `try`), D-07 (`canonical_digest` NFC), D-24 (9 goals / 8
  representations / 8 row schemas vs contract 5 / 4 / 4), D-27 (unmarked
  handoff test).

## 2026-09-09 — Phase 1 (ship blockers)

- D-01: `scale/*.json` added to `package-data`; `tests/release/test_package_data_coverage.py`
  compares on-disk data files with the declared globs; `inspect_python_artifacts.sh`
  asserts every data file is a wheel member; `smoke_install.sh` runs every discovery
  command from the clean venv. Verified locally: `veriformis/scale/support-v1.json`
  is now a wheel member.
- D-02: HTML capture decoded by Veriformis before lxml (BOM, strict UTF-8, declared
  charset); refusals `html.charset-unknown` / `html.charset-invalid`; diagnostics
  `html.charset-declared` / `html.bom-removed`. Parser pin `1.0.0 -> 1.1.0`.
  Frozen goal matrix regenerated through `--generate`; diff: exactly the 13
  `html` cells changed, only `manifest_sha256`, `row_set_sha256`, and
  `supervision_sha256`; every other cell byte-identical.
- D-03: `veriformis._jsonl_frames.frame_jsonl_lines` shared by the JSONL parser,
  dataset-row capture, and the handoff loader. Regressions prove U+2028/U+2029/U+0085
  records survive and fail on the unmodified framers.
- D-06: `_publish_or_recover_finished_bundle` and `_seal_messages` shared by both seal
  paths; `_seal_imported` wrapped in `SealPartialPublicationError`; recovery decodes
  `validation.json` with the sealing path's report loader (adopting an exact prior
  imported publication previously crashed on the document report schema).
- D-08: rejection report written before the `map` transaction opens, via temp file,
  fsync, and rename.
- D-09: `_run` returns the outcome; `map`, `seal`, `mapping-rejections` routed through
  it; `csv.Error`, `RecursionError`, oversized-int `ValueError` typed as
  `csv.invalid` / `json.invalid`; per-page pdfium failures typed as
  `pdf.page-unreadable`.
- D-05: `consume_aptus_handoff` recomputes the forbidden schemas from the taxonomy
  pin, flags capability blocks that differ from the pin, recomputes the masking
  expectation, and requires plan/recipe/construction/split/objective identities and
  the source-id set to match sealed provenance. Forged text-bundle descriptor now
  rejected on Python and CLI.
- D-27: `tests/handoff/test_defectclose_handoff.py` moved to `tests/regressions/`
  (collected by the core gate).
- D-04: Swift writes `run.log` and `confirmed-mapping-plan.json` to a sibling
  `<workspace>.workbench/` directory and no longer pre-creates the CLI workspace;
  real-repo-CLI dataset-row compile test added through `WorkbenchViewModel.compile()`.
- D-28: `profile-integration` job syncs `--extra columnar` and sets
  `VERIFORMIS_REQUIRE_PROFILE_LIBRARIES=1`; tests load emitted TRL / MLX-LM /
  Axolotl / LLaMA-Factory partitions through the official `datasets` loader and
  prove no trainer library is imported.
- `AGENTS.md` suite timing corrected from ~90s to the observed ~15 minutes.

## 2026-09-09 — Phase 2 (claim honesty)

- D-24: goal-catalog-v1 (nine goals, eight representations, nine templates,
  per-representation export table), recipe-preset-v1 (nine presets),
  split-jsonl-export-v1 and canonical-json-export-v1 (eight frozen row schemas),
  generic-exports.md matrix, and current-status.md rows now match `veriformis
  goals`, `presets`, and `export discover`.
- D-25: cli.md documents `map`, `--mode`, `spec-*`, `env-inspect`, `review-*`,
  `scale-support`, `scale-baseline`, `support-matrix`, `extension-capabilities`,
  `ocr-preview`, and all 51 error codes; install.md's command map is complete;
  README's `map` example runs.
- D-26: "no semantic replayer ships" removed from five active documents;
  "extras stay empty" excepts `columnar` everywhere; `ocr-image` vs
  `pdf.ocr-required` corrected; architecture counts (52 commands, ten stage
  commands), package lists, CI job table, and check-run counts corrected;
  health report and debt register advanced from Phase 8 to Phase 20 with
  DOC-008 through DOC-011.
- 2.4: `scripts/check_project_tracking.py` now fails when a packaged data file
  matches no package-data glob, when a contract's frozen
  `supported_row_schemas` block differs from live discovery, when a goal,
  representation, or preset is absent from its contract, or when
  current-status.md misstates the catalog counts; the recipe-literal scan covers
  `automation/`, `workbench/`, `goals/preflight.py`, `goals/preview.py`, and
  `WorkbenchModels.swift`. Each new assertion was shown to fail on the
  pre-fix tree.
- Audited-accurate documents (program.json, packet READMEs, migration,
  support-lifecycle, support-matrix, taxonomy, profile-admission, container
  trees) were not touched.

## 2026-09-09 — Phase 3 (recovery-layer truthfulness)

- D-10 (docx 1.2.0 -> 1.3.0): hardened note-part parser and diagnostics XML probe;
  `lxml>=5.0` floor; declared-inflation and member-count caps before the
  package opens; `docx.drawing-text-omitted` (text loss) for text boxes;
  `w:moveTo` retained once with `docx.revision-move-normalized`,
  `w:moveFrom` dropped with `docx.revision-move-source-omitted`.
- D-11 (pdf 1.0.0 -> 1.1.0): no fabricated `Page N` headings; `Span.page` on
  every paragraph; `pdf.text-layer-normalized`; page-count bound;
  `pdf.page-unreadable`. New fixture `tests/fixtures/group5/two-page-text.pdf`.
- D-12 (html 1.1.0 -> 1.2.0): `<br>` and nested blocks become line breaks with
  `html.line-break-normalized`; `<pre>` whitespace kept; `html.table-flattened`,
  `html.list-flattened`; omitted subtrees with visible text and content outside a
  selected `<main>` labelled text loss.
- D-13 (csv/json/jsonl 1.0.0 -> 1.1.0, text 1.1.0 -> 1.2.0): strict JSON loader
  (no NaN/Infinity, no duplicate keys); shortest-round-trip floats; exact string
  values and source key order; `csv.bom-removed`, `csv.cells-trimmed`,
  `csv.blank-rows-omitted`; `text.not-utf8` typed refusal; `text.bom-removed`.
- D-14: Tesseract runs one pass writing txt and tsv; word-level confidence
  populated; `decide_confidence(None)` is `review`; per-action page lists no
  longer overwritten by the document recovery list.
- D-22: byte and file limits enforced from directory sizes before hashing;
  canonical traversal order makes `duplicate-bytes:<owner>` and `plan_id`
  independent of argument order.
- 3.7: per-strategy chunk producer versions (`sentence` -> 2) validated by the
  workspace; Unicode-aware sentence splitter; ASCII-only derivation keys; PDF
  raster import hoisted; 30 percent safety-rule denominator documented.
- Fixture regeneration: `phase6/goal-acceptance-matrix.json` regenerated through
  `--generate`. Diff: 61 of 74 cells changed only in `manifest_sha256`,
  `row_set_sha256`, `supervision_sha256` (and, for the 7 plain-text cells, the
  `record_id` of the same `exact-duplicate` exclusion); the 13 markdown cells are
  byte-identical because the markdown parser did not change; no cell changed its
  exclusion reasons, supervised keys, loss policy, or instruction. The Phase 16
  compatibility kit's text-parser `report_digest` and the kit SHA pinned by five
  closeout tests were regenerated (source id unchanged). `docs/migration.md`
  records every producer version move.
- D-07 investigated and withdrawn: `canonical_digest` serializes through
  `lossless_json_bytes` and does not NFC-normalize; the NFC helper
  `canonical_json_bytes` has no production callers. The exact fingerprint was
  already exact and consistent with the conflict key. A regression pinning
  NFC/NFD distinctness is added in Phase 4 instead of a fingerprint v2.

## 2026-09-09 — Local takeover and stages 1–3 verification

- Verified branch `cursor/post-20-defect-closure-e294` and local/remote HEAD
  `3e529f4498312b64e3092cd977a8238bdc84586b`. The saved branch has 22 commits
  after `5d617f88c1b22513c5f52ac5682a6a5088570d96`. PR #203 has one separate
  commit, `ae5e13cb0f064a811f10320826f049b9ee5d9c3e`, on
  `feat/quality-report-dataset-row`; neither branch contains the other.
  No integration of #203 was performed. All six local-only files matched
  their preserved copies and SHA-256 receipts before edits.
- The unchanged saved HEAD passed lock, Ruff, and tracking checks. The core
  gate produced `2 failed, 2804 passed, 4 skipped, 32 deselected` in 388.57s.
  Both failures reproduced GitHub: stale project-spec manifest and fixture
  inventory missing `group5/two-page-text.pdf` (912 bytes).
- Recompiled the retained project-spec example from isolated source trees at
  base and saved HEAD. Base reproduced manifest
  `d3f76eb9993476def1bb373ed80eccc9ac7a1bc529c96c04e6667eaa02e88ac8`;
  saved HEAD reproduced
  `e1146ecae6f714fd5a189d313211bfb37f98907047e6930554b2bb4936e1db3b`.
  Raw sources and spec were identical. Recovered payloads were identical as
  a combined set, but parser-derived record identities changed partition
  assignment: Alpha moved from train to evaluation, Beta from evaluation
  to train. Both runs retained one row in each partition. Updated only the
  manifest pin. Regenerated the repository fixture aggregate with
  `scripts/scan_corpus_metadata.py tests/fixtures --source-id repository-test-fixtures --evidence-grade test-verified --portability repository-tracked`.
- Review of D-13 reproduced numeric overflow (`1e999` projected as `inf`).
  JSON and JSONL now refuse overflowing exponents, with producer pins
  `1.1.1` and ten negative cases. Regenerated the 74-cell fixture through
  its existing `--generate` command. Only the JSON-record cells changed,
  and only manifest, row-set, and supervision digests changed.
- The Mac cancellation fake did not create a workspace after D-04 correctly
  moved app-owned files to a sibling sidecar. The fake now reproduces the
  real `parse -o` workspace creation. The receipt continues to report actual
  filesystem existence. No assertion was weakened.
- Focused takeover regressions: `29 passed` in 1.43s. Full exit gates remain
  pending until their results are recorded below.

- Final stages 1–3 exit gates: lock, Ruff, tracking, and diff checks passed.
  Core: `2816 passed, 4 skipped, 32 deselected`, one expected transport warning,
  in 421.64s. The preceding repaired run exposed a second stale copy of the
  project-spec manifest in the Phase 20 adversarial test; both pins now agree.
- Unsigned Debug Mac runtime: `114 tests, 0 failures` in 353.871s, including
  the 74-cell matrix, real dataset-row compile, and cancellation receipts.
  The fake waits for its cancellation handler to be installed before the test
  cancels. D-23 remains open for stage 8.

## 2026-09-09 — Stage 4 (exact export payloads and ZIP64)

- D-15: all seven exact exporters decode their emitted payload bytes and
  provenance into fresh rows before the service compares membership and order.
  Profile prompt assembly uses the verified source field boundary to reverse
  the declared mapping. Trainer round-trip claims remain false.
- A shared planner/renderer corruption reproduced publication of altered data
  in all seven exporters before the fix. All seven now refuse before publication.
- D-16: canonical ZIP64 size and offset extensions emitted by the standard
  library writer are accepted. Extra fields outside that exact encoding refuse.
  The reduced-limit fixture reproduced the writer/verifier mismatch before repair.
- D-07 remains withdrawn: document and imported record regressions prove that
  NFC and NFD text remain distinct. There is no fingerprint version change.
- Stage 4 tests ran on an isolated copy of the repaired working tree. The
  integrated source files were byte-compared with that tested copy. Export and
  profile suite: `593 passed, 3 skipped, 30 deselected` in 30.57s. Core:
  `2829 passed, 4 skipped, 32 deselected`, one expected transport warning, in
  429.02s. Lock, Ruff, tracking, and diff checks passed after integration.

## 2026-09-09 — Stage 5 implementation and focused verification

- D-17: `review-export --workspace` derives the exact current pending items.
  `construct --review-packet` strictly checks the current recipe, result, plan,
  and complete candidate set, then persists the submitted packet and bundle
  identities with the exact unsigned resolution in existing review evidence.
  Python, CLI, and MCP complete accepted decisions and explicit waivers through
  seal and external-digest verification. Rejections remain rejected and cannot
  waive coverage. Corrections require new source or mapping revisions.
  Dataset-row `required` review now refuses execution because its v1 schema
  has no durable receipt. Default review remains `none`; schemas are unchanged.
- D-18: goal and preset construct paths compare all resolved segmentation
  settings. Explicit strategy, size, and overlap overrides are available on
  Python, CLI, and MCP. Pipeline execution carries explicit chunk overrides
  into construct, including after resume filters completed stages.
- D-19: resume checks Python, Veriformis, and declared-extra pins. External
  pipeline content is captured, hashed, and decoded together. Returned locks
  retain the bytes executed even if the reference changes during execution.
  Conflicting stage pins refuse before parse. Embedded spec digests do not change.
- D-21: the scale harness invokes and catches actual cancellation, checks the
  retained parse-only revision, and resumes through seal and external-digest
  verification. A callback that does not cancel leaves both observation flags
  false. Support tiers remain empty.
- D-20: document gates independently check lifecycle, curation, deduplication,
  quality, balance, leakage, binding, objective, schema, and target placement.
  Imported validation reconstructs mappings from exact raw source bytes and
  uses those bytes for split digests. Gate, snapshot, and row-set loaders reject
  incomplete or contradictory rehashed reports. Valid-output schemas stay v1.
- Workflow checkpoint: `102 passed, 1 deselected` in 30.11s. The 74-cell
  cross-surface checkpoint before the independent validation changes passed
  `297 tests` in 278.60s with no golden changes. Validation-focused suite:
  `85 passed` in 11.06s. The common serializer/replay corruption and forged
  imported report regressions passed (`15 tests` in 1.15s). Full stage 5 exit
  gates remain pending; these checkpoints are not stage closeout.

## 2026-09-09 — Stage 5 exit gates

- Full required core gate: `2869 passed, 4 skipped, 32 deselected`, one
  expected transport warning, in 415.95s. This includes the complete 74-cell
  Python, CLI, MCP, and pipeline-spec matrix after the validation repairs.
- `uv lock --check`, Ruff, project tracking, and `git diff --check` passed.
  D-17 through D-21 are closed within their documented v1 perimeter.

## 2026-09-09 — Stage 6 implementation

- D-29: committed anchors replace the digest read from the current seal output.
  Both acceptance objectives require nonempty evaluation. Each measured build
  produced one train and two evaluation rows. Full text manifest:
  `7fce43f7e71d5d8896d30eefb9ffaaf9248b0fda191c46e5e1abd6f6b52fac4c`.
  Continuation manifest:
  `ae8e08c40f4b772706c867582637fc570f8ee11f36cdceafe9f28a97ca258002`.
  The standalone shell gate passed both anchors and transport verification.
- D-30: the negative tests now cover malformed parser content, partial
  publication, forged handoff capabilities and provenance, common exporter
  corruption, noncanonical ZIP64 metadata, stale or incomplete reviews,
  conflicting stage pins, environment drift, raw-capture drift, forged gate
  sets, source coverage loss, and common serializer/replay corruption.
  The evidence table names these regressions by defect. The added golden
  regression supplies a wrong committed anchor and verifies refusal.
- D-31: shared fixture and MCP helpers move to `tests/support/`, preserving
  fixture bytes and test assertions. No test imports a collected test module.
  MCP harnesses own their asyncio loops. CI actions use official immutable
  commit pins. The required `acceptance-matrix` job runs the marked acceptance,
  goal/input-family, and export round-trip cells; four Python/OS jobs run the
  other core tests. Local full gates include both selections.
- Focused workspace and CI regressions: `105 passed` in 9.50s. The helper
  extraction initially lost two dataclass decorators; restored before the
  exit gate. Full stage 6 gates remain pending.

## 2026-09-09 — Stage 6 exit gates

- Full required core gate: `2873 passed, 4 skipped, 32 deselected`, one
  expected transport warning, in 420.63s. This includes both the marked
  acceptance matrix and the other core tests after the helper extraction.
- `uv lock --check`, Ruff, project tracking, and `git diff --check` passed.
  D-29 through D-31 are closed. The changed GitHub jobs still require a
  successful run on the pushed final branch.

## 2026-09-09 — Stage 7 implementation

- D-32: one scoped history verification per outer command. Nested loaders
  reuse captured artifact bytes and copied source/IR/chunk replay results.
  HEAD remains a live read under the commit lock. File facts are rechecked
  on reuse and before promotion; staged cache entries follow only verified
  object installation. Bytes spill to temporary storage after eight MiB.
- D-33: execute inspects its source once, binds reuse to unchanged closed-tree
  file facts, and rechecks after the last cancellation callback. Both renderers
  still receive fresh strict inputs. The first byte tree is spooled; exact
  comparison uses chunks and semantic replay loads each tree separately.
  Two renders still precede any semantic replay. Existing refusal-order tests
  caught and corrected an initial change to that order.
- D-34: an exact prefix join replaces unconditional all-pairs scoring.
  Exhaustive randomized integer-score comparison and full report byte equality
  pass. Two hundred disjoint shingle sets require zero exact pair scores.
  Dense clusters still require all reported member pairs; no scale tier changes.
- D-35: document semantic replay is split into stage functions. The transaction
  retains the publication and error boundaries. Construction and finished
  output kinds derive from the contract registries. Five extracted stage
  branches preserve their statement ASTs; all existing workspace tests remain.
- Focused operation, export-storage, and near-duplicate checks: `18 passed`
  in 1.76s. Workspace/workflow regression checkpoint: `138 passed` in 19.30s.
  Full stage 7 gates remain pending.

## 2026-09-09 — Stage 7 exit gates

- Full required core gate: `2890 passed, 4 skipped, 32 deselected`, one
  expected transport warning, in 335.32s.
- `uv lock --check`, Ruff, project tracking, and `git diff --check` passed.
  D-32 through D-35 are closed. Stage 8 remains the Mac hardening increment.
