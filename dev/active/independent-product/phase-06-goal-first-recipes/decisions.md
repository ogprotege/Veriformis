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
| Item 6.2 binds each goal to `eligible_input_families` proved against what each parser and cleaning rule really supplies: `delimited-table` and `json-records` carry no supported scalar; `source-code` is a single code block cleaning never edits, so it supplies no before-and-after pair; `pdf-text` supplies only synthetic `Page N` labels, so it supplies neither a real section nor a recorded attribute until Phase 12 recovers PDF structure | Accepted | Parser IR emission, cleaning's non-editable code blocks, the constructors' requirements, and the no-invented-target doctrine |
| `balance_mode` in `curation_defaults` uses the persisted `CurationPolicy` spelling; the CLI/MCP hyphenated spelling is unified by Phase 6.4 presets | Accepted | One executable policy authority until presets exist |
| `non_claims` is a closed four-code vocabulary every goal states; `not_this` remains the goal-specific plain-language list | Accepted | One machine-checkable non-claim set without duplicating prose |
| `curation_defaults` in the catalog mirror the executing defaults of the service, CLI, MCP, and recipe library and are test-bound until Phase 6.4 presets become the single executing source | Accepted | Roadmap item 4; avoids a second default authority before presets exist |
| `compatible_generic_exports` is stored per representation and test-derived from the production export catalog | Accepted | Discovery-closed truth without a runtime export dependency inside the catalog loader |
| The Phase 5.6 cancellation-race thread budget is widened to thirty seconds inside item 6.2 as a declared test-robustness fix | Accepted | One observed CI timing failure on a slow runner; the race is event-ordered |
| The goal preview renders rows through the same `render_record_payload` function `format` uses and derives the supervised span as the whole target value under the taxonomy loss policy; nothing is persisted | Accepted | One row semantics; decision "derive, do not persist" |
| Preview sample policy is `first-accepted-record-per-primary-source`, with explicit `record_ids` as the only override; bounds are 64 KiB per record and 256 KiB per response with whole-record omission | Accepted | Phase 5.6 precedent; deterministic, side-effect-free |
| Strict-IR field evidence is reported by JSON pointer with the exact encoded value; it has no character span | Accepted | `structured_field` evidence is an IR scalar, not source text |
| Post-#59 reconciliation cites PR #59 at `65cbd471e96d83f8dd65e2cda60e90f64a916e2b` in every active record while leaving dated historical entries unchanged | Accepted | Project-tracking claim discipline |

No Phase 6 decision is pending. Later items remain scoped to their own
sequential pull requests and cannot broaden these boundaries.
