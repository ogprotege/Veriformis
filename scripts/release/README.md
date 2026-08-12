# Release scripts (Group 9)

Operator entry points for automated public-release gates. Authoritative
procedure and owner-only Mac signing/notarization steps live in
[docs/release.md](../../docs/release.md).

| Script | Purpose |
| --- | --- |
| `check_local.sh` | Required standalone gates (lint, core pytest, clean-wheel golden proof) |
| `smoke_install.sh` | Build/install a wheel, prove package origin, and run standalone golden via its CLI |
| `golden_compile.sh` | Raw golden corpus → canonical seal → external-digest verify; no integration handoff |
| `aptus_integration.sh` | Optional, explicit Aptus descriptor construction and adapter self-conformance check |
| `record_clean_path_evidence.sh` | Retained standalone logs/digests for wheel + golden via installed CLI |
| `macos_package_local.sh` | Local unsigned macOS workbench archive dry-run |

```bash
# Prefer before every push:
bash scripts/release/check_local.sh

bash scripts/release/smoke_install.sh
bash scripts/release/golden_compile.sh
# Retain clean-path evidence pack (logs only):
bash scripts/release/record_clean_path_evidence.sh
# Optional adapter self-conformance; not a core release gate or live-version proof:
bash scripts/release/aptus_integration.sh
# macOS only, unsigned dry-run:
bash scripts/release/macos_package_local.sh
```

Tests marked `aptus_integration` are excluded from required pytest runs. The
optional script and optional CI job are independently invocable and do not
gate the standalone release path.

Limitations for any future beta cut: [docs/beta-limitations.md](../../docs/beta-limitations.md).
