# Phase 20 Decision Index

**Status:** Active

| Decision | State | Basis |
| --- | --- | --- |
| Execute 20.1 through 20.10 as sequential green PRs | Accepted | Operator instruction 2026-08-31: plan and execute Phase 20 the same way as Phase 19 |
| Open the packet inside 20.1 and fold closeout into 20.10 | Accepted | Tracking policy and Phase 12–19 precedent |
| Add honesty only in 20.1 | Accepted | No premature matrix freeze, version bump, signed Mac, Hub, or lifecycle docs |
| Version stays `0.1.0` development alpha until 20.10 | Accepted | L3; L14; roadmap item 10 |
| Freeze only capabilities whose evidence gates passed | Accepted | L4; roadmap next_gate |
| Honest 1.0 is CLI-first; public signed Mac is not in the matrix unless 20.6 produces owner-signed evidence | Accepted | L5; Group 9 remainder; Phase 18 skip record |
| ADR-0020 Decision A stands; no Hub execute | Accepted | L6; Phase 19 closeout |
| ADR-0017 Decision A and ADR-0018 Decision A stand | Accepted | L7; no plugin loader; no generator |
| Empty extras stay empty; profile failure does not block core unless frozen in at 20.8 | Accepted | L8; Phases 8–10 |
| Default review_policy stays none; quality stays preview-only | Accepted | L9; Phase 13 and 14 closeouts |
| Existing SFT and Phase 16–19 goldens stay byte-identical | Accepted | L10 |
| PipelineService owns policy; CLI and MCP are adapters | Accepted | L11; ADR-0019 Decision A |
| Hosted training, family-to-trainer chrome, and GitHub xcodebuild stay out of scope | Accepted | L12 |
| Primary golden path contains no Aptus | Accepted | L13; Phase 1 standalone independence |
| If 20.10 evidence cannot support a 1.0 claim, keep `0.1.0` | Accepted | L14 |
| Do not invent a Phase 21 from this packet | Accepted | L15; Phase 20 is the last roadmap phase |
| Freeze CLI-first 1.0 support matrix; loading is not a version bump | Accepted | Item 20.2 |
| Publish operator migration guide; no silent schema jumps | Accepted | Item 20.3 |
| Record security review without a required network scanner | Accepted | Item 20.4 |
| Retain isolated-wheel golden CLI evidence without Aptus | Accepted | Item 20.5 |
| Skip signed/notarized Mac with a record | Accepted | Item 20.6 |
