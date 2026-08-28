# Phase 17 Execution Plan

**Status:** In progress

**Last updated:** 2026-08-28

**Authority:** [Independent Product Roadmap](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md) Phase 17; [program.json](../program.json); [project tracking policy](../../../../docs/governance/project-tracking.md); operator plan `/Users/biscuit/Desktop/Phase17-Plan.txt`.

**Predecessor:** Phase 16 closeout merged as PR #149 at
`a1fbf04d58d73692cc4237b7d741c5da27022581`. Clean local `main` equaled
`origin/main` there when this packet opened.

Each numbered item is one sequential pull request. Every pull request must pass
focused tests, project tracking, Ruff, the lock check, `git diff --check`, the
core test suite, and every GitHub check. It then merges and leaves clean local
`main` equal to `origin/main` before the next item begins.

Phase 17.9 is an operator gate. No generator may begin before its ADR is
merged and the operator selects the generation boundary. Phase 18 does not
start from this packet.

## Goal

Admit advanced semantic families one at a time from user-provided evidence.
Classification and preference pairs are required. Tool-call, stepwise, unpaired
preference, trainer-profile mappings, and generation are licensed only by later
items. Deterministic compile stays network-free. Existing SFT goldens stay
byte-identical.

## Architecture

`PipelineService` owns family policy. CLI and MCP are adapters. Dataset-row
mapping with `mapped_value` is the default admission path. New families get new
row schemas and loss policies. Taxonomy remains the seven-axis capability-state
registry rather than the executable registry. Family admission is the 17.2
contract plus a taxonomy pin in the executing PR. The extension protocol is not
the admission path. Constrained CSV stays on the three flat SFT schemas.

## Locks

| ID | Lock |
| --- | --- |
| L1 | Execute sequential green PRs. Item 17.1 opens the packet; 17.10 closes it. |
| L2 | Item 17.1 adds honesty records and isolation tests only. |
| L3 | Admit each semantic family separately. A pin is not an execute. |
| L4 | User-provided evidence first. Dataset-row mapping is the default path. |
| L5 | Every supervised field binds `mapped_value` or a named deterministic derivation. |
| L6 | New families get new row schemas and loss policies. Do not overload the four SFT schemas. |
| L7 | Existing SFT goldens, sealed-bundle identities, and Phase 16 extension goldens stay byte-identical. |
| L8 | Constrained CSV stays the three flat SFT schemas. Nested or pair families use split JSONL or canonical JSON. |
| L9 | Generic exporters and existing trainer profiles refuse a new family until that family is admitted and the adapter is pinned. |
| L10 | Quality stays preview-only. Default `review_policy` stays `none`. No heuristic blocks seal. |
| L11 | Taxonomy is not the executable registry. No eighth axis. `planned → implemented` happens in the admitting PR. |
| L12 | Family admission is not an extension-protocol event. No family kind is added to the protocol. ADR-0017 Decision A stands. |
| L13 | Generation is off by default and outside deterministic release claims. Stop after 17.9 for operator review. |
| L14 | Multimodal stays `explicitly_unsupported`. Pre-tokenized stays planned. |
| L15 | `PipelineService` owns policy. CLI and MCP remain adapters. No Mac UI. Do not start Phase 18 from this packet. |

## Checklist

### 17.1 Open the advanced-dataset-families packet

**Branch:** `phase17/01-family-packet`

- [x] Confirm Phase 16 complete and clean `main` at PR #149.
- [x] Create the standard packet and move Phase 17 to `in_progress`.
- [x] Record L1 through L15 and reconcile active tracking documents.
- [x] Add isolation tests for the pre-family architecture.
- [x] Pass all local and GitHub gates, merge, and synchronize clean `main`.

No family contract, row schema, objective, loss policy, constructor, mapping
template, goal, CLI family command, or profile mapping is permitted in this
item.

### 17.2 Define the advanced-family admission contract

**Branch:** `phase17/02-family-admission-contract`

- [x] Add strict `veriformis.advanced-family-admission/v1` models and a
      contract document.
- [x] Name closed family vocabulary, row schemas, loss, evidence, leakage
      keys, review/quality hooks, generation flag, profile eligibility, and
      lifecycle.
- [x] Refuse unknown families, unknown fields, and missing versions. Add no
      execute and no taxonomy promotion.
- [x] Pass all local and GitHub gates, merge, and synchronize clean `main`.

