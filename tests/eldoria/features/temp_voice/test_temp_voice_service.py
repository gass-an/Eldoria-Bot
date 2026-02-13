import eldoria.features.temp_voice.temp_voice_service as svc_mod


def test_find_parent_of_active_delegates_to_repo(monkeypatch):
    calls = {}

    def fake_tv_find_parent_of_active(guild_id: int, channel_id: int):
        calls["args"] = (guild_id, channel_id)
        return 999

    monkeypatch.setattr(
        svc_mod.temp_voice_repo,
        "tv_find_parent_of_active",
        fake_tv_find_parent_of_active,
    )

    svc = svc_mod.TempVoiceService()
    assert svc.find_parent_of_active(1, 2) == 999
    assert calls["args"] == (1, 2)


def test_remove_active_delegates_to_repo(monkeypatch):
    calls = {}

    def fake_tv_remove_active(guild_id: int, parent_channel_id: int, channel_id: int):
        calls["args"] = (guild_id, parent_channel_id, channel_id)
        return None

    monkeypatch.setattr(
        svc_mod.temp_voice_repo,
        "tv_remove_active",
        fake_tv_remove_active,
    )

    svc = svc_mod.TempVoiceService()
    assert svc.remove_active(1, 10, 20) is None
    assert calls["args"] == (1, 10, 20)


def test_get_parent_delegates_to_repo(monkeypatch):
    calls = {}

    def fake_tv_get_parent(guild_id: int, parent_channel_id: int):
        calls["args"] = (guild_id, parent_channel_id)
        return 42

    monkeypatch.setattr(svc_mod.temp_voice_repo, "tv_get_parent", fake_tv_get_parent)

    svc = svc_mod.TempVoiceService()
    assert svc.get_parent(1, 10) == 42
    assert calls["args"] == (1, 10)


def test_add_active_delegates_to_repo(monkeypatch):
    calls = {}

    def fake_tv_add_active(guild_id: int, parent_channel_id: int, channel_id: int):
        calls["args"] = (guild_id, parent_channel_id, channel_id)
        return None

    monkeypatch.setattr(svc_mod.temp_voice_repo, "tv_add_active", fake_tv_add_active)

    svc = svc_mod.TempVoiceService()
    assert svc.add_active(1, 10, 20) is None
    assert calls["args"] == (1, 10, 20)


def test_upsert_parent_delegates_to_repo(monkeypatch):
    calls = {}

    def fake_tv_upsert_parent(guild_id: int, parent_channel_id: int, user_limit: int):
        calls["args"] = (guild_id, parent_channel_id, user_limit)
        return None

    monkeypatch.setattr(
        svc_mod.temp_voice_repo,
        "tv_upsert_parent",
        fake_tv_upsert_parent,
    )

    svc = svc_mod.TempVoiceService()
    assert svc.upsert_parent(1, 10, 5) is None
    assert calls["args"] == (1, 10, 5)


def test_delete_parent_delegates_to_repo(monkeypatch):
    calls = {}

    def fake_tv_delete_parent(guild_id: int, parent_channel_id: int):
        calls["args"] = (guild_id, parent_channel_id)
        return None

    monkeypatch.setattr(
        svc_mod.temp_voice_repo,
        "tv_delete_parent",
        fake_tv_delete_parent,
    )

    svc = svc_mod.TempVoiceService()
    assert svc.delete_parent(1, 10) is None
    assert calls["args"] == (1, 10)


def test_list_parents_delegates_to_repo(monkeypatch):
    calls = {}
    expected = [(10, 5), (11, 0)]

    def fake_tv_list_parents(guild_id: int):
        calls["args"] = (guild_id,)
        return expected

    monkeypatch.setattr(svc_mod.temp_voice_repo, "tv_list_parents", fake_tv_list_parents)

    svc = svc_mod.TempVoiceService()
    assert svc.list_parents(1) == expected
    assert calls["args"] == (1,)


def test_list_active_all_delegates_to_repo(monkeypatch):
    calls = {}
    expected = [(10, 100), (10, 101), (11, 200)]

    def fake_tv_list_active_all(guild_id: int):
        calls["args"] = (guild_id,)
        return expected

    monkeypatch.setattr(
        svc_mod.temp_voice_repo,
        "tv_list_active_all",
        fake_tv_list_active_all,
    )

    svc = svc_mod.TempVoiceService()
    assert svc.list_active_all(1) == expected
    assert calls["args"] == (1,)
