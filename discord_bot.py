import asyncio
import discord
import os

import adp
import common
import inactives
import leaguescoring
import trades

from datetime import datetime
from discord.ext import commands, tasks
from typing import List

from library.model.leagueinactivity import LeagueInactivity
from library.model.trade import Trade
from library.model.seasonscore import SeasonScore
from library.model.weeklyscore import WeeklyScore

# Actual limit is 25, we want to steer clear in case we add fields on top of the iteration
EMBED_FIELD_LIMIT = 20
FTA_ADP_THREAD_CONTENT = "The data here is for the FTA league format. \
These leagues are 14-team, 0.5 PPR Leagues that start \
1 QB, 2 RBs, 3 WRs, 1 TE, 1 W/R/T Flex, 1 K, and 1 DEF.\n\n"
NARFFL_ADP_THREAD_CONTENT = "The data here is for the NarFFL league format. \
These leagues are 12-team, 1.0 PPR Leagues that start \
1 QB, 2 RBs, 2 WRs, 1 TE, 1 W/R/T Flex, 1 K, and 1 DEF.\n\n"
ADP_GLOSSARY = "__**Glossary Terms**__\
```\n\
Av:  The average draft position across all drafts\n\
Min: The earliest a player was drafted\n\
Max: The latest a player was drafted\n\
(#): Number of times a player has been drafted\
```\n\
The designation \"X.Y\" represents a selection in Round X, at Pick Y"

FTA_INACTIVE_STARTERS_THREAD_CONTENT = "Below is a list of every team that started an \
inactive player this week. When generating this, anyone injured this week or ruled out \
at the last minute should have been ignored."

FTA_LEADERBARD_MAIN_POST_CONTENT_HEADER = "Here are your top-scoring teams across all leagues, as well as the highest single-week score this year so far.\n\n\
At the end of the regular season, the top-three season-long scorers and the top single-week score for the year are awarded prizes.\n\n"
LEADERBOARD_SEASON_SCORE_TEAM_TEMPLATE = "{rank}. **[{team_name}](<{roster_link}>)** (_{league}_)  - **{score}**\n"
LEADERBOARD_WEEKLY_SCORE_TEAM_TEMPLATE = "{rank}. **[{team_name}](<{roster_link}>)** (_{league}_)  - Week {week} - **{score}**\n"

NARFFL_LEADERBOARD_LEVEL_SPECIFIC_POST_TEMPLATE = "Here are the top-scoring teams looking at the NarFFL {level} leagues"

# These colors mirror the Sleeper draft board
ALL_PLAYERS_COLOR = discord.Colour.dark_blue()
QB_COLOR = discord.Colour.from_rgb(192, 94, 133)
RB_COLOR = discord.Colour.from_rgb(115, 195, 166)
WR_COLOR = discord.Colour.from_rgb(70, 162, 202)
TE_COLOR = discord.Colour.from_rgb(204, 140, 74)
K_COLOR = discord.Colour.purple()
DEF_COLOR = discord.Colour.from_rgb(154, 95, 78)

FTA_TRADE_CHANNEL_PATH = "./bot_data/fta_trade_channel"
FTA_POSTED_TRADES_PATH = "./bot_data/fta_posted_trades"
FTA_TRADE_POSTING_STATUS_PATH = "./bot_data/fta_trade_posting_status"
FTA_LEAGUE_CHANNEL_MAPPING_PATH = "./bot_data/fta_league_channel_mapping"
NARFFL_TRADE_CHANNEL_PATH = "./bot_data/narffl_trade_channel"
NARFFL_POSTED_TRADES_PATH = "./bot_data/narffl_posted_trades"
NARFFL_TRADE_POSTING_STATUS_PATH = "./bot_data/narffl_trade_posting_status"
NARFFL_LEAGUE_CHANNEL_MAPPING_PATH = "./bot_data/narffl_league_channel_mapping"
FF_DISCORD_TRADE_CHANNEL_PATH = "./bot_data/ff_discord_trade_channel"
FF_DISCORD_POSTED_TRADES_PATH = "./bot_data/ff_discord_posted_trades"
FF_DISCORD_POSTING_STATUS_PATH = "./bot_data/ff_discord_trade_posting_status"
FF_DISCORD_LEAGUE_CHANNEL_MAPPING_PATH = "/bot_data/ff_discord_league_channel_mapping"

TWO_TEAM_TRADE_REACTIONS = ['🅰️', '🅱️', '🤷']
THREE_TEAM_TRADE_REACTIONS = ['1️⃣', '2️⃣', '3️⃣', '🤷']
FOUR_TEAM_TRADE_REACTIONS = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '🤷']

FTAFFL_USER = "FTAFFL"
FTAFFL_LEAGUE_REGEX = "^FTA \#\d+.*$"

NARFFL_USER = "narfflflea@davehenning.net"
NARFFL_FARM_LEAGUE_REGEX = "^NarFFL Farm.*$"
NARFFL_MINORS_LEAGUE_REGEX = "^NarFFL Minors.*$"
NARFFL_MAJORS_LEAGUE_REGEX = "^NarFFL Majors.*$"
NARFFL_PREMIER_LEAGUE_REGEX = "^NarFFL Premier.*$"

FF_DISCORD_USER = "FFDiscordAdmin"

FTA_LEAGUE_ADMIN_ROLE = "League Admin"
NARFFL_ADMIN_ROLE = "Admin"
FF_DISCORD_ADMIN_ROLE = "Commissioner"
BOT_DEV_SERVER_ROLE = "Bot Admin"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='&', intents=intents)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    if _get_trade_posting_status_from_file(FTA_TRADE_POSTING_STATUS_PATH):
        post_fta_trades.start()
    if _get_trade_posting_status_from_file(NARFFL_TRADE_POSTING_STATUS_PATH):
        post_narffl_trades.start()
    if _get_trade_posting_status_from_file(FF_DISCORD_POSTING_STATUS_PATH):
        post_ff_discord_trades.start()

    task_checker.start()

