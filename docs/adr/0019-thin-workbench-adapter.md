# ADR-0019 — Thin Workbench Adapter

**Status:** Accepted

**Date:** 2026-08-28

**Decider:** Phase 18.2 thin-adapter contract. Operator instruction to finish
Phase 18 sequential items. Decision A is the plan's required lock: Swift
wraps CLI; `PipelineService` owns policy.

## Context and evidence

The Mac workbench under `macos/` is a SwiftUI shell over one child
`veriformis` process. Private-beta Phases 0–2 shipped Home / Compile /
History / Settings, document-source compile, goal and preset discovery,
preflight, and post-compile goal preview. Mapping-detect and export
discover / dry-run / execute exist on the Swift CLI bridge and are unused
by views. Default Aptus handoff is off. Default `review_policy` is `none`.
Quality stays preview-only.

Phase 16 ADR-0017 Decision A forbids an untrusted loader and dataset-project
code execution. Phase 17 ADR-0018 Decision A forbids a compile-path
generator. Phase 18 must expose already-owned services without rebuilding
taxonomy, recipes, mapping, review, or export in Swift.

Item 18.1 recorded that honesty. This item is policy. It adds no screen.

## Threat model

| Surface | Threat | v1 control |
| --- | --- | --- |
| Swift as a second policy engine | Recipe defaults, taxonomy, mapping, review, or export live as Swift constants | `PipelineService` / CLI owns policy. A wrap pin requires `policy_owner` `pipeline-service` and `catalog_source` `shared-service`. There is no second catalog. |
| Truncated CLI JSON | Partial stdout is decoded as a catalog or execute receipt | Fail closed on `truncated`. Discovery already refuses truncated taxonomy, goals, presets, and export output. |
| Cancelled child process | Cancel is treated as a successful wrap | Fail closed on `cancelled`. A cancelled child yields no authoritative response. |
| Schema-invalid payload | Unknown fields are coerced or ignored | Fail closed on `schema-invalid`. Strict models refuse extra fields. |
| Dataset-project code execution | The app `import`s project Python, `eval`s a template, or loads a workspace `plugins/` path | Forbidden. ADR-0017 Decision A stands. Dataset projects remain data. The workbench remains a process adapter. |
| Generator or plugin UI | A Mac control installs a plugin or starts a compile-path generator | Forbidden. ADR-0017 and ADR-0018 Decision A stand. Pins refuse `plugin_install_allowed` and `generation_allowed`. |
| Invented review, trainer, or family policy | The Mac requires review, requires Aptus, or admits families in Swift | Pins refuse invented review, trainer, and family policy. Default `review_policy` stays `none`. Aptus stays optional. Families stay on the dataset-row path owned by Python. |

## Decision

1. **Decision A.** The Mac workbench is a process adapter over PipelineService and the CLI. Discovery and execute go through existing CLI, MCP, and Python packets. Swift owns no dataset policy.
2. `veriformis.workbench-adapter/v1` names one wrap (command, request
   schema, response schema). Loading a pin is not an execute and not a
   screen.
3. Truncated, cancelled, or schema-invalid CLI output fails closed. The
   adapter MUST NOT invent a fallback catalog.
4. ADR-0017 Decision A stands. Dataset-project code execution remains
   forbidden. There is no plugin UI.
5. ADR-0018 Decision A stands. There is no generator UI.
6. The Mac MUST NOT invent required-review, trainer, or family policy.
   Default `review_policy` stays `none`.
7. A later item MAY wrap mapping, export, or review by using an already
   owned CLI packet. It MUST NOT add a second catalog or a Swift policy
   engine. Decision B (native Swift policy) is rejected. Decision C
   (defer the remaining phase) is not selected; 18.3 through 18.10 need
   this lock.

## Consequences

- Items 18.3–18.8 may add screens only as thin wraps of existing packets.
- Item 18.2 adds no Review, Exports, or dataset-row UI.
- Public plugin APIs remain unimplemented. This ADR MUST NOT be read as
  shipping a plugin install surface.

## Alternatives considered

- **B — Native Swift policy engine:** rejected. A second taxonomy, recipe,
  mapping, review, or export catalog would diverge from CLI goldens and
  violate ordering rule 11.
- **C — Defer the remaining phase:** rejected. Goal-first IA, input modes,
  export, and review need this lock before they wrap packets.
- **In-process Python besides the CLI child:** rejected. The workbench
  remains one process adapter. Dataset projects stay data.

## Verification

Focused tests load and refuse pins, prove unknown commands and versions
fail closed, prove invented policy flags fail, and prove Review, Exports,
and mapping screens still do not exist. GitHub remains the Python matrix.
This item is policy. It adds no screen.
