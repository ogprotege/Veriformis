# Phase 4 Decision Index

**Status:** Active

| Decision | State | Basis |
| --- | --- | --- |
| The verified `minimal-v1` bundle remains canonical; exports are derivatives | Accepted | ADR-0004; roadmap Phase 4 |
| Phase 4 executes as nine sequential green PRs matching roadmap items 1–9 | Accepted | Owner direction on 2026-08-21 |
| `PipelineService` owns an injected `ExportService`; adapters call only the composition root | Accepted | Existing service architecture and roadmap item 1 |
| Source semantics are captured during descriptor-anchored verification, not by re-reading paths after verification | Accepted | Existing bundle verifier race boundary |
| Existing finished-bundle schemas and the six-file closed set remain unchanged | Accepted | Finished Dataset Contract v1 and Phase 3 compatibility proof |
| Export receipts live with the derivative, never inside the source bundle or workspace | Accepted | ADR-0004 |
| Portable identities exclude absolute paths, clocks, process IDs, temporary names, and durability warnings | Accepted | Cross-surface determinism requirement |
| The v1 overwrite policy begins with no-replace/refuse only | Accepted | Phase 4 safety requirement; replacement is not required |
| The Phase 4 conformance exporter is injected by tests and is absent from product taxonomy/support discovery | Accepted | Phase 4 exit gate versus Phase 5 scope |
| Verified export v1 uses ten strict persisted schemas under `veriformis.verified-export` version 1 | Accepted | Phase 4.2 contract and exact-schema tests |
| Receipt identity excludes its own bytes and binds every other planned destination file | Accepted | Avoid self-hashing while preserving a closed derivative tree |
| Every plan binds at least one exact dependency | Accepted | Empty cannot distinguish dependency-free rendering from omitted evidence |
| Exact-byte and semantic-content-only claims are distinct closed literals | Accepted | Dependency-sensitive renderings cannot overclaim portable bytes |
| Export-source admission defaults to `require_external_digest`; `allow_self_consistent` must be explicit, and supplied evidence never falls back | Accepted | Phase 4.3 source-trust contract and fail-closed service tests |
| Plan population derives every source identity and the complete source membership baseline from one admitted immutable bundle view; callers cannot supply those facts | Accepted | Phase 4.4 source/output binding requirement and verify-then-read race boundary |
| Phase 4.4 binds the source membership baseline; Phase 4.5 reconstructs and compares normalized semantic candidates, while produced destination evidence remains Phase 4.6–4.7 | Accepted | Roadmap items 4–7 remain separate sequential proof obligations |
| Phase 4.5 accepts separate normalized train/evaluation `ProductRow` sequences plus aligned `RowProvenance`, reconstructs a plan-bound `RowSet`, and requires exact row-set and full projection equality | Accepted | Logical partitions cannot be hidden in claimed provenance; counts or assignment digest alone are insufficient |
| Phase 4.5 proves only normalized in-memory semantic membership; produced-file bytes, destination bindings, receipts, and semantic replay remain Phase 4.6–4.7 | Accepted | Preserve the evidence limit while the writer and deterministic replay boundaries remain absent |
| Phase 4.6 exposes no renderer-selection argument or shipped renderer; only a private conformance subclass supplies exact files and normalized candidates | Accepted | Exercise the foundation without creating Phase 4.8 discovery or a Phase 5 support claim |
| Phase 4.6 publishes only `portable_exact_bytes`; Phase 4.7 admits `semantic_content_only` only through private profile-bound byte-to-semantic replay | Accepted | Copying a planned semantic digest into a receipt is not independent observation |
| A canonical receipt is written and independently reloaded inside private staging before one atomic no-replace promotion | Accepted | The visible commit point contains its complete receipt; normal receipt writing cannot fail after promotion |
| Cancellation has checkpoints only before promotion; parent-sync failure is warning-success and any later failure must carry an explicit visible-publication outcome | Accepted | A committed destination is never reported as rolled back or deleted by cleanup |
| Both determinism claims require two private renderer invocations from independent strict plan and source-row-set reloads before destination access | Accepted | One renderer invocation proves instance conformance, not portable reproducibility |
| Exact profiles compare complete normalized path-to-bytes trees; semantic-only profiles compare complete profile-versioned canonical preimage trees and validated memberships while permitting physical bytes to differ | Accepted | The two closed determinism literals make different reproducibility claims |
| A semantic replayer returns canonical preimage bytes plus reconstructed normalized membership evidence; the service computes digests and reuses the Phase 4.5 membership gate | Accepted | A hook-supplied or plan-copied digest is self-attestation rather than observation |
| Semantic publication replays descriptor-reread staged bytes and requires the preflight preimage tree again before verification and promotion | Accepted | Preflight replay alone does not prove that staged destination bytes preserve the checked semantics |
| Exact renderer/replayer dependencies and a versioned, unambiguous semantic preimage definition belong to the container profile contract; any shipped semantic profile must additionally define and enforce resource limits | Accepted | The Phase 4.7 fixture is statically bounded, while library defaults, unversioned canonicalization, and unbounded public parsing cannot support portable semantic claims |
| Phase 4.7 adds runtime admission evidence but no persisted rerender transcript; adding durable cross-render evidence requires a new contract version | Accepted | The ten frozen v1 schemas bind the profile claim and one published instance only |
| Private conformance hooks and fixtures remain absent from taxonomy, support discovery, and public APIs | Accepted | Phase 4.7 evidence cannot silently become Phase 4.8 surfaces or a Phase 5 container |
| Phase 4.8 uses one immutable exports-owned implementation catalog, keyed by exact container and optional consumer identifiers and versions; production discovery is empty and only tests inject conformance implementations | Accepted | Expose truthful executable discovery without creating a public plugin API or premature Phase 5 support claim |
| Dry run and source-bound verify derive plans internally; execute and verify require the operator-confirmed dry-run plan identity | Accepted | Adapters cannot turn caller-supplied plans, profiles, dependencies, file sets, or membership into execution authority |
| Public inspect is explicitly `self_described_physical`; only source-bound verify may produce `ExportVerification` evidence | Accepted | A receipt embedded in the destination is not its own external source authority |
| Every adapter uses the non-persisted canonical export surface request/response v1 protocol, and the Mac bridge shells the CLI with separate stdout/stderr capture | Accepted | Preserve one implementation and one serializer without changing the ten persisted v1 schemas or decoding diagnostics as JSON |
| Public overwrite policy is the single literal `refuse`; no surface exposes force, replacement, renderer, replayer, membership, or registration controls | Accepted | Preserve atomic no-replace publication and the private trusted implementation boundary |
| Python publicly exports the cancellation callback, runtime publication outcome, and visible-partial exception, while all publication hooks remain private | Accepted | Callers must type cancellation and success and catch honest visible publication without importing an underscore module |
| Phase 4 closes with the conformance implementation test-injected and production discovery empty; closing the service-foundation gap does not promote a container or consumer profile | Accepted | Roadmap Phase 4 exit evidence is distinct from Phase 5/8/9/10 support admission |
