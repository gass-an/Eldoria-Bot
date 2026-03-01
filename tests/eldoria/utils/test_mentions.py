from eldoria.utils.mentions import level_label, level_mention
from tests._fakes import FakeRole


def make_guild(roles_by_id=None):
    roles = dict(roles_by_id or {})

    def _get_role(self, role_id: int | None):
        if role_id is None:
            return None
        return roles.get(role_id)

    return type("GuildStub", (), {"get_role": _get_role})()

def test_level_mention_returns_role_mention_when_configured():
    role_ids = {2: 200}
    guild = make_guild({200: FakeRole(200)})

    assert level_mention(guild, 2, role_ids) == "<@&200>"

def test_level_mention_falls_back_when_no_config():
    role_ids = {}
    guild = make_guild({})

    assert level_mention(guild, 3, role_ids) == "level3"

def test_level_mention_falls_back_when_role_missing():
    role_ids = {2: 999}
    guild = make_guild({})

    assert level_mention(guild, 2, role_ids) == "level2"

def test_level_mention_falls_back_when_role_ids_is_none_like():
    guild = make_guild({})

    # role_ids = None n'est pas le type attendu mais ton code le gère via "if role_ids else None"
    assert level_mention(guild, 1, None) == "level1"  # type: ignore[arg-type]

def test_level_label_returns_role_mention_when_possible():
    role_ids = {4: 400}
    guild = make_guild({400: FakeRole(400)})

    assert level_label(guild, role_ids, 4) == "<@&400>"

def test_level_label_falls_back_when_role_ids_is_none():
    guild = make_guild({})
    assert level_label(guild, None, 1) == "lvl1"  # type: ignore[arg-type]

def test_level_label_falls_back_when_role_missing():
    role_ids = {5: 555}
    guild = make_guild({})

    assert level_label(guild, role_ids, 5) == "lvl5"