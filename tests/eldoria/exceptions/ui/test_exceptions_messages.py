from unittest.mock import patch

from eldoria.exceptions.duel import DuelError
from eldoria.exceptions.ui.messages import app_error_message
from tests._support.exceptions import DummyAppError, DummyDuelError


def test_routes_duel_error_to_duel_mapper():
    err = DummyDuelError("duel boom")

    with patch(
        "eldoria.exceptions.ui.messages.duel_error_message",
        return_value="duel message",
    ) as duel_mock, patch(
        "eldoria.exceptions.ui.messages.general_error_message",
        return_value="general message",
    ) as general_mock:
        result = app_error_message(err)

        duel_mock.assert_called_once_with(err)
        general_mock.assert_not_called()
        assert result == "duel message"


def test_routes_non_duel_error_to_general_mapper():
    err = DummyAppError("general boom")

    with patch(
        "eldoria.exceptions.ui.messages.duel_error_message",
        return_value="duel message",
    ) as duel_mock, patch(
        "eldoria.exceptions.ui.messages.general_error_message",
        return_value="general message",
    ) as general_mock:
        result = app_error_message(err)

        general_mock.assert_called_once_with(err)
        duel_mock.assert_not_called()
        assert result == "general message"


def test_duel_subclass_is_still_routed_to_duel_mapper():
    custom_err_type = type("CustomDuelError", (DuelError,), {})
    err = custom_err_type("custom duel")

    with patch(
        "eldoria.exceptions.ui.messages.duel_error_message",
        return_value="duel message",
    ) as duel_mock:
        result = app_error_message(err)

        duel_mock.assert_called_once_with(err)
        assert result == "duel message"