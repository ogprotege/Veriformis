# Phase 19 Execution Plan

**Status:** In progress

**Last updated:** 2026-08-31

**Authority:** [Independent Product Roadmap](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md) Phase 19; [program.json](../program.json); [project tracking policy](../../../../docs/governance/project-tracking.md); operator plan `/Users/biscuit/Desktop/Phase19-Plan.txt`.

**Predecessor:** Phase 18 closeout merged as PR #169 at
`9f384eeedb401441c564c511b642904c403dad38`. Clean local `main` equaled
`origin/main` at PR #170 `2737476eb2df83d82f575e3735b68487ee7cabc8` when this
packet opened (install-smoke SIGPIPE fix after closeout).

Each numbered item is one sequential pull request. Every pull request must pass
focused tests, project tracking, Ruff, the lock check, `git diff --check`, the
core test suite, and every GitHub check. Phase 19 does not change `macos/`
unless a later item is explicitly licensed to wrap spec dry-run as copyable
CLI. Default: no Mac work. GitHub remains the Python matrix; do not add an
Xcode job. The pull request then merges and leaves clean local `main` equal to
`origin/main` before the next item begins.

Phase 19 does not start Phase 20. Network publication is absent from the
default local path.

## Goal

Support reproducible pipelines, CI, and opt-in sharing without turning the
local compiler into a required cloud service. A locked project spec reproduces
the same semantic dataset and verified exports on supported clean hosts.

## Architecture

`PipelineService` owns policy. CLI and MCP are adapters. Project spec is
additive over `veriformis.pipeline/v1`. Mapping in a spec is confirm-then-map.
Dry-run writes nothing. Lockfile is not execute. Loading a publication pin is
not upload. Hub execute waits for an explicit operator license at 19.7;
default is Decision A: pin only.

## Locks

| ID | Lock |
| --- | --- |
| L1 | Sequential green PRs; packet opening is 19.1; closeout folds into 19.10. |
| L2 | No new spec execute, MCP tool, CI job, or Hub path in 19.1. Honesty only. |
| L3 | `veriformis.pipeline/v1` stays executable and byte-stable. Project spec is additive. Unknown keys fail closed. |
| L4 | PipelineService owns policy. CLI and MCP are adapters. No second catalog. No Swift policy. |
| L5 | Mapping in a spec is confirm-then-map. Unconfirmed plans cannot compile. `mapped_value` stays the evidence. |
| L6 | Document-source, dataset-row, and mixed are the only compiler paths. Specs cannot invent a fourth. |
| L7 | Dry-run writes nothing. Lockfile is not execute. Loading a publication pin is not upload. |
| L8 | Default `review_policy` stays `none`. Quality stays preview-only. No heuristic blocks seal. No quality-report command. |
| L9 | Export in a spec still shows bundle and receipt, overwrite refuse, no membership mutation, no trainer launch. |
| L10 | Existing SFT, Phase 16, Phase 17, and Phase 18 parity goldens stay byte-identical. |
| L11 | ADR-0017 Decision A and ADR-0018 Decision A stand. No plugin loader. No generator. |
| L12 | Network publication is absent from the default local path. No silent upload. No credentials in artifacts. |
| L13 | Hub execute waits for an explicit operator license at 19.7. Default is Decision A: pin only. |
| L14 | Hosted training stays out of scope. Family-to-trainer chrome stays out of scope. |
| L15 | Do not start Phase 20 from this packet. Signed/notarized Mac remains the Group 9 owner remainder. |

## Checklist

### 19.1 Open the automation-and-publication packet

**Branch:** `phase19/01-automation-packet`

- [x] Confirm Phase 18 complete and clean `main` at PR #169 plus PR #170.
- [x] Create the standard packet and move Phase 19 to `in_progress`.
- [x] Record L1 through L15 and reconcile active tracking documents.
- [x] Add isolation tests for the current pipeline/MCP/publication boundary.
- [x] Pass all local and GitHub gates, merge, and synchronize clean `main`.

