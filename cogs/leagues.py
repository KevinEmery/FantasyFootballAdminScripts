"""
   Copyright 2025 Kevin Emery

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

import asyncio
import discord
import functools
import re

import cogs.common as cogCommon
import cogs.constants as cogConstants
import library.common as libCommon

from discord import app_commands
from discord.ext import commands
from typing import List

from library.model.league import League
from library.model.user import User
from library.platforms.sleeper.sleeper import Sleeper

# Trying to keep this well clear of the 2000 character limit
OUTPUT_LENGTH_LIMIT = 1500

class LeaguesCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot


    @app_commands.command(
        name="sleeper_list_all_leagues",
        description=
        "Retrieves the specified team's full roster, organized as a depth-chart sorted by position"
    )
    @app_commands.rename(identifier="username")
    @app_commands.describe(identifier="The full Sleeper username of the team owner")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def sleeper_list_all_leagues(self, 
                                       interaction: discord.Interaction,
                                       identifier: str,
                                       year: int = libCommon.DEFAULT_YEAR):
        cogCommon.print_descriptive_log(
            "sleeper_list_all_leagues",
            "user={username}".format(username=identifier, year=year))
        await interaction.response.defer()

        sleeper = Sleeper()

        user = sleeper.get_admin_user_by_identifier(identifier)
        leagues = sleeper.get_all_leagues_for_user(user, year)
        cogCommon.print_descriptive_log("sleeper_list_all_leagues", "Found {count} leagues".format(count=len(leagues)))

        league_format = "**{league_name}**\nDraft: <{draft_link}>\nTeam: <{team_link}>\n"
        for league in leagues:
            team = sleeper.get_team_for_user(league, user)
            response += league_format.format(league_name=league.name, draft_link=cogCommon.create_sleeper_draft_url_from_id(league.draft_id), team_link=team.roster_link)

            if len(response) > OUTPUT_LENGTH_LIMIT:
                    await interaction.channel.send(response)
                    response = ""

        if response != "":
            await interaction.channel.send(response)

        cogCommon.print_descriptive_log("sleeper_list_all_leagues", "Done")
        await interaction.followup.send("Done!")


async def setup(bot):
    await bot.add_cog(LeaguesCog(bot))