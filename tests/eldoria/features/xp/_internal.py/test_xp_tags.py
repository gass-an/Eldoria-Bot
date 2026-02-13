
from eldoria.features.xp._internal.tags import has_active_server_tag_for_guild


class FakeGuild:
    def __init__(self, guild_id: int = 123, tag: str | None = None):
        self.id = guild_id
        if tag is not None:
            self.tag = tag  # attribut optionnel


class FakePrimaryGuild:
    def __init__(
        self,
        *,
        identity_enabled: bool = True,
        identity_guild_id: int | None = 123,
        tag: str | None = None,
    ):
        self.identity_enabled = identity_enabled
        self.identity_guild_id = identity_guild_id
        if tag is not None:
            self.tag = tag  # attribut optionnel


class FakeUser:
    def __init__(self, *, primary_guild=None):
        if primary_guild is not None:
            self.primary_guild = primary_guild


class FakeMember:
    def __init__(self, *, primary_guild=None, user_obj=None):
        # primary_guild peut être sur le member...
        if primary_guild is not None:
            self.primary_guild = primary_guild
        # ...ou sur member._user
        if user_obj is not None:
            self._user = user_obj


def test_returns_false_when_no_primary_guild_anywhere():
    guild = FakeGuild(123, tag="ELD")
    member = FakeMember()
    assert has_active_server_tag_for_guild(member, guild) is False


def test_uses_primary_guild_on_member_when_present():
    guild = FakeGuild(123)
    pg = FakePrimaryGuild(identity_enabled=True, identity_guild_id=123)
    member = FakeMember(primary_guild=pg)
    assert has_active_server_tag_for_guild(member, guild) is True


def test_falls_back_to_member_user_primary_guild():
    guild = FakeGuild(123)
    pg = FakePrimaryGuild(identity_enabled=True, identity_guild_id=123)
    member = FakeMember(user_obj=FakeUser(primary_guild=pg))
    assert has_active_server_tag_for_guild(member, guild) is True


def test_returns_false_when_identity_not_enabled():
    guild = FakeGuild(123)
    pg = FakePrimaryGuild(identity_enabled=False, identity_guild_id=123)
    member = FakeMember(primary_guild=pg)
    assert has_active_server_tag_for_guild(member, guild) is False


def test_returns_false_when_identity_guild_id_differs():
    guild = FakeGuild(123)
    pg = FakePrimaryGuild(identity_enabled=True, identity_guild_id=999)
    member = FakeMember(primary_guild=pg)
    assert has_active_server_tag_for_guild(member, guild) is False


def test_returns_true_when_tags_not_exposed_even_if_identity_matches():
    guild = FakeGuild(123)  # pas de guild.tag
    pg = FakePrimaryGuild(identity_enabled=True, identity_guild_id=123)  # pas de pg.tag
    member = FakeMember(primary_guild=pg)
    assert has_active_server_tag_for_guild(member, guild) is True


def test_returns_true_when_only_one_tag_is_exposed():
    # guild tag présent, user tag absent => le code ne compare pas et retourne True
    guild = FakeGuild(123, tag="ELD")
    pg = FakePrimaryGuild(identity_enabled=True, identity_guild_id=123)  # pas de tag
    member = FakeMember(primary_guild=pg)
    assert has_active_server_tag_for_guild(member, guild) is True

    # user tag présent, guild tag absent => pareil
    guild2 = FakeGuild(123)  # pas de tag
    pg2 = FakePrimaryGuild(identity_enabled=True, identity_guild_id=123, tag="ELD")
    member2 = FakeMember(primary_guild=pg2)
    assert has_active_server_tag_for_guild(member2, guild2) is True


def test_returns_true_when_tags_match_case_insensitive():
    guild = FakeGuild(123, tag="eld")
    pg = FakePrimaryGuild(identity_enabled=True, identity_guild_id=123, tag="ELD")
    member = FakeMember(primary_guild=pg)
    assert has_active_server_tag_for_guild(member, guild) is True


def test_returns_false_when_tags_do_not_match():
    guild = FakeGuild(123, tag="ELD")
    pg = FakePrimaryGuild(identity_enabled=True, identity_guild_id=123, tag="NOPE")
    member = FakeMember(primary_guild=pg)
    assert has_active_server_tag_for_guild(member, guild) is False


def test_handles_missing_identity_enabled_attribute_safely():
    """
    Si primary_guild n'a pas identity_enabled, getattr(..., False) => False.
    """
    guild = FakeGuild(123)

    class PgNoIdentityEnabled:
        identity_guild_id = 123

    member = FakeMember(primary_guild=PgNoIdentityEnabled())
    assert has_active_server_tag_for_guild(member, guild) is False


def test_handles_missing_identity_guild_id_attribute_safely():
    """
    Si primary_guild n'a pas identity_guild_id, getattr(..., None) => None != guild.id => False.
    """
    guild = FakeGuild(123)

    class PgNoGuildId:
        identity_enabled = True

    member = FakeMember(primary_guild=PgNoGuildId())
    assert has_active_server_tag_for_guild(member, guild) is False
