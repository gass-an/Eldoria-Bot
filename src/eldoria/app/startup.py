import logging
import time

from eldoria.db.repo.temp_voice_repo import tv_list_active_all, tv_remove_active
from eldoria.db.schema import init_db
from eldoria.features.duel.games import init_games
from eldoria.ui.duels import init_duel_ui

log = logging.getLogger("eldoria.startup")


def step(name: str, fn, *, critical: bool = True):
    start = time.perf_counter()
    try:
        fn()
        ms = (time.perf_counter() - start) * 1000
        log.info("✅ %-50s %6.1f ms", name, ms)
    except Exception:
        ms = (time.perf_counter() - start) * 1000
        log.exception("❌ %-50s %6.1f ms", name, ms)
        if critical:
            raise


def startup(bot):
    step("Initialisation de la base de données", init_db)

    def cleanup_temp_channels():
        for guild in bot.guilds:
            rows = tv_list_active_all(guild.id)
            for parent_id, channel_id in rows:
                if guild.get_channel(channel_id) is None:
                    tv_remove_active(guild.id, parent_id, channel_id)

    step("Nettoyage des channels temporaires", cleanup_temp_channels, critical=False)
    step("Initialisation des jeux de duel", init_games, critical=False)
    step("Initialisation UI duel", init_duel_ui, critical=False)
