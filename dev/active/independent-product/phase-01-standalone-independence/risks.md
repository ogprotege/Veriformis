# Phase 1 Risk Register

**Last reviewed:** 2026-08-11

| ID | State | Likelihood | Impact | Risk | Control / evidence |
| --- | --- | --- | --- | --- | --- |
| P1-R1 | Mitigated | Medium | High | Changing only the CLI default silently breaks workbench opt-in. | Workbench emits `--aptus-handoff` only on explicit opt-in; Swift regression passed |
| P1-R2 | Mitigated | Medium | High | Old history entries continue opting in through `?? true`. | Missing-field fallback is false; explicit true round-trip regression passed |
| P1-R3 | Mitigated | Medium | High | Aptus remains a hidden import/startup dependency. | Lazy imports plus fresh-subprocess import-isolation regression passed |
| P1-R4 | Mitigated | Medium | High | Core CI still blocks on optional Aptus tests or artifacts. | Core ignores adapter-only collection and excludes marker; standalone scripts and separate non-blocking job are regression-locked |
| P1-R5 | Mitigated | Medium | High | Clean-install smoke proves only `--help`, not compilation. | Isolated installed-wheel module path/dependencies and both full golden compiles passed |
| P1-R6 | Mitigated | Low | High | Renaming the legacy validation gate invalidates persisted identities. | Phase preserved `aptus-row-shape`; versioned migration debt is recorded as DOC-007 |
| P1-R7 | Mitigated | Medium | Medium | Descriptor self-tests are overstated as live Aptus compatibility. | Active docs and scripts limit claim to adapter self-conformance absent named external evidence |
| P1-R8 | Mitigated | Medium | High | Workbench launch evidence proves a process but not CLI resolution. | Bridge-resolution tests plus explicit Veriformis 0.1.0 CLI build/launch smoke passed |
