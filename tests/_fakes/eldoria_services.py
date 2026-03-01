from __future__ import annotations

"""Fakes de services Eldoria partagés par plusieurs tests."""

from datetime import datetime
from types import SimpleNamespace
from typing import Any


class FakeServices(SimpleNamespace):
    """Conteneur de services.

    On peut l'initialiser avec des kwargs: FakeServices(xp=..., duel=...).
    """


class FakeXpService:
    def __init__(self):
        # XP feature flags
        self._enabled = True
        self.sync_calls: list[tuple[Any, list[int]]] = []

        # Generic call log used by multiple suites
        self.calls: list[tuple] = []

        # --- Config & data used by `extensions.xp` tests ---
        # Keep defaults aligned with what UI/admin views expect.
        self._cfg: dict[str, Any] = {
            "enabled": True,
            "points_per_message": 3,
            "cooldown_seconds": 10,
            "bonus_percent": 20,
            "karuta_k_small_percent": 30,
        }
        self._snapshot: dict[str, Any] = {
            "xp": 10,
            "level": 1,
            "level_label": "lvl1",
            "next_level_label": "lvl2",
            "next_xp_required": 20,
        }
        self._levels_with_roles: list[Any] = [{"level": 1, "role_id": 111, "xp_required": 0}]
        self._leaderboard_items: list[Any] = [{"user_id": 1, "xp": 10}]
        self._add_xp_new: int = 150
        self._levels: list[tuple[int, int]] = [(0, 1), (100, 2)]

        # --- Voice XP config used by `extensions.xp_voice` tests ---
        # Some suites treat this dict as the *full* config object, so it must
        # include the global "enabled" flag too.
        self._voice_cfg: dict[str, Any] = {
            "enabled": True,
            "voice_enabled": True,
            "voice_interval_seconds": 180,
            "voice_xp_per_interval": 2,
            "voice_daily_cap_xp": 100,
            "voice_levelup_channel_id": 0,
        }
        self._role_ids: list[int] = []
        self._voice_is_active: bool = True
        self._voice_tick_return: Any = None  # None or (new_xp,new_lvl,old_lvl)
        self._voice_upsert_raises: bool = False
        self._ensure_raises: bool = False

        # per-guild config overrides if a suite needs it
        self._config_by_guild: dict[int, Any] = {}

    def is_enabled(self, guild_id: int) -> bool:
        return self._enabled

    def require_enabled(self, guild_id: int) -> None:
        if not self._enabled:
            from eldoria.exceptions.general import XpDisabled

            raise XpDisabled(guild_id)

    async def sync_xp_roles_for_users(self, guild, user_ids):
        self.sync_calls.append((guild, list(user_ids)))

    # ---------------------------------------------------------------------
    # API: extensions.xp
    # ---------------------------------------------------------------------

    async def ensure_guild_xp_setup(self, guild):
        self.calls.append(("ensure_guild_xp_setup", guild.id))

    def ensure_defaults(self, guild_id: int):
        self.calls.append(("ensure_defaults", guild_id))
        if self._ensure_raises:
            raise RuntimeError("ensure")

    def set_config(self, guild_id: int, **kwargs):
        self.calls.append(("set_config", guild_id, kwargs))
        self._cfg.update(kwargs)

    def get_config(self, guild_id: int):
        self.calls.append(("get_config", guild_id))
        # If a test suite injected a dedicated config, prefer it.
        if guild_id in self._config_by_guild:
            return dict(self._config_by_guild[guild_id])
        # Merge voice cfg + base cfg for convenience.
        # Base cfg must win for overlapping keys like "enabled".
        return {**dict(self._voice_cfg), **dict(self._cfg)}

    def set_level_threshold(self, guild_id: int, level: int, xp_required: int):
        """Update the XP requirement for a given level.

        Production code uses this in the admin "levels" panel.
        """
        self.calls.append(("set_level_threshold", guild_id, level, xp_required))

        # Support both list-of-tuples [(level, xp_required, role_id), ...]
        # and list-of-dicts [{"level":..,"xp_required":..}, ...] depending on suite.
        new_list: list[Any] = []
        updated = False
        for item in list(self._levels_with_roles):
            if isinstance(item, tuple) and len(item) >= 3:
                lvl, _xp, role_id = item[0], item[1], item[2]
                if lvl == level:
                    new_list.append((lvl, xp_required, role_id))
                    updated = True
                else:
                    new_list.append(item)
            elif isinstance(item, dict) and item.get("level") == level:
                new_item = dict(item)
                new_item["xp_required"] = xp_required
                new_list.append(new_item)
                updated = True
            else:
                new_list.append(item)
        if not updated:
            # Append if missing.
            new_list.append((level, xp_required, None))
        self._levels_with_roles = new_list

    def build_snapshot_for_xp_profile(self, guild, user_id: int):
        self.calls.append(("build_snapshot_for_xp_profile", guild.id, user_id))
        return dict(self._snapshot)

    def get_levels_with_roles(self, guild_id: int):
        self.calls.append(("get_levels_with_roles", guild_id))
        return list(self._levels_with_roles)

    def get_leaderboard_items(self, guild, *, limit: int, offset: int):
        self.calls.append(("get_leaderboard_items", guild.id, limit, offset))
        return list(self._leaderboard_items)

    def add_xp(self, guild_id: int, user_id: int, delta: int):
        self.calls.append(("add_xp", guild_id, user_id, delta))
        return self._add_xp_new

    def get_levels(self, guild_id: int):
        self.calls.append(("get_levels", guild_id))
        return list(self._levels)

    def compute_level(self, xp: int):
        self.calls.append(("compute_level", xp))
        # Simple mapping based on `_levels` thresholds.
        lvl = 1
        for threshold, level in self._levels:
            if xp >= threshold:
                lvl = level
        return lvl

    async def sync_member_level_roles(self, guild_id: int, user_id: int, xp: int):
        self.calls.append(("sync_member_level_roles", guild_id, user_id, xp))

    # ---------------------------------------------------------------------
    # API: extensions.xp_voice
    # ---------------------------------------------------------------------

    def is_voice_member_active(self, member):
        self.calls.append(("is_voice_member_active", getattr(member, "id", None)))
        return self._voice_is_active and not getattr(member, "bot", False)

    def voice_upsert_progress(self, guild_id: int, user_id: int, *, last_tick_ts: int):
        self.calls.append(("voice_upsert_progress", guild_id, user_id, last_tick_ts))
        if self._voice_upsert_raises:
            raise RuntimeError("upsert")

    async def tick_voice_xp_for_member(self, guild, member):
        self.calls.append(("tick_voice_xp_for_member", guild.id, member.id))
        return self._voice_tick_return

    def get_role_ids(self, guild_id: int):
        self.calls.append(("get_role_ids", guild_id))
        return list(self._role_ids)


