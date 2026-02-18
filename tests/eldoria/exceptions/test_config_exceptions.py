from eldoria.exceptions.base import AppError
from eldoria.exceptions.config import (
    ConfigError,
    IncompleteFeatureConfig,
    InvalidEnvVar,
    MissingEnvVar,
)


def test_config_error_inherits_app_error():
    """Contrat architectural : ConfigError doit hériter de AppError."""
    assert issubclass(ConfigError, AppError)


def test_missing_env_var_stores_name_and_formats_message():
    err = MissingEnvVar("TOKEN")

    # payload
    assert err.name == "TOKEN"

    # message utile
    assert "TOKEN" in str(err)


def test_invalid_env_var_stores_name_and_expected():
    err = InvalidEnvVar("PORT", "integer")

    assert err.name == "PORT"
    assert err.expected == "integer"

    msg = str(err)
    assert "PORT" in msg
    assert "integer" in msg


def test_incomplete_feature_config_stores_feature_and_missing():
    err = IncompleteFeatureConfig("duel", ["TOKEN", "CHANNEL_ID"])

    assert err.feature == "duel"
    assert err.missing == ["TOKEN", "CHANNEL_ID"]

    msg = str(err)
    assert "duel" in msg
    assert "TOKEN" in msg
    assert "CHANNEL_ID" in msg
