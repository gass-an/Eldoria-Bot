"""Entry point minimal.

Lance le bot en important l'application (setup + events + commandes) depuis eldoria.app.
"""

import logging
import time

from eldoria.app.app import main
from eldoria.utils.logging import setup_logging

if __name__ == "__main__":
    started_at = time.perf_counter()
    setup_logging(logging.INFO)
    main(started_at)
