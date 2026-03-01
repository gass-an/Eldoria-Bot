from __future__ import annotations

import pytest

# ---------- Import module under test ----------
import eldoria.ui.xp.admin.settings as mod  # noqa: E402
from eldoria.ui.xp.admin.settings import XpAdminSettingsView  # noqa: E402
from tests._fakes import FakeGuild, FakeInteraction, FakeUser, FakeXpService
from tests._support.xp_admin_stubs import BasePanelViewStub, RoutedButtonStub


# ---------- Fixture: patch deps ----------
@pytest.fixture
def _patch_deps(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(mod, "BasePanelView", BasePanelViewStub, raising=True)
    monkeypatch.setattr(mod, "RoutedButton", RoutedButtonStub, raising=True)

    # embed builder stub
    def fake_build_settings_embed(cfg: dict):
        return (("SETTINGS_EMBED", cfg.get("points_per_message")), ["F"])

    monkeypatch.setattr(mod, "build_xp_admin_settings_embed", fake_build_settings_embed, raising=True)

    # menu view stub
    def _menu_init(self, *, xp, author_id: int, guild):
        self._ = (xp, author_id, guild)

    def _menu_current(self):
        return ("MENU_EMBED", ["F"])

    MenuViewStub = type("MenuViewStub", (), {"__init__": _menu_init, "current_embed": _menu_current})

    monkeypatch.setattr(mod, "XpAdminMenuView", MenuViewStub, raising=True)

    # modal stub: capture callback + current
    captured: dict = {}

    def _modal_init(self, *, on_submit, current: dict):
        captured["on_submit"] = on_submit
        captured["current"] = current

    ModalStub = type("ModalStub", (), {"__init__": _modal_init})

    monkeypatch.setattr(mod, "XpSettingsModal", ModalStub, raising=True)

    return captured


# ---------- Tests: init / current_embed ----------
def test_init_adds_buttons(_patch_deps):
    xp = FakeXpService()
    xp._cfg = {
        "enabled": True,
        "points_per_message": 3,
        "cooldown_seconds": 10,
        "bonus_percent": 20,
        "karuta_k_small_percent": 30,
    }
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

    inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "xp:set:settings"})
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

    inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "xp:set:settings"})
    await view.route_button(inter)
    on_submit = _patch_deps["on_submit"]

    modal_inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "modal-submit"})

    # payload only None -> should send INFO message, no set_config
    await on_submit(modal_inter, {"points_per_message": None, "bonus_percent": None})

    assert modal_inter.response.sent
    msg = modal_inter.response.sent[-1]
    assert "Aucun champ fourni" in msg["content"]
    assert msg["ephemeral"] is True

    assert not any(c[0] == "set_config" for c in xp.calls)


@pytest.mark.asyncio
async def test_modal_submit_updates_config_and_edits_original(_patch_deps):
    xp = FakeXpService()
    guild = FakeGuild(1)
    view = XpAdminSettingsView(xp=xp, author_id=123, guild=guild)

    inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "xp:set:settings"})
    await view.route_button(inter)
    on_submit = _patch_deps["on_submit"]

    modal_inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "modal-submit"})

    await on_submit(modal_inter, {"points_per_message": 5, "cooldown_seconds": None})

    assert ("ensure_defaults", 1) in xp.calls
    assert ("set_config", 1, {"points_per_message": 5}) in xp.calls

    assert modal_inter.response.deferred is True
    assert modal_inter.original_edits
    last = modal_inter.original_edits[-1]
    assert last["embed"][0] == "SETTINGS_EMBED"
    assert isinstance(last["view"], XpAdminSettingsView)


# ---------- Tests: route_button back / unknown ----------
@pytest.mark.asyncio
async def test_route_button_back_edits_to_menu(_patch_deps):
    xp = FakeXpService()
    guild = FakeGuild(1)
    view = XpAdminSettingsView(xp=xp, author_id=123, guild=guild)

    inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "xp:back"})
    await view.route_button(inter)

    assert inter.response.edits
    last = inter.response.edits[-1]
    assert last["embed"] == "MENU_EMBED"
    assert last["view"].__class__.__name__ == "MenuViewStub"


@pytest.mark.asyncio
async def test_route_button_unknown_defers(_patch_deps):
    xp = FakeXpService()
    guild = FakeGuild(1)
    view = XpAdminSettingsView(xp=xp, author_id=123, guild=guild)

    inter = FakeInteraction(user=FakeUser(1), data={"custom_id": "xp:wat"})
    await view.route_button(inter)

    assert inter.response.deferred is True
    assert inter.response.edits == []