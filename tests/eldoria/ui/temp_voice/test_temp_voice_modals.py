import pytest

from eldoria.ui.temp_voice.modals import UserLimitModal
from tests._fakes import FakeInteraction, FakeUser

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
