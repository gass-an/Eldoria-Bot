import pytest

from eldoria.exceptions import general as exc
from eldoria.exceptions.ui.general_ui import general_error_message


@pytest.mark.parametrize(
    "err, expected",
    [
        (exc.GuildRequired(), "❌ Cette commande doit être utilisée sur un serveur."),
        (exc.UserRequired(), "❌ Cette action doit être effectuée par un utilisateur."),
        (exc.ChannelRequired(), "❌ Impossible de retrouver le salon associé à cette action."),
        (exc.MessageRequired(), "❌ Le message associé à cette action est introuvable."),
        (exc.DatabaseRestoreError(), "❌ Une erreur est survenue lors du remplacement de la base de données."),
        (exc.InvalidMessageId(), "❌ L'identifiant de message fourni est invalide."),
    ],
)
def test_general_error_message_static_messages(err: exc.AppError, expected: str):
    assert general_error_message(err) == expected


def test_general_error_message_member_not_found_includes_ids():
    err = exc.MemberNotFound(guild_id=123, member_id=456)
    msg = general_error_message(err)
    assert msg == "❌ Impossible de retrouver le membre 456 dans le serveur 123."


def test_general_error_message_guild_not_found_includes_id():
    err = exc.GuildNotFound(guild_id=999)
    msg = general_error_message(err)
    assert msg == "❌ Impossible de retrouver le serveur 999."


def test_general_error_message_fallback_for_unhandled_error():
    err = exc.AppError("Something else went wrong")  
    assert general_error_message(err) == "❌ Une erreur est survenue."
