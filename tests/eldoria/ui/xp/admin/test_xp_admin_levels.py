from __future__ import annotations

import sys
import types

import pytest


# ---------- Minimal stubs / shims (complément conftest) ----------
def _ensure_discord_bits() -> None:
    if "discord" not in sys.modules:
        sys.modules["discord"] = types.ModuleType("discord")
    discord = sys.modules["discord"]

    # Base types used in annotations
    for name in ("Guild", "Role", "Embed", "File", "Interaction"):
        if not hasattr(discord, name):
            setattr(discord, name, type(name, (), {}))

    # ButtonStyle
    if not hasattr(discord, "ButtonStyle"):
        class ButtonStyle:  # pragma: no cover
            primary = "primary"
            secondary = "secondary"
        discord.ButtonStyle = ButtonStyle

    # discord.ui namespace + Select / SelectOption
    if not hasattr(discord, "ui"):
        discord.ui = types.SimpleNamespace()

    if not hasattr(discord, "SelectOption"):
        class SelectOption:  # pragma: no cover
            def __init__(self, *, label: str, value: str):
                self.label = label
                self.value = value
        discord.SelectOption = SelectOption

    if not hasattr(discord.ui, "Select"):
        class Select:  # pragma: no cover
            def __init__(self, *, placeholder: str, custom_id: str, options: list, min_values: int, max_values: int, row: int):
                self.placeholder = placeholder
                self.custom_id = custom_id
                self.options = options
                self.min_values = min_values
                self.max_values = max_values
                self.row = row
                self.values: list[str] = []
                self.callback = None
        discord.ui.Select = Select


_ensure_discord_bits()

discord = sys.modules["discord"]


# ---------- Import module under test ----------
import eldoria.ui.xp.admin.levels as mod  # noqa: E402
from eldoria.ui.xp.admin.levels import XpAdminLevelsView  # noqa: E402


# ---------- Local fakes ----------
class FakeRole(discord.Role):  # type: ignore[misc]
    def __init__(self, role_id: int, name: str = "R"):
        self.id = role_id
        self.name = name
        self.mention = f"<@&{role_id}>"


class FakeGuild(discord.Guild):  # type: ignore[misc]
    def __init__(self, guild_id: int):
        self.id = guild_id
        self._roles: dict[int, FakeRole] = {}

    def add_role(self, role: FakeRole):
        self._roles[role.id] = role

    def get_role(self, role_id: int | None):
        if not role_id:
            return None
        return self._roles.get(role_id)


class FakeXpService:
    def __init__(self):
        self.calls: list[tuple] = []
        # levels_with_roles: (level, xp_required, role_id)
        self._levels_with_roles: list[tuple[int, int, int | None]] = [
            (1, 0, None),
            (2, 100, 222),
            (3, 250, None),
            (4, 500, None),
            (5, 1000, None),
        ]

    def ensure_defaults(self, guild_id: int):
        self.calls.append(("ensure_defaults", guild_id))

    def get_levels_with_roles(self, guild_id: int):
        self.calls.append(("get_levels_with_roles", guild_id))
        return list(self._levels_with_roles)

    def upsert_role_id(self, guild_id: int, level: int, role_id: int):
        self.calls.append(("upsert_role_id", guild_id, level, role_id))

    def set_level_threshold(self, guild_id: int, level: int, xp_required: int):
        self.calls.append(("set_level_threshold", guild_id, level, xp_required))


class FakeResponse:
    def __init__(self):
        self.deferred = False
        self.edits: list[dict] = []
        self.modals: list[object] = []

    async def defer(self):
        self.deferred = True

    async def edit_message(self, **kwargs):
        self.edits.append(kwargs)

    async def send_modal(self, modal):
        self.modals.append(modal)


class FakeInteraction(discord.Interaction):  # type: ignore[misc]
    def __init__(self, custom_id: str):
        self.data = {"custom_id": custom_id}
        self.response = FakeResponse()
        self._original_edits: list[dict] = []

    async def edit_original_response(self, **kwargs):
        self._original_edits.append(kwargs)


# ---------- Fixtures: patch external UI dependencies ----------
@pytest.fixture
def _patch_deps(monkeypatch: pytest.MonkeyPatch):
    # BasePanelView / RoutedButton should exist; but we patch them to be predictable
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
    def fake_build_levels_embed(*, levels_with_roles, selected_level, selected_role):
        # Return simple sentinel
        return (("EMBED", levels_with_roles, selected_level, selected_role), ["F"])

    monkeypatch.setattr(mod, "build_xp_admin_levels_embed", fake_build_levels_embed, raising=True)

    # back view stub
    class _FakeMenuView:
        def __init__(self, *, xp, author_id, guild):
            self._ = (xp, author_id, guild)

        def current_embed(self):
            return ("MENU_EMBED", ["F"])

    monkeypatch.setattr(mod, "XpAdminMenuView", _FakeMenuView, raising=True)

    # modal stub (capture callback)
    captured = {}

    class _FakeModal:
        def __init__(self, *, level: int, current_xp: int, on_submit):
            captured["level"] = level
            captured["current_xp"] = current_xp
            captured["on_submit"] = on_submit

    monkeypatch.setattr(mod, "XpLevelThresholdModal", _FakeModal, raising=True)

    return captured


