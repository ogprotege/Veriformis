# Group 3 Finished Dataset Code Review

Last Updated: 2026-07-29

## Executive Summary

Group 3 now implements the intended Veriformis product path: supported raw
source bytes enter parsing, canonical recovery, cleaning, chunking,
construction, curation, leakage-safe splitting, objective-preserving row
lowering, exact validation, atomic sealing, and independent bundle
verification. The production path does not treat cleaned corpus text as the
product boundary and does not bypass evidence-bearing Group 2 records.

The implementation follows the authoritative Group 3 plan and Finished
Dataset Contract v1. Responsibilities are separated into dataset domain
modules, workspace revision semantics, CLI integration, bundle publication,
and an independent verifier. Workspace revision schema v3 binds the exact
stage graph and invalidates descendants after upstream change. The six-file
`minimal-v1` bundle keeps trainer payloads separate from aligned provenance,
binds the passing validation snapshot, and reports trust as either
`self_consistent` or `external_digest` without overstating authenticity.

No unresolved Critical, High, or Important issue remains in the reviewed
Group 3 production changes. Several defects found during review were corrected
and verified before this report was finalized. The complete repository gates
pass:

- `uv lock --check`
- `uv run ruff check src tests`
- `uv run pytest -q`: 606 passed
- `git diff --check`

## Critical Issues (must fix)

No Critical issues found.

## High Findings

No High findings found.

## Important Improvements (should fix)

No unresolved Important improvements found.

## Minor Suggestions (nice to have)

### 1. Make trainer payloads deeply immutable

`ProductRow` is frozen at the Pydantic model level, but its `payload` remains a
mutable dictionary, and `ProductRow.create` performs only a shallow copy
(`src/veriformis/datasets/serialization.py:246-295`). A caller can therefore
mutate a nested messages list or dictionary in memory after construction.

Every persistence, row-set, validation, and sealing boundary revalidates the
payload digest and identity, so this does not provide a silent path into a
sealed dataset. It does weaken the model's literal immutability claim and can
create confusing invalid in-memory values. A later cleanup should use typed
immutable payload variants or a defensive deep-freeze representation while
preserving exact JSON output.

### 2. Reduce duplicate contract registries

Several closed v1 registries have both central and module-local copies. The
curation codes appear in `src/veriformis/contracts.py:91-112` and
`src/veriformis/datasets/models.py:42-59`. Partition values also appear in
`src/veriformis/contracts.py:91`, `src/veriformis/datasets/splitting.py:45-49`,
and `src/veriformis/datasets/serialization.py:63-69`. The verifier's objective
field mapping at `src/veriformis/bundle/verifier.py:389-406` restates a domain
mapping already owned by dataset construction and curation.

Current tests catch the contract drift found during this review. Importing one
authoritative runtime registry where typing permits, with equality tests at
the remaining type boundaries, would reduce future drift.

### 3. Split the workspace semantic validator into private stage validators

`WorkspaceTransaction._validate_stage_semantics` spans
`src/veriformis/workspace.py:2310-3505`. It correctly replays each stage and
fails closed, but its size makes stage-local reasoning and review harder. This
is not a request to introduce the deferred public `PipelineService` in Group 3.
A private dispatcher with one validator per stage would preserve the current
boundary while making later Group 4 work safer.

## Architecture Considerations

### Raw source to sealed dataset

The compiler starts from immutable captured bytes and parser dispatch in
`src/veriformis/parsers/dispatch.py:31-78`. The CLI exposes the complete current
stage path in `src/veriformis/cli.py:821-1810`. Dataset semantics then remain in
focused operations: curation at `src/veriformis/datasets/curation.py:71`, split
construction at `src/veriformis/datasets/splitting.py:558`, row lowering at
`src/veriformis/datasets/serialization.py:994`, and exact validation at
`src/veriformis/datasets/validation.py:1280`.

This is faithful to the product doctrine. Cleaned IR and cleaned corpus state
are replayable intermediate compiler states. `full_text` is one legitimate
training objective, not a shortcut around raw capture, parsing, evidence,
construction, validation, or sealing.

### Identity, evidence, and workspace integration

Workspace v3 declares the exact dependency graph at
`src/veriformis/workspace.py:138-165`. Stage configs and semantic outputs bind
the same finished plan. A changed upstream stage makes all descendants stale,
and migration preserves verified Group 1 and Group 2 facts without treating
legacy downstream state as Group 3 evidence.

Required-review replay extracts the exact immutable `ReviewEvidence` already
embedded in accepted promotion decisions. This is consistent with the Group 2
contract. The evidence is a local, unauthenticated attestation and is not
presented as reviewer authentication. The CLI also states that
`--require-review` leaves candidates pending because completed review evidence
is not yet ingested through that surface.

