from __future__ import annotations

import pytest

# ---------- Import module under test ----------
import eldoria.ui.xp.admin.voice as mod  # noqa: E402
from eldoria.ui.xp.admin.voice import XpAdminVoiceView  # noqa: E402
from tests._fakes import FakeChannel, FakeGuild, FakeInteraction, FakeUser, FakeXpService
from tests._support.xp_admin_stubs import BasePanelViewStub, RoutedButtonStub

 # ---------- Helpers (no local `class` allowed) ----------


def _make_inter(custom_id: str) -> FakeInteraction:
    return FakeInteraction(user=FakeUser(1), data={"custom_id": custom_id})


# ---------- Fixture: patch deps ----------
@pytest.fixture
def _patch_deps(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(mod, "BasePanelView", BasePanelViewStub, raising=True)
    monkeypatch.setattr(mod, "RoutedButton", RoutedButtonStub, raising=True)

    # embed builder stub
    def fake_build_voice_embed(cfg: dict, channel):
        return (("VOICE_EMBED", bool(cfg.get("voice_enabled")), getattr(channel, "id", None)), ["F"])

    monkeypatch.setattr(mod, "build_xp_admin_voice_embed", fake_build_voice_embed, raising=True)

    # menu view stub
    MenuViewStub = type(
        "MenuViewStub",
        (),
        {
            "__init__": lambda self, *, xp, author_id, guild: setattr(self, "_", (xp, author_id, guild)),
            "current_embed": lambda self: ("MENU_EMBED", ["F"]),
        },
    )
    monkeypatch.setattr(mod, "XpAdminMenuView", MenuViewStub, raising=True)

    # modal stub (capture callback + current)
    captured: dict = {}

    ModalStub = type(
        "ModalStub",
        (),
        {
            "__init__": lambda self, *, on_submit, current: captured.update(
                {"on_submit": on_submit, "current": current}
            )
        },
    )
    monkeypatch.setattr(mod, "XpVoiceModal", ModalStub, raising=True)
    return captured


# ---------- Tests: init / current_embed ----------
def test_init_builds_buttons_and_channel_select_disabled_when_voice_off(_patch_deps):
    xp = FakeXpService()
    xp._voice_cfg["voice_enabled"] = False
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
    xp._voice_cfg["voice_enabled"] = True
    xp._voice_cfg["voice_levelup_channel_id"] = 55

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
    xp._voice_cfg["voice_enabled"] = True
    guild = FakeGuild(1)
    view = XpAdminVoiceView(xp=xp, author_id=123, guild=guild)

    chsel = view.children[4]
    # simulate selection value object (ChannelSelect returns channel object)
    chosen = FakeChannel(99, name="xp-logs", mention="#xp-logs")
    chsel.values = [chosen]

    inter = _make_inter("xp:voice:channel")
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
    xp._voice_cfg["voice_enabled"] = True
    guild = FakeGuild(1)
    view = XpAdminVoiceView(xp=xp, author_id=123, guild=guild)

    chsel = view.children[4]
    chsel.values = []

    inter = _make_inter("xp:voice:channel")
    await chsel.callback(inter)  # type: ignore[misc]

    assert inter.response.deferred is True
    assert inter.response.edits == []


# ---------- Tests: route_button voice on/off ----------
@pytest.mark.asyncio
async def test_route_button_voice_on_sets_config_and_edits(_patch_deps):
    xp = FakeXpService()
    xp._voice_cfg["voice_enabled"] = False
    guild = FakeGuild(1)
    view = XpAdminVoiceView(xp=xp, author_id=123, guild=guild)

    inter = _make_inter("xp:voice:on")
    await view.route_button(inter)

    assert ("ensure_defaults", 1) in xp.calls
    assert ("set_config", 1, {"voice_enabled": True}) in xp.calls
    assert inter.response.edits
    assert isinstance(inter.response.edits[-1]["view"], XpAdminVoiceView)


@pytest.mark.asyncio
async def test_route_button_voice_off_sets_config_and_edits(_patch_deps):
    xp = FakeXpService()
    xp._voice_cfg["voice_enabled"] = True
    guild = FakeGuild(1)
    view = XpAdminVoiceView(xp=xp, author_id=123, guild=guild)

    inter = _make_inter("xp:voice:off")
    await view.route_button(inter)

    assert ("ensure_defaults", 1) in xp.calls
    assert ("set_config", 1, {"voice_enabled": False}) in xp.calls
    assert inter.response.edits
    assert isinstance(inter.response.edits[-1]["view"], XpAdminVoiceView)


# ---------- Tests: route_button modal ----------
@pytest.mark.asyncio
async def test_route_button_voice_modal_sends_modal_with_current(_patch_deps):
    xp = FakeXpService()
    xp._voice_cfg["voice_enabled"] = True
    guild = FakeGuild(1)
    view = XpAdminVoiceView(xp=xp, author_id=123, guild=guild)

    inter = _make_inter("xp:voice:modal")
    await view.route_button(inter)

    assert inter.response.modals
    assert ("get_config", 1) in xp.calls
    assert callable(_patch_deps["on_submit"])
    assert "voice_interval_seconds" in _patch_deps["current"]


@pytest.mark.asyncio
async def test_modal_submit_no_payload_sends_info(_patch_deps):
    xp = FakeXpService()
    xp._voice_cfg["voice_enabled"] = True
    guild = FakeGuild(1)
    view = XpAdminVoiceView(xp=xp, author_id=123, guild=guild)

    inter = _make_inter("xp:voice:modal")
    await view.route_button(inter)
    on_submit = _patch_deps["on_submit"]

    modal_inter = _make_inter("modal-submit")
    await on_submit(modal_inter, {"voice_interval_seconds": None, "voice_xp_per_interval": None})

    assert modal_inter.response.sent
    msg = modal_inter.response.sent[-1]
    assert "Aucun champ fourni" in msg["content"]
    assert msg["ephemeral"] is True
    assert not any(c[0] == "set_config" for c in xp.calls)


@pytest.mark.asyncio
async def test_modal_submit_updates_config_and_edits_original(_patch_deps):
    xp = FakeXpService()
    xp._voice_cfg["voice_enabled"] = True
    guild = FakeGuild(1)
    view = XpAdminVoiceView(xp=xp, author_id=123, guild=guild)

    inter = _make_inter("xp:voice:modal")
    await view.route_button(inter)
    on_submit = _patch_deps["on_submit"]

    modal_inter = _make_inter("modal-submit")
    await on_submit(modal_inter, {"voice_interval_seconds": 300, "voice_xp_per_interval": None})

    assert ("ensure_defaults", 1) in xp.calls
    assert ("set_config", 1, {"voice_interval_seconds": 300}) in xp.calls

    assert modal_inter.response.deferred is True
    assert modal_inter.original_edits
    last = modal_inter.original_edits[-1]
    assert last["embed"][0] == "VOICE_EMBED"
    assert isinstance(last["view"], XpAdminVoiceView)


# ---------- Tests: route_button back / unknown ----------
@pytest.mark.asyncio
async def test_route_button_back_edits_to_menu(_patch_deps):
    xp = FakeXpService()
    guild = FakeGuild(1)
    view = XpAdminVoiceView(xp=xp, author_id=123, guild=guild)

    inter = _make_inter("xp:back")
    await view.route_button(inter)

    last = inter.response.edits[-1]
    assert last["embed"] == "MENU_EMBED"
    assert last["view"].__class__.__name__ == "MenuViewStub"


@pytest.mark.asyncio
async def test_route_button_unknown_defers(_patch_deps):
    xp = FakeXpService()
    guild = FakeGuild(1)
    view = XpAdminVoiceView(xp=xp, author_id=123, guild=guild)

    inter = _make_inter("xp:wat")
    await view.route_button(inter)

    assert inter.response.deferred is True
    assert inter.response.edits == []