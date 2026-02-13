from __future__ import annotations

import pytest

from eldoria.ui.duels import registry as R


@pytest.fixture(autouse=True)
def reset_registry():
    # reset entre tests
    R._RENDERERS.clear()
    yield
    R._RENDERERS.clear()


def test_register_and_require_renderer_success():
    async def renderer(snapshot, guild, bot):
        return ("embed", ["files"], None)

    R.register_renderer("rps", renderer)
    fn = R.require_renderer("rps")

    assert fn is renderer


def test_register_renderer_coerces_key_to_str():
    async def renderer(snapshot, guild, bot):
        return ("embed", ["files"], None)

    R.register_renderer(123, renderer)
    fn = R.require_renderer("123")

    assert fn is renderer


def test_require_renderer_raises_when_missing():
    with pytest.raises(ValueError) as e:
        R.require_renderer("nope")
    assert "No duel UI renderer registered" in str(e.value)
