# Phase 17 Evidence

**Status:** Open

**Opened:** 2026-08-28

## Predecessor evidence

Phase 16 completed. Closeout merged as PR #149 at
`a1fbf04d58d73692cc4237b7d741c5da27022581`. At Phase 17 open, clean local
`main`, `origin/main`, and `HEAD` were equal at that commit. Dependencies 3,
7, 13, 14, and 16 were complete in `program.json`.

## Source-verified starting facts

| Fact | Grade | Source |
| --- | --- | --- |
| Implemented training families remain language-modeling and SFT | `source-verified` | `src/veriformis/taxonomy.py` |
| Six advanced families remain `planned`; multimodal remains `explicitly_unsupported` | `source-verified` | `src/veriformis/taxonomy.py`; `docs/contracts/taxonomy-v1.md` |
| V1 row schemas remain `text`, `prompt_completion`, `instruction_output`, `messages` | `source-verified` | `src/veriformis/datasets/serialization.py` |
| `messages` still requires exactly two user/assistant turns | `source-verified` | `src/veriformis/mapping/execute.py`; `src/veriformis/datasets/serialization.py` |
| Mapping payloads are the four SFT shapes; docs refuse preference, tools, multimodal, and free multi-turn chat | `source-verified` | `src/veriformis/mapping/models.py`; `docs/mapping.md` |
| Constructors remain the five deterministic SFT constructors | `source-verified` | `src/veriformis/construction/constructors.py` |
| No `GeneratorPass` exists under `src/veriformis` | `source-verified` | package sources |
| Implemented trainer profiles still refuse preference, tools, ranking, stepwise, unpaired preference, and vision | `source-verified` | `src/veriformis/profiles/admission-v1.json` |
| Constrained CSV still admits only the three flat SFT schemas | `source-verified` | `src/veriformis/exports/constrained_csv.py` |
| Extension protocol still has six kinds and no family kind; no loader | `source-verified` | `src/veriformis/extensions/protocol.py`; ADR-0017 |
| `veriformis.advanced-family-admission/v1` is a schema pin; taxonomy stays planned | `source-verified` | `docs/contracts/advanced-family-admission-v1.md`; `src/veriformis/families/admission.py` |
| Split algorithm remains `transitive-leakage-prefix-v1` | `source-verified` | `src/veriformis/datasets/splitting.py` |
| Quality gates remain preview-only; default review queues have no label/preference/tool/stepwise kinds | `source-verified` | `src/veriformis/quality/gates.py`; `src/veriformis/review/models.py` |
| Seventeen Finished Dataset v1 gates remain unchanged | `source-verified` | `src/veriformis/contracts.py` |

## Required item 17.1 evidence

- [x] Standard packet opened from the Phase 16 closeout merge.
- [x] Phase 17 moved from `planned` to `in_progress` with this packet path.
- [x] L1 through L15 recorded.
- [x] Active tracking documents reconciled to Phase 17 in progress without
      claiming an implemented advanced family.
- [x] Baseline isolation tests added.
- [x] Focused tests, tracking, Ruff, lock, core pytest, and diff check pass.
- [x] Every GitHub check passed. PR #150 merged. Clean `main` equals
      `origin/main` at `712d28a`.

## Required item 17.2 evidence

- [x] `veriformis.advanced-family-admission/v1` contract and strict models.
- [x] Unknown families, fields, and contract versions fail closed with
      requested versus supported identity.
- [x] Taxonomy, constructors, and SFT row schemas unchanged.
- [x] Focused tests, tracking, Ruff, lock, core pytest, and diff check pass.
- [x] Every GitHub check passed. PR #151 merged. Clean `main` equals
      `origin/main` at `c919485`.

## Required item 17.3 evidence

- [x] Grouping keys `source`, `shared-prompt`, `conversation`, `annotator`,
      `entity` with fail-closed missing values.
- [x] Default SFT split algorithm and SplitPolicy fields unchanged.
- [x] Shared-prompt and annotator/entity grouping tests.
- [x] Focused tests, tracking, Ruff, lock, core pytest, and diff check pass.
- [x] Every GitHub check passed. PR #152 merged. Clean `main` equals
      `origin/main` at `db75e5b`.

## Required item 17.4 evidence

- [x] Opt-in review queue kinds `label-conflict`,
      `preference-inconsistency`, `tool-trace-incomplete`, and
      `stepwise-gap`. Default `review_policy` stays `none`.
- [x] Preview-only quality facts for missing label, ranking tie,
      singleton label set, tool-role gap, and unpaired-without-policy.
      Every family gate has `admitted_to_block` false.
- [x] SFT records keep family-hook counts at zero. No family execute.
- [x] Focused tests, tracking, Ruff, lock, core pytest, and diff check pass.
- [x] Every GitHub check passed. PR #153 merged. Clean `main` equals
      `origin/main` at `07bb0d0`.

