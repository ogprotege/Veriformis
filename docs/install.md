# Install Veriformis (private beta / local use)

**Status:** Operator install guide for development alpha `0.1.0`  
**Last reviewed:** 2026-08-23 (independent-product Phase 8.2 admission pins)

This page is the **standard local install** path. It is separate from “I only
use `uv run` inside a checkout,” though that path remains valid for
contributors.

The Mac workbench does **not** reimplement the compiler. It shells to the
`veriformis` **CLI**. If the GUI compiled your encyclicals, the CLI ran under
the hood (usually via the repo’s `.venv` or `uv`).

---

## What you get

| Piece | Role |
| --- | --- |
| **`veriformis` CLI** | Real product: document-source `parse → … → seal` or dataset-row `parse --mode dataset-row` → `map` → … → seal / verify |
| **Mac workbench** (optional) | Thin GUI over that CLI |
| **Sealed `.vfbundle`** | Finished dataset product |
| **Generic export derivatives** | Verified split JSONL, canonical JSON, or compatible flat CSV; no trainer profile |
| **Existing-dataset import** | Confirmed mapping of JSONL, JSON, or compatible CSV rows; [mapping.md](mapping.md) |

There is not yet a notarized App Store–style installer. Private beta means:
install the CLI on your machine, optionally build/open the Debug app.

---

## Prerequisites

