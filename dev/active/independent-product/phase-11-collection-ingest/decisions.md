# Phase 11 Decision Index

**Status:** Active

| Decision | State | Basis |
| --- | --- | --- |
| Items 11.1–11.8 land as one pull request | Accepted | Operator instruction 2026-08-25 |
| Collection lives in Python behind PipelineService | Accepted | ADR-0015 |
| CLI directories expand through the same plan as the Mac | Accepted | U1 |
| Hidden files default-exclude and are counted | Accepted | Matches prior Mac skip; now declared |
| Unsupported siblings are ignored and counted; `--unsupported refuse` fails the collection | Accepted | Fail closed without silent drop |
| Archive ingest skipped | Accepted | No retained zip-as-source evidence |
| Parser subprocess isolation skipped | Accepted | Hardening uses in-process named errors |
| No new input families this phase | Accepted | Corpus matrix still unranked |
| OCR remains Phase 12 | Accepted | ADR-0008 |
