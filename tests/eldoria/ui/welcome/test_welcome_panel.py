from __future__ import annotations

import sys
import types

import discord  # type: ignore
import pytest

import eldoria.ui.welcome.panel as wp_mod
from eldoria.ui.welcome.panel import WelcomePanelView, build_welcome_panel_embed

# ======================================================================
# 🔧 Stabilise ChannelSelect (signature compatible toutes suites)
# ======================================================================

@pytest.fixture(autouse=True)
def _patch_channel_select(monkeypatch: pytest.MonkeyPatch):
    discord_mod = sys.modules["discord"]

    if not hasattr(discord_mod, "ui"):
        discord_mod.ui = types.SimpleNamespace()

    class ChannelSelect:
        def __init__(
            self,
            *,
            placeholder: str,
            custom_id: str,
            channel_types: list,
            min_values: int,
            max_values: int,
            row: int,
            disabled: bool = False,
        ):
            self.placeholder = placeholder
            self.custom_id = custom_id
            self.channel_types = channel_types
            self.min_values = min_values
            self.max_values = max_values
            self.row = row
            self.disabled = disabled
            self.values: list = []
            self.callback = None

    monkeypatch.setattr(discord_mod.ui, "ChannelSelect", ChannelSelect, raising=False)

    # ChannelType stub si absent
    if not hasattr(discord_mod, "ChannelType"):
        class _FakeChannelType:
            text = "text"
            news = "news"
        monkeypatch.setattr(discord_mod, "ChannelType", _FakeChannelType, raising=False)


# ======================================================================
# 🧪 Fakes
# ======================================================================

class _FakeResponse:
    def __init__(self):
        self.deferred = False
        self.edits: list[dict] = []

    async def defer(self):
        self.deferred = True

    async def edit_message(self, **kwargs):
        self.edits.append(kwargs)


class _FakeInteraction:
    def __init__(self, custom_id: str):
        self.data = {"custom_id": custom_id}
        self.response = _FakeResponse()


class _FakeChannel(discord.abc.GuildChannel):  # type: ignore[misc]
    def __init__(self, channel_id: int, name: str = "welcome"):
        self.id = channel_id
        self.name = name
        self.mention = f"<#{channel_id}>"


class _FakeGuild(discord.Guild):  # type: ignore[misc]
    def __init__(self, guild_id: int):
        self.id = guild_id
        self._channels: dict[int, object] = {}

    def get_channel(self, channel_id: int):
        return self._channels.get(channel_id)


class _FakeWelcomeService:
    def __init__(self):
        self.calls: list[tuple] = []
        self._cfg = {"enabled": False, "channel_id": 0}

    def ensure_defaults(self, guild_id: int):
        self.calls.append(("ensure_defaults", guild_id))

    def get_config(self, guild_id: int):
        self.calls.append(("get_config", guild_id))
        return dict(self._cfg)

    def set_enabled(self, guild_id: int, enabled: bool):
        self.calls.append(("set_enabled", guild_id, enabled))

    def set_config(self, guild_id: int, **kwargs):
        self.calls.append(("set_config", guild_id, kwargs))


# ======================================================================
# 🧪 Tests: build_welcome_panel_embed
# ======================================================================

def test_build_embed_disabled_no_channel(monkeypatch):
    monkeypatch.setattr(wp_mod, "decorate", lambda *_a, **_k: None, raising=True)
    monkeypatch.setattr(wp_mod, "common_files", lambda *_a, **_k: ["FILE_A"], raising=True)

    embed, files = build_welcome_panel_embed(enabled=False, channel=None)

    assert embed.colour == wp_mod.EMBED_COLOUR_ERROR
    assert "⛔ Désactivé" in (embed.description or "")
    assert "*(aucun salon configuré)*" in (embed.description or "")
    assert embed.fields == []
    assert embed.footer and embed.footer["text"] == "Configure les messages de bienvenue de ton serveur."
    assert files == ["FILE_A"]


def test_build_embed_enabled_missing_channel_adds_warning(monkeypatch):
    monkeypatch.setattr(wp_mod, "decorate", lambda *_a, **_k: None, raising=True)
    monkeypatch.setattr(wp_mod, "common_files", lambda *_a, **_k: [], raising=True)

    embed, _files = build_welcome_panel_embed(enabled=True, channel=None)

    assert embed.colour == wp_mod.EMBED_COLOUR_VALIDATION
    assert len(embed.fields) == 1
    assert embed.fields[0]["name"] == "⚠️ Salon manquant"


# ======================================================================
# 🧪 Tests: WelcomePanelView init
# ======================================================================