class FakeDuelService:
    def __init__(self):
        self.cleanup_calls: list[Any] = []
        self.cancel_calls = 0
        self.new_duel_calls: list[tuple[int, int, int, int]] = []

        # ------------------------------------------------------------------
        # UI: duels flow (stake config / invite)
        # ------------------------------------------------------------------
        self.allowed_stakes: set[int] = set()
        self.get_allowed_stakes_calls: list[int] = []
        self.configure_calls: list[dict[str, Any]] = []
        self.send_invite_calls: list[dict[str, Any]] = []

        self.raise_on_configure: Exception | None = None
        self.raise_on_send_invite: Exception | None = None

        # Snapshots (valeurs retournées par l'API service côté prod)
        self.snapshot_configure: dict[str, Any] = {
            "duel": {"channel_id": 123, "player_a": 1, "player_b": 2}
        }
        self.snapshot_invite: dict[str, Any] = {
            "xp": {"1": 10},
            "duel": {"stake_xp": 10, "expires_at": 111, "game_type": "rps"},
        }

        # UI: home flow (choix du jeu)
        self.configure_game_type_calls: list[dict[str, Any]] = []
        self.raise_on_configure_game_type: Exception | None = None
        self.snapshot_game_type: dict[str, Any] = {"duel": {"expires_at": 123}}

        # UI: accept/refuse invite
        self.accept_calls: list[dict[str, Any]] = []
        self.refuse_calls: list[dict[str, Any]] = []
        self.raise_on_accept: Exception | None = None
        self.raise_on_refuse: Exception | None = None
        self.snapshot_accept: dict[str, Any] = {"duel": {"game_type": "rps"}}
        self.snapshot_refuse: dict[str, Any] = {
            "duel": {"player_b": 2, "message_id": 444, "channel_id": 555}
        }

        # UI: RPS view actions
        self.play_game_action_calls: list[dict[str, Any]] = []
        self.raise_on_play_game_action: Exception | None = None
        self.snapshot_play_game_action: dict[str, Any] = {"duel": {"id": 1}}

        self._cancel_return: list[dict] = []
        self._new_duel_side_effect: BaseException | None = None

    def cleanup_old_duels(self, ts):
        self.cleanup_calls.append(ts)

    def cancel_expired_duels(self):
        self.cancel_calls += 1
        return list(self._cancel_return)

    def new_duel(self, *, guild_id, channel_id, player_a_id, player_b_id):
        self.new_duel_calls.append((guild_id, channel_id, player_a_id, player_b_id))
        if self._new_duel_side_effect is not None:
            raise self._new_duel_side_effect
        return {"duel": {"expires_at": 111, "id": 777}}

    # ------------------------------------------------------------------
    # UI: duels flow
    # ------------------------------------------------------------------

    def get_allowed_stakes(self, duel_id: int):
        self.get_allowed_stakes_calls.append(duel_id)
        return set(self.allowed_stakes)

    def configure_stake_xp(self, duel_id: int, *, stake_xp: int):
        self.configure_calls.append({"duel_id": duel_id, "stake_xp": stake_xp})
        if self.raise_on_configure is not None:
            raise self.raise_on_configure
        return dict(self.snapshot_configure)

    def send_invite(self, *, duel_id: int, message_id: int):
        self.send_invite_calls.append({"duel_id": duel_id, "message_id": message_id})
        if self.raise_on_send_invite is not None:
            raise self.raise_on_send_invite
        return dict(self.snapshot_invite)

    def configure_game_type(self, duel_id: int, gk: str):
        self.configure_game_type_calls.append({"duel_id": duel_id, "gk": gk})
        if self.raise_on_configure_game_type is not None:
            raise self.raise_on_configure_game_type
        return dict(self.snapshot_game_type)

    def accept_duel(self, *, duel_id: int, user_id: int):
        self.accept_calls.append({"duel_id": duel_id, "user_id": user_id})
        if self.raise_on_accept is not None:
            raise self.raise_on_accept
        return dict(self.snapshot_accept)

    def refuse_duel(self, *, duel_id: int, user_id: int):
        self.refuse_calls.append({"duel_id": duel_id, "user_id": user_id})
        if self.raise_on_refuse is not None:
            raise self.raise_on_refuse
        return dict(self.snapshot_refuse)

    def play_game_action(self, *, duel_id: int, user_id: int, action: dict):
        self.play_game_action_calls.append(
            {"duel_id": duel_id, "user_id": user_id, "action": dict(action)}
        )
        if self.raise_on_play_game_action is not None:
            raise self.raise_on_play_game_action
        return dict(self.snapshot_play_game_action)


