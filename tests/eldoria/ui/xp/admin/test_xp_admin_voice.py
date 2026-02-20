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
            success = "success"
            danger = "danger"
        discord.ButtonStyle = ButtonStyle

    if not hasattr(discord, "ChannelType"):
        class ChannelType:  # pragma: no cover
            text = "text"
            news = "news"
        discord.ChannelType = ChannelType

    if not hasattr(discord, "ui"):
        discord.ui = types.SimpleNamespace()

    if not hasattr(discord.ui, "ChannelSelect"):
        class ChannelSelect:  # pragma: no cover
            def __init__(
                self,
                *,
                placeholder: str,
                custom_id: str,
                channel_types: list,
                min_values: int,
                max_values: int,
                disabled: bool,
                row: int,
            ):
                self.placeholder = placeholder
                self.custom_id = custom_id
                self.channel_types = channel_types
                self.min_values = min_values
                self.max_values = max_values
                self.disabled = disabled
                self.row = row
                self.values = []
                self.callback = None
        discord.ui.ChannelSelect = ChannelSelect


_ensure_discord_bits()
discord = sys.modules["discord"]


# ---------- Import module under test ----------
import eldoria.ui.xp.admin.voice as mod  # noqa: E402
from eldoria.ui.xp.admin.voice import XpAdminVoiceView  # noqa: E402


# ---------- Fakes ----------
class FakeChannel:
    def __init__(self, channel_id: int, *, name: str = "general", mention: str | None = None):
        self.id = channel_id
        self.name = name
        self.mention = mention or f"<#{channel_id}>"


class FakeGuild(discord.Guild):  # type: ignore[misc]
    def __init__(self, guild_id: int):
        self.id = guild_id
        self._channels: dict[int, FakeChannel] = {}

    def add_channel(self, ch: FakeChannel):
        self._channels[ch.id] = ch

    def get_channel(self, channel_id: int):
        return self._channels.get(channel_id)


class FakeXpService:
    def __init__(self):
        self.calls: list[tuple] = []
        self._cfg = {
            "enabled": True,
            "voice_enabled": False,
            "voice_levelup_channel_id": 0,
            "voice_interval_seconds": 180,
            "voice_xp_per_interval": 2,
            "voice_daily_cap_xp": 100,
        }

    def ensure_defaults(self, guild_id: int):
        self.calls.append(("ensure_defaults", guild_id))

    def get_config(self, guild_id: int):
        self.calls.append(("get_config", guild_id))
        return dict(self._cfg)

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
        def __init__(self, *, label: str, style, custom_id: str, disabled: bool = False, emoji: str | None = None, row: int = 0):
            self.label = label
            self.style = style
            self.custom_id = custom_id
            self.disabled = disabled
            self.emoji = emoji
            self.row = row

    monkeypatch.setattr(mod, "BasePanelView", _BasePanelView, raising=True)
    monkeypatch.setattr(mod, "RoutedButton", _RoutedButton, raising=True)

    # embed builder stub
    def fake_build_voice_embed(cfg: dict, channel):
        return (("VOICE_EMBED", bool(cfg.get("voice_enabled")), getattr(channel, "id", None)), ["F"])

    monkeypatch.setattr(mod, "build_xp_admin_voice_embed", fake_build_voice_embed, raising=True)

    # menu view stub
    class _FakeMenuView:
        def __init__(self, *, xp, author_id: int, guild):
            self._ = (xp, author_id, guild)

        def current_embed(self):
            return ("MENU_EMBED", ["F"])

    monkeypatch.setattr(mod, "XpAdminMenuView", _FakeMenuView, raising=True)

    # modal stub (capture callback + current)
    captured: dict = {}

    class _FakeModal:
        def __init__(self, *, on_submit, current: dict):
            captured["on_submit"] = on_submit
            captured["current"] = current

    monkeypatch.setattr(mod, "XpVoiceModal", _FakeModal, raising=True)
    return captured


