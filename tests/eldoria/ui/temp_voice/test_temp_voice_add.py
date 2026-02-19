from __future__ import annotations

import sys
from types import ModuleType

import discord  # type: ignore
import pytest

from eldoria.ui.temp_voice import add as M
from tests._fakes._discord_entities_fakes import FakeGuild, FakeVoiceChannel
from tests._fakes._pages_fakes import FakeInteraction, FakeUser


# ---------------------------------------------------------------------------
# Fakes minimaux (guild/voice channel/service/interactions)
# ---------------------------------------------------------------------------
class FakeTempVoiceService:
    def __init__(self):
        self.upserts: list[tuple[int, int, int]] = []

    def upsert_parent(self, guild_id: int, channel_id: int, user_limit: int) -> None:
        self.upserts.append((guild_id, channel_id, user_limit))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_child(view, *, custom_id: str):
    for child in getattr(view, "children", []):
        if getattr(child, "custom_id", None) == custom_id:
            return child
    return None


# ---------------------------------------------------------------------------
# Tests: build_tempvoice_add_embed
# ---------------------------------------------------------------------------

def test_build_tempvoice_add_embed_no_selection(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_VALIDATION", 777, raising=True)

    called = {"decorate": 0}

    def fake_decorate(embed, t, b):
        called["decorate"] += 1
        return embed

    monkeypatch.setattr(M, "decorate", fake_decorate, raising=True)

    embed = M.build_tempvoice_add_embed(selected_channel=None, user_limit=None, last_saved=None)

    assert isinstance(embed, discord.Embed)
    assert embed.title == "🟢 Ajouter un salon parent"
    assert embed.colour == 777
    assert len(embed.fields) == 2
    assert embed.fields[0] == {"name": "Salon sélectionné", "value": "Aucun", "inline": True}
    assert embed.fields[1] == {"name": "Limite d'utilisateurs", "value": "Non définie", "inline": True}
    assert called["decorate"] == 1


def test_build_tempvoice_add_embed_with_last_saved(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_VALIDATION", 10, raising=True)
    monkeypatch.setattr(M, "decorate", lambda e, *_a: e, raising=True)

    ch = FakeVoiceChannel(42, "General")
    embed = M.build_tempvoice_add_embed(
        selected_channel=ch,
        user_limit=3,
        last_saved=(ch, 8),
    )

    assert len(embed.fields) == 3
    assert embed.fields[0]["name"] == "✅ Configuration enregistrée"
    assert "<#42>" in embed.fields[0]["value"]
    assert "**8**" in embed.fields[0]["value"]
    assert embed.fields[1] == {"name": "Salon sélectionné", "value": "<#42>", "inline": True}
    assert embed.fields[2] == {"name": "Limite d'utilisateurs", "value": "3", "inline": True}


# ---------------------------------------------------------------------------
# Tests: TempVoiceAddView rendering + routing
# ---------------------------------------------------------------------------

def test_temp_voice_add_view_render_empty_guild_disables_select(monkeypatch):
    # Pour que isinstance(ch, discord.VoiceChannel) fonctionne
    monkeypatch.setattr(discord, "VoiceChannel", FakeVoiceChannel, raising=False)

    svc = FakeTempVoiceService()
    guild = FakeGuild(123, voice_channels=[])

    view = M.TempVoiceAddView(temp_voice_service=svc, author_id=1, guild=guild)

    select = _find_child(view, custom_id="tv:add:select")
    assert select is not None
    assert select.disabled is True
    assert len(select.options) == 1
    assert select.options[0].label == "Aucun salon vocal"
    assert select.options[0].value == "none"

    btn_save = _find_child(view, custom_id="tv:add:save")
    assert btn_save is not None
    assert btn_save.disabled is True


def test_temp_voice_add_view_render_enables_save_only_when_ready(monkeypatch):
    monkeypatch.setattr(discord, "VoiceChannel", FakeVoiceChannel, raising=False)

    svc = FakeTempVoiceService()
    guild = FakeGuild(123, voice_channels=[FakeVoiceChannel(1, "A"), FakeVoiceChannel(2, "B")])

    view = M.TempVoiceAddView(temp_voice_service=svc, author_id=1, guild=guild)

    btn_save = _find_child(view, custom_id="tv:add:save")
    assert btn_save is not None
    assert btn_save.disabled is True

    view.selected_channel = guild.voice_channels[0]
    view.user_limit = 5
    view._render()

    btn_save2 = _find_child(view, custom_id="tv:add:save")
    assert btn_save2 is not None
    assert btn_save2.disabled is False


@pytest.mark.asyncio
async def test_route_select_sets_selected_channel_and_edits(monkeypatch):
    monkeypatch.setattr(discord, "VoiceChannel", FakeVoiceChannel, raising=False)

    svc = FakeTempVoiceService()
    guild = FakeGuild(123, voice_channels=[FakeVoiceChannel(11, "V1"), FakeVoiceChannel(22, "V2")])
    view = M.TempVoiceAddView(temp_voice_service=svc, author_id=1, guild=guild)

    inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "tv:add:select"})
    await view.route_select(inter, values=["22"])

    assert view.selected_channel is not None
    assert view.selected_channel.id == 22
    assert inter.response.edits
    last = inter.response.edits[-1]
    assert isinstance(last["embed"], discord.Embed)
    assert last["view"] is view


