# Phase 12 Execution Plan

**Status:** In progress

**Last updated:** 2026-08-25

**Authority:** [Independent Product Roadmap](../../../../docs/plans/2026-08-11-veriformis-independent-product-roadmap.md) Phase 12; [program.json](../program.json); [ADR-0008](../../../../docs/adr/0008-input-family-taxonomy-axis.md); [ADR-0015](../../../../docs/adr/0015-collection-plan-as-ingest-contract.md).

**Predecessor:** Phase 11 closeout merged as PR #104 at
`e856af96043c9876affa275b5246e83541254d9d`. Clean local `main` equals
`origin/main` there.

Each numbered work item is one sequential pull request on branch
`phase12/0N-<slug>` titled `Phase 12.N: <imperative>`. A pull request must
pass its focused and required repository gates, pass every GitHub check,
merge, and leave clean local `main` equal to `origin/main` before the next
item begins. The repository is public; sequential PRs are the operator
instruction of 2026-08-25.

Items 12.3–12.8 may begin only after item 12.2's evaluation and an
owner-approved OCR ADR, or after the operator defers the phase under item
12.2. Closeout is folded into 12.8 if the ADR is accepted. If the phase is
deferred, 12.2 records the deferral and 12.3–12.8 do not start.

## Goal

Recover image-only and mixed PDFs without weakening source evidence, and
without pulling OCR libraries into the core install.

## Architecture

`PipelineService` remains the composition root. Digitally born PDF recovery
stays `pypdfium2` text-layer extraction. OCR, if later admitted, is an
optional recovery path under an isolated extra, bound to engine, model,
language, version, page/image digests, and coordinates. Collection ingest
from Phase 11 does not change suffix dispatch.

## Standing constraints

- Core install, compile, seal, generic export, consumer profiles, and core
  pytest never import an OCR engine.
- Never silently replace recoverable digital text with OCR.
- No cloud OCR. No network model download during parse.
- No handwriting guarantee. No claim of perfect OCR.
- `ocr-image` stays `explicitly_unsupported` until an accepted ADR promotes
  it.
- There is no `ocr` extra until item 12.7, and only if the ADR is accepted.
- Python / CLI / MCP / Mac bridge agree on parser identity.
- Do not start Phase 13 from this packet.

## Key decisions (lock at 12.1)

| Decision | Recommendation | Why |
| --- | --- | --- |
| Sequential PRs | 12.1 then 12.2, then stop. 12.3–12.8 only after ADR or deferral. | Operator instruction 2026-08-25; repo is public. |
| Packet first | 12.1 opens tracking and proves OCR is still refused. | Same honesty pattern as Phase 8.1 / 10.1. |
| Evaluation before ADR | 12.2 records engines on a license-safe corpus. The operator selects or defers. | Roadmap items 1–2; do not ship an engine by assertion. |
| No extra in 12.1 | Do not declare `ocr = []` yet. | Declaring the extra implies a later pin. 12.7 owns isolation after ADR. |
| Digital text first | Empty-text PDF still refuses. Digitally born PDF still extracts the text layer. | ADR-0008; existing `pdf.ocr-required`. |

## Likely files (created across the phase)

- Create: `dev/active/independent-product/phase-12-optional-ocr/` packet (12.1)
- Create later, only if ADR accepted: OCR ADR, parser path, provenance
  contract, `ocr` extra, review hooks, fixtures
- Do not modify in 12.1: production PDF parser behavior, taxonomy implemented
  lists, extras, collection plan, consumer profiles

---

## Checklist

### 12.1 Open the OCR packet

**Branch:** `phase12/01-ocr-packet`
**Title:** `Phase 12.1: Open the OCR packet`

- [x] Confirm the predecessor gate: Phase 11 completed, `HEAD == origin/main`.
- [x] Create the standard Phase 12 packet. Mark Phase 12 `in_progress` in
      `program.json`. Reconcile active tracking documents. Cite the Phase 11
      closeout merge.
- [x] Keep `ocr-image` explicitly unsupported. Discovery must not list it as
      implemented.
