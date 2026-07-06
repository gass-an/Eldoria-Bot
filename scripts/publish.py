"""Publication en une commande.

Publication complète (bump + changelog + commit + tag+push):
  python scripts/publish.py --to 0.6.1

Test local (bump + changelog + commit), WITHOUT tag/push:
  python scripts/publish.py --to 0.6.1 --no-release
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Final

SCRIPTS_DIR: Final[Path] = Path("scripts")
BUMP: Final[Path] = SCRIPTS_DIR / "bump_version.py"
ROLL: Final[Path] = SCRIPTS_DIR / "roll_changelog.py"
COMMIT: Final[Path] = SCRIPTS_DIR / "commit_release.py"
RELEASE: Final[Path] = SCRIPTS_DIR / "release.py"

VERSION_FILE: Final[Path] = Path("src/eldoria/version.py")
CHANGELOG: Final[Path] = Path("CHANGELOG.md")
VERSION_PATTERN: Final[re.Pattern[str]] = re.compile(
    r'VERSION\s*:\s*Final\[str]\s*=\s*"(?P<v>\d+\.\d+\.\d+)"'
)
VERSION_RE: Final[re.Pattern[str]] = re.compile(r"\d+\.\d+\.\d+")


class PublishError(RuntimeError):
    """Erreur contrôlée pendant la publication."""


def run(cmd: list[str]) -> None:
    """Exécute une commande, en levant en cas d'erreur."""
    subprocess.run(cmd, check=True)


def output(cmd: list[str], *, check: bool = True) -> str:
    """Exécute une commande et retourne stdout nettoyé."""
    res = subprocess.run(cmd, capture_output=True, text=True, check=check)
    return res.stdout.strip()


def ensure_repo_root() -> None:
    """Vérifie que le script est lancé depuis la racine du dépôt Git."""
    root = output(["git", "rev-parse", "--show-toplevel"])
    cwd = Path.cwd().resolve()
    if Path(root).resolve() != cwd:
        raise PublishError(f"Lance ce script depuis la racine du dépôt: {root}")


def ensure_on_main() -> None:
    """Vérifie que la publication est lancée depuis main."""
    branch = output(["git", "branch", "--show-current"])
    if branch != "main":
        raise PublishError(f"Publication refusée: branche courante '{branch}', attendu 'main'.")


def ensure_repo_clean() -> None:
    """Vérifie que le repo git est clean (pas de changement non commité ou non suivi)."""
    status = output(["git", "status", "--porcelain"])
    if status:
        raise PublishError("Repo non clean. Commit/stash avant publish.")


def fetch_origin() -> None:
    """Récupère origin/main et les tags avant les vérifications."""
    run(["git", "fetch", "origin", "main", "--tags"])


def is_ancestor(ancestor: str, descendant: str) -> bool:
    """Indique si ancestor est dans l'historique de descendant."""
    res = subprocess.run(["git", "merge-base", "--is-ancestor", ancestor, descendant], check=False)
    return res.returncode == 0


def ensure_publish_base_state(target: str) -> None:
    """Vérifie que l'état Git permet une publication ou une reprise idempotente.

    État normal: HEAD == origin/main.
    Reprise autorisée: HEAD est déjà release(vX.Y.Z) et origin/main est son ancêtre.
    Ce deuxième cas permet de relancer après un --no-release ou après une coupure avant le tag.
    """
    local = output(["git", "rev-parse", "HEAD"])
    remote = output(["git", "rev-parse", "origin/main"])

    if local == remote:
        return

    if is_release_commit_for(target) and is_ancestor("origin/main", "HEAD"):
        print(f"Reprise détectée: commit {release_commit_message(target)} déjà présent localement.")
        return

    raise PublishError(
        "main local n'est pas aligné avec origin/main. Lance: git pull --rebase origin main"
    )


def read_version() -> str:
    """Lit la version actuelle dans src/eldoria/version.py."""
    content = VERSION_FILE.read_text(encoding="utf-8")
    m = VERSION_PATTERN.search(content)
    if not m:
        raise PublishError("VERSION introuvable dans src/eldoria/version.py")
    return m.group("v")


def parse_version(version: str) -> tuple[int, int, int]:
    """Convertit X.Y.Z en tuple comparable."""
    if not VERSION_RE.fullmatch(version):
        raise PublishError("Version invalide. Format attendu: X.Y.Z")
    return tuple(int(part) for part in version.split("."))  # type: ignore[return-value]


