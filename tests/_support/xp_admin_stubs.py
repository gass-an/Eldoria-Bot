from __future__ import annotations

"""Stubs UI partagés pour les tests XP admin.

Les tests sous `tests/eldoria/**` ne doivent contenir aucune déclaration `class`.
Ces stubs sont donc centralisés ici.
"""

from typing import Any


class BasePanelViewStub:
    def __init__(self, *, author_id: int):
        self.author_id = author_id
        self.children: list[object] = []

    def add_item(self, item):
        self.children.append(item)


class RoutedButtonStub:
    def __init__(
        self,
        *,
        label: str,
        style: Any,
        custom_id: str,
        disabled: bool = False,
        emoji: str | None = None,
        row: int = 0,
    ):
        self.label = label
        self.style = style
        self.custom_id = custom_id
        self.disabled = disabled
        self.emoji = emoji
        self.row = row
