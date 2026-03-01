from __future__ import annotations

import pytest

# ---------- Import module under test ----------
import eldoria.ui.xp.admin.levels as mod  # noqa: E402
from eldoria.ui.xp.admin.levels import XpAdminLevelsView  # noqa: E402
from tests._fakes import FakeGuild, FakeInteraction, FakeRole, FakeUser, FakeXpService
from tests._support.xp_admin_stubs import BasePanelViewStub, RoutedButtonStub


# ---------- Fixtures: patch external UI dependencies ----------
@pytest.fixture
def _patch_deps(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(mod, "BasePanelView", BasePanelViewStub, raising=True)
    monkeypatch.setattr(mod, "RoutedButton", RoutedButtonStub, raising=True)

    # embed builder stub
    def fake_build_levels_embed(*, levels_with_roles, selected_level, selected_role):
        # Return simple sentinel
        return (("EMBED", levels_with_roles, selected_level, selected_role), ["F"])

    monkeypatch.setattr(mod, "build_xp_admin_levels_embed", fake_build_levels_embed, raising=True)

    # back view stub
    def _menu_init(self, *, xp, author_id, guild):
        self._ = (xp, author_id, guild)

    def _menu_current_embed(self):
        return ("MENU_EMBED", ["F"])

    MenuViewStub = type("MenuViewStub", (), {"__init__": _menu_init, "current_embed": _menu_current_embed})

    monkeypatch.setattr(mod, "XpAdminMenuView", MenuViewStub, raising=True)

    # modal stub (capture callback)
    captured = {}

    def _modal_init(self, *, level: int, current_xp: int, on_submit):
        captured["level"] = level
        captured["current_xp"] = current_xp
        captured["on_submit"] = on_submit

    ModalStub = type("ModalStub", (), {"__init__": _modal_init})

    monkeypatch.setattr(mod, "XpLevelThresholdModal", ModalStub, raising=True)

    return captured


# ---------- Tests: init / current_embed ----------
def test_init_clamps_selected_level_and_resolves_role(_patch_deps):
    xp = FakeXpService()
    xp._levels_with_roles = [
        (1, 0, None),
        (2, 100, 222),
        (3, 250, None),
        (4, 500, None),
        (5, 1000, None),
    ]
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
    xp._levels_with_roles = [
        (1, 0, None),
        (2, 100, 222),
        (3, 250, None),
        (4, 500, None),
        (5, 1000, None),
    ]
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
    xp._levels_with_roles = [
        (1, 0, None),
        (2, 100, 222),
        (3, 250, None),
        (4, 500, None),
        (5, 1000, None),
    ]
    guild = FakeGuild(1)

    view = XpAdminLevelsView(xp=xp, author_id=123, guild=guild, selected_level=1)
    level_select = view.children[1]
    level_select.values = ["3"]

    inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "xp:levels:pick"})
    await level_select.callback(inter)  # type: ignore[misc]

    assert inter.response.edits
    last = inter.response.edits[-1]
    assert last["embed"][0] == "EMBED"
    assert isinstance(last["view"], XpAdminLevelsView)
    assert last["view"].selected_level == 3


@pytest.mark.asyncio
async def test_level_select_callback_invalid_value_defers(_patch_deps):
    xp = FakeXpService()
    xp._levels_with_roles = [
        (1, 0, None),
        (2, 100, 222),
        (3, 250, None),
        (4, 500, None),
        (5, 1000, None),
    ]
    guild = FakeGuild(1)

    view = XpAdminLevelsView(xp=xp, author_id=123, guild=guild, selected_level=1)
    level_select = view.children[1]
    level_select.values = ["not-an-int"]

    inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "xp:levels:pick"})
    await level_select.callback(inter)  # type: ignore[misc]

    assert inter.response.deferred is True
    assert inter.response.edits == []


# ---------- Tests: route_button set_xp / back / unknown ----------
@pytest.mark.asyncio
async def test_route_button_set_xp_sends_modal_and_submit_updates_threshold(_patch_deps):
    xp = FakeXpService()
    xp._levels_with_roles = [
        (1, 0, None),
        (2, 100, 222),
        (3, 250, None),
        (4, 500, None),
        (5, 1000, None),
    ]
    guild = FakeGuild(1)

    # pick level 2 => current_xp should be 100 from our fake list
    view = XpAdminLevelsView(xp=xp, author_id=123, guild=guild, selected_level=2)

    inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "xp:levels:set_xp"})
    await view.route_button(inter)

    # modal sent
    assert inter.response.modals
    # captured by fixture
    on_submit = _patch_deps["on_submit"]
    assert _patch_deps["level"] == 2
    assert _patch_deps["current_xp"] == 100

    # simulate submit
    modal_inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "modal-submit"})
    await on_submit(modal_inter, 333)

    # ensure_defaults + set_level_threshold called
    assert ("ensure_defaults", 1) in xp.calls
    assert ("set_level_threshold", 1, 2, 333) in xp.calls

    # modal_inter response deferred and original response edited
    assert modal_inter.response.deferred is True
    assert modal_inter.original_edits
    assert isinstance(modal_inter.original_edits[-1]["view"], XpAdminLevelsView)


@pytest.mark.asyncio
async def test_route_button_back_edits_to_menu_view(_patch_deps):
    xp = FakeXpService()
    xp._levels_with_roles = [(1, 0, None)]
    guild = FakeGuild(1)
    view = XpAdminLevelsView(xp=xp, author_id=123, guild=guild, selected_level=1)

    inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "xp:back"})
    await view.route_button(inter)

    assert inter.response.edits
    last = inter.response.edits[-1]
    assert last["embed"] == "MENU_EMBED"
    assert last["view"].__class__.__name__ == "MenuViewStub"


@pytest.mark.asyncio
async def test_route_button_unknown_defers(_patch_deps):
    xp = FakeXpService()
    xp._levels_with_roles = [(1, 0, None)]
    guild = FakeGuild(1)
    view = XpAdminLevelsView(xp=xp, author_id=123, guild=guild, selected_level=1)

    inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "xp:levels:wat"})
    await view.route_button(inter)

    assert inter.response.deferred is True
    assert inter.response.edits == []