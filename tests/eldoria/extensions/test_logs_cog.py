import logging

import pytest

# >>> ADAPTE CE CHEMIN AU BON MODULE <<<
# Exemple si ton cog est dans src/eldoria/extensions/logs.py :
import eldoria.extensions.logs as logs_mod


class DummyFollowup:
    def __init__(self):
        self.calls = []

    async def send(self, *args, **kwargs):
        self.calls.append((args, kwargs))


class DummyUser:
    def __init__(self, user_id: int, name: str = "Faucon"):
        self.id = user_id
        self.name = name


class DummyCtx:
    def __init__(self, user: DummyUser):
        self.user = user
        self.followup = DummyFollowup()
        self.defer_calls = []

    async def defer(self, *args, **kwargs):
        self.defer_calls.append((args, kwargs))


class DummyBot:
    pass


class DummyDiscordFile:
    def __init__(self, fp=None, filename=None):
        self.fp = fp
        self.filename = filename


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch):
    """
    Evite les effets de bord entre tests:
    - reset du logger caplog
    - reset du flag est_deconnecte via nouvelle instance à chaque test
    """
    yield


@pytest.mark.asyncio
async def test_enabled_reflects_log_enabled(monkeypatch):
    monkeypatch.setattr(logs_mod, "LOG_ENABLED", True)
    monkeypatch.setattr(logs_mod, "LOG_ADMIN_ID", 123)

    cog = logs_mod.Logs(DummyBot())
    assert cog._enabled() is True

    monkeypatch.setattr(logs_mod, "LOG_ENABLED", False)
    # nouvelle instance pour refléter la config à l'init
    cog2 = logs_mod.Logs(DummyBot())
    assert cog2._enabled() is False


@pytest.mark.asyncio
async def test_on_disconnect_logs_once_and_sets_flag(monkeypatch, caplog):
    monkeypatch.setattr(logs_mod, "LOG_ENABLED", True)
    monkeypatch.setattr(logs_mod, "LOG_ADMIN_ID", 123)

    cog = logs_mod.Logs(DummyBot())

    caplog.set_level(logging.WARNING, logger=logs_mod.__name__)

    assert cog.est_deconnecte is False
    await cog.on_disconnect()
    assert cog.est_deconnecte is True

    # Second appel: ne doit pas relogger
    await cog.on_disconnect()

    msgs = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert msgs.count("🛑 Déconnexion de la gateway Discord") == 1


@pytest.mark.asyncio
async def test_on_connect_resets_flag_and_logs(monkeypatch, caplog):
    monkeypatch.setattr(logs_mod, "LOG_ENABLED", True)
    monkeypatch.setattr(logs_mod, "LOG_ADMIN_ID", 123)

    cog = logs_mod.Logs(DummyBot())
    cog.est_deconnecte = True

    caplog.set_level(logging.INFO, logger=logs_mod.__name__)

    await cog.on_connect()
    assert cog.est_deconnecte is False

    msgs = [r.message for r in caplog.records if r.levelno == logging.INFO]
    assert "🔌 Connexion à la gateway Discord établie" in msgs


@pytest.mark.asyncio
async def test_on_resumed_resets_flag_and_logs(monkeypatch, caplog):
    monkeypatch.setattr(logs_mod, "LOG_ENABLED", True)
    monkeypatch.setattr(logs_mod, "LOG_ADMIN_ID", 123)

    cog = logs_mod.Logs(DummyBot())
    cog.est_deconnecte = True

    caplog.set_level(logging.INFO, logger=logs_mod.__name__)

    await cog.on_resumed()
    assert cog.est_deconnecte is False

    msgs = [r.message for r in caplog.records if r.levelno == logging.INFO]
    assert "🔁 Session Discord reprise avec succès" in msgs


@pytest.mark.asyncio
async def test_logs_command_feature_disabled(monkeypatch):
    monkeypatch.setattr(logs_mod, "LOG_ENABLED", False)
    # Pas besoin d'admin id si disabled, mais on le met quand même
    monkeypatch.setattr(logs_mod, "LOG_ADMIN_ID", 123)

    cog = logs_mod.Logs(DummyBot())
    ctx = DummyCtx(DummyUser(user_id=123))

    await cog.logs_command(ctx)

    # defer(ephemeral=True) toujours appelé
    assert ctx.defer_calls
    _args, kwargs = ctx.defer_calls[0]
    assert kwargs.get("ephemeral") is True

    # message "feature non configurée"
    assert len(ctx.followup.calls) == 1
    (args, kwargs2) = ctx.followup.calls[0]
    assert kwargs2.get("content") == "Feature logs non configurée (.env)."


@pytest.mark.asyncio
async def test_logs_command_non_admin_denied(monkeypatch):
    monkeypatch.setattr(logs_mod, "LOG_ENABLED", True)
    monkeypatch.setattr(logs_mod, "LOG_ADMIN_ID", 999)

    cog = logs_mod.Logs(DummyBot())
    ctx = DummyCtx(DummyUser(user_id=123))

    await cog.logs_command(ctx)

    assert ctx.defer_calls
    assert len(ctx.followup.calls) == 1
    (_args, kwargs) = ctx.followup.calls[0]
    assert kwargs.get("content") == "Vous ne pouvez pas faire cela"


@pytest.mark.asyncio
async def test_logs_command_admin_sends_codeblock(monkeypatch, caplog):
    monkeypatch.setattr(logs_mod, "LOG_ENABLED", True)
    monkeypatch.setattr(logs_mod, "LOG_ADMIN_ID", 123)

    # tail_lines renvoie un contenu court
    monkeypatch.setattr(logs_mod, "tail_lines", lambda: "ligne1\nligne2\n")

    cog = logs_mod.Logs(DummyBot())
    ctx = DummyCtx(DummyUser(user_id=123, name="Faucon"))

    caplog.set_level(logging.INFO, logger=logs_mod.__name__)

    await cog.logs_command(ctx)

    assert len(ctx.followup.calls) == 1
    (args, kwargs) = ctx.followup.calls[0]
    # message codeblock
    assert args[0].startswith("```text\n")
    assert "ligne1" in args[0]
    assert kwargs.get("ephemeral") is True

    # log d'utilisation
    msgs = [r.message for r in caplog.records if r.levelno == logging.INFO]
    assert any("Utilisation de la commande logs par Faucon" in m for m in msgs)


@pytest.mark.asyncio
async def test_logs_command_admin_sends_file_when_too_long(monkeypatch):
    monkeypatch.setattr(logs_mod, "LOG_ENABLED", True)
    monkeypatch.setattr(logs_mod, "LOG_ADMIN_ID", 123)

    # tail_lines renvoie un gros contenu
    monkeypatch.setattr(logs_mod, "tail_lines", lambda: "a" * 2000)

    # Evite de dépendre de discord.File réel
    monkeypatch.setattr(logs_mod.discord, "File", DummyDiscordFile)

    cog = logs_mod.Logs(DummyBot())
    ctx = DummyCtx(DummyUser(user_id=123, name="Faucon"))

    await cog.logs_command(ctx)

    assert len(ctx.followup.calls) == 1
    (_args, kwargs) = ctx.followup.calls[0]

    assert "file" in kwargs
    assert isinstance(kwargs["file"], DummyDiscordFile)
    assert kwargs["file"].filename == "bot.log.tail.txt"
    assert kwargs.get("ephemeral") is True