from __future__ import annotations

import sys
from types import ModuleType

import eldoria.ui.duels.games as games_pkg
from eldoria.ui.duels import init_duel_ui


def test_init_duel_ui_imports_rps_and_calls_register(monkeypatch):
    calls: list[str] = []

    fake_rps = ModuleType("eldoria.ui.duels.games.rps")

    def register():
        calls.append("register")

    fake_rps.register = register  # type: ignore[attr-defined]

    # 1) On force sys.modules (résolution d'import)
    monkeypatch.setitem(sys.modules, "eldoria.ui.duels.games.rps", fake_rps)

    # 2) TRÈS IMPORTANT: si le package parent a déjà games_pkg.rps (vrai module),
    #    on le remplace aussi, sinon l'import `from .games import rps` peut le reprendre.
    monkeypatch.setattr(games_pkg, "rps", fake_rps, raising=False)

    init_duel_ui()

    assert calls == ["register"]