# General ADP Functions


async def _post_position_adp_data(ctx, forum: discord.ForumChannel, adp_data: List[str],
                                  position_long: str, embed_color: discord.Colour, thread_content: str):
    messages = _break_adp_content_into_messages(adp_data, embed_color)
    thread_title = _get_formatted_date() + ": " + position_long
    thread = (await forum.create_thread(name=thread_title, content=thread_content))[0]
    for message in messages:
        await thread.send(embed=message)


def _break_adp_content_into_messages(content: List[str], embed_color: discord.Colour) -> List[discord.Embed]:
    split_content = []
    current_embed = discord.Embed(colour=embed_color)

    for line in content:
        if (len(current_embed.fields) >= EMBED_FIELD_LIMIT):
            split_content.append(current_embed)
            current_embed = discord.Embed(colour=embed_color)
        _convert_adp_csv_to_embed_field(line, current_embed)

    if len(current_embed.fields) > 0:
        split_content.append(current_embed)

    return split_content


def _convert_adp_csv_to_embed_field(content: str, embed: discord.Embed):
    player_data = content.split(",")
    template = "`Av: {adp:<5} Min: {min:<5} Max: {max:<5} ({n})`"
    embed.add_field(name=player_data[0], value=template.format(n=player_data[4],
                    adp=player_data[1], min=player_data[2], max=player_data[3]), inline=False)


def _get_formatted_date() -> str:
    now = datetime.now()
    return now.strftime("%m/%d/%y")

