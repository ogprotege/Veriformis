# Phase 16 Risk Register

**Status:** Open for Phase 16

| ID | State | Likelihood | Impact | Risk | Control |
| --- | --- | --- | --- | --- | --- |
| P16-R1 | Controlled for 16.1 | High | High | Packet opening implies a plugin API already exists | Isolation tests and explicit non-claims |
| P16-R2 | Open | High | High | A generic registry becomes a second policy engine | `PipelineService` ownership; wrappers preserve existing policy |
| P16-R3 | Open | High | High | Parser migration changes recovery bytes or identities | Frozen parse reports and source-identity goldens |
| P16-R4 | Open | High | High | Export migration duplicates the existing catalog | One catalog; split JSONL migration inside the existing selector model |
| P16-R5 | Controlled | High | High | Third-party declarations become executable before threat modeling | ADR-0017 Decision A; built-in-only registry; origin refusal |
| P16-R6 | Open | Medium | High | Optional import failure prevents core startup | Missing-extra and clean-import isolation tests |
| P16-R7 | Open | Medium | High | Broken extension mutates a workspace before failure | Transaction boundary and no-advance/no-bundle tests |
| P16-R8 | Open | Medium | High | Lifecycle metadata conflicts with support truth | Contract versioning and exact compatibility diagnostics |
| P16-R9 | Controlled | Medium | High | Extension work adds an eighth taxonomy axis | L9 and tracking regression |
| P16-R10 | Controlled | Medium | High | Phase 17 semantics enter through an extension declaration | Closed six-kind contract and L10 |
| P16-R11 | Controlled | Low | High | Mac UI invents extension policy | Mac work excluded until Phase 18 |
