# tunerepo Salvage Manifest

Extracted from `/Users/biscuit/tunerepo` (ToolRepo.ai) on 2026-07-28 before the repo was wiped.
The original repo's git history remains in `/Users/biscuit/tunerepo/.git` (restore with `git checkout -- .`
from that directory), and a full local backup also exists per the owner.

This staging folder holds everything worth carrying into the new dataset-preparation tool
(working name TBD). Nothing else in tunerepo had salvage value.

## engine/

### `udp-processor-flow.ts` (343 lines, TypeScript)
The only substantial engineering in tunerepo. Pure-function document-preparation pipeline:
- `cleanText()` — 8 regex-based cleaning options (headers/footers, page numbers, whitespace,
  special chars, lowercase, URLs, emails) + user-supplied custom regex patterns
- `chunkText()` — 5 strategies: fixed, sentence, paragraph, sliding window, "semantic"
- `formatOutput()` — jsonl / csv / text / markdown serialization
- Statistics (original/processed length, chunk count, removed chars, timing)

Use it as the **reference spec** for the cleaning/chunking taxonomy when writing the new
Python engine. Do NOT port it verbatim — known defects to fix on the way in:
1. `removePageNumbers` regex `/\b\d+\s*(?:of\s*\d+)?\b/gi` deletes **every standalone number**
   in the document (destructive data loss — exactly what the new tool must never do silently).
2. Sliding-window chunking drops the tail and produces zero chunks when `text.length < chunkSize`.
3. "Semantic" chunking is just paragraph grouping — rename honestly or implement for real.
4. Language detection counts 8 common English words; keyword extraction is naive frequency.
   Either do these properly or cut them from v1.

### `document-cleaning.md` (12KB)
Premade doc describing the UDP cleaning taxonomy. Useful when writing the new tool's
cleaning-rule documentation.

## ux-reference/

### `udp-playground-page.tsx` (632 lines) + `udp-playground-actions.ts`
The one interactive workbench UI tunerepo shipped: file upload, cleaning-option toggles,
chunking-strategy form, live statistics panel, chunk list, download. Keep as **UX reference
only** for the new Mac GUI's dataset-prep screen. (Note: this file is also a cautionary
artifact — it imports a non-existent `AlertDescriptionTitle` and renders `<Alert>` without
importing it, crashing on every error path.)

## docs-history/

### `blueprint.md`
The original Firebase-Studio product vision for ToolRepo.ai (5-tool ML ecosystem).
Historical context only.

### `hypertune-mcp-guide.json` (92KB)
Complete spec for a HyperTune MCP server (model DB scraper, FastAPI server, CLI, deployment).
Superseded in substance by Aptus, which implements the planner for real. Retained as product
history; its one still-live idea — an MCP surface — is already proven viable in the owner's
prior internal tooling.