# FTA ADP Commands


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, FTA_LEAGUE_ADMIN_ROLE)
async def post_fta_adps(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_fta_adps", "Posting to " + forum.name + " forum")
    await post_fta_adp_def(ctx, forum)
    await post_fta_adp_k(ctx, forum)
    await post_fta_adp_te(ctx, forum)
    await post_fta_adp_wr(ctx, forum)
    await post_fta_adp_rb(ctx, forum)
    await post_fta_adp_qb(ctx, forum)
    await post_fta_adp_all(ctx, forum)
    _print_descriptive_log("post_fta_adps", "Done")


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, FTA_LEAGUE_ADMIN_ROLE)
async def post_fta_adp_all(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_fta_adp_all", "Posting to " + forum.name + " forum")
    await _post_fta_position_adp(ctx, forum, adp.INCLUDE_ALL, "All Players", ALL_PLAYERS_COLOR)
    _print_descriptive_log("post_fta_adp_all", "Done")


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, FTA_LEAGUE_ADMIN_ROLE)
async def post_fta_adp_qb(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_fta_adp_qb", "Posting to " + forum.name + " forum")
    await _post_fta_position_adp(ctx, forum, "QB", "Quarterback", QB_COLOR)
    _print_descriptive_log("post_fta_adp_qb", "Done")


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, FTA_LEAGUE_ADMIN_ROLE)
async def post_fta_adp_wr(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_fta_adp_wr", "Posting to " + forum.name + " forum")
    await _post_fta_position_adp(ctx, forum, "WR", "Wide Receiver", WR_COLOR)
    _print_descriptive_log("post_fta_adp_wr", "Done")


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, FTA_LEAGUE_ADMIN_ROLE)
async def post_fta_adp_rb(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_fta_adp_rb", "Posting to " + forum.name + " forum")
    await _post_fta_position_adp(ctx, forum, "RB", "Running Back", RB_COLOR)
    _print_descriptive_log("post_fta_adp_rb", "Done")


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, FTA_LEAGUE_ADMIN_ROLE)
async def post_fta_adp_te(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_fta_adp_te", "Posting to " + forum.name + " forum")
    await _post_fta_position_adp(ctx, forum, "TE", "Tight End", TE_COLOR)
    _print_descriptive_log("post_fta_adp_te", "Done")


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, FTA_LEAGUE_ADMIN_ROLE)
async def post_fta_adp_k(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_fta_adp_k", "Posting to " + forum.name + " forum")
    await _post_fta_position_adp(ctx, forum, "K", "Kicker", K_COLOR)
    _print_descriptive_log("post_fta_adp_k", "Done")


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, FTA_LEAGUE_ADMIN_ROLE)
async def post_fta_adp_def(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_fta_adp_def", "Posting to " + forum.name + " forum")
    await _post_fta_position_adp(ctx, forum, "DEF", "Team Defense", DEF_COLOR)
    _print_descriptive_log("post_fta_adp_def", "Done")


async def _post_fta_position_adp(ctx, forum: discord.ForumChannel, position_short: str,
                                 position_long: str, embed_color: discord.Colour):
    adp_data = await asyncio.to_thread(adp.aggregate_adp_data, account_identifier=FTAFFL_USER, league_size=14,
                                       position=position_short, league_regex_string=FTAFFL_LEAGUE_REGEX,
                                       output_format=adp.OutputFormat.FORMATTED_CSV)
    await _post_position_adp_data(ctx, forum, adp_data, position_long, embed_color,
                                  FTA_ADP_THREAD_CONTENT + ADP_GLOSSARY)

# NarFFL ADP Commands


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, NARFFL_ADMIN_ROLE)
async def post_narffl_adps(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_narffl_adps", "Posting to " + forum.name + " forum")
    await post_narffl_adp_def(ctx, forum)
    await post_narffl_adp_k(ctx, forum)
    await post_narffl_adp_te(ctx, forum)
    await post_narffl_adp_wr(ctx, forum)
    await post_narffl_adp_rb(ctx, forum)
    await post_narffl_adp_qb(ctx, forum)
    await post_narffl_adp_all(ctx, forum)
    _print_descriptive_log("post_narffl_adps", "Done")


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, NARFFL_ADMIN_ROLE)
async def post_narffl_adp_all(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_narffl_adp_all", "Posting to " + forum.name + " forum")
    await _post_narffl_position_adp(ctx, forum, adp.INCLUDE_ALL, "All Players", ALL_PLAYERS_COLOR)
    _print_descriptive_log("post_narffl_adp_all", "Done")


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, NARFFL_ADMIN_ROLE)
async def post_narffl_adp_qb(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_narffl_adp_qb", "Posting to " + forum.name + " forum")
    await _post_narffl_position_adp(ctx, forum, "QB", "Quarterback", QB_COLOR)
    _print_descriptive_log("post_narffl_adp_qb", "Done")


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, NARFFL_ADMIN_ROLE)
async def post_narffl_adp_wr(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_narffl_adp_wr", "Posting to " + forum.name + " forum")
    await _post_narffl_position_adp(ctx, forum, "WR", "Wide Receiver", WR_COLOR)
    _print_descriptive_log("post_narffl_adp_wr", "Done")


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, NARFFL_ADMIN_ROLE)
async def post_narffl_adp_rb(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_narffl_adp_rb", "Posting to " + forum.name + " forum")
    await _post_narffl_position_adp(ctx, forum, "RB", "Running Back", RB_COLOR)
    _print_descriptive_log("post_narffl_adp_rb", "Done")


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, NARFFL_ADMIN_ROLE)
async def post_narffl_adp_te(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_narffl_adp_te", "Posting to " + forum.name + " forum")
    await _post_narffl_position_adp(ctx, forum, "TE", "Tight End", TE_COLOR)
    _print_descriptive_log("post_narffl_adp_te", "Done")


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, NARFFL_ADMIN_ROLE)
async def post_narffl_adp_k(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_narffl_adp_k", "Posting to " + forum.name + " forum")
    await _post_narffl_position_adp(ctx, forum, "K", "Kicker", K_COLOR)
    _print_descriptive_log("post_narffl_adp_k", "Done")


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, NARFFL_ADMIN_ROLE)
async def post_narffl_adp_def(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_narffl_adp_def", "Posting to " + forum.name + " forum")
    await _post_narffl_position_adp(ctx, forum, "D/ST", "Team Defense", DEF_COLOR)
    _print_descriptive_log("post_narffl_adp_def", "Done")


async def _post_narffl_position_adp(ctx, forum: discord.ForumChannel, position_short: str,
                                    position_long: str, embed_color: discord.Colour):
    adp_data = await asyncio.to_thread(adp.aggregate_adp_data, account_identifier=NARFFL_USER, league_size=12,
                                       position=position_short, output_format=adp.OutputFormat.FORMATTED_CSV,
                                       platform_selection=common.PlatformSelection.FLEAFLICKER)
    await _post_position_adp_data(ctx, forum, adp_data, position_long, embed_color,
                                  NARFFL_ADP_THREAD_CONTENT + ADP_GLOSSARY)

# General Trade Functions


def _create_file_string_for_trade(trade: Trade) -> str:
    output_list = []
    output_list.append(str(trade.id))
    output_list.append(trade.league.name)
    output_list.append(trade.trade_time.strftime("%m/%d/%Y - %H:%M:%S"))
    for details in trade.details:
        output_list.append(details.team.manager.name)

    return ",".join(output_list)


def _get_trade_id_from_file_entry(file_line: str) -> str:
    split = file_line.split(",")
    return split[0]


def _get_posted_trade_ids_from_file(filename: str) -> List[str]:
    result = []
    if os.path.isfile(filename):
        file = open(filename, "r")
        lines = file.readlines()
        for line in lines:
            result.append(_get_trade_id_from_file_entry(line))
        file.close()

    return result


def _write_trade_to_file(filename: str, trade: Trade):
    if os.path.isfile(filename):
        file = open(filename, "a")
    else:
        file = open(filename, "w")

    file.write(_create_file_string_for_trade(trade)+"\n")
    file.close()


def _get_trade_channel_from_file(filename: str) -> discord.TextChannel:
    if os.path.isfile(filename):
        file = open(filename, "r")
        channel_id = file.read().split(",")[0]
        file.close()
    else:
        return None

    return bot.get_channel(int(channel_id))


def _write_trade_channel_to_file(filename: str, channel: discord.TextChannel):
    file = open(filename, "w")
    file.write(str(channel.id) + "," + channel.name)
    file.close()


def _get_trade_posting_status_from_file(filename: str) -> bool:
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
            _print_descriptive_log("_get_trade_posting_status_from_file",
                                   "Unknown value {value} for trade posting status in {file}".format(value=s, file=filename))
            posting_status = False

        file.close()

    return posting_status


def _write_trade_posting_status_to_file(filename: str, is_active: bool):
    file = open(filename, "w")
    file.write(str(is_active))
    file.close()


async def post_all_unposted_trades(trade_channel: discord.TextChannel, all_trades: List[Trade],
                                   posted_trade_file_path: str, should_react: bool = True):
    posted_trade_ids = _get_posted_trade_ids_from_file(posted_trade_file_path)

    for trade in all_trades:
        if str(trade.id) not in posted_trade_ids:
            message = await trade_channel.send(content=trades.format_trades([trade]))
            if should_react:
                await _react_to_trade(message, len(trade.details))
            _write_trade_to_file(posted_trade_file_path, trade)


async def _react_to_trade(message: discord.Message, trade_size: int):
    if trade_size == 2:
        for reaction in TWO_TEAM_TRADE_REACTIONS:
            await message.add_reaction(reaction)
    elif trade_size == 3:
        for reaction in THREE_TEAM_TRADE_REACTIONS:
            await message.add_reaction(reaction)
    elif trade_size == 4:
        for reaction in FOUR_TEAM_TRADE_REACTIONS:
            await message.add_reaction(reaction)


# FTA Trade Commands


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, FTA_LEAGUE_ADMIN_ROLE)
async def start_posting_fta_trades(ctx):
    _print_descriptive_log("start_posting_fta_trades")
    _write_trade_posting_status_to_file(FTA_TRADE_POSTING_STATUS_PATH, True)
    post_fta_trades.start()


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, FTA_LEAGUE_ADMIN_ROLE)
async def stop_posting_fta_trades(ctx):
    _print_descriptive_log("stop_posting_fta_trades")
    _write_trade_posting_status_to_file(FTA_TRADE_POSTING_STATUS_PATH, False)
    post_fta_trades.cancel()


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, FTA_LEAGUE_ADMIN_ROLE)
async def set_fta_trades_channel(ctx, channel: discord.TextChannel):
    _print_descriptive_log("set_fta_trades_channel", "Channel set to " + channel.name)
    _write_trade_channel_to_file(FTA_TRADE_CHANNEL_PATH, channel)


