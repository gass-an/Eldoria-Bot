import discord

from eldoria.json_tools.help_json import load_help_config
from eldoria.ui.common.embeds.images import common_files, decorate
from eldoria.ui.help.embeds import build_category_embed, build_home_embed


class HelpMenuView(discord.ui.View):
    """Menu de help interactif (embeds + boutons).

    - Affiche une page d'accueil avec les fonctionnalités accessibles.
    - Chaque fonctionnalité ouvre une page détaillant les commandes accessibles.

    Le menu est "permission-aware" : on n'affiche que ce que l'utilisateur peut exécuter.
    """

    def __init__(
        self,
        author_id: int,
        bot,
        cmd_map: dict,
        help_infos: dict,
        visible_by_cat: dict[str, list[str]],
        cat_descriptions: dict[str, str] | None = None,
    ):
        super().__init__(timeout=240)
        self.author_id = author_id
        self.bot = bot
        self.cmd_map = cmd_map
        self.help_infos = help_infos
        self.visible_by_cat = visible_by_cat
        self.cat_descriptions = cat_descriptions or {}
        self.current: str | None = None  # None = home

        # URLs des images une fois le message envoyé.
        # Objectif: éviter de ré-uploader les mêmes fichiers à chaque clic (latence).
        self._thumb_url: str | None = None
        self._banner_url: str | None = None

        # On garde une référence aux boutons de catégories pour pouvoir
        # mettre en évidence la page courante (couleur différente + non cliquable).
        self._cat_buttons: dict[str, discord.ui.Button] = {}

        # Construit les boutons (accueil + 1 bouton par catégorie)
        self.home_button = discord.ui.Button(label="Accueil")
        self.home_button.callback = self._go_home
        self.add_item(self.home_button)

        # Boutons catégories
        for cat in self.visible_by_cat.keys():
            btn = discord.ui.Button(label=cat)
            btn.callback = self._make_cat_cb(cat)
            self.add_item(btn)
            self._cat_buttons[cat] = btn

        # Styles initiaux (Home = page courante)
        self._refresh_nav_buttons()

    def _refresh_nav_buttons(self):
        """Met en évidence la page actuelle.

        - Bouton de la page courante : couleur différente + disabled
        - Tous les autres : cliquables et même couleur
        """
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

    # -------------------- Embeds builders --------------------
    def _common_files(self):
        return common_files(self._thumb_url, self._banner_url)
    def _decorate(self, embed: discord.Embed):
        return decorate(embed, self._thumb_url, self._banner_url)

    def _capture_attachment_urls_from_message(self, interaction: discord.Interaction):
        """Récupère les URLs CDN des images déjà attachées au message."""
        msg = interaction.message
        if not msg or not getattr(msg, "attachments", None):
            return
        for att in msg.attachments:
            if att.filename == "logo_bot.png":
                self._thumb_url = att.url
            elif att.filename == "banner_bot.png":
                self._banner_url = att.url
    def build_home(self):
        embed = build_home_embed(
            visible_by_cat=self.visible_by_cat,
            cat_descriptions=self.cat_descriptions,
            thumb_url=self._thumb_url,
            banner_url=self._banner_url,
        )
        return embed, self._common_files()
    def build_category(self, cat: str):
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

    # -------------------- Interaction guards --------------------
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Empêche les autres utilisateurs de manipuler le menu (utile même en non-ephemeral)
        if interaction.user and interaction.user.id != self.author_id:
            try:
                await interaction.response.send_message(
                    "❌ Ce menu ne t'appartient pas.", ephemeral=True
                )
            except discord.InteractionResponded:
                await interaction.followup.send(
                    "❌ Ce menu ne t'appartient pas.", ephemeral=True
                )
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True


    async def _safe_edit(self, interaction: discord.Interaction, *, embed: discord.Embed, files=None):
        """Ack the interaction quickly, then edit the original message.
        Prevents 'Unknown interaction' when the callback takes too long or the client lags.
        """
        try:
            # On récupère les URLs CDN dès qu'on peut.
            self._capture_attachment_urls_from_message(interaction)

            # Chemin "rapide" : si on ne renvoie pas de fichiers, on peut répondre directement
            # via interaction.response.edit_message (1 seule requête au lieu defer+edit).
            fast_no_files = (self._thumb_url and self._banner_url)
            if not interaction.response.is_done():
                if fast_no_files:
                    await interaction.response.edit_message(embed=embed, view=self)
                    return
                # Sinon, on ACK tout de suite pour éviter l'expiration, puis on édite.
                await interaction.response.defer()

            if fast_no_files:
                await interaction.edit_original_response(embed=embed, view=self)
            else:
                await interaction.edit_original_response(embed=embed, files=files, view=self)
        except discord.NotFound:
            # Interaction expired or message deleted -> nothing we can do safely
            return
        except discord.HTTPException:
            return

    # -------------------- Button callbacks --------------------
    def _make_cat_cb(self, cat: str):
        async def _cb(interaction: discord.Interaction):
            self.current = cat
            self._refresh_nav_buttons()
            embed, files = self.build_category(cat)
            await self._safe_edit(interaction, embed=embed, files=files)

        return _cb

    async def _go_home(self, interaction: discord.Interaction):
        self.current = None
        self._refresh_nav_buttons()
        embed, files = self.build_home()
        await self._safe_edit(interaction, embed=embed, files=files)


