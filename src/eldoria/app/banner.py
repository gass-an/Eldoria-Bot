import sys
import textwrap
from datetime import datetime

import discord

from eldoria.version import VERSION


def startup_banner(started_at: datetime | None = None) -> str:
    started_at = started_at or datetime.now()
    now = started_at.strftime("%H:%M:%S %d/%m/%Y")
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

    lines = [
        f" Eldoria Bot v{VERSION}",
        "",
        f" Python   : {py}",
        f" py-cord  : {pycord}",
        f" Started  : {now}",
    ]

    w = max(len(l) for l in lines) + 2

    top = "╔" + "═" * w + "╗"
    sep = "╟" + "─" * w + "╢"
    bot = "╚" + "═" * w + "╝"

    body = []
    for i, line in enumerate(lines):
        if i == 1:
            body.append(sep)
            continue
        body.append(f"║ {line.ljust(w - 1)}║")

    box = "\n".join([top, *body, bot])

    return f"{logo}\n{box}\n"


