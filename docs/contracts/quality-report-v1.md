# Quality Report Contract v1

**Contract ID:** `veriformis.quality-report`

**Contract version:** `1`

**Schema:** `veriformis.quality-report/v1`

**Status:** Schema pin through independent-product Phase 13.9. Item 13.9
previews configurable quality gates and records labeled fixtures. No
heuristic is admitted to block seal. Seal still uses the seventeen
finished-dataset gates. `veriformis quality-report` emits this preview;
it is not a gate. There is no MCP wrap.

**Last reviewed:** 2026-09-02

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

## Distribution facts (item 13.3)

`report_dataset_distributions` fills one closed, sorted fact set from a
bound recipe, construction result, curation result, and split result.
Integer facts are counts. Text facts are lossless canonical JSON.

| Fact | Value |
| --- | --- |
| `included-record-count` | Included records |
| `excluded-record-count` | Excluded records |
| `quarantined-record-count` | Quarantined records |
| `train-record-count` | Split train assignments |
| `evaluation-record-count` | Split evaluation assignments |
| `distinct-source-count` | Unique source identities on included records |
| `distinct-objective-count` | Unique objective identities on included records |
| `coverage-blocker-count` | Coverage blocker codes across selected sources |
| `language-evidence-qualified-count` | Language tokens from a `language` field or an IR pointer ending `/language` |
| `language-evidence-unqualified-count` | Included records with no language evidence |
| `source-distribution` | Source identity to included-record contribution count |
| `objective-distribution` | Objective identity to included-record count |
| `row-schema-distribution` | Recipe target row schema to included-record count |
| `role-distribution` | Schema-implied `user` / `assistant` counts for v1 `messages` (one of each per included row); otherwise empty |
| `label-distribution` | Constructed field-name counts on included records |
| `target-length-distribution` | Sorted `[character-length, count]` pairs for objective target fields |
| `context-length-distribution` | Sorted `[character-length, count]` pairs for objective context fields |
| `language-distribution` | Evidence-qualified language tokens, or reserved `evidence-unqualified` |
| `exclusion-distribution` | Curation reason codes for non-included records |
| `split-distribution` | `train` and `evaluation` assignment counts |
| `coverage-distribution` | Per-source ledger counts and blocker codes |

Language is reported only where constructed evidence names it: a field named
`language`, or an IR pointer whose last token is `language` (v1
`structured_field` stores that scalar on `fields`). The compiler does not
infer a document language. `evidence-unqualified` is reserved for records
with no such evidence. Lengths are Unicode character counts, not tokens.
v1 `messages` role counts are schema-implied from the two-turn lowering,
not a replay of serialized payloads. Distributions do not delete rows.

## Near-duplicates (item 13.4)

`report_near_duplicates` adds facts from algorithm
`veriformis.near-duplicate-ws-shingle-jaccard/v1`. It is not semantic
identity. It does not delete rows.

| Fact | Value |
| --- | --- |
| `near-duplicate-algorithm` | Algorithm id |
| `near-duplicate-shingle-size` | Character n-gram size (`5`) |
| `near-duplicate-cluster-threshold-ppm` | Inspectable cluster threshold (`800000`) |
| `near-duplicate-cluster-count` | Clusters of size ≥ 2 at that threshold |
| `near-duplicate-member-count` | Included records in those clusters |
| `near-duplicate-clusters` | Sorted list of `{cluster-id, record-ids, pair-similarities-ppm}`. `cluster-id` is `canonical_digest({algorithm, record-ids})`. `record-ids` are sorted. Each pair is `[left, right, ppm]` with `left < right` and integer ppm |
| `near-duplicate-threshold-preview` | Object keyed by decimal ppm strings `"500000"`, `"800000"`, `"900000"`, `"990000"` to `{cluster-count, member-count}` integers |

Normalization is strip, whitespace collapse, and Unicode casefold of the
objective target fields. Similarity is integer Jaccard over overlapping
5-grams, stored as parts per million. Policy records
`near-duplicate-disabled` as `record-only`. Curation
`near_duplicate_policy` remains `disabled`.

## Leakage (item 13.5)

`report_leakage_checks` adds facts. It does not certify contamination
absence.

| Fact | Value |
| --- | --- |
| `leakage-cross-partition-exact-target-count` | Distinct target SHA-256 values present in both train and evaluation |
| `leakage-imported-partition-mismatch-count` | Included records whose imported hint differs from the split assignment |
| `leakage-imported-partition-mismatches` | `{record-id, hinted, assigned}` rows, sorted by record id |
| `leakage-reference-corpus-digest` | Canonical digest of a bound corpus, or `unbound` |
| `leakage-reference-corpus-hit-count` | Included records whose target SHA-256 is in the bound corpus |
| `leakage-reference-corpus-hits` | Sorted included record ids that hit the corpus |

A bound corpus is the sorted unique SHA-256 set of exact target strings.
Unknown imported record ids fail closed. Policy records
`leakage-record-only` as `record-only`.

## Tokenizer simulations (item 13.6)

