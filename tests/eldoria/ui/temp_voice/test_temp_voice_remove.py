from __future__ import annotations

import sys
from types import ModuleType

import discord  # type: ignore
import pytest

from eldoria.ui.temp_voice import remove as M
from tests._fakes import (
    FakeGuild,
    FakeInteraction,
    FakeTempVoiceService,
    FakeUser,
    FakeVoiceChannel,
)


def _make_temp_voice_service(*, guild_id: int, parents: list[tuple[int, int]]):
    svc = FakeTempVoiceService()
    for cid, lim in parents:
        svc.upsert_parent(guild_id, cid, lim)
    return svc


def _find_child(view, *, custom_id: str):
    for child in getattr(view, "children", []):
        if getattr(child, "custom_id", None) == custom_id:
            return child
    return None


# ---------------------------------------------------------------------------
# build_tempvoice_remove_embed
# ---------------------------------------------------------------------------

def test_build_tempvoice_remove_embed_when_empty(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_ERROR", 999, raising=True)

    called = {"decorate": 0}

    def fake_decorate(embed, a, b):
        called["decorate"] += 1
        return embed

    monkeypatch.setattr(M, "decorate", fake_decorate, raising=True)

    embed = M.build_tempvoice_remove_embed(configured=[], selected=None)

    assert isinstance(embed, discord.Embed)
    assert embed.title == "🔴 Retirer un salon parent"
    assert embed.colour == 999
    assert len(embed.fields) == 2

    assert embed.fields[0]["name"] == "Salons configurés"
    assert "Aucun salon parent configuré" in embed.fields[0]["value"]

    assert embed.fields[1] == {"name": "Sélection", "value": "Aucune", "inline": False}

    assert called["decorate"] == 1


def test_build_tempvoice_remove_embed_when_configured_and_selected(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_ERROR", 1, raising=True)
    monkeypatch.setattr(M, "decorate", lambda e, *_a: e, raising=True)

    ch1 = FakeVoiceChannel(10, "A")
    ch2 = FakeVoiceChannel(20, "B")

    embed = M.build_tempvoice_remove_embed(
        configured=[(ch1, 5), (ch2, 9)],
        selected=ch2,
    )

    assert len(embed.fields) == 2
    assert embed.fields[0]["name"] == "Salons configurés"
    v = embed.fields[0]["value"]
    assert "<#10>" in v and "**5**" in v
    assert "<#20>" in v and "**9**" in v

    assert embed.fields[1] == {"name": "Sélection", "value": "<#20>", "inline": False}


# ---------------------------------------------------------------------------
# TempVoiceRemoveView: render/configured
# ---------------------------------------------------------------------------

def test_remove_view_render_no_configured_disables_select(monkeypatch):
    # Pour que isinstance(ch, discord.VoiceChannel) marche
    monkeypatch.setattr(discord, "VoiceChannel", FakeVoiceChannel, raising=False)

    svc = _make_temp_voice_service(guild_id=123, parents=[])
    guild = FakeGuild(123, voice_channels=[FakeVoiceChannel(1, "X")])  # même si salon existe, pas configuré
    view = M.TempVoiceRemoveView(temp_voice_service=svc, author_id=1, guild=guild)

    select = _find_child(view, custom_id="tv:remove:select")
    assert select is not None
    assert select.disabled is True
    assert len(select.options) == 1
    assert select.options[0].label == "Aucun salon configuré"
    assert select.options[0].value == "none"

    btn_delete = _find_child(view, custom_id="tv:remove:delete")
    assert btn_delete is not None
    assert btn_delete.disabled is True  # selected_channel None


def test_remove_view_get_configured_filters_non_voicechannels(monkeypatch):
    monkeypatch.setattr(discord, "VoiceChannel", FakeVoiceChannel, raising=False)

    # guild n'a que le salon 11, mais parents contient aussi 999 (inexistant)
    svc = _make_temp_voice_service(guild_id=123, parents=[(11, 3), (999, 7)])
    guild = FakeGuild(123, voice_channels=[FakeVoiceChannel(11, "OK")])

    view = M.TempVoiceRemoveView(temp_voice_service=svc, author_id=1, guild=guild)
    configured = view._get_configured()

    assert configured == [(guild.voice_channels[0], 3)]


def test_remove_view_render_configured_enables_select_and_delete_when_selected(monkeypatch):
    monkeypatch.setattr(discord, "VoiceChannel", FakeVoiceChannel, raising=False)

    svc = _make_temp_voice_service(guild_id=123, parents=[(11, 3), (22, 9)])
    guild = FakeGuild(123, voice_channels=[FakeVoiceChannel(11, "A"), FakeVoiceChannel(22, "B")])

    view = M.TempVoiceRemoveView(temp_voice_service=svc, author_id=1, guild=guild)

    select = _find_child(view, custom_id="tv:remove:select")
    assert select is not None
    assert select.disabled is False
    assert len(select.options) == 2

    btn_delete = _find_child(view, custom_id="tv:remove:delete")
    assert btn_delete is not None
    assert btn_delete.disabled is True  # pas de sélection

    # Simule sélection + rerender
    view.selected_channel = guild.voice_channels[0]
    view._render()

    btn_delete2 = _find_child(view, custom_id="tv:remove:delete")
    assert btn_delete2 is not None
    assert btn_delete2.disabled is False


# ---------------------------------------------------------------------------
# route_select
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_route_select_none_value_defers(monkeypatch):
    monkeypatch.setattr(discord, "VoiceChannel", FakeVoiceChannel, raising=False)

    svc = _make_temp_voice_service(guild_id=123, parents=[(11, 3)])
    guild = FakeGuild(123, voice_channels=[FakeVoiceChannel(11, "A")])
    view = M.TempVoiceRemoveView(temp_voice_service=svc, author_id=1, guild=guild)

    inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "tv:remove:select"})
    await view.route_select(inter, values=["none"])

    assert inter.response.deferred is True


