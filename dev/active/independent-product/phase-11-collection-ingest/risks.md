# Phase 11 Risk Register

**Status:** Open

| ID | State | Likelihood | Impact | Risk | Control |
| --- | --- | --- | --- | --- | --- |
| P11-R1 | Controlled | High | High | Mac and CLI collect different members | Shared PipelineService expander; Swift walk removed |
| P11-R2 | Controlled | High | High | `parse /` eats the disk | Finite max_files / max_bytes / max_visited; fail closed |
| P11-R3 | Controlled | Medium | High | Symlink escape | lstat; refuse symlink members; capture still O_NOFOLLOW |
| P11-R4 | Controlled | Medium | High | Archive zip-slip as ingest | Archive expansion not implemented |
| P11-R5 | Controlled | Medium | Medium | Discovery names EPUB/xlsx | No taxonomy change; skip record |
| P11-R6 | Controlled | Low | High | OCR claimed | Image-only PDF still refused |
| P11-R7 | Open | Low | Medium | Parser native crash | 11.6 skip; revisit if CI shows process death |