@tasks.loop(minutes=10)
async def post_fta_trades():
    trade_channel = _get_trade_channel_from_file(FTA_TRADE_CHANNEL_PATH)

    if trade_channel is not None:
        _print_descriptive_log("post_fta_trades", "Posting to " + trade_channel.name)
        try:
            all_trades = await asyncio.to_thread(trades.fetch_and_filter_trades,
                                                 account_identifier=FTAFFL_USER, league_regex_string=FTAFFL_LEAGUE_REGEX)
        except:
            # Because this is a periodic task, if there's an intermittent error we can just rely on the
            # next task loop. But to make sure, let's log
            _print_descriptive_log("post_fta_trades", "Exception while retrieving trades, ending task run")
            return

        await post_all_unposted_trades(trade_channel, all_trades, FTA_POSTED_TRADES_PATH)
    else:
        _print_descriptive_log("post_fta_trades", "No trade channel avaialble")

    _print_descriptive_log("post_fta_trades", "Done")


# NarFFL Trade Commands


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, NARFFL_ADMIN_ROLE)
async def start_posting_narffl_trades(ctx):
    _print_descriptive_log("start_posting_narffl_trades")
    _write_trade_posting_status_to_file(NARFFL_TRADE_POSTING_STATUS_PATH, True)
    post_narffl_trades.start()


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, NARFFL_ADMIN_ROLE)
async def stop_posting_narffl_trades(ctx):
    _print_descriptive_log("stop_posting_narffl_trades")
    _write_trade_posting_status_to_file(NARFFL_TRADE_POSTING_STATUS_PATH, False)
    post_narffl_trades.cancel()


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, NARFFL_ADMIN_ROLE)
async def set_narffl_trades_channel(ctx, channel: discord.TextChannel):
    _print_descriptive_log("set_narffl_trades_channel", "Channel set to " + channel.name)
    _write_trade_channel_to_file(NARFFL_TRADE_CHANNEL_PATH, channel)


@tasks.loop(minutes=10)
async def post_narffl_trades():
    trade_channel = _get_trade_channel_from_file(NARFFL_TRADE_CHANNEL_PATH)

    if trade_channel is not None:
        _print_descriptive_log("post_narffl_trades", "Posting to " + trade_channel.name)

        try:
            all_trades = await asyncio.to_thread(trades.fetch_and_filter_trades,
                                                 account_identifier=NARFFL_USER,
                                                 platform_selection=common.PlatformSelection.FLEAFLICKER)
        except:
            # Because this is a periodic task, if there's an intermittent error we can just rely on the
            # next task loop. But to make sure, let's log
            _print_descriptive_log("post_narffl_trades", "Exception while retrieving trades, ending task run")
            return

        await post_all_unposted_trades(trade_channel, all_trades, NARFFL_POSTED_TRADES_PATH)
    else:
        _print_descriptive_log("post_narffl_trades", "No trade channel avaialble")

    _print_descriptive_log("post_narffl_trades", "Done")

# FF Discord Trade Commands


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, FF_DISCORD_ADMIN_ROLE)
async def start_posting_ff_discord_trades(ctx):
    _print_descriptive_log("start_posting_ff_discord_trades")
    _write_trade_posting_status_to_file(FF_DISCORD_POSTING_STATUS_PATH, True)
    post_ff_discord_trades.start()


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, FF_DISCORD_ADMIN_ROLE)
async def stop_posting_ff_discord_trades(ctx):
    _print_descriptive_log("stop_posting_ff_discord_trades")
    _write_trade_posting_status_to_file(FF_DISCORD_POSTING_STATUS_PATH, False)
    post_ff_discord_trades.cancel()


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, FF_DISCORD_ADMIN_ROLE)
async def set_ff_discord_trades_channel(ctx, channel: discord.TextChannel):
    _print_descriptive_log("set_ff_discord_trades_channel", "Channel set to " + channel.name)
    _write_trade_channel_to_file(FF_DISCORD_TRADE_CHANNEL_PATH, channel)


@tasks.loop(minutes=10)
async def post_ff_discord_trades():
    trade_channel = _get_trade_channel_from_file(FF_DISCORD_TRADE_CHANNEL_PATH)

    if trade_channel is not None:
        _print_descriptive_log("post_ff_discord_trades", "Posting to " + trade_channel.name)

        try:
            all_trades = await asyncio.to_thread(trades.fetch_and_filter_trades,
                                                 account_identifier=FF_DISCORD_USER)
        except:
            # Because this is a periodic task, if there's an intermittent error we can just rely on the
            # next task loop. But to make sure, let's log
            _print_descriptive_log("post_ff_discord_trades", "Exception while retrieving trades, ending task run")
            return

        await post_all_unposted_trades(trade_channel, all_trades, FF_DISCORD_POSTED_TRADES_PATH, False)
    else:
        _print_descriptive_log("post_ff_discord_trades", "No trade channel avaialble")

    _print_descriptive_log("post_ff_discord_trades", "Done")

# General Inactivity Functions


