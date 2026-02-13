from __future__ import annotations

import eldoria.ui.duels.games.rps as M


def test_register_calls_register_renderer(monkeypatch):
    calls: list[tuple[str, object]] = []

    # Patch constants.GAME_RPS + render_rps sur le module package
    monkeypatch.setattr(M.constants, "GAME_RPS", "RPS_KEY")
    monkeypatch.setattr(M, "render_rps", object())

    def fake_register_renderer(game_key, renderer):
        calls.append((game_key, renderer))

    # Import local dans register()
    import eldoria.ui.duels.registry as reg
    monkeypatch.setattr(reg, "register_renderer", fake_register_renderer)

    M.register()

    assert calls == [("RPS_KEY", M.render_rps)]
