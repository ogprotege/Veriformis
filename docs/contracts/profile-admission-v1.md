# Consumer Profile Admission v1

**Contract ID:** `veriformis.consumer-profile-admission`

**Contract version:** `1`

**Discovery schema:** `veriformis.profile-admission-discovery/v1`

**Status:** Packaged section-5 pins for implemented `trl`, `mlx-lm`,
`axolotl`, `llama-factory`, and `aptus`, plus the remaining Unsloth
candidate pin. Discovery names accepted, transformed, and rejected goals
and rows. Candidate records are not executable.

**Last reviewed:** 2026-08-24 (independent-product Phase 10.3–10.8)

## Purpose

Pin official-documentation admission records for implemented export
consumer profiles. A pin records the reviewed docs URL, review date,
license, extra name, version range, admitted and transformed row schemas,
accepted and rejected goals, refused dataset types, partition mapping,
row mappings, loss notes, and deprecation policy. Implemented records are
`implemented`.

Generic export selectors remain `consumer_id` null. Selecting an
implemented `consumer_id` emits the matching adapter. `unsloth` remains
the Phase 10 candidate and is not executable.

## Closed vocabularies

| Vocabulary | v1 values |
| --- | --- |
| Profiles | `trl`, `mlx-lm`, `axolotl`, `llama-factory`, `aptus` in that order |
| Candidate pins | `unsloth` |
| State | `implemented` for the five export records; `experimental` for the Unsloth candidate |
| Mapping kind | `identity`, `assemble-prompt`, `remap` |
| Admitted row schemas | `instruction_output`, `messages`, `prompt_completion`, `text`; Aptus omits `text` |
| Round-trip | `false` |

TRL and MLX-LM assemble `instruction_output` into `prompt`/`completion`.
Axolotl remaps `prompt_completion` onto alpaca keys. LLaMA-Factory remaps
`messages` onto sharegpt `conversations` and `prompt_completion` onto
alpaca. Aptus maps admitted schemas by identity and refuses `text`.

## Isolation

Optional extras `trl`, `mlx-lm`, `axolotl`, `llama-factory`, and `unsloth`
exist as empty lists. Version ranges live in the packaged catalogs. Core
install, compile, seal, generic export, implemented adapters, and core
pytest must not import those trainers.

## Non-goals

Emitting Unsloth files. A hosted OpenAI profile. Training launch.

## Discovery

Python `PipelineService.discover_profile_admissions()`, CLI
`veriformis profile-admissions`, and MCP `profile_admissions` emit the same
canonical JSON as `src/veriformis/profiles/admission-v1.json`. Each record
names `accepted_goals`, `transformed_row_schemas`, `rejected_goals`, and
`refused_dataset_types`. All five records remain `implemented`.

Python `PipelineService.discover_candidate_profile_admissions()`, CLI
`veriformis candidate-profile-admissions`, and MCP
`candidate_profile_admissions` emit the same canonical JSON as
`src/veriformis/profiles/candidate-admission-v1.json`
(`veriformis.candidate-profile-admission-discovery/v1`). `unsloth` is
`experimental` and not executable. Item 10.5 skipped it with this pin.
Selecting `unsloth` still refuses as Phase 10.
