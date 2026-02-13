from __future__ import annotations

from datetime import datetime

from eldoria.app import banner as mod


class FakeDiscord:
    __version__ = "X.Y.Z"


def test_startup_banner_with_explicit_started_at_includes_expected_fields(monkeypatch):
    monkeypatch.setattr(mod, "VERSION", "9.9.9", raising=True)
    monkeypatch.setattr(mod, "discord", FakeDiscord, raising=True)

    started_at = datetime(2024, 1, 2, 3, 4, 5)
    s = mod.startup_banner(started_at)

    assert "Eldoria Bot v9.9.9" in s
    assert "py-cord  : X.Y.Z" in s
    assert "Started  : 03:04:05 02/01/2024" in s
    assert "Python   :" in s

    # contient le logo (ligne distinctive)
    assert "███████╗██╗" in s

    # finit par un newline
    assert s.endswith("\n")


def test_startup_banner_when_started_at_none_uses_datetime_now(monkeypatch):
    monkeypatch.setattr(mod, "VERSION", "1.2.3", raising=True)
    monkeypatch.setattr(mod, "discord", FakeDiscord, raising=True)

    fixed_now = datetime(2030, 12, 31, 23, 59, 58)

    # banner.py a fait `from datetime import datetime` -> on remplace mod.datetime
    class FakeDateTime:
        @staticmethod
        def now():
            return fixed_now

    monkeypatch.setattr(mod, "datetime", FakeDateTime, raising=True)

    s = mod.startup_banner(None)
    assert "Started  : 23:59:58 31/12/2030" in s


def test_startup_banner_box_has_valid_structure(monkeypatch):
    monkeypatch.setattr(mod, "VERSION", "X", raising=True)
    monkeypatch.setattr(mod, "discord", FakeDiscord, raising=True)

    started_at = datetime(2024, 6, 1, 0, 0, 0)
    s = mod.startup_banner(started_at)

    all_lines = s.splitlines()

    # Trouve la vraie ligne "top" de la box (pas le logo)
    top_idx = None
    for i, line in enumerate(all_lines):
        if line.startswith("╔") and line.endswith("╗"):
            top_idx = i
            break

    assert top_idx is not None, "Top de la box non trouvé (ligne '╔...╗')"

    box_lines = all_lines[top_idx:]
    # Enlève les lignes vides finales éventuelles
    while box_lines and box_lines[-1] == "":
        box_lines.pop()

    top = box_lines[0]
    bottom = box_lines[-1]

    assert top.startswith("╔") and top.endswith("╗")
    assert bottom.startswith("╚") and bottom.endswith("╝")

    # séparateur présent
    seps = [l for l in box_lines if l.startswith("╟") and l.endswith("╢")]
    assert len(seps) == 1
    sep = seps[0]

    # top/sep/bottom sont alignés (même longueur) dans la box
    assert len(sep) == len(top)
    assert len(bottom) == len(top)

    # contenu : lignes encadrées par ║ ... ║ (hors sep)
    content_lines = [
        l for l in box_lines[1:-1]
        if not (l.startswith("╟") and l.endswith("╢"))
    ]
    assert content_lines, "il doit y avoir des lignes de contenu dans la box"

    for l in content_lines:
        assert l.startswith("║ ")
        assert l.endswith("║")
        assert len(l) == len(top)  # ici on peut être strict, c’est la vraie box





def test_startup_banner_includes_all_label_lines(monkeypatch):
    monkeypatch.setattr(mod, "VERSION", "3.3.3", raising=True)
    monkeypatch.setattr(mod, "discord", FakeDiscord, raising=True)

    started_at = datetime(2025, 2, 3, 4, 5, 6)
    s = mod.startup_banner(started_at)

    assert "Eldoria Bot v3.3.3" in s
    assert "Python   :" in s
    assert "py-cord  : X.Y.Z" in s
    assert "Started  : 04:05:06 03/02/2025" in s