`report_tokenizer_simulations` records token-length facts only when the
caller supplies a bound tokenizer id, revision, positive max-token
policy, and encode function. Whitespace splitting is not a production
tokenizer. Without a pin the status is `unbound` and lengths stay empty.

| Fact | Value |
| --- | --- |
| `tokenizer-status` | `unbound` or `simulated` |
| `tokenizer-id` | Pin id, or `unbound` |
| `tokenizer-revision` | Pin revision, or `unbound` |
| `tokenizer-max-tokens` | Positive policy integer, or `0` when unbound |
| `tokenizer-target-length-distribution` | Sorted `[token-count, count]` pairs |
| `tokenizer-truncation-count` | Included records whose token count exceeds max-tokens |

Encode without a pin, or a pin without encode, fails closed. Policy
records `tokenizer-record-only`.

## Policy detectors (item 13.7)

`report_policy_detectors` scans included field values with named regular
expressions in `veriformis.policy-detectors/v1`. Hits are findings with
false-positive/negative limits. They do not certify privacy, safety, or
license status.

| Fact | Value |
| --- | --- |
| `detector-set-id` | `veriformis.policy-detectors/v1` |
| `detector-pii-hit-count` | Records matching `pii-email` |
| `detector-secret-hit-count` | Records matching AWS-key or PEM private-key patterns |
| `detector-unsafe-hit-count` | Records matching `unsafe-script-tag` |
| `detector-license-hit-count` | Records matching `license-gpl-3` |
| `detector-hits` | Sorted `{record-id, family, pattern-id}` rows |

Policy records `detector-findings-not-certification` as `record-only`.

## Family-hook facts

`family_hook_facts` counts explicit advanced-family fields on included
records. Absent fields stay zero on ordinary SFT rows. These facts feed
preview-only gates. They do not block seal.

| Fact | Value |
| --- | --- |
| `family-missing-label-count` | Included records with an empty `label` field |
| `family-ranking-tie-count` | Extra copies of the same ranked entity/prompt |
| `family-singleton-label-set-count` | `1` when included records share exactly one nonempty label |
| `family-tool-role-gap-count` | Tool fields without a role |
| `family-unpaired-without-policy-count` | `feedback` without `chosen`/`rejected` |

Preview gates `preview-family-missing-label`, `preview-family-ranking-tie`,
`preview-family-singleton-label-set`, `preview-family-tool-role-gap`, and
`preview-family-unpaired-without-policy` bind those facts. `admitted-to-block`
stays false.

## Split findings (item 13.8)

`report_split_findings` records comparability of train versus evaluation
source membership, integer imbalance in ppm, rare field-name shapes, and
empty or malformed-role counts. v1 construction forbids empty fields and
malformed messages roles, so those counts stay zero on valid artifacts.

| Fact | Value |
| --- | --- |
| `split-source-comparability` | Per-source `{train, evaluation}` included counts |
| `split-imbalance-ppm` | `abs(train-eval)*1000000/total` integer |
| `split-rare-shape-count` | Field-name signatures that occur once |
| `split-rare-shapes` | Sorted rare signature strings |
| `split-empty-target-count` | Included records missing a target value |
| `split-empty-context-count` | Included records missing a context value |
| `split-malformed-role-count` | Included records with non-v1 message roles |

Policy records `split-findings-record-only`.

## Quality gates (item 13.9)

`preview_quality_gates` compares integer facts to a versioned policy
`veriformis.quality-gate-policy/v1`. Gates are configurable and
previewable. They bind to the finished-dataset `plan_id`. They do not
add fields to `FinishedDatasetPlan` or the seventeen-gate validation
snapshot. `admitted-to-block` is false for every v1 gate. A caller that
sets `admitted_to_block=True` fails closed.

| Fact | Value |
| --- | --- |
| `quality-gate-policy-id` | `veriformis.quality-gate-policy/v1` |
| `quality-gate-plan-id` | Finished-dataset plan identity |
| `quality-gate-preview` | Sorted `{gate-id, fact, threshold, observed, would-block, admitted-to-block}` rows |
| `quality-gate-would-block-count` | Gates whose observed integer meets the threshold |
| `quality-admitted-blocking-count` | Always `0` in v1 |
| `quality-labeled-fixture-set-id` | `veriformis.quality-labeled-fixtures/v1` |
| `quality-labeled-fixture-count` | Closed labeled-fixture catalog size |

Policy records `quality-gates-preview-only` and
`quality-no-heuristic-admitted-to-block`. Labeled fixtures calibrate
detector, near-duplicate, leakage, family-hook, and split-empty/role heuristics.
None of those heuristics is admitted to fail seal.

## Enforcement

`enforcing` is `false`. Item 13.9 cannot fail seal. A heuristic may block
seal only after a later admission records labeled-fixture performance
for that heuristic. The seventeen finished-dataset gates remain the
seal path.

## Binding

Every report names a finished-dataset `plan_id`. Identity is
`derive_id("qrp", …)` over the payload excluding `report_id`. Distribution
inputs must share that plan, recipe, construction result, and curation
result. Split input identities must equal the included records.

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

Phase 14 review queues are out of scope. Semantic identity, silent row
deletion, contamination/privacy/safety/license certification, and
invented tokenizers are out of scope.