# ---------- Tests: init / current_embed ----------
def test_init_clamps_selected_level_and_resolves_role(_patch_deps):
    xp = FakeXpService()
    guild = FakeGuild(1)
    guild.add_role(FakeRole(222, name="Level2"))

    # selected_level too high -> clamp to 5
    view = XpAdminLevelsView(xp=xp, author_id=123, guild=guild, selected_level=99)
    assert view.selected_level == 5
    assert ("ensure_defaults", 1) in xp.calls
    assert ("get_levels_with_roles", 1) in xp.calls

    # role for level 5 is None in our fake => selected_role None
    assert view.selected_role is None

    # selected_level 2 -> role resolves
    xp.calls.clear()
    view2 = XpAdminLevelsView(xp=xp, author_id=123, guild=guild, selected_level=2)
    assert view2.selected_level == 2
    assert view2.selected_role is not None
    assert view2.selected_role.id == 222

    embed, files = view2.current_embed()
    assert embed[0] == "EMBED"
    assert files == ["F"]
    assert embed[2] == 2  # selected_level passed through
    assert embed[3].id == 222  # selected_role passed through


def test_init_adds_items_buttons_and_select(_patch_deps):
    xp = FakeXpService()
    guild = FakeGuild(1)

    view = XpAdminLevelsView(xp=xp, author_id=123, guild=guild, selected_level=1)

    # children: Back button, Select, Fix XP button (+ maybe RoleSelect if exists)
    # we don't assume RoleSelect exists in stub => at least 3
    assert len(view.children) >= 3

    back = view.children[0]
    assert getattr(back, "custom_id") == "xp:back"

    sel = view.children[1]
    assert sel.custom_id == "xp:levels:pick"
    assert "Niveau sélectionné : 1" in sel.placeholder
    assert len(sel.options) == 5
    assert sel.options[0].label == "Niveau 1"
    assert sel.options[0].value == "1"

    fix = view.children[2]
    assert getattr(fix, "custom_id") == "xp:levels:set_xp"


# ---------- Tests: select callback (level pick) ----------
@pytest.mark.asyncio
async def test_level_select_callback_edits_message_with_new_view(_patch_deps):
    xp = FakeXpService()
    guild = FakeGuild(1)

    view = XpAdminLevelsView(xp=xp, author_id=123, guild=guild, selected_level=1)
    level_select = view.children[1]
    level_select.values = ["3"]

    inter = FakeInteraction("xp:levels:pick")
    await level_select.callback(inter)  # type: ignore[misc]

    assert inter.response.edits
    last = inter.response.edits[-1]
    assert last["embed"][0] == "EMBED"
    assert isinstance(last["view"], XpAdminLevelsView)
    assert last["view"].selected_level == 3


@pytest.mark.asyncio
async def test_level_select_callback_invalid_value_defers(_patch_deps):
    xp = FakeXpService()
    guild = FakeGuild(1)

    view = XpAdminLevelsView(xp=xp, author_id=123, guild=guild, selected_level=1)
    level_select = view.children[1]
    level_select.values = ["not-an-int"]

    inter = FakeInteraction("xp:levels:pick")
    await level_select.callback(inter)  # type: ignore[misc]

    assert inter.response.deferred is True
    assert inter.response.edits == []


# ---------- Tests: route_button set_xp / back / unknown ----------
@pytest.mark.asyncio
async def test_route_button_set_xp_sends_modal_and_submit_updates_threshold(_patch_deps):
    xp = FakeXpService()
    guild = FakeGuild(1)

    # pick level 2 => current_xp should be 100 from our fake list
    view = XpAdminLevelsView(xp=xp, author_id=123, guild=guild, selected_level=2)

    inter = FakeInteraction("xp:levels:set_xp")
    await view.route_button(inter)

    # modal sent
    assert inter.response.modals
    # captured by fixture
    on_submit = _patch_deps["on_submit"]
    assert _patch_deps["level"] == 2
    assert _patch_deps["current_xp"] == 100

    # simulate submit
    modal_inter = FakeInteraction("modal-submit")
    await on_submit(modal_inter, 333)

    # ensure_defaults + set_level_threshold called
    assert ("ensure_defaults", 1) in xp.calls
    assert ("set_level_threshold", 1, 2, 333) in xp.calls

    # modal_inter response deferred and original response edited
    assert modal_inter.response.deferred is True
    assert modal_inter._original_edits
    assert isinstance(modal_inter._original_edits[-1]["view"], XpAdminLevelsView)


@pytest.mark.asyncio
async def test_route_button_back_edits_to_menu_view(_patch_deps):
    xp = FakeXpService()
    guild = FakeGuild(1)
    view = XpAdminLevelsView(xp=xp, author_id=123, guild=guild, selected_level=1)

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
    view = XpAdminLevelsView(xp=xp, author_id=123, guild=guild, selected_level=1)

    inter = FakeInteraction("xp:levels:wat")
    await view.route_button(inter)

    assert inter.response.deferred is True
    assert inter.response.edits == []