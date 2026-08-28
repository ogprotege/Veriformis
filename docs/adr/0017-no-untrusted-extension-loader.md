# ADR-0017 — No Untrusted Extension Loader in Phase 16

**Status:** Accepted

**Date:** 2026-08-27

**Decider:** Phase 16.8 threat model. Operator instruction to finish
Phase 16 sequential items. Decision A is the plan's likely boundary and
the only option that 16.8 itself may record without adding a loader.

## Context and evidence

Phase 16 extracted `veriformis.extension-protocol/v1`, wrapped existing
bindings in a built-in-only registry, declared read-only capabilities,
migrated the text parser and generic `split-jsonl-directory` exporter, and
published a test-only compatibility kit. Those items satisfy the required
internal architecture.

A public or project-local plugin loader is optional and forbidden unless
this ADR approves a sandbox. Hard non-goals already forbid arbitrary
in-process Python from a dataset project and premature public plugin APIs.
Phase 11.6 skipped parser subprocess isolation; built-in parsers remain
in-process fail-closed. Optional extras (`trl`, `mlx-lm`, `columnar`,
`axolotl`, `llama-factory`, `unsloth`, `ocr`) stay empty. There is no
`loader.py`, no packaging entry point beyond the CLI script, and no
workspace `plugins/` scan.

This item is policy. It adds no loader.

## Threat model

| Surface | Threat | v1 control |
| --- | --- | --- |
| Process isolation | Untrusted code shares the compiler process and can rewrite memory, imports, or identities | No untrusted in-process load. Built-ins stay trusted in-process fail-closed. A future sandbox, if ever approved, MUST be a separate process. |
| Permissions / filesystem | A plugin reads or writes workspace objects, `HEAD`, or sibling files | No plugin filesystem grant. Dataset projects are data. Workspace transactions remain the only mutation path. |
| Network policy | A plugin phones home or pulls weights | Offline default. Declarations already refuse `network=true` and require `offline=true`. Core compile still makes no network call. |
| Resource limits | A plugin loops, allocates, or forks until the host is unusable | No untrusted process to bound. A future sandbox MUST cap CPU, memory, files, and wall time before any execute. |
| Signing / trust | An unsigned or substituted artifact becomes executable | No third-party artifact is executable. Origin `third_party` is a declaration token only. Built-in origin is the only runtime origin. |
| Crash containment | A plugin abort corrupts the interpreter or leaves a half-written bundle | No plugin process. Workspace commits already fail closed on replay mismatch. A future sandbox MUST treat crash as refusal and MUST NOT advance `HEAD`. |
| Workspace corruption | A broken extra or hostile declaration mutates content-addressed objects | Content-addressed objects are immutable. Missing or broken optional extras MUST fail in isolation (item 16.9). |
| Dataset-project code execution | `import` of project Python, `eval`, entry points under the project, or a `plugins/` folder | Forbidden. Dataset projects remain data. Item 16.10 refuses a workspace `plugins/` path. |

## Decision

1. **Decision A.** Phase 16 does not install an untrusted loader. There is
   no setuptools entry-point discovery, no `importlib` plugin scan, no
   workspace `plugins/` directory, and no CLI/MCP install-extension
   operation.
2. Built-ins remain distinct from third-party origin. Third-party origin
   may appear on a declaration. It MUST NOT become executable in this
   phase.
3. Dataset-project Python MUST remain non-executable. This includes
   in-process import, `eval`, and any path that treats a compile workspace
   as a package.
4. Built-in parsers stay in-process fail-closed. Subprocess isolation is
   reserved for a later, separately approved untrusted plugin boundary.
5. A later phase MAY propose Decision B (narrow sandbox: separate process,
   no network, signed artifacts, explicit install) only with a new ADR that
   supersedes this one. Decision C (reject the internal protocol) is not
   selected; items 16.2–16.7 already shipped the protocol.

## Consequences

- Items 16.9 and 16.10 complete isolation and adversarial closeout without
  a public plugin API.
- 16.10 skips public plugin loading with a dated record, the same honesty
  as Phase 15.5–15.8.
- Phase 18 Mac UI MUST NOT invent a plugin install surface from this ADR.
- Phase 17 MUST NOT admit new families through this protocol.

## Alternatives considered

- **B — Narrow sandbox now:** rejected for Phase 16. Signing, process
  isolation, resource limits, and an install surface are new product
  machinery. 16.8 is not licensed to add them.
- **C — Defer the remaining phase:** rejected. The internal protocol is
  the required work and is already implemented.
- **In-process plugins with a deny-list:** rejected. Deny-lists do not
  restore process isolation, and dataset-project import remains a
  hard non-goal.
- **Workspace `plugins/` with operator confirm:** rejected. Confirmation
  does not make in-process Python from a dataset project acceptable.

## Verification

Item 16.8 publishes this ADR and adds no loader. Isolation tests continue
to prove `loader.py` is absent, packaging has no plugin entry points, and
CLI/MCP/PipelineService expose no install-extension operation. Items 16.9
and 16.10 prove missing/broken extra isolation and adversarial refusals.

## Review triggers

Any proposal to load third-party code; setuptools entry points; a
workspace `plugins/` path; in-process project imports; subprocess plugin
isolation; signing or trust roots; Mac plugin UI; promoting origin
`third_party` to executable.
