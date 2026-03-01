"""Façade d'import pour les fakes de tests.

Permet dans les tests:

    from tests._fakes import FakeGuild, FakeMember, FakeInteraction, ...
"""

from __future__ import annotations

from tests._fakes.discord_bot import (
    FakeBot,
    FakeCog,
    FakeCtx,
    FakeIntents,
    FakeLog,
    make_discord_intents,
)
from tests._fakes.discord_channels import (
    FakeChannel,    FakeFetchMessageChannel,
    FakeReactionChannel,
    FakeTextChannel,
    FakeVoiceChannel,
)
from tests._fakes.discord_entities import (
    FakeAttachment,
    FakeAuthor,
    FakeAvatar,
    FakeColor,
    FakeDisplayMember,
    FakeEmbed,
    FakeEmoji,
    FakeFile,
    FakeGuild,
    FakeMember,
    FakeMessage,
    FakePrimaryGuild,
    FakeReactionPayload,
    FakeRole,
    FakeUser,
    FakeVoiceState,
)
from tests._fakes.discord_interactions import (
    FakeFollowup,
    FakeInteraction,
    FakePerms,
    FakeResponse,
    set_raise_on_edit_original_http,
    set_raise_on_edit_original_not_found,
    set_raise_on_second_response_send,
)
from tests._fakes.eldoria_services import (
    Conn,
    ConnCM,
    Cursor,
    FakeBotGuild,
    FakeConn,
    FakeConnCM,
    FakeCursor,
    FakeDatetime,
    FakeDiscord,
    FakeDuelError,
    FakeDuelService,
    FakeRoleService,
    FakeSaveService,
    FakeServices,
    FakeTempVoiceService,
    FakeWelcomeService,
    FakeXpService,
    Logger,
    is_enterable,
    make_datetime_now,
    make_db_error,
    make_services_class,
    make_tests_path,
)

__all__ = [
    # entities
    "FakeGuild",
    "FakeMember",
    "FakeRole",
    "FakeUser",
    "FakeMessage",
    "FakeAttachment",
    "FakeAvatar",
    "FakeAuthor",
    "FakeDisplayMember",
    "FakePrimaryGuild",
    "FakeVoiceState",
    "FakeEmoji",
    "FakeReactionPayload",
    "FakeColor",
    "FakeFile",
    "FakeEmbed",
    # channels
    "FakeChannel",
    "FakeTextChannel",
    "FakeVoiceChannel",    "FakeFetchMessageChannel",
    "FakeReactionChannel",
    # interactions
    "FakeInteraction",
    "FakeResponse",
    "FakeFollowup",
    "FakePerms",
    "set_raise_on_second_response_send",
    "set_raise_on_edit_original_not_found",
    "set_raise_on_edit_original_http",
    # bot
    "FakeBot",
    "FakeCtx",
    "FakeCog",
    "FakeIntents",
    "make_discord_intents",
    "FakeLog",
    # services
    "FakeServices",
    "FakeXpService",
    "FakeDuelService",
    "FakeRoleService",
    "FakeSaveService",
    "FakeTempVoiceService",
    "FakeWelcomeService",
    # app/db helpers
    "FakeDiscord",
    "make_datetime_now",
    "Logger",
    "make_tests_path",
    "make_services_class",
    "FakeBotGuild",
    "FakeDatetime",
    "FakeDuelError",
    "FakeCursor",
    "FakeConn",
    "FakeConnCM",
    "is_enterable",
    "Conn",
    "Cursor",
    "ConnCM",
    "make_db_error",
]
