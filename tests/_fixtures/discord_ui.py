import discord  # type: ignore
import pytest


@pytest.fixture(autouse=True)
def patch_discord_ui_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Patch global pour compenser les limites du stub discord installé par tests/_bootstrap/discord_stub.py
    """

    # View.clear_items / remove_item manquants
    View = discord.ui.View

    if not hasattr(View, "clear_items"):
        def clear_items(self) -> None:
            self.children.clear()
        monkeypatch.setattr(View, "clear_items", clear_items, raising=False)

    if not hasattr(View, "remove_item"):
        def remove_item(self, item) -> None:
            if item in self.children:
                self.children.remove(item)
        monkeypatch.setattr(View, "remove_item", remove_item, raising=False)

    # Button.__init__ du stub n'accepte pas emoji=
    Button = discord.ui.Button
    orig_init = Button.__init__

    def patched_init(self, *args, **kwargs):
        emoji = kwargs.pop("emoji", None)
        orig_init(self, *args, **kwargs)
        setattr(self, "emoji", emoji)

    monkeypatch.setattr(Button, "__init__", patched_init, raising=True)