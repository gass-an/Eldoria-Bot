from __future__ import annotations

import os
import sys
from pathlib import Path

# Pytest peut choisir un rootdir différent selon le contexte. Pour garantir
# que le package `tests.*` résout bien les modules locaux (et non un éventuel
# package `tests` tiers), on force le dossier projet dans sys.path.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Si un autre package nommé `tests` a été importé avant (rare mais possible
# en environnement de CI / tooling), on force l'utilisation du nôtre.
_loaded_tests = sys.modules.get("tests")
if _loaded_tests is not None:
    loaded_path = getattr(_loaded_tests, "__file__", "") or ""
    if not loaded_path.startswith(str(Path(__file__).resolve().parent)):
        sys.modules.pop("tests", None)

from tests._bootstrap.discord_stub import install_discord_stub
from tests._bootstrap.ensure_exceptions import ensure_general_exceptions
from tests._bootstrap.force_mentions import force_real_mentions_module
from tests._bootstrap.sys_path import add_src_to_syspath

# ------------------------------------------------------------
# Env vars (tests) — keep src/ config importable
# ------------------------------------------------------------
# `eldoria.config` lit des variables d'environnement au moment de l'import
# et lève si DISCORD_TOKEN est manquant. En prod c'est normal, en tests on
# injecte une valeur factice.
os.environ.setdefault("DISCORD_TOKEN", "TEST_TOKEN")

# ------------------------------------------------------------
# Bootstrap AVANT imports projet
# ------------------------------------------------------------
add_src_to_syspath()
install_discord_stub()
ensure_general_exceptions()
force_real_mentions_module()

# ------------------------------------------------------------
# Plugins/fixtures partagés
# ------------------------------------------------------------
pytest_plugins = [
    "tests._fixtures.sqlite",
    "tests._fixtures.discord_ui",
]

# ------------------------------------------------------------
# Expose quelques fakes partagés
# ------------------------------------------------------------
from tests._fakes import (  # noqa: E402,F401
    FakeGuild,
    FakeMember,
    FakeMessage,
    FakePrimaryGuild,
    FakeVoiceState,
)
