# Phase 6 Decision Index

**Status:** Active

| Decision | State | Basis |
| --- | --- | --- |
| Phase 6 executes as seven sequential green pull requests matching roadmap items 1–7, with packet opening folded into 6.1 and closeout into 6.7 | Accepted | Phase 4 and Phase 5 precedent; roadmap Phase 6 work items |
| Every goal resolves to exactly one of the five persisted objective kinds and one named recipe library id; the catalog adds no objective | Accepted | Taxonomy v1 "MUST NOT add, rename, or drop"; roadmap invariant 6 |
| Supervised instruction and conversation representations are catalog representations over the four supervised objectives, admitted only where the source supplies both context and target; they are not a sixth goal | Accepted | Roadmap work item 1 wording; finished-dataset v1 row lowering |
| The goal catalog, presets, and their plain-language copy are packaged versioned JSON validated by strict models; CLI, MCP, service, runner, and Swift consume them through discovery rather than constants | Accepted | Roadmap work item 4 ("versioned data, not duplicated CLI/Swift constants") |
| The Mac workbench gains a catalog-driven goal picker (6.4), preflight panel (6.5), and loss/row preview screen (6.3) in Phase 6; Phase 18 extends rather than rebuilds them | Accepted | Owner direction 2026-08-22; Phase 18 depends on Phase 6; exit gate is phrased for a non-developer |
| `input_family` becomes the seventh taxonomy axis, additive to taxonomy v1 under ADR-0008 without a contract version bump | Accepted | Owner direction 2026-08-22; Phases 11 and 12 need a discoverable per-family support claim; preflight needs per-source eligibility |
| The supervised region is derived from objective field roles and the taxonomy loss policy for preview and is not persisted in `ProductRow` or provenance | Accepted | Under finished-dataset v1 the boundary is a pure function of row schema; Phase 17 multi-span supervision requires a new row contract version that would redesign any field added now |
| Usability criteria U1–U6 are predeclared in `plan.md` before any picker or preview is built | Accepted | Roadmap usability layer requires predeclared comprehension and task-completion criteria |
| Preview and preflight are runtime-only responses bounded exactly like the Phase 5.6 dry-run preview; they never mutate a workspace, call a renderer, or access a destination | Accepted | Phase 5.6 precedent and fail-closed doctrine |
| Compile preflight reports only source eligibility, incompatible selections, missing evidence, expected exclusions, and known limitations; distributions, near-duplicates, PII, and tokenizer simulation remain Phase 13 | Accepted | Roadmap work item 5 scope versus Phase 13 |
| Instruction truthfulness is enforced deterministically: catalog templates are the default instruction literals, and operator instructions must pass a documented per-goal claim-vocabulary check | Accepted | Roadmap work item 7; v1 has no LLM or heuristic judgment |
| Post-#59 reconciliation cites PR #59 at `65cbd471e96d83f8dd65e2cda60e90f64a916e2b` in every active record while leaving dated historical entries unchanged | Accepted | Project-tracking claim discipline |

No Phase 6 decision is pending. Later items remain scoped to their own
sequential pull requests and cannot broaden these boundaries.
