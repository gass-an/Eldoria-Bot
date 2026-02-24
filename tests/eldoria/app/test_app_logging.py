import logging
import sys
from logging.handlers import RotatingFileHandler

from eldoria.app.logging import DiscordReconnectNoiseFilter, setup_logging


def _reset_logging():
    """Reset minimal du root logger pour éviter les effets globaux entre tests."""
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.NOTSET)


def test_setup_logging_sets_root_level_and_handlers(tmp_path, monkeypatch):
    _reset_logging()

    # On force un LOG_PATH test pour éviter d'écrire dans le vrai fichier
    log_file = tmp_path / "logs" / "bot.log"

    setup_logging(level=logging.DEBUG, log_file=str(log_file))

    root = logging.getLogger()

    # Root level
    assert root.level == logging.DEBUG

    # Deux handlers: console + fichier
    assert len(root.handlers) == 2

    # Handler console
    sh = next(h for h in root.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler))
    assert sh.stream is sys.stdout
    assert sh.level == logging.DEBUG

    # Handler fichier
    fh = next(h for h in root.handlers if isinstance(h, RotatingFileHandler))
    assert fh.level == logging.DEBUG
    assert getattr(fh, "baseFilename", "").endswith("bot.log")

    # Le dossier doit être créé
    assert log_file.parent.exists()


def test_setup_logging_sets_discord_loggers_to_warning(tmp_path):
    _reset_logging()

    setup_logging(level=logging.INFO, log_file=str(tmp_path / "bot.log"))

    assert logging.getLogger("discord").level == logging.WARNING
    assert logging.getLogger("discord.client").level == logging.WARNING
    assert logging.getLogger("discord.gateway").level == logging.WARNING

    # propagate désactivé pour gateway
    assert logging.getLogger("discord.gateway").propagate is False


def test_setup_logging_replaces_existing_handlers(tmp_path):
    _reset_logging()

    root = logging.getLogger()
    root.addHandler(logging.StreamHandler())

    assert len(root.handlers) == 1

    setup_logging(level=logging.INFO, log_file=str(tmp_path / "bot.log"))

    # Les anciens handlers doivent être supprimés et remplacés par 2 handlers
    assert len(root.handlers) == 2
    assert any(isinstance(h, logging.StreamHandler) for h in root.handlers)
    assert any(isinstance(h, RotatingFileHandler) for h in root.handlers)


def test_setup_logging_formatter_format_and_datefmt(tmp_path):
    _reset_logging()

    setup_logging(level=logging.INFO, log_file=str(tmp_path / "bot.log"))

    root = logging.getLogger()
    for handler in root.handlers:
        formatter = handler.formatter
        assert formatter is not None
        assert formatter._fmt == "%(asctime)s  %(levelname)-10s  %(name)-30s - %(message)s"
        assert formatter.datefmt == "%d/%m/%Y  %H:%M:%S"


def test_setup_logging_adds_noise_filter_to_handlers(tmp_path):
    _reset_logging()

    setup_logging(level=logging.INFO, log_file=str(tmp_path / "bot.log"))

    root = logging.getLogger()
    for handler in root.handlers:
        # On vérifie qu'un filtre de type DiscordReconnectNoiseFilter est présent
        assert any(isinstance(f, DiscordReconnectNoiseFilter) for f in handler.filters)


def test_discord_reconnect_noise_filter_filters_expected_messages():
    f = DiscordReconnectNoiseFilter()

    # On fabrique des LogRecord
    r1 = logging.LogRecord("discord.client", logging.ERROR, __file__, 1, "Attempting a reconnect in 1.66s", args=(), exc_info=None)
    r2 = logging.LogRecord("discord.client", logging.ERROR, __file__, 1, "ClientConnectorDNSError: Cannot connect to host discord.com", args=(), exc_info=None)
    r3 = logging.LogRecord("discord.client", logging.ERROR, __file__, 1, "socket.gaierror: [Errno 11001] getaddrinfo failed", args=(), exc_info=None)
    r4 = logging.LogRecord("discord.client", logging.ERROR, __file__, 1, "Autre message", args=(), exc_info=None)

    assert f.filter(r1) is False
    assert f.filter(r2) is False
    assert f.filter(r3) is False
    assert f.filter(r4) is True