class FakeRoleService:
    def __init__(self):
        self._rr_role_id = None
        self._by_message: dict[str, int] = {}
        self._guild_grouped: list[Any] = []
        self.calls: list[tuple] = []

        # secret roles
        self._secret_role_ids: set[int] = set()

        # secret_roles extension API
        self._sr_match_role_id: int | None = None
        self._sr_guild_grouped: list[Any] = []

    # reaction roles API
    def rr_get_role_id(self, guild_id: int, message_id: int, emoji: str):
        self.calls.append(("rr_get_role_id", guild_id, message_id, emoji))
        return self._rr_role_id

    def rr_list_by_message(self, guild_id: int, message_id: int):
        self.calls.append(("rr_list_by_message", guild_id, message_id))
        return dict(self._by_message)

    def rr_upsert(self, guild_id: int, message_id: int, emoji: str, role_id: int):
        self.calls.append(("rr_upsert", guild_id, message_id, emoji, role_id))

    def rr_delete(self, guild_id: int, message_id: int, emoji: str):
        self.calls.append(("rr_delete", guild_id, message_id, emoji))

    def rr_delete_message(self, guild_id: int, message_id: int):
        self.calls.append(("rr_delete_message", guild_id, message_id))

    def rr_list_by_guild_grouped(self, guild_id: int):
        self.calls.append(("rr_list_by_guild_grouped", guild_id))
        return list(self._guild_grouped)

    # secret_roles API
    def sr_match(self, guild_id: int, channel_id: int, message: str):
        self.calls.append(("sr_match", guild_id, channel_id, message))
        return self._sr_match_role_id

    def sr_upsert(self, guild_id: int, channel_id: int, message: str, role_id: int):
        self.calls.append(("sr_upsert", guild_id, channel_id, message, role_id))

    def sr_delete(self, guild_id: int, channel_id: int, message: str):
        self.calls.append(("sr_delete", guild_id, channel_id, message))

    def sr_list_by_guild_grouped(self, guild_id: int):
        self.calls.append(("sr_list_by_guild_grouped", guild_id))
        return list(self._sr_guild_grouped)

    # secret roles API (minimal)
    def secret_is_enabled(self, guild_id: int) -> bool:
        self.calls.append(("secret_is_enabled", guild_id))
        return True

    def secret_list_role_ids(self, guild_id: int):
        self.calls.append(("secret_list_role_ids", guild_id))
        return list(self._secret_role_ids)

    def secret_set_role_enabled(self, guild_id: int, role_id: int, enabled: bool):
        self.calls.append(("secret_set_role_enabled", guild_id, role_id, enabled))
        if enabled:
            self._secret_role_ids.add(role_id)
        else:
            self._secret_role_ids.discard(role_id)


