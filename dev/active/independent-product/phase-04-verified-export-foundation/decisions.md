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
| Phase 4.4 binds the source membership baseline but does not claim preservation; Phase 4.5 reconstructs and compares renderer/destination membership | Accepted | Roadmap items 4 and 5 remain separate sequential proof obligations |
