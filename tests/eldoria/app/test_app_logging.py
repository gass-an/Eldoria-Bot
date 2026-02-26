import logging
import sys
from logging.handlers import RotatingFileHandler

import pytest

from eldoria.app.logging import DiscordReconnectNoiseFilter, setup_logging


@pytest.fixture(autouse=True)
def _reset_logging():
    """Reset minimal du root logger pour éviter les effets globaux entre tests."""
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.NOTSET)
    yield
    root.handlers.clear()
    root.setLevel(logging.NOTSET)


def _get_handlers():
    root = logging.getLogger()
    sh = next(
        h for h in root.handlers
        if isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler)
    )
    fh = next(h for h in root.handlers if isinstance(h, RotatingFileHandler))
    return sh, fh


def test_setup_logging_sets_root_level_and_handlers(tmp_path):
    log_file = tmp_path / "logs" / "bot.log"

    setup_logging(level=logging.DEBUG, log_file=str(log_file))

    root = logging.getLogger()
    assert root.level == logging.DEBUG
    assert len(root.handlers) == 2

    sh, fh = _get_handlers()

    assert sh.stream is sys.stdout
    assert sh.level == logging.DEBUG

    assert fh.level == logging.DEBUG
    assert fh.baseFilename.endswith("bot.log")

    assert log_file.parent.exists()


def test_setup_logging_sets_discord_loggers_to_warning(tmp_path):
    setup_logging(level=logging.INFO, log_file=str(tmp_path / "bot.log"))

    assert logging.getLogger("discord").level == logging.WARNING
    assert logging.getLogger("discord.client").level == logging.WARNING
    assert logging.getLogger("discord.gateway").level == logging.WARNING
    assert logging.getLogger("discord.gateway").propagate is False


def test_setup_logging_replaces_existing_handlers(tmp_path):
    root = logging.getLogger()

    # On ajoute un handler sentinelle qu'on veut voir disparaître
    sentinel = logging.StreamHandler()
    root.addHandler(sentinel)

    assert sentinel in root.handlers  # stable

    setup_logging(level=logging.INFO, log_file=str(tmp_path / "bot.log"))

    # Le handler sentinelle doit être supprimé
    assert sentinel not in root.handlers

    # Et on doit avoir nos 2 handlers (console + fichier)
    assert any(
        isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler)
        for h in root.handlers
    )
    assert any(isinstance(h, RotatingFileHandler) for h in root.handlers)


def test_setup_logging_formatter_format_and_datefmt(tmp_path):
    setup_logging(level=logging.INFO, log_file=str(tmp_path / "bot.log"))

    root = logging.getLogger()
    for handler in root.handlers:
        formatter = handler.formatter
        assert formatter is not None
        assert formatter._fmt == "%(asctime)s  %(levelname)-10s  %(name)-30s - %(message)s"
        assert formatter.datefmt == "%d/%m/%Y  %H:%M:%S"


def test_setup_logging_adds_noise_filter_to_handlers(tmp_path):
    setup_logging(level=logging.INFO, log_file=str(tmp_path / "bot.log"))

    root = logging.getLogger()
    for handler in root.handlers:
        assert any(isinstance(f, DiscordReconnectNoiseFilter) for f in handler.filters)


def test_setup_logging_rotating_file_handler_config(tmp_path):
    log_file = tmp_path / "bot.log"

    setup_logging(
        level=logging.INFO,
        log_file=str(log_file),
        max_bytes=1234,
        backup_count=7,
    )

    _, fh = _get_handlers()
    assert isinstance(fh, RotatingFileHandler)

    # Paramètres de rotation
    assert fh.maxBytes == 1234
    assert fh.backupCount == 7

    # Encoding (selon versions, attribut peut être absent => on tolère)
    if hasattr(fh, "encoding"):
        assert fh.encoding == "utf-8"


def test_setup_logging_writes_startup_marker_in_file(tmp_path):
    log_file = tmp_path / "logs" / "bot.log"

    setup_logging(level=logging.INFO, log_file=str(log_file))

    text = log_file.read_text(encoding="utf-8")
    assert "========== DÉMARRAGE DU BOT ==========" in text
    # On s'assure qu'il y a bien deux sauts de ligne avant le marqueur
    assert "\n\n========== DÉMARRAGE DU BOT ==========" in text


def test_noise_filter_prevents_reconnect_noise_from_being_written(tmp_path):
    """
    Test "end-to-end": on loggue un message bruité et on vérifie qu'il n'apparaît pas dans le fichier.
    """
    log_file = tmp_path / "logs" / "bot.log"
    setup_logging(level=logging.INFO, log_file=str(log_file))

    logger = logging.getLogger("discord.client")
    logger.error("Attempting a reconnect in 1.66s")

    text = log_file.read_text(encoding="utf-8")

    # Le marqueur de démarrage est là...
    assert "DÉMARRAGE DU BOT" in text
    # ...mais pas le message filtré
    assert "Attempting a reconnect" not in text


def test_discord_reconnect_noise_filter_filters_expected_messages():
    f = DiscordReconnectNoiseFilter()

    r1 = logging.LogRecord("discord.client", logging.ERROR, __file__, 1, "Attempting a reconnect in 1.66s", args=(), exc_info=None)
    r2 = logging.LogRecord("discord.client", logging.ERROR, __file__, 1, "ClientConnectorDNSError: Cannot connect to host discord.com", args=(), exc_info=None)
    r3 = logging.LogRecord("discord.client", logging.ERROR, __file__, 1, "socket.gaierror: [Errno 11001] getaddrinfo failed", args=(), exc_info=None)
    r4 = logging.LogRecord("discord.client", logging.ERROR, __file__, 1, "Autre message", args=(), exc_info=None)

    assert f.filter(r1) is False
    assert f.filter(r2) is False
    assert f.filter(r3) is False
    assert f.filter(r4) is True