def ensure_target_version_is_valid(current: str, target: str) -> None:
    """Vérifie que la version cible est valide et supérieure ou égale à la version actuelle."""
    current_tuple = parse_version(current)
    target_tuple = parse_version(target)
    if target_tuple < current_tuple:
        raise PublishError(f"Version cible inférieure à la version actuelle: {target} < {current}")


def release_commit_message(version: str) -> str:
    """Retourne le message attendu pour le commit de release."""
    return f"release(v{version})"


def head_commit_message() -> str:
    """Retourne le sujet du commit courant."""
    return output(["git", "log", "-1", "--pretty=%s"])


def rev_parse(ref: str) -> str | None:
    """Retourne le hash d'une référence Git, ou None si elle n'existe pas."""
    res = subprocess.run(["git", "rev-parse", "--verify", ref], capture_output=True, text=True)
    if res.returncode != 0:
        return None
    return res.stdout.strip()


def tag_commit(ref: str) -> str | None:
    """Retourne le commit pointé par un tag local, en supportant aussi les tags annotés."""
    return rev_parse(f"{ref}^{{}}") or rev_parse(ref)


def remote_tag_commit(tag: str) -> str | None:
    """Retourne le commit du tag distant origin/tag, ou None s'il n'existe pas."""
    res = subprocess.run(["git", "ls-remote", "--tags", "origin", tag], capture_output=True, text=True, check=True)
    lines = [line for line in res.stdout.splitlines() if line.strip()]
    if not lines:
        return None
    peeled = [line for line in lines if line.endswith(f"refs/tags/{tag}^{{}}")]
    selected = peeled[0] if peeled else lines[0]
    return selected.split()[0]


def ensure_tag_available(tag: str, *, allow_current_head: bool = False) -> None:
    """Vérifie qu'un tag local/distant n'existe pas déjà, sauf s'il pointe vers HEAD et est autorisé."""
    head = output(["git", "rev-parse", "HEAD"])
    local = tag_commit(f"refs/tags/{tag}")
    remote = remote_tag_commit(tag)

    for label, commit in (("local", local), ("distant", remote)):
        if commit is None:
            continue
        if allow_current_head and commit == head:
            continue
        raise PublishError(f"Tag {label} {tag} existe déjà. Abandon.")


def changelog_has_release(version: str) -> bool:
    """Indique si CHANGELOG.md contient déjà la section de cette version."""
    text = CHANGELOG.read_text(encoding="utf-8")
    return bool(re.search(rf"^## \[{re.escape(version)}\]", text, flags=re.MULTILINE))


def changelog_unreleased_has_entries() -> bool:
    """Vérifie qu'Unreleased contient au moins une entrée '- ...'."""
    text = CHANGELOG.read_text(encoding="utf-8")
    m = re.search(r"^## \[Unreleased\]\s*$", text, flags=re.MULTILINE)
    if not m:
        raise PublishError("CHANGELOG.md: section '## [Unreleased]' introuvable.")
    header_end = text.find("\n", m.end())
    header_end = len(text) if header_end == -1 else header_end + 1
    m2 = re.search(r"^## \[.+?\]", text[header_end:], flags=re.MULTILINE)
    body_end = header_end + m2.start() if m2 else len(text)
    body = text[header_end:body_end]
    return any(line.strip().startswith("-") for line in body.splitlines())


def is_release_commit_for(version: str) -> bool:
    """Indique si HEAD est déjà le commit release(vX.Y.Z) pour la version cible."""
    return read_version() == version and head_commit_message() == release_commit_message(version)


def rollback(start_ref: str, local_tag_to_delete: str | None = None) -> None:
    """Revient à l'état initial en cas d'échec local avant effet distant."""
    print("Rollback local en cours...")
    if local_tag_to_delete and tag_commit(f"refs/tags/{local_tag_to_delete}") is not None:
        subprocess.run(["git", "tag", "-d", local_tag_to_delete], check=False)
    subprocess.run(["git", "reset", "--hard", start_ref], check=False)
    print("Rollback local terminé.")


