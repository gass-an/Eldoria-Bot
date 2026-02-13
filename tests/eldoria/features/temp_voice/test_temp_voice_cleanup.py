from __future__ import annotations

import eldoria.features.temp_voice.cleanup as cleanup_mod
from eldoria.features.temp_voice.cleanup import cleanup_temp_channels


class FakeGuild:
    def __init__(self, guild_id: int, existing_channel_ids: set[int]):
        self.id = guild_id
        self._existing = set(existing_channel_ids)

    def get_channel(self, channel_id: int):
        return object() if channel_id in self._existing else None


class FakeBot:
    def __init__(self, guilds):
        self.guilds = list(guilds)


def test_cleanup_temp_channels_does_nothing_when_no_guilds(monkeypatch):
    bot = FakeBot(guilds=[])

    calls = {"list": 0, "remove": 0}

    monkeypatch.setattr(
        cleanup_mod,
        "tv_list_active_all",
        lambda guild_id: calls.__setitem__("list", calls["list"] + 1) or [],
    )
    monkeypatch.setattr(
        cleanup_mod,
        "tv_remove_active",
        lambda *a, **k: calls.__setitem__("remove", calls["remove"] + 1),
    )

    cleanup_temp_channels(bot)

    assert calls["list"] == 0
    assert calls["remove"] == 0


def test_cleanup_temp_channels_removes_only_missing_channels(monkeypatch):
    g1 = FakeGuild(guild_id=1, existing_channel_ids={100})
    bot = FakeBot(guilds=[g1])

    monkeypatch.setattr(cleanup_mod, "tv_list_active_all", lambda guild_id: [(10, 100), (10, 101)])

    removed: list[tuple[int, int, int]] = []
    monkeypatch.setattr(
        cleanup_mod,
        "tv_remove_active",
        lambda gid, parent_id, channel_id: removed.append((gid, parent_id, channel_id)),
    )

    cleanup_temp_channels(bot)

    assert removed == [(1, 10, 101)]


def test_cleanup_temp_channels_handles_multiple_guilds(monkeypatch):
    g1 = FakeGuild(guild_id=1, existing_channel_ids={200})
    g2 = FakeGuild(guild_id=2, existing_channel_ids=set())
    bot = FakeBot(guilds=[g1, g2])

    def fake_list(guild_id: int):
        if guild_id == 1:
            return [(20, 200), (20, 201)]
        if guild_id == 2:
            return [(30, 300), (31, 301)]
        return []

    monkeypatch.setattr(cleanup_mod, "tv_list_active_all", fake_list)

    removed: list[tuple[int, int, int]] = []
    monkeypatch.setattr(
        cleanup_mod,
        "tv_remove_active",
        lambda gid, parent_id, channel_id: removed.append((gid, parent_id, channel_id)),
    )

    cleanup_temp_channels(bot)

    assert removed == [
        (1, 20, 201),
        (2, 30, 300),
        (2, 31, 301),
    ]


def test_cleanup_temp_channels_does_not_remove_when_all_exist(monkeypatch):
    g = FakeGuild(guild_id=1, existing_channel_ids={100, 101, 102})
    bot = FakeBot(guilds=[g])

    monkeypatch.setattr(cleanup_mod, "tv_list_active_all", lambda guild_id: [(10, 100), (10, 101), (11, 102)])

    removed: list[tuple[int, int, int]] = []
    monkeypatch.setattr(
        cleanup_mod,
        "tv_remove_active",
        lambda gid, parent_id, channel_id: removed.append((gid, parent_id, channel_id)),
    )

    cleanup_temp_channels(bot)

    assert removed == []
