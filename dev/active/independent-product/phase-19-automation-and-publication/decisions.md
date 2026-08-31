# Phase 19 Decision Index

**Status:** Active

| Decision | State | Basis |
| --- | --- | --- |
| Execute 19.1 through 19.10 as sequential green PRs | Accepted | Operator instruction 2026-08-31 |
| Open the packet inside 19.1 and fold closeout into 19.10 | Accepted | Tracking policy and Phase 12–18 precedent |
| Add honesty only in 19.1 | Accepted | No premature spec, lock, dry-run, MCP, CI, or Hub |
| `veriformis.pipeline/v1` stays executable and byte-stable; project spec is additive | Accepted | L3; existing pipeline documents still run |
| PipelineService owns policy; CLI and MCP are adapters | Accepted | L4; ADR-0019 Decision A |
| Mapping in a spec is confirm-then-map with mapped_value | Accepted | L5; row-mapping v1 |
| Document-source, dataset-row, and mixed are the only compiler paths | Accepted | L6; ADR-0010 |
| Dry-run writes nothing; lockfile is not execute; loading a publication pin is not upload | Accepted | L7 |
| Default review_policy stays none; quality stays preview-only | Accepted | L8; Phase 13 and 14 closeouts |
| Export still shows bundle and receipt; no membership mutation; no trainer launch | Accepted | L9; verified-export v1 |
| Existing SFT, Phase 16, Phase 17, and Phase 18 parity goldens stay byte-identical | Accepted | L10 |
| ADR-0017 Decision A and ADR-0018 Decision A stand | Accepted | L11; no plugin loader; no generator |
| Network publication is absent from the default local path | Accepted | L12; operator approval as written |
| ADR-0020 Decision A: pin only; no Hub execute unless licensed before 19.7 | Accepted | L13; operator approval 2026-08-31 |
| Hosted training and family-to-trainer chrome stay out of scope | Accepted | L14 |
| Do not start Phase 20 from this packet | Accepted | L15; signed/notarized Mac remains Group 9 owner remainder |
| Skip package/package-verify MCP wraps with a record unless 19.5 audit requires them | Accepted | Operator Phase 19 plan |
| Skip Mac project-spec UI and GitHub xcodebuild | Accepted | Operator Phase 19 plan |
