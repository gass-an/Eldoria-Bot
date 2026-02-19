from __future__ import annotations

import discord  # type: ignore
import pytest

from eldoria.ui.temp_voice.modals import UserLimitModal
from tests._fakes._pages_fakes import FakeInteraction, FakeUser

# ---------------------------------------------------------------------------
# Helpers / patches stub discord.ui for Modal/InputText
# ---------------------------------------------------------------------------

class _FakeInputText:
    def __init__(
        self,
        *,
        label: str,
        placeholder: str | None = None,
        required: bool = True,
        min_length: int | None = None,
        max_length: int | None = None,
    ):
        self.label = label
        self.placeholder = placeholder
        self.required = required
        self.min_length = min_length
        self.max_length = max_length
        self.value: str | None = None


@pytest.fixture(autouse=True)
def _patch_modal_inputtext(monkeypatch: pytest.MonkeyPatch) -> None:
    # Certains stubs n'ont pas InputText, ou pas les bons kwargs
    monkeypatch.setattr(discord.ui, "InputText", _FakeInputText, raising=False)

    # Certains stubs de Modal peuvent ne pas avoir add_item()
    Modal = discord.ui.Modal
    if not hasattr(Modal, "add_item"):
        def add_item(self, item) -> None:
            # Pour nos tests, on n'a pas besoin de plus.
            if not hasattr(self, "children"):
                self.children = []
            self.children.append(item)
        monkeypatch.setattr(Modal, "add_item", add_item, raising=False)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_user_limit_modal_non_numeric_sends_error_ephemeral():
    called: list[tuple[FakeInteraction, int]] = []

    async def on_value(interaction, value: int):
        called.append((interaction, value))

    modal = UserLimitModal(on_value=on_value)
    modal.limit_input.value = "abc"

    inter = FakeInteraction(user=FakeUser(1))
    await modal.callback(inter)

    assert called == []
    assert inter.response.sent, "Doit envoyer un message d'erreur"
    last = inter.response.sent[-1]
    assert last["ephemeral"] is True
    assert "entrer un nombre" in last["content"]


@pytest.mark.asyncio
async def test_user_limit_modal_out_of_range_low_sends_error_ephemeral():
    called: list[tuple[FakeInteraction, int]] = []

    async def on_value(interaction, value: int):
        called.append((interaction, value))

    modal = UserLimitModal(on_value=on_value)
    modal.limit_input.value = "0"

    inter = FakeInteraction(user=FakeUser(1))
    await modal.callback(inter)

    assert called == []
    last = inter.response.sent[-1]
    assert last["ephemeral"] is True
    assert "entre 1 et 99" in last["content"]


@pytest.mark.asyncio
async def test_user_limit_modal_out_of_range_high_sends_error_ephemeral():
    called: list[tuple[FakeInteraction, int]] = []

    async def on_value(interaction, value: int):
        called.append((interaction, value))

    modal = UserLimitModal(on_value=on_value)
    modal.limit_input.value = "100"

    inter = FakeInteraction(user=FakeUser(1))
    await modal.callback(inter)

    assert called == []
    last = inter.response.sent[-1]
    assert last["ephemeral"] is True
    assert "entre 1 et 99" in last["content"]


@pytest.mark.asyncio
@pytest.mark.parametrize("raw, expected", [("1", 1), ("99", 99), (" 5 ", 5)])
async def test_user_limit_modal_valid_calls_on_value(raw: str, expected: int):
    called: list[tuple[FakeInteraction, int]] = []

    async def on_value(interaction, value: int):
        called.append((interaction, value))

    modal = UserLimitModal(on_value=on_value)
    modal.limit_input.value = raw

    inter = FakeInteraction(user=FakeUser(1))
    await modal.callback(inter)

    assert called == [(inter, expected)]
    # ne doit pas envoyer de message d'erreur
    assert inter.response.sent == []
