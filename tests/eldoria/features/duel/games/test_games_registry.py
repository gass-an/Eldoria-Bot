from __future__ import annotations

import pytest

import eldoria.features.duel.games.registry as reg

GameStub = type("GameStub", (), {"GAME_KEY": "FAKE"})
Game2Stub = type("Game2Stub", (), {"GAME_KEY": "FAKE"})


@pytest.fixture(autouse=True)
def _clear_registry():
    reg._REGISTRY.clear()
    yield
    reg._REGISTRY.clear()


def test_register_game_then_get_game_returns_instance():
    g = GameStub()
    reg.register_game(g)

    assert reg.get_game("FAKE") is g


def test_require_game_raises_when_not_registered():
    from eldoria.exceptions.duel import InvalidGameType

    with pytest.raises(InvalidGameType):
        reg.require_game("MISSING")


def test_register_game_overwrites_existing_key():
    g1 = GameStub()
    g2 = Game2Stub()

    reg.register_game(g1)
    reg.register_game(g2)

    assert reg.get_game("FAKE") is g2
