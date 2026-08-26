# Review Contract v1

**Contract ID:** `veriformis.review`

**Contract version:** `1`

**Schema:** `veriformis.review-bundle/v1`

**Status:** Schema pin through independent-product Phase 14.3. Item 14.3
fills core queue kinds from construction `pending_review` and curation
conflicts. The bundle does not block seal. There is no review-submit
CLI command. Mac Review belongs to Phase 18.

**Last reviewed:** 2026-08-26

**Authority:** [Independent Product Roadmap](../plans/2026-08-11-veriformis-independent-product-roadmap.md) Phase 14.

## Purpose

Record human review as bound, replayable evidence. A waiver never changes
dataset bytes. A correction is a source-grounded transform or a new mapping
revision. Reviewer identity is an opaque local unsigned attestation.

## Bundle

`empty_review_bundle` binds to a finished-dataset `plan_id`. Identity is
`derive_id("rvb", …)` over the payload excluding `bundle_id`.
`blocks_seal` is `false` in item 14.2. Queues, items, assignments,
verdicts, waivers, corrections, and supersessions stay vacant until later
items fill them.

## Queue kinds

| Kind | Role in v1 |
| --- | --- |
| `construction-pending` | Core |
| `conflict` | Core |
| `ocr-review` | Core |
| `mapping` | Core |
| `parser-degradation` | Core |
| `sample-acceptance` | Sampling item |
| `near-duplicate` | Opt-in only |
| `detector-finding` | Opt-in only |

## Waiver and correction

A waiver has `changes_bytes=false`. A correction `kind` is `transform` or
`mapping-revision`. In-place mutation of accepted records is out of scope.

## Limitations

- `default-review-none`
- `no-default-heuristic-required-review`
- `no-mac-review`
- `no-seal-block`
- `unsigned-reviewer`
- `waiver-does-not-change-bytes`

## Non-goals

Mac Review screens. CLI submit. Seal blocking. Phase 15 scale work.
Privacy or safety certification from detector findings.
