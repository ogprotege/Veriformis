# ADR-0018 — No Compile-Path Generator in Phase 17

**Status:** Accepted

**Date:** 2026-08-28

**Decider:** Phase 17.9 threat model. Operator instruction to finish
Phase 17 sequential items. Decision A is the plan's likely boundary and
the only option that 17.9 itself may record without adding a
`GeneratorPass`.

## Context and evidence

Phase 17 admitted four user-provided families on the dataset-row path:
`explicit-label-classification`, `preference-and-ranking`,
`tool-call-conversations`, and `stepwise-supervision`. Every supervised
field binds `mapped_value`. `generation_allowed` stays `false` on every
admission pin. There is no `GeneratorPass` under `src/veriformis`. Core
compile makes no network call. Default `review_policy` stays `none`.
Optional extras (`trl`, `mlx-lm`, `columnar`, `axolotl`,
`llama-factory`, `unsloth`, `ocr`) stay empty. ADR-0017 Decision A
still forbids untrusted loaders and dataset-project code execution.

A governed generator is optional and forbidden unless this ADR approves
a boundary. Hard non-goals already forbid treating synthetic data as
source truth, making generated data a prerequisite for the standalone
product, and inventing supervision. Group 8 `GeneratorPass` remains
owner-gated, not v1.

This item is policy. It adds no generator.

## Threat model

| Surface | Threat | v1 control |
| --- | --- | --- |
| Offline default vs explicit network opt-in | A compile stage phones home, pulls weights, or silently enables network | Offline default. Core compile makes no network call. There is no generation extra and no hosted-model client. An explicit network opt-in cannot exist until a later ADR supersedes this one. |
| Model identity, revision, prompt/system digests, parameters | Generated text is unlabeled and unreproducible | No generator. A future adapter MUST record model identity, immutable revision, prompt and system-prompt digests, and parameters before any candidate is admitted. |
| Source evidence supplied to the model | The model invents facts not present in supplied source evidence | No generator. User-provided families bind `mapped_value`. A future adapter MUST supply only declared source evidence and MUST NOT invent facts. |
| Output identity, reproducibility limit, cost/network disclosure | Generated rows look like source truth or hide cost and network use | No generator. A future adapter MUST give candidates a distinct identity, disclose reproducibility limits, and disclose cost and network use. Generated data MUST NOT be treated as source truth. |
| Required review policy | Generated candidates seal under default `review_policy` `none` | Default `review_policy` stays `none` on user-provided recipes. Generated candidates MUST NOT seal under that default. A future adapter MUST require review. |
| Isolation from deterministic v1 release claims | Generation is counted as deterministic compile | Deterministic v1 remains network-free and LLM-free. Generation stays outside those claims. |
| Dataset-project code execution | A generator `import`s project Python, `eval`s a prompt template from the workspace, or loads an untrusted extra | Forbidden. ADR-0017 Decision A stands. Dataset projects remain data. |

## Decision

1. **Decision A.** Phase 17 does not install a compile-path generator.
   There is no `GeneratorPass`, no hosted-model extra, no network client
   on the compile path, and no default-on generation.
2. `generation_allowed` remains `false` on
   `veriformis.advanced-family-admission/v1`. True continues to fail
   closed.
3. User-provided admitted families remain the Phase 17 executable
   surface. Generated candidates are not source truth.
4. Deterministic v1 release claims stay isolated from generation.
5. A later phase MAY propose Decision B (narrow offline adapter: named
   local runtime, no network, required review, outside deterministic
   release claims) only with a new ADR that supersedes this one.
   Decision C (defer remaining Phase 17) is not selected; the admission
   contract and user-provided families are the required work and are
   already implemented.

## Consequences

- Item 17.10 completes adversarial closeout without a `GeneratorPass`.
- 17.10 skips generation with a dated record, the same honesty as
  Phase 15.5–15.8 and the 16.10 public-plugin skip.
- Phase 18 Mac UI MUST NOT invent a generator surface from this ADR.
- ADR-0017 Decision A still holds: no untrusted loader and no
  dataset-project code execution.

## Alternatives considered

- **B — Narrow offline adapter now:** rejected for Phase 17. A named
  local runtime, required review on generated candidates, output
  identity, and isolation from deterministic claims are new product
  machinery. 17.9 is not licensed to add them.
- **C — Defer the remaining phase:** rejected. The admission contract
  and user-provided families are the required work and are already
  implemented.
- **Default-on generation with an operator confirm:** rejected.
  Confirmation does not make generated text source truth, and v1
  compile must remain network-free.
- **Hosted-model extra behind an empty optional extra:** rejected. An
  extra name is a support claim. Empty extras already isolate optional
  trainers and OCR; generation is not licensed to join them.

## Verification

Item 17.9 publishes this ADR and adds no generator. Tests continue to
prove `GeneratorPass` is absent, `generation_allowed` cannot be true,
CLI/MCP/PipelineService expose no generate operation, packaging has no
hosted-model extra, and core compile still makes no network call.
Item 17.10 skips generation with a record.

## Review triggers

Any compile-path LLM call; hosted-model extra; `generation_allowed`
true; default-on generation; treating synthetic or generated data as
source truth; Mac generator UI; promoting `governed-generated-candidates`
to implemented.
