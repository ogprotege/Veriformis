# Phase 10 Closeout

**Status:** Complete

**Last reviewed:** 2026-08-24

## Exit-gate judgment

Passed. Axolotl, LLaMA-Factory, and Aptus are implemented optional
`ExportService` adapters over a verified bundle. Unsloth remains
experimental and is not executable. Official-schema JSONL, YAML, and
`dataset_info.json` harnesses load without installing those trainers.
Incompatibles fail in Veriformis first. Sidecars do not launch
training. Core pytest still passes without trainer extras. The sibling
Aptus handoff CLI remains; default seal still does not write the
descriptor.

Items 10.3–10.8 are this closeout pull request. Do not start Phase 11
or 13 from this packet.

## Usability criteria

| ID | Judgment | Current-tree evidence |
| --- | --- | --- |
| U1 | Pass | Discovery lists Axolotl, LLaMA-Factory, and Aptus as implemented; Unsloth stays candidate |
| U2 | Pass | Selecting `unsloth` refuses as Phase 10 before a trainer library is imported |
| U3 | Pass | One text fixture exports to TRL, MLX-LM, Axolotl, and LLaMA-Factory with identical membership |
| U4 | Pass | Preference, tools, extra turns, and Aptus `text` fail in Veriformis |
| U5 | Pass | Python, CLI, and MCP share admission JSON |
| U6 | Pass | Core pytest excludes `profile_integration`; extras stay empty |
| U7 | Pass | The same bundle exports to every implemented Phase 8 and Phase 10 profile that admits its row schema |

## Delivered scope

- 10.1 opened the packet and published ADR-0014 (PR #97).
- 10.2 pinned section-5 records (PR #98).
- 10.3 emitted Axolotl JSONL plus dataset-only YAML.
- 10.4 emitted LLaMA-Factory alpaca/sharegpt plus `dataset_info.json`.
- 10.5 skipped Unsloth with the experimental candidate pin.
- 10.6 moved Aptus onto `consumer_id=aptus` identity export; sibling handoff remains.
- 10.7 added official-schema harnesses and optional CI selection.
- 10.8 named accepted/transformed/rejected goals and rows, pinned deprecation, and closed the phase.

## Remaining bounds (not Phase 10 gaps)

- Extras `axolotl`, `llama-factory`, and `unsloth` stay empty.
- Unsloth is not executable.
- The exporter does not train.
- Hosted OpenAI remains out of scope.
- Quality heuristics remain Phase 13.

## Verification summary

Local core gates for items 10.3–10.8 are recorded in `evidence.md`.
Do not start Phase 11 or 13 from this closeout.
