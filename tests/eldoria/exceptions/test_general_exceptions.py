from eldoria.exceptions.base import AppError
from eldoria.exceptions.general import (
    GuildNotFound,
    GuildRequired,
    MemberNotFound,
)


def test_general_exceptions_inherit_app_error():
    """Contrat architectural : les erreurs générales doivent être des AppError."""
    assert issubclass(GuildRequired, AppError)


def test_member_not_found_stores_ids_and_message_contains_them():
    err = MemberNotFound(guild_id=1, member_id=2)

    assert err.guild_id == 1
    assert err.member_id == 2

    msg = str(err)
    assert "1" in msg
    assert "2" in msg


def test_guild_not_found_stores_id_and_message_contains_it():
    err = GuildNotFound(guild_id=999)

    assert err.guild_id == 999
    assert "999" in str(err)
