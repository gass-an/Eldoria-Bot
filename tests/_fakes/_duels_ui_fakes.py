from __future__ import annotations

# Fakes partagés pour les tests UI duels.

class FakeDuelError(Exception):
    pass


class FakeServices:
    def __init__(self, duel):
        self.duel = duel


class FakeBot:
    def __init__(self, duel):
        self.services = FakeServices(duel)