# ---------- Tests: init / current_embed ----------
def test_init_builds_buttons_and_channel_select_disabled_when_voice_off(_patch_deps):
    xp = FakeXpService()
    xp._cfg["voice_enabled"] = False
    guild = FakeGuild(1)

    view = XpAdminVoiceView(xp=xp, author_id=123, guild=guild)

    assert ("ensure_defaults", 1) in xp.calls
    assert ("get_config", 1) in xp.calls

    # children: back + on + off + modifier + channel_select
    assert len(view.children) == 5
    assert view.children[0].custom_id == "xp:back"
    assert view.children[1].custom_id == "xp:voice:on"
    assert view.children[2].custom_id == "xp:voice:off"
    assert view.children[3].custom_id == "xp:voice:modal"

    chsel = view.children[4]
    assert chsel.custom_id == "xp:voice:channel"
    assert chsel.disabled is True

    embed, files = view.current_embed()
    assert embed[0] == "VOICE_EMBED"
    assert files == ["F"]


def test_init_channel_select_placeholder_when_channel_configured(_patch_deps):
    xp = FakeXpService()
    xp._cfg["voice_enabled"] = True
    xp._cfg["voice_levelup_channel_id"] = 55

    guild = FakeGuild(1)
    guild.add_channel(FakeChannel(55, name="annonces"))

    view = XpAdminVoiceView(xp=xp, author_id=123, guild=guild)
    chsel = view.children[4]

    assert chsel.disabled is False
    assert "Salon actuel : #annonces" in chsel.placeholder


# ---------- Tests: channel_select callback ----------
@pytest.mark.asyncio
async def test_channel_select_callback_sets_config_and_edits(_patch_deps):
    xp = FakeXpService()
    xp._cfg["voice_enabled"] = True
    guild = FakeGuild(1)
    view = XpAdminVoiceView(xp=xp, author_id=123, guild=guild)

    chsel = view.children[4]
    # simulate selection value object (ChannelSelect returns channel object)
    chosen = FakeChannel(99, name="xp-logs", mention="#xp-logs")
    chsel.values = [chosen]

    inter = FakeInteraction("xp:voice:channel")
    await chsel.callback(inter)  # type: ignore[misc]

    assert ("ensure_defaults", 1) in xp.calls
    assert ("set_config", 1, {"voice_levelup_channel_id": 99}) in xp.calls

    assert inter.response.edits
    last = inter.response.edits[-1]
    assert last["embed"][0] == "VOICE_EMBED"
    assert isinstance(last["view"], XpAdminVoiceView)


@pytest.mark.asyncio
async def test_channel_select_callback_no_values_defers(_patch_deps):
    xp = FakeXpService()
    xp._cfg["voice_enabled"] = True
    guild = FakeGuild(1)
    view = XpAdminVoiceView(xp=xp, author_id=123, guild=guild)

    chsel = view.children[4]
    chsel.values = []

    inter = FakeInteraction("xp:voice:channel")
    await chsel.callback(inter)  # type: ignore[misc]

    assert inter.response.deferred is True
    assert inter.response.edits == []


# ---------- Tests: route_button voice on/off ----------
@pytest.mark.asyncio
async def test_route_button_voice_on_sets_config_and_edits(_patch_deps):
    xp = FakeXpService()
    xp._cfg["voice_enabled"] = False
    guild = FakeGuild(1)
    view = XpAdminVoiceView(xp=xp, author_id=123, guild=guild)

    inter = FakeInteraction("xp:voice:on")
    await view.route_button(inter)

    assert ("ensure_defaults", 1) in xp.calls
    assert ("set_config", 1, {"voice_enabled": True}) in xp.calls
    assert inter.response.edits
    assert isinstance(inter.response.edits[-1]["view"], XpAdminVoiceView)