def _create_embed_for_inactive_league(league_inactivity: LeagueInactivity) -> discord.Embed:
    embed = discord.Embed(colour=discord.Colour.red(), title=league_inactivity.league.name)

    last_transaction_template = "_Last transaction: {date}_\n"
    date_format = "%m-%d-%Y"
    player_template = "{name}, {position} - {status}\n"

    for roster in league_inactivity.rosters:
        embed_value = ""
        if roster.last_transaction is not None:
            embed_value += last_transaction_template.format(
                date=roster.last_transaction.time.strftime(date_format))
        for player in roster.inactive_players:
            embed_value += player_template.format(name=player.name, position=player.position, status=player.status)
        embed.add_field(name=roster.team.manager.name, value=embed_value, inline=False)

    return embed


def _create_file_string_for_league_and_channel(league_name: str, channel: discord.TextChannel) -> str:
    output_list = []
    output_list.append(league_name)
    output_list.append(str(channel.id))
    output_list.append(channel.name)

    return ",".join(output_list)


def _write_channel_mapping_for_league(filename: str, league_name: str, channel: discord.TextChannel):
    if os.path.isfile(filename):
        file = open(filename, "a")
    else:
        file = open(filename, "w")

    file.write(_create_file_string_for_league_and_channel(league_name, channel)+"\n")
    file.close()


def _get_channel_for_league(filename: str, league_name: str) -> discord.TextChannel:
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
    return bot.get_channel(int(channel_id))


# FTA Inactivity Commands

@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, FTA_LEAGUE_ADMIN_ROLE)
async def post_fta_inactives_for_select_teams(ctx, week: int, *, only_teams: str = ""):
    _print_descriptive_log("post_fta_inactives_for_select_teams")
    only_teams_list = only_teams.split(",")

    inactive_leagues = await asyncio.to_thread(inactives.get_all_league_inactivity,
                                               account_identifier=FTAFFL_USER,
                                               week=week, include_transactions=False,
                                               only_teams=only_teams_list)

    for league_inactivity in inactive_leagues:
        channel = _get_channel_for_league(FTA_LEAGUE_CHANNEL_MAPPING_PATH, league_inactivity.league.name)
        if channel is not None:
            await channel.send(embed=_create_embed_for_inactive_league(league_inactivity), content="__**Current Inactive Starters**__")
        else:
            _print_descriptive_log("post_fta_inactives_for_select_teams",
                                   "Failed to post for league {name}".format(name=league_inactivity.league.name))

    _print_descriptive_log("post_fta_inactives_for_select_teams", "Done")


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, FTA_LEAGUE_ADMIN_ROLE)
async def post_fta_inactives_excluding_teams(ctx, week: int, *, teams_to_ignore: str = ""):
    _print_descriptive_log("post_fta_inactives_excluding_teams")
    teams_to_ignore_list = teams_to_ignore.split(",")

    inactive_leagues = await asyncio.to_thread(inactives.get_all_league_inactivity,
                                               account_identifier=FTAFFL_USER,
                                               week=week, include_transactions=False,
                                               teams_to_ignore=teams_to_ignore_list)

    for league_inactivity in inactive_leagues:
        channel = _get_channel_for_league(FTA_LEAGUE_CHANNEL_MAPPING_PATH, league_inactivity.league.name)
        if channel is not None:
            await channel.send(embed=_create_embed_for_inactive_league(league_inactivity), content="__**Current Inactive Starters**__")
        else:
            _print_descriptive_log("post_fta_inactives_excluding_teams",
                                   "Failed to post for league {name}".format(name=league_inactivity.league.name))

    _print_descriptive_log("post_fta_inactives_excluding_teams", "Done")


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, FTA_LEAGUE_ADMIN_ROLE)
async def post_fta_inactives_to_forum(ctx, week: int, forum: discord.ForumChannel, *, player_names_to_ignore: str = ""):
    _print_descriptive_log("post_fta_inactives_to_forum")
    player_names_to_ignore_list = player_names_to_ignore.split(",")
    if player_names_to_ignore_list[0] == '':
        player_names_to_ignore_list = []

    inactive_leagues = await asyncio.to_thread(inactives.get_all_league_inactivity,
                                               account_identifier=FTAFFL_USER,
                                               league_regex_string=FTAFFL_LEAGUE_REGEX,
                                               week=week, include_transactions=True,
                                               player_names_to_ignore=player_names_to_ignore_list)

    thread_title = "Week {week} Inactive Starters".format(week=str(week))
    thread_content = FTA_INACTIVE_STARTERS_THREAD_CONTENT
    if player_names_to_ignore_list:
        thread_content += "\n\n"
        thread_content += "__Players Ignored__\n"
        for player_name in player_names_to_ignore_list:
            thread_content += "- {name}\n".format(name=player_name)

    thread = (await forum.create_thread(name=thread_title, content=thread_content))[0]
    for league_inactivity in inactive_leagues:
        await thread.send(embed=_create_embed_for_inactive_league(league_inactivity))

    _print_descriptive_log("post_fta_inactives_to_forum", "Done")


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, FTA_LEAGUE_ADMIN_ROLE)
async def create_fta_league_to_channel_mapping(ctx, league_name: str, channel: discord.TextChannel):
    _print_descriptive_log("create_fta_league_to_channel_mapping")
    _write_channel_mapping_for_league(FTA_LEAGUE_CHANNEL_MAPPING_PATH, league_name, channel)

