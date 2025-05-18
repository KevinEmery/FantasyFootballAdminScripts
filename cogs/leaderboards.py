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

import cogs.common as cogCommon
import cogs.constants as cogConstants
import cogs.strings as strings
import common
import leaguescoring
import topleaguescore

from discord import app_commands
from discord.ext import commands
from typing import List

from library.model.seasonscore import SeasonScore
from library.model.weeklyscore import WeeklyScore


class LeaderboardsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # FTA commands
    @app_commands.command(
        name="post_fta_leaderboard",
        description=
        "Posts the combined FTA leaderboard with a top summary and then expanded info in the thread"
    )
    @app_commands.guilds(cogConstants.FTA_SERVER_GUILD_ID,
                         cogConstants.DEV_SERVER_GUILD_ID)
    async def post_fta_leaderboard(self, interaction: discord.Interaction,
                                   end_week: int, forum: discord.ForumChannel):
        cogCommon.print_descriptive_log("post_fta_leaderboard")
        await interaction.response.defer()

        main_leaderboard_length = 5
        expanded_leaderboard_length = 15
        scoring_results = await asyncio.to_thread(
            leaguescoring.get_scoring_results,
            account_identifier=cogConstants.FTAFFL_USER,
            starting_week=1,
            ending_week=end_week,
            get_weekly_results=True,
            get_current_weeks_results=True,
            get_season_results=True,
            get_max_scores=True,
            get_min_scores=False,
            league_regex_string=cogConstants.FTAFFL_LEAGUE_REGEX)

        # Build the main leaderboard for the thread content
        thread_title = "Week {week} Leaderboard".format(week=end_week)

        thread_content = strings.FTA_LEADERBARD_MAIN_POST_CONTENT_HEADER
        thread_content += self._build_season_long_leaderboard_string(
            scoring_results.max_season_scores, main_leaderboard_length) + "\n"
        thread_content += self._build_weekly_score_leaderboard_string(
            scoring_results.max_weekly_scores, 1,
            "__Top Single-Week Scorer__\n") + "\n"
        thread_content += "\nFor the expanded leaderboards, please see the messages below. Good luck everyone!"

        # Create the forum thread
        thread = (await forum.create_thread(name=thread_title,
                                            content=thread_content))[0]

        # Send the expanded leaderboards as followup messages
        message = self._build_season_long_leaderboard_string(
            scoring_results.max_season_scores, expanded_leaderboard_length)
        await thread.send(content=message)

        message = self._build_weekly_score_leaderboard_string(
            scoring_results.max_weekly_scores, expanded_leaderboard_length,
            "__Top {count} Single-Week Scorers__\n".format(
                count=expanded_leaderboard_length))
        await thread.send(content=message)

        message = self._build_weekly_score_leaderboard_string(
            scoring_results.max_scores_this_week, expanded_leaderboard_length,
            "__Top {count} Week {week} Scorers__\n".format(
                count=expanded_leaderboard_length, week=end_week))
        await thread.send(content=message)

        cogCommon.print_descriptive_log("post_fta_leaderboard", "Done")
        await interaction.followup.send(
            "Leaderboard posted to <#{forum_id}> for Week {week}".format(
                forum_id=forum.id, week=end_week))

    # NarFFL Commands
    @app_commands.command(name="send_all_narffl_leaderboards",
                          description="Posts each of the NarFFL leaderboards")
    @app_commands.guilds(cogConstants.NARFFL_SERVER_GUILD_ID,
                         cogConstants.DEV_SERVER_GUILD_ID)
    async def send_all_narffl_leaderboards(self,
                                           interaction: discord.Interaction,
                                           end_week: int,
                                           forum: discord.ForumChannel):
        cogCommon.print_descriptive_log(
            "send_all_narffl_leaderboards",
            "Posting to {forum}".format(forum=forum.name))
        await interaction.response.defer()

        await asyncio.gather(
            await asyncio.to_thread(self._post_specific_narffl_leaderboard,
                                    "Farm",
                                    cogConstants.NARFFL_FARM_LEAGUE_REGEX,
                                    end_week, forum), await
            asyncio.to_thread(self._post_narffl_top_farm_scores_leaderboard,
                              end_week, forum), await
            asyncio.to_thread(self._post_specific_narffl_leaderboard, "Minors",
                              cogConstants.NARFFL_MINORS_LEAGUE_REGEX,
                              end_week, forum), await
            asyncio.to_thread(self._post_specific_narffl_leaderboard, "Majors",
                              cogConstants.NARFFL_MAJORS_LEAGUE_REGEX,
                              end_week, forum), await
            asyncio.to_thread(self._post_specific_narffl_leaderboard,
                              "Premier",
                              cogConstants.NARFFL_PREMIER_LEAGUE_REGEX,
                              end_week, forum), await
            asyncio.to_thread(self._post_narffl_overall_leaderboard, end_week,
                              forum))

        cogCommon.print_descriptive_log("send_all_narffl_leaderboards", "Done")
        await interaction.followup.send(
            "NarFFL leaderboards posted to <#{forum_id}> for Week {week}".
            format(forum_id=forum.id, week=end_week))

    @app_commands.command(
        name="post_narffl_top_farm_scores",
        description=
        "Posts the leaderboard for the top weekly score in each Farm league")
    @app_commands.guilds(cogConstants.NARFFL_SERVER_GUILD_ID,
                         cogConstants.DEV_SERVER_GUILD_ID)
    async def post_narffl_top_farm_scores(self,
                                          interaction: discord.Interaction,
                                          end_week: int,
                                          forum: discord.ForumChannel):
        cogCommon.print_descriptive_log(
            "post_narffl_top_farm_scores",
            "Posting to {forum}".format(forum=forum.name))
        await interaction.response.defer()

        await self._post_narffl_top_farm_scores_leaderboard(end_week, forum)

        cogCommon.print_descriptive_log("post_narffl_top_farm_scores", "Done")
        await interaction.followup.send(
            "Top Weekly Farm scores posted to <#{forum_id}> for Week {week}".
            format(forum_id=forum.id, week=end_week))

    @app_commands.command(name="post_narffl_farm_leaderboard",
                          description="Posts the weekly Farm leaderboard")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def post_narffl_farm_leaderboard(self,
                                           interaction: discord.Interaction,
                                           end_week: int,
                                           forum: discord.ForumChannel):
        cogCommon.print_descriptive_log(
            "post_narffl_farm_leaderboard",
            "Posting to {forum}".format(forum=forum.name))
        await interaction.response.defer()

        await self._post_specific_narffl_leaderboard(
            "Farm", cogConstants.NARFFL_FARM_LEAGUE_REGEX, end_week, forum)

        cogCommon.print_descriptive_log("post_narffl_farm_leaderboard", "Done")
        await interaction.followup.send(
            "Farm leaderboard posted to <#{forum_id}> for Week {week}".format(
                forum_id=forum.id, week=end_week))

    @app_commands.command(name="post_narffl_minors_leaderboard",
                          description="Posts the weekly Minors leaderboard")
    @app_commands.guilds(cogConstants.NARFFL_SERVER_GUILD_ID,
                         cogConstants.DEV_SERVER_GUILD_ID)
    async def post_narffl_minors_leaderboard(self,
                                             interaction: discord.Interaction,
                                             end_week: int,
                                             forum: discord.ForumChannel):
        cogCommon.print_descriptive_log(
            "post_narffl_minors_leaderboard",
            "Posting to {forum}".format(forum=forum.name))
        await interaction.response.defer()

        await self._post_specific_narffl_leaderboard(
            "Minors", cogConstants.NARFFL_MINORS_LEAGUE_REGEX, end_week, forum)

        cogCommon.print_descriptive_log("post_narffl_minors_leaderboard",
                                        "Done")
        await interaction.followup.send(
            "Minors leaderboard posted to <#{forum_id}> for Week {week}".
            format(forum_id=forum.id, week=end_week))

    @app_commands.command(name="post_narffl_majors_leaderboard",
                          description="Posts the weekly Majors leaderboard")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def post_narffl_majors_leaderboard(self,
                                             interaction: discord.Interaction,
                                             end_week: int,
                                             forum: discord.ForumChannel):
        cogCommon.print_descriptive_log(
            "post_narffl_majors_leaderboard",
            "Posting to {forum}".format(forum=forum.name))
        await interaction.response.defer()

        await self._post_specific_narffl_leaderboard(
            "Majors", cogConstants.NARFFL_MAJORS_LEAGUE_REGEX, end_week, forum)

        cogCommon.print_descriptive_log("post_narffl_majors_leaderboard",
                                        "Done")
        await interaction.followup.send(
            "Majors leaderboard posted to <#{forum_id}> for Week {week}".
            format(forum_id=forum.id, week=end_week))

    @app_commands.command(name="post_narffl_premier_leaderboard",
                          description="Posts the weekly Premier leaderboard")
    @app_commands.guilds(cogConstants.NARFFL_SERVER_GUILD_ID,
                         cogConstants.DEV_SERVER_GUILD_ID)
    async def post_narffl_premier_leaderboard(self,
                                              interaction: discord.Interaction,
                                              end_week: int,
                                              forum: discord.ForumChannel):
        cogCommon.print_descriptive_log(
            "post_narffl_premier_leaderboard",
            "Posting to {forum}".format(forum=forum.name))
        await interaction.response.defer()

        await self._post_specific_narffl_leaderboard(
            "Premier", cogConstants.NARFFL_PREMIER_LEAGUE_REGEX, end_week,
            forum)

        cogCommon.print_descriptive_log("post_narffl_premier_leaderboard",
                                        "Done")
        await interaction.followup.send(
            "Premier leaderboard posted to <#{forum_id}> for Week {week}".
            format(forum_id=forum.id, week=end_week))

    @app_commands.command(
        name="post_narffl_overall_leaderboard",
        description="Posts the weekly leaderboard across all NarFFL leagues")
    @app_commands.guilds(cogConstants.NARFFL_SERVER_GUILD_ID,
                         cogConstants.DEV_SERVER_GUILD_ID)
    async def post_narffl_overall_leaderboard(self,
                                              interaction: discord.Interaction,
                                              end_week: int,
                                              forum: discord.ForumChannel):
        cogCommon.print_descriptive_log(
            "post_narffl_overall_leaderboard",
            "Posting to {forum}".format(forum=forum.name))
        await interaction.response.defer()

        await self._post_narffl_overall_leaderboard(end_week, forum)

        cogCommon.print_descriptive_log("post_narffl_overall_leaderboard",
                                        "Done")
        await interaction.followup.send(
            "Overall leaderboard posted to <#{forum_id}> for Week {week}".
            format(forum_id=forum.id, week=end_week))

    @app_commands.command(
        name="post_ff_discord_leaderboard",
        description="Posts the FF Discord leaderboard with a link to the website"
    )
    @app_commands.guilds(cogConstants.FF_DISCORD_SERVER_GUILD_ID,
                         cogConstants.DEV_SERVER_GUILD_ID)
    async def post_ff_discord_leaderboard(self,
                                          interaction: discord.Interaction,
                                          end_week: int,
                                          channel: discord.TextChannel):
        cogCommon.print_descriptive_log(
            "post_ff_discord_leaderboard",
            "Posting to {channel}".format(channel=channel.name))
        await interaction.response.defer()

        leaderboard_length = 5
        scoring_results = await asyncio.to_thread(
            leaguescoring.get_scoring_results,
            account_identifier=cogConstants.FF_DISCORD_USER,
            starting_week=1,
            ending_week=end_week,
            get_weekly_results=False,
            get_current_weeks_results=True,
            get_season_results=True,
            get_max_scores=True,
            get_min_scores=False)

        post_content = "## Week {week} Leaderboard\n\n\n".format(week=end_week)

        post_content += self._build_season_long_leaderboard_string(
            scoring_results.max_season_scores, leaderboard_length) + "\n"
        post_content += self._build_weekly_score_leaderboard_string(
            scoring_results.max_scores_this_week, leaderboard_length,
            "__Top {count} Week {week} Scores__\n".format(
                count=leaderboard_length, week=end_week)) + "\n"

        post_content += "Full standings at https://www.flexspotff.com/leagues/leaderboard/2025/{week}".format(
            week=end_week)

        await channel.send(content=post_content)

        cogCommon.print_descriptive_log("post_ff_discord_leaderboard", "Done")
        await interaction.followup.send(
            "Leaderboard posted to <#{channel_id}> for Week {week}".format(
                channel_id=channel.id, week=end_week))

    # Generic Leaderboard Helpers

    def _build_season_long_leaderboard_string(
            self,
            scores: List[SeasonScore],
            count: int,
            league_prefix_to_remove: str = "") -> str:
        string = "__Top {count} Season-Long Scorers__\n".format(count=count)

        for n in range(count):
            result = scores[n]
            league_name = result.league.name.removeprefix(
                league_prefix_to_remove)
            string += strings.LEADERBOARD_SEASON_SCORE_TEAM_TEMPLATE.format(
                rank=n + 1,
                team_name=result.team.manager.name,
                league=league_name,
                score=result.score,
                roster_link=result.team.roster_link)

        return string

    def _build_weekly_score_leaderboard_string(
            self,
            scores: List[WeeklyScore],
            count: int,
            title: str,
            league_prefix_to_remove: str = ""):
        string = title
        for n in range(count):
            result = scores[n]
            league_name = result.league.name.removeprefix(
                league_prefix_to_remove)
            string += strings.LEADERBOARD_WEEKLY_SCORE_TEAM_TEMPLATE.format(
                rank=n + 1,
                team_name=result.team.manager.name,
                league=league_name,
                score=result.score,
                roster_link=result.team.roster_link,
                week=str(result.week))

        return string

    def _build_unordered_weekly_score_leaderboard_string(
            self,
            scores: List[WeeklyScore],
            count: int,
            title: str = "",
            league_prefix_to_remove: str = ""):
        string = title
        for n in range(count):
            result = scores[n]
            league_name = result.league.name.removeprefix(
                league_prefix_to_remove)
            string += strings.LEADERBOARD_UNORDERED_WEEKLY_SCORE_TEMPLATE.format(
                team_name=result.team.manager.name,
                league=league_name,
                score=result.score,
                roster_link=result.team.roster_link,
                week=str(result.week))

        return string

    # NarFFL helpers

    async def _post_specific_narffl_leaderboard(self, league_level: str,
                                                league_regex_string: str,
                                                end_week: int,
                                                forum: discord.ForumChannel):
        season_leaderboard_length = 15
        weekly_leaderboard_length = 10

        scoring_results = await asyncio.to_thread(
            leaguescoring.get_scoring_results,
            account_identifier=cogConstants.NARFFL_USER,
            starting_week=1,
            ending_week=end_week,
            platform_selection=common.PlatformSelection.FLEAFLICKER,
            get_weekly_results=True,
            get_current_weeks_results=True,
            get_season_results=True,
            get_max_scores=True,
            get_min_scores=False,
            league_regex_string=league_regex_string)

        # Create the forum post
        thread_title = "Week {week} {level} Leaderboard".format(
            week=end_week, level=league_level)
        thread_content = strings.NARFFL_LEADERBOARD_LEVEL_SPECIFIC_POST_TEMPLATE.format(
            level=league_level)
        post = (await forum.create_thread(name=thread_title,
                                          content=thread_content))[0]

        league_prefix_to_remove = "NarFFL {level} - ".format(
            level=league_level)

        # Send the leaderboards as followup messages
        message = self._build_season_long_leaderboard_string(
            scoring_results.max_season_scores, season_leaderboard_length,
            league_prefix_to_remove)
        await post.send(content=message)

        message = self._build_weekly_score_leaderboard_string(
            scoring_results.max_weekly_scores, weekly_leaderboard_length,
            "__Top {count} Single-Week Scorers__\n".format(
                count=weekly_leaderboard_length), league_prefix_to_remove)
        await post.send(content=message)

        message = self._build_weekly_score_leaderboard_string(
            scoring_results.max_scores_this_week, weekly_leaderboard_length,
            "__Top {count} Week {week} Scorers__\n".format(
                count=weekly_leaderboard_length, week=end_week),
            league_prefix_to_remove)
        await post.send(content=message)

    async def _post_narffl_top_farm_scores_leaderboard(
            self, end_week: int, forum: discord.ForumChannel):
        leagues_posted = 0
        batch_size = 4

        top_scores = await asyncio.to_thread(
            topleaguescore.get_top_weekly_score_for_each_league,
            account_identifier=cogConstants.NARFFL_USER,
            league_regex_string=cogConstants.NARFFL_FARM_LEAGUE_REGEX,
            starting_week=1,
            ending_week=end_week,
            platform_selection=common.PlatformSelection.FLEAFLICKER)

        # Create the forum post
        thread_title = "Week {week} Farm Top Scores".format(week=end_week)
        thread_content = strings.NARFFL_TOP_FARM_LEAGUE_SCORES_CONTENT
        post = (await forum.create_thread(name=thread_title,
                                          content=thread_content))[0]

        farm_prefix = "NarFFL Farm - "

        # Loop over the top scores until they're all posted, using the specified batch_size
        while leagues_posted < len(top_scores):
            content = self._build_unordered_weekly_score_leaderboard_string(
                top_scores[leagues_posted:leagues_posted + batch_size],
                batch_size,
                league_prefix_to_remove=farm_prefix)

            await post.send(content=content)

            leagues_posted += batch_size

    async def _post_narffl_overall_leaderboard(self, end_week: int,
                                               forum: discord.ForumChannel):
        leaderboard_length = 10

        scoring_results = await asyncio.to_thread(
            leaguescoring.get_scoring_results,
            account_identifier=cogConstants.NARFFL_USER,
            starting_week=1,
            ending_week=end_week,
            platform_selection=common.PlatformSelection.FLEAFLICKER,
            get_weekly_results=True,
            get_current_weeks_results=True,
            get_season_results=True,
            get_max_scores=True,
            get_min_scores=False)

        # Create the forum post
        thread_title = "Week {week} Overall Leaderboard".format(week=end_week)
        thread_content = "Here are the top-scoring teams looking at all NarFFL Leagues."
        post = (await forum.create_thread(name=thread_title,
                                          content=thread_content))[0]

        # Send the leaderboards as followup messages
        message = self._build_season_long_leaderboard_string(
            scoring_results.max_season_scores, leaderboard_length)
        await post.send(content=message)

        message = self._build_weekly_score_leaderboard_string(
            scoring_results.max_weekly_scores, leaderboard_length,
            "__Top {count} Single-Week Scorers__\n".format(
                count=leaderboard_length))
        await post.send(content=message)

        message = self._build_weekly_score_leaderboard_string(
            scoring_results.max_scores_this_week, leaderboard_length,
            "__Top {count} Week {week} Scorers__\n".format(
                count=leaderboard_length, week=end_week))
        await post.send(content=message)


async def setup(bot):
    await bot.add_cog(LeaderboardsCog(bot))
