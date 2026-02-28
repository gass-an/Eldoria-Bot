from __future__ import annotations

import types

import pytest


class _Guild:
    def __init__(self, gid: int = 1):
        self.id = gid


class _Member:
    def __init__(self, mid: int = 1, *, bot: bool = False, top_role_position: int = 10):
        self.id = mid
        self.bot = bot
        self.top_role = types.SimpleNamespace(position=top_role_position)


class _Role:
    def __init__(self, rid: int = 1, *, position: int = 0):
        self.id = rid
        self.position = position


def _make_ctx(*, guild=None, channel=None, user=None):
    return types.SimpleNamespace(guild=guild, channel=channel, user=user)


def test_require_guild_ctx_raises_when_no_guild():
    from eldoria.exceptions.general import GuildRequired
    from eldoria.utils.guards import require_guild_ctx

    ctx = _make_ctx(guild=None, channel=object(), user=_Member(1))
    with pytest.raises(GuildRequired):
        require_guild_ctx(ctx)


def test_require_guild_ctx_raises_when_channel_invalid(monkeypatch):
    # require_guild_ctx vérifie isinstance(channel, discord.abc.GuildChannel)
    import sys
    import types as pytypes

    if "discord" not in sys.modules:
        sys.modules["discord"] = pytypes.ModuleType("discord")
    discord = sys.modules["discord"]
    if not hasattr(discord, "abc"):
        discord.abc = pytypes.SimpleNamespace()  # type: ignore[attr-defined]
    if not hasattr(discord.abc, "GuildChannel"):
        class GuildChannel:  # pragma: no cover
            pass
        discord.abc.GuildChannel = GuildChannel  # type: ignore[attr-defined]

    from eldoria.exceptions.general import ChannelRequired
    from eldoria.utils.guards import require_guild_ctx

    ctx = _make_ctx(guild=_Guild(1), channel=object(), user=_Member(1))
    with pytest.raises(ChannelRequired):
        require_guild_ctx(ctx)


def test_require_guild_ctx_ok(monkeypatch):
    import sys
    import types as pytypes

    if "discord" not in sys.modules:
        sys.modules["discord"] = pytypes.ModuleType("discord")
    discord = sys.modules["discord"]
    if not hasattr(discord, "abc"):
        discord.abc = pytypes.SimpleNamespace()  # type: ignore[attr-defined]
    if not hasattr(discord.abc, "GuildChannel"):
        class GuildChannel:  # pragma: no cover
            pass
        discord.abc.GuildChannel = GuildChannel  # type: ignore[attr-defined]

    from eldoria.utils.guards import require_guild_ctx

    class _Chan(discord.abc.GuildChannel):
        pass

    g = _Guild(1)
    ch = _Chan()
    ctx = _make_ctx(guild=g, channel=ch, user=_Member(1))
    out_g, out_ch = require_guild_ctx(ctx)
    assert out_g is g
    assert out_ch is ch


def test_require_not_bot_raises():
    from eldoria.exceptions.general import BotTargetNotAllowed
    from eldoria.utils.guards import require_not_bot

    with pytest.raises(BotTargetNotAllowed):
        require_not_bot(_Member(1, bot=True))


def test_require_not_self_raises():
    from eldoria.exceptions.duel import SamePlayerDuel
    from eldoria.utils.guards import require_not_self

    ctx = _make_ctx(guild=_Guild(1), channel=object(), user=_Member(5))
    with pytest.raises(SamePlayerDuel):
        require_not_self(ctx, _Member(5))


def test_require_specific_guild_raises_on_mismatch():
    from eldoria.exceptions.role import InvalidGuild
    from eldoria.utils.guards import require_specific_guild

    with pytest.raises(InvalidGuild):
        require_specific_guild(actual_guild_id=2, expected_guild_id=1)


def test_require_role_assignable_by_bot_raises_when_above():
    from eldoria.exceptions.role import RoleAboveBot
    from eldoria.utils.guards import require_role_assignable_by_bot

    bot_member = _Member(999, top_role_position=5)
    role = _Role(10, position=5)
    with pytest.raises(RoleAboveBot):
        require_role_assignable_by_bot(bot_member, role)


def test_require_no_rr_conflict_raises_role_already_bound():
    from eldoria.exceptions.role import RoleAlreadyBound
    from eldoria.utils.guards import require_no_rr_conflict

    with pytest.raises(RoleAlreadyBound):
        require_no_rr_conflict(message_id=10, emoji="🔥", role_id=42, existing={"😀": 42})


def test_require_no_rr_conflict_raises_emoji_already_bound():
    from eldoria.exceptions.role import EmojiAlreadyBound
    from eldoria.utils.guards import require_no_rr_conflict

    with pytest.raises(EmojiAlreadyBound):
        require_no_rr_conflict(message_id=10, emoji="🔥", role_id=42, existing={"🔥": 99})


def test_require_secretrole_not_conflicting_raises_message_already_bound():
    from eldoria.exceptions.role import MessageAlreadyBound
    from eldoria.utils.guards import require_secretrole_not_conflicting

    with pytest.raises(MessageAlreadyBound):
        require_secretrole_not_conflicting(message="hello", existing_role_id=999, role_id=1)


def test_require_feature_enabled_and_specific_user_id():
    from eldoria.exceptions.general import FeatureNotConfigured, NotAllowed
    from eldoria.utils.guards import require_feature_enabled, require_specific_user_id

    with pytest.raises(FeatureNotConfigured):
        require_feature_enabled(False, feature_name="logs")

    ctx = _make_ctx(guild=_Guild(1), channel=object(), user=_Member(1))
    with pytest.raises(NotAllowed):
        require_specific_user_id(ctx, allowed_user_id=2)
