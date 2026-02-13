from __future__ import annotations

import eldoria.features.duel.games as games_mod


class FakeGame:
    GAME_KEY = "RPS"


def test_init_games_registers_rps(monkeypatch):
    calls = []

    # On remplace register_game par un spy
    monkeypatch.setattr(games_mod, "register_game", lambda game: calls.append(game))

    # On remplace rps_game importé par un fake
    monkeypatch.setattr(games_mod, "rps_game", FakeGame())

    games_mod.init_games()

    assert calls == [games_mod.rps_game]
