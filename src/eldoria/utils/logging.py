"""Utilitaires pour la configuration du logging, avec un format lisible et une réduction du bruit des logs Discord."""

from __future__ import annotations

import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """Configure le logging pour afficher les messages de niveau INFO ou supérieur, avec un format lisible, et réduit le bruit des logs Discord."""
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    # Réduction du bruit Discord
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.client").setLevel(logging.WARNING)
    logging.getLogger("discord.gateway").setLevel(logging.WARNING)
    logging.getLogger("discord.gateway").propagate = False

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)-10s  %(levelname)-10s  %(name)-30s - %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(formatter)

    root.addHandler(handler)