Unreadable or digest-invalid workspace objects are workspace corruption and
fail closed before a new revision commits. This is distinct from a readable,
valid dataset snapshot whose gates fail. The latter produces explicit failed
and blocked validation results.

### Validation and independent verification

Validation reruns construction, curation, split, serialization, evidence, and
all 17 ordered gates against one immutable snapshot. Seal revalidates the saved
passing report instead of trusting a stored Boolean.

The independent verifier at `src/veriformis/bundle/verifier.py:385-767`
strict-loads every provenance row and reconstructs its product row,
serialization plan, included curation decision, and complete row set. It
checks exact field-to-payload lowering, field-evidence source membership,
snapshot identities, and exact snapshot source coverage. It also enforces one
objective and serialization plan, unique identities and record fingerprints,
source-scoped target consistency, one leakage group per source, and no source
or leakage group crossing partitions. Finally, it aligns train-then-evaluation
counts, ordinals, partitions, row IDs, and payload digests, then checks the
reconstructed row-set identity and canonical bytes against the snapshot. It
uses only bundle bytes plus an optional caller-supplied manifest digest.

The minimal bundle intentionally does not copy raw files, cleaned IR, or all
replay artifacts. The snapshot directly binds the six semantic Group 3
artifacts and three emitted files. The construction-result binding includes
its construction input digest, while raw, parse, clean, and chunk artifacts
remain inspectable in workspace history and are replayed before seal. The
minimal bundle does not embed those workspace artifacts. A portable bundle
with embedded replay material requires a later explicit retention profile.
Users who need an external authenticity anchor must retain the manifest
SHA-256 separately.

### Atomic publication and its security boundary

Seal publication now runs under the workspace's exclusive commit lock
immediately before `HEAD` promotion
(`src/veriformis/workspace.py:2126-2278`). A visible publication followed by a
receipt failure is reported truthfully and can be recovered only from an
independently verified, byte-identical bundle
(`src/veriformis/cli.py:1703-1758`).

Bundle staging uses descriptor-anchored writes, recursive cleanup, and
parent-descriptor-anchored no-replace rename
(`src/veriformis/bundle/finished.py:1089-1314`). The contract now states the
necessary boundary at `docs/contracts/finished-dataset-v1.md:654-663`: the
destination parent must be an integrity-controlled namespace. A hostile
same-owner process can mutate that namespace during an operating-system call
and therefore requires OS permission isolation. This limitation is explicit
and is not hidden behind the `external_digest` trust grade.

### Resolved during review

The following issues were found, corrected, and retested before finalization:

- Curation now rejects a finished plan whose serialization schema contradicts
  its construction recipe at `src/veriformis/datasets/curation.py:97-100`.
- The closed Group 3 schema registry now includes
  `veriformis.exact-record-fingerprint/v1` at
  `src/veriformis/contracts.py:134-160`.
- Bundle verification now performs semantic payload and provenance alignment,
  including exact objective and serialization-plan reconstruction, exact
  field-to-payload lowering, and field-evidence source membership at
  `src/veriformis/bundle/verifier.py:385-473` and
  `src/veriformis/datasets/serialization.py:381-387`.
- Cross-row verification now rejects duplicate exact record fingerprints,
  source-scoped conflicting targets, a source assigned to multiple leakage
  groups, and any source or leakage group crossing partitions. It also requires
  emitted sources to cover the snapshot source scope exactly at
  `src/veriformis/bundle/verifier.py:503-732`.
- Each emitted curation-decision identity is now reconstructed as an included,
  quality-passed decision. The verifier also reconstructs the full row set and
  compares both its identity and canonical bytes with the validation snapshot
  at `src/veriformis/bundle/verifier.py:592-603` and
  `src/veriformis/bundle/verifier.py:735-767`.
- Default current-snapshot publication now occurs under the workspace commit
  lock, exact retry recovery does not overwrite a visible bundle, and cleanup
  cannot recursively delete a swapped top-level path.

These are resolved implementation changes, not unresolved findings.

## Next Steps

1. Accept this review as the Group 3 architecture and security closeout because
   no Critical, High, or Important finding remains.
2. Schedule the three minor maintainability items with Group 4 work or a small
   follow-up change. They do not block the Group 3 exit gate.
3. Preserve the 606-test repository gate and exact contract checks in CI.
4. Keep the separately retained manifest digest and integrity-controlled
   publication-parent requirements visible in every future sealing surface.
5. Proceed to the Group 4 `PipelineService` and thin CLI boundary only after
   this Group 3 review and implementation are committed together.

The three minor suggestions are nonblocking Group 4 or follow-up candidates.
They do not keep the Group 3 exit gate open and require no approval before
Group 3 closeout.
