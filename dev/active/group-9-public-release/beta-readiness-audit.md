# Veriformis Beta Readiness Audit

**Date:** 2026-08-05  
**Scope:** Honest gap list for a **flawless beta** (not public production).  
**Baseline:** Groups 1–7 + Group 9 automated gates on `main` (PRs #14/#15).  
**Policy:** Do not publish until this list is closed or explicitly accepted as beta limitations.  
**Updated:** 2026-08-05 (P0.1–P0.3 progress after #15 merge)

## Verdict (current)

| Claim | Status |
| --- | --- |
| Development alpha with strong core pipeline | **Yes** (local + CI suite green) |
| Automated install + golden compile evidence | **Yes** (CI on main + retained clean-path pack) |
| Explicit limitations register | **Yes** (`docs/beta-limitations.md`) — maturity still alpha |
| Beta-ready product | **No** (label not cut; remaining P0/P1 open) |
| Public-ready product | **No** |

**Recommended maturity label until beta cut:** `0.1.0` development alpha.  
**Do not rebrand to beta** until remaining P0 items and a deliberate label decision close.

---

## Severity key

- **P0** — Blocks any beta label (correctness, honesty, or install path).
- **P1** — Blocks a *comfortable* beta (operator confidence, polish, evidence).
- **P2** — Nice for beta quality; acceptable as known limitation if documented.
- **P3** — Post-beta / public production.

---

## P0 — Must close before “beta”

| # | Gap | Status | Notes |
| --- | --- | --- | --- |
| P0.1 | **GitHub CI must be green** on `main` | **Closed** | PR #15 fixed Ruff F401; main CI green after merge (matrix + install-smoke + golden-compile). |
| P0.2 | **Known limitations must be explicit** | **Closed (doc)** | [`docs/beta-limitations.md`](../../../docs/beta-limitations.md) — still alpha until beta label cut. |
| P0.3 | **Clean-path operator evidence retained** | **Closed (dev Mac pack)** | [`evidence/20260805T-local-mac/`](evidence/20260805T-local-mac/) via `record_clean_path_evidence.sh`. CI Ubuntu jobs remain ongoing evidence. |
| P0.4 | **No silent overclaim in docs** | **Open at beta cut** | Keep alpha wording until deliberate re-label; README points at limitations. |
| P0.5 | **Core suite green on CI matrix** | **Closed (current)** | Re-verify on every release candidate; any red is a beta blocker. |

---

## P1 — Strongly recommended before beta

| # | Gap | Evidence / why | Suggested fix |
| --- | --- | --- | --- |
| P1.1 | **Mac workbench beta path** | **Documented CLI-first** in beta-limitations; workbench remains optional/unsigned unless owner checklist. |
| P1.2 | **Aptus handoff story for beta** | **Documented** in beta-limitations (full_text text schema reject; prefer continuation). |
| P1.3 | **Local CI parity script** | **Closed** — `scripts/release/check_local.sh`. |
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

1. ~~Fix CI (P0.1)~~ — done on main.  
2. ~~Harden G9 + check_local~~ — done.  
3. ~~Beta limitations doc (P0.2)~~ — `docs/beta-limitations.md`.  
4. ~~Clean-path evidence (P0.3)~~ — retained pack + recorder script.  
5. **Before any external beta invite:** deliberate label decision (P0.4), optional second OS clean-path pack, and owner Mac path only if shipping workbench.

---

## Non-goals of this audit

- Implementing Group 8 (model-assisted construction).  
- Claiming public release readiness.  
- Expanding format support or OCR.  
- Changing product doctrine (fail-closed, offline, evidence-bound).
