# Phase 3 Progress Log

This file is append-only by dated entry. Corrections are recorded in later
entries rather than deleting the earlier account.

## 2026-08-20 — Phase 3 started

**Status:** In progress

**Predecessor:** Phase 2 completed on 2026-08-11. Pre-Phase-3 defect closure
completed and merged on `main` as PR #30 (`f8dd1bf`). Phase 3 remained
`planned` with `packet: null` until this packet.

**Starting facts reviewed:**

- `TrainingObjective` is already distinct from product row schema.
- Implemented objective kinds are the five deterministic v1 kinds in
  `DETERMINISTIC_V1_OBJECTIVE_KINDS`.
- Implemented row schemas are `text`, `prompt_completion`,
  `instruction_output`, and `messages`.
- `full_text` requires `text`; every other objective forbids `text`.
- Physical publication is the canonical `minimal-v1` directory plus the
  Phase 2 deterministic `.vfbundle.zip` transport.
- Aptus handoff v1 is an optional consumer profile and already records
  supervised-boundary notes per row schema.
- ADR 0003 accepted the four-axis model; this phase persists the vocabulary
  and compatibility matrix.

**Next action:** Define the versioned taxonomy contract and a machine registry
that reuses those identifiers, then pin invalid combinations.

## 2026-08-20 — Taxonomy contract and registry opened

**Status:** In progress

Published `docs/contracts/taxonomy-v1.md` and `src/veriformis/taxonomy.py`.
The registry reuses the five deterministic objectives, four product row
schemas, `minimal-v1`, the Phase 2 transport container, and the optional Aptus
profile. Implemented families are only source-grounded language modeling and
source-grounded supervised fine-tuning. Planned and explicitly unsupported
families are named and excluded from implemented discovery. Loss policies
match the existing Aptus supervised-boundary strings. Invalid objective/row
pairs and UI aliases fail closed in the registry; surface wiring and the
public “format” inventory remain open.

**Next action:** Wire `assert_compile_combination` through `PipelineService`
and the remaining surfaces, then expose one discovery listing.
