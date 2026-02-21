from __future__ import annotations

import sys
import types

import pytest


# ---------- Minimal stubs (complément conftest) ----------
def _ensure_discord_bits() -> None:
    if "discord" not in sys.modules:
        sys.modules["discord"] = types.ModuleType("discord")
    discord = sys.modules["discord"]

    for name in ("Guild", "Embed", "File", "Interaction"):
        if not hasattr(discord, name):
            setattr(discord, name, type(name, (), {}))

    if not hasattr(discord, "ButtonStyle"):
        class ButtonStyle:  # pragma: no cover
            success = "success"
            danger = "danger"
            secondary = "secondary"
        discord.ButtonStyle = ButtonStyle


_ensure_discord_bits()
discord = sys.modules["discord"]


# ---------- Import module under test ----------
import eldoria.ui.xp.admin.menu as mod  # noqa: E402
from eldoria.ui.xp.admin.menu import XpAdminMenuView  # noqa: E402


# ---------- Fakes ----------
class FakeGuild(discord.Guild):  # type: ignore[misc]
    def __init__(self, guild_id: int):
        self.id = guild_id


class FakeXpService:
    def __init__(self):
        self.calls: list[tuple] = []
        self._cfg = {"enabled": True}

    def ensure_defaults(self, guild_id: int):
        self.calls.append(("ensure_defaults", guild_id))

    def get_config(self, guild_id: int):
        self.calls.append(("get_config", guild_id))
        return dict(self._cfg)

    def set_config(self, guild_id: int, **kwargs):
        self.calls.append(("set_config", guild_id, kwargs))
        # keep internal cfg somewhat consistent
        self._cfg.update(kwargs)

    async def ensure_guild_xp_setup(self, guild):
        self.calls.append(("ensure_guild_xp_setup", guild.id))


class FakeResponse:
    def __init__(self):
        self.deferred = False
        self.edits: list[dict] = []

    async def defer(self):
        self.deferred = True

    async def edit_message(self, **kwargs):
        self.edits.append(kwargs)


class FakeInteraction(discord.Interaction):  # type: ignore[misc]
    def __init__(self, custom_id: str):
        self.data = {"custom_id": custom_id}
        self.response = FakeResponse()


# ---------- Fixture: patch UI deps (BasePanelView / RoutedButton / embed builder) ----------
@pytest.fixture
def _patch_deps(monkeypatch: pytest.MonkeyPatch):
    class _BasePanelView:
        def __init__(self, *, author_id: int):
            self.author_id = author_id
            self.children: list[object] = []

        def add_item(self, item):
            self.children.append(item)

    class _RoutedButton:
        def __init__(self, *, label: str, style, custom_id: str, disabled: bool = False, emoji: str | None = None, row: int = 0):
            self.label = label
            self.style = style
            self.custom_id = custom_id
            self.disabled = disabled
            self.emoji = emoji
            self.row = row

    monkeypatch.setattr(mod, "BasePanelView", _BasePanelView, raising=True)
    monkeypatch.setattr(mod, "RoutedButton", _RoutedButton, raising=True)

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

    class _View:
        def __init__(self, *, xp, author_id: int, guild):
            self.xp = xp
            self.author_id = author_id
            self.guild = guild

        def current_embed(self):
            return (embed_value, ["F"])

    setattr(m, class_name, _View)
    sys.modules[module_name] = m
    return _View


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

    inter = FakeInteraction("xp:enable")
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

    inter = FakeInteraction("xp:disable")
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

    inter = FakeInteraction("xp:nav:settings")
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

    inter = FakeInteraction("xp:nav:voice")
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

    inter = FakeInteraction("xp:nav:levels")
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

    inter = FakeInteraction("xp:wat")
    await view.route_button(inter)

    assert inter.response.deferred is True
    assert inter.response.edits == []