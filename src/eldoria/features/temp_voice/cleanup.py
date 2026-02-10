from eldoria.app.bot import EldoriaBot
from eldoria.db.repo.temp_voice_repo import tv_list_active_all, tv_remove_active


def cleanup_temp_channels(bot: EldoriaBot) -> None:
    for guild in bot.guilds:
        rows = tv_list_active_all(guild.id)
        for parent_id, channel_id in rows:
            if guild.get_channel(channel_id) is None:
                tv_remove_active(guild.id, parent_id, channel_id)