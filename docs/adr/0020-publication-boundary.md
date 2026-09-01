# ADR-0020 — Optional Publication Boundary

**Status:** Accepted

**Date:** 2026-08-31

**Decider:** Phase 19.7 publication pin. Operator instruction: Decision A
(pin only; no Hub execute).

## Context and evidence

Phase 19 supports reproducible pipelines, CI, and opt-in sharing without
turning the local compiler into a required cloud service. Hugging Face
Dataset is a local container, not Hub upload. `veriformis run`, compile,
and export execute have no network publication. Credentials must never
appear in workspaces, bundles, specs, lockfiles, logs, or receipts.

Roadmap deliverables allow “only approved opt-in publication adapters.”
Hosted training stays out of scope. ADR-0017 Decision A and ADR-0018
Decision A stand.

## Threat model

| Surface | Threat | v1 control |
| --- | --- | --- |
| Silent upload | Compile, `run`, export execute, MCP, or Mac uploads | Default local path has no upload. `execute_allowed` is false. |
| Pin mistaken for execute | Loading `publication-adapter/v1` calls Hub | Loading is not upload. No network client in the pin module. |
| Credential persistence | HF_TOKEN or `.netrc` copied into artifacts | `credential_source` is `none`. Specs and locks refuse credential-shaped fields. |
| Local container as Hub | `hugging-face-dataset` export is described as upload | Local container is not Hub upload. Pin field `local_container_is_not_upload`. |
| Retry without execute | 19.9 ships retry with no adapter | `retry_allowed` is false. 19.9 skips unless Decision B. |

## Decision

1. **Decision A.** Phase 19 does not install Hub execute, retry, or
   credential helpers. Network publication remains a separate
   authenticated action over an already verified export.
2. `veriformis.publication-adapter/v1` names repository, visibility,
   revision, credential source `none`, required dry-run, and
   `execute_allowed` false. Loading a pin is not upload.
3. Hugging Face Dataset local container is not Hub upload.
4. ADR-0017 Decision A and ADR-0018 Decision A stand.
5. **Decision B** (a narrow HF Hub adapter with dry-run then
   operator-confirmed upload) is rejected unless a later operator
   license supersedes this ADR.

## Consequences

- Item 19.8 still proves credentials never persist.
- Item 19.9 skips retry/idempotency with a record.
- CLI, MCP, and Mac gain no `hub-upload` command in this phase.

## Alternatives considered

- **B — Narrow HF Hub execute adapter:** rejected for Phase 19. The
  operator licensed Decision A.
- **Required cloud publication:** rejected. Network publication is
  absent from the default local path.

## Verification

Focused tests load and refuse pins, prove `execute_allowed` and
credential fields fail closed, prove CLI/MCP have no Hub tool, and
prove the ADR exists. GitHub remains the Python matrix.
