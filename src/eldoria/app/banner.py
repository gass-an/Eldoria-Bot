import sys
from datetime import datetime
import textwrap

import discord

from eldoria.version import VERSION


def startup_banner(started_at: datetime | None = None) -> str:
    started_at = started_at or datetime.now()
    now = started_at.strftime("%Y-%m-%d %H:%M:%S")
    py = sys.version.split()[0]
    pycord = discord.__version__

    logo = textwrap.dedent(r"""
                           
███████╗██╗     ██████╗  ██████╗ ██████╗ ██╗ █████╗
██╔════╝██║     ██╔══██╗██╔═══██╗██╔══██╗██║██╔══██╗
█████╗  ██║     ██║  ██║██║   ██║██████╔╝██║███████║
██╔══╝  ██║     ██║  ██║██║   ██║██╔══██╗██║██╔══██║
███████╗███████╗██████╔╝╚██████╔╝██║  ██║██║██║  ██║
╚══════╝╚══════╝╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝
""")

    info = [
        f"Eldoria Bot v{VERSION}",
        f"Python {py} | py-cord {pycord}",
        f"Started at {now}",
    ]
    w = max(len(x) for x in info) + 2
    box = ["┌" + "─" * w + "┐"] + [f"│ {x.ljust(w-1)}│" for x in info] + ["└" + "─" * w + "┘"]

    return logo + "\n" +"\n".join(box) + "\n"

