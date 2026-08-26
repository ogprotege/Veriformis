# Review Contract v1

**Contract ID:** `veriformis.review`

**Contract version:** `1`

**Schema:** `veriformis.review-bundle/v1`

**Status:** Implemented through independent-product Phase 14 closeout.
Required unresolved reviews block seal. Corrections create new
identities. Supersession keeps prior reviews auditable. Mac Review
belongs to Phase 18.

**Last reviewed:** 2026-08-26

**Authority:** [Independent Product Roadmap](../plans/2026-08-11-veriformis-independent-product-roadmap.md) Phase 14.

## Purpose

Record human review as bound, replayable evidence. A waiver never changes
dataset bytes. A correction is a source-grounded transform or a new mapping
revision. Reviewer identity is an opaque local unsigned attestation.

## Bundle

`empty_review_bundle` binds to a finished-dataset `plan_id`. Identity is
`derive_id("rvb", …)` over the payload excluding `bundle_id`.
`blocks_seal` is true when required items remain unresolved. Default
`none` recipes do not block. A `veriformis.review-packet/v1`
round-trips pending items and completed decisions, waivers, or
corrections through Python, CLI, and MCP.

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
- `required-review-blocks-seal`
- `unsigned-reviewer`
- `waiver-does-not-change-bytes`

## Non-goals

Mac Review screens. Phase 15 scale work. Privacy or safety certification
from detector findings. In-place edits of content-addressed records.
Statistical meaning for samples. Default heuristic required-review.
