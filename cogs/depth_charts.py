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
from library.model.futuredraftpick import FutureDraftPick
from library.model.roster import Roster
from library.model.user import User
from library.platforms.sleeper.sleeper import Sleeper


class SortedRoster():
    def __init__(self, roster: Roster):
        # These are all maps of player position (str) -> List of players (List[Player])
        self.starters = {}
        self.bench = {}
        self.taxi = {}

        # Set containing all positions that this team has rostered
        self.all_positions = set()

        for player in roster.starters:
            if player.position not in self.starters:
                self.starters[player.position] = []
                self.all_positions.add(player.position)

            self.starters[player.position].append(player)

        for player in roster.bench:
            if player.position not in self.bench:
                self.bench[player.position] = []
                self.all_positions.add(player.position)

            self.bench[player.position].append(player)

        for player in roster.taxi:
            if player.position not in self.taxi:
                self.taxi[player.position] = []
                self.all_positions.add(player.position)

            self.taxi[player.position].append(player)

        self.all_positions = sorted(self.all_positions,
                                    key=functools.cmp_to_key(
                                        SortedRoster._compare_positions))

    def _compare_positions(item1, item2):
        forced_position_order = {
            "QB": 1,
            "RB": 2,
            "WR": 3,
            "TE": 4,
            "K": 5,
            "DEF": 6,
            "DL": 7,
            "LB": 8,
            "DB": 9
        }

        index1 = forced_position_order[
            item1] if item1 in forced_position_order else 99
        index2 = forced_position_order[
            item2] if item2 in forced_position_order else 99

        return index1 - index2


class DepthChartsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="sleeper_depth_chart",
        description=
        "Retrieves the specified team's full roster, organized as a depth-chart sorted by position"
    )
    @app_commands.rename(identifier="username")
    @app_commands.describe(league_name="Some or all of the league name")
    @app_commands.describe(
        identifier="The full Sleeper username of the team owner")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID,
                         cogConstants.FF_DISCORD_SERVER_GUILD_ID,
                         cogConstants.FTA_SERVER_GUILD_ID)
    async def sleeper_depth_chart(self,
                                  interaction: discord.Interaction,
                                  league_name: str,
                                  identifier: str,
                                  year: int = libCommon.DEFAULT_YEAR):
        cogCommon.print_descriptive_log(
            "sleeper_depth_chart",
            "league_name={league_name}, user={username}, year={year}".format(
                league_name=league_name, username=identifier, year=year))
        await interaction.response.defer()

        sleeper = Sleeper()

        user = sleeper.get_admin_user_by_identifier(identifier)

        # Error handling for user
        if user.user_id == "Error":
            cogCommon.print_descriptive_log(
                "sleeper_depth_chart",
                "No user found for {username}".format(username=identifier))
            await interaction.followup.send(
                "Sleeper account `{username}` not found. Please double-check and try again."
                .format(username=identifier))
            return

        leagues = await asyncio.to_thread(sleeper.get_all_leagues_for_user,
                                          user,
                                          year,
                                          name_substring=league_name,
                                          include_pre_draft=True)

        # Error handling for leagues
        if len(leagues) == 0:
            cogCommon.print_descriptive_log(
                "sleeper_depth_chart",
                "No leagues matching {league_name} found for {user}".format(
                    league_name=league_name, user=identifier))
            await interaction.followup.send(
                "`{username}` does not have any leagues matching `{league_name}`. Please double-check and try again."
                .format(username=identifier, league_name=league_name))
            return
        elif len(leagues) > 1:
            cogCommon.print_descriptive_log(
                "sleeper_depth_chart",
                "{user} has more than one league matching {league_name}".
                format(league_name=league_name, user=identifier))
            await interaction.followup.send(
                "`{username}` has more than one league matching `{league_name}`. Please be more specific.\n\n__Matching Leagues__\n{league_list}"
                .format(username=identifier,
                        league_name=league_name,
                        league_list=self._create_markdown_list_of_league_names(
                            leagues)))
            return

        league = leagues[0]
        roster = await asyncio.to_thread(
            sleeper.get_roster_for_league_and_user, league, user)

        if roster is None:
            cogCommon.print_descriptive_log(
                "sleeper_depth_chart",
                "Error retrieving roster for {user} in {league_name}".format(
                    user=identifier, league_name=league.name))
            await interaction.followup.send(
                "No roster found for `{user}` in `{league_name}`.".format(
                    user=identifier, league_name=league.name))
            return

        await interaction.followup.send(
            embed=self._create_embed_for_roster(roster, identifier, league))
        cogCommon.print_descriptive_log("sleeper_depth_chart", "Done")

    def _create_markdown_list_of_league_names(self,
                                              leagues: List[League]) -> str:
        league_list = ""
        template = "- {league_name}\n"

        for league in leagues:
            league_list += template.format(league_name=league.name)

        return league_list

    def _create_embed_for_roster(self, roster: Roster, user: str,
                                 league: League) -> discord.Embed:
        starter_template = "**{player_name}**"
        taxi_template = "__*{player_name}*__"

        embed = discord.Embed(title="{league} - {username}".format(
            league=league.name, username=user))

        embed.add_field(name="Scoring Settings",
                        value=league.get_league_config_summary_string(),
                        inline=False)

        embed.add_field(name="Roster Settings",
                        value=league.get_roster_count_string(),
                        inline=False)

        embed.add_field(name="Roster Link",
                        value="<{roster_link}>".format(
                            roster_link=roster.team.roster_link),
                        inline=False)

        sorted_roster = SortedRoster(roster)

        for position in sorted_roster.all_positions:
            player_list = ""

            if position in sorted_roster.starters:
                for player in sorted_roster.starters[position]:
                    player_list += starter_template.format(
                        player_name=player.name) + ", "

            if position in sorted_roster.bench:
                for player in sorted_roster.bench[position]:
                    player_list += player.name + ", "

            if position in sorted_roster.taxi:
                for player in sorted_roster.taxi[position]:
                    player_list += taxi_template.format(
                        player_name=player.name) + ", "

            # Trim the trailing comma
            if len(player_list) > 0:
                player_list = player_list[:-2]

            embed.add_field(name=position, value=player_list, inline=False)

        if roster.future_picks:
            embed.add_field(name="Future Picks",
                            value=self._format_future_picks(
                                roster.future_picks),
                            inline=False)

        return embed

    def _format_future_picks(self, picks: List[FutureDraftPick]) -> str:
        year_template = "{year}: "
        formatted_string = ""
        year_to_round_list = {}

        for pick in picks:
            if pick.year not in year_to_round_list:
                year_to_round_list[pick.year] = []

            year_to_round_list[pick.year].append(pick.get_round_with_suffix())

        for year, rounds in year_to_round_list.items():
            formatted_string += year_template.format(year=str(year))

            for item in rounds:
                formatted_string += item + ", "

            formatted_string = formatted_string[:-2] + "\n"

        return formatted_string


async def setup(bot):
    await bot.add_cog(DepthChartsCog(bot))
