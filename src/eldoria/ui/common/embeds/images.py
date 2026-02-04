import discord

# ---------------------------------------------------------------------------
# Images helpers (centralisé)
# ---------------------------------------------------------------------------

DEFAULT_THUMBNAIL_PATH = "./assets/images/logo_bot.png"
DEFAULT_BANNER_PATH = "./assets/images/banner_bot.png"
DEFAULT_THUMBNAIL_FILENAME = "logo_bot.png"
DEFAULT_BANNER_FILENAME = "banner_bot.png"


def common_files(
    thumb_url: str | None,
    banner_url: str | None,
    *,
    thumbnail_path: str = DEFAULT_THUMBNAIL_PATH,
    banner_path: str = DEFAULT_BANNER_PATH,
    thumbnail_filename: str = DEFAULT_THUMBNAIL_FILENAME,
    banner_filename: str = DEFAULT_BANNER_FILENAME,
) -> list[discord.File]:
    """Retourne les fichiers à attacher (thumbnail + banner).

    - Pour éviter de ré-uploader à chaque interaction : si les URLs CDN sont
      déjà connues, on ne renvoie rien.
    - Sinon, on renvoie les fichiers en tant que pièces jointes.
    """
    if thumb_url and banner_url:
        return []

    return [
        discord.File(thumbnail_path, filename=thumbnail_filename),
        discord.File(banner_path, filename=banner_filename),
    ]


def decorate(
    embed: discord.Embed,
    thumb_url: str | None,
    banner_url: str | None,
    *,
    thumbnail_filename: str = DEFAULT_THUMBNAIL_FILENAME,
    banner_filename: str = DEFAULT_BANNER_FILENAME,
) -> discord.Embed:
    """Applique thumbnail + banner sur un embed.

    - Si les URLs CDN sont connues (après le premier envoi), on les réutilise.
    - Sinon, on pointe vers les attachments du message.
    """
    if thumb_url and banner_url:
        embed.set_thumbnail(url=thumb_url)
        embed.set_image(url=banner_url)
    else:
        embed.set_thumbnail(url=f"attachment://{thumbnail_filename}")
        embed.set_image(url=f"attachment://{banner_filename}")

    return embed




def common_thumb(
    thumb_url: str | None,
    *,
    thumbnail_path: str = DEFAULT_THUMBNAIL_PATH,
    thumbnail_filename: str = DEFAULT_THUMBNAIL_FILENAME,
) -> list[discord.File]:
    """Retourne le fichier à attacher (thumbnail).

    - Pour éviter de ré-uploader à chaque interaction : si les URLs CDN sont
      déjà connues, on ne renvoie rien.
    - Sinon, on renvoie le fichier en tant que pièces jointes.
    """
    if thumb_url:
        return []

    return [
        discord.File(thumbnail_path, filename=thumbnail_filename),
    ]


def decorate_thumb_only(
    embed: discord.Embed,
    thumb_url: str | None,
    *,
    thumbnail_filename: str = DEFAULT_THUMBNAIL_FILENAME,
) -> discord.Embed:
    """Applique thumbnail sur un embed.

    - Si les URLs CDN sont connues (après le premier envoi), on les réutilise.
    - Sinon, on pointe vers les attachments du message.
    """
    if thumb_url:
        embed.set_thumbnail(url=thumb_url)
    else:
        embed.set_thumbnail(url=f"attachment://{thumbnail_filename}")

    return embed
