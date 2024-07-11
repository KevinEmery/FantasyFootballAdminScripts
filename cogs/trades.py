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

import cogs.common as cogCommon
import cogs.constants as cogConstants
import common
import trades

from datetime import datetime
from discord import app_commands
from discord.ext import commands, tasks
from typing import List

from library.model.trade import Trade

FTA_TRADE_CHANNEL_PATH = "./bot_data/fta_trade_channel"
FTA_POSTED_TRADES_PATH = "./bot_data/fta_posted_trades"
FTA_TRADE_POSTING_STATUS_PATH = "./bot_data/fta_trade_posting_status"
NARFFL_TRADE_CHANNEL_PATH = "./bot_data/narffl_trade_channel"
NARFFL_POSTED_TRADES_PATH = "./bot_data/narffl_posted_trades"
NARFFL_TRADE_POSTING_STATUS_PATH = "./bot_data/narffl_trade_posting_status"
FF_DISCORD_TRADE_CHANNEL_PATH = "./bot_data/ff_discord_trade_channel"
FF_DISCORD_POSTED_TRADES_PATH = "./bot_data/ff_discord_posted_trades"
FF_DISCORD_POSTING_STATUS_PATH = "./bot_data/ff_discord_trade_posting_status"

TWO_TEAM_TRADE_REACTIONS = ['🅰️', '🅱️', '🤷']
THREE_TEAM_TRADE_REACTIONS = ['1️⃣', '2️⃣', '3️⃣', '🤷']
FOUR_TEAM_TRADE_REACTIONS = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '🤷']


class TradesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        if self._get_trade_posting_status_from_file(
                FTA_TRADE_POSTING_STATUS_PATH):
            self.post_fta_trades.start()
        if self._get_trade_posting_status_from_file(
                NARFFL_TRADE_POSTING_STATUS_PATH):
            self.post_narffl_trades.start()
        if self._get_trade_posting_status_from_file(
                FF_DISCORD_POSTING_STATUS_PATH):
            self.post_ff_discord_trades.start()

        self.trade_task_checker.start()

    def cog_unload(self):
        self.post_fta_trades.cancel()
        self.trade_task_checker.cancel()

    # General Task Diagnostics
    @app_commands.command(name="get_trade_task_states",
                          description="Retrieves the state of all trade tasks")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def get_trade_task_states(self, interaction: discord.Interaction):
        await interaction.response.defer()
        template = "Task {task}.running(): {state}\n"
        responseString = ""

        responseString += template.format(
            task="post_fta_trades", state=self.post_fta_trades.is_running())
        responseString += template.format(
            task="post_narffl_trades",
            state=self.post_narffl_trades.is_running())
        responseString += template.format(
            task="post_ff_discord_trades",
            state=self.post_ff_discord_trades.is_running())
        responseString += template.format(
            task="trade_task_checker",
            state=self.trade_task_checker.is_running())

        await interaction.followup.send(responseString)

    @tasks.loop(minutes=7)
    async def trade_task_checker(self):
        # Verifies that the tasks are still running, and restarts them if next scheduled
        # is before now. If this consistently happens, schedule tasks less frequently.
        next_fta_trade = self.post_fta_trades.next_iteration
        next_narffl_trade = self.post_narffl_trades.next_iteration
        next_ff_discord_trade = self.post_ff_discord_trades.next_iteration

        if next_fta_trade is not None:
            now = datetime.now(tz=next_fta_trade.tzinfo)
        elif next_narffl_trade is not None:
            now = datetime.now(tz=next_narffl_trade.tzinfo)
        elif next_ff_discord_trade is not None:
            now = datetime.now(tz=next_ff_discord_trade.tzinfo)
        else:
            cogCommon.print_descriptive_log("trade_task_checker",
                                            "No trade tasks running.")
            return

        if next_fta_trade is not None and next_fta_trade < now:
            cogCommon.print_descriptive_log(
                "trade_task_checker", "FTA Trade task is delayed, restarting")
            self.post_fta_trades.restart()

        if next_narffl_trade is not None and next_narffl_trade < now:
            cogCommon.print_descriptive_log(
                "trade_task_checker",
                "NarFFL Trade task is delayed, restarting")
            self.post_narffl_trades.restart()

        if next_ff_discord_trade is not None and next_ff_discord_trade < now:
            cogCommon.print_descriptive_log(
                "trade_task_checker",
                "FF Discord Trade task is delayed, restarting")
            self.post_ff_discord_trades.restart()

    @trade_task_checker.before_loop
    async def before_trade_task_checker(self):
        await self.bot.wait_until_ready()

    # FTA Trade Commands/Tasks
    @app_commands.command(name="start_posting_fta_trades",
                          description="Starts the recurring trade loop")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def start_posting_fta_trades(self, interaction: discord.Interaction):
        cogCommon.print_descriptive_log("start_posting_fta_trades")
        self._write_trade_posting_status_to_file(FTA_TRADE_POSTING_STATUS_PATH,
                                                 True)
        self.post_fta_trades.start()
        await asyncio.sleep(1)
        await interaction.response.send_message(
            "FTA trade task is {status}.".format(
                status=self._get_task_status(self.post_fta_trades)))

    @app_commands.command(name="stop_posting_fta_trades",
                          description="Stops the recurring trade loop")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def stop_posting_fta_trades(self, interaction: discord.Interaction):
        cogCommon.print_descriptive_log("stop_posting_fta_trades")
        self._write_trade_posting_status_to_file(FTA_TRADE_POSTING_STATUS_PATH,
                                                 False)
        self.post_fta_trades.cancel()
        await asyncio.sleep(1)
        await interaction.response.send_message(
            "FTA trade task is {status}.".format(
                status=self._get_task_status(self.post_fta_trades)))

    @app_commands.command(
        name="set_fta_trades_channel",
        description="Sets the channel where FTA trades will be posted")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def set_fta_trades_channel(self, interaction: discord.Interaction,
                                     channel: discord.TextChannel):
        cogCommon.print_descriptive_log("set_fta_trades_channel",
                                        "Channel set to " + channel.name)
        self._write_trade_channel_to_file(FTA_TRADE_CHANNEL_PATH, channel)
        await interaction.response.send_message(
            "FTA trade channel set to <#{channel_id}>".format(
                channel_id=channel.id))

    @tasks.loop(minutes=10)
    async def post_fta_trades(self):
        trade_channel = self._get_trade_channel_from_file(
            FTA_TRADE_CHANNEL_PATH)

        if trade_channel is not None:
            cogCommon.print_descriptive_log("post_fta_trades",
                                            "Posting to " + trade_channel.name)
            try:
                all_trades = await asyncio.to_thread(
                    trades.fetch_and_filter_trades,
                    account_identifier=cogConstants.FTAFFL_USER,
                    league_regex_string=cogConstants.FTAFFL_LEAGUE_REGEX)
            except:
                # Because this is a periodic task, if there's an intermittent error we can just rely on the
                # next task loop. But to make sure, let's log
                cogCommon.print_descriptive_log(
                    "post_fta_trades",
                    "Exception while retrieving trades, ending task run")
                return

            await self._post_all_unposted_trades(trade_channel, all_trades,
                                                 FTA_POSTED_TRADES_PATH)
        else:
            cogCommon.print_descriptive_log("post_fta_trades",
                                            "No trade channel avaialble")

        cogCommon.print_descriptive_log("post_fta_trades", "Done")

    @post_fta_trades.before_loop
    async def before_post_fta_trades(self):
        await self.bot.wait_until_ready()

    # NarFFL Trade Commands/Tasks
    @app_commands.command(name="start_posting_narffl_trades",
                          description="Starts the recurring trade loop")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def start_posting_narffl_trades(self,
                                          interaction: discord.Interaction):
        cogCommon.print_descriptive_log("start_posting_narffl_trades")
        self._write_trade_posting_status_to_file(
            NARFFL_TRADE_POSTING_STATUS_PATH, True)
        self.post_narffl_trades.start()
        await asyncio.sleep(1)
        await interaction.response.send_message(
            "NarFFL trade task is {status}.".format(
                status=self._get_task_status(self.post_narffl_trades)))

    @app_commands.command(name="stop_posting_narffl_trades",
                          description="Stops the recurring trade loop")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def stop_posting_narffl_trades(self,
                                         interaction: discord.Interaction):
        cogCommon.print_descriptive_log("stop_posting_narffl_trades")
        self._write_trade_posting_status_to_file(
            NARFFL_TRADE_POSTING_STATUS_PATH, False)
        self.post_narffl_trades.cancel()
        await asyncio.sleep(1)
        await interaction.response.send_message(
            "NarFFL trade task is {status}.".format(
                status=self._get_task_status(self.post_narffl_trades)))

    @app_commands.command(
        name="set_narffl_trades_channel",
        description="Sets the channel where NarFFL trades will be posted")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def set_narffl_trades_channel(self, interaction: discord.Interaction,
                                        channel: discord.TextChannel):
        cogCommon.print_descriptive_log("set_narffl_trades_channel",
                                        "Channel set to " + channel.name)
        self._write_trade_channel_to_file(NARFFL_TRADE_CHANNEL_PATH, channel)
        await interaction.response.send_message(
            "NarFFL trade channel set to <#{channel_id}>".format(
                channel_id=channel.id))

    @tasks.loop(minutes=10)
    async def post_narffl_trades(self):
        trade_channel = self._get_trade_channel_from_file(
            NARFFL_TRADE_CHANNEL_PATH)

        if trade_channel is not None:
            cogCommon.print_descriptive_log("post_narffl_trades",
                                            "Posting to " + trade_channel.name)

            try:
                all_trades = await asyncio.to_thread(
                    trades.fetch_and_filter_trades,
                    account_identifier=cogConstants.NARFFL_USER,
                    platform_selection=common.PlatformSelection.FLEAFLICKER)
            except Exception as error:
                # Because this is a periodic task, if there's an intermittent error we can just rely on the
                # next task loop. But to make sure, let's log
                cogCommon.print_descriptive_log(
                    "post_narffl_trades",
                    "Exception while retrieving trades, ending task run" +
                    str(error))
                return

            await self._post_all_unposted_trades(trade_channel, all_trades,
                                                 NARFFL_POSTED_TRADES_PATH)
        else:
            cogCommon.print_descriptive_log("post_narffl_trades",
                                            "No trade channel avaialble")

        cogCommon.print_descriptive_log("post_narffl_trades", "Done")

    @post_narffl_trades.before_loop
    async def before_post_narffl_trades(self):
        await self.bot.wait_until_ready()

    # FF Discord Commands/Tasks
    @app_commands.command(name="start_posting_ff_discord_trades",
                          description="Starts the recurring trade loop")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def start_posting_ff_discord_trades(
            self, interaction: discord.Interaction):
        cogCommon.print_descriptive_log("start_posting_ff_discord_trades")
        self._write_trade_posting_status_to_file(
            FF_DISCORD_POSTING_STATUS_PATH, True)
        self.post_ff_discord_trades.start()
        await asyncio.sleep(1)
        await interaction.response.send_message(
            "FF Discord trade task is {status}.".format(
                status=self._get_task_status(self.post_ff_discord_trades)))

    @app_commands.command(name="stop_posting_ff_discord_trades",
                          description="Stops the recurring trade loop")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def stop_posting_ff_discord_trades(self,
                                             interaction: discord.Interaction):
        cogCommon.print_descriptive_log("stop_posting_ff_discord_trades")
        self._write_trade_posting_status_to_file(
            FF_DISCORD_POSTING_STATUS_PATH, False)
        self.post_ff_discord_trades.cancel()
        await asyncio.sleep(1)
        await interaction.response.send_message(
            "FF Discord trade task is {status}.".format(
                status=self._get_task_status(self.post_ff_discord_trades)))

    @app_commands.command(
        name="set_ff_discord_trades_channel",
        description="Sets the channel where FF Discord trades will be posted")
    @app_commands.guilds(cogConstants.DEV_SERVER_GUILD_ID)
    async def set_ff_discord_trades_channel(self,
                                            interaction: discord.Interaction,
                                            channel: discord.TextChannel):
        cogCommon.print_descriptive_log("set_ff_discord_trades_channel",
                                        "Channel set to " + channel.name)
        self._write_trade_channel_to_file(FF_DISCORD_TRADE_CHANNEL_PATH,
                                          channel)
        await interaction.response.send_message(
            "FF Discord trade channel set to <#{channel_id}>".format(
                channel_id=channel.id))

    @tasks.loop(minutes=10)
    async def post_ff_discord_trades(self):
        trade_channel = self._get_trade_channel_from_file(
            FF_DISCORD_TRADE_CHANNEL_PATH)

        if trade_channel is not None:
            cogCommon.print_descriptive_log("post_ff_discord_trades",
                                            "Posting to " + trade_channel.name)

            try:
                all_trades = await asyncio.to_thread(
                    trades.fetch_and_filter_trades,
                    account_identifier=cogConstants.FF_DISCORD_USER)
            except:
                # Because this is a periodic task, if there's an intermittent error we can just rely on the
                # next task loop. But to make sure, let's log
                cogCommon.print_descriptive_log(
                    "post_ff_discord_trades",
                    "Exception while retrieving trades, ending task run")
                return

            await self._post_all_unposted_trades(
                trade_channel, all_trades, FF_DISCORD_POSTED_TRADES_PATH,
                False)
        else:
            cogCommon.print_descriptive_log("post_ff_discord_trades",
                                            "No trade channel avaialble")

        cogCommon.print_descriptive_log("post_ff_discord_trades", "Done")

    @post_ff_discord_trades.before_loop
    async def before_post_ff_discord_trades(self):
        await self.bot.wait_until_ready()

    # General Helpers
    def _create_file_string_for_trade(self, trade: Trade) -> str:
        output_list = []
        output_list.append(str(trade.id))
        output_list.append(trade.league.name)
        output_list.append(trade.trade_time.strftime("%m/%d/%Y - %H:%M:%S"))
        for details in trade.details:
            output_list.append(details.team.manager.name)

        return ",".join(output_list)

    def _get_trade_id_from_file_entry(self, file_line: str) -> str:
        split = file_line.split(",")
        return split[0]

    def _get_posted_trade_ids_from_file(self, filename: str) -> List[str]:
        result = []
        if os.path.isfile(filename):
            file = open(filename, "r")
            lines = file.readlines()
            for line in lines:
                result.append(self._get_trade_id_from_file_entry(line))
            file.close()

        return result

    def _write_trade_to_file(self, filename: str, trade: Trade):
        if os.path.isfile(filename):
            file = open(filename, "a")
        else:
            file = open(filename, "w")

        file.write(self._create_file_string_for_trade(trade) + "\n")
        file.close()

    def _get_trade_channel_from_file(self,
                                     filename: str) -> discord.TextChannel:
        if os.path.isfile(filename):
            file = open(filename, "r")
            channel_id = file.read().split(",")[0]
            file.close()
        else:
            return None

        return self.bot.get_channel(int(channel_id))

    def _write_trade_channel_to_file(self, filename: str,
                                     channel: discord.TextChannel):
        file = open(filename, "w")
        file.write(str(channel.id) + "," + channel.name)
        file.close()

    def _get_trade_posting_status_from_file(self, filename: str) -> bool:
        # Assume default status is false
        posting_status = False

        if os.path.isfile(filename):
            file = open(filename, "r")
            s = file.read()
            s = s.strip()

            if s == 'True':
                posting_status = True
            elif s == 'False':
                posting_status = False
            else:
                cogCommon.print_descriptive_log(
                    "_get_trade_posting_status_from_file",
                    "Unknown value {value} for trade posting status in {file}".
                    format(value=s, file=filename))
                posting_status = False

            file.close()

        return posting_status

    def _write_trade_posting_status_to_file(self, filename: str,
                                            is_active: bool):
        file = open(filename, "w")
        file.write(str(is_active))
        file.close()

    def _get_task_status(self, task) -> str:
        return "running" if task.is_running() else "not running"

    async def _post_all_unposted_trades(self,
                                        trade_channel: discord.TextChannel,
                                        all_trades: List[Trade],
                                        posted_trade_file_path: str,
                                        should_react: bool = True):
        posted_trade_ids = self._get_posted_trade_ids_from_file(
            posted_trade_file_path)

        for trade in all_trades:
            if str(trade.id) not in posted_trade_ids:
                message = await trade_channel.send(
                    content=trades.format_trades([trade]))
                if should_react:
                    await self._react_to_trade(message, len(trade.details))
                self._write_trade_to_file(posted_trade_file_path, trade)

    async def _react_to_trade(self, message: discord.Message, trade_size: int):
        if trade_size == 2:
            for reaction in TWO_TEAM_TRADE_REACTIONS:
                await message.add_reaction(reaction)
        elif trade_size == 3:
            for reaction in THREE_TEAM_TRADE_REACTIONS:
                await message.add_reaction(reaction)
        elif trade_size == 4:
            for reaction in FOUR_TEAM_TRADE_REACTIONS:
                await message.add_reaction(reaction)


async def setup(bot):
    await bot.add_cog(TradesCog(bot))
