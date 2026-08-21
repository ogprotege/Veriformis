# Phase 3 Execution Plan

**Status:** In progress

**Last updated:** 2026-08-21

## Checklist

### 3.1 Open the packet and pin current taxonomy facts

- [x] Create the standard Phase 3 packet after Phase 2 and pre-Phase-3 defect closure.
- [x] Mark Phase 3 `in_progress` in the program ledger and WIP table.
- [x] Record existing objective, row-schema, container, and profile constants in one registry.
- [x] Pin the already implemented objective/row compatibility rules without changing persisted IDs.
- [x] Identify public “format” uses that collapse more than one axis.

### 3.2 Define the versioned taxonomy contract

- [x] Publish `docs/contracts/taxonomy-v1.md` for training family, objective,
      semantic row, physical container, consumer profile, and loss policy.
- [x] Reuse existing construction, finished-dataset, bundle, transport, and
      Aptus identifiers where they remain compatible.
- [x] State that a later incompatible meaning change requires a versioned
      migration, not silent reinterpretation.

### 3.3 Review current names and record UI aliases

- [x] Review `full_text`, `continuation`, `section_reconstruction`,
      `before_after_transformation`, and `structured_field` against their
      actual learning semantics.
- [x] Keep persisted identifiers unchanged.
- [x] Record UI/legacy aliases (`completion`, `instruction`, `chat`) as
      non-persisted names only.

### 3.4 Define current and future-only families

- [x] Declare the conservative implemented families: source-grounded language
      modeling / continued pretraining, and source-grounded supervised
      fine-tuning.
- [x] Name future-only families without advertising them as implemented:
      preference/ranking, explicit-label classification, tool use, multimodal,
      stepwise supervision, and pre-tokenized training.
- [x] Keep Group 8 generated-candidate work owner-gated and unnamed as a
      current family.

### 3.5 Define loss and masking for every semantic row

- [x] Give each implemented row schema one exact supervised-boundary
      description.
- [x] Allow a consumer profile to further constrain a row, never to silently
      change its loss meaning.

### 3.6 Add the compatibility matrix and fail-closed checks

- [x] Encode valid objective/row/profile combinations in the registry.
- [x] Fail unknown or impossible combinations before compile on every surface.
- [x] Keep Aptus `text` refusal as an optional profile constraint, not a core
      product ban.

### 3.7 Expose one registry on every surface

- [x] Add discovery through `PipelineService`.
- [x] Add CLI discovery that names each axis separately.
- [x] Add MCP resources or tools over the same registry.
- [x] Add workbench help copy from the same registry.
- [x] Remove or rewrite public “format” language that can mean more than one
      axis.

### 3.8 Migration tests and closeout

- [ ] Add schema/version and golden round-trip tests for the taxonomy catalog.
- [ ] Prove existing default-rule workspaces and sealed bundles still load.
- [ ] Update current status, support registry, evidence index, WIP, and docs.
- [ ] Complete `closeout.md` and mark Phase 3 completed only if every exit
      gate passes.

## Exit gate

No public API or screen uses “format” where it could mean more than one axis.
Every implemented recipe and row schema has one explicit training-family and
loss interpretation. Invalid objective, row, container, or profile
combinations fail before compile. Existing persisted v1 identifiers remain
readable without reinterpretation.

## Non-goals

- Preference, ranking, classification, tool-use, multimodal, or generated-data
  implementation.
- New export containers or trainer profiles.
- Renaming the persisted `aptus-row-shape` gate without a versioned migration.
- Signing, notarization, a beta label, or a public-ready claim.
