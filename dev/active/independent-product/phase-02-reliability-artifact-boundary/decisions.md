# Phase 2 Decision Index

**Status:** Active

| Decision | State | Basis |
| --- | --- | --- |
| Preserve strict `minimal-v1` directory verification | Accepted | Finished Dataset Contract v1 and retained Finder mutation evidence |
| Never special-case or ignore `.DS_Store` inside a canonical bundle | Accepted | Closed-set verification is an integrity boundary |
| Process work and pipe draining must not run on the main actor | Accepted | Source-verified synchronous wait in an inherited main-actor task |
| Cancellation must terminate the active child and leave an auditable receipt | Accepted | Phase 2 roadmap exit gate |
| Finder-safe distribution form | Accepted | ADR 0005 selects deterministic `.vfbundle.zip`; registered package presentation remains mutable and Mac-specific |

No new data format or trainer compatibility claim is authorized by this phase.
