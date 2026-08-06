# Clean-path evidence packs

Operator evidence for beta P0.3: wheel install **outside** the repo `.venv`,
then golden corpus compile using the installed `veriformis` CLI
(`VERIFORMIS_USE_PATH=1`).

## Produce a new pack

```bash
bash scripts/release/record_clean_path_evidence.sh
# or:
EVIDENCE_STAMP=my-label SMOKE_PYTHON=3.12 bash scripts/release/record_clean_path_evidence.sh
```

Only logs and digests are written (no wheel binary in-tree).

## Packs

| Directory | Host | Git HEAD | Result |
| --- | --- | --- | --- |
| `20260805T-local-mac/` | macOS arm64 Darwin 25.6, Python 3.12.13 | `452b6e5` (main after PR #15) | PASS |

CI also runs `install-smoke` and `golden-compile` on Ubuntu for every PR/main push;
those jobs are complementary machine evidence without a committed log tree.