def test_panel_init_disabled_adds_only_buttons(monkeypatch):
    monkeypatch.setattr(wp_mod, "decorate", lambda *_a, **_k: None, raising=True)
    monkeypatch.setattr(wp_mod, "common_files", lambda *_a, **_k: [], raising=True)

    welcome = _FakeWelcomeService()
    welcome._cfg = {"enabled": False, "channel_id": 0}
    guild = _FakeGuild(111)

    view = WelcomePanelView(welcome_service=welcome, author_id=999, guild=guild)

    assert view.enabled is False
    assert view.channel is None
    assert len(view.children) == 2
    assert view.children[0].custom_id == "wm:enable"
    assert view.children[1].custom_id == "wm:disable"


def test_panel_init_enabled_adds_channelselect(monkeypatch):
    monkeypatch.setattr(wp_mod, "decorate", lambda *_a, **_k: None, raising=True)
    monkeypatch.setattr(wp_mod, "common_files", lambda *_a, **_k: [], raising=True)

    welcome = _FakeWelcomeService()
    welcome._cfg = {"enabled": True, "channel_id": 555}

    guild = _FakeGuild(111)
    guild._channels[555] = _FakeChannel(555, name="accueil")

    view = WelcomePanelView(welcome_service=welcome, author_id=999, guild=guild)

    assert view.enabled is True
    assert view.channel is not None
    assert len(view.children) == 3

    chsel = view.children[2]
    assert chsel.custom_id == "wm:channel"
    assert hasattr(chsel, "values")
    assert callable(chsel.callback)
    assert "Salon actuel : #accueil" in chsel.placeholder


# ======================================================================
# 🧪 Tests: ChannelSelect callback
# ======================================================================

@pytest.mark.asyncio
async def test_channelselect_callback_sets_config_and_edits(monkeypatch):
    monkeypatch.setattr(wp_mod, "decorate", lambda *_a, **_k: None, raising=True)
    monkeypatch.setattr(wp_mod, "common_files", lambda *_a, **_k: [], raising=True)

    welcome = _FakeWelcomeService()
    welcome._cfg = {"enabled": True, "channel_id": 0}
    guild = _FakeGuild(111)

    view = WelcomePanelView(welcome_service=welcome, author_id=123, guild=guild)
    chsel = view.children[2]
    selected = _FakeChannel(777, name="bienvenue")
    chsel.values = [selected]

    class _SpyView:
        def __init__(self, *, welcome_service, author_id, guild):
            pass

        def current_embed(self):
            return ("NEW_EMBED", [])

    monkeypatch.setattr(wp_mod, "WelcomePanelView", _SpyView, raising=True)

    inter = _FakeInteraction("wm:channel")
    await chsel.callback(inter)  # type: ignore

    assert ("ensure_defaults", 111) in welcome.calls
    assert ("set_config", 111, {"channel_id": 777, "enabled": True}) in welcome.calls
    assert inter.response.edits[-1]["embed"] == "NEW_EMBED"


# ======================================================================
# 🧪 Tests: route_button
# ======================================================================

@pytest.mark.asyncio
async def test_route_button_enable_and_disable(monkeypatch):
    monkeypatch.setattr(wp_mod, "decorate", lambda *_a, **_k: None, raising=True)
    monkeypatch.setattr(wp_mod, "common_files", lambda *_a, **_k: [], raising=True)

    guild = _FakeGuild(111)

    class _SpyView:
        def __init__(self, *, welcome_service, author_id, guild):
            pass

        def current_embed(self):
            return ("EMBED", [])

    monkeypatch.setattr(wp_mod, "WelcomePanelView", _SpyView, raising=True)

    # enable
    welcome = _FakeWelcomeService()
    welcome._cfg = {"enabled": False, "channel_id": 0}
    view = WelcomePanelView(welcome_service=welcome, author_id=123, guild=guild)

    inter = _FakeInteraction("wm:enable")
    await view.route_button(inter)

    assert ("set_enabled", 111, True) in welcome.calls
    assert inter.response.edits[-1]["embed"] == "EMBED"

    # disable
    welcome2 = _FakeWelcomeService()
    welcome2._cfg = {"enabled": True, "channel_id": 0}
    view2 = WelcomePanelView(welcome_service=welcome2, author_id=123, guild=guild)

    inter2 = _FakeInteraction("wm:disable")
    await view2.route_button(inter2)

    assert ("set_enabled", 111, False) in welcome2.calls
    assert inter2.response.edits[-1]["embed"] == "EMBED"