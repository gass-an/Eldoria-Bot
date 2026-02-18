from eldoria.exceptions.base import AppError
from eldoria.exceptions.duel import (
    DuelAlreadyHandled,
    DuelError,
    DuelInsertFailed,
    DuelNotAcceptable,
    DuelNotFound,
    ExpiredDuel,
    InvalidGameType,
    SamePlayerDuel,
    WrongGameType,
)


def test_duel_error_inherits_app_error():
    """Contrat architectural : toutes les erreurs duel doivent être des AppError."""
    assert issubclass(DuelError, AppError)


def test_duel_insert_failed_has_non_empty_message():
    """Contrat : les erreurs techniques doivent être explicites (debug/log)."""
    err = DuelInsertFailed()
    assert str(err)  # non vide


def test_duel_not_found_stores_duel_id_and_message_contains_it():
    err = DuelNotFound(42)
    assert err.duel_id == 42
    assert "42" in str(err)


def test_duel_not_acceptable_stores_status_and_message_contains_it():
    err = DuelNotAcceptable("PENDING")
    assert err.status == "PENDING"
    assert "PENDING" in str(err)


def test_duel_already_handled_stores_payload_and_message_contains_it():
    err = DuelAlreadyHandled(10, "ACTIVE")
    assert err.duel_id == 10
    assert err.expected_status == "ACTIVE"

    msg = str(err)
    assert "10" in msg
    assert "ACTIVE" in msg


def test_same_player_duel_stores_both_player_ids_and_message_contains_them():
    err = SamePlayerDuel(111, 111)
    assert err.player_a_id == 111
    assert err.player_b_id == 111
    assert "111" in str(err)


def test_invalid_game_type_stores_game_type_and_message_contains_it():
    err = InvalidGameType("chess")
    assert err.game_type == "chess"
    assert "chess" in str(err)


def test_wrong_game_type_stores_received_and_expected_and_message_contains_them():
    err = WrongGameType(game_type_received="rps", game_type_expected="coinflip")
    assert err.game_type_received == "rps"
    assert err.game_type_expected == "coinflip"

    msg = str(err)
    assert "rps" in msg
    assert "coinflip" in msg


def test_expired_duel_stores_duel_id_and_message_contains_it():
    err = ExpiredDuel(77)
    assert err.duel_id == 77
    assert "77" in str(err)
