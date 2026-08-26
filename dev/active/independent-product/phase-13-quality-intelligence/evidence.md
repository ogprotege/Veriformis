# Phase 13 Evidence

**Status:** Open — item 13.5 leakage; report is not enforcing

**Opened:** 2026-08-25

## Predecessor evidence

Phase 12 completed. Closeout merged as PR #112 at
`892939f527974b69282296ded04eb3b43643554f`, then stamped as PR #113 at
`783a2a1448049a2fbfa384df586e9d1497b36afb`.

Operator compile of Pius X *Pascendi Dominici Gregis* at
`/Users/biscuit/Documents/Veriformis` (`2026-08-24T13-54-52Z`): `full_text`
/`text`, 31 train / 0 evaluation, manifest
`94b63232166aeedc9db797fdc0ec0167b2135d8c01bd3934635250a0a2245ace`. Seal
`self_consistent`; zip `external_digest`. Recorded in
[operator-compile-2026-08-24-pascendi.md](../operator-compile-2026-08-24-pascendi.md).

## Source-verified starting facts

| Fact | Grade | Source |
| --- | --- | --- |
| Seventeen finished-dataset validation gates | `source-verified` | `src/veriformis/contracts.py` `V1_FINISHED_DATASET_GATES` |
| Quality-finding codes are target-too-short, exact-duplicate, conflicting-target, primary-source-cap | `source-verified` | `src/veriformis/contracts.py` `V1_QUALITY_FINDING_CODES` |
| `near_duplicate_policy` is `disabled` | `source-verified` | `src/veriformis/datasets/models.py` `CurationPolicy` |
| Preflight names `no-quality-intelligence` | `source-verified` | `src/veriformis/goals/preflight.py` |
| There is no quality-report schema | `source-verified` | `FINISHED_DATASET_SCHEMA_IDS` |
| CLI has no `quality-report` command | `source-verified` | `src/veriformis/cli.py` |

## Required item 13.1 evidence

- [x] Packet opened; Phase 13 `in_progress`; Phase 12 merge cited.
- [x] Seventeen gates and four quality-finding codes unchanged.
- [x] `near_duplicate_policy` stays `disabled`.
- [x] Preflight still names `no-quality-intelligence`.
- [x] CLI and MCP have no quality-report command.
- [x] Focused isolation tests, tracking, Ruff, lock, and diff check.

## Required item 13.2 evidence

- [x] `veriformis.quality-report/v1` binds to a finished-dataset plan.
- [x] Facts, policy decisions, and recommendations are separate types.
- [x] `enforcing` is false. Seal gates are unchanged.
- [x] A fact cannot be named as a recommendation. Layers cannot share names.
- [x] CLI still has no quality-report command.

## Required item 13.3 evidence

- [x] Source, objective, row, role/label, target-length, context-length,
      language-where-qualified, exclusion, split, and coverage facts.
- [x] Language without IR/field evidence is `evidence-unqualified`.
- [x] Reports reproduce from bound inputs. Mixed identities fail closed.
- [x] `enforcing` is false. Policy and recommendations stay vacant.
- [x] CLI still has no quality-report command.

## Required item 13.4 evidence

- [x] Named algorithm `veriformis.near-duplicate-ws-shingle-jaccard/v1`.
- [x] Inspectable clusters and threshold previews in ppm integers.
- [x] Near-duplicates are not called semantic identity.
- [x] Included records are not deleted. `near_duplicate_policy` stays disabled.
- [x] `enforcing` is false. Policy is `record-only`.

## Required item 13.5 evidence

- [x] Imported partition-hint mismatches are facts, not deletions.
- [x] Optional reference corpora are bound by digest.
- [x] Unbound corpora are recorded as `unbound`.
- [x] The report does not certify contamination absence.
