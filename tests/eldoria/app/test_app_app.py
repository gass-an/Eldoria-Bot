import pytest

from eldoria.app import app as mod


class FakeIntents:
    def __init__(self):
        self.message_content = False
        self.guilds = False
        self.members = False


class FakeBot:
    def __init__(self, *, intents):
        self.intents = intents
        self.started_at = None
        self.discord_started_at = None
        self.ran_with = None

    def set_started_at(self, started_at: float):
        self.started_at = started_at

    def run(self, token: str):
        self.ran_with = token

    def set_discord_started_at(self, ts: float):
        self.discord_started_at = ts


def test_create_bot_sets_required_intents(monkeypatch):
    intents_obj = FakeIntents()

    class FakeDiscordIntents:
        @staticmethod
        def default():
            return intents_obj

    # patch discord.Intents.default()
    monkeypatch.setattr(mod.discord, "Intents", FakeDiscordIntents, raising=True)

    created = {}

    def fake_eldoria_bot(*, intents):
        created["intents"] = intents
        return FakeBot(intents=intents)

    monkeypatch.setattr(mod, "EldoriaBot", fake_eldoria_bot, raising=True)

    bot = mod.create_bot()

    assert bot.intents is intents_obj
    assert intents_obj.message_content is True
    assert intents_obj.guilds is True
    assert intents_obj.members is True
    assert created["intents"] is intents_obj


def test_main_raises_when_token_missing(monkeypatch):
    monkeypatch.setattr(mod, "TOKEN", "", raising=False)
    with pytest.raises(RuntimeError, match="discord_token manquant"):
        mod.main(123.0)


def test_main_happy_path_calls_startup_and_runs(monkeypatch, capsys):
    # token OK
    monkeypatch.setattr(mod, "TOKEN", "TOKEN123", raising=False)

    # banner
    monkeypatch.setattr(mod, "startup_banner", lambda: "BANNER!", raising=True)

    # create_bot -> FakeBot
    bot = FakeBot(intents=FakeIntents())
    monkeypatch.setattr(mod, "create_bot", lambda: bot, raising=True)

    # startup(bot)
    startup_calls = []

    def fake_startup(b):
        startup_calls.append(b)

    monkeypatch.setattr(mod, "startup", fake_startup, raising=True)

    monkeypatch.setattr(mod.time, "perf_counter", lambda: 1234.0, raising=True)

    # logger
    info_calls = []

    class FakeLog:
        def info(self, msg):
            info_calls.append(msg)

    monkeypatch.setattr(mod, "log", FakeLog(), raising=True)

    mod.main(999.5)

    # banner imprimée
    out = capsys.readouterr().out
    assert "BANNER!" in out

    # startup appelé
    assert startup_calls == [bot]

    # started_at set
    assert bot.started_at == 999.5

    # discord_started_at set
    assert bot.discord_started_at == 1234.0

    # log info
    assert info_calls == ["⏳ Connexion à Discord…"]

    # bot.run avec TOKEN
    assert bot.ran_with == "TOKEN123"
