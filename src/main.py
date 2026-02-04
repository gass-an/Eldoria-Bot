"""Entry point minimal.

Lance le bot en important l'application (setup + events + commandes) depuis eldoria.app.
"""

import logging
from eldoria.app.app import main
from eldoria.utils.logging import setup_logging


if __name__ == "__main__":
    setup_logging(logging.INFO)
    main()
