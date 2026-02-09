import time
from discord.ext import commands

from eldoria.app.services import Services

class EldoriaBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self._booted: bool = False
        self._started_at: float | None = time.perf_counter()
        self.services: Services | None = None
