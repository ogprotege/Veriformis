# Phase 7 Decision Index

**Status:** Active

| Decision | State | Basis |
| --- | --- | --- |
| Phase 7 executes as ten sequential green pull requests matching roadmap items 1–10, with packet opening folded into 7.1 and closeout into 7.10 | Accepted | Phase 5 and Phase 6 precedent |
| Input mode is a compiler path (`document-source`, `dataset-row`, `mixed`), not an eighth taxonomy axis | Accepted | ADR-0010 |
| `document-source` remains the default compiler path; suffix must not select import | Accepted | Backward-compatible compiles |
| `dataset-row` is executable for JSONL from item 7.3; `mixed` refuses until 7.7 | Accepted | Mapping execution and workspace revision v4 |
| Imported rows are `imported-record/v1`, not widened `dataset-record/v1`; format emits ordinary `ProductRow` v1 | Accepted | ADR-0011 |
| Dataset-row workspaces use revision schema 4 (`parse → map → curate → split → format → validate → seal`) and reject `clean` / `chunk` / `construct` | Accepted | Distinct compiler path; no invented chunks |
| Dataset-row capture will not reuse `parsers/structured.py` | Accepted | Phase 5.3 refused that parser as round-trip evidence |
| Usability criteria U1–U7 are predeclared in `plan.md` before mapper UI exists | Accepted | Roadmap usability layer |
