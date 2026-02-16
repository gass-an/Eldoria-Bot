from __future__ import annotations

import pytest

from eldoria.app import startup as mod

# ----------------------------
# Fakes
# ----------------------------

class FakeLogger:
    def __init__(self):
        self.infos = []
        self.exceptions = []

    def info(self, *args):
        self.infos.append(args)

    def exception(self, *args):
        self.exceptions.append(args)


class FakeBot:
    def __init__(self):
        self.loaded = []
        self._services = None

    # L'implémentation prod expose `set_services(...)`.
    def set_services(self, services):
        self._services = services

    @property
    def services(self):
        return self._services

    def load_extension(self, name: str):
        self.loaded.append(name)


# ----------------------------
# step()
# ----------------------------

def test_step_logs_info_with_default_logger_when_success_and_result_none(monkeypatch):
    fake_log = FakeLogger()
    monkeypatch.setattr(mod, "log", fake_log, raising=True)

    # perf_counter: start=1.0 end=1.1 => 100 ms
    t = {"n": 0}

    def fake_perf_counter():
        t["n"] += 1
        return 1.0 if t["n"] == 1 else 1.1

    monkeypatch.setattr(mod.time, "perf_counter", fake_perf_counter, raising=True)

    def action():
        return None

    mod.step("MyStep", action)

    assert len(fake_log.infos) == 1
    fmt, label, ms = fake_log.infos[0]
    assert "✅" in fmt
    assert label == "MyStep"
    assert ms == pytest.approx(100.0)


def test_step_logs_info_with_result_in_label(monkeypatch):
    fake_log = FakeLogger()
    monkeypatch.setattr(mod, "log", fake_log, raising=True)

    t = {"n": 0}

    def fake_perf_counter():
        t["n"] += 1
        return 10.0 if t["n"] == 1 else 10.005  # 5ms

    monkeypatch.setattr(mod.time, "perf_counter", fake_perf_counter, raising=True)

    def action():
        return 3

    mod.step("Load", action)

    _, label, ms = fake_log.infos[0]
    assert label == "Load (3)"
    assert ms == pytest.approx(5.0)


def test_step_uses_provided_logger(monkeypatch):
    fake_log = FakeLogger()
    monkeypatch.setattr(mod.time, "perf_counter", lambda: 0.0, raising=True)

    mod.step("X", lambda: None, logger=fake_log)
    assert len(fake_log.infos) == 1


def test_step_exception_critical_true_reraises(monkeypatch):
    fake_log = FakeLogger()
    monkeypatch.setattr(mod, "log", fake_log, raising=True)

    # start=1.0 end=1.2 => 200ms
    t = {"n": 0}

    def fake_perf_counter():
        t["n"] += 1
        return 1.0 if t["n"] == 1 else 1.2

    monkeypatch.setattr(mod.time, "perf_counter", fake_perf_counter, raising=True)

    def action():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        mod.step("Explode", action, critical=True)

    assert len(fake_log.exceptions) == 1
    fmt, name, ms = fake_log.exceptions[0]
    assert "❌" in fmt
    assert name == "Explode"
    assert ms == pytest.approx(200.0)


def test_step_exception_critical_false_does_not_raise(monkeypatch):
    fake_log = FakeLogger()
    monkeypatch.setattr(mod, "log", fake_log, raising=True)
    monkeypatch.setattr(mod.time, "perf_counter", lambda: 0.0, raising=True)

    def action():
        raise RuntimeError("boom")

    # ne doit pas lever
    mod.step("Explode", action, critical=False)
    assert len(fake_log.exceptions) == 1


# ----------------------------
# load_extensions()
# ----------------------------

def test_load_extensions_loads_all_and_returns_count(monkeypatch):
    bot = FakeBot()
    monkeypatch.setattr(mod, "EXTENSIONS", ["a", "b", "c"], raising=True)

    count = mod.load_extensions(bot)

    assert count == 3
    assert bot.loaded == ["a", "b", "c"]


# ----------------------------
# init_services()
# ----------------------------

def test_init_services_assigns_services_and_returns_len(monkeypatch):
    bot = FakeBot()

    # Remplace les classes de services par des sentinelles (constructeurs)
    class Svc:
        pass

    monkeypatch.setattr(mod, "DuelService", lambda: ("duel",), raising=True)
    monkeypatch.setattr(mod, "RoleService", lambda: ("role",), raising=True)
    monkeypatch.setattr(mod, "SaveService", lambda: ("save",), raising=True)
    monkeypatch.setattr(mod, "TempVoiceService", lambda: ("temp_voice",), raising=True)
    monkeypatch.setattr(mod, "WelcomeService", lambda: ("welcome",), raising=True)
    monkeypatch.setattr(mod, "XpService", lambda: ("xp",), raising=True)

    # Services(...) -> on retourne un objet avec __len__
    created = {}

    class FakeServices:
        def __init__(self, **kwargs):
            created.update(kwargs)

        def __len__(self):
            return len(created)

    monkeypatch.setattr(mod, "Services", FakeServices, raising=True)

    n = mod.init_services(bot)

    assert n == 6
    assert bot._services is not None
    assert set(created.keys()) == {"duel", "role", "save", "temp_voice", "welcome", "xp"}


# ----------------------------
# startup()
# ----------------------------

def test_startup_calls_steps_in_order_and_runs_actions(monkeypatch):
    bot = FakeBot()

    calls = []

    def fake_run_tests(*_, **__):
        calls.append(("run_tests", None))
        return None
    
    # On patch les fonctions appelées par startup() pour prouver qu'elles sont exécutées
    monkeypatch.setattr(mod, "init_services", lambda b: calls.append(("init_services", b)) or 6, raising=True)
    monkeypatch.setattr(mod, "load_extensions", lambda b: calls.append(("load_extensions", b)) or 2, raising=True)
    monkeypatch.setattr(mod, "init_db", lambda: calls.append(("init_db", None)), raising=True)
    monkeypatch.setattr(mod, "cleanup_temp_channels", lambda b: calls.append(("cleanup", b)), raising=True)
    monkeypatch.setattr(mod, "init_games", lambda: calls.append(("init_games", None)), raising=True)
    monkeypatch.setattr(mod, "init_duel_ui", lambda: calls.append(("init_duel_ui", None)), raising=True)
    monkeypatch.setattr(mod, "run_tests", fake_run_tests, raising=True)

    # Fake step : on capture les paramètres, et on exécute action() pour simuler le vrai comportement
    step_calls = []

    def fake_step(name, action, *, critical=True, logger=None):
        step_calls.append((name, critical))
        return action()

    monkeypatch.setattr(mod, "step", fake_step, raising=True)

    mod.startup(bot)

    assert step_calls == [
        ("Tests", False),
        ("Initialisation des services", False),
        ("Initialisation des extensions", True),
        ("Initialisation de la base de données", True),
        ("Nettoyage des channels temporaires", False),
        ("Initialisation des jeux de duel", False),
        ("Initialisation UI duel", False),
    ]

    
    assert calls == [
        ("run_tests", None),
        ("init_services", bot),
        ("load_extensions", bot),
        ("init_db", None),
        ("cleanup", bot),
        ("init_games", None),
        ("init_duel_ui", None),
    ]