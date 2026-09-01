# Phase 20 Risk Register

**Status:** Open for Phase 20

| ID | State | Likelihood | Impact | Risk | Control |
| --- | --- | --- | --- | --- | --- |
| P20-R1 | Controlled for 20.1 | High | High | Packet opening implies a 1.0 version, signed Mac, or Hub path exists | Isolation tests and explicit non-claims |
| P20-R2 | Open | High | High | Support matrix weakly claims a candidate that did not pass its gate | L4; 20.2 names exclusions |
| P20-R3 | Open | High | High | Version or classifier changes before the evidence index is complete | L3; L14; 20.10 only |
| P20-R4 | Open | High | High | Public Mac readiness claimed without owner-signed notarized evidence | L5; 20.6 skip record |
| P20-R5 | Open | High | High | Hub execute, generator, or plugin loader appears | L6; L7; isolation names |
| P20-R6 | Open | Medium | High | Empty extras become required or profile failure blocks core | L8; 20.8 |
| P20-R7 | Open | Medium | High | Quality-report command or heuristic seal block appears | L9 |
| P20-R8 | Open | Medium | High | SFT or Phase 16–19 goldens change | L10; 20.10 digest replay |
| P20-R9 | Open | Medium | High | Golden path grows an Aptus requirement | L13; install-smoke and golden-compile |
| P20-R10 | Open | Low | High | GitHub xcodebuild or Swift policy appears | L11; L12 |
| P20-R11 | Open | Medium | High | Migration path for a supported prior version is missing | 20.3 completeness tests |
| P20-R12 | Controlled | Low | High | Phase 21 invented from this packet | L15 |
