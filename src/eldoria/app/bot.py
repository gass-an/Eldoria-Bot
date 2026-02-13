"""Module principal du bot Eldoria, définissant la classe EldoriaBot et ses fonctionnalités de base."""

import time
from collections.abc import Callable, Coroutine, Iterable
from typing import Any, TypeAlias

import discord
from discord.ext import commands

from eldoria.app.services import Services

BotLike: TypeAlias = commands.Bot | commands.AutoShardedBot

CommandPrefix: TypeAlias = str | Iterable[str] | Callable[
    [BotLike, discord.Message],
    str | Iterable[str] | Coroutine[Any, Any, str | Iterable[str]],
]

class EldoriaBot(commands.Bot):
    """Classe principale du bot Eldoria, héritant de commands.Bot et ajoutant des fonctionnalités spécifiques à l'application."""

    def __init__(
        self,
        *,
        intents: discord.Intents,
        command_prefix: CommandPrefix = commands.when_mentioned,
        **options: Any,
    ) -> None:
        """Initialise une instance du bot Eldoria avec les intentions, le préfixe de commande et les options spécifiés."""
        super().__init__(command_prefix=command_prefix, intents=intents, **options) # pyright: ignore[reportUnknownMemberType]

        self._booted: bool = False
        self._started_at: float = time.perf_counter()
        self._discord_started_at: float | None = None
        self.services: Services | None = None

    def set_started_at(self, timestamp: float) -> None:
        """Définit le timestamp de démarrage du bot, utilisé pour mesurer les temps de chargement et d'exécution."""
        self._started_at = timestamp

    def get_started_at(self) -> float | None:
        """Retourne le timestamp de démarrage du bot, ou None s'il n'a pas encore été défini."""
        return self._started_at
    
    def set_booted(self, value: bool) -> None:
        """Définit l'état de démarrage du bot, indiquant s'il a déjà été prêt ou non."""
        self._booted = value

    def is_booted(self) -> bool:
        """Retourne True si le bot a déjà été prêt, False sinon."""
        return self._booted
    
    def set_discord_started_at(self, timestamp: float) -> None:
        """Définit le timestamp de connexion à Discord, utilisé pour mesurer les temps de chargement liés à Discord."""
        self._discord_started_at = timestamp

    def get_discord_started_at(self) -> float | None:
        """Retourne le timestamp de connexion à Discord, ou None s'il n'a pas encore été défini."""
        return self._discord_started_at
