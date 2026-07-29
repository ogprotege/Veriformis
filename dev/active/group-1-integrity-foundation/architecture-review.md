# Group 1 Integrity Foundation Architecture Review

Last Updated: 2026-07-29

## Executive Summary

Group 1 is architecturally sound for its declared Steps 1 through 6. No
unresolved Critical or High-severity findings remain.

The implementation now preserves a continuous, fail-closed chain from captured
raw bytes through deterministic parsing, canonical IR, diagnostics, immutable
source evidence, transactional revisions, replayable cleaning plans, and
evidence-bearing chunks. The final corrective pass also closed stage input
self-cycles, forged stage configuration, invalid child-to-parent history
transitions, unreferenced artifact insertion, cleaning identity forgery, source
locator ambiguity, incomplete object verification, and post-commit durability
ambiguity.

The current local closeout gate passes:

- `uv run pytest -q`: 320 passed, 8 expected failures.
- `uv run ruff check src tests`: passed.
- `uv lock --check`: passed.
- `git diff --check`: passed.

The eight expected failures are assigned to later roadmap Steps 8, 10, 13, 14,
15, and 16. None represents unfinished Group 1 behavior.

Two Important architecture deferrals remain. They concern large-corpus
operation and future implementation-version compatibility. Neither invalidates
the present Group 1 integrity contract, but both should be addressed before
Veriformis processes large production corpora or changes a persisted parser,
rule, or chunker implementation.

## Critical Issues (must fix)

None.

No unresolved Critical or High-severity issue remains in the Group 1 scope. The
final adversarial review specifically rechecked exact stage dependencies,
source and artifact lineage, revision ancestry and legal transitions, durable
identity reconstruction, parser replay, cleaning-plan replay, diagnostics,
evidence reconstruction, and atomic commit behavior.

## Important Improvements (should fix)

### 1. Bound memory use and deduplicate integrity work for large corpora

**Evidence:** The parse command currently reads every input into `captured` and
retains every parse result before opening its transaction
(`src/veriformis/cli.py:544-552`). Downstream loaders recursively reload and
replay prior stages (`src/veriformis/cli.py:188-486`). `Workspace.head()` also
walks the complete history by default, and history verification hashes every
artifact in every visited revision (`src/veriformis/workspace.py:1237-1274` and
`src/veriformis/workspace.py:1349-1365`). Shared artifacts can therefore be read
and hashed repeatedly during one command and again across historical revisions.

**Impact:** Correctness remains intact, but memory and I/O grow poorly with raw
corpus size, artifact size, and revision count. Group 2 will add more constructed
objects, which will amplify this cost.

**Recommendation:** Introduce a per-command validated snapshot context that
deduplicates object verification and parsed artifact loading by immutable ID.
Stream raw capture and parsing one source at a time into transaction storage
instead of retaining the entire corpus in memory. Add corpus-size benchmarks
and memory ceilings before advertising large-corpus support. This internal
context can later become part of the planned `PipelineService` without moving
the complete Step 17 surface forward.

### 2. Make deterministic replay version-addressable before implementations change

**Evidence:** Persisted sources and artifacts record parser and producer
versions, but replay dispatch selects the currently installed parser from the
file suffix (`src/veriformis/parsers/dispatch.py:31-79`). Cleaning and chunk
replay likewise resolve the currently installed rule and strategy registries
(`src/veriformis/rules/library.py:74-82` and
`src/veriformis/chunkers/pipeline.py:30-91`). There is no registry of historical
implementations and no explicit workspace migration path yet.

**Impact:** The current version fails closed and is reproducible. A future
behavior-changing parser, cleaner, or chunker release could make an older
workspace impossible to replay or extend even though its recorded artifacts
remain valid.

**Recommendation:** Resolve replay by `(producer_id, producer_version)` and keep
the required historical implementation available, or define a versioned,
explicit migration that creates a new revision while retaining the old one.
Add old-workspace compatibility fixtures before changing any persisted producer
behavior.

## Minor Suggestions

### Adopt a formatting baseline deliberately

`ruff format --check src tests` is not a current project gate and reports 36
files that would be reformatted. If automatic formatting is desired, land one
separate mechanical baseline change, then add the check to CI. Keeping it
separate will preserve readable history for the Group 1 implementation.

### Expand the supported-version CI matrix at the release gate

The package declares Python 3.11 and 3.12 support, while current CI runs Ubuntu
with Python 3.12 only (`.github/workflows/ci.yml:5-13`). Add Python 3.11 and
supported macOS verification when implementing roadmap Step 26. This is a
release-readiness item, not a Group 1 correctness blocker.

## Architecture Considerations

Group 2 must continue the product as a compiler from raw material to finished
datasets. Canonical text and cleaned IR are intermediate states, not the final
product. Training objectives, recipes, construction passes, candidate records,
accepted immutable records, and every rejection decision should remain explicit
and versioned.

Current evidence proves canonical visible text. IR-only metadata still needs
field-level evidence before any `structured_field` constructor is enabled, as
already recorded in `docs/development.md:119-122` and the Group 2 exit gate in
`docs/plans/2026-07-29-veriformis-roadmap.md:84-93`.

The validated snapshot context proposed above should remain surface-neutral.
CLI, future MCP, and future SwiftUI adapters should call the same orchestration
and must not reimplement identity, replay, validation, or sealing policy.

## Next Steps

1. Publish Group 1 with the current green gate and this review attached to the
   implementation record.
2. Track the two Important deferrals as explicit engineering work. Complete the
   version-addressed replay path before changing persisted producer behavior.
   Complete bounded-memory and deduplicated snapshot work before claiming
   large-corpus readiness.
3. Begin Group 2 in roadmap order: training objectives and recipes, construction
   passes with field evidence, candidate and record lifecycle, then deterministic
   constructors.
4. Preserve the Group 1 raw-byte, identity, transactional, diagnostics,
   evidence, and replay contracts as non-negotiable acceptance gates for every
   later group.
