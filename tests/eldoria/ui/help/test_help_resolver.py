from __future__ import annotations

from types import SimpleNamespace

import pytest

from eldoria.ui.help import resolver as R
from tests._fakes import FakeCtx, FakeUser


def make_perms(value: int):
    return SimpleNamespace(value=value)


def make_leaf(name: str, *, parent=None, dp=None, can_run=True):
    async def _can_run(ctx):
        if isinstance(can_run, BaseException):
            raise can_run
        return bool(can_run)

    return SimpleNamespace(
        name=name,
        parent=parent,
        default_member_permissions=dp,
        can_run=_can_run,
    )


def make_group(
    name: str,
    *,
    children_attr: str = "commands",
    children=None,
    parent=None,
    dp=None,
    can_run=True,
):
    async def _can_run(ctx):
        if isinstance(can_run, BaseException):
            raise can_run
        return bool(can_run)

    obj = SimpleNamespace(
        name=name,
        parent=parent,
        default_member_permissions=dp,
        can_run=_can_run,
    )
    setattr(obj, children_attr, list(children or []))
    return obj


# ----------------------------
# build_command_index
# ----------------------------
@pytest.mark.parametrize("attr", ["commands", "subcommands", "children", "options"])
def test_build_command_index_flattens_groups_and_builds_qualified_names(attr):
    # /xp profile, /xp leaderboard
    # NOTE: on teste que build_command_index lit bien les enfants via "attr"
    group = make_group("xp", children_attr=attr, children=[])

    profile = make_leaf("profile", parent=group)
    leader = make_leaf("leaderboard", parent=group)

    # met les enfants sur l'attribut choisi
    setattr(group, attr, [profile, leader])

    bot = SimpleNamespace(application_commands=[group])

    pairs, cmd_map = R.build_command_index(bot)

    # pairs inclut le groupe + sous-commandes
    assert ("xp", group) in pairs
    assert ("xp profile", profile) in pairs
    assert ("xp leaderboard", leader) in pairs

    # map par qualified name
    assert cmd_map["xp"] is group
    assert cmd_map["xp profile"] is profile
    assert cmd_map["xp leaderboard"] is leader


def test_build_command_index_ignores_objects_without_name_or_callable():
    bot = SimpleNamespace(application_commands=[object()])

    pairs, cmd_map = R.build_command_index(bot)
    assert pairs == []
    assert cmd_map == {}


# ----------------------------
# normalize_categories
# ----------------------------
def test_normalize_categories_expands_group_to_leaf_commands_only():
    # /xp is group; leaves = profile/roles
    g = make_group("xp", children_attr="commands", children=[])
    profile = make_leaf("profile", parent=g)
    roles = make_leaf("roles", parent=g)
    g.commands = [profile, roles]

    pairs = [("xp", g), ("xp profile", profile), ("xp roles", roles)]
    cmd_map = {k: v for k, v in pairs}

    categories = {"XP": ["xp"]}
    norm = R.normalize_categories(categories=categories, cmd_map=cmd_map, pairs=pairs)

    assert norm == {"XP": ["xp profile", "xp roles"]}


def test_normalize_categories_keeps_unknown_entries_as_is_and_deduplicates():
    # group exists with one leaf; unknown entry kept
    g = make_group("xp", children_attr="commands", children=[])
    profile = make_leaf("profile", parent=g)
    g.commands = [profile]

    pairs = [("xp", g), ("xp profile", profile)]
    cmd_map = {k: v for k, v in pairs}

    categories = {"Cat": ["xp", "unknown", "xp", "unknown"]}
    norm = R.normalize_categories(categories=categories, cmd_map=cmd_map, pairs=pairs)

    # xp expands, unknown kept, duplicates removed preserving order
    assert norm == {"Cat": ["xp profile", "unknown"]}


def test_normalize_categories_does_not_expand_leaf():
    leaf = make_leaf("ping")
    pairs = [("ping", leaf)]
    cmd_map = {"ping": leaf}

    categories = {"General": ["ping"]}
    norm = R.normalize_categories(categories=categories, cmd_map=cmd_map, pairs=pairs)
    assert norm == {"General": ["ping"]}


# ----------------------------
# resolve_visible_by_category
# ----------------------------
@pytest.mark.asyncio
async def test_resolve_visible_by_category_adds_autres_for_undeclared_leaf_excludes_group_and_help():
    # Declared category has 'a'. Undeclared 'b' should go to Autres.
    # Group 'xp' should NOT go to Autres. 'help' should NOT go to Autres.
    cmd_a = make_leaf("a", can_run=True)
    cmd_b = make_leaf("b", can_run=True)
    cmd_help = make_leaf("help", can_run=True)

    g = make_group("xp", children_attr="commands", children=[])
    profile = make_leaf("profile", parent=g, can_run=True)
    g.commands = [profile]

    pairs = [
        ("a", cmd_a),
        ("b", cmd_b),
        ("help", cmd_help),
        ("xp", g),
        ("xp profile", profile),
    ]
    cmd_map = {k: v for k, v in pairs}

    user = FakeUser(1, guild_permissions=make_perms(0xFFFF))
    ctx = FakeCtx(user=user)

    categories = {"Utils": ["a"]}

    visible = await R.resolve_visible_by_category(
        ctx=ctx,
        cmd_map=cmd_map,
        pairs=pairs,
        categories=categories,
        excluded_cmds=set(),
    )

    # Utils: a ; Autres: b + xp profile (leaf non déclarée)
    assert visible == {"Utils": ["a"], "Autres": ["b", "xp profile"]}