@pytest.mark.asyncio
async def test_route_select_sets_selected_channel_and_edits(monkeypatch):
    monkeypatch.setattr(discord, "VoiceChannel", FakeVoiceChannel, raising=False)

    svc = _make_temp_voice_service(guild_id=123, parents=[(11, 3), (22, 9)])
    guild = FakeGuild(123, voice_channels=[FakeVoiceChannel(11, "A"), FakeVoiceChannel(22, "B")])
    view = M.TempVoiceRemoveView(temp_voice_service=svc, author_id=1, guild=guild)

    inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "tv:remove:select"})
    await view.route_select(inter, values=["22"])

    assert view.selected_channel is not None
    assert view.selected_channel.id == 22

    assert inter.response.edits
    last = inter.response.edits[-1]
    assert isinstance(last.get("embed"), discord.Embed)
    assert last.get("view") is view


# ---------------------------------------------------------------------------
# route_button
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_route_button_delete_calls_service_resets_and_edits(monkeypatch):
    monkeypatch.setattr(discord, "VoiceChannel", FakeVoiceChannel, raising=False)

    svc = _make_temp_voice_service(guild_id=123, parents=[(11, 3)])
    guild = FakeGuild(123, voice_channels=[FakeVoiceChannel(11, "A")])
    view = M.TempVoiceRemoveView(temp_voice_service=svc, author_id=1, guild=guild)

    # prépare sélection
    view.selected_channel = guild.voice_channels[0]
    view._render()

    inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "tv:remove:delete"})
    await view.route_button(inter)

    assert ("delete_parent", 123, 11) in svc.calls
    assert view.selected_channel is None

    assert inter.response.edits
    last = inter.response.edits[-1]
    assert isinstance(last.get("embed"), discord.Embed)
    assert last.get("view") is view


@pytest.mark.asyncio
async def test_route_button_back_builds_home_and_edits(monkeypatch):
    monkeypatch.setattr(discord, "VoiceChannel", FakeVoiceChannel, raising=False)

    # Injecte un faux module eldoria.ui.temp_voice.home avec TempVoiceHomeView
    fake_home_mod = ModuleType("eldoria.ui.temp_voice.home")

    def _init(self, *, temp_voice_service, author_id: int, guild):
        self.temp_voice_service = temp_voice_service
        self.author_id = author_id
        self.guild = guild

    def _current_embed(self):
        return (discord.Embed(title="HOME", description="OK", color=1), [])

    TempVoiceHomeViewStub = type(
        "TempVoiceHomeViewStub",
        (),
        {"__init__": _init, "current_embed": _current_embed},
    )

    fake_home_mod.TempVoiceHomeView = TempVoiceHomeViewStub
    sys.modules["eldoria.ui.temp_voice.home"] = fake_home_mod

    svc = _make_temp_voice_service(guild_id=123, parents=[(11, 3)])
    guild = FakeGuild(123, voice_channels=[FakeVoiceChannel(11, "A")])
    view = M.TempVoiceRemoveView(temp_voice_service=svc, author_id=1, guild=guild)

    inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "tv:back"})
    await view.route_button(inter)

    assert inter.response.edits
    last = inter.response.edits[-1]
    assert isinstance(last.get("embed"), discord.Embed)
    assert last["embed"].title == "HOME"
    assert isinstance(last.get("view"), TempVoiceHomeViewStub)


@pytest.mark.asyncio
async def test_route_button_unknown_defers(monkeypatch):
    monkeypatch.setattr(discord, "VoiceChannel", FakeVoiceChannel, raising=False)

    svc = _make_temp_voice_service(guild_id=123, parents=[(11, 3)])
    guild = FakeGuild(123, voice_channels=[FakeVoiceChannel(11, "A")])
    view = M.TempVoiceRemoveView(temp_voice_service=svc, author_id=1, guild=guild)

    inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "tv:unknown"})
    await view.route_button(inter)

    assert inter.response.deferred is True
