# ADR-0015 — Collection Plan as Ingest Contract

**Status:** Accepted

**Date:** 2026-08-25

**Decider:** Independent-product Phase 11 opening; operator instruction to land
11.1–11.8 as one pull request

## Context and evidence

`parse` captured an explicit file list. `capture_source_batch` already pins a
source root, refuses child symlinks, and rejects duplicate locators. The Mac
workbench walked folders in Swift (`SourceDropView.expand`) with hidden-file
skipping and silent drops of unsupported suffixes. That walk was not a
versioned contract, not shared with CLI or MCP, and produced no
accepted/ignored/refused counts.

ADR-0008 already makes `input_family` the taxonomy axis for recovery. Phase 12
owns OCR. Zip is export transport, not source ingest.

## Decision

1. Collection membership is a first-class, surface-neutral contract
   (`veriformis.collection-plan/v1`). `PipelineService` owns the expander.
   CLI, MCP, and the Mac bridge are adapters.
2. Directories are legal `parse` / `preflight` / `collect` inputs. Expansion
   is deterministic: sorted unique logical paths, no symlink follow, hidden
   names ignored by default, package directories not recursed by default,
   unsupported suffixes counted and not parsed.
3. Limits (`max_files`, `max_bytes`, `max_visited`) fail closed. They do not
   truncate.
4. Duplicate bytes keep the first logical path and count later copies as
   `duplicate`.
5. Archive expansion as source ingest is not implemented in this phase. Zip
   remains `.vfbundle.zip` / `.vfexport.zip` transport.
6. New suffixes and families are not admitted without an ADR-0008 support-
   registry change, recovery contract, and fixtures. This packet does not
   implement EPUB, spreadsheets, presentations, email, notebooks, XML,
   subtitles, or extra code suffixes.
7. Parser process isolation is not added unless hardening evidence shows an
   in-process crash that fail-closed errors cannot contain.

## Consequences

- Dropping a folder in the Mac and passing that folder to CLI `parse` produce
  the same accepted members.
- Compile of an explicit file list remains valid.
- Image-only PDF remains `ocr-image` / Phase 12.

## Alternatives considered

- Documenting the Swift enumerator as the contract: rejected; dual policy
  drifts.
- Expanding archives by default: rejected; no retained ingest evidence.
- Guessing new suffixes from the roadmap candidate list: rejected;
  `corpus-demand-matrix.json` still ranks them unranked.

## Verification

Collection fixtures prove mixed-directory identity, symlink refusal, hidden
and unsupported counts, duplicate-byte handling, and limit failures. Golden
file-list compile still passes. Parser hardening fixtures fail closed.
Discovery does not name unimplemented families.

## Review triggers

Any new collection setting; archive ingest; parser subprocess isolation; a
new `input_family` or suffix; Phase 12 OCR.
