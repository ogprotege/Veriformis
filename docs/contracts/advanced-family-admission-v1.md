# Advanced Family Admission Contract v1

**Contract ID:** `veriformis.advanced-family-admission`

**Contract version:** `1`

**Schema:** `veriformis.advanced-family-admission/v1`

**Status:** Schema pin plus leakage grouping substrate. Item 17.5 admits
`explicit-label-classification` and item 17.6 admits
`preference-and-ranking` as executes on the dataset-row path.
Loading a pin is not itself an execute. Extra grouping keys do not change
default SFT split identities. Trainer-profile mappings remain empty.

**Last reviewed:** 2026-08-28

**Authority:** [Independent Product Roadmap](../plans/2026-08-11-veriformis-independent-product-roadmap.md) Phase 17.

## Purpose

Name one advanced semantic family as a closed admission pin so later items can
execute that family without inventing supervision or overloading SFT row
schemas. A pin is metadata. It is not an execute, not a taxonomy promotion,
and not an extension-protocol event.

## Families

| Family ID | Role in this contract |
| --- | --- |
| `explicit-label-classification` | Admitted execute. User-provided labels. |
| `preference-and-ranking` | Admitted execute. User-provided chosen/rejected pairs. Unpaired and ranking-order schemas skipped with a record. |
| `tool-call-conversations` | Admittable. User-provided tool traces. New schema; do not widen two-turn `messages`. |
| `stepwise-supervision` | Admittable. User-provided ordered steps. |
| `pre-tokenized-training` | Named, not admitted here. Tokenizer/model-bound. |
| `governed-generated-candidates` | Named, not admitted here. Waits for the 17.9 generator boundary. |
| `multimodal-training` | Explicitly unsupported. |

Unknown families fail closed. Errors list the four admittable family ids and
name the requested and supported contract versions.

## Pin

`veriformis.advanced-family-admission/v1` is one frozen object:

| Field | Rule |
| --- | --- |
| `contract_id` | `veriformis.advanced-family-admission` |
| `contract_version` | `1` |
| `schema_id` | `veriformis.advanced-family-admission/v1` |
| `family_id` | One of the four admittable family ids |
| `lifecycle` | `planned`, `admitted`, `deprecated`, or `removed` |
| `row_schema_ids` | Non-empty sorted unique hyphenated tokens. Must not be an SFT schema (`text`, `prompt_completion`, `instruction_output`, `messages`). |
| `loss_policy_id` | Hyphenated token that is not an SFT loss policy |
| `evidence_kinds` | Non-empty sorted unique subset of `mapped_value`, `declared-deterministic-derivation`. Must include `mapped_value`. |
| `missing_invalid_policy` | `refuse` |
| `leakage_grouping_keys` | Non-empty sorted unique subset of `source`, `shared-prompt`, `conversation`, `annotator`, `entity`. Must include `source`. Item 17.3 executes these keys as union-find tokens. Extra-key values are caller-supplied exact strings. Missing or empty values fail closed. Default SFT split does not use extra keys and keeps `transitive-leakage-prefix-v1`. |
| `review_hook_ids` | Sorted unique subset of `label-conflict`, `preference-inconsistency`, `tool-trace-incomplete`, `stepwise-gap`. Empty is allowed. |
| `quality_hook_ids` | Sorted unique subset of `missing-label`, `singleton-label-set`, `unpaired-without-policy`, `ranking-tie`, `tool-role-gap`. Empty is allowed. |
| `generation_allowed` | `false`. True waits for the 17.9 generator boundary. |
| `profile_eligibility` | Empty. Trainer-profile mappings wait for an independently admitted adapter. |
| `admission_id` | `derive_id("afa", …)` over the payload excluding `admission_id` |

Unknown fields fail closed. Missing or unknown contract versions fail closed
and name the requested version and the supported version
`1` (`veriformis.advanced-family-admission/v1`).

## Limitations

- `no-execute`
- `no-taxonomy-promotion`
- `no-invented-supervision`
- `no-sft-schema-overload`
- `no-generation`
- `no-profile-mapping`
- `no-extension-protocol-admission`
- `no-mac-family-ui`

## Non-goals

Invented labels, ranks, tools, or steps. A deterministic `summary` objective.
Widening two-turn `messages`. Constrained CSV nested rows. Trainer-profile
mappings. Multimodal training. A pre-tokenized generic family. A compile-path
generator. Public plugin APIs. Mac family UI. Phase 18 workbench rebuilds.