- macOS or Linux (CI proves Ubuntu + macOS Python)
- Python **3.11+**
- [uv](https://docs.astral.sh/uv/) (recommended) **or** pip + venv

```bash
# install uv if needed (example)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## Standard CLI install (recommended for operators)

### Option A — Install from a local checkout (private beta)

```bash
git clone https://github.com/ogprotege/Veriformis.git
cd Veriformis
uv sync
```

**Use without “installing” onto PATH:**

```bash
uv run veriformis version          # expect 0.1.0
uv run veriformis --help
```

**Put `veriformis` on your PATH for this checkout** (stable for Terminal and for
the GUI if you point at this binary):

```bash
# After uv sync — console script lives here:
ls .venv/bin/veriformis

# Optional: add to your shell profile for this machine only
export PATH="$PWD/.venv/bin:$PATH"
veriformis version
```

**Or install as a uv tool** (global-ish user tool entry; re-run after updates):

```bash
cd /path/to/Veriformis
uv tool install --editable .
veriformis version
```

### Option B — Editable pip install into a venv you control

```bash
cd /path/to/Veriformis
python3.12 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
veriformis version
```

---

## Mac workbench (GUI)

The app is still a **Debug build from the repo**, not a signed public installer.

**One command (preferred):**

```bash
cd /path/to/Veriformis
uv sync
./script/build_and_run.sh
```

That script:

1. Requires the installed `.venv/bin/veriformis` or an explicit `VERIFORMIS_CLI`
2. Builds the checked-in Xcode project into a deterministic DerivedData path
3. Opens it with `open --env` so the GUI finds the CLI (plain `export` + `open`
   does **not** pass env into GUI apps)

Use `--verify`, `--debug`, `--logs`, or `--telemetry` for the corresponding
development mode. `macos/scripts/run_workbench.sh` remains a compatibility
wrapper around the same entrypoint.

**Prerequisite for the GUI:** Xcode.

Details: [macos/README.md](../macos/README.md).

---

## CLI command map (the real surface)

All stage policy lives here. Full options: [cli.md](cli.md).

| Command | Purpose |
| --- | --- |
| `veriformis version` | Print package version |
| `veriformis taxonomy` | Print the implemented training taxonomy as read-only JSON |
| `veriformis goals` | Print the versioned goal catalog |
| `veriformis presets` | Print versioned recipe presets |
| `veriformis profile-admissions` | Print implemented TRL and MLX-LM admission pins |
| `veriformis columnar-schemas` | Print packaged Arrow and Hugging Face feature schema pins |
| `veriformis preflight PATH... --goal ID` | Raw-source compile admission without a workspace |
| `veriformis parse FILES… -o WORKSPACE [--source-root DIR]` | Capture + parse |
| `veriformis clean WORKSPACE` | Cleaning plan + apply |
| `veriformis chunk WORKSPACE` | Evidence-bearing chunks |
| `veriformis construct WORKSPACE --goal ID` | Build records from a catalog goal (or `--objective`) |
| `veriformis curate WORKSPACE` | Curation; omitted `--instruction` uses the catalog template |
| `veriformis goal-preview WORKSPACE` | Show rows and the exact supervised span |
| `veriformis split WORKSPACE` | Train / evaluation assignment |
| `veriformis format WORKSPACE` | Lower to product rows |
| `veriformis validate WORKSPACE` | 17-gate validation |
| `veriformis seal WORKSPACE -o BUNDLE.vfbundle` | Atomic canonical six-file bundle; no integration artifact by default |
| `veriformis verify BUNDLE [--manifest-sha256 HEX]` | Independent verify |
| `veriformis package BUNDLE -o BUNDLE.vfbundle.zip --manifest-sha256 HEX` | Deterministic Finder-safe transport |
| `veriformis package-verify ARCHIVE --manifest-sha256 HEX` | Verify transport bytes and reconstructed bundle |
| `veriformis package EXPORT -o EXPORT.vfexport.zip --export-receipt-sha256 HEX` | Deterministic receipt-anchored transport of an unchanged generic export directory |
| `veriformis package-verify ARCHIVE --export-receipt-sha256 HEX` | Verify receipt-bound export members and canonical transport bytes |
| `veriformis export discover` | List executable verified-export implementations; includes `constrained-csv`, `json`, and `split-jsonl-directory` v1 |
| `veriformis export dry-run --request-json JSON` | Derive a source-anchored plan plus exact first-row/non-empty-partition samples and normalized plan-derived tree, without renderer or destination access; whole payloads over 65,536 bytes or excluded by the response budget are omitted with an exact reason |
| `veriformis export inspect --request-json JSON` | Inspect a self-described export's closed physical tree |
| `veriformis export execute --request-json JSON` | Publish one operator-confirmed plan with no-replace `refuse` |
| `veriformis export-verify --request-json JSON` | Re-derive source authority and independently verify an export |
| `veriformis handoff BUNDLE --manifest-sha256 HEX` | Build/write Aptus handoff |
| `veriformis handoff-verify HANDOFF --bundle BUNDLE` | Consumer check |
| `veriformis list-recipes` | Named recipes |
| `veriformis run PIPELINE.yaml` | YAML pipeline |
| `veriformis mcp` | Local MCP adapter |
| `veriformis preview PATH` | Cleaning preview without commit |
| `veriformis upgrade-workspace WORKSPACE` | Migrate older workspace revisions |

### Choose a generic export container

Use the [Generic Export Operator Guide](generic-exports.md) to choose among
split JSONL, canonical JSON, and constrained CSV. The container encodes rows
whose training objective, semantic row schema, curation, and train/evaluation
membership are already fixed; it does not choose those semantics or prove
compatibility with a trainer. Phase 5.6's exact dry-run preview merged as PR #58
at `cd017941090c7352cb1d10f9a383042b954d4f2e`. The Phase 5.7 guide and Phase 5
closeout merged as PR #59 at `65cbd471e96d83f8dd65e2cda60e90f64a916e2b`.
Product maturity remains development alpha.

### Verified split JSONL derivative

`split-jsonl-directory` v1 is the first production generic export. A request-v1
dry run, execute, or source-bound verify uses these fixed defaults:

```json
{"evaluation_partition_name":"evaluation","include_provenance":true,"schema_version":"veriformis.split-jsonl-options/v1","train_partition_name":"train"}
```

The resulting closed derivative directory contains canonical payload-only
`data/train.jsonl` and `data/evaluation.jsonl`, deterministic `README.md` and
`metadata/dataset-card.json`, aligned
`metadata/row-provenance.jsonl`, and `export-receipt.json`. To use different
safe partition filename stems or omit the provenance sidecar, use
`veriformis.export-surface-request/v2` and provide the complete options object;
partial options are refused. These choices do not change row content, order,
curation, split policy, or train/evaluation membership. The container advertises
no trainer compatibility. See the [CLI reference](cli.md) and
[Split JSONL Export v1](contracts/split-jsonl-export-v1.md).

### Verified canonical JSON derivative

Canonical `json` v1 uses request v1 and publishes a fixed closed tree:

```text
README.md
dataset.json
export-receipt.json
metadata/row-provenance.json
```

`dataset.json` contains explicit schema/objective/loss/split metadata and
payload-only `train` and `evaluation` arrays. The mandatory provenance object
contains the complete aligned train-then-evaluation sequence. This selector has
no container options, so request v2 is refused. It preserves rows and logical
partitions and advertises no trainer compatibility. See
[Canonical JSON Export v1](contracts/canonical-json-export-v1.md).

### Verified constrained CSV derivative

`constrained-csv` v1 uses request v1 and publishes a fixed closed tree:

```text
README.md
data/evaluation.csv
data/train.csv
export-receipt.json
metadata/dataset-card.json
metadata/row-provenance.jsonl
```

The CSV is UTF-8 without a BOM. It quotes every header and field, uses commas,
doubles embedded quotes, and terminates every record with LF. Exact ordered
headers are `text`; `prompt,completion`; or `instruction,input,output` for the
three supported flat schemas. Embedded line endings, Unicode, and formula-like
strings are preserved exactly inside quotes. Provenance is mandatory and
aligned train then evaluation. The selector has no options and refuses request
v2 before source access. After source admission reveals nested `messages`, the
schema is refused before destination access with a split JSONL or canonical
JSON alternative. The container preserves rows and
logical partitions and advertises neither trainer nor spreadsheet
compatibility. See
[Constrained CSV Export v1](contracts/constrained-csv-export-v1.md).

### Minimal terminal compile (same path as the GUI)

```bash
# After install / uv sync:
veriformis parse document.md -o /tmp/ws --source-root /path/to/dir
veriformis clean /tmp/ws
veriformis chunk /tmp/ws
veriformis construct /tmp/ws --objective full_text
veriformis curate /tmp/ws --allow-empty-evaluation
veriformis split /tmp/ws
veriformis format /tmp/ws
veriformis validate /tmp/ws
veriformis seal /tmp/ws -o /tmp/out.vfbundle
MANIFEST_SHA256="$(shasum -a 256 /tmp/out.vfbundle/manifest.json | awk '{print $1}')"
veriformis verify /tmp/out.vfbundle --manifest-sha256 "$MANIFEST_SHA256"
veriformis package /tmp/out.vfbundle -o /tmp/out.vfbundle.zip \
  --manifest-sha256 "$MANIFEST_SHA256"
veriformis package-verify /tmp/out.vfbundle.zip \
  --manifest-sha256 "$MANIFEST_SHA256"
```

### Goal-first walkthrough (pick → preflight → compile → preview → export)

This is the documented non-developer walkthrough for usability criterion U6.
Use two independent sources so the default split keeps a non-empty
evaluation partition. The Mac workbench follows the same sequence: pick a
goal, run preflight, compile, inspect the preview, then dry-run an export.

```bash
mkdir -p /tmp/vf-demo
cat > /tmp/vf-demo/alpha.txt <<'EOF'
Alpha opening is long enough to split into context and target. The remainder stays in this same independent source.

Alpha second paragraph keeps the leakage groups distinct.
EOF
cat > /tmp/vf-demo/beta.txt <<'EOF'
Beta opening is long enough to split into context and target. The remainder stays in this same independent source.

Beta second paragraph keeps the leakage groups distinct.
EOF

veriformis goals
veriformis preflight /tmp/vf-demo/alpha.txt /tmp/vf-demo/beta.txt \
  --source-root /tmp/vf-demo --goal continue-a-passage
veriformis parse /tmp/vf-demo/alpha.txt /tmp/vf-demo/beta.txt \
  -o /tmp/vf-ws --source-root /tmp/vf-demo
veriformis clean /tmp/vf-ws
veriformis chunk /tmp/vf-ws --preset continue-a-passage.safe
veriformis construct /tmp/vf-ws --goal continue-a-passage --preset continue-a-passage.safe
veriformis curate /tmp/vf-ws --preset continue-a-passage.safe
veriformis split /tmp/vf-ws
veriformis format /tmp/vf-ws
veriformis validate /tmp/vf-ws
veriformis seal /tmp/vf-ws -o /tmp/out.vfbundle
veriformis goal-preview /tmp/vf-ws
MANIFEST_SHA256="$(sha256sum /tmp/out.vfbundle/manifest.json | awk '{print $1}')"
veriformis verify /tmp/out.vfbundle --manifest-sha256 "$MANIFEST_SHA256"
```

Omitted `--instruction` on instruction-and-output uses the catalog template
after the truthfulness check. To inspect a generic export without writing a
destination, use `veriformis export dry-run --request-json` as described in
the [CLI reference](cli.md) and the
[Generic Export Operator Guide](generic-exports.md).

Optional Aptus adapter use is explicit: pass `--aptus-handoff` to `seal`, or
run `handoff` after retaining the manifest digest. The adapter's current policy
accepts the supervised row schemas `prompt_completion`, `instruction_output`,
and `messages`, and rejects the `text` row schema required by the `full_text`
objective; this does not constrain standalone Veriformis output.

---

## How the GUI related to “I never installed the CLI”

If you used `./script/build_and_run.sh` (or the compatibility wrapper, or a
Debug build from this repo after `uv sync`):

1. `uv sync` created `.venv/bin/veriformis`
2. The app was pointed at that binary (or `uv run … veriformis`)
3. Every stage chip ran a real CLI command

So you **did** use the CLI bundle — through the workbench — without a global
`pip install` or a notarized app.

A future **public** Mac installer (signed/notarized) is separate (Group 9 owner
checklist). Private beta standard install = **CLI on the machine + optional
Debug workbench**.

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| GUI: could not locate CLI | `uv sync`, then `./script/build_and_run.sh` |
| `veriformis: command not found` | Use `uv run veriformis` or put `.venv/bin` on PATH / `uv tool install` |
| `source root is not a directory` | Pass a directory to `--source-root`, not a file (fixed in recent workbench) |
| Optional Aptus handoff rejected for `full_text` | Expected under the adapter policy: plain `text` schema; use a supported supervised objective only when that integration is your target |

---

## Related

- [CLI reference](cli.md)
- [macOS workbench](../macos/README.md)
- [Beta limitations](beta-limitations.md)
- [Private beta workbench plan](plans/2026-08-06-private-beta-workbench.md)
- [Release guide](release.md) (public Mac packaging)
