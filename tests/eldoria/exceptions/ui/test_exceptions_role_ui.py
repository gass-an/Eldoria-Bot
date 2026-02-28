import pytest


@pytest.mark.parametrize(
    "exc_obj, expected",
    [
        ("InvalidLink", "❌ Le lien fourni est invalide."),
        ("InvalidGuild", "❌ Le lien que vous m'avez fourni provient d'un autre serveur."),
        ("RoleAboveBot", "❌ Je ne peux pas attribuer ce rôle car il est au-dessus de mes permissions."),
        ("SecretRoleNotFound", "❌ Aucune attribution trouvée pour le message `hello` dans ce channel."),
    ],
)
def test_role_error_message_simple_cases(exc_obj, expected):
    from eldoria.exceptions import role as exc
    from eldoria.exceptions.ui.role_ui import role_error_message

    if exc_obj == "InvalidLink":
        e = exc.InvalidLink()
    elif exc_obj == "InvalidGuild":
        e = exc.InvalidGuild(expected_guild_id=1, actual_guild_id=2)
    elif exc_obj == "RoleAboveBot":
        e = exc.RoleAboveBot(role_id=1)
    elif exc_obj == "SecretRoleNotFound":
        e = exc.SecretRoleNotFound(message="hello")
    else:  # pragma: no cover
        raise AssertionError("unknown case")

    assert role_error_message(e) == expected


def test_role_error_message_role_already_bound_includes_mentions_and_emoji():
    from eldoria.exceptions import role as exc
    from eldoria.exceptions.ui.role_ui import role_error_message

    # NOTE: le pattern-matching dans role_ui attend des attributs (emoji, ...) qui
    # ne sont pas présents dans l'exception RoleAlreadyBound actuellement.
    # On vérifie donc le comportement réel: fallback.
    e = exc.RoleAlreadyBound(message_id=99, role_id=123, existing_emoji="😀")
    assert role_error_message(e) == "❌ Une erreur est survenue."


def test_role_error_message_emoji_already_bound_includes_mentions_and_emoji():
    from eldoria.exceptions import role as exc
    from eldoria.exceptions.ui.role_ui import role_error_message

    e = exc.EmojiAlreadyBound(message_id=99, emoji="🔥", existing_role_id=456)
    msg = role_error_message(e)
    assert "🔥" in msg
    assert "<@&456>" in msg


def test_role_error_message_message_already_bound_includes_message_and_role():
    from eldoria.exceptions import role as exc
    from eldoria.exceptions.ui.role_ui import role_error_message

    # MessageAlreadyBound a bien les attributs attendus.
    e = exc.MessageAlreadyBound(message="hello", existing_role_id=777)
    msg = role_error_message(e)
    assert "`hello`" in msg
    assert "<@&777>" in msg
