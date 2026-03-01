import pytest

import eldoria.ui.welcome.panel as wp_mod
from eldoria.ui.welcome.panel import WelcomePanelView, build_welcome_panel_embed
from tests._fakes import FakeChannel, FakeGuild, FakeInteraction, FakeUser, FakeWelcomeService

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

    welcome = FakeWelcomeService()
    welcome._cfg = {"enabled": False, "channel_id": 0}
    guild = FakeGuild(guild_id=111)

    view = WelcomePanelView(welcome_service=welcome, author_id=999, guild=guild)

    assert view.enabled is False
    assert view.channel is None
    assert len(view.children) == 2
    assert view.children[0].custom_id == "wm:enable"
    assert view.children[1].custom_id == "wm:disable"


def test_panel_init_enabled_adds_channelselect(monkeypatch):
    monkeypatch.setattr(wp_mod, "decorate", lambda *_a, **_k: None, raising=True)
    monkeypatch.setattr(wp_mod, "common_files", lambda *_a, **_k: [], raising=True)

    welcome = FakeWelcomeService()
    welcome._cfg = {"enabled": True, "channel_id": 555}

    guild = FakeGuild(guild_id=111, channels=[FakeChannel(555, name="accueil")])

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

    welcome = FakeWelcomeService()
    welcome._cfg = {"enabled": True, "channel_id": 0}
    guild = FakeGuild(guild_id=111)

    view = WelcomePanelView(welcome_service=welcome, author_id=123, guild=guild)
    chsel = view.children[2]
    selected = FakeChannel(777, name="bienvenue")
    chsel.values = [selected]

    def _init(self, *, welcome_service, author_id, guild):
        pass

    def _current_embed(self):
        return ("NEW_EMBED", [])

    SpyView = type("SpyView", (), {"__init__": _init, "current_embed": _current_embed})

    monkeypatch.setattr(wp_mod, "WelcomePanelView", SpyView, raising=True)

    inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "wm:channel"})
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

    guild = FakeGuild(guild_id=111)

    def _init(self, *, welcome_service, author_id, guild):
        pass

    def _current_embed(self):
        return ("EMBED", [])

    SpyView = type("SpyView", (), {"__init__": _init, "current_embed": _current_embed})

    monkeypatch.setattr(wp_mod, "WelcomePanelView", SpyView, raising=True)

    # enable
    welcome = FakeWelcomeService()
    welcome._cfg = {"enabled": False, "channel_id": 0}
    view = WelcomePanelView(welcome_service=welcome, author_id=123, guild=guild)

    inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "wm:enable"})
    await view.route_button(inter)

    assert ("set_enabled", 111, True) in welcome.calls
    assert inter.response.edits[-1]["embed"] == "EMBED"

    # disable
    welcome2 = FakeWelcomeService()
    welcome2._cfg = {"enabled": True, "channel_id": 0}
    view2 = WelcomePanelView(welcome_service=welcome2, author_id=123, guild=guild)

    inter2 = FakeInteraction(user=FakeUser(1), data={"custom_id": "wm:disable"})
    await view2.route_button(inter2)

    assert ("set_enabled", 111, False) in welcome2.calls
    assert inter2.response.edits[-1]["embed"] == "EMBED"