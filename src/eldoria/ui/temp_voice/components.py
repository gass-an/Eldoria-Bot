"""Module contenant les composants de l'interface utilisateur pour la fonctionnalité de salons vocaux temporaires."""
from __future__ import annotations

import discord


class BasePanelView(discord.ui.View):
    """Base View réutilisable : contrôle auteur + timeout."""

    def __init__(self, *, author_id: int, timeout: float = 180) -> None:
        """Initialise la BasePanelView avec l'ID de l'auteur autorisé à interagir et un timeout pour désactiver les composants après une période d'inactivité."""
        super().__init__(timeout=timeout)
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Vérifie que l'utilisateur qui interagit avec la View est bien l'auteur de la commande.
        
        Si ce n'est pas le cas, envoie un message d'erreur éphémère et ignore l'interaction.
        """
        if interaction.user is None or interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ Seul l'auteur de la commande peut utiliser ce panneau.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        """Désactive tous les composants de la View lorsque le timeout est atteint."""
        for item in self.children:
            if isinstance(item, (discord.ui.Button, discord.ui.Select)):
                item.disabled = True


class RoutedButton(discord.ui.Button):
    """Bouton qui délègue à un handler unique (router) dans la View."""

    def __init__(
        self,
        *,
        label: str,
        style: discord.ButtonStyle,
        custom_id: str,
        disabled: bool = False,
        emoji: str | None = None,
    ) -> None:
        """Initialise le RoutedButton avec les paramètres standard d'un bouton Discord, ainsi qu'un custom_id pour l'identification dans le router de la View."""
        super().__init__(label=label, style=style, custom_id=custom_id, disabled=disabled, emoji=emoji)

    async def callback(self, interaction: discord.Interaction) -> None:
        """Lorsqu'un bouton est cliqué, délègue le traitement à la méthode route_button de la View, en lui passant l'interaction."""
        view = self.view
        if view is None or not hasattr(view, "route_button"):
            return
        await getattr(view, "route_button")(interaction)


class RoutedSelect(discord.ui.Select):
    """Select qui délègue à un handler unique (router) dans la View."""

    def __init__(
        self,
        *,
        placeholder: str,
        options: list[discord.SelectOption],
        custom_id: str,
        min_values: int = 1,
        max_values: int = 1,
        disabled: bool = False,
    ) -> None:
        """Initialise le RoutedSelect avec les paramètres standard d'un select Discord, ainsi qu'un custom_id pour l'identification dans le router de la View."""
        super().__init__(
            placeholder=placeholder,
            options=options,
            custom_id=custom_id,
            min_values=min_values,
            max_values=max_values,
            disabled=disabled,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        """Lorsqu'une option est sélectionnée, délègue le traitement à la méthode route_select de la View, en lui passant l'interaction et les valeurs sélectionnées."""
        view = self.view
        if view is None or not hasattr(view, "route_select"):
            return
        await getattr(view, "route_select")(interaction, list(self.values))
