import discord

import cogs.common

from discord.ext import commands

class DiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="&", intents=intents)

        self.cogs_list = [
            'cogs.test'
        ]

    async def setup_hook(self):
        for ext in self.cogs_list:
            await self.load_extension(ext)

        await self.tree.sync(guild=discord.Object(id=cogs.common.DEV_SERVER_GUILD_ID))


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
