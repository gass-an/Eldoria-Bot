import logging
import sys

from eldoria.utils.logging import setup_logging


def _reset_logging():
    """Reset minimal du root logger pour éviter les effets globaux entre tests."""
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.NOTSET)


def test_setup_logging_sets_root_level_and_handler():
    _reset_logging()

    setup_logging(level=logging.DEBUG)

    root = logging.getLogger()

    # Root level
    assert root.level == logging.DEBUG

    # Un seul handler
    assert len(root.handlers) == 1

    handler = root.handlers[0]

    # Handler est un StreamHandler
    assert isinstance(handler, logging.StreamHandler)

    # Handler écrit vers stdout
    assert handler.stream is sys.stdout

    # Handler level correct
    assert handler.level == logging.DEBUG


def test_setup_logging_sets_discord_loggers_to_warning():
    _reset_logging()

    setup_logging(level=logging.INFO)

    assert logging.getLogger("discord").level == logging.WARNING
    assert logging.getLogger("discord.client").level == logging.WARNING
    assert logging.getLogger("discord.gateway").level == logging.WARNING

    # propagate désactivé pour gateway
    assert logging.getLogger("discord.gateway").propagate is False


def test_setup_logging_replaces_existing_handlers():
    _reset_logging()

    root = logging.getLogger()
    root.addHandler(logging.StreamHandler())

    assert len(root.handlers) == 1

    setup_logging(level=logging.INFO)

    # Les anciens handlers doivent être supprimés
    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0], logging.StreamHandler)


def test_setup_logging_formatter_format():
    _reset_logging()

    setup_logging(level=logging.INFO)

    handler = logging.getLogger().handlers[0]
    formatter = handler.formatter

    # Vérifie le format exact
    assert formatter._fmt == "%(asctime)-10s  %(levelname)-10s  %(name)-30s - %(message)s"
    assert formatter.datefmt == "%H:%M:%S"
