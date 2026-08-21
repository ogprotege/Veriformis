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
| Phase 4.6 publishes only `portable_exact_bytes`; `semantic_content_only` fails closed until actual byte-to-semantic replay exists in Phase 4.7 | Accepted | Copying a planned semantic digest into a receipt is not independent observation |
| A canonical receipt is written and independently reloaded inside private staging before one atomic no-replace promotion | Accepted | The visible commit point contains its complete receipt; normal receipt writing cannot fail after promotion |
| Cancellation has checkpoints only before promotion; parent-sync failure is warning-success and any later failure must carry an explicit visible-publication outcome | Accepted | A committed destination is never reported as rolled back or deleted by cleanup |
