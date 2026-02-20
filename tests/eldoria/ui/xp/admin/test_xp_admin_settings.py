from __future__ import annotations

import sys
import types

import pytest


# ---------- Minimal discord shims (complément conftest) ----------
def _ensure_discord_bits() -> None:
    if "discord" not in sys.modules:
        sys.modules["discord"] = types.ModuleType("discord")
    discord = sys.modules["discord"]

    for name in ("Guild", "Embed", "File", "Interaction"):
        if not hasattr(discord, name):
            setattr(discord, name, type(name, (), {}))

    if not hasattr(discord, "ButtonStyle"):
        class ButtonStyle:  # pragma: no cover
            primary = "primary"
            secondary = "secondary"
        discord.ButtonStyle = ButtonStyle


_ensure_discord_bits()
discord = sys.modules["discord"]


# ---------- Import module under test ----------
import eldoria.ui.xp.admin.settings as mod  # noqa: E402
from eldoria.ui.xp.admin.settings import XpAdminSettingsView  # noqa: E402


# ---------- Fakes ----------
class FakeGuild(discord.Guild):  # type: ignore[misc]
    def __init__(self, guild_id: int):
        self.id = guild_id


class FakeXpService:
    def __init__(self):
        self.calls: list[tuple] = []
        self._cfg = {
            "enabled": True,
            "points_per_message": 3,
            "cooldown_seconds": 10,
            "bonus_percent": 20,
            "karuta_k_small_percent": 30,
        }

    def get_config(self, guild_id: int):
        self.calls.append(("get_config", guild_id))
        return dict(self._cfg)

    def ensure_defaults(self, guild_id: int):
        self.calls.append(("ensure_defaults", guild_id))

    def set_config(self, guild_id: int, **kwargs):
        self.calls.append(("set_config", guild_id, kwargs))
        self._cfg.update(kwargs)


class FakeResponse:
    def __init__(self):
        self.deferred = False
        self.edits: list[dict] = []
        self.modals: list[object] = []
        self.messages: list[dict] = []

    async def defer(self):
        self.deferred = True

    async def edit_message(self, **kwargs):
        self.edits.append(kwargs)

    async def send_modal(self, modal):
        self.modals.append(modal)

    async def send_message(self, content: str, ephemeral: bool = False):
        self.messages.append({"content": content, "ephemeral": ephemeral})


class FakeInteraction(discord.Interaction):  # type: ignore[misc]
    def __init__(self, custom_id: str):
        self.data = {"custom_id": custom_id}
        self.response = FakeResponse()
        self._original_edits: list[dict] = []

    async def edit_original_response(self, **kwargs):
        self._original_edits.append(kwargs)


# ---------- Fixture: patch deps ----------
@pytest.fixture
def _patch_deps(monkeypatch: pytest.MonkeyPatch):
    # BasePanelView / RoutedButton
    class _BasePanelView:
        def __init__(self, *, author_id: int):
            self.author_id = author_id
            self.children: list[object] = []

        def add_item(self, item):
            self.children.append(item)

    class _RoutedButton:
        def __init__(self, *, label: str, style, custom_id: str, emoji: str | None = None, row: int = 0, disabled: bool = False):
            self.label = label
            self.style = style
            self.custom_id = custom_id
            self.emoji = emoji
            self.row = row
            self.disabled = disabled

    monkeypatch.setattr(mod, "BasePanelView", _BasePanelView, raising=True)
    monkeypatch.setattr(mod, "RoutedButton", _RoutedButton, raising=True)

    # embed builder stub
    def fake_build_settings_embed(cfg: dict):
        return (("SETTINGS_EMBED", cfg.get("points_per_message")), ["F"])

    monkeypatch.setattr(mod, "build_xp_admin_settings_embed", fake_build_settings_embed, raising=True)

    # menu view stub
    class _FakeMenuView:
        def __init__(self, *, xp, author_id: int, guild):
            self._ = (xp, author_id, guild)

        def current_embed(self):
            return ("MENU_EMBED", ["F"])

    monkeypatch.setattr(mod, "XpAdminMenuView", _FakeMenuView, raising=True)

    # modal stub: capture callback + current
    captured: dict = {}

    class _FakeModal:
        def __init__(self, *, on_submit, current: dict):
            captured["on_submit"] = on_submit
            captured["current"] = current

    monkeypatch.setattr(mod, "XpSettingsModal", _FakeModal, raising=True)

    return captured


