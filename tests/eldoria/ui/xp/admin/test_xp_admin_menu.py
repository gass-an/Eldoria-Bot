from __future__ import annotations

import sys
import types

import pytest

# ---------- Import module under test ----------
import eldoria.ui.xp.admin.menu as mod  # noqa: E402
from eldoria.ui.xp.admin.menu import XpAdminMenuView  # noqa: E402
from tests._fakes import FakeGuild, FakeInteraction, FakeUser, FakeXpService
from tests._support.xp_admin_stubs import BasePanelViewStub, RoutedButtonStub


# ---------- Fixture: patch UI deps (BasePanelView / RoutedButton / embed builder) ----------
@pytest.fixture
def _patch_deps(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(mod, "BasePanelView", BasePanelViewStub, raising=True)
    monkeypatch.setattr(mod, "RoutedButton", RoutedButtonStub, raising=True)

    def fake_build_menu_embed(cfg: dict):
        # Return a stable sentinel
        return (("MENU_EMBED", cfg.get("enabled")), ["F"])

    monkeypatch.setattr(mod, "build_xp_admin_menu_embed", fake_build_menu_embed, raising=True)


# ---------- Helpers: install stub modules for local imports in route_button ----------
def _install_local_view_module(module_name: str, class_name: str, embed_value: str):
    """
    Creates sys.modules[module_name] containing a class class_name with current_embed().
    """
    m = types.ModuleType(module_name)

    def _init(self, *, xp, author_id: int, guild):
        self.xp = xp
        self.author_id = author_id
        self.guild = guild

    def _current_embed(self):
        return (embed_value, ["F"])

    ViewT = type(class_name, (), {"__init__": _init, "current_embed": _current_embed})

    setattr(m, class_name, ViewT)
    sys.modules[module_name] = m
    return ViewT


# ---------- Tests: init / current_embed ----------
def test_init_buttons_disabled_state_when_enabled(_patch_deps):
    xp = FakeXpService()
    xp._cfg = {"enabled": True}
    guild = FakeGuild(1)

    view = XpAdminMenuView(xp=xp, author_id=123, guild=guild)

    assert ("ensure_defaults", 1) in xp.calls
    assert ("get_config", 1) in xp.calls

    # 5 buttons: enable/disable + 3 nav
    assert len(view.children) == 5

    btn_enable = view.children[0]
    btn_disable = view.children[1]
    nav_settings = view.children[2]
    nav_voice = view.children[3]
    nav_levels = view.children[4]

    assert btn_enable.custom_id == "xp:enable"
    assert btn_enable.disabled is True
    assert btn_disable.custom_id == "xp:disable"
    assert btn_disable.disabled is False

    assert nav_settings.custom_id == "xp:nav:settings"
    assert nav_settings.disabled is False
    assert nav_voice.custom_id == "xp:nav:voice"
    assert nav_voice.disabled is False
    assert nav_levels.custom_id == "xp:nav:levels"
    assert nav_levels.disabled is False

    embed, files = view.current_embed()
    assert embed[0] == "MENU_EMBED"
    assert embed[1] is True
    assert files == ["F"]


def test_init_buttons_disabled_state_when_disabled(_patch_deps):
    xp = FakeXpService()
    xp._cfg = {"enabled": False}
    guild = FakeGuild(1)

    view = XpAdminMenuView(xp=xp, author_id=123, guild=guild)

    assert len(view.children) == 5
    btn_enable = view.children[0]
    btn_disable = view.children[1]
    nav_settings = view.children[2]
    nav_voice = view.children[3]
    nav_levels = view.children[4]

    assert btn_enable.disabled is False
    assert btn_disable.disabled is True

    assert nav_settings.disabled is True
    assert nav_voice.disabled is True
    assert nav_levels.disabled is True


# ---------- Tests: route_button enable / disable ----------
@pytest.mark.asyncio
async def test_route_button_enable_updates_config_and_edits(_patch_deps):
    xp = FakeXpService()
    xp._cfg = {"enabled": False}
    guild = FakeGuild(1)
    view = XpAdminMenuView(xp=xp, author_id=123, guild=guild)

    inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "xp:enable"})
    await view.route_button(inter)

    assert ("ensure_defaults", 1) in xp.calls
    assert ("set_config", 1, {"enabled": True}) in xp.calls

    assert inter.response.edits
    last = inter.response.edits[-1]
    assert last["embed"][0] == "MENU_EMBED"
    assert isinstance(last["view"], XpAdminMenuView)


@pytest.mark.asyncio
async def test_route_button_disable_updates_config_and_edits(_patch_deps):
    xp = FakeXpService()
    xp._cfg = {"enabled": True}
    guild = FakeGuild(1)
    view = XpAdminMenuView(xp=xp, author_id=123, guild=guild)

    inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "xp:disable"})
    await view.route_button(inter)

    assert ("ensure_defaults", 1) in xp.calls
    assert ("set_config", 1, {"enabled": False}) in xp.calls

    assert inter.response.edits
    last = inter.response.edits[-1]
    assert last["embed"][0] == "MENU_EMBED"
    assert isinstance(last["view"], XpAdminMenuView)


# ---------- Tests: route_button navigation ----------
@pytest.mark.asyncio
async def test_route_button_nav_settings_edits_to_settings_view(_patch_deps):
    _SettingsView = _install_local_view_module(
        "eldoria.ui.xp.admin.settings",
        "XpAdminSettingsView",
        embed_value="SETTINGS_EMBED",
    )

    xp = FakeXpService()
    xp._cfg = {"enabled": True}
    guild = FakeGuild(1)
    view = XpAdminMenuView(xp=xp, author_id=123, guild=guild)

    inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "xp:nav:settings"})
    await view.route_button(inter)

    last = inter.response.edits[-1]
    assert last["embed"] == "SETTINGS_EMBED"
    assert isinstance(last["view"], _SettingsView)


@pytest.mark.asyncio
async def test_route_button_nav_voice_edits_to_voice_view(_patch_deps):
    _VoiceView = _install_local_view_module(
        "eldoria.ui.xp.admin.voice",
        "XpAdminVoiceView",
        embed_value="VOICE_EMBED",
    )

    xp = FakeXpService()
    xp._cfg = {"enabled": True}
    guild = FakeGuild(1)
    view = XpAdminMenuView(xp=xp, author_id=123, guild=guild)

    inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "xp:nav:voice"})
    await view.route_button(inter)

    last = inter.response.edits[-1]
    assert last["embed"] == "VOICE_EMBED"
    assert isinstance(last["view"], _VoiceView)


@pytest.mark.asyncio
async def test_route_button_nav_levels_edits_to_levels_view(_patch_deps):
    _LevelsView = _install_local_view_module(
        "eldoria.ui.xp.admin.levels",
        "XpAdminLevelsView",
        embed_value="LEVELS_EMBED",
    )

    xp = FakeXpService()
    xp._cfg = {"enabled": True}
    guild = FakeGuild(1)
    view = XpAdminMenuView(xp=xp, author_id=123, guild=guild)

    inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "xp:nav:levels"})
    await view.route_button(inter)

    last = inter.response.edits[-1]
    assert last["embed"] == "LEVELS_EMBED"
    assert isinstance(last["view"], _LevelsView)


# ---------- Tests: route_button unknown ----------
@pytest.mark.asyncio
async def test_route_button_unknown_defers(_patch_deps):
    xp = FakeXpService()
    guild = FakeGuild(1)
    view = XpAdminMenuView(xp=xp, author_id=123, guild=guild)

    inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "xp:wat"})
    await view.route_button(inter)

    assert inter.response.deferred is True
    assert inter.response.edits == []