# NarFFL Inactivity Commands


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, NARFFL_ADMIN_ROLE)
async def post_narffl_inactives_for_select_teams(ctx, week: int, *, only_teams: str = ""):
    _print_descriptive_log("post_narffl_inactives_for_select_teams")
    only_teams_list = only_teams.split(",")

    inactive_leagues = await asyncio.to_thread(inactives.get_all_league_inactivity,
                                               account_identifier=NARFFL_USER,
                                               week=week, include_transactions=False,
                                               platform_selection=common.PlatformSelection.FLEAFLICKER,
                                               only_teams=only_teams_list)

    for league_inactivity in inactive_leagues:
        channel = _get_channel_for_league(NARFFL_LEAGUE_CHANNEL_MAPPING_PATH, league_inactivity.league.name)
        if channel is not None:
            await channel.send(embed=_create_embed_for_inactive_league(league_inactivity), content="__**Current Inactive Starters**__")
        else:
            _print_descriptive_log("post_narffl_inactives_for_select_teams",
                                   "Failed to post for league {name}".format(name=league_inactivity.league.name))

    _print_descriptive_log("post_narffl_inactives_for_select_teams", "Done")


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, NARFFL_ADMIN_ROLE)
async def post_narffl_inactives_excluding_teams(ctx, week: int, *, teams_to_ignore: str = ""):
    _print_descriptive_log("post_narffl_inactives_excluding_teams")
    teams_to_ignore_list = teams_to_ignore.split(",")

    inactive_leagues = await asyncio.to_thread(inactives.get_all_league_inactivity,
                                               account_identifier=NARFFL_USER,
                                               week=week, include_transactions=False,
                                               platform_selection=common.PlatformSelection.FLEAFLICKER,
                                               teams_to_ignore=teams_to_ignore_list)

    for league_inactivity in inactive_leagues:
        channel = _get_channel_for_league(NARFFL_LEAGUE_CHANNEL_MAPPING_PATH, league_inactivity.league.name)
        if channel is not None:
            await channel.send(embed=_create_embed_for_inactive_league(league_inactivity), content="__**Current Inactive Starters**__")
        else:
            _print_descriptive_log("post_narffl_inactives_excluding_teams",
                                   "Failed to post for league {name}".format(name=league_inactivity.league.name))

    _print_descriptive_log("post_narffl_inactives_excluding_teams", "Done")


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, NARFFL_ADMIN_ROLE)
async def create_narffl_league_to_channel_mapping(ctx, league_name: str, channel: discord.TextChannel):
    _print_descriptive_log("create_narffl_league_to_channel_mapping")
    _write_channel_mapping_for_league(NARFFL_LEAGUE_CHANNEL_MAPPING_PATH, league_name, channel)


# FF Discord Inactivity Commands


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, FF_DISCORD_ADMIN_ROLE)
async def post_ff_discord_inactives_for_select_teams(ctx, week: int, *, only_teams: str = ""):
    _print_descriptive_log("post_ff_discord_inactives_for_select_teams")
    only_teams_list = only_teams.split(",")

    inactive_leagues = await asyncio.to_thread(inactives.get_all_league_inactivity,
                                               account_identifier=FF_DISCORD_USER,
                                               week=week, include_transactions=False,
                                               only_teams=only_teams_list)

    for league_inactivity in inactive_leagues:
        channel = _get_channel_for_league(FF_DISCORD_LEAGUE_CHANNEL_MAPPING_PATH, league_inactivity.league.name)
        if channel is not None:
            await channel.send(embed=_create_embed_for_inactive_league(league_inactivity), content="__**Current Inactive Starters**__")
        else:
            _print_descriptive_log("post_ff_discord_inactives_for_select_teams",
                                   "Failed to post for league {name}".format(name=league_inactivity.league.name))

    _print_descriptive_log("post_ff_discord_inactives_for_select_teams", "Done")


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, FF_DISCORD_ADMIN_ROLE)
async def post_ff_discord_inactives_excluding_teams(ctx, week: int, *, teams_to_ignore: str = ""):
    _print_descriptive_log("post_ff_discord_inactives_excluding_teams")
    teams_to_ignore_list = teams_to_ignore.split(",")

    inactive_leagues = await asyncio.to_thread(inactives.get_all_league_inactivity,
                                               account_identifier=FF_DISCORD_USER,
                                               week=week, include_transactions=False,
                                               teams_to_ignore=teams_to_ignore_list)

    for league_inactivity in inactive_leagues:
        channel = _get_channel_for_league(FF_DISCORD_LEAGUE_CHANNEL_MAPPING_PATH, league_inactivity.league.name)
        if channel is not None:
            await channel.send(embed=_create_embed_for_inactive_league(league_inactivity), content="__**Current Inactive Starters**__")
        else:
            _print_descriptive_log("post_ff_discord_inactives_excluding_teams",
                                   "Failed to post for league {name}".format(name=league_inactivity.league.name))

    _print_descriptive_log("post_ff_discord_inactives_excluding_teams", "Done")


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, FF_DISCORD_ADMIN_ROLE)
async def post_ff_discord_inactives_to_forum(ctx, week: int, forum: discord.ForumChannel, *, player_names_to_ignore: str = ""):
    _print_descriptive_log("post_ff_discord_inactives_to_forum")
    player_names_to_ignore_list = player_names_to_ignore.split(",")
    if player_names_to_ignore_list[0] == '':
        player_names_to_ignore_list = []

    inactive_leagues = await asyncio.to_thread(inactives.get_all_league_inactivity,
                                               account_identifier=FF_DISCORD_USER,
                                               week=week, include_transactions=True,
                                               player_names_to_ignore=player_names_to_ignore_list)

    thread_title = "Week {week} Inactive Starters".format(week=str(week))
    thread_content = FTA_INACTIVE_STARTERS_THREAD_CONTENT
    if player_names_to_ignore_list:
        thread_content += "\n\n"
        thread_content += "__Players Ignored__\n"
        for player_name in player_names_to_ignore_list:
            thread_content += "- {name}\n".format(name=player_name)

    thread = (await forum.create_thread(name=thread_title, content=thread_content))[0]
    for league_inactivity in inactive_leagues:
        await thread.send(embed=_create_embed_for_inactive_league(league_inactivity))

    _print_descriptive_log("post_ff_discord_inactives_to_forum", "Done")


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, FF_DISCORD_ADMIN_ROLE)
async def create_ff_discord_league_to_channel_mapping(ctx, league_name: str, channel: discord.TextChannel):
    _print_descriptive_log("create_ff_discord_league_to_channel_mapping")
    _write_channel_mapping_for_league(FF_DISCORD_LEAGUE_CHANNEL_MAPPING_PATH, league_name, channel)