# ---------- Tests: init / current_embed ----------
def test_init_adds_buttons(_patch_deps):
    xp = FakeXpService()
    guild = FakeGuild(1)

    view = XpAdminSettingsView(xp=xp, author_id=123, guild=guild)

    assert len(view.children) == 2
    assert view.children[0].custom_id == "xp:back"
    assert view.children[1].custom_id == "xp:set:settings"


def test_current_embed_uses_cfg_and_builder(_patch_deps):
    xp = FakeXpService()
    guild = FakeGuild(1)
    view = XpAdminSettingsView(xp=xp, author_id=123, guild=guild)

    embed, files = view.current_embed()

    assert ("get_config", 1) in xp.calls
    assert embed[0] == "SETTINGS_EMBED"
    assert files == ["F"]


# ---------- Tests: route_button modal path ----------
@pytest.mark.asyncio
async def test_route_button_set_settings_sends_modal_with_current(_patch_deps):
    xp = FakeXpService()
    guild = FakeGuild(1)
    view = XpAdminSettingsView(xp=xp, author_id=123, guild=guild)

    inter = FakeInteraction("xp:set:settings")
    await view.route_button(inter)

    assert inter.response.modals  # modal sent
    assert ("get_config", 1) in xp.calls  # current = xp.get_config called

    # captured current passed to modal
    assert _patch_deps["current"]["points_per_message"] == 3
    assert callable(_patch_deps["on_submit"])


@pytest.mark.asyncio
async def test_modal_submit_filters_none_and_noop_when_empty_payload(_patch_deps):
    xp = FakeXpService()
    guild = FakeGuild(1)
    view = XpAdminSettingsView(xp=xp, author_id=123, guild=guild)

    inter = FakeInteraction("xp:set:settings")
    await view.route_button(inter)
    on_submit = _patch_deps["on_submit"]

    modal_inter = FakeInteraction("modal-submit")

    # payload only None -> should send INFO message, no set_config
    await on_submit(modal_inter, {"points_per_message": None, "bonus_percent": None})

    assert modal_inter.response.messages
    msg = modal_inter.response.messages[-1]
    assert "Aucun champ fourni" in msg["content"]
    assert msg["ephemeral"] is True

    assert not any(c[0] == "set_config" for c in xp.calls)


@pytest.mark.asyncio
async def test_modal_submit_updates_config_and_edits_original(_patch_deps):
    xp = FakeXpService()
    guild = FakeGuild(1)
    view = XpAdminSettingsView(xp=xp, author_id=123, guild=guild)

    inter = FakeInteraction("xp:set:settings")
    await view.route_button(inter)
    on_submit = _patch_deps["on_submit"]

    modal_inter = FakeInteraction("modal-submit")

    await on_submit(modal_inter, {"points_per_message": 5, "cooldown_seconds": None})

    assert ("ensure_defaults", 1) in xp.calls
    assert ("set_config", 1, {"points_per_message": 5}) in xp.calls

    assert modal_inter.response.deferred is True
    assert modal_inter._original_edits
    last = modal_inter._original_edits[-1]
    assert last["embed"][0] == "SETTINGS_EMBED"
    assert isinstance(last["view"], XpAdminSettingsView)


# ---------- Tests: route_button back / unknown ----------
@pytest.mark.asyncio
async def test_route_button_back_edits_to_menu(_patch_deps):
    xp = FakeXpService()
    guild = FakeGuild(1)
    view = XpAdminSettingsView(xp=xp, author_id=123, guild=guild)

    inter = FakeInteraction("xp:back")
    await view.route_button(inter)

    assert inter.response.edits
    last = inter.response.edits[-1]
    assert last["embed"] == "MENU_EMBED"
    assert last["view"].__class__.__name__ == "_FakeMenuView"


@pytest.mark.asyncio
async def test_route_button_unknown_defers(_patch_deps):
    xp = FakeXpService()
    guild = FakeGuild(1)
    view = XpAdminSettingsView(xp=xp, author_id=123, guild=guild)

    inter = FakeInteraction("xp:wat")
    await view.route_button(inter)

    assert inter.response.deferred is True
    assert inter.response.edits == []