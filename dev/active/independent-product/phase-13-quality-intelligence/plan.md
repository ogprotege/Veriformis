# Phase 13 Execution Plan

**Status:** In progress

**Last updated:** 2026-08-25

**Authority:** [Independent Product Roadmap](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md) Phase 13; [program.json](../program.json); [Finished Dataset Contract v1](../../../../docs/contracts/finished-dataset-v1.md).

**Predecessor:** Phase 12 closeout merged as PR #112 at
`892939f527974b69282296ded04eb3b43643554f`, then stamped as PR #113 at
`783a2a1448049a2fbfa384df586e9d1497b36afb`. Clean local `main` equals
`origin/main` there.

Each numbered work item is one sequential pull request on branch
`phase13/0N-<slug>` titled `Phase 13.N: <imperative>`. A pull request must
pass its focused and required repository gates, pass every GitHub check,
merge, and leave clean local `main` equal to `origin/main` before the next
item begins. The repository is public; sequential PRs are the operator
instruction of 2026-08-25.

Closeout is folded into 13.9. Do not start Phase 14 from this packet.

## Goal

Help users decide whether the correct compiled artifact is also a suitable
training dataset, without claiming privacy, copyright status, safety,
absence of contamination, or downstream model quality.

## Architecture

`PipelineService` remains the composition root. Existing curation findings
and the seventeen finished-dataset validation gates stay the seal path.
Quality intelligence, if later admitted, is a versioned report over bound
inputs: facts stay separate from policy decisions and recommendations.
No heuristic may block seal until item 13.9 records calibrated labeled
fixtures for that heuristic.

## Standing constraints

- Facts, policy decisions, and recommendations stay separate.
- Near-duplicates are not semantic identity and must not silently delete
  rows.
- Optional detectors are findings with false-positive/negative limits, not
  certification.
- Tokenizer simulations require an exact tokenizer revision and policy from
  a profile.
- Every blocking heuristic needs a predeclared threshold and labeled-fixture
  performance before it can fail seal.
- Python / CLI / MCP agree on report identity and finding names.
- Do not start Phase 14 from this packet.

## Key decisions (lock at 13.1)

| Decision | Recommendation | Why |
| --- | --- | --- |
| Sequential PRs | 13.1 then 13.2 through 13.9, one green merge at a time. | Operator instruction 2026-08-25; same as Phase 12. |
| Packet first | 13.1 opens tracking and proves current quality facts. | Honesty pattern of Phase 8.1 / 10.1 / 12.1. |
| No report in 13.1 | Do not add `quality-report` schema, CLI, or MCP. | Declaring the report implies later heuristics. 13.2 owns the contract. |
| No blocking in 13.1 | `near_duplicate_policy` stays `disabled`. | Roadmap item 9; calibrate before enforcement. |
| Closeout in 13.9 | Previewable gates and labeled fixtures close the phase. | Roadmap items 8–9; Phase 12 folded closeout into the last item. |

## Likely files (created across the phase)

- Create: `dev/active/independent-product/phase-13-quality-intelligence/` packet (13.1)
- Create later: quality-report contract, heuristics, fixtures, CLI/MCP preview
- Do not modify in 13.1: validation gates, quality-finding codes, curation
  policy, seal path, extras, taxonomy, consumer profiles

---

## Checklist

### 13.1 Open the quality-intelligence packet

**Branch:** `phase13/01-quality-packet`
**Title:** `Phase 13.1: Open the quality-intelligence packet`

- [x] Confirm the predecessor gate: Phase 12 completed, `HEAD == origin/main`.
- [x] Create the standard Phase 13 packet. Mark Phase 13 `in_progress` in
      `program.json`. Reconcile active tracking documents. Cite the Phase 12
      closeout merge.
- [x] Prove the seventeen finished-dataset gates and four quality-finding
      codes are unchanged.
- [x] Prove `near_duplicate_policy` stays `disabled`.
- [x] Prove preflight still names `no-quality-intelligence`.
- [x] Prove CLI and MCP have no quality-report command.
- [x] Record focused, tracking, lint, lock, and diff evidence. Do not claim
      quality intelligence.

### 13.2 Define the versioned quality report

**Branch:** `phase13/02-quality-report`
**Title:** `Phase 13.2: Define the versioned quality report`

- [x] Versioned report schema with facts separated from policy decisions and
      recommendations. No heuristic enforcement.

### 13.3 Report dataset distributions

**Branch:** `phase13/03-distributions`
**Title:** `Phase 13.3: Report dataset distributions`

- [ ] Source, objective, row, role/label, target-length, context-length,
      language where evidence-qualified, exclusion, split, and coverage
      distributions.

### 13.4 Add near-duplicate detection

**Branch:** `phase13/04-near-duplicates`
**Title:** `Phase 13.4: Add near-duplicate detection`

- [ ] Named, versioned algorithm; inspectable clusters; threshold previews.
      Do not call it semantic identity. Do not silently delete rows.

### 13.5 Add leakage checks against bound corpora

**Branch:** `phase13/05-leakage-checks`
**Title:** `Phase 13.5: Add leakage checks against bound corpora`

- [ ] Leakage checks across imported partitions and optional external
      evaluation/reference corpora bound by digest.

### 13.6 Add tokenizer-bound length simulations

**Branch:** `phase13/06-tokenizer-simulations`
**Title:** `Phase 13.6: Add tokenizer-bound length simulations`

- [ ] Token-length and truncation simulations only when a profile supplies
      an exact tokenizer revision and policy.

### 13.7 Add optional PII and policy detectors

**Branch:** `phase13/07-policy-detectors`
**Title:** `Phase 13.7: Add optional PII and policy detectors`

- [ ] Optional detectors for likely PII, secrets, unsafe content, or license
      policy signals. Findings, not certification.

### 13.8 Add split-comparability and rare-shape findings

**Branch:** `phase13/08-split-findings`
**Title:** `Phase 13.8: Add split-comparability and rare-shape findings`

- [ ] Split-comparability, imbalance, rare-shape, malformed-role, and empty
      target/context findings.

### 13.9 Preview quality gates and close Phase 13

**Branch:** `phase13/09-gates-closeout`
**Title:** `Phase 13.9: Preview quality gates and close Phase 13`

- [ ] Every quality gate configurable, versioned, previewable, and recorded
      in the plan and validation snapshot. Calibrated labeled fixtures before
      a heuristic may block seal. Closeout. Do not start Phase 14.

## Usability criteria

| ID | Criterion |
| --- | --- |
| U1 | Facts stay separate from policy decisions and recommendations. |
| U2 | Reports reproduce from bound inputs. |
| U3 | A heuristic cannot block seal without a predeclared threshold and labeled-fixture evidence. |
| U4 | Findings link to source or row evidence. |
| U5 | Near-duplicates are not called semantic identity and do not silently delete rows. |
| U6 | Detectors are findings with false-positive/negative limits, not certification. |
| U7 | Privacy, copyright status, safety, contamination absence, and model quality are not claimed. |
| U8 | Python, CLI, and MCP agree on report identity and finding names. |
| U9 | Phase 14 does not start from this packet. |

## Exit gate

Reports reproduce from bound inputs; all blocking heuristics have
predeclared thresholds and labeled-fixture performance; findings link to
source/row evidence and can be reviewed.

**Result:** Pending item 13.1. See [closeout.md](closeout.md).