# -------------------- Slash command helper --------------------
async def send_help_menu(ctx: discord.ApplicationContext, bot):
    """Send the interactive help menu (same logic as the original core /help)."""

    await ctx.defer(ephemeral=True)

    cmd_map = {c.name: c for c in bot.application_commands}
    member_perms = ctx.user.guild_permissions

    # Help config (normalisée) via json_tools/gestionJson.py
    help_infos, categories, cat_descriptions = load_help_config()

    # Commandes internes / techniques qu'on ne veut pas exposer dans le /help
    excluded_cmds = {"manual_save", "insert_db"}
    for _c in excluded_cmds:
        cmd_map.pop(_c, None)
        help_infos.pop(_c, None)

    # Nettoie les catégories (au cas où elles contiennent une commande exclue)
    for _cat, _cmds in list(categories.items()):
        categories[_cat] = [c for c in _cmds if c not in excluded_cmds]

    async def is_command_visible(cmd_name: str) -> bool:
        cmd = cmd_map.get(cmd_name)
        if cmd is None:
            return False

        dp = getattr(cmd, "default_member_permissions", None)
        if dp is not None:
            # l'utilisateur doit posséder toutes les perms par défaut requises
            if (member_perms.value & dp.value) != dp.value:
                return False

        try:
            can = await cmd.can_run(ctx)
            if not can:
                return False
        except Exception:
            return False

        return True

    # ---- Catégorisation

    # Ajoute automatiquement les commandes non déclarées dans une catégorie "Autres"
    declared = {c for cmds in categories.values() for c in cmds}
    for cmd_name in cmd_map.keys():
        if cmd_name in ("help",):
            continue
        if cmd_name not in declared:
            categories.setdefault("Autres", []).append(cmd_name)

    # Filtrage par visibilité
    visible_by_cat: dict[str, list[str]] = {}
    for cat, cmds in categories.items():
        visible_cmds = []
        for cmd_name in cmds:
            if await is_command_visible(cmd_name):
                visible_cmds.append(cmd_name)
        if visible_cmds:
            visible_by_cat[cat] = visible_cmds

    if not visible_by_cat:
        await ctx.followup.send(
            "Aucune commande disponible avec vos permissions.",
            ephemeral=True,
        )
        return

    view = HelpMenuView(
        author_id=ctx.user.id,
        bot=bot,
        cmd_map=cmd_map,
        help_infos=help_infos,
        visible_by_cat=visible_by_cat,
        cat_descriptions=cat_descriptions,
    )
    embed, files = view.build_home()
    await ctx.followup.send(embed=embed, files=files, view=view, ephemeral=True)
