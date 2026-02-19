from __future__ import annotations

import discord  # type: ignore
import pytest

from eldoria.ui.temp_voice.components import BasePanelView, RoutedButton, RoutedSelect
from tests._fakes._pages_fakes import FakeInteraction, FakeUser

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _last_sent(inter: FakeInteraction) -> dict:
    assert inter.response.sent, "Aucun message n'a été envoyé via interaction.response.send_message"
    return inter.response.sent[-1]


# ---------------------------------------------------------------------------
# BasePanelView
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_base_panel_interaction_check_allows_author():
    view = BasePanelView(author_id=42)

    inter = FakeInteraction(user=FakeUser(42))
    ok = await view.interaction_check(inter)

    assert ok is True
    assert inter.response.sent == []


@pytest.mark.asyncio
async def test_base_panel_interaction_check_denies_other_user_sends_ephemeral():
    view = BasePanelView(author_id=42)

    inter = FakeInteraction(user=FakeUser(999))
    ok = await view.interaction_check(inter)

    assert ok is False
    sent = _last_sent(inter)
    assert sent["ephemeral"] is True
    assert "Seul l'auteur" in sent["content"]


@pytest.mark.asyncio
async def test_base_panel_interaction_check_denies_when_user_none_sends_ephemeral():
    view = BasePanelView(author_id=42)

    inter = FakeInteraction(user=FakeUser(42))
    inter.user = None  # type: ignore[assignment]

    ok = await view.interaction_check(inter)

    assert ok is False
    sent = _last_sent(inter)
    assert sent["ephemeral"] is True
    assert "Seul l'auteur" in sent["content"]


@pytest.mark.asyncio
async def test_base_panel_on_timeout_disables_buttons_and_selects():
    view = BasePanelView(author_id=1)

    btn = discord.ui.Button(label="A", style=discord.ButtonStyle.primary, custom_id="b1")  # type: ignore[arg-type]
    sel = discord.ui.Select(placeholder="X", options=[], custom_id="s1")  # type: ignore[arg-type]

    class DummyItem:
        def __init__(self):
            self.disabled = False

    dummy = DummyItem()

    view.children.extend([btn, sel, dummy])  # type: ignore[attr-defined]

    assert getattr(btn, "disabled", False) is False
    assert getattr(sel, "disabled", False) is False
    assert dummy.disabled is False

    await view.on_timeout()

    assert btn.disabled is True
    assert sel.disabled is True
    assert dummy.disabled is False


# ---------------------------------------------------------------------------
# RoutedButton
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_routed_button_callback_no_view_does_nothing():
    btn = RoutedButton(label="X", style=discord.ButtonStyle.primary, custom_id="cid")
    btn.view = None  # type: ignore[attr-defined]  # stub: l'attribut n'existe pas par défaut

    inter = FakeInteraction(user=FakeUser(1))
    await btn.callback(inter)  # doit juste return sans erreur


@pytest.mark.asyncio
async def test_routed_button_callback_view_without_route_button_does_nothing():
    btn = RoutedButton(label="X", style=discord.ButtonStyle.primary, custom_id="cid")

    class ViewNoRouter(discord.ui.View):
        pass

    v = ViewNoRouter()
    btn.view = v  # type: ignore[attr-defined]

    inter = FakeInteraction(user=FakeUser(1))
    await btn.callback(inter)


@pytest.mark.asyncio
async def test_routed_button_callback_calls_view_router():
    called: list[FakeInteraction] = []

    class ViewWithRouter(discord.ui.View):
        async def route_button(self, interaction):
            called.append(interaction)

    v = ViewWithRouter()
    btn = RoutedButton(label="X", style=discord.ButtonStyle.primary, custom_id="cid")
    btn.view = v  # type: ignore[attr-defined]

    inter = FakeInteraction(user=FakeUser(1))
    await btn.callback(inter)

    assert called == [inter]


# ---------------------------------------------------------------------------
# RoutedSelect
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_routed_select_callback_no_view_does_nothing(monkeypatch):
    sel = RoutedSelect(
        placeholder="P",
        options=[],
        custom_id="cid",
    )
    sel.view = None  # type: ignore[attr-defined]  # stub: l'attribut n'existe pas par défaut

    # Même si values n'est pas utilisé quand view=None, on sécurise selon stub
    monkeypatch.setattr(type(sel), "values", property(lambda _self: ()), raising=False)

    inter = FakeInteraction(user=FakeUser(1))
    await sel.callback(inter)


@pytest.mark.asyncio
async def test_routed_select_callback_view_without_route_select_does_nothing(monkeypatch):
    sel = RoutedSelect(
        placeholder="P",
        options=[],
        custom_id="cid",
    )

    class ViewNoRouter(discord.ui.View):
        pass

    v = ViewNoRouter()
    sel.view = v  # type: ignore[attr-defined]

    monkeypatch.setattr(type(sel), "values", property(lambda _self: ("x",)), raising=False)

    inter = FakeInteraction(user=FakeUser(1))
    await sel.callback(inter)


@pytest.mark.asyncio
async def test_routed_select_callback_calls_view_router_with_values_list(monkeypatch):
    received: list[tuple[FakeInteraction, list[str]]] = []

    class ViewWithRouter(discord.ui.View):
        async def route_select(self, interaction, values):
            received.append((interaction, values))

    v = ViewWithRouter()
    sel = RoutedSelect(
        placeholder="P",
        options=[],
        custom_id="cid",
    )
    sel.view = v  # type: ignore[attr-defined]

    # Simule sélection
    monkeypatch.setattr(type(sel), "values", property(lambda _self: ("a", "b")), raising=False)

    inter = FakeInteraction(user=FakeUser(1))
    await sel.callback(inter)

    assert received == [(inter, ["a", "b"])]
