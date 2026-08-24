# Phase 10 Execution Plan

**Status:** Complete

**Last updated:** 2026-08-24

**Authority:** [Independent Product Roadmap](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md) Phase 10; [program.json](../program.json); [ADR-0014](../../../../docs/adr/0014-independently-admitted-consumer-profiles.md).

**Predecessor:** Phase 9 closeout merged as PR #96 at
`abdcce6474aadd33fcf38a5360b63a4f8d293a5c` after all 18 GitHub checks
passed. Clean local `main` equals `origin/main` there.

Each numbered work item is one sequential pull request on branch
`phase10/0N-<slug>` titled `Phase 10.N: <imperative>`. A pull request must
pass its focused and required repository gates, pass every GitHub check,
merge, and leave clean local `main` equal to `origin/main` before the next
item begins.

Isolation and admission land before emission. Closeout is folded into 10.8,
matching Phases 6–9. Items 10.3–10.5 emit only profiles whose 10.2 pins
pass. The operator reviews after 10.2 before 10.3 begins.

## Goal

Expand named trainer adapters under section-5 evidence gates without
pulling trainer libraries into core, without coupling profiles to each
other, and without advertising a candidate that has not been admitted.

## Architecture

`ExportService` remains the only export composition boundary.
`PipelineService`, CLI, MCP, and the Mac bridge are adapters. Generic
containers stay `consumer_profile: null`. A named profile is a later
catalog implementation with selector `(container_id, container_version,
consumer_id, consumer_profile_version)`. Core pytest continues to exclude
optional trainer integrations.

## Standing constraints

- Core install, compile, seal, generic export, TRL/MLX-LM adapters, and
  core pytest never import Axolotl, LLaMA-Factory, Unsloth, or another
  new trainer library.
- Optional extras and optional CI jobs, same isolation as Aptus and
  Phase 8/9 extras (`continue-on-error`, separate evidence).
- Incompatible rows fail in Veriformis before the consumer sees them.
- A profile may refuse a row schema; it must not silently change the
  loss-policy ID.
- No preference, tool-call, multimodal, ranking, or hosted OpenAI claim.
- Sidecars are config/launch instructions only. The exporter does not train.
- Aptus remains the sibling handoff until item 10.6.
- Python / CLI / MCP / Mac bridge agree on profile identity.
- Do not start Phase 11 or 13 from this packet.

## Key decisions (lock at 10.1)

| Decision | Recommendation | Why |
| --- | --- | --- |
| Independent admission | Each candidate is admitted on its own pin. Failed pins do not emit. ADR-0014. | Roadmap section 5; Phase 8 proved the adapter pattern. |
| Isolation | New extras `axolotl`, `llama-factory`, and `unsloth` are empty lists. Version ranges live in later pins. | Standalone release gates (ADR-0002). |
| Candidate refusal | Those three `consumer_id` values refuse as Phase 10 candidates. | Same honesty pattern as Phase 8.1. |
| Aptus | Sibling handoff until 10.6. | ADR-0012 already deferred the move. |
| Closeout | Folded into 10.8 with discovery and deprecation. | Phase 6–9 precedent. |

## Likely files (created across the phase)

- Create: `dev/active/independent-product/phase-10-profile-expansion/` packet (10.1)
- Create: `docs/adr/0014-independently-admitted-consumer-profiles.md` (10.1)
- Modify: `pyproject.toml` empty extras (10.1)
- Create later: admission pins, renderers, Aptus profile migration, harnesses
- Do not modify in 10.1: production generic renderers, TRL/MLX-LM adapters, taxonomy implemented lists, Aptus defaults

---

## Checklist

### 10.1 Open the profile-expansion packet

**Branch:** `phase10/01-profile-expansion-packet`
**Title:** `Phase 10.1: Open the profile-expansion packet`

