from __future__ import annotations

import sys
import types

import pytest


# ---------- Minimal discord shims (complément conftest) ----------
def _ensure_discord_ui_bits() -> None:
    if "discord" not in sys.modules:
        sys.modules["discord"] = types.ModuleType("discord")
    discord = sys.modules["discord"]

    if not hasattr(discord, "Interaction"):
        discord.Interaction = type("Interaction", (), {})

    if not hasattr(discord, "ui"):
        discord.ui = types.SimpleNamespace()

    if not hasattr(discord.ui, "Modal"):
        class Modal:  # pragma: no cover
            def __init__(self, *, title: str = ""):
                self.title = title
                self.children = []

            def add_item(self, item):
                self.children.append(item)

        discord.ui.Modal = Modal

    if not hasattr(discord.ui, "InputText"):
        class InputText:  # pragma: no cover
            def __init__(self, *, label: str, placeholder: str = "", required: bool = False, min_length: int = 0, max_length: int = 0):
                self.label = label
                self.placeholder = placeholder
                self.required = required
                self.min_length = min_length
                self.max_length = max_length
                self.value: str | None = None

        discord.ui.InputText = InputText


_ensure_discord_ui_bits()
discord = sys.modules["discord"]


# ---------- Import module under test ----------
import eldoria.ui.xp.admin.modals as mod  # noqa: E402
from eldoria.ui.xp.admin.modals import (  # noqa: E402
    XpLevelThresholdModal,
    XpSettingsModal,
    XpVoiceModal,
    _parse_optional_int,
)


# ---------- Fakes ----------
class FakeResponse:
    def __init__(self):
        self.messages: list[dict] = []
        self.deferred = False

    async def send_message(self, content: str, ephemeral: bool = False):
        self.messages.append({"content": content, "ephemeral": ephemeral})

    async def defer(self):
        self.deferred = True


class FakeInteraction(discord.Interaction):  # type: ignore[misc]
    def __init__(self):
        self.response = FakeResponse()


# ---------- Tests: _parse_optional_int ----------
def test_parse_optional_int_none_or_blank():
    assert _parse_optional_int(None) is None
    assert _parse_optional_int("") is None
    assert _parse_optional_int("   ") is None


def test_parse_optional_int_valid():
    assert _parse_optional_int("0") == 0
    assert _parse_optional_int("  42 ") == 42


def test_parse_optional_int_invalid_raises():
    with pytest.raises(ValueError):
        _parse_optional_int("nope")


