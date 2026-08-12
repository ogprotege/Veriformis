# Phase 2 Risk Register

**Last reviewed:** 2026-08-11

| ID | State | Likelihood | Impact | Risk | Control / evidence |
| --- | --- | --- | --- | --- | --- |
| P2-R1 | Mitigated | High | High | Main-actor process waiting freezes progress and cancellation UI. | Async runner and main-actor responsiveness tests pass |
| P2-R2 | Mitigated | Medium | High | Child stdout/stderr fills a pipe and deadlocks. | Concurrent drain and 10,000-line dual-stream fixture pass |
| P2-R3 | Mitigated | Medium | High | Cancellation leaves an orphaned process. | Every stage, TERM, bounded grace, KILL, PID, quit, and recovery tests pass |
| P2-R4 | Mitigated | Medium | High | Unbounded output exhausts app memory. | Per-process retained bytes and UI lines are bounded with truncation evidence |
| P2-R5 | Mitigated | Medium | High | Invalid UTF-8 silently disappears or crashes display. | Stable lossy replacement regression passes |
| P2-R6 | Mitigated | High | High | Finder mutates a browsable directory bundle. | Strict failure retained; ADR 0005 immutable transport implemented |
| P2-R7 | Mitigated | Medium | High | A transport extractor permits traversal, links, or duplicate paths. | Fixed destinations plus adversarial Mac/Linux tests pass |
| P2-R8 | Mitigated | Medium | Medium | Copy/reveal UI mutates or opens the canonical bundle contents. | Workbench reveals verified transport archive, not canonical directory |