### 17.3 Add leakage grouping keys for advanced families

**Branch:** `phase17/03-advanced-leakage-grouping`

- [x] Name grouping keys `source`, `shared-prompt`, `conversation`,
      `annotator`, and `entity`.
- [x] Keep the default SFT split `transitive-leakage-prefix-v1`.
- [x] Prove shared-prompt and annotator grouping without changing SFT goldens.
- [x] Pass all local and GitHub gates, merge, and synchronize clean `main`.

### 17.4 Add review and quality hooks for advanced families

**Branch:** `phase17/04-advanced-review-quality`

- [x] Add opt-in review queue kinds for label, preference, tool-trace, and
      stepwise facts.
- [x] Add previewable quality detectors. Keep `admitted_to_block` false.
- [x] Keep default `review_policy` `none`. Do not execute a family.
- [x] Pass all local and GitHub gates, merge, and synchronize clean `main`.

### 17.5 Admit explicit-label-classification

**Branch:** `phase17/05-admit-classification`

- [x] Promote `explicit-label-classification` with a new objective, row
      schema, loss policy, mapping path, and goal/preset entries.
- [x] Bind user-provided labels with `mapped_value`. Refuse invented labels.
- [x] Seal through split JSONL and canonical JSON. Existing profiles refuse
      the new schema.
- [x] Pass all local and GitHub gates, merge, and synchronize clean `main`.

### 17.6 Admit preference-and-ranking

**Branch:** `phase17/06-admit-preference`

- [x] Promote `preference-and-ranking` with a pair schema and pair
      supervision reading.
- [x] Map chosen and rejected with `mapped_value`. Rankings require a
      user-provided order.
- [x] Skip unpaired feedback with a record if the pair contract does not
      cover it. Existing profiles keep refusing preference.

### 17.7 Admit tool-call-conversations

**Branch:** `phase17/07-admit-tool-calls`

- [ ] Promote `tool-call-conversations` with a new conversation schema.
- [ ] Keep two-turn `messages` exactly two turns.
- [ ] Skip with a record if no retained license-safe fixture can be named.

### 17.8 Admit stepwise-supervision

**Branch:** `phase17/08-admit-stepwise`

- [ ] Promote `stepwise-supervision` with a stepwise row schema.
- [ ] Require user-provided steps. Do not invent chain-of-thought.
- [ ] Skip with a record if no retained stepwise fixture can be named.

### 17.9 Threat-model governed generation

**Branch:** `phase17/09-generator-boundary`

- [ ] Add ADR-0018 covering offline default, model identity, supplied
      evidence, output identity, required review, and isolation from
      deterministic v1 claims.
- [ ] Add no `GeneratorPass`. Stop for operator review.

### 17.10 Add adversarial family tests and close Phase 17

**Branch:** `phase17/10-adversarial-closeout`

- [ ] Refuse unknown families, missing labels/pairs/traces, shared-prompt
      leakage, two-turn widening, nested CSV, profile mapping, declaration
      tamper, and invented supervision.
- [ ] Reprove small-corpus SFT goldens and Phase 16 kit goldens.
- [ ] Skip generation, multimodal, pre-tokenized generic families, and
      unmapped profiles with records unless earlier items licensed them.
      Close Phase 17. Do not start Phase 18 from this packet.

## Skip rules

| Item | Skip only when |
| --- | --- |
| 17.1–17.6 pair schema, 17.10 | Do not skip. |
| 17.6 unpaired schema | Pair leakage/evidence does not cover unpaired. |
| 17.7 tool-call, 17.8 stepwise | No retained license-safe fixture can be named. |
| Generator in 17.9/17.10 | 17.9 does not approve it (expected Decision A). |
| Trainer-profile mappings | That family has not passed core acceptance. |
| Multimodal, pre-tokenized generic family | Forbidden / out of scope. Record at closeout. |
| Mac / Hub / public plugins | Phases 18–19. ADR-0017 stands. |

## Exit gate

The admission contract exists. Classification and preference pairs compile
from user-provided evidence through curate, split, format, validate, seal, and
verify with identical goldens on replay. Unsupported advanced forms fail
closed. Deterministic compile remains network-free. Existing SFT goldens stay
unchanged. A generator, multimodal family, pre-tokenized generic family, Mac
UI, or Phase 18 workbench rebuild exists only if a numbered item licensed it.
