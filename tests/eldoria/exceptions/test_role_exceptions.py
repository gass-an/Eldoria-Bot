import pytest


def test_role_exceptions_inheritance_and_payloads():
    from eldoria.exceptions.base import AppError
    from eldoria.exceptions.role import (
        EmojiAlreadyBound,
        InvalidGuild,
        InvalidLink,
        MessageAlreadyBound,
        RoleAboveBot,
        RoleAlreadyBound,
        RoleError,
        SecretRoleNotFound,
    )

    # Base inheritance
    assert issubclass(RoleError, AppError)
    assert issubclass(InvalidLink, RoleError)
    assert issubclass(InvalidGuild, RoleError)

    # Concrete payloads
    e1 = InvalidLink()
    assert isinstance(e1, RoleError)
    assert "invalide" in str(e1).lower()

    e2 = InvalidGuild(expected_guild_id=111, actual_guild_id=222)
    assert "222" in str(e2) and "111" in str(e2)

    e3 = RoleAboveBot(role_id=42)
    assert e3.role_id == 42
    assert "42" in str(e3)

    e4 = RoleAlreadyBound(message_id=10, role_id=99, existing_emoji="😀")
    assert e4.message_id == 10
    assert e4.role_id == 99
    assert e4.existing_emoji == "😀"

    e5 = EmojiAlreadyBound(message_id=10, emoji="🔥", existing_role_id=5)
    assert e5.message_id == 10
    assert e5.emoji == "🔥"
    assert e5.existing_role_id == 5

    e6 = MessageAlreadyBound(message="hello", existing_role_id=123)
    assert e6.message == "hello"
    assert e6.existing_role_id == 123

    e7 = SecretRoleNotFound(message="hello")
    assert e7.message == "hello"


@pytest.mark.parametrize(
    "exc_cls, kwargs",
    [
        ("InvalidLink", {}),
        ("InvalidGuild", {"expected_guild_id": 2, "actual_guild_id": 1}),
        ("RoleAboveBot", {"role_id": 1}),
        ("RoleAlreadyBound", {"message_id": 1, "role_id": 2, "existing_emoji": "😀"}),
        ("EmojiAlreadyBound", {"message_id": 1, "emoji": "🔥", "existing_role_id": 2}),
        ("MessageAlreadyBound", {"message": "m", "existing_role_id": 2}),
        ("SecretRoleNotFound", {"message": "m"}),
    ],
)
def test_role_exceptions_are_catchable_as_roleerror(exc_cls, kwargs):
    from eldoria.exceptions import role as role_exc

    e = getattr(role_exc, exc_cls)(**kwargs)
    assert isinstance(e, role_exc.RoleError)
