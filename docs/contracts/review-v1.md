# Review Contract v1

**Contract ID:** `veriformis.review`

**Contract version:** `1`

**Schema:** `veriformis.review-bundle/v1`

**Status:** Schema pin through independent-product Phase 14.5. Item 14.5
adds named-seed HMAC-SHA256 sampling with complete population evidence.
It claims no statistical meaning. The bundle does not block seal. There
is no review-submit CLI command. Mac Review belongs to Phase 18.

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
| `sample-acceptance` | Named-seed sample; not a required review |
| `near-duplicate` | Opt-in only |
| `detector-finding` | Opt-in only |

## Sampling

Algorithm `veriformis.review-sample-hmac-sha256/v1` ranks a complete
recorded population by HMAC-SHA256 of a named lowercase seed and the
subject token, then takes `size` members. The draw replays. It is not
a random sample, confidence interval, or representativeness claim.
Sample-acceptance items are not required reviews.

## Waiver and correction

A waiver has `changes_bytes=false` and does not produce a transform. A
correction `kind` is `transform` or `mapping-revision` and names a new
`result_id` (`trn` or `mpl`). A transform must change bytes. A mapping
revision must create a new mapping-plan identity. In-place mutation of
accepted records fails closed.

## Limitations

- `default-review-none`
- `no-default-heuristic-required-review`
- `no-mac-review`
- `no-seal-block`
- `unsigned-reviewer`
- `waiver-does-not-change-bytes`

## Non-goals

Mac Review screens. CLI submit. Seal blocking. Phase 15 scale work.
Privacy or safety certification from detector findings. In-place edits
of content-addressed records. Statistical meaning for samples.