# Generic Leaderboard Helpers

def _build_season_long_leaderboard_string(scores: List[SeasonScore], count: int, league_prefix_to_remove: str = "") -> str:
    string = "__Top {count} Season-Long Scorers__\n".format(count=count)

    for n in range(count):
        result = scores[n]
        league_name = result.league.name.removeprefix(league_prefix_to_remove)
        string += LEADERBOARD_SEASON_SCORE_TEAM_TEMPLATE.format(
            rank=n+1, team_name=result.team.manager.name, league=league_name,
            score=result.score, roster_link=result.team.roster_link)

    return string


def _build_weekly_score_leaderboard_string(scores: List[WeeklyScore], count: int, title: str, league_prefix_to_remove: str = ""):
    string = title
    for n in range(count):
        result = scores[n]
        league_name = result.league.name.removeprefix(league_prefix_to_remove)
        string += LEADERBOARD_WEEKLY_SCORE_TEAM_TEMPLATE.format(
            rank=n+1, team_name=result.team.manager.name, league=league_name,
            score=result.score, roster_link=result.team.roster_link, week=str(result.week))

    return string


# FTA Leaderboard Commands

@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, FTA_LEAGUE_ADMIN_ROLE)
async def post_fta_leaderboard(ctx, end_week: int, forum: discord.ForumChannel):
    _print_descriptive_log("post_fta_leaderboard")
    main_leaderboard_length = 5
    expanded_leaderboard_length = 15
    scoring_results = await asyncio.to_thread(leaguescoring.get_scoring_results, account_identifier=FTAFFL_USER,
                                              starting_week=1, ending_week=end_week,
                                              get_weekly_results=True, get_current_weeks_results=True,  get_season_results=True,
                                              get_max_scores=True, get_min_scores=False, league_regex_string=FTAFFL_LEAGUE_REGEX)

    # Build the main leaderboard for the thread content
    thread_title = "Week {week} Leaderboard".format(week=end_week)

    thread_content = FTA_LEADERBARD_MAIN_POST_CONTENT_HEADER
    thread_content += _build_season_long_leaderboard_string(
        scoring_results.max_season_scores, main_leaderboard_length) + "\n"
    thread_content += _build_weekly_score_leaderboard_string(
        scoring_results.max_weekly_scores, 1, "__Top Single-Week Scorer__\n") + "\n"
    thread_content += "\nFor the expanded leaderboards, please see the messages below. Good luck everyone!"

    # Create the forum thread
    thread = (await forum.create_thread(name=thread_title, content=thread_content))[0]

    # Send the expanded leaderboards as followup messages
    message = _build_season_long_leaderboard_string(scoring_results.max_season_scores, expanded_leaderboard_length)
    await thread.send(content=message)

    message = _build_weekly_score_leaderboard_string(scoring_results.max_weekly_scores, expanded_leaderboard_length,
                                                     "__Top {count} Single-Week Scorers__\n".format(count=expanded_leaderboard_length))
    await thread.send(content=message)

    message = _build_weekly_score_leaderboard_string(scoring_results.max_scores_this_week, expanded_leaderboard_length,
                                                     "__Top {count} Week {week} Scorers__\n".format(count=expanded_leaderboard_length, week=end_week))
    await thread.send(content=message)

    _print_descriptive_log("post_fta_leaderboard", "Done")


# NarFFL Leaderboard Commands

async def _post_specific_narffl_leaderboard(league_level: str, league_regex_string: str, end_week: int, forum: discord.ForumChannel):
    season_leaderboard_length = 15
    weekly_leaderboard_length = 10

    scoring_results = await asyncio.to_thread(leaguescoring.get_scoring_results, account_identifier=NARFFL_USER,
                                              starting_week=1, ending_week=end_week, platform_selection=common.PlatformSelection.FLEAFLICKER,
                                              get_weekly_results=True, get_current_weeks_results=True,  get_season_results=True,
                                              get_max_scores=True, get_min_scores=False, league_regex_string=league_regex_string)

    # Create the forum post
    thread_title = "Week {week} {level} Leaderboard".format(week=end_week, level=league_level)
    thread_content = NARFFL_LEADERBOARD_LEVEL_SPECIFIC_POST_TEMPLATE.format(level=league_level)
    post = (await forum.create_thread(name=thread_title, content=thread_content))[0]

    league_prefix_to_remove = "NarFFL {level} - ".format(level=league_level)

    # Send the leaderboards as followup messages
    message = _build_season_long_leaderboard_string(
        scoring_results.max_season_scores, season_leaderboard_length, league_prefix_to_remove)
    print(len(message))
    await post.send(content=message)

    message = _build_weekly_score_leaderboard_string(scoring_results.max_weekly_scores, weekly_leaderboard_length,
                                                     "__Top {count} Single-Week Scorers__\n".format(
                                                         count=weekly_leaderboard_length),
                                                     league_prefix_to_remove)
    print(len(message))
    await post.send(content=message)

    message = _build_weekly_score_leaderboard_string(scoring_results.max_scores_this_week, weekly_leaderboard_length,
                                                     "__Top {count} Week {week} Scorers__\n".format(
                                                         count=weekly_leaderboard_length, week=end_week),
                                                     league_prefix_to_remove)
    print(len(message))
    await post.send(content=message)


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, NARFFL_ADMIN_ROLE)
async def post_narffl_leaderboards(ctx, end_week: int, forum: discord.ForumChannel):
    _print_descriptive_log("post_narffl_leaderboards", "Posting to {forum}".format(forum=forum.name))
    await post_narffl_farm_leaderboard(ctx, end_week, forum)
    await post_narffl_minors_leaderboard(ctx, end_week, forum)
    await post_narffl_majors_leaderboard(ctx, end_week, forum)
    await post_narffl_premier_leaderboard(ctx, end_week, forum)
    await post_narffl_overall_leaderboard(ctx, end_week, forum)
    _print_descriptive_log("post_narffl_leaderboards", "Done")


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, NARFFL_ADMIN_ROLE)
async def post_narffl_farm_leaderboard(ctx, end_week: int, forum: discord.ForumChannel):
    _print_descriptive_log("post_narffl_farm_leaderboard", "Posting to {forum}".format(forum=forum.name))
    await _post_specific_narffl_leaderboard("Farm", NARFFL_FARM_LEAGUE_REGEX, end_week, forum)
    _print_descriptive_log("post_narffl_farm_leaderboard", "Done")


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, NARFFL_ADMIN_ROLE)
async def post_narffl_minors_leaderboard(ctx, end_week: int, forum: discord.ForumChannel):
    _print_descriptive_log("post_narffl_minors_leaderboard", "Posting to {forum}".format(forum=forum.name))
    await _post_specific_narffl_leaderboard("Minors", NARFFL_MINORS_LEAGUE_REGEX, end_week, forum)
    _print_descriptive_log("post_narffl_minors_leaderboard", "Done")


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, NARFFL_ADMIN_ROLE)
async def post_narffl_majors_leaderboard(ctx, end_week: int, forum: discord.ForumChannel):
    _print_descriptive_log("post_narffl_majors_leaderboard", "Posting to {forum}".format(forum=forum.name))
    await _post_specific_narffl_leaderboard("Majors", NARFFL_MAJORS_LEAGUE_REGEX, end_week, forum)
    _print_descriptive_log("post_narffl_majors_leaderboard", "Done")


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, NARFFL_ADMIN_ROLE)
async def post_narffl_premier_leaderboard(ctx, end_week: int, forum: discord.ForumChannel):
    _print_descriptive_log("post_narffl_premier_leaderboard", "Posting to {forum}".format(forum=forum.name))
    await _post_specific_narffl_leaderboard("Premier", NARFFL_PREMIER_LEAGUE_REGEX, end_week, forum)
    _print_descriptive_log("post_narffl_premier_leaderboard", "Done")


