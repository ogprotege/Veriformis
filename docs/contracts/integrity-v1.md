# Integrity Contract v1

**Contract ID:** `veriformis.acceptance.group1`

**Contract version:** `1`

**Product contract:** `veriformis.product`, version `1`

**Canonical stream contract:** `veriformis.canonical-stream`, version `1`

**Execution profile:** `offline-deterministic-v1`

**Implementation status:** Implemented in Group 1

**Last reviewed:** 2026-08-11 (historical scope reconciled with current runtime)

## Purpose

This document translates the product contract into exact Group 1 guarantees.
It governs the acceptance fixture, public contract identifiers, regression
tests, and the exit decision for roadmap Steps 1 through 6.

Veriformis owns the path from raw source capture through the verified dataset
seal. Group 1 establishes the integrity substrate for that complete product.
It does not reduce the product to cleaned corpus output.

## Version boundary

The package version and contract versions are independent. Package version
`0.1.0` remains a development alpha. Contract version `1` identifies the first
stable statement of product ownership and Group 1 acceptance.

A change that alters the meaning of an existing contract field, source range,
canonical stream, identity, or cleaning plan requires a contract-version
decision. Adding an implementation behind an already-declared guarantee does
not by itself require a product-contract version change.

## Product ownership

Veriformis owns these ordered stages:

1. `raw_capture`
2. `canonical_recovery`
3. `cleaning`
4. `construction`
5. `curation`
6. `balancing_and_splitting`
7. `formatting`
8. `validation`
9. `seal`

Training systems begin only after Veriformis produces a finished dataset
contract. Aptus is one optional downstream integration. Neither Aptus nor any
other consumer may silently replace Veriformis curation or split policy.

## Declared deterministic v1 boundary

The deterministic pipeline performs no network calls and no model generation.
The current declared suffix registry covers plain text, Markdown, DOCX, HTML,
digitally-born PDF, CSV, JSON, JSONL, and the code suffixes `.py`, `.js`,
`.ts`, `.java`, `.c`, `.cpp`, `.go`, `.rs`, `.rb`, and `.sh`. OCR-only PDFs
remain a named refusal rather than an implied success.

Its declared objective kinds are:

- `full_text`
- `continuation`
- `section_reconstruction`
- `before_after_transformation`
- `structured_field`

Its declared row schemas are:

- `text`
- `prompt_completion`
- `instruction_output`
- `messages`

These are product declarations. Only capabilities listed as implemented in
the current-status document may be presented as current runtime behavior.

## Group 1 guarantees

### Transactional workspace

Each successful stage commit creates a new immutable `WorkspaceRevision`.
Stage output becomes visible only after the complete revision is verified and
promoted. A failed or interrupted commit leaves the previous revision current.
Opening a workspace verifies the complete parent chain through its init
revision and the content-addressed objects referenced by every revision.
If the `HEAD` replacement succeeds but its final directory sync fails, the
visible revision remains the committed outcome and the API and CLI surface
crash-durability uncertainty explicitly.

Parse cross-validates source descriptors, the registry, canonical text, strict
IR, and parse reports before promotion. Clean cross-validates parsed and cleaned
IR, replayed plans, block derivations, and transforms before promotion.

Changing a stage invalidates every descendant in the current nine-stage graph.
A command with a stale expected revision fails with
`workspace-revision-conflict`.

### Source-scoped identity

Step 4 gives each current source instance, artifact, transform, chunk, and
revision a collision-resistant identity. Steps 5 and 6 apply the same
domain-separated substrate to diagnostics, evidence, cleaning operations, and
plans. Two files with the same basename remain distinct. Two source instances
with identical bytes retain distinct instance identities while sharing the
same raw SHA-256.

Artifact JSON and durable identity and configuration-digest payloads preserve
Unicode string and object-key sequences. Those durable paths apply NFC
normalization only to explicit locator fields, such as logical source paths,
before those fields enter an identity payload. Revision IDs are audit
identities and also bind parent history and commit time. Portable state digests
and per-source parse-input digests bind reproducible semantic state.

Candidate, dataset-record, and split types do not exist in Group 1. Their later
implementations must adopt this identity substrate.

Duplicate durable identities fail closed with `duplicate-identity`.

### Canonical recovery and evidence

Each supported parser returns a canonical document, a source registration,
the canonical-stream contract version and digest, and a diagnostics list.
The diagnostics list may be empty. Unsupported or degraded constructs must not
disappear without a typed diagnostic and source location.

