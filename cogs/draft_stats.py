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
import time

import cogs.common as cogCommon
import cogs.constants as cogConstants
import library.common as libCommon
import library.platforms.sleeper.api as sleeperApi

from datetime import datetime
from discord import app_commands
from discord.ext import commands, tasks

from library.model.league import League
from library.platforms.sleeper.sleeper import Sleeper

TRACKED_DRAFTS_LIST_FILE = "./bot_data/draft_stats_league_list"
DRAFT_FILE_PATH_TEMPLATE = "./bot_data/drafts/{draft_id}/draft_data"
ALL_DRAFT_DATA_DIRECTORY_PATH = "./bot_data/drafts"
SPECIFIC_DRAFT_DIRECTORY_PATH_TEMPLATE = "./bot_data/drafts/{draft_id}"

# Pulled from existing drafts in Sleeper
PRE_DRAFT_STATUS = "pre_draft"
DRAFTING_STATUS = "drafting"
POST_DRAFT_STATUS = "complete"

class DraftStatsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.update_draft_stats.start()
        self.update_draft_stats_checker.start()

    def cog_unload(self):
        self.update_draft_stats.cancel()
        self.update_draft_stats_checker.cancel()

    # Verifies that the task is still running, and restarts them if next scheduled
    # is before now. Handles the occassional crash, but should not happen consistently.
    @tasks.loop(minutes=8)
    async def update_draft_stats_checker(self):

        next_iteration = self.update_draft_stats.next_iteration

        if next_iteration is not None:
            now = datetime.now(tz=next_iteration.tzinfo)
        else:
            # No loops runnning, return
            return

        if next_iteration is not None and next_iteration < now:
            cogCommon.print_descriptive_log(
                "update_draft_stats_checker", "Update Draft Stats task is delayed, restarting")
            self.update_draft_stats.restart()

    @update_draft_stats_checker.before_loop
    async def before_update_draft_stats_checker(self):
        await self.bot.wait_until_ready()


    @app_commands.command(
        name="start_tracking_draft",
        description="Adds the provided league to the list of leagues being tracked for stats"
    )
    @app_commands.rename(identifier="username")
    @app_commands.describe(league_name="Some or all of the league name")
    @app_commands.describe(
        identifier="The full Sleeper username of a league member")
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
        identifier="The full Sleeper username of a league member")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def stop_tracking_draft(self, interaction: discord.Interaction, league_name: str, identifier: str, delete_data: bool = True, year: int = libCommon.DEFAULT_YEAR):
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

        self._remove_league_from_tracking(league, delete_data)

        cogCommon.print_descriptive_log("stop_tracking_draft", "Done - tracking ended for {league_name}".format(league_name=league.name))
        await interaction.followup.send("No longer tracking the draft for {league_name}.".format(league_name=league.name))

    @app_commands.command(
        name="list_tracked_drafts",
        description="Lists out all of the drafts being tracked"
    )
    @app_commands.describe(include_inactive_drafts="Should the response include non-active drafts?")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def list_tracked_drafts(self, interaction: discord.Interaction, include_inactive_drafts: bool = True):
        cogCommon.print_descriptive_log("list_tracked_drafts", "Starting")
        await interaction.response.defer()

        list_item_template = "* [{league_name}](<https://sleeper.com/draft/nfl/{draft_id}>)\n"
        active_drafts_list = []
        inactive_drafts_list = []

        with open(TRACKED_DRAFTS_LIST_FILE, "r") as file:
            for line in file:
                split = line.split(',')
                is_active=(True if split[3].strip() == "True" else False)
                rendered_text=list_item_template.format(league_name=split[2].strip(), draft_id=split[1])
                if is_active:
                    active_drafts_list.append(rendered_text)
                else:
                    inactive_drafts_list.append(rendered_text)


        response = ""

        if len(active_drafts_list) > 0:
            response += "__Active Drafts Being Tracked__\n"
            response_list = sorted(active_drafts_list)
            for item in active_drafts_list:
                response += item

        if include_inactive_drafts and len(inactive_drafts_list) > 0:
            response += "\n__Inactive Drafts Being Tracked__\n"
            response_list = sorted(inactive_drafts_list)
            for item in response_list:
                response += item

        if response == "" and include_inactive_drafts:
            response = "There are no tracked drafts."
        elif response == "" and not include_inactive_drafts:
            response = "There are no active tracked drafts."

        cogCommon.print_descriptive_log("list_tracked_drafts", "Done")
        await interaction.followup.send(response)

    @tasks.loop(minutes=5)
    async def update_draft_stats(self):
        # List to store the active drafts that need to be processed
        drafts_to_process = []

        # Read out all of the tracked drafts so we have them saved.
        # We'll write them back in the next file I/O block
        with open(TRACKED_DRAFTS_LIST_FILE, "r") as file:
            file_lines = file.readlines()

        with open(TRACKED_DRAFTS_LIST_FILE, "w") as file:
            # Iterate over each tracked league to determine if we need to process.
            for draft_metadata in file_lines:
                split = draft_metadata.split(',')
                league_id=split[0]
                draft_id=split[1]
                league_name=split[2]
                is_active=(True if split[3].strip() == "True" else False)

                raw_draft = sleeperApi.get_draft(draft_id)
                draft_status = raw_draft["status"]

                if not is_active and draft_status == DRAFTING_STATUS:
                    # League has started drafting, mark as active
                    is_active = True
                    drafts_to_process.append(draft_id)
                elif is_active and draft_status == POST_DRAFT_STATUS:
                    # League has stopped drafting, mark as inactive but we need
                    # to look at it one last time
                    is_active = False
                    drafts_to_process.append(draft_id)
                elif is_active:
                    # Draft is running, process normally
                    drafts_to_process.append(draft_id)

                file.write(self._format_tracked_draft_entry(league_id, draft_id, league_name, is_active))

        for draft_id in drafts_to_process:
            user_ids = []
            user_id_to_name = {}
            user_id_to_mins_on_clock = {}
            user_id_to_pick_count = {}

            with open(self._get_file_path_for_draft_id(draft_id), "r") as file:
                file_lines = file.readlines()

            # Make the API calls up front
            raw_draft = sleeperApi.get_draft(draft_id)
            raw_draft_picks = sleeperApi.get_all_picks_for_draft(draft_id)
            user_to_draft_spot = raw_draft["draft_order"]
            league_name = raw_draft["metadata"]["name"]

            # Handle new-file/new-league logic
            if len(file_lines) == 0:
                now_mins = self._convert_time_to_minutes(time.time())
                file_lines.append(self._format_last_pick_info(now_mins, 0))
                for user_id, spot in user_to_draft_spot.items():
                    user = sleeperApi.get_user_from_identifier(user_id)
                    file_lines.append(self._format_user_info_for_draft(user_id, user.name, 0, 0))

            # Initialize content lists/maps from the file contents
            split = file_lines[0].split(',')
            last_pick_time = int(split[0])
            last_pick_num = int(split[1])
            for line in file_lines[1:]:
                raw_stat_info = line.split(',')
                user_id = raw_stat_info[0]
                user_ids.append(user_id)
                user_id_to_name[user_id] = raw_stat_info[1]
                user_id_to_mins_on_clock[user_id] = int(raw_stat_info[2])
                user_id_to_pick_count[user_id] = int(raw_stat_info[3])

            # If someone was added to the draft, they're not yet in the file and we need to manually
            # add them before parsing picks
            for user_id, spot in user_to_draft_spot.items():
                if user_id not in user_id_to_name:
                    user = sleeperApi.get_user_from_identifier(user_id)
                    logString = "Adding new user {name} to {league}".format(name=user.name, league=league_name)
                    cogCommon.print_descriptive_log("update_draft_stats", logString)
                    user_ids.append(user_id)
                    user_id_to_name[user_id] = user.name
                    user_id_to_mins_on_clock[user_id] = int(0)
                    user_id_to_pick_count[user_id] = int(0)

            # This means a new pick came in! Time to process some things
            if len(raw_draft_picks) != last_pick_num:
                new_count = len(raw_draft_picks) - last_pick_num
                logString = "{count} new pick{plural} in {league}".format(count=str(new_count), 
                                                                          plural=self._format_pluralization(new_count),
                                                                          league = league_name)
                cogCommon.print_descriptive_log("update_draft_stats", logString)

                # The raw_draft API incloudes the last pick time, but it doesn't appear to update at
                # the same cadence a the raw_draft_picks API, leading to inconsistencies. For now
                # just say the latest pick happened "now""
                latest_pick_time = self._convert_time_to_minutes(time.time())
                time_elapsed = latest_pick_time - last_pick_time

                # Attribute the time spent otc to the right person
                previous_otc = raw_draft_picks[last_pick_num]["picked_by"]

                # Debug logging, remove later
                logString = "{mins} minutes computed before pick by {otc}. Previous {last}, Latest {latest}".format(mins=time_elapsed,
                                                                                                                    otc=user_id_to_name[previous_otc],
                                                                                                                    last=last_pick_time,
                                                                                                                    latest=latest_pick_time)
                cogCommon.print_descriptive_log("update_draft_stats", logString)
                user_id_to_mins_on_clock[previous_otc] = user_id_to_mins_on_clock[previous_otc] + time_elapsed

                # Iterate through all new picks to attribute pick counts
                for pick in raw_draft_picks[last_pick_num:]:
                    picking_user = pick["picked_by"]
                    user_id_to_pick_count[picking_user] = user_id_to_pick_count[picking_user] + 1

                # Save the new "last pick" information
                last_pick_num = len(raw_draft_picks)
                last_pick_time = latest_pick_time

            # Write everything out to the file
            with open(self._get_file_path_for_draft_id(draft_id), "w") as file:
                file.write(self._format_last_pick_info(last_pick_time, last_pick_num))
                for user_id in user_ids:
                    file.write(self._format_user_info_for_draft(user_id,
                                                                user_id_to_name[user_id],
                                                                user_id_to_mins_on_clock[user_id],
                                                                user_id_to_pick_count[user_id]))

    @update_draft_stats.before_loop
    async def before_update_draft_stats(self):
        await self.bot.wait_until_ready()

    @app_commands.command(
        name="get_stats_for_draft",
        description="Retrieves stats for the specified league's draft"
    )
    @app_commands.rename(identifier="username")
    @app_commands.describe(league_name="Some or all of the league name")
    @app_commands.describe(
        identifier="The full Sleeper username of a league member")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def get_stats_for_draft(self, interaction: discord.Interaction, league_name: str, identifier: str, year: int = libCommon.DEFAULT_YEAR):
        cogCommon.print_descriptive_log(
            "get_stats_for_draft",
            "league_name={league_name}, user={username}, year={year}".format(
                league_name=league_name, username=identifier, year=year))
        await interaction.response.defer()

        sleeper = Sleeper()
        league, user, err_string = await asyncio.to_thread(cogCommon.get_matching_sleeper_league, sleeper, league_name, identifier, year)

        if err_string is not None:
            await interaction.followup.send(err_string)
            return

        if not self._is_draft_being_tracked(league):
            cogCommon.print_descriptive_log("get_stats_for_draft", "Untracked draft for {league_name} requested".format(league_name=league.name))
            await interaction.followup.send("{league_name} isn't being tracked.".format(league_name=league.name))
            return

        username_to_average = {}
        username_to_pick_count = {}
        with open(self._get_file_path_for_league(league), "r") as file:
            for line in file.readlines()[1:]:
                raw_stat_info = line.split(',')
                username = raw_stat_info[1]
                time_on_clock = int(raw_stat_info[2])
                pick_count = int(raw_stat_info[3])

                if pick_count == 0:
                    username_to_average[username] = 0
                    username_to_pick_count[username] = 0
                else:
                    average_hours = (time_on_clock / pick_count) / 60.0
                    username_to_average[username] = average_hours
                    username_to_pick_count[username] = pick_count

        response = "__Average Time OTC in {league}__\n".format(league=league.name)
        pick_template = "* `{user:<20}{hours:6.2f} hour{plural}`\n"
        for user in sorted(username_to_average, key=username_to_average.get, reverse=True):
            time = username_to_average[user]
            response += pick_template.format(user=user, hours=time, plural=self._format_pluralization(time))

        cogCommon.print_descriptive_log("get_stats_for_draft", "Done")
        await interaction.followup.send(response)


    def _convert_time_to_minutes(self, epochtime: int) -> int:
        return int(epochtime / 60)

    def _convert_sleeper_time_to_minutes(self, sleepertime: int) -> int:
        return int (sleepertime / 60 / 1000)

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
            file.write(self._create_tracked_draft_entry_from_league(league))

    def _remove_league_from_tracking(self, league: League, delete_data: bool):
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
        if delete_data:
            os.remove(self._get_file_path_for_league(league))
            os.rmdir(self._get_dir_path_for_league(league))

    def _get_file_path_for_league(self, league: League) -> str:
        return self._get_file_path_for_draft_id(league.draft_id)

    def _get_file_path_for_draft_id(self, draft_id: int) -> str:
        return DRAFT_FILE_PATH_TEMPLATE.format(draft_id=str(draft_id))

    def _get_dir_path_for_league(self, league: League) -> str:
        return SPECIFIC_DRAFT_DIRECTORY_PATH_TEMPLATE.format(draft_id=league.draft_id)

    def _create_tracked_draft_entry_from_league(self, league: League) -> str:
        return self._format_tracked_draft_entry(league.league_id, league.draft_id, league.name)

    def _format_tracked_draft_entry(self, league_id: int, draft_id: int, league_name: str, is_active: bool = False) -> str:
        template = "{league_id},{draft_id},{league_name},{is_active}\n"
        return template.format(league_id=league_id, draft_id=draft_id,league_name=league_name,is_active=is_active)

    def _format_last_pick_info(self, timestamp: int, pick_num: int) -> str:
        template = "{timestamp},{pick_num}\n"
        return template.format(timestamp=str(timestamp), pick_num=str(pick_num))

    def _format_user_info_for_draft(self, user_id: str, username: str, mins_on_clock: int, pick_count: int) -> str:
        template = "{user_id},{username},{mins_on_clock},{pick_count}\n"
        return template.format(user_id=user_id,username=username,mins_on_clock=mins_on_clock,pick_count=pick_count)

    def _format_pluralization(self, count: float) -> str:
        return ("s" if count != 1 else "")

async def setup(bot):
    await bot.add_cog(DraftStatsCog(bot))