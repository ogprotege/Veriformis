# Clean-machine CLI evidence (Phase 20.5)

Retained 2026-09-01 from `scripts/release/record_clean_path_evidence.sh`.

Isolated wheel install of `veriformis-0.1.0-py3-none-any.whl`, then golden
compile through that installed CLI. The primary path contains no Aptus
distribution and no automatic handoff descriptor. Logs and digests only;
the wheel binary is not retained.

Rerun:

```bash
EVIDENCE_DIR=dev/active/independent-product/phase-20-stable-1.0/evidence/clean-machine-cli \
  bash scripts/release/record_clean_path_evidence.sh
```