The canonical visible-text projection preserves image alt text, citations, and
footnote and endnote references. Body and note blocks index one shared stream,
while source evidence distinguishes `body`, `footnote:<id>`, and
`endnote:<id>` regions. IR-only metadata remains in strict IR. Field-level
evidence for that metadata is deferred to Group 2 and is required before
`structured_field` construction.

Every derived text unit resolves to immutable source ranges plus any ordered
deterministic derivations. Spanless linkage and a bare `transformed` flag are
not sufficient evidence.

### Replayable cleaning

Preview and application consume the same source-scoped cleaning plan. The plan
records rule identity and parameters, ordered edits, source locations, before
and after digests, character counts, UTF-8 byte counts, warnings, and its own
canonical digest.

Applying the plan and replaying the plan over the same input produce the same
output digest. Cleaning preserves rich node structure unless the plan records
an explicit structural operation.

Current prose rules treat inline code, code blocks, math, and other literal
payloads as no-op regions.

With the same locator, bytes, parser, rules, and cleaning configuration,
raw-file preview, workspace preview, and clean produce the exact same plan ID.

### Strict persisted schemas

Canonical IR, parse reports, transform records, chunks, and source evidence
use strict versioned schemas. Loaders reject missing or unknown fields and
recompute durable identities or digests where applicable. Cleaning plans use
the same fail-closed exact-schema approach.

## Stable Group 1 failure codes

- `workspace-revision-conflict`
- `workspace-corrupt`
- `workspace-locked`
- `stale-stage`
- `duplicate-identity`
- `unsupported-workspace-version`
- `source-evidence-invalid`
- `cleaning-plan-invalid`

Human-readable messages may improve without changing these machine codes.

## Acceptance corpus

The checked-in fixture is under `tests/fixtures/acceptance/v1/`. Its manifest
pins every stored raw source by relative path, size, parser kind, and SHA-256.
DOCX input is generated deterministically inside contract tests rather than
stored as a binary fixture. The generator sorts ZIP entries, normalizes ZIP
timestamps and platform metadata, fixes compression settings, and checks the
result against a pinned size and SHA-256.

The corpus intentionally contains:

- different sources with the same filename stem;
- distinct source instances with identical bytes;
- Unicode text;
- rich Markdown structure;
- an unsupported Markdown HTML block requiring a diagnostic; and
- text and code sources already supported by M1.

The historical M1.1 acceptance requirement used one source inventory to produce both a
`full_text` dataset with `text` rows and a `continuation` dataset with
`prompt_completion` rows. Group 1 pinned that later requirement; it is now
implemented and tracked by the current status and release evidence.

## Regression policy

Every confirmed Group 1 defect receives a normal regression test. Such a test
must fail when its repair is removed. No Steps 1 through 6 test may remain
marked as an expected failure when Group 1 closes.

Confirmed defects owned by later roadmap steps are pinned with strict expected
failures. An unexpected pass fails the suite and requires removing the marker.
An expected failure is recorded debt, not completed behavior.

## Group 1 exit

Group 1 is complete only when:

- public constants and fixture manifests agree;
- all prior supported behavior remains covered;
- every Steps 1 through 6 regression is an ordinary passing test;
- multi-source revisions commit atomically;
- identities are source-scoped and duplicates are rejected;
- parser loss is explicit;
- provenance resolves through immutable evidence; and
- cleaning preview and application share one replayable plan.

Later-step expected failures remain visible until their owning roadmap steps
replace them with ordinary passing tests.

Rerun the project checks for current Group 1 closeout evidence. Strict expected
failures belong to later roadmap steps. Test totals are intentionally omitted
because coverage grows and the count is not a permanent contract term.

## Historical Group 1 implementation boundary

The current CLI persists Group 1 state through immutable workspace revisions.
Parse stores raw bytes, canonical text, canonical IR, and a mandatory parse
report for each source. Clean stores a replayable source plan and block
derivations. Chunk output carries reconstructible source evidence. Preview and
clean call the same planner and replay engine. Audit revision IDs may differ
between equivalent histories, while portable state and per-source parse-input
digests preserve semantic reproducibility.

At Group 1 closeout, dataset recipes, candidate records, curation,
authoritative splits, structured training rows, exact candidate-bundle
validation, and atomic closed-set sealing were intentionally assigned to later
roadmap groups. Those deferrals are historical: the capabilities are now
implemented. See [current status](../current-status.md) and the
[independent product roadmap](../plans/2026-08-11-veriformis-independent-product-roadmap.md)
for current maturity and remaining work.
