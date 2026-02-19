from __future__ import annotations

import discord  # type: ignore
import pytest

from eldoria.ui.temp_voice import home as M
from tests._fakes._discord_entities_fakes import FakeGuild
from tests._fakes._pages_fakes import FakeInteraction, FakeUser


class FakeTempVoiceService:
    """Minimal: HomeView ne l'utilise que pour le passer aux sous-views."""
    pass


def _find_child(view, *, custom_id: str):
    for child in getattr(view, "children", []):
        if getattr(child, "custom_id", None) == custom_id:
            return child
    return None


# ---------------------------------------------------------------------------
# build_tempvoice_home_embed
# ---------------------------------------------------------------------------

def test_build_tempvoice_home_embed_builds_embed_and_files(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 123, raising=True)

    called = {"decorate": 0, "common_files": 0}

    def fake_decorate(embed, a, b):
        called["decorate"] += 1
        return embed

    def fake_common_files(a, b):
        called["common_files"] += 1
        return ["file1", "file2"]

    monkeypatch.setattr(M, "decorate", fake_decorate, raising=True)
    monkeypatch.setattr(M, "common_files", fake_common_files, raising=True)

    embed, files = M.build_tempvoice_home_embed()

    assert isinstance(embed, discord.Embed)
    assert embed.title == "🔊 Vocaux temporaires"
    assert embed.colour == 123
    assert len(embed.fields) == 2
    assert embed.fields[0]["name"] == "🟢 Ajouter"
    assert embed.fields[1]["name"] == "🔴 Retirer"
    assert files == ["file1", "file2"]

    assert called["decorate"] == 1
    assert called["common_files"] == 1


# ---------------------------------------------------------------------------
# TempVoiceHomeView init
# ---------------------------------------------------------------------------

def test_home_view_init_adds_three_buttons(monkeypatch):
    # Le stub peut ne pas exposer discord.Guild; on passe FakeGuild
    svc = FakeTempVoiceService()
    guild = FakeGuild(123)

    view = M.TempVoiceHomeView(temp_voice_service=svc, author_id=42, guild=guild)

    btn_add = _find_child(view, custom_id="tv:go:add")
    btn_remove = _find_child(view, custom_id="tv:go:remove")
    btn_close = _find_child(view, custom_id="tv:close")

    assert btn_add is not None
    assert btn_remove is not None
    assert btn_close is not None

    assert getattr(btn_add, "label", None) == "Ajouter"
    assert getattr(btn_remove, "label", None) == "Retirer"
    assert getattr(btn_close, "label", None) == "Fermer"


# ---------------------------------------------------------------------------
# route_button
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_route_button_close_edits_message(monkeypatch):
    svc = FakeTempVoiceService()
    guild = FakeGuild(123)
    view = M.TempVoiceHomeView(temp_voice_service=svc, author_id=42, guild=guild)

    inter = FakeInteraction(user=FakeUser(42), data={"custom_id": "tv:close"})
    await view.route_button(inter)

    assert inter.response.edits
    last = inter.response.edits[-1]
    assert last["content"] == "✅ Fermé."
    assert last["embed"] is None
    assert last["view"] is None
    assert last["attachments"] == []


@pytest.mark.asyncio
async def test_route_button_go_add_instantiates_add_view_and_edits(monkeypatch):
    svc = FakeTempVoiceService()
    guild = FakeGuild(123)
    home = M.TempVoiceHomeView(temp_voice_service=svc, author_id=42, guild=guild)

    # Fake AddView
    class FakeAddView:
        def __init__(self, *, temp_voice_service, author_id: int, guild):
            self.temp_voice_service = temp_voice_service
            self.author_id = author_id
            self.guild = guild

        def current_embed(self):
            return discord.Embed(title="ADD", description="ok", color=1)

    monkeypatch.setattr(M, "TempVoiceAddView", FakeAddView, raising=True)

    inter = FakeInteraction(user=FakeUser(42), data={"custom_id": "tv:go:add"})
    await home.route_button(inter)

    assert inter.response.edits
    last = inter.response.edits[-1]
    assert isinstance(last["embed"], discord.Embed)
    assert last["embed"].title == "ADD"
    assert isinstance(last["view"], FakeAddView)


@pytest.mark.asyncio
async def test_route_button_go_remove_instantiates_remove_view_and_edits(monkeypatch):
    svc = FakeTempVoiceService()
    guild = FakeGuild(123)
    home = M.TempVoiceHomeView(temp_voice_service=svc, author_id=42, guild=guild)

    # Fake RemoveView
    class FakeRemoveView:
        def __init__(self, *, temp_voice_service, author_id: int, guild):
            self.temp_voice_service = temp_voice_service
            self.author_id = author_id
            self.guild = guild

        def current_embed(self):
            return discord.Embed(title="REMOVE", description="ok", color=1)

    monkeypatch.setattr(M, "TempVoiceRemoveView", FakeRemoveView, raising=True)

    inter = FakeInteraction(user=FakeUser(42), data={"custom_id": "tv:go:remove"})
    await home.route_button(inter)

    assert inter.response.edits
    last = inter.response.edits[-1]
    assert isinstance(last["embed"], discord.Embed)
    assert last["embed"].title == "REMOVE"
    assert isinstance(last["view"], FakeRemoveView)


@pytest.mark.asyncio
async def test_route_button_unknown_defers():
    svc = FakeTempVoiceService()
    guild = FakeGuild(123)
    home = M.TempVoiceHomeView(temp_voice_service=svc, author_id=42, guild=guild)

    inter = FakeInteraction(user=FakeUser(42), data={"custom_id": "tv:???unknown"})
    await home.route_button(inter)

    assert inter.response.deferred is True
