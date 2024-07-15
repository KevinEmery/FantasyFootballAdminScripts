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

import cogs.constants
import cogs.common

from discord import app_commands
from discord.ext import commands

GUILD_IDS = [
    cogs.constants.DEV_SERVER_GUILD_ID,
    cogs.constants.FTA_SERVER_GUILD_ID,
    cogs.constants.NARFFL_SERVER_GUILD_ID,
    cogs.constants.FF_DISCORD_SERVER_GUILD_ID
]

class DiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="&&&unused", intents=intents)

        self.cogs_list = [
            'cogs.adp',
            'cogs.depth_charts',
            'cogs.leaderboards',
            'cogs.inactives',
            'cogs.trades',
        ]

    async def setup_hook(self):
        for ext in self.cogs_list:
            await self.load_extension(ext)

        # Specifically sync the target servers.
        for guild_id in GUILD_IDS:
            await self.tree.sync(guild=discord.Object(guild_id))

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')


def _retrieve_token() -> str:
    token_file = open("./local/bot_token", "r")
    token_string = token_file.read()
    token_file.close()

    return token_string


bot = DiscordBot()


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction,
                               error: app_commands.AppCommandError):
    await interaction.followup.send(
        "Error during execution, please reach out to the author for more information"
    )
    if isinstance(error, app_commands.CommandInvokeError):
        message_template = "Error during execution of {command_name}: {error}"
        cogs.common.print_descriptive_log(
            "on_app_command_error",
            message_template.format(command_name=error.command.name,
                                    error=error.original))
    else:
        cogs.common.print_descriptive_log("on_app_command_error", error)


bot.run(_retrieve_token())
