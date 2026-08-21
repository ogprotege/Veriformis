# Phase 4 Risk Register

**Last reviewed:** 2026-08-21

| ID | State | Likelihood | Impact | Risk | Control |
| --- | --- | --- | --- | --- | --- |
| P4-R1 | Active | High | High | An exporter becomes a second construction, curation, or split pipeline. | No membership-changing plan fields; bind and independently compare complete membership projections |
| P4-R2 | Mitigated | Medium | High | Self-consistency is misreported as trusted source identity. | Phase 4.3 defaults export admission to retained expected manifest SHA-256, requires explicit lower trust, and rejects evidence drift without fallback |
| P4-R3 | Active | Medium | High | Verify-then-read races allow source substitution. | Capture immutable row and provenance semantics during descriptor-anchored verification |
| P4-R4 | Active | High | High | Traversal, links, aliases, or races escape the destination. | Reuse strict portable-path policy, descriptor anchoring, closed trees, and adversarial tests |
| P4-R5 | Active | Medium | High | A failure leaves a partial or falsely rolled-back export. | Private staging, staged verification, one atomic promotion, explicit visible-publication outcome |
| P4-R6 | Active | Medium | Medium | Cancellation after visibility is reported as rollback. | Define visibility as the commit point and return the visible receipt after promotion |
| P4-R7 | Active | Medium | Medium | Dependency-specific bytes are called portable deterministic bytes. | Per-container exact-byte versus semantic-only evidence declaration |
| P4-R8 | Active | Medium | High | CLI, MCP, or Mac code reimplements export policy. | All surfaces delegate to `PipelineService` and share parity fixtures |
| P4-R9 | Active | High | High | The conformance exporter is mistaken for a supported Phase 5 container. | Keep it test-injected and absent from taxonomy, support registry, and user discovery |
| P4-R10 | Active | Medium | High | Phase 4 absorbs generic containers or trainer profiles. | Preserve every Phase 5/8/9/10 capability state until its own packet and evidence gate |
