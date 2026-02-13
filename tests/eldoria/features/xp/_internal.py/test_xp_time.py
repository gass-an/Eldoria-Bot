from datetime import datetime

from eldoria.features.xp._internal import time as mod  # <-- adapte si nom différent


def test_day_key_with_explicit_timestamp_does_not_call_now_ts(monkeypatch):
    # Si ts est fourni, now_ts ne doit pas être utilisé
    monkeypatch.setattr(mod, "now_ts", lambda: (_ for _ in ()).throw(AssertionError("now_ts should not be called")))

    # 1er janvier 2024 00:00:00 UTC
    ts = 1704067200
    key = mod.day_key_utc(ts)

    expected = datetime.fromtimestamp(ts, tz=mod.TIMEZONE).strftime("%Y%m%d")
    assert key == expected


def test_day_key_uses_now_ts_when_ts_is_none(monkeypatch):
    ts = 1704067200  # 2024-01-01
    monkeypatch.setattr(mod, "now_ts", lambda: ts)

    key = mod.day_key_utc()

    expected = datetime.fromtimestamp(ts, tz=mod.TIMEZONE).strftime("%Y%m%d")
    assert key == expected


def test_day_key_timezone_effect(monkeypatch):
    """
    Vérifie que la timezone TIMEZONE est bien utilisée.
    """
    # Timestamp proche d'un changement de jour UTC
    ts = 1704067199  # 2023-12-31 23:59:59 UTC

    monkeypatch.setattr(mod, "now_ts", lambda: ts)

    key = mod.day_key_utc()

    expected = datetime.fromtimestamp(ts, tz=mod.TIMEZONE).strftime("%Y%m%d")
    assert key == expected


def test_day_key_boundary_crossing(monkeypatch):
    """
    Test autour d'un changement de jour.
    """
    # 23:59:59 puis +1 seconde
    ts_before = 1704067199
    ts_after = ts_before + 1

    key_before = mod.day_key_utc(ts_before)
    key_after = mod.day_key_utc(ts_after)

    expected_before = datetime.fromtimestamp(ts_before, tz=mod.TIMEZONE).strftime("%Y%m%d")
    expected_after = datetime.fromtimestamp(ts_after, tz=mod.TIMEZONE).strftime("%Y%m%d")

    assert key_before == expected_before
    assert key_after == expected_after