@pytest.mark.asyncio
async def test_route_button_voice_off_sets_config_and_edits(_patch_deps):
    xp = FakeXpService()
    xp._cfg["voice_enabled"] = True
    guild = FakeGuild(1)
    view = XpAdminVoiceView(xp=xp, author_id=123, guild=guild)

    inter = FakeInteraction("xp:voice:off")
    await view.route_button(inter)

    assert ("ensure_defaults", 1) in xp.calls
    assert ("set_config", 1, {"voice_enabled": False}) in xp.calls
    assert inter.response.edits
    assert isinstance(inter.response.edits[-1]["view"], XpAdminVoiceView)


# ---------- Tests: route_button modal ----------
@pytest.mark.asyncio
async def test_route_button_voice_modal_sends_modal_with_current(_patch_deps):
    xp = FakeXpService()
    xp._cfg["voice_enabled"] = True
    guild = FakeGuild(1)
    view = XpAdminVoiceView(xp=xp, author_id=123, guild=guild)

    inter = FakeInteraction("xp:voice:modal")
    await view.route_button(inter)

    assert inter.response.modals
    assert ("get_config", 1) in xp.calls
    assert callable(_patch_deps["on_submit"])
    assert "voice_interval_seconds" in _patch_deps["current"]


@pytest.mark.asyncio
async def test_modal_submit_no_payload_sends_info(_patch_deps):
    xp = FakeXpService()
    xp._cfg["voice_enabled"] = True
    guild = FakeGuild(1)
    view = XpAdminVoiceView(xp=xp, author_id=123, guild=guild)

    inter = FakeInteraction("xp:voice:modal")
    await view.route_button(inter)
    on_submit = _patch_deps["on_submit"]

    modal_inter = FakeInteraction("modal-submit")
    await on_submit(modal_inter, {"voice_interval_seconds": None, "voice_xp_per_interval": None})

    assert modal_inter.response.messages
    msg = modal_inter.response.messages[-1]
    assert "Aucun champ fourni" in msg["content"]
    assert msg["ephemeral"] is True
    assert not any(c[0] == "set_config" for c in xp.calls)


@pytest.mark.asyncio
async def test_modal_submit_updates_config_and_edits_original(_patch_deps):
    xp = FakeXpService()
    xp._cfg["voice_enabled"] = True
    guild = FakeGuild(1)
    view = XpAdminVoiceView(xp=xp, author_id=123, guild=guild)

    inter = FakeInteraction("xp:voice:modal")
    await view.route_button(inter)
    on_submit = _patch_deps["on_submit"]

    modal_inter = FakeInteraction("modal-submit")
    await on_submit(modal_inter, {"voice_interval_seconds": 300, "voice_xp_per_interval": None})

    assert ("ensure_defaults", 1) in xp.calls
    assert ("set_config", 1, {"voice_interval_seconds": 300}) in xp.calls

    assert modal_inter.response.deferred is True
    assert modal_inter._original_edits
    last = modal_inter._original_edits[-1]
    assert last["embed"][0] == "VOICE_EMBED"
    assert isinstance(last["view"], XpAdminVoiceView)


# ---------- Tests: route_button back / unknown ----------
@pytest.mark.asyncio
async def test_route_button_back_edits_to_menu(_patch_deps):
    xp = FakeXpService()
    guild = FakeGuild(1)
    view = XpAdminVoiceView(xp=xp, author_id=123, guild=guild)

    inter = FakeInteraction("xp:back")
    await view.route_button(inter)

    last = inter.response.edits[-1]
    assert last["embed"] == "MENU_EMBED"
    assert last["view"].__class__.__name__ == "_FakeMenuView"


@pytest.mark.asyncio
async def test_route_button_unknown_defers(_patch_deps):
    xp = FakeXpService()
    guild = FakeGuild(1)
    view = XpAdminVoiceView(xp=xp, author_id=123, guild=guild)

    inter = FakeInteraction("xp:wat")
    await view.route_button(inter)

    assert inter.response.deferred is True
    assert inter.response.edits == []