- [x] Confirm the predecessor gate: Phase 9 completed, `HEAD == origin/main`.
- [x] Create the standard Phase 10 packet. Mark Phase 10 `in_progress` in `program.json`. Reconcile active tracking documents. Cite the Phase 9 closeout merge.
- [x] Publish ADR-0014.
- [x] Keep `axolotl`, `llama-factory`, and `unsloth` as candidates. Refuse those `consumer_id` values as Phase 10.
- [x] Prove generic JSONL, JSON, CSV, Parquet, Arrow, Hugging Face Dataset, TRL, and MLX-LM discovery still executable.
- [x] Declare empty extras `axolotl`, `llama-factory`, and `unsloth` so `uv lock` does not pull those trainers.
- [x] Record focused, tracking, lint, lock, and diff evidence. Do not claim Axolotl, LLaMA-Factory, Unsloth, or Aptus-as-profile support.

### 10.2 Pin admission records for every candidate

**Branch:** `phase10/02-admission-pins`
**Title:** `Phase 10.2: Pin admission records for every candidate`

- [x] Section-5 gate records for Axolotl, LLaMA-Factory, Unsloth, and Aptus-as-profile: official docs, review dates, pinned version ranges, loss/refusal model, license/deprecation.
- [x] If a candidate has no stable machine-checkable contract, the pin says experimental / not executable.
- [x] Declare extras remain empty. Do not emit trainer files.

### 10.3 Emit the first admitted profile

**Branch:** `phase10/03-<first-admitted>`
**Title:** `Phase 10.3: Emit the first admitted profile`

- [x] First profile whose 10.2 pin passes. Operator approval required before this item begins. Combined 10.3–10.8 PR emits Axolotl.

### 10.4 Emit the second admitted profile

**Branch:** `phase10/04-<second-admitted>`
**Title:** `Phase 10.4: Emit the second admitted profile`

- [x] Independent of 10.3. Same bundle exports to both with identical membership and targets. Combined PR emits LLaMA-Factory.

### 10.5 Emit the third admitted profile

**Branch:** `phase10/05-<third-admitted>`
**Title:** `Phase 10.5: Emit the third admitted profile`

- [x] Same pattern. Skip with an explicit non-admission record if 10.2 did not admit a third profile. Unsloth remains experimental.

### 10.6 Move Aptus under the common profile lifecycle

**Branch:** `phase10/06-aptus-as-profile`
**Title:** `Phase 10.6: Move Aptus under the common profile lifecycle`

- [x] Keep external-digest and assignment checks. Remove special product authority. Default seal still does not write the descriptor.

### 10.7 Load artifacts through the real consumers

**Branch:** `phase10/07-conformance-harness`
**Title:** `Phase 10.7: Load artifacts through the real consumers`

- [x] Isolated harnesses and optional CI. Golden load succeeds. Incompatibles never reach the loader.

### 10.8 Tell the truth, pin deprecation, and close Phase 10

**Branch:** `phase10/08-discovery-deprecation-closeout`
**Title:** `Phase 10.8: Tell the truth, pin deprecation, and close Phase 10`

- [x] Sidecars do not launch training. Discovery names accepted, transformed, and rejected goals and rows. Explicit deprecation policy. Promote only admitted harness-green profiles. Closeout. Do not start Phase 11 or 13.

## Usability criteria

| ID | Criterion |
| --- | --- |
| U1 | Discovery does not imply implemented Axolotl, LLaMA-Factory, Unsloth, or Aptus-as-profile export until that profile is promoted. |
| U2 | Selecting a candidate profile fails in Veriformis as Phase 10, before a trainer library is imported. |
| U3 | A profile export never changes membership or targets relative to the source bundle. |
| U4 | Preference, tools, multimodal, and ranking rows fail in Veriformis before the consumer sees them. |
| U5 | Python, CLI, and MCP agree on profile identity. |
| U6 | Core pytest passes without the new extras. |
| U7 | One bundle can export to every implemented Phase 8 and Phase 10 profile with identical membership and targets. |

## Exit gate

Each advertised profile's golden export loads in its pinned consumer or
authoritative schema path. Deliberate incompatibles fail in Veriformis first.
Core tests still pass without trainer extras. Failure or absence of any one
profile integration does not break core compile, generic export, or another
profile.

**Result:** Passed. See [closeout.md](closeout.md).
