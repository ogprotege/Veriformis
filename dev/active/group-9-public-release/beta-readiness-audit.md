# Veriformis Beta Readiness Audit

**Date:** 2026-08-05  
**Scope:** Honest gap list for a **flawless beta** (not public production).  
**Baseline:** Groups 1–7 on `main`; Group 9 automated gates on PR #14 (+ follow-up harden).  
**Policy:** Do not publish until this list is closed or explicitly accepted as beta limitations.

## Verdict (current)

| Claim | Status |
| --- | --- |
| Development alpha with strong core pipeline | **Yes** (local suite green) |
| Automated install + golden compile evidence | **In progress** (scripts + CI; must be green on GitHub) |
| Beta-ready product | **No** |
| Public-ready product | **No** |

**Recommended maturity label until gates close:** `0.1.0` development alpha.  
**Do not rebrand to beta** until P0 items below are closed.

---

## Severity key

- **P0** — Blocks any beta label (correctness, honesty, or install path).
- **P1** — Blocks a *comfortable* beta (operator confidence, polish, evidence).
- **P2** — Nice for beta quality; acceptable as known limitation if documented.
- **P3** — Post-beta / public production.

---

## P0 — Must close before “beta”

| # | Gap | Evidence / why | Suggested fix |
| --- | --- | --- | --- |
| P0.1 | **GitHub CI must be green** on the release branch | PR #14 failed all matrix cells on Ruff F401 (`pytest` unused in Group 9 tests). Local green ≠ remote green. | Fix lint; re-run; require green `test` + `install-smoke` + `golden-compile` before merge. |
| P0.2 | **Known limitations must be explicit for beta** | OCR unsupported; Aptus rejects plain `text` / `full_text` handoff; offline-only; no multi-user/cloud; Mac workbench unsigned without owner steps. | Add a short `docs/beta-limitations.md` (or section in release.md) and link from README when labeling beta. |
| P0.3 | **Primary operator path proven end-to-end on a clean machine** | Golden compile + wheel smoke exist as scripts; owner has not yet proven a *clean* Mac (or clean Linux) install outside the dev tree with retained transcript. | Run `smoke_install` + `golden_compile` with `VERIFORMIS_USE_PATH=1` after wheel install; keep log under `dev/active/.../evidence/`. |
| P0.4 | **No silent overclaim in docs** | Status/WIP must keep “not public-ready” until checklist complete. Beta label requires deliberate maturity bump. | Doc review at beta cut; forbid “production-ready” / “public release” wording. |
| P0.5 | **Core suite remains the source of truth** | 658 local tests (post–G9). Any failure is a beta blocker. | Gate: full pytest green on CI matrix 3.11–3.13 (+ macOS 3.12). |

---

## P1 — Strongly recommended before beta

| # | Gap | Evidence / why | Suggested fix |
| --- | --- | --- | --- |
| P1.1 | **Mac workbench beta path unclear** | Workbench shells CLI; no signed binary; Xcode/XcodeGen required for builds. Beta users may expect a drag-drop app. | Either (a) ship CLI-only beta, or (b) owner-signed notarized workbench with install notes. Document choice. |
| P1.2 | **Aptus handoff story for beta** | Continuation + supervised schemas accept; `full_text` handoff is rejected by design. Operators may think seal success = Aptus-ready. | Beta docs: default recommended objective for Aptus is continuation (or other accepted schemas); link Aptus contract. |
| P1.3 | **Local CI parity script** | Contributors may push without matching CI. | `scripts/release/check_local.sh` (lint, pytest, smoke, golden). |
| P1.4 | **Failure UX for operators** | Fail-closed is correct; some CLI errors still dense for non-authors. | Spot-check top 10 failure codes for actionable messages; no behavior change required if messages are located. |
| P1.5 | **Migration / upgrade story** | Migration tests exist; beta users with old workspaces need a one-page “upgrade-workspace” note. | Short section in release or development guide. |
| P1.6 | **Dependency surface for wheel install** | Runtime pulls `mcp` and heavy optional-ish stack even for pure compile. | Accept for beta or split extras later (`[project.optional-dependencies] mcp`). Not blocking if install smoke is green. |

---

## P2 — Documented limitations OK for beta

| # | Item | Notes |
| --- | --- | --- |
| P2.1 | No OCR | Refuse path is intentional. |
| P2.2 | No LLM / network generation | Doctrine; Group 8 deferred. |
| P2.3 | No typechecker / coverage hard gate | Optional quality; not product contract. |
| P2.4 | No dependency CVE audit in CI | Add as P3 public gate if desired. |
| P2.5 | No multi-user / auth / cloud | Out of product. |
| P2.6 | Deterministic v1 only | Five objectives; no model-assisted construction. |
| P2.7 | Generated DOCX in acceptance manifest | Golden compile uses on-disk corpus only (txt/md/code); generated docx path is separate fixture story. |

---

## P3 — Public / post-beta

| # | Item |
| --- | --- |
| P3.1 | Developer ID + notarization + staple + Gatekeeper on clean Mac |
| P3.2 | Compatible Aptus release binary acceptance with retained logs |
| P3.3 | Security review / dependency review as hard gates |
| P3.4 | Version bump + changelog + signed artifacts with digests |
| P3.5 | Broader platform claims (Windows, etc.) if ever desired |

---

## Automated evidence map (beta bar)

| Gate | Command / job | Beta role |
| --- | --- | --- |
| Lockfile | `uv lock --check` | Required |
| Lint | `uv run ruff check src tests` | Required |
| Suite | `uv run pytest -q` | Required (matrix on CI) |
| Wheel install | `scripts/release/smoke_install.sh` | Required |
| Golden product path | `scripts/release/golden_compile.sh` | Required |
| Local all-in-one | `scripts/release/check_local.sh` | Strongly recommended pre-push |
| Mac unsigned archive | `scripts/release/macos_package_local.sh` | Optional for CLI-only beta |
| Signed Mac product | Owner checklist in `docs/release.md` | Required for *Mac app* beta, not CLI beta |

---

## Suggested beta cut definition

Call **CLI beta** only when:

1. CI green: all `test` matrix cells + `install-smoke` + `golden-compile`.
2. Retained local evidence of smoke + golden on a clean venv (not just repo `.venv`).
3. Published beta limitations page linked from README.
4. Explicit support statement: e.g. “Python 3.11–3.13; offline; no OCR; Aptus supervised row schemas only.”
5. Version/tag policy decided (still `0.1.0b1` or stay `0.1.0` alpha with “beta candidate” language).

Call **workbench beta** only when CLI beta is true **and** Mac packaging path is chosen and proven (signed or clearly “unsigned developer build”).

---

## Immediate next actions (ordered)

1. **Fix CI** (P0.1) — remove unused imports; push; wait for green.  
2. **Harden G9** — independent smoke/golden jobs; pinned smoke Python; `check_local.sh`.  
3. **Write beta limitations** when ready to label (P0.2) — not required for merging G9 infrastructure.  
4. **Owner clean-path evidence** (P0.3) when hardware/time allows.  
5. **Decide CLI-only vs workbench beta** (P1.1) before any external invite.

---

## Non-goals of this audit

- Implementing Group 8 (model-assisted construction).  
- Claiming public release readiness.  
- Expanding format support or OCR.  
- Changing product doctrine (fail-closed, offline, evidence-bound).
