# Consumer Profile Admission v1

**Contract ID:** `veriformis.consumer-profile-admission`

**Contract version:** `1`

**Discovery schema:** `veriformis.profile-admission-discovery/v1`

**Status:** Packaged section-5 pins for implemented `trl` and `mlx-lm`.
Discovery names accepted, transformed, and rejected goals and rows.

**Last reviewed:** 2026-08-23

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
| State | `implemented` |
| Mapping kind | `identity`, `assemble-prompt` |
| Admitted row schemas | `instruction_output`, `messages`, `prompt_completion`, `text` |
| Round-trip | `false` |

`instruction_output` maps by assembling `prompt` from `instruction` plus a
newline and `input` when `input` is nonempty; `completion` is `output`. The
other three schemas map by identity onto the destination keys named in the
pin.

## Isolation

Optional extras `trl` and `mlx-lm` exist as empty lists. Version ranges live
in the packaged catalog. Core install, compile, seal, generic export, and
core pytest must not import TRL, MLX-LM, torch, or mlx. Item 8.5 optional
CI may install those packages into isolated harnesses.

## Non-goals

Parquet/Arrow (Phase 9) and Aptus as a common profile (Phase 10).

## Discovery

Python `PipelineService.discover_profile_admissions()`, CLI
`veriformis profile-admissions`, and MCP `profile_admissions` emit the same
canonical JSON as `src/veriformis/profiles/admission-v1.json`. Each record
names `accepted_goals`, `transformed_row_schemas`, `rejected_goals`, and
`refused_dataset_types`.
