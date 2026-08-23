# Phase 8 Execution Plan

**Status:** In progress

**Last updated:** 2026-08-23

**Authority:** [Independent Product Roadmap](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md) Phase 8; [program.json](../program.json); [ADR-0012](../../../../docs/adr/0012-consumer-profile-as-optional-adapter.md).

**Predecessor:** Phase 7 closeout merged as PR #80 at
`b7bb7f0c2046fba87fd7c9da12f7d2ccb5c2c88f` after all 14 GitHub checks passed.
Active-doc continuity merged as PR #81 at
`64a7799c27d1a489f01d77d8ba399910c95c0712`. Clean local `main` equals
`origin/main` there.

Each numbered roadmap work item is one sequential pull request on branch
`phase8/0N-<slug>` titled `Phase 8.N: <imperative>`. A pull request must pass
its focused and required repository gates, pass every GitHub check, merge, and
leave clean local `main` equal to `origin/main` before the next item begins.

The plan below is the roadmap's seven work items, reordered so isolation and
admission land before emission. Closeout is folded into 8.7, matching Phase 6
and Phase 7.

## Goal

Prove two versioned trainer profiles (TRL and MLX-LM) as optional adapters
over a verified finished bundle, with isolated extras, official-doc pins,
conformance through the real loaders, and discovery that states exactly which
goals and rows are accepted, transformed, or rejected.

## Architecture

`ExportService` remains the only export composition boundary.
`PipelineService`, CLI, MCP, and the Mac bridge are adapters. Generic
`split-jsonl-directory`, `json`, and `constrained-csv` stay
`consumer_profile: null`. A named profile is a later catalog implementation
with its own selector `(container_id, container_version, consumer_id,
consumer_profile_version)`. Core pytest continues to exclude optional trainer
integrations.

## Standing constraints

- Core install, compile, seal, generic export, and core pytest never import
  TRL, MLX-LM, or another trainer library.
- Optional extras and optional CI jobs, same isolation as Aptus
  (`continue-on-error`, separate evidence).
- Incompatible rows fail in Veriformis before the consumer sees them.
- A profile may refuse a row schema; it must not silently change the
  loss-policy ID.
- No preference, tool-call, multimodal, ranking, or “works with Hugging Face”
  claim.
- Sidecars are config/launch instructions only. The exporter does not train.
- The same canonical bundle exports to both profiles with identical membership
  and targets.
- Python / CLI / MCP / Mac bridge agree on profile identity and produced files.
- Aptus remains the existing optional handoff until Phase 10.
- Parquet / Arrow / Hugging Face Dataset remain Phase 9.

## Key decisions (lock at 8.1)

| Decision | Recommendation | Why |
| --- | --- | --- |
| Adapter, not compiler | A profile adapts a verified bundle. It does not curate, resplit, or change membership. ADR-0012. | ADR-0004 already forbids exporters from becoming a second pipeline. |
| Isolation | Trainer libraries live in optional extras and optional CI. Core extra remains `test` until 8.2 pins packages. | Standalone release gates (ADR-0002). |
| Planned refusal | `trl` refuses naming item 8.3; `mlx-lm` refuses naming item 8.4; candidates name Phase 10. | Same honesty pattern as Phase 7.1 planned modes. |
| Closeout | Folded into 8.7 with discovery truthfulness. | Phase 6 and 7 precedent. |

## Likely files (created across the phase)

- Create: `dev/active/independent-product/phase-08-consumer-profiles/` packet (8.1)
- Create: `docs/adr/0012-consumer-profile-as-optional-adapter.md` (8.1)
- Create later: profile contracts, extras, renderers, harnesses, sidecars, optional CI jobs
- Modify: `src/veriformis/exports/service.py` planned-profile refusal (8.1)
- Create in 8.2: `src/veriformis/profiles/`, empty extras, CLI `profile-admissions`, MCP `profile_admissions`
- Do not modify in 8.1: production generic renderers, taxonomy implemented lists, Aptus handoff defaults

