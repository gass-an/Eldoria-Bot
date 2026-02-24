"""Utilitaires pour la configuration du logging, avec un format lisible et une réduction du bruit des logs Discord."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from eldoria.config import LOG_PATH


class DiscordReconnectNoiseFilter(logging.Filter):
    """Filtre de logging pour réduire le bruit des messages de reconnect de la bibliothèque pycord."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Filtre les messages de log liés aux tentatives de reconnexion bruyantes (DNS / connect host) de pycord."""
        msg = record.getMessage()
        # Filtre les reconnects bruyants (DNS / connect host)
        if "Attempting a reconnect" in msg:
            return False
        if "ClientConnectorDNSError" in msg or "getaddrinfo failed" in msg:
            return False
        return True
    

def setup_logging(
        level: int = logging.INFO,
        log_file: str = LOG_PATH,
        max_bytes: int = 5_000_000,  # ~5MB
        backup_count: int = 5,       # garde bot.log.1 ... bot.log.5
        ) -> None:
    """Configure le logging avec un format lisible et une réduction du bruit des logs Discord."""
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    # Réduction du bruit Discord
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.client").setLevel(logging.WARNING)
    logging.getLogger("discord.gateway").setLevel(logging.WARNING)
    logging.getLogger("discord.gateway").propagate = False

    formatter = logging.Formatter(
        "%(asctime)s  %(levelname)-10s  %(name)-30s - %(message)s",
        datefmt="%d/%m/%Y  %H:%M:%S",
    )
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)
    stream_handler.addFilter(DiscordReconnectNoiseFilter())
    
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
    file_handler.addFilter(DiscordReconnectNoiseFilter())
