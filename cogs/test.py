import discord

from discord import app_commands
from discord.ext import commands

from .common import DEV_SERVER_GUILD_ID

class TestCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="helloworld", description="The only logical first command")
    @app_commands.guilds(DEV_SERVER_GUILD_ID)
    async def testing(self, interaction: discord.Interaction):
        await interaction.response.send_message("Hello, World!")

async def setup(bot):
    await bot.add_cog(TestCog(bot))