@pytest.mark.asyncio
async def test_route_select_ignores_none_value(monkeypatch):
    monkeypatch.setattr(discord, "VoiceChannel", FakeVoiceChannel, raising=False)

    svc = FakeTempVoiceService()
    guild = FakeGuild(123, voice_channels=[FakeVoiceChannel(11, "V1")])
    view = M.TempVoiceAddView(temp_voice_service=svc, author_id=1, guild=guild)

    inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "tv:add:select"})
    await view.route_select(inter, values=["none"])

    assert view.selected_channel is None
    assert inter.response.edits


@pytest.mark.asyncio
async def test_route_button_limit_sends_modal_and_callback_updates_limit(monkeypatch):
    monkeypatch.setattr(discord, "VoiceChannel", FakeVoiceChannel, raising=False)

    class FakeUserLimitModal:
        def __init__(self, *, on_value):
            self.on_value = on_value

    monkeypatch.setattr(M, "UserLimitModal", FakeUserLimitModal, raising=True)

    svc = FakeTempVoiceService()
    guild = FakeGuild(123, voice_channels=[FakeVoiceChannel(11, "V1")])
    view = M.TempVoiceAddView(temp_voice_service=svc, author_id=1, guild=guild)

    inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "tv:add:limit"})
    await view.route_button(inter)

    assert inter.response.modals
    modal = inter.response.modals[0]
    assert isinstance(modal, FakeUserLimitModal)

    inter2 = FakeInteraction(user=FakeUser(1))
    await modal.on_value(inter2, 7)

    assert view.user_limit == 7
    assert inter2.response.edits


@pytest.mark.asyncio
async def test_route_button_save_calls_service_and_resets_state(monkeypatch):
    monkeypatch.setattr(discord, "VoiceChannel", FakeVoiceChannel, raising=False)

    svc = FakeTempVoiceService()
    guild = FakeGuild(555, voice_channels=[FakeVoiceChannel(99, "Parent")])
    view = M.TempVoiceAddView(temp_voice_service=svc, author_id=1, guild=guild)

    view.selected_channel = guild.voice_channels[0]
    view.user_limit = 12
    view._render()

    inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "tv:add:save"})
    await view.route_button(inter)

    assert svc.upserts == [(555, 99, 12)]
    assert view.last_saved is not None
    ch, limit = view.last_saved
    assert ch.id == 99
    assert limit == 12
    assert view.selected_channel is None
    assert view.user_limit is None
    assert inter.response.edits

    embed = view.current_embed()
    assert any(f.get("name") == "✅ Configuration enregistrée" for f in embed.fields)


@pytest.mark.asyncio
async def test_route_button_back_builds_home_and_edits(monkeypatch):
    monkeypatch.setattr(discord, "VoiceChannel", FakeVoiceChannel, raising=False)

    fake_home_mod = ModuleType("eldoria.ui.temp_voice.home")

    class FakeTempVoiceHomeView:
        def __init__(self, *, temp_voice_service, author_id: int, guild):
            self.temp_voice_service = temp_voice_service
            self.author_id = author_id
            self.guild = guild

        def current_embed(self):
            # le code fait: embed, _ = home.current_embed()
            return (discord.Embed(title="HOME", description="OK", color=1), None)

    fake_home_mod.TempVoiceHomeView = FakeTempVoiceHomeView
    sys.modules["eldoria.ui.temp_voice.home"] = fake_home_mod

    svc = FakeTempVoiceService()
    guild = FakeGuild(123, voice_channels=[FakeVoiceChannel(1, "A")])
    view = M.TempVoiceAddView(temp_voice_service=svc, author_id=1, guild=guild)

    inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "tv:back"})
    await view.route_button(inter)

    assert inter.response.edits
    last = inter.response.edits[-1]
    assert isinstance(last["embed"], discord.Embed)
    assert last["embed"].title == "HOME"
    assert isinstance(last["view"], FakeTempVoiceHomeView)


@pytest.mark.asyncio
async def test_route_button_unknown_custom_id_defers(monkeypatch):
    monkeypatch.setattr(discord, "VoiceChannel", FakeVoiceChannel, raising=False)

    svc = FakeTempVoiceService()
    guild = FakeGuild(123, voice_channels=[FakeVoiceChannel(1, "A")])
    view = M.TempVoiceAddView(temp_voice_service=svc, author_id=1, guild=guild)

    inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "tv:unknown"})
    await view.route_button(inter)

    assert inter.response.deferred is True
