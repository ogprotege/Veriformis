# Phase 18 Decision Index

**Status:** Active

| Decision | State | Basis |
| --- | --- | --- |
| Execute 18.1 through 18.10 as sequential green PRs | Accepted | Operator instruction 2026-08-28 |
| Open the packet inside 18.1 and fold closeout into 18.10 | Accepted | Tracking policy and Phase 12–17 precedent |
| Add honesty only in 18.1 | Accepted | No premature screen, mode, or CLI wrap |
| Swift is a thin CLI adapter; PipelineService owns policy | Accepted | Roadmap ordering rule 11 |
| Expose only capabilities already owned by shared services | Accepted | Phase 18 next_gate |
| Workbench success is seal + verify, not a trainer handoff | Accepted | Product contract; Aptus optional |
| Document-source, dataset-row, and mixed are the only compiler paths | Accepted | ADR-0010 |
| Mapping is confirm-then-map with mapped_value | Accepted | Row-mapping v1 |
| Default review_policy stays none | Accepted | Phase 14 closeout |
| Quality stays preview-only | Accepted | Phase 13 closeout |
| Export always shows the source bundle and receipt | Accepted | Verified-export v1 |
| Existing SFT, Phase 16, and Phase 17 goldens stay byte-identical | Accepted | Phase 18 exit evidence |
| ADR-0017 Decision A and ADR-0018 Decision A stand | Accepted | No plugin UI; no generator UI |
| Phase 17 families appear only through dataset-row mapping | Accepted | Phase 17 closeout; no family-to-trainer chrome |
| Accessibility and keyboard required for new screens; skip virtualization and full localization with records | Accepted | Operator Phase 18 plan |
| Do not start Phase 19 from this packet | Accepted | Signed/notarized Mac remains Group 9 owner remainder |
| Pin `veriformis.workbench-adapter/v1` as a schema-only contract in 18.2 | Accepted | Loading a pin is not a screen; ADR-0019 Decision A |
| Goal-first Home/Compile copy; Aptus optional Integrations | Accepted | Item 18.3; no required trainer |
| Mode picker uses ADR-0010 identifiers; confirm-then-map; family goals only after confirmed mapping | Accepted | Item 18.4; no auto-confirm; no family-to-trainer |
