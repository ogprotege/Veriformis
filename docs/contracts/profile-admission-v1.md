# Consumer Profile Admission v1

**Contract ID:** `veriformis.consumer-profile-admission`

**Contract version:** `1`

**Discovery schema:** `veriformis.profile-admission-discovery/v1`

**Status:** Packaged section-5 pins for implemented `trl` and `mlx-lm`,
plus Phase 10 candidate pins. Discovery names accepted, transformed, and
rejected goals and rows. Candidate records are not executable.

**Last reviewed:** 2026-08-24 (independent-product Phase 10.2)

## Purpose

Pin official-documentation admission records for the two Phase 8 consumer
profiles. A pin records the reviewed docs URL, review date, license, extra
name, version range, admitted and transformed row schemas, accepted and
rejected goals, refused dataset types, partition mapping, row mappings,
loss notes, and deprecation policy. Both records are `implemented`.

Generic export selectors remain `consumer_id` null. Selecting `trl` or
`mlx-lm` emits the matching adapter. Candidates remain Phase 10.

## Closed vocabularies

| Vocabulary | v1 values |
| --- | --- |
| Profiles | `trl`, `mlx-lm` in that order |
| Candidate pins | `axolotl`, `llama-factory`, `unsloth`, `aptus` in that order |
| State | `implemented` for the two Phase 8 records; `admitted`, `experimental`, or `deferred` for candidate records |
| Mapping kind | `identity`, `assemble-prompt` |
| Admitted row schemas | `instruction_output`, `messages`, `prompt_completion`, `text` |
| Round-trip | `false` |

`instruction_output` maps by assembling `prompt` from `instruction` plus a
newline and `input` when `input` is nonempty; `completion` is `output`. The
other three schemas map by identity onto the destination keys named in the
pin.

## Isolation

Optional extras `trl`, `mlx-lm`, `axolotl`, `llama-factory`, and `unsloth`
exist as empty lists. Version ranges live in the packaged catalogs. Core
install, compile, seal, generic export, implemented adapters, and core
pytest must not import those trainers.

## Non-goals

Emitting Axolotl, LLaMA-Factory, or Unsloth files from item 10.2. Moving
Aptus onto `ExportService` (item 10.6). A hosted OpenAI profile.

## Discovery

Python `PipelineService.discover_profile_admissions()`, CLI
`veriformis profile-admissions`, and MCP `profile_admissions` emit the same
canonical JSON as `src/veriformis/profiles/admission-v1.json`. Each record
names `accepted_goals`, `transformed_row_schemas`, `rejected_goals`, and
`refused_dataset_types`. Both records remain `implemented`.

Python `PipelineService.discover_candidate_profile_admissions()`, CLI
`veriformis candidate-profile-admissions`, and MCP
`candidate_profile_admissions` emit the same canonical JSON as
`src/veriformis/profiles/candidate-admission-v1.json`
(`veriformis.candidate-profile-admission-discovery/v1`). `axolotl` and
`llama-factory` are `admitted` and `emit_eligible` for later items
10.3–10.5 after operator approval. `unsloth` is `experimental` and not
executable. `aptus` is `deferred` to item 10.6 and is not a
`consumer_id`. Selecting a candidate `consumer_id` still refuses as
Phase 10.
