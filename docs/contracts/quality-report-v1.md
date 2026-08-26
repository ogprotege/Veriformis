# Quality Report Contract v1

**Contract ID:** `veriformis.quality-report`

**Contract version:** `1`

**Schema:** `veriformis.quality-report/v1`

**Status:** Schema pin through independent-product Phase 13.2. The report does
not enforce heuristics. Seal still uses the seventeen finished-dataset gates.
There is no quality-report CLI command.

**Last reviewed:** 2026-08-25

**Authority:** [Independent Product Roadmap](../plans/2026-08-11-veriformis-independent-product-roadmap.md) Phase 13.

## Purpose

Record dataset quality intelligence as a bound, replayable report. Facts stay
separate from policy decisions and recommendations. This contract does not
certify privacy, copyright status, safety, absence of contamination, or
downstream model quality.

## Layers

| Layer | Meaning in v1 |
| --- | --- |
| `facts` | Observed counts or text bound to the finished-dataset plan |
| `policy_decisions` | Named actions. v1 admits only `record-only` |
| `recommendations` | Advisory messages that may name facts. They are not facts |

A name cannot appear in both `facts` and `policy_decisions`. A recommendation
may only name facts that are present in the same report.

## Enforcement

`enforcing` is `false`. Item 13.2 cannot fail seal. Later items may add
previewable gates; a heuristic may block seal only after item 13.9 records
calibrated labeled fixtures for that heuristic.

## Binding

Every report names a finished-dataset `plan_id`. Identity is
`derive_id("qrp", …)` over the payload excluding `report_id`.

## Limitations

The v1 limitation set is:

- `no-blocking`
- `facts-are-not-policy`
- `recommendations-are-not-facts`
- `no-privacy-certification`
- `no-copyright-certification`
- `no-safety-certification`
- `no-contamination-certification`
- `no-model-quality-claim`

## Non-goals

Distributions, near-duplicates, leakage corpora, tokenizer simulations,
PII/secret detectors, and split-comparability findings. Those are later
Phase 13 items. Phase 14 review queues are out of scope.
