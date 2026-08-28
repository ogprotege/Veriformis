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
- [ ] Every GitHub check passes.
- [ ] PR merges and clean local `main` equals `origin/main` before 17.4.

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
