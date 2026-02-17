import logging
from types import SimpleNamespace

import pytest

from eldoria.app.run_tests import _parse_pytest_counts, run_tests


class FakeLogger(logging.Logger):
    def __init__(self):
        super().__init__("fake")
        self.infos = []
        self.warnings = []
        self.exceptions = []

    def info(self, msg, *args, **kwargs):
        self.infos.append(msg % args if args else msg)

    def warning(self, msg, *args, **kwargs):
        self.warnings.append(msg % args if args else msg)

    def exception(self, msg, *args, **kwargs):
        self.exceptions.append(msg % args if args else msg)


def test_parse_pytest_counts_full_summary_line():
    out = """
================== short test summary info ==================
2 failed, 367 passed, 4 skipped in 3.21s
"""
    assert _parse_pytest_counts(out) == {
        "failed": 2,
        "passed": 367,
        "skipped": 4,
        "xfailed": 0,
        "xpassed": 0,
    }


def test_parse_pytest_counts_minimal_summary_line():
    out = "367 passed in 2.13s\n"
    assert _parse_pytest_counts(out)["passed"] == 367
    assert _parse_pytest_counts(out)["failed"] == 0


def test_parse_pytest_counts_fallback_without_in_keyword_hits_fallback_loop():
    # Couvre le fallback (cas: sortie très minimale sans "in ...s")
    out = "367 passed\n"
    assert _parse_pytest_counts(out) == {
        "failed": 0,
        "passed": 367,
        "skipped": 0,
        "xfailed": 0,
        "xpassed": 0,
    }


def test_parse_pytest_counts_with_xfail_xpass():
    out = "1 failed, 2 passed, 3 skipped, 4 xfailed, 5 xpassed in 0.10s\n"
    assert _parse_pytest_counts(out) == {
        "failed": 1,
        "passed": 2,
        "skipped": 3,
        "xfailed": 4,
        "xpassed": 5,
    }


def test_parse_pytest_counts_no_match_returns_zeros():
    out = "some random output\nno summary here\n"
    assert _parse_pytest_counts(out) == {
        "failed": 0,
        "passed": 0,
        "skipped": 0,
        "xfailed": 0,
        "xpassed": 0,
    }


def test_run_tests_returns_none_when_running_inside_pytest(monkeypatch):
    # under pytest, sys.modules contains "pytest" -> should short-circuit
    import sys

    assert "pytest" in sys.modules  # sanity
    assert run_tests(logger=FakeLogger()) is None

    # also test the env var short-circuit (even if pytest not in sys.modules)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "x")
    assert run_tests(logger=FakeLogger()) is None


def test_run_tests_returns_none_when_no_tests_exist(monkeypatch):
    # Force guard to not short-circuit: remove markers
    import sys

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delitem(sys.modules, "pytest", raising=False)

    # Patch TESTS_PATH to a fake object with exists False
    import eldoria.app.run_tests as mod

    class FakePath:
        def exists(self):
            return False

        def rglob(self, _pattern):
            return []

    monkeypatch.setattr(mod, "TESTS_PATH", FakePath(), raising=True)

    assert mod.run_tests(logger=FakeLogger()) is None


def test_run_tests_success_returns_ratio_label(monkeypatch):
    import sys

    import eldoria.app.run_tests as mod

    # disable "already in pytest" guard
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delitem(sys.modules, "pytest", raising=False)

    # tests exist
    class FakePath:
        def exists(self):
            return True

        def rglob(self, _pattern):
            return [SimpleNamespace(name="test_x.py")]

    monkeypatch.setattr(mod, "TESTS_PATH", FakePath(), raising=True)

    # subprocess.run for first call returns passing output
    def fake_run(args, capture_output=True, text=True):
        assert args[:3] == [sys.executable, "-m", "pytest"]
        return SimpleNamespace(
            returncode=0,
            stdout="10 passed, 2 skipped in 0.10s\n",
            stderr="",
        )

    monkeypatch.setattr(mod.subprocess, "run", fake_run, raising=True)

    label = mod.run_tests(logger=FakeLogger())
    assert label == "10/12 Tests validés"


def test_run_tests_success_parsing_ko_but_returncode_ok(monkeypatch):
    import sys

    import eldoria.app.run_tests as mod

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delitem(sys.modules, "pytest", raising=False)

    class FakePath:
        def exists(self):
            return True

        def rglob(self, _pattern):
            return [SimpleNamespace(name="test_x.py")]

    monkeypatch.setattr(mod, "TESTS_PATH", FakePath(), raising=True)

    def fake_run(_args, capture_output=True, text=True):
        return SimpleNamespace(returncode=0, stdout="NO SUMMARY HERE\n", stderr="")

    monkeypatch.setattr(mod.subprocess, "run", fake_run, raising=True)

    assert mod.run_tests(logger=FakeLogger()) == "Tests validés"


