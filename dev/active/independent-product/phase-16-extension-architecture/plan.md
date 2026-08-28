# Phase 16 Execution Plan

**Status:** In progress

**Last updated:** 2026-08-27

**Authority:** [Independent Product Roadmap](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md) Phase 16; [program.json](../program.json); [project tracking policy](../../../../docs/governance/project-tracking.md).

**Predecessor:** Phase 15 closeout merged as PR #139 at
`435bd63c90778674ff4eb68a5d882a168349baca`. Clean local `main` equaled
`origin/main` there when this packet opened.

Each numbered item is one sequential pull request. Every pull request must pass
focused tests, project tracking, Ruff, the lock check, `git diff --check`, the
core test suite, and every GitHub check. It then merges and leaves clean local
`main` equal to `origin/main` before the next item begins.

Phase 16.8 is an operator gate. No untrusted loader may begin before its ADR is
merged and the operator selects the trust boundary. Phase 17 does not start
from this packet.

## Goal

Extract a thin internal protocol over existing bindings, migrate one built-in
parser and one exporter without changing their golden outputs, publish a
compatibility test kit, and prove that missing or broken optional extensions
cannot break core startup or corrupt a workspace.

## Architecture

`PipelineService` owns extension policy. CLI and MCP are adapters. Taxonomy
remains the seven-axis capability-state registry rather than the executable
registry. Built-ins stay trusted and in-process fail-closed. Third-party code,
if it is ever approved, requires a separate process boundary and explicit
trust controls. Exporters and consumer profiles remain in one catalog.

## Locks

| ID | Lock |
| --- | --- |
| L1 | Execute sequential green PRs. Item 16.1 opens the packet; 16.10 closes it. |
| L2 | Item 16.1 adds honesty records and isolation tests only. |
| L3 | Internal registries precede any public plugin API. |
| L4 | `PipelineService` owns policy. CLI and MCP remain adapters. No Mac UI. |
| L5 | Built-ins and third-party extensions remain distinct. |
| L6 | Dataset projects never execute arbitrary in-process Python. |
| L7 | Parser and exporter migrations preserve identical goldens. |
| L8 | Existing empty extras stay empty until a named isolation fixture requires otherwise. |
| L9 | Taxonomy is not the executable registry. No eighth taxonomy axis. |
| L10 | The protocol admits no new parser, input family, container, or profile. |
| L11 | Built-in parsers stay in-process fail-closed. Only approved untrusted plugins require subprocess isolation. |
| L12 | Exporters and profiles use one catalog. Profiles remain adapters identified by `consumer_id`. |
| L13 | Phase 4.7 render and replay hooks remain trusted conformance code. |
| L14 | Stop after 16.8 for operator review before any untrusted loader. |
| L15 | Do not start Phase 17 from this packet. |

## Checklist

### 16.1 Open the extension-architecture packet

**Branch:** `phase16/01-extension-packet`

- [x] Confirm Phase 15 complete and clean `main` at PR #139.
- [x] Create the standard packet and move Phase 16 to `in_progress`.
- [x] Record L1 through L15 and reconcile active tracking documents.
- [x] Add isolation tests for the pre-Phase-16 architecture.
- [x] Pass all local and GitHub gates, merge, and synchronize clean `main`.

No protocol, executable registry, loader, extra, CLI operation, or MCP
operation is permitted in this item.

### 16.2 Define the internal extension protocol

**Branch:** `phase16/02-extension-protocol`

- [x] Add strict `veriformis.extension-protocol/v1` declarations for six
      kinds: source parser, row mapper, deterministic constructor, quality
      check, container exporter, and consumer profile.
- [x] Version origins, lifecycle, extras, deterministic requirements,
      diagnostics, fixtures, and discovery metadata.
- [x] Refuse unknown fields, kinds, and contract versions. Add no loader or
      dispatch change.

### 16.3 Install internal typed registries

**Branch:** `phase16/03-internal-registries`

- [x] Wrap existing parser dispatch, row mapping, constructors, quality
      checks, exporters, and profiles behind built-in-only typed registries.
- [x] Preserve one export catalog and the unchanged default runtime path.
- [x] Prove unchanged parse reports, constructor selectors, export selectors,
      and sealed-bundle identities.

### 16.4 Declare built-in capabilities

**Branch:** `phase16/04-capability-declarations`

- [x] Add one read-only declaration per built-in with exact contract version,
      extra, deterministic requirements, diagnostics, fixtures, discovery
      metadata, and supported lifecycle state.
- [x] Surface declarations through `PipelineService` and thin adapters only
      where needed. Keep third-party loading absent.

### 16.5 Migrate the text parser

**Branch:** `phase16/05-migrate-text-parser`

- [x] Select `text` only through the protocol while every other suffix retains
      existing dispatch.
- [x] Preserve byte-identical parse reports and source identities. Refuse
      unknown contract versions with exact version diagnostics.

### 16.6 Migrate split JSONL

**Branch:** `phase16/06-migrate-split-jsonl`

- [ ] Bind `split-jsonl-directory` only through the protocol.
- [ ] Preserve exact files, membership, receipt digest, and the single export
      catalog. Leave all other containers and profiles unchanged.

### 16.7 Publish the compatibility test kit

**Branch:** `phase16/07-compatibility-kit`

- [ ] Freeze source, row, and export fixtures for the two exemplars.
- [ ] Add refusals for unknown kind, unknown version, missing extra, broken
      declaration, and unapproved third-party origin.
- [ ] Keep the kit test-only. Add no product plugin runner or project-local
      plugin path.

### 16.8 Threat-model third-party plugins

**Branch:** `phase16/08-plugin-threat-model`

- [ ] Add ADR-0017 covering process isolation, permissions, network, resource
      limits, signing, crash containment, and workspace corruption.
- [ ] Add no untrusted loader. Merge green, synchronize `main`, and stop for
      operator decision A, B, or C.

### 16.9 Isolate missing and broken optional extensions

**Branch:** `phase16/09-broken-extension-isolation`

- [ ] Prove core CLI, MCP, and `PipelineService` start with a missing extra.
- [ ] Prove a broken test-only optional binding cannot advance `HEAD`, write a
      bundle, or corrupt a workspace.
- [ ] If 16.8 selects B, prove the approved sandbox against crashes, network
      attempts, and unsigned artifacts. Otherwise add no untrusted loader.

### 16.10 Add adversarial tests and close Phase 16

**Branch:** `phase16/10-adversarial-closeout`

- [ ] Refuse unknown versions, duplicate selectors, unapproved third-party
      origins, project-local plugins, declaration tampering, and registry
      mutation.
- [ ] Reprove text, split-JSONL, and sealed-bundle goldens.
- [ ] Record any skipped public loader, reconcile all tracking and support
      claims, close Phase 16, and do not start Phase 17.

## Exit gate

One built-in parser and one exporter run through the protocol with identical
golden outputs. A missing or broken optional extension fails in isolation while
core starts and workspaces remain uncorrupted. Compatibility errors name exact
contract versions. Public plugins exist only if 16.8 and the operator approve
the sandbox.