def handle_release_failure(start_ref: str, tag: str, local_tag_before: str | None) -> str:
    """Rollback uniquement si aucun effet distant n'est détecté, sinon conserve l'état pour relance.

    Retourne:
    - "published" si la release est finalement visible côté distant;
    - "kept" si un état partiel réutilisable est conservé;
    - "rolled_back" si le rollback local a été effectué.
    """
    head = output(["git", "rev-parse", "HEAD"])

    try:
        fetch_origin()
        remote_main = output(["git", "rev-parse", "origin/main"])
        remote_tag = remote_tag_commit(tag)
    except Exception:
        print("Impossible de vérifier l'état distant après l'échec. État local conservé pour relance.")
        return "kept"

    if remote_tag == head:
        print(f"Release {tag} déjà publiée côté distant.")
        return "published"

    if remote_main == head or tag_commit(f"refs/tags/{tag}") == head:
        print(
            "Échec pendant la publication distante, mais un état partiel réutilisable a été détecté. "
            "Aucun rollback effectué: relance la commande pour reprendre."
        )
        return "kept"

    tag_to_delete = tag if local_tag_before is None else None
    rollback(start_ref, tag_to_delete)
    return "rolled_back"


def parse_args(argv: list[str]) -> tuple[str, bool]:
    """Parse les arguments CLI."""
    if "--to" not in argv:
        raise PublishError(__doc__.strip())  # type: ignore[arg-type]

    no_release = "--no-release" in argv
    args = [a for a in argv if a != "--no-release"]

    if len(args) != 2 or args[0] != "--to":
        raise PublishError(__doc__.strip())  # type: ignore[arg-type]

    return args[1], no_release


def prepare_release_commit(target: str) -> bool:
    """Prépare le commit de release si HEAD ne l'est pas déjà.

    Retourne True si un commit a été créé par cette exécution.
    """
    current = read_version()

    if is_release_commit_for(target):
        print(f"Commit {release_commit_message(target)} déjà prêt.")
        return False

    ensure_target_version_is_valid(current, target)

    if current == target and changelog_has_release(target):
        # État partiel possible, mais sans commit release en HEAD: on refuse pour éviter de deviner.
        raise PublishError(
            f"La version {target} semble déjà appliquée mais HEAD n'est pas {release_commit_message(target)}. "
            "Vérifie l'état Git avant de relancer."
        )

    if not changelog_unreleased_has_entries():
        raise PublishError("Unreleased est vide (aucune entrée '- ...'). Abandon.")

    run(["python", str(BUMP), "--to", target])

    after = read_version()
    if after != target:
        raise PublishError(f"La version lue après bump est {after}, attendu {target}.")

    run(["python", str(ROLL), target])
    run(["python", str(COMMIT), target])
    return True


def main() -> None:
    """Publie une nouvelle version avec preflight checks, rollback et idempotence."""
    try:
        target, no_release = parse_args(sys.argv[1:])
        parse_version(target)

        ensure_repo_root()
        ensure_on_main()
        ensure_repo_clean()
        fetch_origin()
        ensure_publish_base_state(target)

        tag = f"v{target}"
        start_ref = output(["git", "rev-parse", "HEAD"])
        local_tag_before = tag_commit(f"refs/tags/{tag}")

        ensure_tag_available(tag, allow_current_head=is_release_commit_for(target))

        created_commit = False
        try:
            created_commit = prepare_release_commit(target)

            if no_release:
                print(f"Local publish OK (no tag/push): v{target}")
                return

            try:
                run(["python", str(RELEASE)])
            except subprocess.CalledProcessError as exc:
                recovery = "rolled_back"
                if created_commit or is_release_commit_for(target):
                    recovery = handle_release_failure(start_ref, tag, local_tag_before)
                if recovery == "published":
                    print(f"Published v{target}")
                    return
                if recovery == "kept":
                    raise PublishError(
                        "Publication partielle conservée. Relance la même commande pour reprendre."
                    ) from exc
                raise PublishError("Publication échouée. Rollback local effectué.") from exc

            print(f"Published v{target}")
        except Exception:
            # En --no-release, le comportement historique laisse le commit local créé.
            # En publication complète, rollback seulement avant effet distant.
            if not no_release and created_commit:
                current_head = output(["git", "rev-parse", "HEAD"], check=False)
                remote_main = rev_parse("origin/main")
                if current_head and remote_main != current_head:
                    rollback(start_ref)
            raise

    except PublishError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
