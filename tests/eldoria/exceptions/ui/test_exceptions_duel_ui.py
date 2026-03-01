import pytest

from eldoria.exceptions import duel as exc
from eldoria.exceptions.ui import duel_ui as M
from tests._support.exceptions import UnknownDuelError


@pytest.mark.parametrize(
    "error, expected",
    [
        (exc.SamePlayerDuel(1, 1), "😅 Tu ne peux pas te défier toi-même."),
        (exc.PlayerAlreadyInDuel(), "⚠️ L'un des joueurs est déjà en duel."),
        (exc.DuelNotFound(42), "⚠️ Ce duel n'existe plus (ou a expiré)."),
        (exc.ExpiredDuel(42), "⌛ Ce duel a expiré."),
        (exc.NotAuthorizedPlayer(1), "⛔ Tu n'as pas l'autorisation d'interagir avec ce duel."),
        (exc.ConfigurationIncomplete(), "⚠️ Le duel n'est pas entièrement configuré."),
        (exc.InvalidGameType("rps"), "⚠️ Jeu invalide."),
        (exc.InvalidStake(999), "⚠️ Mise invalide."),
        (exc.DuelNotAcceptable("CONFIG"), "⚠️ Ce duel ne peut pas être accepté dans son état actuel."),
        (exc.DuelNotFinishable("ACTIVE"), "⚠️ Ce duel ne peut pas être terminé dans son état actuel."),
        (exc.DuelNotActive("CONFIG"), "⚠️ Le duel n'est pas actif."),
        (exc.WrongGameType("a", "b"), "⚠️ Mauvais jeu pour cette action."),
        (exc.InvalidMove(), "⚠️ Coup invalide."),
        (exc.AlreadyPlayed(), "⚠️ Tu as déjà joué."),
        (exc.PayloadError(), "⚠️ Petit souci technique, réessaie."),
        (exc.DuelAlreadyHandled(1, "ACTIVE"), "ℹ️ Ce duel a déjà été traité (quelqu'un a cliqué juste avant)."),
        (exc.InvalidSnapshot(), "⚠️ Le duel est dans un état inattendu. Réessaie."),
    ],
)
def test_duel_error_message_specific_cases(error, expected):
    assert M.duel_error_message(error) == expected


def test_duel_error_message_insufficient_xp():
    e = exc.InsufficientXp(required=250)
    msg = M.duel_error_message(e)
    assert "250" in msg
    assert "XP" in msg


@pytest.mark.parametrize(
    "error",
    [
        exc.ConfigurationError(),
        exc.MissingMessageId(),
        exc.InvalidResult("X"),
        exc.DuelNotFinished(1, "ACTIVE"),
    ],
)
def test_duel_error_message_grouped_generic(error):
    assert M.duel_error_message(error) == "❌ Une erreur est survenue. Réessaie."
def test_duel_error_message_fallback():
    e = UnknownDuelError("boom")
    assert M.duel_error_message(e) == "❌ Une erreur est survenue."
