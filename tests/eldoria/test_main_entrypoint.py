from __future__ import annotations

import runpy
import sys
import types


def test_main_module_runs_setup_logging_and_calls_app_main(monkeypatch):
    calls = {"setup": [], "main": []}

    # Fake eldoria.utils.logging.setup_logging
    fake_logging_mod = types.ModuleType("eldoria.utils.logging")

    def setup_logging(level):
        calls["setup"].append(level)

    fake_logging_mod.setup_logging = setup_logging  # type: ignore[attr-defined]

    # Fake eldoria.app.app.main
    fake_app_mod = types.ModuleType("eldoria.app.app")

    def main(started_at):
        calls["main"].append(started_at)

    fake_app_mod.main = main  # type: ignore[attr-defined]

    # Ensure parent packages exist
    sys.modules.setdefault("eldoria", types.ModuleType("eldoria"))
    sys.modules.setdefault("eldoria.utils", types.ModuleType("eldoria.utils"))
    sys.modules.setdefault("eldoria.app", types.ModuleType("eldoria.app"))

    monkeypatch.setitem(sys.modules, "eldoria.utils.logging", fake_logging_mod)
    monkeypatch.setitem(sys.modules, "eldoria.app.app", fake_app_mod)

    # Stabilise perf_counter
    import time

    monkeypatch.setattr(time, "perf_counter", lambda: 12.34, raising=True)

    # Exécute `src/main.py` comme si lancé en script.
    runpy.run_module("main", run_name="__main__")

    assert calls["setup"], "setup_logging doit être appelé"
    assert calls["main"] == [12.34]
