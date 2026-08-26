# Phase 14 Execution Plan

**Status:** In progress

**Last updated:** 2026-08-26

**Authority:** [Independent Product Roadmap](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md) Phase 14; [program.json](../program.json); [Dataset Construction Contract v1](../../../../docs/contracts/dataset-construction-v1.md); [Finished Dataset Contract v1](../../../../docs/contracts/finished-dataset-v1.md); [Quality Report Contract v1](../../../../docs/contracts/quality-report-v1.md).

**Predecessor:** Phase 13 closeout merged as PR #122 at
`ef31559c9184b553209a3c45eca5d943fbb9a680`, then stamped as PR #123 at
`4d7b00fca9b685df95aa2a19349604f2b40d2406`. Clean local `main` equals
`origin/main` there.

Each numbered work item is one sequential pull request on branch
`phase14/0N-<slug>` titled `Phase 14.N: <imperative>`. A pull request must
pass its focused and required repository gates, pass every GitHub check,
merge, and leave clean local `main` equal to `origin/main` before the next
item begins. The repository is public; sequential PRs are the operator
instruction of 2026-08-25.

Closeout is folded into 14.8. Do not start Phase 15 from this packet.

## Goal

Make ambiguous recovery, mapping, curation, and quality decisions resolvable
without editing content-addressed files by hand.

## Architecture

`PipelineService` remains the composition root. CLI, MCP, and later Mac
Review screens are adapters. Construction `ReviewEvidence` is the seed, not
the whole model. Corrections are new transforms or mapping revisions.
Waivers do not change bytes. Default `review_policy` stays `none`. Required
review, once declared, must refuse seal. Phase 13 heuristics stay findings
unless an opt-in policy names them.

## Standing constraints

- One composition root. No dataset policy in Swift in this packet.
- Default review policy is `none`. Required review is opt-in and then
  fail-closed.
- Waiver never changes bytes. Correction always creates a new identity.
- No default Phase 13 heuristic becomes a required-review trigger.
- Reviewer identity is an opaque local unsigned attestation.
- Core queues: construction pending, conflicts, OCR `review`, mapping,
  parser degradation. Sampling is its own item. Near-duplicate and
  detector queues are opt-in only.
- Mac Review screens belong to Phase 18.
- Do not start Phase 15 from this packet.

## Key decisions (lock at 14.1)

| Decision | Recommendation | Why |
| --- | --- | --- |
| Sequential PRs | 14.1 then 14.2 through 14.8, one green merge at a time. | Operator instruction; same as Phases 12–13. |
| Packet first | 14.1 opens tracking and proves current review facts. | Honesty pattern of 13.1. |
| No queue in 14.1 | Do not add review-queue schema, submit command, or Mac UI. | Declaring queues implies later seal blocking. 14.2 owns contracts. |
| Six operator locks | API+CLI/MCP in 14; Mac in 18; core queues as named; default `none`; waiver ≠ correction; no default 13 heuristic trigger; unsigned local reviewer. | Operator accepted 2026-08-26 against the product mission. |
| Closeout in 14.8 | Supersession and exit evidence close the phase. | Same fold as Phase 13.9. |

## Likely files (created across the phase)

- Create: `dev/active/independent-product/phase-14-review-workflows/` packet (14.1)
- Create later: review contracts, queues, corrections, sampling, exchange, seal block
- Do not modify in 14.1: validation gates, quality admission, construction
  `ReviewEvidence` schema, seal path, Mac UI

---

## Checklist

### 14.1 Open the review-workflow packet

**Branch:** `phase14/01-review-packet`
**Title:** `Phase 14.1: Open the review-workflow packet`

- [x] Confirm the predecessor gate: Phase 13 completed, `HEAD == origin/main`.
- [x] Create the standard Phase 14 packet. Mark Phase 14 `in_progress` in
      `program.json`. Reconcile active tracking documents. Cite the Phase 13
      closeout merge. Record the six operator locks.
- [x] Prove construction `review_policy` defaults to `none`.
- [x] Prove `ReviewEvidence` is an unsigned local attestation.
- [x] Prove CLI, MCP, and `PipelineService` cannot submit completed review
      evidence.
- [x] Prove OCR preview and quality findings are not review queues.
- [x] Prove no Phase 13 heuristic is admitted to block seal.
- [x] Record focused, tracking, lint, lock, and diff evidence. Do not claim
      review queues.

### 14.2 Define review contracts

**Branch:** `phase14/02-review-contracts`
**Title:** `Phase 14.2: Define review contracts`

- [x] Versioned identity, queue, assignment, verdict, rationale, waiver, and
      supersession contracts. No Mac. No seal change.

### 14.3 Add first queues over existing facts

**Branch:** `phase14/03-first-queues`
**Title:** `Phase 14.3: Add first queues over existing facts`

- [x] Construction pending, conflicts, OCR `review`, mapping, and parser
      degradation as real queues. Near-duplicate and detector queues remain
      opt-in. Findings still do not delete rows.

### 14.4 Implement corrections as transforms or mapping revisions

**Branch:** `phase14/04-corrections`
**Title:** `Phase 14.4: Implement corrections as transforms or mapping revisions`

- [x] Corrections create a new transform or mapping revision. Fail closed on
      in-place mutation of accepted records. Waivers do not change bytes.

### 14.5 Add deterministic sampling

**Branch:** `phase14/05-sampling`
**Title:** `Phase 14.5: Add deterministic sampling`

- [x] Named seed, complete population and selection evidence, replay. No
      statistical meaning claimed.

### 14.6 Add review exchange on CLI, MCP, and Python

**Branch:** `phase14/06-review-exchange`
**Title:** `Phase 14.6: Add review exchange on CLI, MCP, and Python`

- [x] Export and import review packets. Close “CLI cannot submit completed
      human review evidence.” No Mac Review screens.

### 14.7 Block seal on required unresolved reviews

**Branch:** `phase14/07-required-review-seal`
**Title:** `Phase 14.7: Block seal on required unresolved reviews`

- [x] Required-review fixtures cannot seal until resolved. Default recipes
      stay `none`. No default Phase 13 heuristic trigger.

### 14.8 Add supersession and close Phase 14

**Branch:** `phase14/08-supersession-closeout`
**Title:** `Phase 14.8: Add supersession and close Phase 14`

- [ ] Inter-reviewer supersession with auditable history. Closeout. Do not
      start Phase 15 from this packet.

## Usability criteria

| ID | Criterion |
| --- | --- |
| U1 | `PipelineService` owns review policy. CLI, MCP, and later Mac are adapters. |
| U2 | Corrections are source-grounded transforms or new mapping revisions. |
| U3 | A waiver never changes dataset bytes. |
| U4 | Default `review_policy` is `none`. Required review refuses seal until resolved. |
| U5 | No Phase 13 heuristic is a default required-review trigger. |
| U6 | Reviewer identity is an opaque local unsigned attestation. |
| U7 | Python, CLI, and MCP agree on review identities. Mac Review is Phase 18. |
| U8 | Sampling replays from a named seed and records the population. |
| U9 | Phase 15 does not start from this packet. |

## Exit gate

Required-review fixtures cannot seal until resolved; every correction
replays from immutable inputs; old decisions remain auditable after
supersession.

**Result:** Pending item 14.1. See [closeout.md](closeout.md).
