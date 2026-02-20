"""Menu de help interactif (embeds + boutons)."""
from __future__ import annotations

import discord

from eldoria.app.bot import EldoriaBot
from eldoria.json_tools.help_json import load_help_config
from eldoria.ui.common.components import BasePanelView, RoutedButton
from eldoria.ui.common.embeds.images import common_files
from eldoria.ui.help.embeds import build_category_embed, build_home_embed
from eldoria.ui.help.resolver import build_command_index, resolve_visible_by_category


class HelpMenuView(BasePanelView):
    """Menu de help interactif (embeds + boutons), permission-aware."""

    def __init__(
        self,
        *,
        author_id: int,
        cmd_map: dict[str, object],
        help_infos: dict[str, str],
        visible_by_cat: dict[str, list[str]],
        cat_descriptions: dict[str, str] | None = None,
    ) -> None:
        """Initialise la view."""
        super().__init__(author_id=author_id, timeout=240)
        self.cmd_map = cmd_map
        self.help_infos = help_infos
        self.visible_by_cat = visible_by_cat
        self.cat_descriptions = cat_descriptions or {}

        self.current: str | None = None  # None = home

        # URLs des images une fois le message envoyé (si tu décides de les set plus tard)
        self._thumb_url: str | None = None
        self._banner_url: str | None = None

        # Marque si on a déjà uploadé les fichiers au moins une fois
        self._uploaded_once = False

        # Boutons
        self._cat_buttons: dict[str, discord.ui.Button] = {}

        self.home_button = RoutedButton(
            label="Accueil",
            style=discord.ButtonStyle.secondary,
            custom_id="help:home",
        )
        self.add_item(self.home_button)

        for cat in self.visible_by_cat.keys():
            btn = RoutedButton(
                label=cat,
                style=discord.ButtonStyle.secondary,
                custom_id=f"help:cat:{cat}",
            )
            self.add_item(btn)
            self._cat_buttons[cat] = btn

        self._refresh_nav_buttons()

    # -------------------- Routing --------------------
    async def route_button(self, interaction: discord.Interaction) -> None:
        """Router unique pour tous les boutons de la view."""
        cid = getattr(interaction.data, "get", lambda _k, _d=None: None)("custom_id")  # type: ignore[attr-defined]
        if not isinstance(cid, str):
            return

        if cid == "help:home":
            await self._go_home(interaction)
            return

        if cid.startswith("help:cat:"):
            cat = cid.removeprefix("help:cat:")
            if cat not in self.visible_by_cat:
                return
            self.current = cat
            self._refresh_nav_buttons()
            embed, files = self.build_category(cat)
            await self._safe_edit(interaction, embed=embed, files=files)
            return

    # -------------------- UI helpers --------------------
    def _refresh_nav_buttons(self) -> None:
        """Met en évidence la page actuelle (couleur + disabled)."""
        default_style = discord.ButtonStyle.secondary
        active_style = discord.ButtonStyle.primary

        # Home
        if self.current is None:
            self.home_button.style = active_style
            self.home_button.disabled = True
        else:
            self.home_button.style = default_style
            self.home_button.disabled = False

        # Catégories
        for cat, btn in self._cat_buttons.items():
            if self.current == cat:
                btn.style = active_style
                btn.disabled = True
            else:
                btn.style = default_style
                btn.disabled = False

    def _common_files(self) -> list[discord.File]:
        return common_files(self._thumb_url, self._banner_url)

    def build_home(self) -> tuple[discord.Embed, list[discord.File]]:
        """Construit l'embed de la page d'accueil."""
        embed = build_home_embed(
            visible_by_cat=self.visible_by_cat,
            cat_descriptions=self.cat_descriptions,
            thumb_url=self._thumb_url,
            banner_url=self._banner_url,
        )
        return embed, self._common_files()

    def build_category(self, cat: str) -> tuple[discord.Embed, list[discord.File]]:
        """Construit l'embed d'une catégorie donnée."""
        cmds = self.visible_by_cat.get(cat, [])
        embed = build_category_embed(
            cat=cat,
            cmds=cmds,
            help_infos=self.help_infos,
            cmd_map=self.cmd_map,
            thumb_url=self._thumb_url,
            banner_url=self._banner_url,
        )
        return embed, self._common_files()

    async def _safe_edit(
        self,
        interaction: discord.Interaction,
        *,
        embed: discord.Embed,
        files: list[discord.File] | None = None,
    ) -> None:
        """Edite le message sans ré-uploader les fichiers après le 1er envoi (comportement conservé)."""
        try:
            # 1) Si on peut répondre directement, on le fait (1 call)
            if not interaction.response.is_done():
                await interaction.response.edit_message(embed=embed, view=self)
                return

            # 2) Sinon, on édite l'original
            if getattr(self, "_uploaded_once", False):
                await interaction.edit_original_response(embed=embed, view=self)
                return

            # 3) Fallback rare
            await interaction.edit_original_response(embed=embed, files=files or [], view=self)
            self._uploaded_once = True

        except (discord.NotFound, discord.HTTPException):
            return

    async def _go_home(self, interaction: discord.Interaction) -> None:
        self.current = None
        self._refresh_nav_buttons()
        embed, files = self.build_home()
        await self._safe_edit(interaction, embed=embed, files=files)


# -------------------- Slash command helper --------------------
async def send_help_menu(ctx: discord.ApplicationContext, bot: EldoriaBot) -> None:
    """Commande d'ouverture du menu de help."""
    # Compat tests/fakes: defer peut ne pas être totalement conforme
    try:
        if hasattr(ctx, "defer"):
            await ctx.defer(ephemeral=True)
    except Exception:
        pass

    # Index commandes (inclut SlashCommandGroup -> sous-commandes)
    pairs, cmd_map = build_command_index(bot)

    # Help config (json)
    help_infos, categories, cat_descriptions = load_help_config()

    # Commandes internes à masquer
    excluded_cmds = {"manual_save", "insert_db"}
    for name in excluded_cmds:
        cmd_map.pop(name, None)
        help_infos.pop(name, None)

    # Nettoie les catégories (si elles listent des excluded)
    for cat, lst in list(categories.items()):
        categories[cat] = [c for c in lst if c not in excluded_cmds]

    # Filtrage permission-aware + "Autres"
    visible_by_cat = await resolve_visible_by_category(
        ctx=ctx,
        cmd_map=cmd_map,
        pairs=pairs,
        categories=categories,
        excluded_cmds=excluded_cmds,
    )

    if not visible_by_cat:
        await ctx.followup.send(
            content="Aucune commande disponible avec vos permissions.",
            ephemeral=True,
        )
        return

    view = HelpMenuView(
        author_id=ctx.user.id,
        cmd_map=cmd_map,
        help_infos=help_infos,
        visible_by_cat=visible_by_cat,
        cat_descriptions=cat_descriptions,
    )
    embed, files = view.build_home()
    await ctx.followup.send(embed=embed, files=files, view=view, ephemeral=True)
    view._uploaded_once = True