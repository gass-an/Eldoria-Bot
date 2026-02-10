import logging
import time
from discord.ext import commands

from eldoria.app.bot import EldoriaBot
from eldoria.app.extensions import EXTENSIONS
from eldoria.app.services import Services
from eldoria.db.repo.temp_voice_repo import tv_list_active_all, tv_remove_active
from eldoria.db.schema import init_db
from eldoria.features.duel.duel_service import DuelService
from eldoria.features.duel.games import init_games
from eldoria.features.xp.xp_service import XpService
from eldoria.ui.duels import init_duel_ui

log = logging.getLogger(__name__)


def step(name: str, fn, *, critical: bool = True, logger: logging.Logger | None = None):
    start = time.perf_counter()
    if logger is None : 
        logger = log
    try:
        result = fn()
        ms = (time.perf_counter() - start) * 1000
        label = f"{name} ({result})" if result is not None else name
        logger.info("✅ %-53s %8.1f ms", label, ms)
    except Exception:
        ms = (time.perf_counter() - start) * 1000
        logger.exception("❌ %-50s %8.1f ms", name, ms)
        if critical:
            raise

def load_extensions(bot: EldoriaBot) -> int:
    count = 0
    for ext in EXTENSIONS:
        bot.load_extension(ext)
        count += 1
    return count

def cleanup_temp_channels(bot: EldoriaBot):
    for guild in bot.guilds:
        rows = tv_list_active_all(guild.id)
        for parent_id, channel_id in rows:
            if guild.get_channel(channel_id) is None:
                tv_remove_active(guild.id, parent_id, channel_id)

def init_services(bot: EldoriaBot):
    bot.services = Services(
        duel=DuelService(),
        xp=XpService(),
    )

def startup(bot):
    step("Initialisation des services", lambda: init_services(bot), critical=False)
    step("Initialisation des extensions", lambda: load_extensions(bot))
    step("Initialisation de la base de données", init_db)
    step("Nettoyage des channels temporaires", lambda: cleanup_temp_channels(bot), critical=False)
    step("Initialisation des jeux de duel", init_games, critical=False)
    step("Initialisation UI duel", init_duel_ui, critical=False)
