# Veriformis Security, Privacy, and Provenance Review

**Status:** Operator-facing review for development alpha `0.1.0`

**Last reviewed:** 2026-09-01 (independent-product Phase 20.4)

This page records the Phase 20.4 license inventory, parser threat model,
secret isolation, artifact reproducibility, and provenance review. It is
not a CVE subscription, not a notarized Mac claim, and not a version bump.

## License inventory

Veriformis itself is **MIT**. See [LICENSE](../LICENSE) and
`pyproject.toml` `license = "MIT"`.

Direct runtime dependencies are declared in `pyproject.toml` and pinned by
`uv.lock`. Optional extras (`trl`, `mlx-lm`, `columnar`, `axolotl`,
`llama-factory`, `unsloth`, `ocr`) stay empty, so trainer and OCR wheels are
not part of the core install. Transitive licenses are those of the locked
packages; this review does not invent SPDX identifiers for them.

No copyleft obligation is introduced by Veriformis's own license. CI runs
`uv lock --check`. This item does not add a required network license crawler.

## Vulnerability review

Core compile does not import `httpx`, `requests`, `huggingface_hub`, or
`openai`. ADR-0020 Decision A installs no Hub execute. ADR-0017 Decision A
installs no untrusted loader. Empty extras keep trainer CVEs out of the
independent core.

This review does not subscribe to an external vulnerability database. A
later owner may run an optional scanner; it is not a required CI gate.

## Parser threat model

Parsers run in-process on captured local bytes. There is no network fetch
and no archive ingest.

| Threat | Control |
| --- | --- |
| Unknown suffix | Fail closed (`UnsupportedInputError`) |
| Image-only PDF | Named `ocr-image` refusal on the default path |
| Malformed DOCX ZIP | `ParseError`; OOXML XML uses `resolve_entities=False` and `no_network=True` |
| HTML chrome / scripts | Stripped with diagnostics; no network |
| Non-UTF-8 text | Fail closed |
| Truncated JSON / JSONL | Refused or degraded, never silent |
| Symlink / non-regular capture | Collection plan refuses |
| Parser subprocess | Skipped with a Phase 11 record; optional Tesseract is an empty extra |
| Untrusted plugin code | ADR-0017 Decision A; no loader |

Untrusted files are expected. The compiler must fail closed rather than
execute embedded content.

## Secret scan

Project specs and locks refuse credential-shaped fields. `env-inspect`
does not echo secrets. Injected `HF_TOKEN`, `AWS_SECRET_ACCESS_KEY`, and
`AUTHORIZATION` do not persist in compiler artifacts. GitHub workflows
carry no Hub secrets. Package metadata has no `HF_TOKEN`.

This item does not store live credentials. A private key or cloud token
in `src/`, `scripts/`, `examples/`, or `docs/` is a defect.

## Artifact reproducibility

The same sources produce the same manifest SHA-256. Golden compile and
install-smoke retain that path. Identities are content-addressed.
`pipeline/v1` and the project-spec example pin committed fingerprints.
This is local determinism, not bit-identical wheels across every
operating system.

## Provenance

Every constructed field binds to source-text or strict-IR evidence.
Imported rows bind `mapped_value`. Finished bundles carry manifest,
attestation, provenance, and validation. Exports carry a receipt.
Independent `verify` does not trust the machine that sealed the bundle.

## Privacy

The compiler is local and offline. There are no accounts, telemetry,
billing, or required cloud storage. Network publication is absent from
the default path.

## Non-claims

- Public signed, notarized, or stapled Mac
- Hub execute or hosted training
- A required pip-audit / OSV CI job
- A published corpus SLA

See [support-lifecycle.md](support-lifecycle.md) for vulnerability response
and release rollback. Privacy stays local and offline.
