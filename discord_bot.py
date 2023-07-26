import asyncio
import discord
import os

import adp
import common
import trades

from datetime import datetime
from discord.ext import commands, tasks
from typing import List

from library.model.trade import Trade

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

TWO_TEAM_TRADE_REACTIONS = ['🅰️', '🅱️', '🤷']
THREE_TEAM_TRADE_REACTIONS = ['1️⃣', '2️⃣', '3️⃣', '🤷']
FOUR_TEAM_TRADE_REACTIONS = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '🤷']

FTAFFL_USER = "FTAFFL"
FTAFFL_LEAGUE_REGEX = "^FTA \#\d+.*$"

NARFFL_USER = "narfflflea@davehenning.net"

FTA_LEAGUE_ADMIN_ROLE = "League Admin"
NARFFL_ADMIN_ROLE = "Admin"
LOB_COMMISH_ROLE = "Commissioner"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='&', intents=intents)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    if _get_fta_trade_posting_status():
        post_fta_trades.start()

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
@commands.has_any_role(LOB_COMMISH_ROLE, FTA_LEAGUE_ADMIN_ROLE)
async def post_fta_adps(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_fta_adps", "Posting to " + forum.name + " forum")
    await post_fta_adp_all(ctx, forum)
    await post_fta_adp_qb(ctx, forum)
    await post_fta_adp_rb(ctx, forum)
    await post_fta_adp_wr(ctx, forum)
    await post_fta_adp_te(ctx, forum)
    await post_fta_adp_k(ctx, forum)
    await post_fta_adp_def(ctx, forum)


@bot.command()
@commands.has_any_role(LOB_COMMISH_ROLE, FTA_LEAGUE_ADMIN_ROLE)
async def post_fta_adp_all(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_fta_adp_all", "Posting to " + forum.name + " forum")
    await _post_fta_position_adp(ctx, forum, adp.INCLUDE_ALL, "All Players", ALL_PLAYERS_COLOR)


@bot.command()
@commands.has_any_role(LOB_COMMISH_ROLE, FTA_LEAGUE_ADMIN_ROLE)
async def post_fta_adp_qb(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_fta_adp_qb", "Posting to " + forum.name + " forum")
    await _post_fta_position_adp(ctx, forum, "QB", "Quarterback", QB_COLOR)


@bot.command()
@commands.has_any_role(LOB_COMMISH_ROLE, FTA_LEAGUE_ADMIN_ROLE)
async def post_fta_adp_wr(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_fta_adp_wr", "Posting to " + forum.name + " forum")
    await _post_fta_position_adp(ctx, forum, "WR", "Wide Receiver", WR_COLOR)


@bot.command()
@commands.has_any_role(LOB_COMMISH_ROLE, FTA_LEAGUE_ADMIN_ROLE)
async def post_fta_adp_rb(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_fta_adp_rb", "Posting to " + forum.name + " forum")
    await _post_fta_position_adp(ctx, forum, "RB", "Running Back", RB_COLOR)


@bot.command()
@commands.has_any_role(LOB_COMMISH_ROLE, FTA_LEAGUE_ADMIN_ROLE)
async def post_fta_adp_te(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_fta_adp_te", "Posting to " + forum.name + " forum")
    await _post_fta_position_adp(ctx, forum, "TE", "Tight End", TE_COLOR)


@bot.command()
@commands.has_any_role(LOB_COMMISH_ROLE, FTA_LEAGUE_ADMIN_ROLE)
async def post_fta_adp_k(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_fta_adp_k", "Posting to " + forum.name + " forum")
    await _post_fta_position_adp(ctx, forum, "K", "Kicker", K_COLOR)


@bot.command()
@commands.has_any_role(LOB_COMMISH_ROLE, FTA_LEAGUE_ADMIN_ROLE)
async def post_fta_adp_def(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_fta_adp_def", "Posting to " + forum.name + " forum")
    await _post_fta_position_adp(ctx, forum, "DEF", "Team Defense", DEF_COLOR)


async def _post_fta_position_adp(ctx, forum: discord.ForumChannel, position_short: str,
                                 position_long: str, embed_color: discord.Colour):
    adp_data = adp.aggregate_adp_data(FTAFFL_USER, 14, position=position_short,
                                      league_regex_string=FTAFFL_LEAGUE_REGEX,
                                      output_format=adp.OutputFormat.FORMATTED_CSV)
    await _post_position_adp_data(ctx, forum, adp_data, position_long, embed_color,
                                  FTA_ADP_THREAD_CONTENT + ADP_GLOSSARY)

# NarFFL ADP Commands


@bot.command()
@commands.has_any_role(LOB_COMMISH_ROLE, NARFFL_ADMIN_ROLE)
async def post_narffl_adps(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_narffl_adps", "Posting to " + forum.name + " forum")
    await post_narffl_adp_all(ctx, forum)
    await post_narffl_adp_qb(ctx, forum)
    await post_narffl_adp_rb(ctx, forum)
    await post_narffl_adp_wr(ctx, forum)
    await post_narffl_adp_te(ctx, forum)
    await post_narffl_adp_k(ctx, forum)
    await post_narffl_adp_def(ctx, forum)


@bot.command()
@commands.has_any_role(LOB_COMMISH_ROLE, NARFFL_ADMIN_ROLE)
async def post_narffl_adp_all(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_narffl_adp_all", "Posting to " + forum.name + " forum")
    await _post_narffl_position_adp(ctx, forum, adp.INCLUDE_ALL, "All Players", ALL_PLAYERS_COLOR)


@bot.command()
@commands.has_any_role(LOB_COMMISH_ROLE, NARFFL_ADMIN_ROLE)
async def post_narffl_adp_qb(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_narffl_adp_qb", "Posting to " + forum.name + " forum")
    await _post_narffl_position_adp(ctx, forum, "QB", "Quarterback", QB_COLOR)


@bot.command()
@commands.has_any_role(LOB_COMMISH_ROLE, NARFFL_ADMIN_ROLE)
async def post_narffl_adp_wr(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_narffl_adp_wr", "Posting to " + forum.name + " forum")
    await _post_narffl_position_adp(ctx, forum, "WR", "Wide Receiver", WR_COLOR)


@bot.command()
@commands.has_any_role(LOB_COMMISH_ROLE, NARFFL_ADMIN_ROLE)
async def post_narffl_adp_rb(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_narffl_adp_rb", "Posting to " + forum.name + " forum")
    await _post_narffl_position_adp(ctx, forum, "RB", "Running Back", RB_COLOR)


@bot.command()
@commands.has_any_role(LOB_COMMISH_ROLE, NARFFL_ADMIN_ROLE)
async def post_narffl_adp_te(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_narffl_adp_te", "Posting to " + forum.name + " forum")
    await _post_narffl_position_adp(ctx, forum, "TE", "Tight End", TE_COLOR)


@bot.command()
@commands.has_any_role(LOB_COMMISH_ROLE, NARFFL_ADMIN_ROLE)
async def post_narffl_adp_k(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_narffl_adp_k", "Posting to " + forum.name + " forum")
    await _post_narffl_position_adp(ctx, forum, "K", "Kicker", K_COLOR)


@bot.command()
@commands.has_any_role(LOB_COMMISH_ROLE, NARFFL_ADMIN_ROLE)
async def post_narffl_adp_def(ctx, forum: discord.ForumChannel):
    _print_descriptive_log("post_narffl_adp_def", "Posting to " + forum.name + " forum")
    await _post_narffl_position_adp(ctx, forum, "D/ST", "Team Defense", DEF_COLOR)


async def _post_narffl_position_adp(ctx, forum: discord.ForumChannel, position_short: str,
                                    position_long: str, embed_color: discord.Colour):
    adp_data = await asyncio.to_thread(adp.aggregate_adp_data, account_identifier=NARFFL_USER, league_size=12,
                                       position=position_short, output_format=adp.OutputFormat.FORMATTED_CSV,
                                       platform_selection=common.PlatformSelection.FLEAFLICKER)
    await _post_position_adp_data(ctx, forum, adp_data, position_long, embed_color,
                                  NARFFL_ADP_THREAD_CONTENT + ADP_GLOSSARY)

# FTA Trade Commands


@bot.command()
@commands.has_any_role(LOB_COMMISH_ROLE, FTA_LEAGUE_ADMIN_ROLE)
async def start_posting_fta_trades(ctx):
    _print_descriptive_log("start_posting_fta_trades")
    _write_fta_trade_posting_status(True)
    post_fta_trades.start()


@bot.command()
@commands.has_any_role(LOB_COMMISH_ROLE, FTA_LEAGUE_ADMIN_ROLE)
async def stop_posting_fta_trades(ctx):
    _print_descriptive_log("stop_posting_fta_trades")
    _write_fta_trade_posting_status(False)
    post_fta_trades.cancel()


@tasks.loop(minutes=5)
async def post_fta_trades():
    _print_descriptive_log("post_fta_trades")
    trade_channel = _get_fta_trade_channel()
    posted_trade_ids = _get_all_fta_trade_ids()

    if trade_channel is not None:
        _print_descriptive_log("post_fta_trades", "Posting to " + trade_channel.name)
        # Pull all available trades
        all_trades = await asyncio.to_thread(trades.fetch_and_filter_trades,
                                             FTAFFL_USER, league_regex_string=FTAFFL_LEAGUE_REGEX)

        # Post the non-posted trades with reactions
        for trade in all_trades:
            if trade.id not in posted_trade_ids:
                message = await trade_channel.send(content=trades.format_trades([trade]))
                await _react_to_trade(message, len(trade.details))
                _write_fta_trade_to_file(trade)
    else:
        _print_descriptive_log("post_fta_trades", "No trade channel avaialble")


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


@bot.command()
@commands.has_any_role(LOB_COMMISH_ROLE, FTA_LEAGUE_ADMIN_ROLE)
async def set_fta_trades_channel(ctx, channel: discord.TextChannel):
    _print_descriptive_log("set_fta_trades_channel", "Channel set to " + channel.name)
    file = open(FTA_TRADE_CHANNEL_PATH, "w")
    file.write(str(channel.id) + "," + channel.name)
    file.close()


def _get_fta_trade_channel() -> discord.TextChannel:
    if os.path.isfile(FTA_TRADE_CHANNEL_PATH):
        file = open(FTA_TRADE_CHANNEL_PATH, "r")
        channel_id = file.read().split(",")[0]
        file.close()
    else:
        return None

    return bot.get_channel(int(channel_id))


def _write_fta_trade_to_file(trade: Trade):
    if os.path.isfile(FTA_POSTED_TRADES_PATH):
        file = open(FTA_POSTED_TRADES_PATH, "a")
    else:
        file = open(FTA_POSTED_TRADES_PATH, "w")

    file.write(_create_file_string_for_trade(trade)+"\n")
    file.close()


def _get_all_fta_trade_ids() -> List[str]:
    result = []
    if os.path.isfile(FTA_POSTED_TRADES_PATH):
        file = open(FTA_POSTED_TRADES_PATH, "r")
        lines = file.readlines()
        for line in lines:
            result.append(_get_trade_id_from_file_entry(line))
        file.close()

    return result


def _write_fta_trade_posting_status(is_active: bool):
    file = open(FTA_TRADE_POSTING_STATUS_PATH, "w")
    file.write(str(is_active))
    file.close()


def _get_fta_trade_posting_status() -> bool:
    # Assume default status is false
    posting_status = False

    if os.path.isfile(FTA_TRADE_POSTING_STATUS_PATH):
        file = open(FTA_TRADE_POSTING_STATUS_PATH, "r")
        s = file.read()

        if s == 'True':
            posting_status = True
        elif s == 'False':
            posting_status = False
        else:
            _print_descriptive_log("_get_fta_trade_posting_status",
                                   "Unknown value %s for trade posting status".format(s))
            posting_status = False

        file.close()

    return posting_status


def _create_file_string_for_trade(trade: Trade) -> str:
    output_list = []
    output_list.append(trade.id)
    output_list.append(trade.league.name)
    output_list.append(trade.trade_time.strftime("%m/%d/%Y - %H:%M:%S"))
    for details in trade.details:
        output_list.append(details.team.manager.name)

    return ",".join(output_list)


def _get_trade_id_from_file_entry(file_line: str) -> str:
    split = file_line.split(",")
    return split[0]


def _print_descriptive_log(log_method: str, log_line: str = ""):
    log_template = "{time:<20}{log_method:40.40}\t{log_line}"
    formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(log_template.format(time=formatted_time, log_method=log_method, log_line=log_line))


def _retrieve_token() -> str:
    token_file = open("./local/bot_token", "r")
    token_string = token_file.read()
    token_file.close()

    return token_string


bot.run(_retrieve_token())
