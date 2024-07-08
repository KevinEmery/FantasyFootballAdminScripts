"""
   Copyright 2024 Kevin Emery

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import discord

import cogs.common as cogCommon

from discord import app_commands
from discord.ext import commands

class TestCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="helloworld", description="The only logical first command")
    @app_commands.guilds(cogCommon.DEV_SERVER_GUILD_ID)
    async def testing(self, interaction: discord.Interaction):
        cogCommon.print_descriptive_log("helloworld", "Log Testing!")
        await interaction.response.send_message("Hello, World!")

async def setup(bot):
    await bot.add_cog(TestCog(bot))