---

## Checklist

### 8.1 Open the consumer-profile packet

**Branch:** `phase8/01-profile-packet`
**Title:** `Phase 8.1: Open the consumer-profile packet`

- [x] Confirm the predecessor gate: Phase 7 completed, docs continuity on `main`, `HEAD == origin/main`.
- [x] Create the standard Phase 8 packet. Mark Phase 8 `in_progress` in `program.json`. Reconcile active tracking documents. Cite the Phase 7 closeout merge.
- [x] Publish ADR-0012.
- [x] Keep `trl` and `mlx-lm` planned. Refuse those `consumer_id` values with the named later item. Refuse candidates as Phase 10.
- [x] Prove generic export discovery still has a null consumer profile.
- [x] Prove `pyproject.toml` optional extras remain only `test`.
- [x] Record focused, tracking, lint, structured-JSON, and diff evidence. Do not claim TRL or MLX-LM support.

### 8.2 Pin TRL and MLX-LM admission records

**Branch:** `phase8/02-admission-pins`
**Title:** `Phase 8.2: Pin TRL and MLX-LM admission records`

- [x] Complete section-5 gate records: official docs, review dates, pinned version ranges, loss/refusal model, license/deprecation.
- [x] Declare optional extras without emitting trainer files.

### 8.3 Emit the TRL profile

**Branch:** `phase8/03-trl-profile`
**Title:** `Phase 8.3: Emit the TRL profile`

- [x] TRL profile for currently proven row schemas only. Dataset/DatasetDict-compatible local data plus profile metadata. Refuse preference/stepwise.

### 8.4 Emit the MLX-LM profile

**Branch:** `phase8/04-mlx-lm-profile`
**Title:** `Phase 8.4: Emit the MLX-LM profile`

- [x] Required `train.jsonl`, optional `valid.jsonl`, supported shapes, explicit masking/completion. `test.jsonl` is not mapped from Veriformis evaluation.

### 8.5 Load artifacts through the real consumers

**Branch:** `phase8/05-conformance-harness`
**Title:** `Phase 8.5: Load artifacts through the real consumers`

- [x] Isolated harnesses using the pinned loader or its authoritative schema. Golden load succeeds; incompatibles never reach the loader. Optional CI jobs.

### 8.6 Ship config sidecars

**Branch:** `phase8/06-profile-sidecars`
**Title:** `Phase 8.6: Ship config sidecars`

- [x] Profile-specific config/launch fragments beside the export. No training process.

### 8.7 Tell the truth in discovery and close Phase 8

**Branch:** `phase8/07-discovery-closeout`
**Title:** `Phase 8.7: Tell the truth in discovery and close Phase 8`

- [ ] Discovery states exactly which goals/rows are accepted, transformed, or rejected.
- [ ] Partition, empty-eval, Unicode, nested messages, system roles, multi-assistant, and schema-refusal tests.
- [ ] Promote `trl` and `mlx-lm` to implemented. Closeout. Do not start Phase 9, 10, or 13.

## Usability criteria

| ID | Criterion |
| --- | --- |
| U1 | Discovery names accepted, transformed, and rejected goals/rows without implying unimplemented profiles. |
| U2 | Selecting a planned profile fails in Veriformis with the later item, before any trainer library is imported. |
| U3 | A profile never changes membership or targets relative to the source bundle. |
| U4 | Incompatible rows never reach the consumer loader. |
| U5 | Python, CLI, and MCP agree on profile identity. |
| U6 | Sidecars do not launch training. |
| U7 | One bundle exports to both admitted profiles with identical membership and targets. |

## Exit gate

Each profile's golden dataset loads in its pinned consumer; incompatibles fail
in Veriformis first; one bundle exports to both without changing membership or
targets. Core tests still pass without trainer extras.

**Result:** Pending. See [closeout.md](closeout.md).
