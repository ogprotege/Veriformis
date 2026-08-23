# Phase 8 Evidence

**Status:** Open — item 8.1 packet opening

**Opened:** 2026-08-23

## Predecessor evidence

Phase 7 completed. Item 7.10 merged as PR #80 at
`b7bb7f0c2046fba87fd7c9da12f7d2ccb5c2c88f` after all 14 GitHub checks passed.
Active-doc continuity merged as PR #81 at
`64a7799c27d1a489f01d77d8ba399910c95c0712`.

## Source-verified starting facts

| Fact | Grade | Source |
| --- | --- | --- |
| Generic export discovery has a null consumer profile | `source-verified` | `src/veriformis/exports/split_jsonl.py` and siblings; `tests/goals/test_goal_contracts.py` |
| `trl` and `mlx-lm` are planned taxonomy identifiers | `source-verified` | `src/veriformis/taxonomy.py`; `docs/governance/support-registry.json` |
| Core optional extras are only `test` | `source-verified` | `pyproject.toml` |
| `ExportConsumerProfile` exists as a persisted model | `source-verified` | `src/veriformis/exports/models.py` |
| Aptus is an optional sibling handoff, not a generic export profile | `source-verified` | `src/veriformis/handoff/aptus_v1.py` |

## Required item 8.1 evidence

- [x] Packet opened; Phase 8 `in_progress`; Phase 7 merge cited.
- [x] ADR-0012 published and indexed.
- [x] `trl` and `mlx-lm` remain planned and refuse export with items 8.3 and 8.4.
- [x] Candidate profiles refuse as Phase 10.
- [x] Generic discovery still has `consumer_profile` null.
- [x] `pyproject.toml` optional extras remain only `test`.
- [x] Core pytest: 1964 passed, 1 deselected, expected transport warning.
