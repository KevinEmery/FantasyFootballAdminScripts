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

from discord.ext import commands

class DiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="&", intents=intents)

        self.cogs_list = [
            'cogs.adp',
            'cogs.test',
        ]

    async def setup_hook(self):
        for ext in self.cogs_list:
            await self.load_extension(ext)

        await self.tree.sync(guild=discord.Object(id=cogs.constants.DEV_SERVER_GUILD_ID))


    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')


def _retrieve_token() -> str:
    token_file = open("./local/bot_token", "r")
    token_string = token_file.read()
    token_file.close()

    return token_string

bot = DiscordBot()
bot.run(_retrieve_token())
