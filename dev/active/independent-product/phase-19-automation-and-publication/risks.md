# Phase 19 Risk Register

**Status:** Open for Phase 19

| ID | State | Likelihood | Impact | Risk | Control |
| --- | --- | --- | --- | --- | --- |
| P19-R1 | Controlled for 19.1 | High | High | Packet opening implies a project spec, lockfile, dry-run, or Hub path exists | Isolation tests and explicit non-claims |
| P19-R2 | Open | High | High | Project spec smuggles mode/map/export into `pipeline/v1` | L3; additive spec in 19.2; unknown keys fail closed |
| P19-R3 | Open | High | High | Spec execute or dry-run writes a workspace, bundle, or destination | L7; 19.3 dry-run writes nothing |
| P19-R4 | Open | High | High | Unconfirmed mapping compiles from a spec | L5; confirm-then-map |
| P19-R5 | Open | Medium | High | Spec invents a fourth compiler path | L6; ADR-0010 closed vocabulary |
| P19-R6 | Open | High | High | MCP grows a Hub, quality-report, or plugin tool | L2; 19.5 audit; isolation names |
| P19-R7 | Open | High | High | Network publication becomes default compile/run/export | L12; ADR-0020 Decision A |
| P19-R8 | Open | High | High | Credentials land in workspaces, bundles, specs, locks, logs, or receipts | L12; 19.8 adversarial isolation |
| P19-R9 | Open | Medium | High | Retry/idempotency ships without an execute adapter | 19.9 skip unless Decision B |
| P19-R10 | Open | Medium | High | SFT, Phase 16, Phase 17, or Phase 18 goldens change | L10; 19.10 digest replay |
| P19-R11 | Open | Medium | High | Quality-report command or heuristic seal block appears | L8 |
| P19-R12 | Controlled | Low | High | Phase 20 starts from this packet | L15 |
