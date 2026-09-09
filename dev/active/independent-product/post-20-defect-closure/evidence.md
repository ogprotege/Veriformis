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
| D-24 | `scripts/check_project_tracking.py::_check_contracts_match_discovery` (fails on the pre-fix contracts) |
| D-25 | `tests/release/test_xcodebuild_debug_ci.py::test_cli_reference_command_count_matches_typer`; manual `veriformis map` example run |
| D-26 | `scripts/check_project_tracking.py::_check_package_data_coverage`; reviewed statements listed in `progress.md` |
| D-10 | `tests/parsers/test_docx_hardening.py` |
| D-11 | `tests/parsers/test_pdf_page_provenance.py`; `tests/goals/test_goal_input_families.py::test_pdf_text_supplies_paragraphs_with_page_provenance_and_no_headings` |
| D-12 | `tests/parsers/test_html_structure.py` |
| D-13 | `tests/parsers/test_structured_exactness.py`; `tests/parsers/test_hardening_matrix.py::test_text_empty_and_non_utf8_fail_closed` |
| D-14 | `tests/ocr/test_tesseract_confidence.py`; `tests/ocr/test_recovery_paths.py::test_provider_without_confidence_requires_review_instead_of_accepting` |
| D-22 | `tests/collection/test_collection_plan.py` (limits before hashing; argument-order independence) |
| 3.7 | `tests/chunkers/test_strategies.py::test_sentence_splitter_handles_unicode_terminators_and_quotes` |
| D-07 | Withdrawn; `tests/datasets/test_models_and_curation.py::test_unicode_is_exact_for_dedup_conflict_and_identity`; imported NFC/NFD case in `tests/mapping/test_mapping_provenance.py` |
| D-15 | `tests/exports/test_exact_decoding.py` rejects common planner/renderer corruption for all seven exact exporters; complete export/profile and core suites passed |
| D-16 | `tests/bundle/test_zip64.py` tests writer size/offset extensions and refuses noncanonical extras |
