# Phase 9 Decision Index

**Status:** Active

| Decision | State | Basis |
| --- | --- | --- |
| Phase 9 executes as eight sequential green pull requests, with packet opening folded into 9.1 and closeout into 9.8 | Accepted | Phase 6, 7, and 8 precedent |
| Columnar containers are generic exports with `consumer_id` null | Accepted | ADR-0013 |
| `parquet` refuses naming item 9.4; `arrow` refuses naming item 9.5; `hugging-face-dataset` refuses naming item 9.6 | Accepted | Same honesty pattern as Phase 8.1 |
| Extra `columnar` is an empty list in 9.1; version ranges live in later pins | Accepted | Keep `uv lock` free of PyArrow and datasets |
| Arrow/feature pins are packaged JSON with `utf8`/`value` strings, nested messages as list of struct `role` then `content`, all non-null | Accepted | Item 9.2; product payload order |
| `datasets >=3.0.0,<6.0.0` and `pyarrow >=19.0.0,<26.0.0` live in the pin catalog, not the core lock | Accepted | Item 9.2; official docs reviewed 2026-08-23 |
| Columnar v1 fingerprint is `semantic_content_only` over ordered payloads; container id is excluded so the three containers share identity; receipts still bind exact emitted bytes | Accepted | Item 9.3; ADR-0013; usability U7 |
| Semantic fingerprint is cross-version identity; receipt SHA-256 is this-run exact bytes | Accepted | Roadmap item 5; ADR-0013 |
| Hub upload is out of scope | Accepted | Roadmap Phase 9 non-goal |
| Optional CI installs pin-range wheels with `uv run --with`; extra `columnar` stays empty | Accepted | Item 9.8; keep `uv lock` free of PyArrow |
| Taxonomy promotion of the three containers lands in closeout, not in the first emission item | Accepted | Phase 8.3–8.7 pattern |
| JSONL versus columnar size notes cite the measured fixture only | Accepted | Roadmap item 8; risk P9-R6 |
