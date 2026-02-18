from __future__ import annotations

import pytest

import eldoria.features.duel.games.registry as reg


class FakeGame:
    GAME_KEY = "FAKE"


class FakeGame2:
    GAME_KEY = "FAKE"


@pytest.fixture(autouse=True)
def _clear_registry():
    reg._REGISTRY.clear()
    yield
    reg._REGISTRY.clear()


def test_register_game_then_get_game_returns_instance():
    g = FakeGame()
    reg.register_game(g)

    assert reg.get_game("FAKE") is g


def test_require_game_raises_when_not_registered():
    from eldoria.exceptions.duel import InvalidGameType

    with pytest.raises(InvalidGameType):
        reg.require_game("MISSING")


def test_register_game_overwrites_existing_key():
    g1 = FakeGame()
    g2 = FakeGame2()

    reg.register_game(g1)
    reg.register_game(g2)

    assert reg.get_game("FAKE") is g2