class FakeSaveService:
    def __init__(self, db_path: str = "./data/eldoria.db"):
        self.calls: list[tuple] = []

        # UI API
        self._list_return: list[Any] = []
        self._download_return: Any = None

        # Saves cog API
        self._db_path = db_path
        self.backup_calls: list[str] = []
        self.replace_calls: list[str] = []
        self.init_db_calls = 0

    # --- UI API ---
    def list_saves(self, guild_id: int):
        self.calls.append(("list_saves", guild_id))
        return list(self._list_return)

    def download_save(self, guild_id: int, name: str):
        self.calls.append(("download_save", guild_id, name))
        return self._download_return

    def upload_save(self, guild_id: int, name: str, data: bytes):
        self.calls.append(("upload_save", guild_id, name, data))

    def delete_save(self, guild_id: int, name: str):
        self.calls.append(("delete_save", guild_id, name))

    # --- Saves cog API ---
    def get_db_path(self):
        return self._db_path

    def backup_to_file(self, dst: str):
        self.backup_calls.append(dst)

    def replace_db_file(self, tmp_new: str):
        self.replace_calls.append(tmp_new)

    def init_db(self):
        self.init_db_calls += 1


class FakeTempVoiceService:
    def __init__(self):
        self.calls: list[tuple] = []

        # Config API (temp voice settings)
        self._configs: dict[int, Any] = {}

        # Active/parents API (temp voice runtime)
        self._parents: dict[tuple[int, int], int] = {}
        self._find_parent_of_active: dict[tuple[int, int], int] = {}

        # Saves cog cleanup API
        self._list_active_all_return: list[tuple[int, int]] = [(1, 111), (1, 222)]

        # compat assertions (saves tests)
        self.remove_calls: list[tuple[int, int, int]] = []

    def get_config(self, guild_id: int):
        self.calls.append(("get_config", guild_id))
        return self._configs.get(guild_id)

    def set_config(self, guild_id: int, config: Any):
        self.calls.append(("set_config", guild_id, config))
        self._configs[guild_id] = config

    # --- runtime API (used by temp voice cog) ---
    def find_parent_of_active(self, guild_id: int, channel_id: int):
        self.calls.append(("find_parent_of_active", guild_id, channel_id))
        return self._find_parent_of_active.get((guild_id, channel_id))

    def remove_active(self, guild_id: int, parent_id: int, channel_id: int):
        self.calls.append(("remove_active", guild_id, parent_id, channel_id))
        self.remove_calls.append((guild_id, parent_id, channel_id))

    def get_parent(self, guild_id: int, channel_id: int):
        self.calls.append(("get_parent", guild_id, channel_id))
        return self._parents.get((guild_id, channel_id))

    def add_active(self, guild_id: int, parent_id: int, channel_id: int):
        self.calls.append(("add_active", guild_id, parent_id, channel_id))
        self._find_parent_of_active[(guild_id, channel_id)] = parent_id

    def upsert_parent(self, guild_id: int, channel_id: int, user_limit: int):
        self.calls.append(("upsert_parent", guild_id, channel_id, user_limit))
        self._parents[(guild_id, channel_id)] = user_limit

    def delete_parent(self, guild_id: int, channel_id: int):
        self.calls.append(("delete_parent", guild_id, channel_id))
        self._parents.pop((guild_id, channel_id), None)

    def list_parents(self, guild_id: int):
        self.calls.append(("list_parents", guild_id))
        # API canonique du service: [(parent_channel_id, user_limit), ...]
        return [
            (cid, lim)
            for (gid, cid), lim in self._parents.items()
            if gid == guild_id
        ]

    def list_active_all(self, guild_id: int):
        self.calls.append(("list_active_all", guild_id))
        return list(self._list_active_all_return)


