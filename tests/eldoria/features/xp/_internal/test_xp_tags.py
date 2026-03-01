
from eldoria.features.xp._internal.tags import has_active_server_tag_for_guild


def _g_init(self, guild_id: int = 123, tag: str | None = None):
    self.id = guild_id
    if tag is not None:
        self.tag = tag


GuildStub = type("GuildStub", (), {"__init__": _g_init})


def _pg_init(self, *, identity_enabled: bool = True, identity_guild_id: int | None = 123, tag: str | None = None):
    self.identity_enabled = identity_enabled
    self.identity_guild_id = identity_guild_id
    if tag is not None:
        self.tag = tag


PrimaryGuildStub = type("PrimaryGuildStub", (), {"__init__": _pg_init})


def _u_init(self, *, primary_guild=None):
    if primary_guild is not None:
        self.primary_guild = primary_guild


UserStub = type("UserStub", (), {"__init__": _u_init})


def _m_init(self, *, primary_guild=None, user_obj=None):
    if primary_guild is not None:
        self.primary_guild = primary_guild
    if user_obj is not None:
        self._user = user_obj


MemberStub = type("MemberStub", (), {"__init__": _m_init})


def test_returns_false_when_no_primary_guild_anywhere():
    guild = GuildStub(123, tag="ELD")
    member = MemberStub()
    assert has_active_server_tag_for_guild(member, guild) is False


def test_uses_primary_guild_on_member_when_present():
    guild = GuildStub(123)
    pg = PrimaryGuildStub(identity_enabled=True, identity_guild_id=123)
    member = MemberStub(primary_guild=pg)
    assert has_active_server_tag_for_guild(member, guild) is True


def test_falls_back_to_member_user_primary_guild():
    guild = GuildStub(123)
    pg = PrimaryGuildStub(identity_enabled=True, identity_guild_id=123)
    member = MemberStub(user_obj=UserStub(primary_guild=pg))
    assert has_active_server_tag_for_guild(member, guild) is True


def test_returns_false_when_identity_not_enabled():
    guild = GuildStub(123)
    pg = PrimaryGuildStub(identity_enabled=False, identity_guild_id=123)
    member = MemberStub(primary_guild=pg)
    assert has_active_server_tag_for_guild(member, guild) is False


def test_returns_false_when_identity_guild_id_differs():
    guild = GuildStub(123)
    pg = PrimaryGuildStub(identity_enabled=True, identity_guild_id=999)
    member = MemberStub(primary_guild=pg)
    assert has_active_server_tag_for_guild(member, guild) is False


def test_returns_true_when_tags_not_exposed_even_if_identity_matches():
    guild = GuildStub(123)  # pas de guild.tag
    pg = PrimaryGuildStub(identity_enabled=True, identity_guild_id=123)  # pas de pg.tag
    member = MemberStub(primary_guild=pg)
    assert has_active_server_tag_for_guild(member, guild) is True


def test_returns_true_when_only_one_tag_is_exposed():
    # guild tag présent, user tag absent => le code ne compare pas et retourne True
    guild = GuildStub(123, tag="ELD")
    pg = PrimaryGuildStub(identity_enabled=True, identity_guild_id=123)  # pas de tag
    member = MemberStub(primary_guild=pg)
    assert has_active_server_tag_for_guild(member, guild) is True

    # user tag présent, guild tag absent => pareil
    guild2 = GuildStub(123)  # pas de tag
    pg2 = PrimaryGuildStub(identity_enabled=True, identity_guild_id=123, tag="ELD")
    member2 = MemberStub(primary_guild=pg2)
    assert has_active_server_tag_for_guild(member2, guild2) is True


def test_returns_true_when_tags_match_case_insensitive():
    guild = GuildStub(123, tag="eld")
    pg = PrimaryGuildStub(identity_enabled=True, identity_guild_id=123, tag="ELD")
    member = MemberStub(primary_guild=pg)
    assert has_active_server_tag_for_guild(member, guild) is True


def test_returns_false_when_tags_do_not_match():
    guild = GuildStub(123, tag="ELD")
    pg = PrimaryGuildStub(identity_enabled=True, identity_guild_id=123, tag="NOPE")
    member = MemberStub(primary_guild=pg)
    assert has_active_server_tag_for_guild(member, guild) is False


def test_handles_missing_identity_enabled_attribute_safely():
    """
    Si primary_guild n'a pas identity_enabled, getattr(..., False) => False.
    """
    guild = GuildStub(123)

    PgNoIdentityEnabled = type("PgNoIdentityEnabled", (), {"identity_guild_id": 123})
    member = MemberStub(primary_guild=PgNoIdentityEnabled())
    assert has_active_server_tag_for_guild(member, guild) is False


def test_handles_missing_identity_guild_id_attribute_safely():
    """
    Si primary_guild n'a pas identity_guild_id, getattr(..., None) => None != guild.id => False.
    """
    guild = GuildStub(123)

    PgNoGuildId = type("PgNoGuildId", (), {"identity_enabled": True})
    member = MemberStub(primary_guild=PgNoGuildId())
    assert has_active_server_tag_for_guild(member, guild) is False