@bot.command()
@commands.has_any_role(BOT_DEV_SERVER_ROLE, NARFFL_ADMIN_ROLE)
async def post_narffl_overall_leaderboard(ctx, end_week: int, forum: discord.ForumChannel):
    _print_descriptive_log("post_narffl_overall_leaderboard", "Posting to {forum}".format(forum=forum.name))

    leaderboard_length = 10

    scoring_results = await asyncio.to_thread(leaguescoring.get_scoring_results, account_identifier=NARFFL_USER,
                                              starting_week=1, ending_week=end_week, platform_selection=common.PlatformSelection.FLEAFLICKER,
                                              get_weekly_results=True, get_current_weeks_results=True,  get_season_results=True,
                                              get_max_scores=True, get_min_scores=False)

    # Create the forum post
    thread_title = "Week {week} Overall Leaderboard".format(week=end_week)
    thread_content = "Here are the top-scoring teams looking at all NarFFL Leagues."
    post = (await forum.create_thread(name=thread_title, content=thread_content))[0]

    # Send the leaderboards as followup messages
    message = _build_season_long_leaderboard_string(scoring_results.max_season_scores, leaderboard_length)
    print(len(message))
    await post.send(content=message)

    message = _build_weekly_score_leaderboard_string(scoring_results.max_weekly_scores, leaderboard_length,
                                                     "__Top {count} Single-Week Scorers__\n".format(count=leaderboard_length))
    print(len(message))
    await post.send(content=message)

    message = _build_weekly_score_leaderboard_string(scoring_results.max_scores_this_week, leaderboard_length,
                                                     "__Top {count} Week {week} Scorers__\n".format(count=leaderboard_length, week=end_week))
    print(len(message))
    await post.send(content=message)

    _print_descriptive_log("post_narffl_overall_leaderboard", "Done")


# General Bot Diagnostic Commands

@bot.command()
@commands.has_role(BOT_DEV_SERVER_ROLE)
async def get_task_states(ctx):
    template = "Task {task}.running(): {state}"

    await ctx.send(template.format(task="post_fta_trades", state=post_fta_trades.is_running()))
    await ctx.send(template.format(task="post_narffl_trades", state=post_narffl_trades.is_running()))
    await ctx.send(template.format(task="post_ff_discord_trades", state=post_ff_discord_trades.is_running()))


@tasks.loop(minutes=7)
async def task_checker():
    # Verifies that the tasks are still running, and restarts them if next scheduled
    # is before now. If this consistently happens, schedule tasks less frequently.
    next_narffl_trade = post_narffl_trades.next_iteration
    next_fta_trade = post_fta_trades.next_iteration
    next_ff_discord_trade = post_ff_discord_trades.next_iteration
    now = datetime.now(tz=next_narffl_trade.tzinfo)

    if next_narffl_trade is not None and next_narffl_trade < now:
        _print_descriptive_log("task_checker", "NarFFL Trade task is delayed, restarting")
        post_narffl_trades.restart()

    if next_fta_trade is not None and next_fta_trade < now:
        _print_descriptive_log("task_checker", "FTA Trade task is delayed, restarting")
        post_fta_trades.restart()

    if next_ff_discord_trade is not None and next_ff_discord_trade < now:
        _print_descriptive_log("task_checker", "FF Discord Trade task is delayed, restarting")
        post_ff_discord_trades.restart()


# General bot helper functions

def _print_descriptive_log(log_method: str, log_line: str = ""):
    log_template = "{time:<20}{log_method:40.40}\t{log_line}"
    formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(log_template.format(time=formatted_time, log_method=log_method, log_line=log_line))


def _retrieve_token() -> str:
    token_file = open("./local/bot_token", "r")
    token_string = token_file.read()
    token_file.close()

    return token_string


# Command to start things
bot.run(_retrieve_token())