class FakeWelcomeService:
    def __init__(self):
        self.calls: list[tuple] = []
        self._config_by_guild: dict[int, Any] = {}

        # welcome message API
        self._welcome_ret: tuple[str, str, list[str]] = ("Titre", "Message de bienvenue", ["😀", "🔥"])

        # panel config defaults
        self._cfg: dict[str, Any] = {"enabled": False, "channel_id": 0}

    def get_config(self, guild_id: int):
        self.calls.append(("get_config", guild_id))
        if guild_id in self._config_by_guild:
            return self._config_by_guild[guild_id]
        return dict(self._cfg)

    def set_config(self, guild_id: int, config: Any = None, **kwargs):
        # Supporte les 2 formes:
        # - set_config(guild_id, config_dict)
        # - set_config(guild_id, **kwargs)
        if kwargs:
            payload = dict(kwargs)
            self.calls.append(("set_config", guild_id, payload))
            cfg = dict(self.get_config(guild_id))
            cfg.update(payload)
            self._config_by_guild[guild_id] = cfg
            return None

        self.calls.append(("set_config", guild_id, config))
        self._config_by_guild[guild_id] = config
        return None

    # ---- panel API ----
    def ensure_defaults(self, guild_id: int):
        self.calls.append(("ensure_defaults", guild_id))

    def set_enabled(self, guild_id: int, enabled: bool):
        self.calls.append(("set_enabled", guild_id, enabled))
        cfg = dict(self.get_config(guild_id))
        cfg["enabled"] = enabled
        self._config_by_guild[guild_id] = cfg

    # alias explicite si une suite en a besoin
    def set_config_kwargs(self, guild_id: int, **kwargs):
        return self.set_config(guild_id, **kwargs)

    def set_welcome_message_result(self, ret: tuple[str, str, list[str]]):
        self._welcome_ret = ret

    def get_welcome_message(self, guild_id: int, *, user: str, server: str, recent_limit: int):
        self.calls.append(("get_welcome_message", guild_id, user, server, recent_limit))
        return self._welcome_ret


# ---------------------------------------------------------------------------
# Divers fakes utilitaires (app/db/ui) – centralisés pour réduire les fichiers.
# ---------------------------------------------------------------------------


class FakeDiscord:
    """Stub de module discord utilisé par `eldoria.app.banner`."""

    __version__ = "X.Y.Z"


def make_datetime_now(fixed_now: datetime):
    """Factory pour monkeypatch `datetime.datetime` dans les tests."""

    class DateTime:
        @staticmethod
        def now():
            return fixed_now

    return DateTime


class Logger:
    """Logger polyvalent pour les tests app.

    - `eldoria.app.startup` : attend `infos`/`exceptions` contenant des tuples.
    - `eldoria.app.run_tests` : attend `warnings` (strings) avec formatage %.
    """

    def __init__(self):
        self.infos: list[tuple] = []
        self.exceptions: list[tuple] = []
        self.warnings: list[str] = []

    def info(self, msg, *args, **_kwargs):
        # startup() passe (fmt, label, ms) => on conserve les tuples
        if args:
            self.infos.append((msg, *args))
        else:
            self.infos.append(str(msg))

    def warning(self, msg, *args, **_kwargs):
        if args:
            try:
                msg = msg % args
            except Exception:
                msg = " ".join([str(msg), *map(str, args)])
        self.warnings.append(str(msg))

    def exception(self, msg, *args, **_kwargs):
        # Dans startup() on stocke les args bruts.
        self.exceptions.append((msg, *args))


