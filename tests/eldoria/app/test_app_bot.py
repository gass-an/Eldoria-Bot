
from eldoria.app.bot import EldoriaBot


class FakeIntents:
    pass


def test_eldoria_bot_init_calls_super_with_expected_args(monkeypatch):
    calls = {}

    def fake_bot_init(self, *, command_prefix, intents, **options):
        # capture des valeurs passées à super().__init__
        calls["command_prefix"] = command_prefix
        calls["intents"] = intents
        calls["options"] = dict(options)

    # Patch la classe mère (commands.Bot.__init__)
    from discord.ext import commands
    monkeypatch.setattr(commands.Bot, "__init__", fake_bot_init, raising=True)

    # Fixe perf_counter pour contrôler _started_at initial
    import eldoria.app.bot as bot_mod
    monkeypatch.setattr(bot_mod.time, "perf_counter", lambda: 123.456, raising=True)

    intents = FakeIntents()
    bot = EldoriaBot(intents=intents, command_prefix="!")

    assert calls["command_prefix"] == "!"
    assert calls["intents"] is intents
    assert calls["options"] == {}

    assert bot.is_booted() is False
    assert bot.get_started_at() == 123.456
    assert bot.services is None


def test_eldoria_bot_init_passes_options(monkeypatch):
    calls = {}

    def fake_bot_init(self, *, command_prefix, intents, **options):
        calls["options"] = dict(options)

    from discord.ext import commands
    monkeypatch.setattr(commands.Bot, "__init__", fake_bot_init, raising=True)

    import eldoria.app.bot as bot_mod
    monkeypatch.setattr(bot_mod.time, "perf_counter", lambda: 1.0, raising=True)

    EldoriaBot(intents=FakeIntents(), command_prefix="!", help_command=None, description="Eldoria")

    assert calls["options"] == {"help_command": None, "description": "Eldoria"}


def test_started_at_set_and_get(monkeypatch):
    # Patch super init pour éviter la vraie init discord
    from discord.ext import commands
    monkeypatch.setattr(commands.Bot, "__init__", lambda self, **kwargs: None, raising=True)

    import eldoria.app.bot as bot_mod
    monkeypatch.setattr(bot_mod.time, "perf_counter", lambda: 10.0, raising=True)

    bot = EldoriaBot(intents=FakeIntents())
    assert bot.get_started_at() == 10.0

    bot.set_started_at(99.9)
    assert bot.get_started_at() == 99.9


def test_booted_flag(monkeypatch):
    from discord.ext import commands
    monkeypatch.setattr(commands.Bot, "__init__", lambda self, **kwargs: None, raising=True)

    import eldoria.app.bot as bot_mod
    monkeypatch.setattr(bot_mod.time, "perf_counter", lambda: 0.0, raising=True)

    bot = EldoriaBot(intents=FakeIntents())
    assert bot.is_booted() is False

    bot.set_booted(True)
    assert bot.is_booted() is True

    bot.set_booted(False)
    assert bot.is_booted() is False
