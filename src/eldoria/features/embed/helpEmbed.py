import discord
from discord.ext import commands


async def generate_help_embed(list_of_tuple_title_description, current_page, total_pages, id, bot: commands.Bot):
    
    embed=discord.Embed(
            title="Liste des Commandes",
            description="Voici ci-dessous la liste de toutes les commandes disponible.",
            colour=discord.Color(0x00FFFF)
        )

    for element in list_of_tuple_title_description:
        embed.add_field(name='', value='',inline=False)
        embed.add_field(
            name=f"· /{element[0]} ",
            value=f"{element[1]}",
            inline=False
        )

    embed.set_footer(text=f"Page {current_page + 1}/{total_pages}")

    thumbnail_path = "./images/logo_Bot.png"
    thumbnail_file = discord.File(thumbnail_path, filename="logo_Bot.png")
    embed.set_thumbnail(url="attachment://logo_Bot.png")

    image_path = f"./images/banner_Bot.png"
    image_file = discord.File(image_path, filename="banner_Bot.png")
    embed.set_image(url="attachment://banner_Bot.png")

    files =[thumbnail_file,image_file]
    return embed,files