def make_tests_path(*, exists: bool, names: list[str] | None = None):
    """Factory pour monkeypatch Path-like (eldoria.app.run_tests)."""

    from types import SimpleNamespace

    names = names or []

    class Path:
        def exists(self):
            return exists

        def rglob(self, _pattern):
            return [SimpleNamespace(name=n) for n in names]

    return Path()


def make_services_class(sink: dict):
    """Factory pour monkeypatch `Services` (eldoria.app.startup)."""

    class Services:
        def __init__(self, **kwargs):
            sink.update(kwargs)

        def __len__(self):
            return len(sink)

    return Services


class FakeBotGuild:
    """Guild objects inside bot.guilds for cleanup loop (saves)."""

    def __init__(self, gid: int, existing_channel_ids: set[int]):
        self.id = gid
        self._existing = existing_channel_ids

    def get_channel(self, cid: int):
        return object() if cid in self._existing else None


class FakeDatetime(datetime):
    """datetime subclass used by monkeypatch in saves tests."""

    _now: datetime | None = None

    @classmethod
    def now(cls, tz=None):
        assert cls._now is not None
        return cls._now


class FakeDuelError(Exception):
    pass


# ---------------------------------------------------------------------------
# DB fakes (repos + connection/schema/maintenance)
# ---------------------------------------------------------------------------


class FakeCursor:
    """Cursor minimaliste pour les repos (fetchone/fetchall/lastrowid)."""

    def __init__(self, *, one: Any = None, all: Any = None, lastrowid: Any = None):
        self._one = one
        self._all = all
        self.lastrowid = lastrowid

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._all


class FakeConn:
    """Connexion SQLite fake consolidée.

    Supporte à la fois:
    - tests de repos: execute(sql, params) -> cursor + `calls`
    - tests de connexion: execute(sql) + commit/close + `executed`
    """

    def __init__(self):
        self.calls: list[tuple[str, tuple]] = []
        self.executed: list[str] = []
        self.committed = 0
        self.closed = 0
        self._raise_on_execute: str | None = None
        self._next = FakeCursor(one=None, all=[])

    def set_next_cursor(self, cursor: FakeCursor):
        self._next = cursor

    def set_next(self, *, one=None, all=None, lastrowid=None):
        self._next = FakeCursor(one=one, all=all, lastrowid=lastrowid)

    def execute(self, sql: str, params: tuple = ()):  # compat: params optionnels
        self.executed.append(sql)
        self.calls.append((sql.strip(), params))
        if self._raise_on_execute and self._raise_on_execute in sql:
            raise RuntimeError("boom execute")
        return self._next

    def commit(self):
        self.committed += 1

    def close(self):
        self.closed += 1


class FakeConnCM:
    """Context manager qui renvoie une FakeConn."""

    def __init__(self, conn: FakeConn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        return False


def is_enterable(obj) -> bool:
    return hasattr(obj, "__enter__") and hasattr(obj, "__exit__")


class Cursor:
    """Cursor générique (db maintenance/schema)."""

    def __init__(self, row=(1,), rows=None):
        self._row = row
        self._rows = rows

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


class Conn:
    """Connexion générique pour tests db maintenance/schema."""

    def __init__(self, name: str = "main", *, pragma_rows=None):
        self.name = name
        self.pragma_rows = pragma_rows if pragma_rows is not None else []
        self.executed: list[str] = []
        self.scripts: list[str] = []
        self.closed = 0
        self.backup_calls: list[object] = []

    def execute(self, sql: str):
        self.executed.append(sql)
        if sql.strip().upper().startswith("PRAGMA TABLE_INFO"):
            return Cursor(rows=self.pragma_rows)
        return Cursor(row=(1,))

    def executescript(self, script: str):
        self.scripts.append(script)
        return None

    def close(self):
        self.closed += 1

    def backup(self, other_conn):
        self.backup_calls.append(other_conn)


class ConnCM:
    """Context manager qui retourne une Conn."""

    def __init__(self, conn: Conn):
        self.conn = conn
        self.entered = 0
        self.exited = 0

    def __enter__(self):
        self.entered += 1
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        self.exited += 1
        return False


def make_db_error(sqlite_db_error_type: type[BaseException]) -> type[BaseException]:
    """Crée un type d'exception qui hérite de `sqlite3.DatabaseError` du module testé."""

    return type("DbError", (sqlite_db_error_type,), {})
