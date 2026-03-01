import logging
from types import SimpleNamespace

import pytest

import eldoria.extensions.logs as logs_mod
from tests._fakes import FakeBot, FakeCtx, FakeUser


@pytest.fixture(autouse=True)
def _reset_state():
    # Le module Logs garde un peu d'état interne. On laisse pytest isoler chaque test.
    yield


@pytest.mark.asyncio
async def test_enabled_reflects_log_enabled(monkeypatch):
    monkeypatch.setattr(logs_mod, "LOG_ENABLED", True)
    monkeypatch.setattr(logs_mod, "get_log_admin_id", lambda: 123)

    cog = logs_mod.Logs(FakeBot())
    assert cog._enabled() is True
    assert cog.admin_user_id == 123

    monkeypatch.setattr(logs_mod, "LOG_ENABLED", False)
    cog2 = logs_mod.Logs(FakeBot())
    assert cog2._enabled() is False
    # pas d'admin_user_id défini quand disabled (comportement actuel)
    assert not hasattr(cog2, "admin_user_id")


@pytest.mark.asyncio
async def test_on_disconnect_logs_once_and_sets_flag(monkeypatch, caplog):
    monkeypatch.setattr(logs_mod, "LOG_ENABLED", True)
    monkeypatch.setattr(logs_mod, "get_log_admin_id", lambda: 123)

    cog = logs_mod.Logs(FakeBot())

    caplog.set_level(logging.WARNING, logger=logs_mod.__name__)

    assert cog.est_deconnecte is False
    await cog.on_disconnect()
    assert cog.est_deconnecte is True

    await cog.on_disconnect()

    msgs = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert msgs.count("🛑 Déconnexion de la gateway Discord") == 1


@pytest.mark.asyncio
async def test_on_connect_resets_flag_and_logs(monkeypatch, caplog):
    monkeypatch.setattr(logs_mod, "LOG_ENABLED", True)
    monkeypatch.setattr(logs_mod, "get_log_admin_id", lambda: 123)

    cog = logs_mod.Logs(FakeBot())
    cog.est_deconnecte = True

    caplog.set_level(logging.INFO, logger=logs_mod.__name__)

    await cog.on_connect()
    assert cog.est_deconnecte is False

    msgs = [r.message for r in caplog.records if r.levelno == logging.INFO]
    assert "🔌 Connexion à la gateway Discord établie" in msgs


@pytest.mark.asyncio
async def test_on_resumed_resets_flag_and_logs(monkeypatch, caplog):
    monkeypatch.setattr(logs_mod, "LOG_ENABLED", True)
    monkeypatch.setattr(logs_mod, "get_log_admin_id", lambda: 123)

    cog = logs_mod.Logs(FakeBot())
    cog.est_deconnecte = True

    caplog.set_level(logging.INFO, logger=logs_mod.__name__)

    await cog.on_resumed()
    assert cog.est_deconnecte is False

    msgs = [r.message for r in caplog.records if r.levelno == logging.INFO]
    assert "🔁 Session Discord reprise avec succès" in msgs


@pytest.mark.asyncio
async def test_logs_command_feature_disabled(monkeypatch):
    monkeypatch.setattr(logs_mod, "LOG_ENABLED", False)
    # pas appelé si disabled, mais on peut le patcher quand même
    monkeypatch.setattr(logs_mod, "get_log_admin_id", lambda: 123)

    cog = logs_mod.Logs(FakeBot())
    ctx = FakeCtx(user=FakeUser(123))

    from eldoria.exceptions.general import FeatureNotConfigured

    with pytest.raises(FeatureNotConfigured):
        await cog.logs_command(ctx)


@pytest.mark.asyncio
async def test_logs_command_non_admin_denied(monkeypatch):
    monkeypatch.setattr(logs_mod, "LOG_ENABLED", True)
    monkeypatch.setattr(logs_mod, "get_log_admin_id", lambda: 999)

    cog = logs_mod.Logs(FakeBot())
    ctx = FakeCtx(user=FakeUser(123))

    from eldoria.exceptions.general import NotAllowed

    with pytest.raises(NotAllowed):
        await cog.logs_command(ctx)


@pytest.mark.asyncio
async def test_logs_command_admin_sends_codeblock(monkeypatch, caplog):
    monkeypatch.setattr(logs_mod, "LOG_ENABLED", True)
    monkeypatch.setattr(logs_mod, "get_log_admin_id", lambda: 123)

    monkeypatch.setattr(logs_mod, "tail_lines", lambda: "ligne1\nligne2\n")

    cog = logs_mod.Logs(FakeBot())

    user = FakeUser(123)
    # logs.py lit `.name` pour la trace.
    user.name = "Faucon"  # type: ignore[attr-defined]
    ctx = FakeCtx(user=user)

    caplog.set_level(logging.INFO, logger=logs_mod.__name__)

    await cog.logs_command(ctx)

    assert len(ctx.followup.sent) == 1
    payload = ctx.followup.sent[0]
    assert str(payload["content"]).startswith("```text\n")
    assert "ligne1" in str(payload["content"])
    assert payload.get("ephemeral") is True

    msgs = [r.message for r in caplog.records if r.levelno == logging.INFO]
    assert any("Utilisation de la commande logs par Faucon" in m for m in msgs)


@pytest.mark.asyncio
async def test_logs_command_admin_sends_file_when_too_long(monkeypatch):
    monkeypatch.setattr(logs_mod, "LOG_ENABLED", True)
    monkeypatch.setattr(logs_mod, "get_log_admin_id", lambda: 123)

    monkeypatch.setattr(logs_mod, "tail_lines", lambda: "a" * 2000)

    # discord.File(...) -> objet minimal inspecté par le test
    monkeypatch.setattr(
        logs_mod.discord,
        "File",
        lambda fp=None, filename=None: SimpleNamespace(fp=fp, filename=filename),
    )

    cog = logs_mod.Logs(FakeBot())
    user = FakeUser(123)
    user.name = "Faucon"  # type: ignore[attr-defined]
    ctx = FakeCtx(user=user)

    await cog.logs_command(ctx)

    assert len(ctx.followup.sent) == 1
    payload = ctx.followup.sent[0]

    assert "file" in payload
    assert payload["file"].filename == "bot.log.tail.txt"
    assert payload.get("ephemeral") is True
