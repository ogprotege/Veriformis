# Phase 4 Risk Register

**Last reviewed:** 2026-08-21

| ID | State | Likelihood | Impact | Risk | Control |
| --- | --- | --- | --- | --- | --- |
| P4-R1 | Active | High | High | An exporter becomes a second construction, curation, or split pipeline. | Phase 4.5 exposes no mutation controls and fresh-reconstructs normalized candidate row-set and membership evidence for exact comparison with the plan baseline; produced destination-byte replay still must close in later increments |
| P4-R2 | Mitigated | Medium | High | Self-consistency is misreported as trusted source identity. | Phase 4.3 defaults export admission to retained expected manifest SHA-256, requires explicit lower trust, and rejects evidence drift without fallback |
| P4-R3 | Mitigated | Medium | High | Verify-then-read races allow source substitution. | Phase 4.4 derives every plan source fact and membership baseline from the immutable row and provenance semantics captured during descriptor-anchored verification; it does not reopen source paths |
| P4-R4 | Active | High | High | Traversal, links, aliases, or races escape the destination. | Phase 4.6 local gates pass for strict portable paths, descriptor-anchored staging and traversal, a closed regular-file/directory tree, final identity checks, and atomic no-replace promotion; Phase 4.9 adversarial closeout remains pending |
| P4-R5 | Active | Medium | High | A failure leaves a partial or falsely rolled-back export. | Phase 4.6 local gates pass for in-staging receipt verification, one promotion, owned-object cleanup, and explicit runtime visible-publication outcomes; Phase 4.9 closeout remains pending |
| P4-R6 | Active | Medium | Medium | Cancellation after visibility is reported as rollback. | Phase 4.6 local gates pass with cancellation only before promotion and post-visibility parent-sync failure as warning-success; Phase 4.9 closeout remains pending |
| P4-R7 | Active | Medium | Medium | Dependency-specific bytes are called portable deterministic bytes. | Phase 4.6 rejects semantic-only publication and proves only one instance against exact planned bytes; portable rerender and semantic replay remain Phase 4.7 |
| P4-R8 | Active | Medium | High | CLI, MCP, or Mac code reimplements export policy. | All surfaces delegate to `PipelineService` and share parity fixtures |
| P4-R9 | Active | High | High | The conformance exporter is mistaken for a supported Phase 5 container. | Keep it test-injected and absent from taxonomy, support registry, and user discovery |
| P4-R10 | Active | Medium | High | Phase 4 absorbs generic containers or trainer profiles. | Preserve every Phase 5/8/9/10 capability state until its own packet and evidence gate |