@pytest.mark.asyncio
async def test_resolve_visible_by_category_excludes_excluded_cmds_everywhere():
    cmd_a = make_leaf("a", can_run=True)
    cmd_hidden = make_leaf("manual_save", can_run=True)

    pairs = [("a", cmd_a), ("manual_save", cmd_hidden)]
    cmd_map = {k: v for k, v in pairs}

    user = FakeUser(1, guild_permissions=make_perms(0xFFFF))
    ctx = FakeCtx(user=user)

    categories = {"Utils": ["a", "manual_save"]}

    visible = await R.resolve_visible_by_category(
        ctx=ctx,
        cmd_map=cmd_map,
        pairs=pairs,
        categories=categories,
        excluded_cmds={"manual_save"},
    )

    assert visible == {"Utils": ["a"]}


@pytest.mark.asyncio
async def test_resolve_visible_by_category_filters_by_default_member_permissions():
    # cmd requires perm bit 0b10, user only has 0b01 => hidden
    cmd_admin = make_leaf("admin", dp=make_perms(0b10), can_run=True)

    pairs = [("admin", cmd_admin)]
    cmd_map = {"admin": cmd_admin}

    user = FakeUser(1, guild_permissions=make_perms(0b01))
    ctx = FakeCtx(user=user)

    categories = {"Admin": ["admin"]}
    visible = await R.resolve_visible_by_category(ctx=ctx, cmd_map=cmd_map, pairs=pairs, categories=categories)

    assert visible == {}  # rien visible


@pytest.mark.asyncio
async def test_resolve_visible_by_category_inherits_permissions_from_parent_group():
    # group requires perm 0b10; leaf has no perms; user has 0b10 => visible
    group = make_group("xp", children_attr="commands", children=[], dp=make_perms(0b10), can_run=True)
    leaf = make_leaf("profile", parent=group, dp=None, can_run=True)
    group.commands = [leaf]

    pairs = [("xp", group), ("xp profile", leaf)]
    cmd_map = {k: v for k, v in pairs}

    user_ok = FakeUser(1, guild_permissions=make_perms(0b10))
    ctx_ok = FakeCtx(user=user_ok)

    categories = {"XP": ["xp"]}  # expands to xp profile
    visible_ok = await R.resolve_visible_by_category(ctx=ctx_ok, cmd_map=cmd_map, pairs=pairs, categories=categories)
    assert visible_ok == {"XP": ["xp profile"]}

    user_no = FakeUser(2, guild_permissions=make_perms(0b01))
    ctx_no = FakeCtx(user=user_no)
    visible_no = await R.resolve_visible_by_category(ctx=ctx_no, cmd_map=cmd_map, pairs=pairs, categories=categories)
    assert visible_no == {}  # hidden due to inherited perms


@pytest.mark.asyncio
async def test_resolve_visible_by_category_can_run_false_or_exception_filters_out():
    cmd_ok = make_leaf("ok", can_run=True)
    cmd_no = make_leaf("no", can_run=False)
    cmd_boom = make_leaf("boom", can_run=RuntimeError("fail"))

    pairs = [("ok", cmd_ok), ("no", cmd_no), ("boom", cmd_boom)]
    cmd_map = {k: v for k, v in pairs}

    user = FakeUser(1, guild_permissions=make_perms(0xFFFF))
    ctx = FakeCtx(user=user)

    categories = {"Cat": ["ok", "no", "boom"]}
    visible = await R.resolve_visible_by_category(ctx=ctx, cmd_map=cmd_map, pairs=pairs, categories=categories)

    assert visible == {"Cat": ["ok"]}


@pytest.mark.asyncio
async def test_resolve_visible_by_category_inherits_can_run_from_parent_group():
    # group can_run False => leaf hidden even if leaf can_run True
    group = make_group("rr", children_attr="commands", children=[], can_run=False)
    leaf = make_leaf("add", parent=group, can_run=True)
    group.commands = [leaf]

    pairs = [("rr", group), ("rr add", leaf)]
    cmd_map = {k: v for k, v in pairs}

    user = FakeUser(1, guild_permissions=make_perms(0xFFFF))
    ctx = FakeCtx(user=user)

    categories = {"RR": ["rr"]}  # expands to rr add
    visible = await R.resolve_visible_by_category(ctx=ctx, cmd_map=cmd_map, pairs=pairs, categories=categories)

    assert visible == {}  # hidden due to parent can_run False