## Required item 17.5 evidence

- [x] `explicit-label-classification` is implemented with objective
      `explicit_label`, row schema `label-classification`, and loss
      `label-only`.
- [x] Dataset-row mapping binds context, label, and annotator with
      `mapped_value`. Empty labels refuse. Document-source construction
      cannot invent labels.
- [x] split-jsonl and canonical json emit the schema. Constrained CSV
      and existing trainer profiles refuse it.
- [x] Focused tests, tracking, Ruff, lock, core pytest, and diff check pass.
- [x] Every GitHub check passed. PR #154 merged. Clean `main` equals
      `origin/main` at `301d1a6`.

## Required item 17.6 evidence

- [x] `preference-and-ranking` is implemented with objective
      `preference_pair`, row schema `preference-pair`, and loss
      `pair-supervision`.
- [x] Dataset-row mapping binds prompt, chosen, and rejected with
      `mapped_value`. Empty chosen or rejected refuse. Document-source
      construction cannot invent pairs.
- [x] Shared-prompt leakage keeps one prompt in one partition.
      split-jsonl and canonical json emit the schema. Constrained CSV
      and existing trainer profiles refuse it.
- [x] Unpaired feedback and ranking-order schemas skipped with a
      record: the pair contract does not cover them.
- [x] Focused tests, tracking, Ruff, lock, core pytest, and diff check pass.
- [x] Every GitHub check passed. PR #155 merged. Clean `main` equals
      `origin/main` at `4496d0e`.

## Required item 17.7 evidence

- [x] `tool-call-conversations` is implemented with objective
      `tool_call`, row schema `tool-call-conversation`, and loss
      `tool-trace-suffix`.
- [x] Dataset-row mapping binds conversation identity and ordered
      turns with `mapped_value`. Malformed traces refuse.
      Document-source construction cannot invent traces.
- [x] Conversation leakage keeps one thread in one partition.
      split-jsonl and canonical json emit the schema. Constrained CSV
      and existing trainer profiles refuse it. Two-turn `messages`
      stays exactly two turns.
- [x] Focused tests, tracking, Ruff, lock, core pytest, and diff check pass.
- [x] Every GitHub check passed. PR #156 merged. Clean `main` equals
      `origin/main` at `132fd47`.

## Required item 17.8 evidence

- [x] `stepwise-supervision` is implemented with objective `stepwise`,
      row schema `stepwise-trace`, and loss `final-step-only`.
- [x] Dataset-row mapping binds prompt and ordered steps with
      `mapped_value`. Empty or single-step traces refuse.
      Document-source construction cannot invent steps.
- [x] Shared-prompt leakage keeps one prompt in one partition.
      split-jsonl and canonical json emit the schema. Constrained CSV
      and existing trainer profiles refuse it. Copied source text is
      never labeled reasoning.
- [x] Focused tests, tracking, Ruff, lock, core pytest, and diff check pass.
- [x] Every GitHub check passed. PR #157 merged. Clean `main` equals
      `origin/main` at `d407023`.

## Required item 17.9 evidence

- [x] ADR-0018 covers offline default, model identity, supplied
      evidence, output identity, required review, isolation from
      deterministic v1 claims, and dataset-project code execution.
- [x] Decision A: no compile-path generator in Phase 17.
- [x] No `GeneratorPass`, hosted-model extra, or generate operation.
- [x] `generation_allowed` stays false and fails closed.
- [x] Focused tests, tracking, Ruff, lock, core pytest, and diff check pass.
- [x] Every GitHub check passed. PR #158 merged. Clean `main` equals
      `origin/main` at `dcd9a54`.

## Required item 17.10 evidence

- [x] Adversarial refusals: unknown family, unknown row schema, missing
      steps/traces, shared-prompt grouping, two-turn messages, nested
      CSV, profile mapping, declaration tamper, invented supervision.
- [x] Phase 16 kit goldens and SFT sealed-bundle identities unchanged.
- [x] Generation, multimodal, pre-tokenized, and unmapped profiles
      skipped with records under ADR-0018 Decision A.
- [x] Phase 17 marked completed. Do not start Phase 18 from this packet.
- [x] Focused tests, tracking, Ruff, lock, core pytest, and diff check pass.
- [ ] Every GitHub check passes.
- [ ] PR merges and clean local `main` equals `origin/main`.

## Item 17.10 local gate evidence

| Gate | Result |
| --- | --- |
| `uv run pytest -q tests/families/test_phase17_adversarial_closeout.py` | 11 passed |
| `uv run python scripts/check_project_tracking.py` | PASS |
| `uv run ruff check src tests` | PASS |
| `uv lock --check` | PASS; 50 packages resolved |
| Core pytest excluding optional integration and scale markers | 2,463 passed, 17 deselected, one expected durability warning |
| `git diff --check` | PASS |

