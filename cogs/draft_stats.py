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
import os

import cogs.common as cogCommon
import cogs.constants as cogConstants
import library.common as libCommon

from discord import app_commands
from discord.ext import commands
from typing import List

from library.model.league import League
from library.model.user import User
from library.platforms.sleeper.sleeper import Sleeper

# File format
# Leagues file
#   Path: ./bot_data/draft_stats_list
#   league_id,draft_id,league_name
# TODO - add an "is_active" bool to the line above
# Draft per league file
#   Path: ./bot_data/drafts/<draft_id>/draft_data
#   Per person: idenfifier,name,mins_on_clock,pick_count

TRACKED_DRAFTS_LIST_FILE = "./bot_data/draft_stats_league_list"
DRAFT_FILE_PATH_TEMPLATE = "./bot_data/drafts/{draft_id}/draft_data"
ALL_DRAFT_DATA_DIRECTORY_PATH = "./bot_data/drafts"
SPECIFIC_DRAFT_DIRECTORY_PATH_TEMPLATE = "./bot_data/drafts/{draft_id}"

class DraftStatsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="start_tracking_draft",
        description="Adds the provided league to the list of leagues being tracked for stats"
    )
    @app_commands.rename(identifier="username")
    @app_commands.describe(league_name="Some or all of the league name")
    @app_commands.describe(
        identifier="The full Sleeper username of the team owner")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def start_tracking_draft(self, interaction: discord.Interaction, league_name: str, identifier: str, year: int = libCommon.DEFAULT_YEAR):
        cogCommon.print_descriptive_log(
            "start_tracking_draft",
            "league_name={league_name}, user={username}, year={year}".format(
                league_name=league_name, username=identifier, year=year))
        await interaction.response.defer()

        sleeper = Sleeper()
        league, user, err_string = await asyncio.to_thread(cogCommon.get_matching_sleeper_league, sleeper, league_name, identifier, year)

        if err_string is not None:
            await interaction.followup.send(err_string)
            return

        if self._is_draft_being_tracked(league):
            cogCommon.print_descriptive_log("start_tracking_draft", "Done - {league_name} already being tracked".format(league_name=league.name))
            await interaction.followup.send("{league_name} is already being tracked.".format(league_name=league.name))
            return

        self._add_league_to_be_tracked(league)

        cogCommon.print_descriptive_log("start_tracking_draft", "Done - tracking started for {league_name}".format(league_name=league.name))
        await interaction.followup.send("Now tracking the draft for {league_name}.".format(league_name=league.name))


    @app_commands.command(
        name="stop_tracking_draft",
        description="Removes the provided league to the list of leagues being tracked for stats"
    )
    @app_commands.rename(identifier="username")
    @app_commands.describe(league_name="Some or all of the league name")
    @app_commands.describe(
        identifier="The full Sleeper username of the team owner")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def stop_tracking_draft(self, interaction: discord.Interaction, league_name: str, identifier: str, year: int = libCommon.DEFAULT_YEAR):
        cogCommon.print_descriptive_log(
            "stop_tracking_draft",
            "league_name={league_name}, user={username}, year={year}".format(
                league_name=league_name, username=identifier, year=year))
        await interaction.response.defer()

        sleeper = Sleeper()
        league, user, err_string = await asyncio.to_thread(cogCommon.get_matching_sleeper_league, sleeper, league_name, identifier, year)

        if err_string is not None:
            await interaction.followup.send(err_string)
            return

        if not self._is_draft_being_tracked(league):
            cogCommon.print_descriptive_log("stop_tracking_draft", "Done - {league_name} wasn't being tracked".format(league_name=league.name))
            await interaction.followup.send("{league_name} wasn't being tracked.".format(league_name=league.name))
            return

        self._remove_league_from_tracking(league)

        cogCommon.print_descriptive_log("stop_tracking_draft", "Done - tracking ended for {league_name}".format(league_name=league.name))
        await interaction.followup.send("No longer tracking the draft for {league_name}.".format(league_name=league.name))

    @app_commands.command(
        name="list_tracked_drafts",
        description="Lists out all of the drafts being tracked"
    )
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def list_tracked_drafts(self, interaction: discord.Interaction):
        cogCommon.print_descriptive_log("list_tracked_drafts", "Starting")
        await interaction.response.defer()

        list_item_template = "* [{league_name}](<https://sleeper.com/draft/nfl/{draft_id}>)\n"
        response_list = []

        with open(TRACKED_DRAFTS_LIST_FILE, "r") as file:
            for line in file:
                split = line.split(',')
                response_list.append(list_item_template.format(league_name=split[2].strip(), draft_id=split[1]))


        response = "__Drafts Being Tracked__\n"
        response_list = sorted(response_list)
        for item in response_list:
            response += item

        cogCommon.print_descriptive_log("list_tracked_drafts", "Done - Tracking {count} drafts".format(count=str(len(response_list))))
        await interaction.followup.send(response)

    # TODO the actual loop task to monitor and update the draft data

    async def get_stats_for_draft(self, interaction: discord.Interaction, league_name: str, identifier: str, year: int = libCommon.DEFAULT_YEAR):
        print("Unimplemented")

    def _is_draft_being_tracked(self, league: League) -> bool:
        if not os.path.exists(TRACKED_DRAFTS_LIST_FILE):
            return False

        with open(TRACKED_DRAFTS_LIST_FILE, "r") as file:
            for line in file:
                split = line.split(',')
                if split[0] == league.league_id:
                    return True

        return False


    def _add_league_to_be_tracked(self, league: League):
        if self._is_draft_being_tracked(league):
            return

        os.makedirs(ALL_DRAFT_DATA_DIRECTORY_PATH, exist_ok=True)
        os.makedirs(self._get_dir_path_for_league(league), exist_ok=True)
        open(self._get_file_path_for_league(league), 'a').close()

        with open(TRACKED_DRAFTS_LIST_FILE, "a+") as file:
            file.write(self._format_tracked_draft_entry(league))

    def _remove_league_from_tracking(self, league: League):
        if not self._is_draft_being_tracked(league):
            return

        # Read all the lines, and then write out the ones that aren't being removed
        with open(TRACKED_DRAFTS_LIST_FILE, "r") as file:
            lines = file.readlines()
        with open(TRACKED_DRAFTS_LIST_FILE, "w") as file:
            for line in lines:
                if line.split(',')[0] != league.league_id:
                    file.write(line)

        # Remove the draft directory
        os.remove(self._get_file_path_for_league(league))
        os.rmdir(self._get_dir_path_for_league(league))

    def _get_file_path_for_league(self, league: League) -> str:
        return DRAFT_FILE_PATH_TEMPLATE.format(draft_id=league.draft_id)

    def _get_dir_path_for_league(self, league: League) -> str:
        return SPECIFIC_DRAFT_DIRECTORY_PATH_TEMPLATE.format(draft_id=league.draft_id)

    def _format_tracked_draft_entry(self, league: League) -> str:
        template = "{league_id},{draft_id},{league_name}\n"
        return template.format(league_id=league.league_id, draft_id=league.draft_id,league_name=league.name)


async def setup(bot):
    await bot.add_cog(DraftStatsCog(bot))