No project spec, lockfile, dry-run command, MCP tool, CI example, Hub pin, or
resume path is permitted in this item.

### 19.2 Pin the versioned project spec

**Branch:** `phase19/02-project-spec`

- [x] Add additive `veriformis.project-spec/v1`. Mode, confirmed mapping,
      export, profiles. Loading is not execute. `pipeline/v1` stays.
- [x] Pass all local and GitHub gates, merge, and synchronize clean `main`.

### 19.3 Add spec schema, dry-run, lockfile, and environment inspection

**Branch:** `phase19/03-spec-dry-run-and-lock`

- [x] Schema from the model. Dry-run writes nothing. Lockfile pins spec
      digest. Env inspect. Deterministic exit codes.
- [x] Pass all local and GitHub gates, merge, and synchronize clean `main`.

### 19.4 Add machine-readable diagnostics and spec resume

**Branch:** `phase19/04-diagnostics-and-resume`

- [x] JSON diagnostics. Spec execute through PipelineService. Resume only
      on matching lock + HEAD.
- [x] Pass all local and GitHub gates, merge, and synchronize clean `main`.

### 19.5 Close remaining MCP parity gaps

**Branch:** `phase19/05-mcp-parity`

- [x] Audit listed packets. Wrap missing service packets only. No Hub. No
      quality-report. Skip `package` / `package-verify` with a record unless
      the audit treats them as verification.
- [x] Pass all local and GitHub gates, merge, and synchronize clean `main`.

### 19.6 Add CI examples with committed semantic fingerprints

**Branch:** `phase19/06-ci-examples`

- [x] Retained fixtures, example spec/lock, fingerprint verify. Do not
      replace golden-compile. No secrets. No xcodebuild.
- [x] Pass all local and GitHub gates, merge, and synchronize clean `main`.

### 19.7 Pin the optional publication boundary

**Branch:** `phase19/07-publication-boundary`

- [x] ADR-0020 Decision A: no Hub execute. Pin authenticated-action
      contract. Loading is not upload.
- [x] Pass all local and GitHub gates, merge, and synchronize clean `main`.

### 19.8 Prove credentials never persist in compiler artifacts

**Branch:** `phase19/08-credential-isolation`

- [x] Env/spec injection cannot appear in artifacts. Required even if Hub
      is skipped.
- [x] Pass all local and GitHub gates, merge, and synchronize clean `main`.

### 19.9 Add network retry and idempotency — or skip with a record

**Branch:** `phase19/09-publication-retry`

- [x] Skip with a record unless 19.7 Decision B shipped an execute adapter.
- [x] Pass all local and GitHub gates, merge, and synchronize clean `main`.

### 19.10 Add adversarial automation tests and close Phase 19

**Branch:** `phase19/10-adversarial-closeout`

- [x] Spec/mapping/export/Hub/credential refusals. Digest parity. Skip
      records. Closeout. Do not start Phase 20 from this packet.
- [ ] Pass all local and GitHub gates, merge, and synchronize clean `main`.

## Skip rules

| Item | Skip only when |
| --- | --- |
| 19.1–19.4, 19.6, 19.8, 19.10 | Do not skip. |
| 19.5 MCP parity | Do not skip the audit. Skip individual wraps only when the CLI/service packet does not exist (quality-report) or is outside the listed set (package transport). Record each skip. |
| 19.7 Hub execute | Default skip execute; required pin (Decision A). License Decision B only in writing before 19.7. |
| 19.9 retry/idempotency | Skip with a record unless 19.7 Decision B shipped an execute adapter. |
| Hosted training | Forbidden unless separately authorized. Record at closeout. |
| Mac project-spec UI | Skip with a record; Phase 18 already has copyable CLI. |
| GitHub xcodebuild, family-to-trainer, generator, plugins, signed Mac | Forbidden / out of scope. Record at closeout. |

## Exit gate

A locked project spec reproduces the same semantic dataset and verified
exports on supported clean hosts. Network publication is absent from the
default path. Existing goldens stay unchanged. Phase 20 stays planned.
