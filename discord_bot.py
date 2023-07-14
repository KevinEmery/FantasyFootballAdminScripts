import adp
import discord

from datetime import datetime
from typing import List

MESSAGE_LENGTH_LIMIT = 2000
MARKDOWN_CODE_BLOCK_BOUNDARY = "```\n"
FTA_ADP_THREAD_CONTENT = "The data here is for the FTA league format. \
These leagues are 14-team, 0.5 PPR Leagues that start \
1 QB, 2 RBs, 3 WRs, 1 TE, 1 W/R/T Flex, 1 K, and 1 DEF.\n\n"
ADP_GLOSSARY = "__**Glossary Terms**__\
```\n\
ADP: The average draft position across all drafts\n\
Min: The earliest a player was drafted\n\
Max: The latest a player was drafted\n\
N:   The number of times a player has been drafted\
```\n\
The designation \"X.Y\" represents a selection in Round X, at Pick Y"
ADP_FORMAT_NOTE = "Data is best viewed with a Desktop client. Each \
player should be on their own line."

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = discord.ext.commands.Bot(command_prefix='&', intents=intents)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')


@bot.command()
@discord.ext.commands.has_any_role("Commissioner", "League Admin")
async def post_fta_adps(ctx, forum: discord.ForumChannel):
    await post_fta_adp_all(ctx, forum)
    await post_fta_adp_wr(ctx, forum)
    await post_fta_adp_rb(ctx, forum)
    await post_fta_adp_te(ctx, forum)


@bot.command()
@discord.ext.commands.has_any_role("Commissioner", "League Admin")
async def post_fta_adp_all(ctx, forum: discord.ForumChannel):
    await _post_fta_position_adp(ctx, forum, adp.INCLUDE_ALL, "All Players")


@bot.command()
@discord.ext.commands.has_any_role("Commissioner", "League Admin")
async def post_fta_adp_wr(ctx, forum: discord.ForumChannel):
    await _post_fta_position_adp(ctx, forum, "WR", "Wide Receiver")


@bot.command()
@discord.ext.commands.has_any_role("Commissioner", "League Admin")
async def post_fta_adp_rb(ctx, forum: discord.ForumChannel):
    await _post_fta_position_adp(ctx, forum, "RB", "Running Back")


@bot.command()
@discord.ext.commands.has_any_role("Commissioner", "League Admin")
async def post_fta_adp_te(ctx, forum: discord.ForumChannel):
    await _post_fta_position_adp(ctx, forum, "TE", "Tight End")


@bot.command()
@discord.ext.commands.has_any_role("Commissioner", "League Admin")
async def post_fta_adp_k(ctx, forum: discord.ForumChannel):
    await _post_fta_position_adp(ctx, forum, "K", "Kicker")


@bot.command()
@discord.ext.commands.has_any_role("Commissioner", "League Admin")
async def post_fta_adp_def(ctx, forum: discord.ForumChannel):
    await _post_fta_position_adp(ctx, forum, "DEF", "Team Defense")


async def _post_fta_position_adp(ctx, forum: discord.ForumChannel, position_short: str, position_long: str):
    adp_data = adp.aggregate_adp_data("FTAFFL", 14, position=position_short, league_regex_string="^FTA \#\d+.*$")
    messages = _break_adp_content_into_messages(adp_data)
    thread_title = _get_formatted_date() + ": " + position_long
    thread_content = FTA_ADP_THREAD_CONTENT + ADP_GLOSSARY + ADP_FORMAT_NOTE
    thread = (await forum.create_thread(name=thread_title, content=thread_content))[0]
    for message in messages:
        await thread.send(message)


def _break_adp_content_into_messages(content: List[str], title: str = "") -> List[str]:
    split_content = []
    current_content = title + "\n\n" + MARKDOWN_CODE_BLOCK_BOUNDARY if title else MARKDOWN_CODE_BLOCK_BOUNDARY

    for line in content:
        if (MESSAGE_LENGTH_LIMIT - len(current_content)) < 2 * len(line):
            current_content += MARKDOWN_CODE_BLOCK_BOUNDARY
            split_content.append(current_content)
            current_content = MARKDOWN_CODE_BLOCK_BOUNDARY

        current_content += line + "\n"

    if current_content != MARKDOWN_CODE_BLOCK_BOUNDARY:
        current_content += MARKDOWN_CODE_BLOCK_BOUNDARY
        split_content.append(current_content)

    return split_content


def _get_formatted_date() -> str:
    now = datetime.now()
    return now.strftime("%m/%d/%y")


def _retrieve_token() -> str:
    token_file = open("./local/bot_token", "r")
    token_string = token_file.read()
    token_file.close()

    return token_string


bot.run(_retrieve_token())
