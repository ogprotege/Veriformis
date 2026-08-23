# Consumer Profile Admission v1

**Contract ID:** `veriformis.consumer-profile-admission`

**Contract version:** `1`

**Discovery schema:** `veriformis.profile-admission-discovery/v1`

**Status:** Packaged section-5 pins for planned `trl` and `mlx-lm` only.
Discovery is executable. Emission is not. Both records remain `planned`.

**Last reviewed:** 2026-08-23

## Purpose

Pin official-documentation admission records for the two Phase 8 consumer
profiles before any trainer files are emitted. A pin records the reviewed
docs URL, review date, license, extra name, version range, admitted row
schemas, refused dataset types, partition mapping, row mappings, loss notes,
and deprecation policy. It does not make the profile executable.

Generic export selectors remain `consumer_id` null. Selecting `trl` still
refuses naming item 8.3. Selecting `mlx-lm` still refuses naming item 8.4.

## Closed vocabularies

| Vocabulary | v1 values |
| --- | --- |
| Profiles | `trl`, `mlx-lm` in that order |
| State | `planned` |
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
core pytest must not import TRL, MLX-LM, torch, or mlx. Item 8.5 installs
those packages into isolated harnesses.

## Non-goals

Trainer file emission (8.3, 8.4), loader conformance (8.5), config sidecars
(8.6), promoting records to `implemented` (8.7), Parquet/Arrow, and Aptus as
a common profile.

## Discovery

Python `PipelineService.discover_profile_admissions()`, CLI
`veriformis profile-admissions`, and MCP `profile_admissions` emit the same
canonical JSON as `src/veriformis/profiles/admission-v1.json`.
