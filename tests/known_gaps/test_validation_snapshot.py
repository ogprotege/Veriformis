import pytest

from veriformis.validate.gates import run_gates


@pytest.mark.xfail(strict=True, reason="roadmap-step-15: required datasets must be nonempty")
def test_empty_required_dataset_fails_validation():
    results = run_gates([], "completion", [], {})
    assert not all(result.passed for result in results)
    assert any("empty" in " ".join(result.messages).lower() for result in results)
