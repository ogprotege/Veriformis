# Phase 10 Decision Index

**Status:** Active

| Decision | State | Basis |
| --- | --- | --- |
| Phase 10 executes as eight sequential green pull requests, with packet opening folded into 10.1 and closeout into 10.8 | Accepted | Phase 6–9 precedent |
| Each candidate is admitted independently; failed pins do not emit | Accepted | ADR-0014; roadmap section 5 |
| `axolotl`, `llama-factory`, and `unsloth` refuse as Phase 10 candidates | Accepted | Same honesty pattern as Phase 8.1 |
| Empty extras `axolotl`, `llama-factory`, and `unsloth` in 10.1; version ranges live in later pins | Accepted | Keep `uv lock` free of those trainers |
| Aptus remains the sibling handoff until item 10.6 | Accepted | ADR-0012 |
| Hosted OpenAI is out of this packet | Accepted | Roadmap: research separately; offline default |
| Operator reviews after 10.2 before 10.3 begins | Accepted | Operator instruction 2026-08-24 |
| Items 10.3–10.8 land as one pull request | Accepted | Operator instruction 2026-08-24 after 10.2 |
| First admitted emit is Axolotl; second is LLaMA-Factory | Accepted | 10.2 pins; Unsloth experimental |
| Unsloth is skipped with the experimental candidate pin | Accepted | Item 10.5 skip rule |
| Aptus becomes `consumer_id=aptus`; sibling handoff remains | Accepted | Item 10.6; default seal still false |
| The exporter does not train | Accepted | ADR-0012 |
