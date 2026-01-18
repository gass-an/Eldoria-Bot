import sys
import types

import pytest


if "discord" not in sys.modules:
    sys.modules["discord"] = types.SimpleNamespace()


from eldoria.utils import mentions  # noqa: E402


class FakeRole:
    def __init__(self, role_id: int):
        self.id = role_id
        self.mention = f"<@&{role_id}>"


class FakeGuild:
    def __init__(self, guild_id: int = 123, roles_by_id=None):
        self.id = guild_id
        self._roles = dict(roles_by_id or {})

    def get_role(self, role_id: int | None):
        if role_id is None:
            return None
        return self._roles.get(role_id)


@pytest.fixture()
def stub_role_ids(monkeypatch):
    box = {"role_ids": {}}

    def xp_get_role_ids(guild_id: int):
        return dict(box["role_ids"])

    monkeypatch.setattr(mentions.gestionDB, "xp_get_role_ids", xp_get_role_ids)
    return box


def test_level_mention_returns_role_mention_when_configured(stub_role_ids):
    stub_role_ids["role_ids"] = {2: 200}
    guild = FakeGuild(roles_by_id={200: FakeRole(200)})

    assert mentions.level_mention(guild, 2) == "<@&200>"


def test_level_mention_falls_back_when_no_config(stub_role_ids):
    stub_role_ids["role_ids"] = {}
    guild = FakeGuild(roles_by_id={})

    assert mentions.level_mention(guild, 3) == "level3"


def test_level_mention_falls_back_when_role_missing(stub_role_ids):
    stub_role_ids["role_ids"] = {2: 999}
    guild = FakeGuild(roles_by_id={})

    assert mentions.level_mention(guild, 2) == "level2"


def test_level_label_returns_role_mention_when_possible():
    role_ids = {4: 400}
    guild = FakeGuild(roles_by_id={400: FakeRole(400)})

    assert mentions.level_label(guild, role_ids, 4) == "<@&400>"


def test_level_label_falls_back_when_role_ids_is_none():
    guild = FakeGuild(roles_by_id={})
    assert mentions.level_label(guild, None, 1) == "lvl1"


def test_level_label_falls_back_when_role_missing():
    role_ids = {5: 555}
    guild = FakeGuild(roles_by_id={})
    assert mentions.level_label(guild, role_ids, 5) == "lvl5"
