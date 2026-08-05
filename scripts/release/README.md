# Release scripts (Group 9)

Operator entry points for automated public-release gates. Authoritative
procedure and owner-only Mac signing/notarization steps live in
[docs/release.md](../../docs/release.md).

| Script | Purpose |
| --- | --- |
| `check_local.sh` | Local parity with automated gates (lint, pytest, smoke, golden) |
| `smoke_install.sh` | Build wheel, install into a clean venv, smoke the CLI |
| `golden_compile.sh` | Golden corpus → seal → external_digest verify → handoff-verify |
| `macos_package_local.sh` | Local unsigned macOS workbench archive dry-run |

```bash
# Prefer before every push:
bash scripts/release/check_local.sh

bash scripts/release/smoke_install.sh
bash scripts/release/golden_compile.sh
# macOS only, unsigned dry-run:
bash scripts/release/macos_package_local.sh
```
