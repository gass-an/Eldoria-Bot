"""Module de démarrage du bot Eldoria, contenant les fonctions nécessaires pour initialiser les services, charger les extensions et préparer l'application avant de se connecter à Discord."""

import logging
import time
from collections.abc import Callable
from typing import Any

from eldoria.app.bot import EldoriaBot
from eldoria.app.extensions import EXTENSIONS
from eldoria.app.run_tests import run_tests
from eldoria.app.services import Services
from eldoria.db.schema import init_db
from eldoria.features.duel.duel_service import DuelService
from eldoria.features.duel.games import init_games
from eldoria.features.role.role_service import RoleService
from eldoria.features.save.save_service import SaveService
from eldoria.features.temp_voice.cleanup import cleanup_temp_channels
from eldoria.features.temp_voice.temp_voice_service import TempVoiceService
from eldoria.features.welcome.welcome_service import WelcomeService
from eldoria.features.xp.xp_service import XpService
from eldoria.ui.duels import init_duel_ui

log = logging.getLogger(__name__)


def step(name: str, action: Callable[[], Any], *, critical: bool = True, logger: logging.Logger | None = None) -> None:
    """Exécute une étape de démarrage du bot en mesurant le temps d'exécution et en gérant les exceptions de manière centralisée."""
    start = time.perf_counter()
    if logger is None : 
        logger = log
    try:
        result = action()
        ms = (time.perf_counter() - start) * 1000
        label = f"{name} ({result})" if result is not None else name
        logger.info("✅ %-53s %8.1f ms", label, ms)
    except Exception:
        ms = (time.perf_counter() - start) * 1000
        logger.exception("❌ %-50s %8.1f ms", name, ms)
        if critical:
            raise

def load_extensions(bot: EldoriaBot) -> int:
    """Charge les extensions définies dans EXTENSIONS et retourne le nombre d'extensions chargées."""
    count = 0
    for ext in EXTENSIONS:
        bot.load_extension(ext)
        count += 1
    return count

def init_services(bot: EldoriaBot) -> int:
    """Initialise les services utilisés par le bot et les assigne à l'attribut services du bot, puis retourne le nombre de services initialisés."""
    bot.set_services(Services(
        duel=DuelService(),
        role=RoleService(),
        save=SaveService(),
        temp_voice=TempVoiceService(),
        welcome=WelcomeService(),
        xp=XpService(),
    ))
    return len(bot.services)

def startup(bot: EldoriaBot) -> None:
    """Exécute les différentes étapes de démarrage du bot en utilisant la fonction step pour mesurer le temps d'exécution et gérer les exceptions."""
    step("Tests", lambda: run_tests(logger=log), critical=False)

    step("Initialisation des services", lambda: init_services(bot), critical=False)
    step("Initialisation des extensions", lambda: load_extensions(bot))
    step("Initialisation de la base de données", init_db)
    step("Nettoyage des channels temporaires", lambda: cleanup_temp_channels(bot), critical=False)
    step("Initialisation des jeux de duel", init_games, critical=False)
    step("Initialisation UI duel", init_duel_ui, critical=False)