# ---------- Tests: XpSettingsModal.callback ----------
@pytest.mark.asyncio
async def test_settings_modal_invalid_integer_sends_error(monkeypatch: pytest.MonkeyPatch):
    # Ensure validate_int_ranges doesn't matter (should fail before)
    monkeypatch.setattr(mod, "validate_int_ranges", lambda *_a, **_k: [], raising=True)

    called = {"submit": 0}

    async def on_submit(_inter, _payload):
        called["submit"] += 1

    m = XpSettingsModal(
        on_submit=on_submit,
        current={"points_per_message": 1, "cooldown_seconds": 2, "bonus_percent": 3, "karuta_k_small_percent": 4},
    )
    m.points_per_message.value = "abc"  # invalid

    inter = FakeInteraction()
    await m.callback(inter)

    assert called["submit"] == 0
    assert inter.response.messages
    assert "Valeur invalide" in inter.response.messages[-1]["content"]
    assert inter.response.messages[-1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_settings_modal_range_errors_sends_list(monkeypatch: pytest.MonkeyPatch):
    # Force validation errors
    monkeypatch.setattr(mod, "XP_SETTINGS_RULES", {"dummy": (0, 1)}, raising=False)
    monkeypatch.setattr(mod, "validate_int_ranges", lambda payload, rules: ["err1", "err2"], raising=True)

    async def on_submit(_inter, _payload):
        raise AssertionError("should not call submit when errors")

    m = XpSettingsModal(on_submit=on_submit, current={})
    m.points_per_message.value = "1"
    m.cooldown_seconds.value = ""      # -> None
    m.bonus_percent.value = "2"
    m.karuta_k_small_percent.value = "3"

    inter = FakeInteraction()
    await m.callback(inter)

    msg = inter.response.messages[-1]["content"]
    assert "Paramètres invalides" in msg
    assert "err1" in msg and "err2" in msg
    assert inter.response.messages[-1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_settings_modal_success_calls_submit(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(mod, "validate_int_ranges", lambda *_a, **_k: [], raising=True)

    received = {}

    async def on_submit(_inter, payload):
        received["payload"] = payload

    m = XpSettingsModal(on_submit=on_submit, current={})
    m.points_per_message.value = "5"
    m.cooldown_seconds.value = "10"
    m.bonus_percent.value = ""  # -> None
    m.karuta_k_small_percent.value = "30"

    inter = FakeInteraction()
    await m.callback(inter)

    assert received["payload"] == {
        "points_per_message": 5,
        "cooldown_seconds": 10,
        "bonus_percent": None,
        "karuta_k_small_percent": 30,
    }
    assert inter.response.messages == []


# ---------- Tests: XpVoiceModal.callback ----------
@pytest.mark.asyncio
async def test_voice_modal_invalid_integer_sends_error(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(mod, "validate_int_ranges", lambda *_a, **_k: [], raising=True)

    called = {"submit": 0}

    async def on_submit(_inter, _payload):
        called["submit"] += 1

    m = XpVoiceModal(on_submit=on_submit, current={})
    m.voice_interval_seconds.value = "x"  # invalid

    inter = FakeInteraction()
    await m.callback(inter)

    assert called["submit"] == 0
    assert "Valeur invalide" in inter.response.messages[-1]["content"]
    assert inter.response.messages[-1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_voice_modal_range_errors_sends_list(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(mod, "XP_VOICE_RULES", {"dummy": (0, 1)}, raising=False)
    monkeypatch.setattr(mod, "validate_int_ranges", lambda payload, rules: ["bad"], raising=True)

    async def on_submit(_inter, _payload):
        raise AssertionError("should not call submit when errors")

    m = XpVoiceModal(on_submit=on_submit, current={})
    m.voice_interval_seconds.value = "30"
    m.voice_xp_per_interval.value = "2"
    m.voice_daily_cap_xp.value = "100"

    inter = FakeInteraction()
    await m.callback(inter)

    msg = inter.response.messages[-1]["content"]
    assert "Paramètres invalides" in msg
    assert "bad" in msg
    assert inter.response.messages[-1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_voice_modal_success_calls_submit(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(mod, "validate_int_ranges", lambda *_a, **_k: [], raising=True)

    received = {}

    async def on_submit(_inter, payload):
        received["payload"] = payload

    m = XpVoiceModal(on_submit=on_submit, current={})
    m.voice_interval_seconds.value = "180"
    m.voice_xp_per_interval.value = ""  # -> None
    m.voice_daily_cap_xp.value = "200"

    inter = FakeInteraction()
    await m.callback(inter)

    assert received["payload"] == {
        "voice_interval_seconds": 180,
        "voice_xp_per_interval": None,
        "voice_daily_cap_xp": 200,
    }
    assert inter.response.messages == []


# ---------- Tests: XpLevelThresholdModal.callback ----------
@pytest.mark.asyncio
async def test_level_threshold_modal_invalid_non_int_sends_error():
    called = {"submit": 0}

    async def on_submit(_inter, _val: int):
        called["submit"] += 1

    m = XpLevelThresholdModal(level=2, current_xp=100, on_submit=on_submit)
    m.xp_required.value = "abc"  # invalid

    inter = FakeInteraction()
    await m.callback(inter)

    assert called["submit"] == 0
    assert "XP requis invalide" in inter.response.messages[-1]["content"]
    assert inter.response.messages[-1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_level_threshold_modal_invalid_negative_sends_error():
    called = {"submit": 0}

    async def on_submit(_inter, _val: int):
        called["submit"] += 1

    m = XpLevelThresholdModal(level=2, current_xp=100, on_submit=on_submit)
    m.xp_required.value = "-1"

    inter = FakeInteraction()
    await m.callback(inter)

    assert called["submit"] == 0
    assert "XP requis invalide" in inter.response.messages[-1]["content"]


@pytest.mark.asyncio
async def test_level_threshold_modal_success_calls_submit():
    received = {}

    async def on_submit(_inter, val: int):
        received["val"] = val

    m = XpLevelThresholdModal(level=3, current_xp=250, on_submit=on_submit)
    m.xp_required.value = " 300 "

    inter = FakeInteraction()
    await m.callback(inter)

    assert received["val"] == 300
    assert inter.response.messages == []