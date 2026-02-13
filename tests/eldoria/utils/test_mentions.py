
from eldoria.utils.mentions import level_label, level_mention


class FakeRole:
    def __init__(self, role_id: int):
        self.id = role_id
        self.mention = f"<@&{role_id}>"


class FakeGuild:
    def __init__(self, roles_by_id=None):
        self._roles = dict(roles_by_id or {})

    def get_role(self, role_id: int | None):
        if role_id is None:
            return None
        return self._roles.get(role_id)


def test_level_mention_returns_role_mention_when_configured():
    role_ids = {2: 200}
    guild = FakeGuild(roles_by_id={200: FakeRole(200)})

    assert level_mention(guild, 2, role_ids) == "<@&200>"


def test_level_mention_falls_back_when_no_config():
    role_ids = {}
    guild = FakeGuild(roles_by_id={})

    assert level_mention(guild, 3, role_ids) == "level3"


def test_level_mention_falls_back_when_role_missing():
    role_ids = {2: 999}
    guild = FakeGuild(roles_by_id={})

    assert level_mention(guild, 2, role_ids) == "level2"


def test_level_mention_falls_back_when_role_ids_is_none_like():
    guild = FakeGuild(roles_by_id={})

    # role_ids = None n'est pas le type attendu mais ton code le gère via "if role_ids else None"
    assert level_mention(guild, 1, None) == "level1"  # type: ignore[arg-type]


def test_level_label_returns_role_mention_when_possible():
    role_ids = {4: 400}
    guild = FakeGuild(roles_by_id={400: FakeRole(400)})

    assert level_label(guild, role_ids, 4) == "<@&400>"


def test_level_label_falls_back_when_role_ids_is_none():
    guild = FakeGuild(roles_by_id={})
    assert level_label(guild, None, 1) == "lvl1"  # type: ignore[arg-type]


def test_level_label_falls_back_when_role_missing():
    role_ids = {5: 555}
    guild = FakeGuild(roles_by_id={})

    assert level_label(guild, role_ids, 5) == "lvl5"
