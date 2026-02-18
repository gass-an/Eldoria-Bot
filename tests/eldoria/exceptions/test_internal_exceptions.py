from eldoria.exceptions.base import AppError
from eldoria.exceptions.internal import (
    InternalStateError,
    ServicesAlreadyInitialized,
    ServicesNotInitialized,
    TestsFailed,
)


def test_internal_state_error_inherits_app_error():
    """Contrat architectural : les erreurs internes doivent être des AppError."""
    assert issubclass(InternalStateError, AppError)


def test_services_not_initialized_has_explicit_message():
    err = ServicesNotInitialized()
    assert "Services" in str(err)


def test_services_already_initialized_has_explicit_message():
    err = ServicesAlreadyInitialized()
    assert "déjà" in str(err).lower()


def test_tests_failed_has_explicit_message():
    err = TestsFailed()
    assert "tests" in str(err).lower()
