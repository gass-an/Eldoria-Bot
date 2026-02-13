import datetime

import pytest

import eldoria.utils.timestamp as ts_mod
from eldoria.utils.timestamp import add_duration, now_ts

# ------------------------------------------------------------
# now_ts
# ------------------------------------------------------------

def test_now_ts_returns_int(monkeypatch):
    fake_now = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.UTC)

    class FakeDateTime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return fake_now

    monkeypatch.setattr(ts_mod, "datetime", FakeDateTime)

    result = now_ts()

    assert isinstance(result, int)
    assert result == int(fake_now.timestamp())


# ------------------------------------------------------------
# add_duration
# ------------------------------------------------------------

def test_add_duration_seconds():
    base = 1000
    assert add_duration(base, seconds=30) == 1030


def test_add_duration_minutes():
    base = 1000
    assert add_duration(base, minutes=2) == 1000 + 120


def test_add_duration_hours():
    base = 1000
    assert add_duration(base, hours=1) == 1000 + 3600


def test_add_duration_days():
    base = 1000
    assert add_duration(base, days=1) == 1000 + 86400


def test_add_duration_combined():
    base = 1000
    result = add_duration(base, seconds=10, minutes=1, hours=1, days=1)
    expected = 1000 + 10 + 60 + 3600 + 86400
    assert result == expected


def test_add_duration_zero_returns_same_timestamp():
    base = 1000
    assert add_duration(base) == base


@pytest.mark.parametrize(
    "kwargs",
    [
        {"seconds": -1},
        {"minutes": -1},
        {"hours": -1},
        {"days": -1},
    ],
)
def test_add_duration_rejects_negative_values(kwargs):
    with pytest.raises(ValueError):
        add_duration(1000, **kwargs)
