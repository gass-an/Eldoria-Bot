from __future__ import annotations

from tests._bootstrap.discord_stub import install_discord_stub
from tests._bootstrap.ensure_exceptions import ensure_general_exceptions
from tests._bootstrap.force_mentions import force_real_mentions_module
from tests._bootstrap.sys_path import add_src_to_syspath

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
]

# ------------------------------------------------------------
# (Compat) Expose quelques fakes historiques si certains tests les utilisent
# ------------------------------------------------------------
from tests._fakes._discord_entities_fakes import (  # noqa: E402,F401
    FakeGuild,
    FakeMember,
    FakeMessage,
    FakePrimaryGuild,
    FakeVoiceState,
)
