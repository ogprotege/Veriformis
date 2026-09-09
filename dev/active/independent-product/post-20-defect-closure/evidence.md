# Evidence

Verification proof per defect. Each row names the regression that pins the
fix. Rows are appended as items close; an item without a row is open.

| ID | Regression / proof |
| --- | --- |
| D-01 | `tests/release/test_package_data_coverage.py`; `scripts/release/inspect_python_artifacts.sh` wheel-member check; `scripts/release/smoke_install.sh` discovery loop |
| D-02 | `tests/parsers/test_html_charset.py`; regenerated `tests/regressions/fixtures/phase6/goal-acceptance-matrix.json` (13 html cells) |
| D-03 | `tests/parsers/test_jsonl_framing.py` (parser, capture, handoff loader) |
| D-04 | `macos/Tests/CLIBridgeTests.swift::testWorkbenchSidecarDirectoryIsASiblingOfTheCLIWorkspace`, `::testDatasetRowCompileThroughTheWorkbenchSealsWithRealRepoCLI` (runs in the optional Debug xcodebuild job) |
| D-05 | `tests/regressions/test_post20_handoff_consume.py` (forged capabilities, forged masking, forged provenance identities, CLI rejection) |
| D-06 | `tests/regressions/test_post20_imported_seal_recovery.py` (partial publication on Python and CLI, exact prior adoption, foreign destination refusal) |
| D-08 | `tests/regressions/test_post20_imported_seal_recovery.py::test_map_rows_writes_the_rejection_report_before_head_advances` |
| D-09 | `tests/test_cli_error_funnel.py` |
| D-27 | `tests/regressions/test_defectclose_handoff.py` (moved; collected by the core gate) |
| D-28 | `tests/profiles/test_profile_integration.py` under `VERIFORMIS_REQUIRE_PROFILE_LIBRARIES=1` with extra `columnar` |
