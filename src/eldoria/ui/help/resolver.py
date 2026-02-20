"""Résolution des commandes du help (flatten SlashCommandGroup + permissions + catégories).

Ce module ne gère PAS l'UI. Il produit juste:
- cmd_map: {"qualified name": cmd_obj}
- categories: catégories normalisées (groupes expand)
- visible_by_cat: catégories filtrées par permissions/checks
"""

from __future__ import annotations

import discord


def build_command_index(bot: object) -> tuple[list[tuple[str, object]], dict[str, object]]:
    """Construit un index de commandes à plat à partir de bot.application_commands.

    Retourne:
    - pairs: [(qualified_name, cmd_obj), ...] incluant groupes + sous-commandes
    - cmd_map: {qualified_name: cmd_obj}
    """
    cmds = getattr(bot, "application_commands", None) or []

    def _children(cmd: object) -> list[object]:
        # Compat multi-versions (discord.py / pycord): on tente plusieurs attributs.
        for attr in ("subcommands", "commands", "children"):
            val = getattr(cmd, attr, None)
            if isinstance(val, list) and val:
                return val
        # Certains frameworks exposent les subcommands dans options.
        val = getattr(cmd, "options", None)
        if isinstance(val, list) and val:
            return val
        return []

    def _is_command_obj(x: object) -> bool:
        # Heuristique: une commande a typiquement un name + (callback|can_run)
        return hasattr(x, "name") and (hasattr(x, "callback") or hasattr(x, "can_run"))

    def _walk(cmd: object, prefix: str = "") -> list[tuple[str, object]]:
        name = getattr(cmd, "name", None)
        if not name:
            return []
        qn = f"{prefix}{name}".strip()
        out: list[tuple[str, object]] = [(qn, cmd)]
        kids = [k for k in _children(cmd) if _is_command_obj(k)]
        for k in kids:
            out.extend(_walk(k, prefix=f"{qn} "))
        return out

    pairs: list[tuple[str, object]] = []
    for c in cmds:
        pairs.extend(_walk(c))

    cmd_map: dict[str, object] = {qualified: obj for qualified, obj in pairs}
    return pairs, cmd_map


def normalize_categories(
    *,
    categories: dict[str, list[str]],
    cmd_map: dict[str, object],
    pairs: list[tuple[str, object]],
) -> dict[str, list[str]]:
    """Expand les groupes présents dans les catégories JSON.

    Exemple:
    - JSON: ["xp"]
    - -> ["xp profile", "xp roles", "xp leaderboard", ...] (les feuilles seulement)
    """

    def _children(cmd: object) -> list[object]:
        for attr in ("subcommands", "commands", "children"):
            val = getattr(cmd, attr, None)
            if isinstance(val, list) and val:
                return val
        val = getattr(cmd, "options", None)
        if isinstance(val, list) and val:
            return val
        return []

    def _is_command_obj(x: object) -> bool:
        return hasattr(x, "name") and (hasattr(x, "callback") or hasattr(x, "can_run"))

    def _is_group(cmd: object) -> bool:
        return any(_is_command_obj(k) for k in _children(cmd))

    def _expand_entry(entry: str) -> list[str]:
        obj = cmd_map.get(entry)
        if obj is None:
            return [entry]
        if _is_group(obj):
            out: list[str] = []
            prefix = entry + " "
            for qn, o in pairs:
                if qn.startswith(prefix) and not _is_group(o):
                    out.append(qn)
            return out
        return [entry]

    normalized: dict[str, list[str]] = {}
    for cat, lst in categories.items():
        expanded: list[str] = []
        for entry in lst:
            expanded.extend(_expand_entry(entry))

        # dédoublonnage en gardant l'ordre
        seen: set[str] = set()
        uniq: list[str] = []
        for x in expanded:
            if x not in seen:
                seen.add(x)
                uniq.append(x)

        normalized[cat] = uniq

    return normalized


async def resolve_visible_by_category(
    *,
    ctx: discord.ApplicationContext,
    cmd_map: dict[str, object],
    pairs: list[tuple[str, object]],
    categories: dict[str, list[str]],
    excluded_cmds: set[str] | None = None,
) -> dict[str, list[str]]:
    """Filtre les commandes par permissions/checks et remplit 'Autres' pour les oubliées.

    Comportement conservé:
    - on n'affiche pas excluded_cmds
    - on n'ajoute pas les groupes dans "Autres"
    - on n'ajoute pas /help dans "Autres" (mais il peut être affiché si déclaré dans une catégorie)
    """
    excluded_cmds = excluded_cmds or set()

    def _children(cmd: object) -> list[object]:
        for attr in ("subcommands", "commands", "children"):
            val = getattr(cmd, attr, None)
            if isinstance(val, list) and val:
                return val
        val = getattr(cmd, "options", None)
        if isinstance(val, list) and val:
            return val
        return []

    def _is_command_obj(x: object) -> bool:
        return hasattr(x, "name") and (hasattr(x, "callback") or hasattr(x, "can_run"))

    def _is_group(cmd: object) -> bool:
        return any(_is_command_obj(k) for k in _children(cmd))

    def _parent(cmd: object) -> object | None:
        return getattr(cmd, "parent", None)

    def _effective_default_perms(cmd: object) -> object | None:
        """Calcule les permissions requises en remontant les parents (groupe -> sous-commandes)."""
        cur = cmd
        while cur is not None:
            dp = getattr(cur, "default_member_permissions", None)
            if dp is None:
                dp = getattr(cur, "default_permissions", None)
            if dp is not None:
                return dp
            cur = _parent(cur)
        return None

    async def _effective_can_run(cmd: object, ctx_: discord.ApplicationContext) -> bool:
        """Applique can_run en remontant les parents (groupe -> sous-commandes)."""
        cur = cmd
        while cur is not None:
            fn = getattr(cur, "can_run", None)
            if fn is not None:
                try:
                    res = fn(ctx_)
                    if hasattr(res, "__await__"):
                        res = await res
                    if not bool(res):
                        return False
                except Exception:
                    return False
            cur = _parent(cur)
        return True

    # Permissions user
    member_perms = getattr(getattr(ctx, "user", None), "guild_permissions", None)
    member_perm_value = getattr(member_perms, "value", 0)

    async def is_command_visible(cmd_name: str) -> bool:
        cmd = cmd_map.get(cmd_name)
        if cmd is None:
            return False

        dp = _effective_default_perms(cmd)
        if dp is not None:
            dp_value = getattr(dp, "value", 0)
            if (member_perm_value & dp_value) != dp_value:
                return False

        return await _effective_can_run(cmd, ctx)

    # 1) Normalisation (expand groupes)
    categories = normalize_categories(categories=categories, cmd_map=cmd_map, pairs=pairs)

    # 2) Ajoute les commandes non déclarées dans "Autres"
    declared = {c for lst in categories.values() for c in lst}
    for cmd_name, obj in list(cmd_map.items()):
        if cmd_name == "help":
            continue
        if cmd_name in excluded_cmds:
            continue
        if _is_group(obj):
            continue
        if cmd_name not in declared:
            categories.setdefault("Autres", []).append(cmd_name)

    # 3) Filtrage par visibilité
    visible_by_cat: dict[str, list[str]] = {}
    for cat, cmd_names in categories.items():
        visible: list[str] = []
        for name in cmd_names:
            if name in excluded_cmds:
                continue
            if await is_command_visible(name):
                visible.append(name)
        if visible:
            visible_by_cat[cat] = visible

    return visible_by_cat