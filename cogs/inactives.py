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
import os
import re

import cogs.common as cogCommon
import cogs.constants as cogConstants
import cogs.strings as strings
import common
import inactives

from discord import app_commands
from discord.ext import commands
from typing import Dict, List, Set

from library.model.leagueinactivity import LeagueInactivity

INACTIVE_STARTERS_THREAD_CONTENT = "Below is a list of every team that started an \
inactive player this week. When generating this, anyone injured this week or ruled out \
at the last minute should have been ignored."

FTA_LEAGUE_CHANNEL_MAPPING_PATH = "./bot_data/fta_league_channel_mapping"
NARFFL_LEAGUE_CHANNEL_MAPPING_PATH = "./bot_data/narffl_league_channel_mapping"
FF_DISCORD_LEAGUE_CHANNEL_MAPPING_PATH = "./bot_data/ff_discord_league_channel_mapping"

SLEEPER_USERNAME_TO_DISCORD_ID_PATH = "./bot_data/sleeper_username_to_discord_id"
FLEAFLICKER_USERNAME_TO_DISCORD_ID_PATH = "./bot_data/fleaflicker_username_to_discord_id"


class InactivesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Username:Discord mapping commands
    @app_commands.command(
        name="register_sleeper_username",
        description="Connect your Discord and Sleeper usernames for the bot")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def register_sleeper_username(self, interaction: discord.Interaction,
                                        sleeper_username: str):
        await interaction.response.defer()
        author = interaction.user
        cogCommon.print_descriptive_log(
            "register_sleeper_username",
            "{username}: {discord_user}".format(username=sleeper_username,
                                                discord_user=author.name))

        self._write_platform_user_to_discord_id_mapping(
            SLEEPER_USERNAME_TO_DISCORD_ID_PATH, sleeper_username, author)

        await interaction.followup.send(
            "`{username}` has been registered to you.".format(
                username=sleeper_username))

    @app_commands.command(
        name="check_sleeper_registration",
        description=
        "Check the Sleeper username(s) registered to you Discord account")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def check_sleeper_registration(self,
                                         interaction: discord.Interaction):
        await interaction.response.defer()
        author = interaction.user
        cogCommon.print_descriptive_log("check_sleeper_registration",
                                        author.name)

        usernames = self._get_usernames_for_discord_id(
            SLEEPER_USERNAME_TO_DISCORD_ID_PATH, author.id)

        if len(usernames) == 0:
            return_message = "No Sleeper username registered"
        else:
            username_list = self._create_printable_username_list_from_set(
                usernames)
            return_message = "The following Sleeper usernames are registered to you: " + username_list

        cogCommon.print_descriptive_log("check_sleeper_registration", "Done")
        await interaction.followup.send(return_message)

    @app_commands.command(
        name="delete_sleeper_registration",
        description="Delete any Sleeper usernames registered to your account")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def delete_sleeper_registration(self,
                                          interaction: discord.Interaction):
        await interaction.response.defer()
        author = interaction.user
        cogCommon.print_descriptive_log("delete_sleeper_registration",
                                        author.name)

        removedCount = self._remove_username_registration_for_discord_id(
            SLEEPER_USERNAME_TO_DISCORD_ID_PATH, author.id)

        cogCommon.print_descriptive_log("delete_sleeper_registration", "Done")
        await interaction.followup.send(
            "Deleted {count} registration{plural}.".format(
                count=removedCount, plural=("s" if removedCount != 1 else "")))

    @app_commands.command(
        name="register_fleaflicker_username",
        description="Connect your Discord and Fleaflicker usernames for the bot"
    )
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def register_fleaflicker_username(self,
                                            interaction: discord.Interaction,
                                            fleaflicker_username: str):
        await interaction.response.defer()
        author = interaction.user
        cogCommon.print_descriptive_log(
            "register_fleaflicker_username",
            "{username}: {discord_user}".format(username=fleaflicker_username,
                                                discord_user=author.name))

        self._write_platform_user_to_discord_id_mapping(
            FLEAFLICKER_USERNAME_TO_DISCORD_ID_PATH, fleaflicker_username,
            author)

        await interaction.followup.send(
            "{username} has been registered to {discord_user}.".format(
                username=fleaflicker_username, discord_user=author.name))

    @app_commands.command(
        name="check_fleaflicker_registration",
        description=
        "Check the Fleaflicker username(s) registered to you Discord account")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def check_fleaflicker_registration(self,
                                             interaction: discord.Interaction):
        await interaction.response.defer()
        author = interaction.user
        cogCommon.print_descriptive_log("check_fleaflicker_registration",
                                        author.name)

        usernames = self._get_usernames_for_discord_id(
            FLEAFLICKER_USERNAME_TO_DISCORD_ID_PATH, author.id)

        if len(usernames) == 0:
            return_message = "No Fleaflicker username registered"
        else:
            username_list = self._create_printable_username_list_from_set(
                usernames)
            return_message = "The following Fleaflicker usernames are registered to you: " + username_list

        cogCommon.print_descriptive_log("check_fleaflicker_registration",
                                        "Done")
        await interaction.followup.send(return_message)

    @app_commands.command(
        name="delete_fleaflicker_registration",
        description="Delete any Fleaflicker usernames registered to your account"
    )
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def delete_fleaflicker_registration(
            self, interaction: discord.Interaction):
        await interaction.response.defer()
        author = interaction.user
        cogCommon.print_descriptive_log("delete_fleaflicker_registration",
                                        author.name)

        removedCount = self._remove_username_registration_for_discord_id(
            FLEAFLICKER_USERNAME_TO_DISCORD_ID_PATH, author.id)

        cogCommon.print_descriptive_log("delete_fleaflicker_registration",
                                        "Done")
        await interaction.followup.send(
            "Deleted {count} registration{plural}.".format(
                count=removedCount, plural=("s" if removedCount != 1 else "")))

    # Personal Inactivity Commands
    @app_commands.command(
        name="list_inactives_for_sleeper_user",
        description="Looks up all inactive starters for a given user")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def list_inactives_for_sleeper_user(self,
                                              interaction: discord.Interaction,
                                              username: str, week: int):
        cogCommon.print_descriptive_log("list_inactives_for_sleeper_user")
        await interaction.response.defer()

        inactive_leagues = await asyncio.to_thread(
            inactives.get_all_league_inactivity,
            account_identifier=username,
            week=week,
            include_transactions=False,
            user_only=True)

        for league_inactivity in inactive_leagues:
            await interaction.channel.send(
                embed=self._create_embed_for_inactive_league(league_inactivity)
            )

        cogCommon.print_descriptive_log("list_inactives_for_sleeper_user",
                                        "Done")
        await interaction.followup.send("Done!")

    # FTA Inactivity Commands
    @app_commands.command(
        name="fta_inactives_for_select",
        description=
        "Posts FTA rosters with inactive starters from the specified teams")
    @app_commands.describe(
        select_teams="Comma-separated list of NFL team abbreviations")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def fta_inactives_for_select(self, interaction: discord.Interaction,
                                       week: int, select_teams: str):
        cogCommon.print_descriptive_log("fta_inactives_for_select")
        await interaction.response.defer()

        only_teams_list = select_teams.split(",")
        sleeper_username_to_discord_id_mapping = self._create_username_to_discord_id_map(
            SLEEPER_USERNAME_TO_DISCORD_ID_PATH)

        inactive_leagues = await asyncio.to_thread(
            inactives.get_all_league_inactivity,
            account_identifier=cogConstants.FTAFFL_USER,
            week=week,
            include_transactions=False,
            only_teams=only_teams_list)

        for league_inactivity in inactive_leagues:
            channel = self._get_channel_for_league(
                FTA_LEAGUE_CHANNEL_MAPPING_PATH, league_inactivity.league.name)
            if channel is not None:
                message_content = "__**Current Inactive Starters**__"

                mentions_string = self._generate_mentions_string_from_league_inactivity(
                    sleeper_username_to_discord_id_mapping, league_inactivity)
                if mentions_string:
                    message_content += "\n" + mentions_string

                await channel.send(
                    embed=self._create_embed_for_inactive_league(
                        league_inactivity),
                    content=message_content)
            else:
                cogCommon.print_descriptive_log(
                    "fta_inactives_for_select",
                    "Failed to post for league {name}".format(
                        name=league_inactivity.league.name))

        cogCommon.print_descriptive_log("fta_inactives_for_select", "Done")
        await interaction.followup.send("Done!")

    @app_commands.command(
        name="fta_inactives_excluding",
        description=
        "Posts FTA rosters with inactive starters from all but the excluded teams"
    )
    @app_commands.describe(
        excluded_teams="Comma-separated list of NFL team abbreviations")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def fta_inactives_excluding(self, interaction: discord.Interaction,
                                      week: int, excluded_teams: str):
        cogCommon.print_descriptive_log("fta_inactives_excluding")
        await interaction.response.defer()

        teams_to_ignore_list = excluded_teams.split(",")
        sleeper_username_to_discord_id_mapping = self._create_username_to_discord_id_map(
            SLEEPER_USERNAME_TO_DISCORD_ID_PATH)

        inactive_leagues = await asyncio.to_thread(
            inactives.get_all_league_inactivity,
            account_identifier=cogConstants.FTAFFL_USER,
            week=week,
            include_transactions=False,
            teams_to_ignore=teams_to_ignore_list)

        for league_inactivity in inactive_leagues:
            channel = self._get_channel_for_league(
                FTA_LEAGUE_CHANNEL_MAPPING_PATH, league_inactivity.league.name)
            if channel is not None:
                message_content = "__**Current Inactive Starters**__"

                mentions_string = self._generate_mentions_string_from_league_inactivity(
                    sleeper_username_to_discord_id_mapping, league_inactivity)
                if mentions_string:
                    message_content += "\n" + mentions_string

                await channel.send(
                    embed=self._create_embed_for_inactive_league(
                        league_inactivity),
                    content=message_content)
            else:
                cogCommon.print_descriptive_log(
                    "fta_inactives_excluding",
                    "Failed to post for league {name}".format(
                        name=league_inactivity.league.name))

        cogCommon.print_descriptive_log("fta_inactives_excluding", "Done")
        await interaction.followup.send("Done!")

    @app_commands.command(
        name="fta_inactives_to_forum",
        description="Posts all inactives from FTA rosters to the linked forum")
    @app_commands.describe(
        player_names_to_ignore="Comma-separated list of player names")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def fta_inactives_to_forum(self,
                                     interaction: discord.Interaction,
                                     week: int,
                                     forum: discord.ForumChannel,
                                     player_names_to_ignore: str = ""):
        cogCommon.print_descriptive_log("fta_inactives_to_forum")
        await interaction.response.defer()

        player_names_to_ignore_list = player_names_to_ignore.split(",")
        if player_names_to_ignore_list[0] == '':
            player_names_to_ignore_list = []

        inactive_leagues = await asyncio.to_thread(
            inactives.get_all_league_inactivity,
            account_identifier=cogConstants.FTAFFL_USER,
            league_regex_string=cogConstants.FTAFFL_LEAGUE_REGEX,
            week=week,
            include_transactions=True,
            player_names_to_ignore=player_names_to_ignore_list)

        thread_title = "Week {week} Inactive Starters".format(week=str(week))
        thread_content = INACTIVE_STARTERS_THREAD_CONTENT
        if player_names_to_ignore_list:
            thread_content += "\n\n"
            thread_content += "__Players Ignored__\n"
            for player_name in player_names_to_ignore_list:
                thread_content += "- {name}\n".format(name=player_name)

        thread = (await forum.create_thread(name=thread_title,
                                            content=thread_content))[0]
        for league_inactivity in inactive_leagues:
            await thread.send(
                embed=self._create_embed_for_inactive_league(league_inactivity)
            )

        cogCommon.print_descriptive_log("fta_inactives_to_forum", "Done")
        await interaction.followup.send("Done!")

    @app_commands.command(
        name="fta_league_channel_mapping",
        description="Maps league names to their match league channel in Discord"
    )
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def fta_league_channel_mapping(self,
                                         interaction: discord.Interaction,
                                         league_name: str,
                                         channel: discord.TextChannel):
        cogCommon.print_descriptive_log("fta_league_channel_mapping")
        await interaction.response.defer()
        self._write_channel_mapping_for_league(FTA_LEAGUE_CHANNEL_MAPPING_PATH,
                                               league_name, channel)
        await interaction.followup.send(
            "{league} has been mapped to <#{channel_id}>".format(
                league=league_name, channel_id=channel.id))

    # NarFFL Commands
    @app_commands.command(
        name="narffl_inactives_for_select",
        description=
        "Posts NarFFL rosters with inactive starters from the specified teams")
    @app_commands.describe(
        select_teams="Comma-separated list of NFL team abbreviations")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def narffl_inactives_for_select(self,
                                          interaction: discord.Interaction,
                                          week: int, select_teams: str):
        cogCommon.print_descriptive_log("narffl_inactives_for_select")
        await interaction.response.defer()

        only_teams_list = select_teams.split(",")
        fleaflicker_username_to_discord_id_mapping = self._create_username_to_discord_id_map(
            FLEAFLICKER_USERNAME_TO_DISCORD_ID_PATH)

        inactive_leagues = await asyncio.to_thread(
            inactives.get_all_league_inactivity,
            account_identifier=cogConstants.NARFFL_USER,
            week=week,
            include_transactions=False,
            platform_selection=common.PlatformSelection.FLEAFLICKER,
            only_teams=only_teams_list)

        for league_inactivity in inactive_leagues:
            channel = self._get_channel_for_league(
                NARFFL_LEAGUE_CHANNEL_MAPPING_PATH,
                league_inactivity.league.name)
            if channel is not None:
                message_content = "__**Current Inactive Starters**__"

                mentions_string = self._generate_mentions_string_from_league_inactivity(
                    fleaflicker_username_to_discord_id_mapping,
                    league_inactivity)
                if mentions_string:
                    message_content += "\n" + mentions_string

                await channel.send(
                    embed=self._create_embed_for_inactive_league(
                        league_inactivity),
                    content=message_content)
            else:
                cogCommon.print_descriptive_log(
                    "narffl_inactives_for_select",
                    "Failed to post for league {name}".format(
                        name=league_inactivity.league.name))

        cogCommon.print_descriptive_log("narffl_inactives_for_select", "Done")
        await interaction.followup.send("Done!")

    @app_commands.command(
        name="narffl_inactives_excluding",
        description=
        "Posts NarFFL rosters with inactive starters from all but the excluded teams"
    )
    @app_commands.describe(
        excluded_teams="Comma-separated list of NFL team abbreviations")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def narffl_inactives_excluding(self,
                                         interaction: discord.Interaction,
                                         week: int, excluded_teams: str):
        cogCommon.print_descriptive_log("narffl_inactives_excluding")
        await interaction.response.defer()

        teams_to_ignore_list = excluded_teams.split(",")
        fleaflicker_username_to_discord_id_mapping = self._create_username_to_discord_id_map(
            FLEAFLICKER_USERNAME_TO_DISCORD_ID_PATH)

        inactive_leagues = await asyncio.to_thread(
            inactives.get_all_league_inactivity,
            account_identifier=cogConstants.NARFFL_USER,
            week=week,
            include_transactions=False,
            platform_selection=common.PlatformSelection.FLEAFLICKER,
            teams_to_ignore=teams_to_ignore_list)

        for league_inactivity in inactive_leagues:
            channel = self._get_channel_for_league(
                NARFFL_LEAGUE_CHANNEL_MAPPING_PATH,
                league_inactivity.league.name)
            if channel is not None:
                message_content = "__**Current Inactive Starters**__"

                mentions_string = self._generate_mentions_string_from_league_inactivity(
                    fleaflicker_username_to_discord_id_mapping,
                    league_inactivity)
                if mentions_string:
                    message_content += "\n" + mentions_string

                await channel.send(
                    embed=self._create_embed_for_inactive_league(
                        league_inactivity),
                    content=message_content)
            else:
                cogCommon.print_descriptive_log(
                    "narffl_inactives_excluding",
                    "Failed to post for league {name}".format(
                        name=league_inactivity.league.name))

        cogCommon.print_descriptive_log("narffl_inactives_excluding", "Done")
        await interaction.followup.send("Done!")

    @app_commands.command(
        name="narffl_league_channel_mapping",
        description="Maps league names to their match league channel in Discord"
    )
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def narffl_league_channel_mapping(self,
                                            interaction: discord.Interaction,
                                            league_name: str,
                                            channel: discord.TextChannel):
        cogCommon.print_descriptive_log("narffl_league_channel_mapping")
        await interaction.response.defer()
        self._write_channel_mapping_for_league(
            NARFFL_LEAGUE_CHANNEL_MAPPING_PATH, league_name, channel)
        await interaction.followup.send(
            "{league} has been mapped to <#{channel_id}>".format(
                league=league_name, channel_id=channel.id))

    ## FF Discord Commands
    @app_commands.command(
        name="ff_discord_inactives_for_select",
        description=
        "Posts FF Discord rosters with inactive starters from the specified teams"
    )
    @app_commands.describe(
        select_teams="Comma-separated list of NFL team abbreviations")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def ff_discord_inactives_for_select(self,
                                              interaction: discord.Interaction,
                                              week: int, select_teams: str):
        cogCommon.print_descriptive_log("ff_discord_inactives_for_select")
        await interaction.response.defer()

        only_teams_list = select_teams.split(",")
        sleeper_username_to_discord_id_mapping = self._create_username_to_discord_id_map(
            SLEEPER_USERNAME_TO_DISCORD_ID_PATH)

        inactive_leagues = await asyncio.to_thread(
            inactives.get_all_league_inactivity,
            account_identifier=cogConstants.FF_DISCORD_USER,
            week=week,
            include_transactions=False,
            only_teams=only_teams_list)

        for league_inactivity in inactive_leagues:
            channel = self._get_channel_for_league(
                FF_DISCORD_LEAGUE_CHANNEL_MAPPING_PATH,
                league_inactivity.league.name)
            if channel is not None:
                message_content = "__**Current Inactive Starters**__"

                mentions_string = self._generate_mentions_string_from_league_inactivity(
                    sleeper_username_to_discord_id_mapping, league_inactivity)
                if mentions_string:
                    message_content += "\n" + mentions_string

                await channel.send(
                    embed=self._create_embed_for_inactive_league(
                        league_inactivity),
                    content=message_content)
            else:
                cogCommon.print_descriptive_log(
                    "ff_discord_inactives_for_select",
                    "Failed to post for league {name}".format(
                        name=league_inactivity.league.name))

        cogCommon.print_descriptive_log("ff_discord_inactives_for_select",
                                        "Done")
        await interaction.followup.send("Done!")

    @app_commands.command(
        name="ff_discord_inactives_excluding",
        description=
        "Posts FF Discord rosters with inactive starters from all but the excluded teams"
    )
    @app_commands.describe(
        excluded_teams="Comma-separated list of NFL team abbreviations")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def ff_discord_inactives_excluding(self,
                                             interaction: discord.Interaction,
                                             week: int, excluded_teams: str):
        cogCommon.print_descriptive_log("ff_discord_inactives_excluding")
        await interaction.response.defer()

        teams_to_ignore_list = excluded_teams.split(",")
        sleeper_username_to_discord_id_mapping = self._create_username_to_discord_id_map(
            SLEEPER_USERNAME_TO_DISCORD_ID_PATH)

        inactive_leagues = await asyncio.to_thread(
            inactives.get_all_league_inactivity,
            account_identifier=cogConstants.FF_DISCORD_USER,
            week=week,
            include_transactions=False,
            teams_to_ignore=teams_to_ignore_list)

        for league_inactivity in inactive_leagues:
            channel = self._get_channel_for_league(
                FF_DISCORD_LEAGUE_CHANNEL_MAPPING_PATH,
                league_inactivity.league.name)
            if channel is not None:
                message_content = "__**Current Inactive Starters**__"

                mentions_string = self._generate_mentions_string_from_league_inactivity(
                    sleeper_username_to_discord_id_mapping, league_inactivity)
                if mentions_string:
                    message_content += "\n" + mentions_string

                await channel.send(
                    embed=self._create_embed_for_inactive_league(
                        league_inactivity),
                    content=message_content)
            else:
                cogCommon.print_descriptive_log(
                    "ff_discord_inactives_excluding",
                    "Failed to post for league {name}".format(
                        name=league_inactivity.league.name))

        cogCommon.print_descriptive_log("ff_discord_inactives_excluding",
                                        "Done")
        await interaction.followup.send("Done!")

    @app_commands.command(
        name="ff_discord_inactives_to_forum",
        description=
        "Posts all inactives from FF Discord rosters to the linked forum")
    @app_commands.describe(
        player_names_to_ignore="Comma-separated list of player names")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def ff_discord_inactives_to_forum(self,
                                            interaction: discord.Interaction,
                                            week: int,
                                            forum: discord.ForumChannel,
                                            player_names_to_ignore: str = ""):
        cogCommon.print_descriptive_log("post_ff_discord_inactives_to_forum")
        await interaction.response.defer()

        player_names_to_ignore_list = player_names_to_ignore.split(",")
        if player_names_to_ignore_list[0] == '':
            player_names_to_ignore_list = []

        inactive_leagues = await asyncio.to_thread(
            inactives.get_all_league_inactivity,
            account_identifier=cogConstants.FF_DISCORD_USER,
            week=week,
            include_transactions=True,
            player_names_to_ignore=player_names_to_ignore_list)

        thread_title = "Week {week} Inactive Starters".format(week=str(week))
        thread_content = INACTIVE_STARTERS_THREAD_CONTENT
        if player_names_to_ignore_list:
            thread_content += "\n\n"
            thread_content += "__Players Ignored__\n"
            for player_name in player_names_to_ignore_list:
                thread_content += "- {name}\n".format(name=player_name)

        thread = (await forum.create_thread(name=thread_title,
                                            content=thread_content))[0]
        for league_inactivity in inactive_leagues:
            await thread.send(
                embed=self._create_embed_for_inactive_league(league_inactivity)
            )

        cogCommon.print_descriptive_log("post_ff_discord_inactives_to_forum",
                                        "Done")
        await interaction.followup.send("Done!")

    @app_commands.command(
        name="ff_disc_league_channel_mapping",
        description="Maps league names to their match league channel in Discord"
    )
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def ff_disc_league_channel_mapping(self,
                                             interaction: discord.Interaction,
                                             league_name: str,
                                             channel: discord.TextChannel):
        cogCommon.print_descriptive_log("ff_disc_league_channel_mapping")
        await interaction.response.defer()
        self._write_channel_mapping_for_league(
            FF_DISCORD_LEAGUE_CHANNEL_MAPPING_PATH, league_name, channel)
        await interaction.followup.send(
            "{league} has been mapped to <#{channel_id}>".format(
                league=league_name, channel_id=channel.id))

    # Helpers
    def _create_embed_for_inactive_league(
            self, league_inactivity: LeagueInactivity) -> discord.Embed:
        embed = discord.Embed(colour=discord.Colour.red(),
                              title=league_inactivity.league.name)

        last_transaction_template = "_Last transaction: {date}_\n"
        date_format = "%m-%d-%Y"
        player_template = "{name}, {position} - {status}\n"

        for roster in league_inactivity.rosters:
            embed_value = "[Current Roster]({roster_link})\n".format(
                roster_link=roster.team.roster_link)
            if roster.last_transaction is not None:
                embed_value += last_transaction_template.format(
                    date=roster.last_transaction.time.strftime(date_format))
            for player in roster.inactive_players:
                embed_value += player_template.format(name=player.name,
                                                      position=player.position,
                                                      status=player.status)
            embed.add_field(name=roster.team.manager.name,
                            value=embed_value,
                            inline=False)

        return embed

    def _create_file_string_for_league_and_channel(
            self, league_name: str, channel: discord.TextChannel) -> str:
        output_list = []
        output_list.append(league_name)
        output_list.append(str(channel.id))
        output_list.append(channel.name)

        return ",".join(output_list)

    def _write_channel_mapping_for_league(self, filename: str,
                                          league_name: str,
                                          channel: discord.TextChannel):
        if os.path.isfile(filename):
            file = open(filename, "a")
        else:
            file = open(filename, "w")

        file.write(
            self._create_file_string_for_league_and_channel(
                league_name, channel) + "\n")
        file.close()

    def _get_channel_for_league(self, filename: str,
                                league_name: str) -> discord.TextChannel:
        channel_id = None

        if os.path.isfile(filename):
            file = open(filename, "r")
            lines = file.readlines()
            for line in lines:
                line_split = line.split(",")
                if line_split[0] == league_name:
                    channel_id = line_split[1]
                    break
            file.close()
        else:
            return None

        if channel_id is None:
            return None
        return self.bot.get_channel(int(channel_id))

    def _create_discord_mention_from_id(self, discord_id: str) -> str:
        return "<@{id}>".format(id=discord_id)

    def _generate_mentions_string_from_league_inactivity(
            self, username_to_discord_id_mapping: Dict[str, Set[str]],
            league_inactivity: LeagueInactivity) -> str:
        mentions_string = ""

        for roster in league_inactivity.rosters:
            username = roster.team.manager.name

            if username in username_to_discord_id_mapping:
                discord_users = username_to_discord_id_mapping[username]
                for id in discord_users:
                    mentions_string += self._create_discord_mention_from_id(
                        id) + " "

        return mentions_string

    def _write_platform_user_to_discord_id_mapping(self, filename: str,
                                                   platform_id: str,
                                                   discord_user: discord.User):
        if os.path.isfile(filename):
            file = open(filename, "a")
        else:
            file = open(filename, "w")

        file.write("{platform},{discord_id},{discord_name}\n".format(
            platform=platform_id.lower(),
            discord_id=discord_user.id,
            discord_name=discord_user.name))

    def _create_username_to_discord_id_map(
            self, filename: str) -> Dict[str, Set[str]]:
        result = {}

        if os.path.isfile(filename):
            file = open(filename, "r")
            lines = file.readlines()
            for line in lines:
                line_split = line.split(",")
                username = line_split[0]

                if username not in result:
                    result[username] = set()

                result[username].add(line_split[1].strip())

            file.close()

        return result

    def _get_usernames_for_discord_id(self, filename: str,
                                      discord_id: int) -> Set[str]:
        usernames = set()

        if os.path.isfile(filename):
            file = open(filename, "r")

            lines = file.readlines()
            for line in lines:
                line_split = line.split(",")
                d_id = str(line_split[1].strip())

                if d_id == str(discord_id):
                    usernames.add(line_split[0])

            file.close()

        return usernames

    def _create_printable_username_list_from_set(self, usernames: Set) -> str:
        username_list = ""
        for name in usernames:
            if not len(username_list) == 0:
                username_list += ","
            username_list += "`" + name + "`"

        return username_list

    def _remove_username_registration_for_discord_id(self, filename: str,
                                                     discord_id: int) -> int:
        discord_id_regex = re.compile(
            ".*,{discord_id},.*".format(discord_id=str(discord_id)))
        removed_count = 0

        with open(filename, "r+") as file:
            lines = file.readlines()
            file.seek(0)
            file.truncate()

            for line in lines:
                if not discord_id_regex.match(line):
                    file.write(line)
                else:
                    cogCommon.print_descriptive_log(
                        "_remove_username_registration_for_discord_id",
                        "Removing line: {line}".format(line=line.strip()))
                    removed_count += 1

        return removed_count


async def setup(bot):
    await bot.add_cog(InactivesCog(bot))
