from __future__ import annotations

from eldoria.features.xp._internal import snapshot as mod


class FakeGuild:
    def __init__(self, guild_id: int = 123):
        self.id = guild_id


def test_build_snapshot_nominal_next_level_found(monkeypatch):
    guild = FakeGuild(123)
    user_id = 42

    # DB
    monkeypatch.setattr(mod, "xp_get_member", lambda gid, uid: (150, 0))
    levels = [(1, 0), (2, 100), (3, 250)]
    monkeypatch.setattr(mod, "xp_get_levels", lambda gid: levels)
    role_ids = {1: 111, 2: 222, 3: 333}
    monkeypatch.setattr(mod, "xp_get_role_ids", lambda gid: role_ids)

    # compute_level => lvl2 (et donc next = lvl3)
    monkeypatch.setattr(mod, "compute_level", lambda xp, lvls: 2)

    # level_label doit être appelé 2 fois: lvl et lvl+1
    label_calls: list[int] = []

    def fake_level_label(g, rids, lvl):
        assert g is guild
        assert rids is role_ids
        label_calls.append(lvl)
        return f"@level{lvl}"

    monkeypatch.setattr(mod, "level_label", fake_level_label)

    snap = mod.build_snapshot_for_xp_profile(guild, user_id)

    assert snap["xp"] == 150
    assert snap["level"] == 2
    assert snap["level_label"] == "@level2"
    assert snap["next_level_label"] == "@level3"
    assert snap["next_xp_required"] == 250
    assert label_calls == [2, 3]


def test_build_snapshot_no_next_level(monkeypatch):
    guild = FakeGuild(123)
    user_id = 42

    monkeypatch.setattr(mod, "xp_get_member", lambda gid, uid: (999, 0))
    levels = [(1, 0), (2, 100)]
    monkeypatch.setattr(mod, "xp_get_levels", lambda gid: levels)
    monkeypatch.setattr(mod, "xp_get_role_ids", lambda gid: {1: 111, 2: 222})
    monkeypatch.setattr(mod, "compute_level", lambda xp, lvls: 2)

    monkeypatch.setattr(mod, "level_label", lambda g, rids, lvl: f"@level{lvl}")

    snap = mod.build_snapshot_for_xp_profile(guild, user_id)

    assert snap["level"] == 2
    assert snap["level_label"] == "@level2"
    assert snap["next_level_label"] is None
    assert snap["next_xp_required"] is None


def test_build_snapshot_levels_empty(monkeypatch):
    guild = FakeGuild(123)
    user_id = 42

    monkeypatch.setattr(mod, "xp_get_member", lambda gid, uid: (0, 0))
    monkeypatch.setattr(mod, "xp_get_levels", lambda gid: [])
    monkeypatch.setattr(mod, "xp_get_role_ids", lambda gid: {})
    # compute_level appelé avec levels vides => renvoie 1 dans ton impl actuelle
    monkeypatch.setattr(mod, "compute_level", lambda xp, lvls: 1)

    calls = []

    def fake_level_label(g, rids, lvl):
        calls.append(lvl)
        return "Niveau 0"

    monkeypatch.setattr(mod, "level_label", fake_level_label)

    snap = mod.build_snapshot_for_xp_profile(guild, user_id)

    assert snap == {
        "xp": 0,
        "level": 1,
        "level_label": "Niveau 0",
        "next_level_label": None,
        "next_xp_required": None,
    }
    assert calls == [1]  # pas de next lookup


def test_build_snapshot_gap_in_levels_no_next_even_if_higher_exists(monkeypatch):
    """
    Si levels contient un trou (ex: lvl1 puis lvl3), l'algo cherche strictement lvl+1.
    Donc lvl=1 => pas de next (lvl2 absent).
    """
    guild = FakeGuild(123)
    user_id = 42

    monkeypatch.setattr(mod, "xp_get_member", lambda gid, uid: (50, 0))
    monkeypatch.setattr(mod, "xp_get_levels", lambda gid: [(1, 0), (3, 200)])
    monkeypatch.setattr(mod, "xp_get_role_ids", lambda gid: {1: 111, 3: 333})
    monkeypatch.setattr(mod, "compute_level", lambda xp, lvls: 1)
    monkeypatch.setattr(mod, "level_label", lambda g, rids, lvl: f"@level{lvl}")

    snap = mod.build_snapshot_for_xp_profile(guild, user_id)

    assert snap["level"] == 1
    assert snap["next_level_label"] is None
    assert snap["next_xp_required"] is None


def test_get_leaderboard_items_builds_items_and_passes_limit_offset(monkeypatch):
    guild = FakeGuild(123)

    list_calls = []

    def fake_xp_list_members(gid, limit, offset):
        list_calls.append((gid, limit, offset))
        # on conserve l'ordre que la DB renvoie
        return [(10, 500), (20, 150), (30, 0)]

    monkeypatch.setattr(mod, "xp_list_members", fake_xp_list_members)

    levels = [(1, 0), (2, 100), (3, 250)]
    monkeypatch.setattr(mod, "xp_get_levels", lambda gid: levels)
    role_ids = {1: 111, 2: 222, 3: 333}
    monkeypatch.setattr(mod, "xp_get_role_ids", lambda gid: role_ids)

    compute_calls = []

    def fake_compute_level(xp, lvls):
        compute_calls.append(xp)
        return 3 if xp >= 250 else 2 if xp >= 100 else 1

    monkeypatch.setattr(mod, "compute_level", fake_compute_level)

    label_calls = []

    def fake_level_label(g, rids, lvl):
        assert g is guild
        assert rids is role_ids
        label_calls.append(lvl)
        return f"@level{lvl}"

    monkeypatch.setattr(mod, "level_label", fake_level_label)

    items = mod.get_leaderboard_items(guild, limit=2, offset=5)

    assert list_calls == [(123, 2, 5)]
    assert compute_calls == [500, 150, 0]
    assert items == [
        (10, 500, 3, "@level3"),
        (20, 150, 2, "@level2"),
        (30, 0, 1, "@level1"),
    ]
    assert label_calls == [3, 2, 1]


def test_get_leaderboard_items_empty_rows(monkeypatch):
    guild = FakeGuild(123)

    monkeypatch.setattr(mod, "xp_list_members", lambda gid, limit, offset: [])
    monkeypatch.setattr(mod, "xp_get_levels", lambda gid: [(1, 0)])
    monkeypatch.setattr(mod, "xp_get_role_ids", lambda gid: {})
    monkeypatch.setattr(mod, "compute_level", lambda xp, lvls: 1)
    monkeypatch.setattr(mod, "level_label", lambda g, rids, lvl: "Niveau 0")

    assert mod.get_leaderboard_items(guild) == []
