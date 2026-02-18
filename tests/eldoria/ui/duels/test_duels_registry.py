from __future__ import annotations

import pytest

from eldoria.ui.duels import registry as R


def test_register_renderer_then_require_returns_fn():
    async def renderer(snapshot, guild, bot):
        return ("embed", [], None)

    R._RENDERERS.clear()
    R.register_renderer(123, renderer)
    fn = R.require_renderer("123")

    assert fn is renderer


def test_require_renderer_raises_when_missing():
    from eldoria.exceptions.duel import InvalidGameType

    R._RENDERERS.clear()
    with pytest.raises(InvalidGameType):
        R.require_renderer("nope")