def test_run_tests_failure_strict_raises_and_logs_details(monkeypatch):
    import sys

    import eldoria.app.run_tests as mod

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delitem(sys.modules, "pytest", raising=False)

    class FakePath:
        def exists(self):
            return True

        def rglob(self, _pattern):
            return [SimpleNamespace(name="test_x.py")]

    monkeypatch.setattr(mod, "TESTS_PATH", FakePath(), raising=True)

    # first run => failing summary
    calls = {"n": 0}

    def fake_run(args, capture_output=True, text=True):
        calls["n"] += 1
        if calls["n"] == 1:
            return SimpleNamespace(returncode=1, stdout="2 failed, 3 passed in 0.10s\n", stderr="")
        # second run => details with short summary
        return SimpleNamespace(
            returncode=1,
            stdout="""
=========================== short test summary info ============================
FAILED tests/test_a.py::test_x - AssertionError: boom
ERROR tests/test_b.py::test_y - RuntimeError: nope
""",
            stderr="",
        )

    monkeypatch.setattr(mod.subprocess, "run", fake_run, raising=True)

    monkeypatch.setenv("TESTS_STRICT", "1")
    logger = FakeLogger()

    with pytest.raises(RuntimeError, match="Tests failed"):
        mod.run_tests(logger=logger)

    assert any("Détails des échecs" in w for w in logger.warnings)


def test_run_tests_failure_non_strict_returns_label(monkeypatch):
    import sys

    import eldoria.app.run_tests as mod

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delitem(sys.modules, "pytest", raising=False)

    class FakePath:
        def exists(self):
            return True

        def rglob(self, _pattern):
            return [SimpleNamespace(name="test_x.py")]

    monkeypatch.setattr(mod, "TESTS_PATH", FakePath(), raising=True)

    calls = {"n": 0}

    def fake_run(_args, capture_output=True, text=True):
        calls["n"] += 1
        if calls["n"] == 1:
            return SimpleNamespace(returncode=1, stdout="2 failed, 3 passed in 0.10s\n", stderr="")
        return SimpleNamespace(returncode=1, stdout="FAILED tests/test_a.py::test_x\n", stderr="")

    monkeypatch.setattr(mod.subprocess, "run", fake_run, raising=True)

    monkeypatch.setenv("TESTS_STRICT", "0")
    assert mod.run_tests(logger=FakeLogger()) == "2 tests fails / 5"


def test_run_tests_failure_parsing_ko_raises(monkeypatch):
    import sys

    import eldoria.app.run_tests as mod

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delitem(sys.modules, "pytest", raising=False)

    class FakePath:
        def exists(self):
            return True

        def rglob(self, _pattern):
            return [SimpleNamespace(name="test_x.py")]

    monkeypatch.setattr(mod, "TESTS_PATH", FakePath(), raising=True)

    def fake_run(_args, capture_output=True, text=True):
        return SimpleNamespace(returncode=1, stdout="garbage\n", stderr="also garbage\n")

    monkeypatch.setattr(mod.subprocess, "run", fake_run, raising=True)

    monkeypatch.setenv("TESTS_STRICT", "1")
    with pytest.raises(RuntimeError, match="Tests failed"):
        mod.run_tests(logger=FakeLogger())


def test_run_tests_logger_defaults_to_module_log(monkeypatch):
    import sys

    import eldoria.app.run_tests as mod

    # disable "already in pytest" guard
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delitem(sys.modules, "pytest", raising=False)

    # tests exist
    class FakePath:
        def exists(self):
            return True

        def rglob(self, _pattern):
            return [SimpleNamespace(name="test_x.py")]

    monkeypatch.setattr(mod, "TESTS_PATH", FakePath(), raising=True)

    # make module log observable
    fake_logger = FakeLogger()
    monkeypatch.setattr(mod, "log", fake_logger, raising=True)

    def fake_run(_args, capture_output=True, text=True):
        return SimpleNamespace(returncode=0, stdout="1 passed in 0.01s\n", stderr="")

    monkeypatch.setattr(mod.subprocess, "run", fake_run, raising=True)

    assert mod.run_tests(logger=None) == "1/1 Tests validés"
    # Verify defaulted logger is used
    assert any("Lancement des tests" in msg for msg in fake_logger.infos)
