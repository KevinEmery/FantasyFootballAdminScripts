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

import adp
import cogs.common as cogCommon
import cogs.constants as cogConstants
import cogs.strings as strings
import common

from datetime import datetime
from discord import app_commands
from discord.ext import commands
from typing import List

# Actual limit is 25, we want to steer clear in case we add fields on top of the iteration
EMBED_FIELD_LIMIT = 20

# These colors mirror the Sleeper draft board
ALL_PLAYERS_COLOR = discord.Colour.dark_blue()
QB_COLOR = discord.Colour.from_rgb(192, 94, 133)
RB_COLOR = discord.Colour.from_rgb(115, 195, 166)
WR_COLOR = discord.Colour.from_rgb(70, 162, 202)
TE_COLOR = discord.Colour.from_rgb(204, 140, 74)
K_COLOR = discord.Colour.purple()
DEF_COLOR = discord.Colour.from_rgb(154, 95, 78)


class ADPCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # FTA Commands
    @app_commands.command(name="send_all_fta_adp_posts",
                          description="Creates all of the FTA ADP Forum posts")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def send_all_fta_adp_posts(self, interaction: discord.Interaction,
                                     forum: discord.ForumChannel):
        cogCommon.print_descriptive_log("send_all_fta_adp_posts",
                                        "Posting to " + forum.name + " forum")

        await interaction.response.defer()
        await self._post_fta_position_adp(forum, "DEF", "Team Defense",
                                          DEF_COLOR)
        await self._post_fta_position_adp(forum, "K", "Kicker", K_COLOR)
        await self._post_fta_position_adp(forum, "TE", "Tight End", TE_COLOR)
        await self._post_fta_position_adp(forum, "WR", "Wide Receiver",
                                          WR_COLOR)
        await self._post_fta_position_adp(forum, "RB", "Running Back",
                                          RB_COLOR)
        await self._post_fta_position_adp(forum, "QB", "Quarterback", QB_COLOR)
        await self._post_fta_position_adp(forum, adp.INCLUDE_ALL,
                                          "All Players", ALL_PLAYERS_COLOR)

        cogCommon.print_descriptive_log("send_all_fta_adp_posts", "Done")
        await interaction.followup.send("Done!")

    @app_commands.command(name="post_fta_overall_adp",
                          description="Posts the FTA ADP for all positions")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def post_fta_overall_adp(self, interaction: discord.Interaction,
                                   forum: discord.ForumChannel):
        cogCommon.print_descriptive_log("post_fta_overall_adp",
                                        "Posting to " + forum.name + " forum")
        await interaction.response.defer()

        await self._post_fta_position_adp(forum, adp.INCLUDE_ALL,
                                          "All Players", ALL_PLAYERS_COLOR)

        cogCommon.print_descriptive_log("post_fta_overall_adp", "Done")
        await interaction.followup.send("Done!")

    @app_commands.command(name="post_fta_qb_adp",
                          description="Posts the FTA ADP for QBs")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def post_fta_qb_adp(self, interaction: discord.Interaction,
                              forum: discord.ForumChannel):
        cogCommon.print_descriptive_log("post_fta_qb_adp",
                                        "Posting to " + forum.name + " forum")
        await interaction.response.defer()

        await self._post_fta_position_adp(forum, "QB", "Quarterback", QB_COLOR)

        cogCommon.print_descriptive_log("post_fta_qb_adp", "Done")
        await interaction.followup.send("Done!")

    @app_commands.command(name="post_fta_wr_adp",
                          description="Posts the FTA ADP for WRs")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def post_fta_wr_adp(self, interaction: discord.Interaction,
                              forum: discord.ForumChannel):
        cogCommon.print_descriptive_log("post_fta_wr_adp",
                                        "Posting to " + forum.name + " forum")
        await interaction.response.defer()

        await self._post_fta_position_adp(forum, "WR", "Wide Receiver",
                                          WR_COLOR)

        cogCommon.print_descriptive_log("post_fta_wr_adp", "Done")
        await interaction.followup.send("Done!")

    @app_commands.command(name="post_fta_rb_adp",
                          description="Posts the FTA ADP for RBs")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def post_fta_rb_adp(self, interaction: discord.Interaction,
                              forum: discord.ForumChannel):
        cogCommon.print_descriptive_log("post_fta_rb_adp",
                                        "Posting to " + forum.name + " forum")
        await interaction.response.defer()

        await self._post_fta_position_adp(forum, "RB", "Running Back",
                                          RB_COLOR)

        cogCommon.print_descriptive_log("post_fta_rb_adp", "Done")
        await interaction.followup.send("Done!")

    @app_commands.command(name="post_fta_te_adp",
                          description="Posts the FTA ADP for TEs")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def post_fta_te_adp(self, interaction: discord.Interaction,
                              forum: discord.ForumChannel):
        cogCommon.print_descriptive_log("post_fta_te_adp",
                                        "Posting to " + forum.name + " forum")
        await interaction.response.defer()

        await self._post_fta_position_adp(forum, "TE", "Tight End", TE_COLOR)

        cogCommon.print_descriptive_log("post_fta_te_adp", "Done")
        await interaction.followup.send("Done!")

    @app_commands.command(name="post_fta_k_adp",
                          description="Posts the FTA ADP for Ks")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def post_fta_k_adp(self, interaction: discord.Interaction,
                             forum: discord.ForumChannel):
        cogCommon.print_descriptive_log("post_fta_k_adp",
                                        "Posting to " + forum.name + " forum")
        await interaction.response.defer()

        await self._post_fta_position_adp(forum, "K", "Kicker", K_COLOR)

        cogCommon.print_descriptive_log("post_fta_k_adp", "Done")
        await interaction.followup.send("Done!")

    @app_commands.command(name="post_fta_dst_adp",
                          description="Posts the FTA ADP for DSTs")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def post_fta_dst_adp(self, interaction: discord.Interaction,
                               forum: discord.ForumChannel):
        cogCommon.print_descriptive_log("post_fta_dst_adp",
                                        "Posting to " + forum.name + " forum")
        await interaction.response.defer()

        await self._post_fta_position_adp(forum, "DEF", "Team Defense",
                                          DEF_COLOR)

        cogCommon.print_descriptive_log("post_fta_dst_adp", "Done")
        await interaction.followup.send("Done!")

    # NarFFL Commands
    @app_commands.command(
        name="send_all_narffl_adp_posts",
        description="Creates all of the NarFFL ADP Forum posts")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def send_all_narffl_adp_posts(self, interaction: discord.Interaction,
                                        forum: discord.ForumChannel):
        cogCommon.print_descriptive_log("send_all_narffl_adp_posts",
                                        "Posting to " + forum.name + " forum")

        await interaction.response.defer()
        await self._post_narffl_position_adp(forum, "DEF", "Team Defense",
                                             DEF_COLOR)
        await self._post_narffl_position_adp(forum, "K", "Kicker", K_COLOR)
        await self._post_narffl_position_adp(forum, "TE", "Tight End",
                                             TE_COLOR)
        await self._post_narffl_position_adp(forum, "WR", "Wide Receiver",
                                             WR_COLOR)
        await self._post_narffl_position_adp(forum, "RB", "Running Back",
                                             RB_COLOR)
        await self._post_narffl_position_adp(forum, "QB", "Quarterback",
                                             QB_COLOR)
        await self._post_narffl_position_adp(forum, adp.INCLUDE_ALL,
                                             "All Players", ALL_PLAYERS_COLOR)

        cogCommon.print_descriptive_log("send_all_narffl_adp_posts", "Done")
        await interaction.followup.send("Done!")

    @app_commands.command(name="post_narffl_overall_adp",
                          description="Posts the NarFFL ADP for all positions")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def post_narffl_overall_adp(self, interaction: discord.Interaction,
                                      forum: discord.ForumChannel):
        cogCommon.print_descriptive_log("post_narffl_overall_adp",
                                        "Posting to " + forum.name + " forum")
        await interaction.response.defer()

        await self._post_narffl_position_adp(forum, adp.INCLUDE_ALL,
                                             "All Players", ALL_PLAYERS_COLOR)

        cogCommon.print_descriptive_log("post_narffl_overall_adp", "Done")
        await interaction.followup.send("Done!")

    @app_commands.command(name="post_narffl_qb_adp",
                          description="Posts the NarFFL ADP for QBs")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def post_narffl_qb_adp(self, interaction: discord.Interaction,
                                 forum: discord.ForumChannel):
        cogCommon.print_descriptive_log("post_narffl_qb_adp",
                                        "Posting to " + forum.name + " forum")
        await interaction.response.defer()

        await self._post_narffl_position_adp(forum, "QB", "Quarterback",
                                             QB_COLOR)

        cogCommon.print_descriptive_log("post_narffl_qb_adp", "Done")
        await interaction.followup.send("Done!")

    @app_commands.command(name="post_narffl_wr_adp",
                          description="Posts the NarFFL ADP for WRs")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def post_narffl_wr_adp(self, interaction: discord.Interaction,
                                 forum: discord.ForumChannel):
        cogCommon.print_descriptive_log("post_narffl_wr_adp",
                                        "Posting to " + forum.name + " forum")
        await interaction.response.defer()

        await self._post_narffl_position_adp(forum, "WR", "Wide Receiver",
                                             WR_COLOR)

        cogCommon.print_descriptive_log("post_narffl_wr_adp", "Done")
        await interaction.followup.send("Done!")

    @app_commands.command(name="post_narffl_rb_adp",
                          description="Posts the NarFFL ADP for RBs")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def post_narffl_rb_adp(self, interaction: discord.Interaction,
                                 forum: discord.ForumChannel):
        cogCommon.print_descriptive_log("post_narffl_rb_adp",
                                        "Posting to " + forum.name + " forum")
        await interaction.response.defer()

        await self._post_narffl_position_adp(forum, "RB", "Running Back",
                                             RB_COLOR)

        cogCommon.print_descriptive_log("post_narffl_rb_adp", "Done")
        await interaction.followup.send("Done!")

    @app_commands.command(name="post_narffl_te_adp",
                          description="Posts the NarFFL ADP for TEs")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def post_narffl_te_adp(self, interaction: discord.Interaction,
                                 forum: discord.ForumChannel):
        cogCommon.print_descriptive_log("post_narffl_te_adp",
                                        "Posting to " + forum.name + " forum")
        await interaction.response.defer()

        await self._post_narffl_position_adp(forum, "TE", "Tight End",
                                             TE_COLOR)

        cogCommon.print_descriptive_log("post_narffl_te_adp", "Done")
        await interaction.followup.send("Done!")

    @app_commands.command(name="post_narffl_k_adp",
                          description="Posts the NarFFL ADP for Ks")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def post_narffl_k_adp(self, interaction: discord.Interaction,
                                forum: discord.ForumChannel):
        cogCommon.print_descriptive_log("post_narffl_k_adp",
                                        "Posting to " + forum.name + " forum")
        await interaction.response.defer()

        await self._post_narffl_position_adp(forum, "K", "Kicker", K_COLOR)

        cogCommon.print_descriptive_log("post_narffl_k_adp", "Done")
        await interaction.followup.send("Done!")

    @app_commands.command(name="post_narffl_dst_adp",
                          description="Posts the NarFFL ADP for DSTs")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def post_narffl_dst_adp(self, interaction: discord.Interaction,
                                  forum: discord.ForumChannel):
        cogCommon.print_descriptive_log("post_narffl_dst_adp",
                                        "Posting to " + forum.name + " forum")
        await interaction.response.defer()

        await self._post_narffl_position_adp(forum, "D/ST", "Team Defense",
                                             DEF_COLOR)

        cogCommon.print_descriptive_log("post_narffl_dst_adp", "Done")
        await interaction.followup.send("Done!")

    # Helpers
    async def _post_position_adp_data(self, forum: discord.ForumChannel,
                                      adp_data: List[str], position_long: str,
                                      embed_color: discord.Colour,
                                      thread_content: str):
        messages = self._break_adp_content_into_messages(adp_data, embed_color)
        thread_title = self._get_formatted_date() + ": " + position_long
        thread = (await forum.create_thread(name=thread_title,
                                            content=thread_content))[0]
        for message in messages:
            await thread.send(embed=message)

    def _break_adp_content_into_messages(
            self, content: List[str],
            embed_color: discord.Colour) -> List[discord.Embed]:
        split_content = []
        current_embed = discord.Embed(colour=embed_color)

        for line in content:
            if (len(current_embed.fields) >= EMBED_FIELD_LIMIT):
                split_content.append(current_embed)
                current_embed = discord.Embed(colour=embed_color)
            self._convert_adp_csv_to_embed_field(line, current_embed)

        if len(current_embed.fields) > 0:
            split_content.append(current_embed)

        return split_content

    def _convert_adp_csv_to_embed_field(self, content: str,
                                        embed: discord.Embed):
        player_data = content.split(",")
        template = "`Av: {adp:<5} Min: {min:<5} Max: {max:<5} ({n})`"
        embed.add_field(name=player_data[0],
                        value=template.format(n=player_data[4],
                                              adp=player_data[1],
                                              min=player_data[2],
                                              max=player_data[3]),
                        inline=False)

    def _get_formatted_date(self) -> str:
        now = datetime.now()
        return now.strftime("%m/%d/%y")

    async def _post_fta_position_adp(self, forum: discord.ForumChannel,
                                     position_short: str, position_long: str,
                                     embed_color: discord.Colour):
        adp_data = await asyncio.to_thread(
            adp.aggregate_adp_data,
            account_identifier=cogConstants.FTAFFL_USER,
            league_size=14,
            position=position_short,
            league_regex_string=cogConstants.FTAFFL_LEAGUE_REGEX,
            output_format=adp.OutputFormat.FORMATTED_CSV)
        await self._post_position_adp_data(
            forum, adp_data, position_long, embed_color,
            strings.FTA_ADP_THREAD_CONTENT + strings.ADP_GLOSSARY)

    async def _post_narffl_position_adp(self, forum: discord.ForumChannel,
                                        position_short: str,
                                        position_long: str,
                                        embed_color: discord.Colour):
        adp_data = await asyncio.to_thread(
            adp.aggregate_adp_data,
            account_identifier=cogConstants.NARFFL_USER,
            league_size=12,
            position=position_short,
            output_format=adp.OutputFormat.FORMATTED_CSV,
            platform_selection=common.PlatformSelection.FLEAFLICKER)
        await self._post_position_adp_data(
            forum, adp_data, position_long, embed_color,
            strings.NARFFL_ADP_THREAD_CONTENT + strings.ADP_GLOSSARY)


async def setup(bot):
    await bot.add_cog(ADPCog(bot))
