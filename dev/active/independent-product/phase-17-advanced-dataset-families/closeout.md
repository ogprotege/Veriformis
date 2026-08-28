# Phase 17 Closeout

**Status:** Complete

**Last reviewed:** 2026-08-28

## Exit-gate judgment

Passed. The advanced-family admission contract is implemented.
Classification, preference pairs, tool-call conversations, and stepwise
supervision compile from user-provided `mapped_value` evidence through
curate, split, format, validate, seal, and verify. Unsupported advanced
forms fail closed. Deterministic compile remains network-free. Existing
SFT goldens and Phase 16 kit goldens stay unchanged. ADR-0018 Decision A:
no compile-path generator. Generation, multimodal, pre-tokenized generic
families, and unmapped trainer profiles are skipped with records. No Mac
UI. Do not start Phase 18 from this packet.

## Usability criteria

| ID | Judgment | Evidence |
| --- | --- | --- |
| Admission contract | Pass | `veriformis.advanced-family-admission/v1`; unknown families, fields, and versions fail closed |
| Classification | Pass | User-provided labels; `mapped_value`; leakage; seal goldens |
| Preference pairs | Pass | User-provided chosen/rejected; unpaired and ranking skipped with a record |
| Tool-call | Pass | New conversation schema; two-turn `messages` stays exact |
| Stepwise | Pass | User-provided ordered steps; copied source text is never labeled reasoning |
| No generator | Pass | ADR-0018 Decision A; generation skipped with a record |
| No Phase 18 | Pass | Packet and ledger forbid starting Phase 18 |

## Delivered scope

- 17.1 packet and pre-family isolation.
- 17.2 `veriformis.advanced-family-admission/v1`.
- 17.3 leakage grouping keys.
- 17.4 opt-in review queues and preview-only quality hooks.
- 17.5 `explicit-label-classification`.
- 17.6 `preference-and-ranking` pair schema.
- 17.7 `tool-call-conversations`.
- 17.8 `stepwise-supervision`.
- 17.9 ADR-0018 Decision A.
- 17.10 adversarial refusals and closeout. Generation skipped.

## Exclusions

Compile-path generator. Multimodal training. Pre-tokenized generic family.
Trainer-profile mappings for admitted families. Unpaired preference and
ranking-order schemas. Constrained CSV nested rows. Widening two-turn
`messages`. Mac family UI (Phase 18). Public plugins (ADR-0017).

## Remaining debt

A later phase may propose Decision B (narrow offline generator adapter)
only with a new ADR that supersedes ADR-0018. Until then
`generation_allowed` stays false and generated data is not source truth.
Trainer-profile mappings wait for independently admitted adapters.

## Skip record

Generation in 17.9/17.10 is skipped with a record because ADR-0018
selected Decision A. Multimodal stays `explicitly_unsupported`.
Pre-tokenized training stays planned. Trainer-profile mappings are
skipped because no independently admitted adapter was pinned. Unpaired
preference and ranking-order schemas were skipped in 17.6. Same honesty
as Phase 15.5–15.8 and the 16.10 public-plugin skip.