## Item 17.9 local gate evidence

| Gate | Result |
| --- | --- |
| `uv run pytest -q tests/families/test_phase17_threat_model.py tests/families/test_family_admission.py tests/families/test_phase17_family_isolation.py` | 39 passed |
| `uv run python scripts/check_project_tracking.py` | PASS |
| `uv run ruff check src tests` | PASS |
| `uv lock --check` | PASS; 50 packages resolved |
| Core pytest excluding optional integration and scale markers | 2,452 passed, 17 deselected, one expected durability warning |
| `git diff --check` | PASS |

## Item 17.8 local gate evidence

| Gate | Result |
| --- | --- |
| `uv run pytest -q tests/families/test_stepwise_supervision.py` | 10 passed |
| `uv run python scripts/check_project_tracking.py` | PASS |
| `uv run ruff check src tests` | PASS |
| `uv lock --check` | PASS; 50 packages resolved |
| Core pytest excluding optional integration and scale markers | 2,447 passed, 17 deselected, one expected durability warning |
| `git diff --check` | PASS |

## Item 17.7 local gate evidence

| Gate | Result |
| --- | --- |
| `uv run pytest -q tests/families/test_tool_call_conversations.py` | 10 passed |
| `uv run python scripts/check_project_tracking.py` | PASS |
| `uv run ruff check src tests` | PASS |
| `uv lock --check` | PASS; 50 packages resolved |
| Core pytest excluding optional integration and scale markers | 2,437 passed, 17 deselected, one expected durability warning |
| `git diff --check` | PASS |

## Item 17.6 local gate evidence

| Gate | Result |
| --- | --- |
| `uv run pytest -q tests/families/test_preference_ranking.py` | 11 passed |
| `uv run python scripts/check_project_tracking.py` | PASS |
| `uv run ruff check src tests` | PASS |
| `uv lock --check` | PASS; 50 packages resolved |
| Core pytest excluding optional integration and scale markers | 2,427 passed, 17 deselected, one expected durability warning |
| `git diff --check` | PASS |

## Item 17.4 local gate evidence

| Gate | Result |
| --- | --- |
| `uv run pytest -q tests/families/test_advanced_review_quality.py tests/families/test_phase17_family_isolation.py tests/review/test_review_contracts.py tests/quality` | 60 passed |
| `uv run python scripts/check_project_tracking.py` | PASS |
| `uv run ruff check src tests` | PASS |
| `uv lock --check` | PASS; 50 packages resolved |
| Core pytest excluding optional integration and scale markers | 2,407 passed, 17 deselected, one expected durability warning |
| `git diff --check` | PASS |

## Item 17.5 local gate evidence

| Gate | Result |
| --- | --- |
| `uv run pytest -q tests/families/test_explicit_label_classification.py` | 9 passed |
| `uv run python scripts/check_project_tracking.py` | PASS |
| `uv run ruff check src tests` | PASS |
| `uv lock --check` | PASS; 50 packages resolved |
| Core pytest excluding optional integration and scale markers | 2,416 passed, 17 deselected, one expected durability warning |
| `git diff --check` | PASS |

GitHub checks for item 17.5 remain pending.

## Item 17.3 local gate evidence

| Gate | Result |
| --- | --- |
| `uv run pytest -q tests/families/ tests/datasets/test_splitting.py` | 52 passed |
| `uv run python scripts/check_project_tracking.py` | PASS |
| `uv run ruff check src tests` | PASS |
| `uv lock --check` | PASS; 50 packages resolved |
| Core pytest excluding optional integration and scale markers | 2,403 passed, 17 deselected, one expected durability warning |
| `git diff --check` | PASS |

GitHub checks for item 17.3 remain pending.

## Item 17.1 local gate evidence

| Gate | Result |
| --- | --- |
| `uv run pytest -q tests/families/test_phase17_family_isolation.py` | 16 passed |
| `uv run python scripts/check_project_tracking.py` | PASS; 21 roadmap phases and governed packets agree |
| `uv run ruff check src tests` | PASS |
| `uv lock --check` | PASS; 50 packages resolved |
| Core pytest excluding optional integration and scale markers | 2,376 passed, 17 deselected, one expected durability warning |
| `git diff --check` | PASS |

PR #150 merged; clean `main` synchronized.

## Item 17.2 local gate evidence

| Gate | Result |
| --- | --- |
| `uv run pytest -q tests/families/` | 34 passed |
| `uv run python scripts/check_project_tracking.py` | PASS |
| `uv run ruff check src tests` | PASS |
| `uv lock --check` | PASS; 50 packages resolved |
| Core pytest excluding optional integration and scale markers | 2,394 passed, 17 deselected, one expected durability warning |
| `git diff --check` | PASS |

PR #151 merged; clean `main` synchronized.