- [x] Prove empty-text PDF still refuses with `pdf.ocr-required` and
      limitation `ocr-unsupported`. Digitally born PDF still extracts its
      text layer.
- [x] Prove `pyproject.toml` has no `ocr` extra and the lock does not name
      OCR engine packages.
- [x] Record focused, tracking, lint, lock, and diff evidence. Do not claim
      OCR support.

### 12.2 Evaluate candidate local OCR engines

**Branch:** `phase12/02-ocr-engine-evaluation`
**Title:** `Phase 12.2: Evaluate candidate local OCR engines`

- [x] Compare candidate local OCR engines on a retained, license-safe corpus
      covering languages, scans, mixed text/images, rotation, tables,
      handwriting exclusions, and degraded pages.
- [x] Record accuracy proxies, runtime, memory, platform support, model size,
      licensing, and offline behavior.
- [x] Do not add an `ocr` extra, do not change taxonomy state, and do not
      emit OCR text as source recovery.
- [x] Stop for the operator to accept an OCR ADR or defer the phase. Do not
      start items 12.3–12.8 from this item.

### 12.3 Record the OCR ADR and recovery identities

**Branch:** `phase12/03-ocr-adr-identities`
**Title:** `Phase 12.3: Record the OCR ADR and recovery identities`

- [x] Operator accepted Tesseract 5. ADR-0016 and
      `veriformis.ocr-recovery-identity/v1` pin engine, tessdata, page
      digest, coordinates, confidence, preprocess, and limitations.
      Recovery is not executable. `ocr-image` stays unsupported.

### 12.4 Distinguish digital, OCR, and merged recovery

**Branch:** `phase12/04-recovery-paths`
**Title:** `Phase 12.4: Distinguish digital, OCR, and merged recovery`

- [x] Classify digital, OCR, and merged pages. Digital text is never
      sent to an OCR provider. Default parse still refuses image-only
      PDFs. `ocr-image` stays unsupported.

### 12.5 Add confidence thresholds

**Branch:** `phase12/05-confidence-thresholds`
**Title:** `Phase 12.5: Add confidence thresholds`

- [x] Confidence policy v1: warn / review / refuse. Refused OCR text is
      omitted from the stream and retained on `held_text`.

### 12.6 Add page previews and review hooks

**Branch:** `phase12/06-preview-review-hooks`
**Title:** `Phase 12.6: Add page previews and review hooks`

- [x] Read-only `ocr-preview` on PipelineService, CLI, and MCP. Pending
      review is a page flag. Sources are not mutated.

### 12.7 Isolate the OCR extra

**Branch:** `phase12/07-ocr-extra`
**Title:** `Phase 12.7: Isolate the OCR extra`

- [ ] Extra `ocr`; core install unchanged.

### 12.8 Prove no-network recovery and close Phase 12

**Branch:** `phase12/08-ocr-harness-closeout`
**Title:** `Phase 12.8: Prove no-network recovery and close Phase 12`

- [ ] No-network, missing model, multilingual, corrupt image,
      resource-limit, and provenance-replay tests. Closeout. Do not start
      Phase 13.

## Usability criteria

| ID | Criterion |
| --- | --- |
| U1 | Discovery does not imply implemented OCR until an accepted ADR promotes `ocr-image`. |
| U2 | Empty-text and image-only PDFs refuse in Veriformis as `pdf.ocr-required` until a later item emits OCR. |
| U3 | Digitally born PDF text is not replaced by OCR. |
| U4 | Core pytest passes without an OCR extra or OCR engine import. |
| U5 | Python, CLI, and MCP agree on parser identity and limitation names. |
| U6 | Cloud OCR and network model fetch during parse are absent. |
| U7 | Handwriting is excluded or explicitly limited; it is not guaranteed. |

## Exit gate

The retained OCR corpus meets thresholds chosen and recorded before final
implementation acceptance; every emitted character is marked by recovery
path and page evidence; low-quality cases warn or fail according to policy.
If item 12.2 defers the phase, the exit is the recorded deferral with
`ocr-image` still unsupported.

**Result:** Pending item 12.1. See [closeout.md](closeout.md).
