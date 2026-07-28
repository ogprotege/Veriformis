# tests/test_scaffold.py
import veriformis


def test_package_imports_and_has_version():
    assert isinstance(veriformis.__version__, str)
    assert veriformis.__version__ == "0.1.0"
