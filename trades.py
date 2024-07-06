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

import argparse
import re
import sys

from datetime import datetime
from dateutil import parser
from typing import List

import common
import library.common as libCommon

from library.model.league import League
from library.model.player import Player
from library.model.trade import Trade
from library.model.user import User

from library.platforms.platform import Platform
from library.platforms.fleaflicker.fleaflicker import Fleaflicker
from library.platforms.sleeper.sleeper import Sleeper

# Needs to be large enough for longest player name plus a couple (MVS)
OUTPUT_COLUMN_WIDTH = 30

DEFAULT_LEAGUE_REGEX_STRING = ".*"
DEFAULT_START = "12-31-1999"
DEFAULT_END = "12-31-2099"
DEFAULT_PLATFORM = common.PlatformSelection.SLEEPER


def _filter_and_sort_trades_by_date(trades: List[Trade], start: datetime,
                                    end: datetime) -> List[Trade]:
    filtered_trades = list(
        filter(
            lambda trade: trade.trade_time < end and trade.trade_time > start,
            trades))
    filtered_trades.sort()
    return filtered_trades


# Utility function that abstracts away the constant newlines, and makes it easier to
# rewrite this class to return strings instead of printing from the helpers.
def _append_with_newline(base: str, new_content: str) -> str:
    return base + new_content + "\n"


# Format all of the league's trades using Discord markdown formatting
def format_trades(trades: List[Trade]) -> str:
    output = ""
    for trade in trades:
        output = _append_with_newline(output, "__**" + trade.league.name + "**__\n")
        # Switch based on the trade size. Two team trades have a better visualization but
        # it's hard to do that for trades with more than 2.
        if len(trade.details) == 2:
            output = _append_with_newline(output, _format_two_team_trade(trade))
        else:
            output = _append_with_newline(output, _format_larger_trade(trade))

    return output


def _format_two_team_trade(trade: Trade) -> str:
    output = ""

    # Define the template variables
    manager_template = "**Team {number}: [{manager}](<{roster_link}>)**"
    date_template = "%m-%d-%Y"

    # Extract the information from the trade
    trade_detail = trade.details[0]

    team_a_adds = []
    team_b_adds = []

    for player in trade.details[0].added_players:
        team_a_adds.append(_format_player_string(player))
    for pick in trade.details[0].added_draft_picks:
        team_a_adds.append(pick)
    if trade.details[0].faab_added > 0:
        team_a_adds.append(_format_faab(trade_detail.faab_added))

    for player in trade.details[1].added_players:
        team_b_adds.append(_format_player_string(player))
    for pick in trade.details[1].added_draft_picks:
        team_b_adds.append(pick)
    if trade.details[1].faab_added > 0:
        team_b_adds.append(_format_faab(trade_detail.faab_lost))

    # Output the trade itself
    output = _append_with_newline(output, "Trade on " + trade.trade_time.strftime(date_template))
    output = _append_with_newline(output,
                                  manager_template.format(number="A",
                                                          manager=trade.details[0].team.manager.name,
                                                          roster_link=trade.details[0].team.roster_link))
    output = _append_with_newline(output,
                                  manager_template.format(number="B",
                                                          manager=trade.details[1].team.manager.name,
                                                          roster_link=trade.details[1].team.roster_link))

    # Preferred format, but looks bad on mobile
    # output += _format_side_by_side_table(team_a_adds, team_b_adds)

    # Formats well on desktop and mobile
    output += _format_two_separate_tables(team_a_adds, team_b_adds)

    return output


def _format_side_by_side_table(team_a_adds: List[str], team_b_adds: List[str]) -> str:
    output = ""

    # Define the templates
    header_template = "|{team_a:^{column_width}}|{team_b:^{column_width}}|"
    row_template = "|{player_a:^{column_width}}|{player_b:^{column_width}}|"

    # Print the table
    output = _append_with_newline(output, "```")
    output = _append_with_newline(output, "=" * (OUTPUT_COLUMN_WIDTH * 2 + 3))
    output = _append_with_newline(output,
                                  header_template.format(team_a="Team A Gained",
                                                         team_b="Team B Gained",
                                                         column_width=OUTPUT_COLUMN_WIDTH))
    output = _append_with_newline(output, "|" + "=" * (OUTPUT_COLUMN_WIDTH * 2 + 1) + "|")

    for i in range(0, max(len(team_a_adds), len(team_b_adds))):
        player_a = ''
        player_b = ''
        if i < len(team_a_adds):
            player_a = team_a_adds[i]
        if i < len(team_b_adds):
            player_b = team_b_adds[i]
        output = _append_with_newline(output,
                                      row_template.format(player_a=player_a,
                                                          player_b=player_b,
                                                          column_width=OUTPUT_COLUMN_WIDTH))

    output = _append_with_newline(output, "=" * (OUTPUT_COLUMN_WIDTH * 2 + 3))
    output = _append_with_newline(output, "```")

    return output


def _format_two_separate_tables(team_a_adds: List[str], team_b_adds: List[str]) -> str:
    output = ""

    output = _append_with_newline(output, "```")
    output += _format_single_team_adds("Team A Gained", team_a_adds)
    output += _format_single_team_adds("Team B Gained", team_b_adds)
    output = _append_with_newline(output, "```")

    return output


def _format_single_team_adds(header_text: str, players: List[str]):
    output = ""

    # Define the templates
    template = "|{text:^{column_width}}|"

    # Print the table
    output = _append_with_newline(output, "=" * (OUTPUT_COLUMN_WIDTH + 2))
    output = _append_with_newline(output, template.format(text=header_text, column_width=OUTPUT_COLUMN_WIDTH))
    output = _append_with_newline(output, "|" + "=" * OUTPUT_COLUMN_WIDTH + "|")

    for i in range(0, len(players)):
        output = _append_with_newline(output,
                                      template.format(text=players[i], column_width=OUTPUT_COLUMN_WIDTH))

    output = _append_with_newline(output, "=" * (OUTPUT_COLUMN_WIDTH + 2))

    return output


def _format_larger_trade(trade: Trade) -> str:
    output = ""

    output = _append_with_newline(output, "Trade on " + trade.trade_time.strftime("%m-%d-%Y"))
    for trade_detail in trade.details:
        output = _append_with_newline(output, "**Team: [{name}](<{roster_link}>)**".format(name=trade_detail.team.manager.name, roster_link=trade_detail.team.roster_link))
        if len(trade_detail.added_players) > 0 or len(
                trade_detail.added_draft_picks
        ) > 0 or trade_detail.faab_added > 0:
            output = _append_with_newline(output, "*Traded For*")
        for player in trade_detail.added_players:
            output = _append_with_newline(output, "    " + _format_player_string(player))
        for pick in trade_detail.added_draft_picks:
            output = _append_with_newline(output, "    " + pick)
        if trade_detail.faab_added > 0:
            output = _append_with_newline(output, "    " + _format_faab(trade_detail.faab_added))
        if len(trade_detail.lost_players) > 0 or len(
                trade_detail.lost_draft_picks
        ) > 0 or trade_detail.faab_lost > 0:
            output = _append_with_newline(output, "*Traded Away*")
        for player in trade_detail.lost_players:
            output = _append_with_newline(output, "    " + _format_player_string(player))
        for pick in trade_detail.lost_draft_picks:
            output = _append_with_newline(output, "    " + pick)
        if trade_detail.faab_lost > 0:
            output = _append_with_newline(output, "    " + _format_faab(trade_detail.faab_lost))
        output += "\n"

    return output


def _format_player_string(player: Player) -> str:
    template = "{name} ({position})"
    return template.format(name=player.name, position=player.position)


def _format_faab(faab: int) -> str:
    template = "${number} FAAB"
    return template.format(number=faab)


def _parse_user_provided_flags() -> argparse.Namespace:
    arg_parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter)
    arg_parser.add_argument(
        "-y",
        "--year",
        help="The year to run the analysis on, defaults to 2024",
        type=int,
        default=libCommon.DEFAULT_YEAR)
    arg_parser.add_argument(
        "-r",
        "--league_regex",
        help="Regular expression used to select which leagues to analyze",
        type=str,
        default=DEFAULT_LEAGUE_REGEX_STRING)
    arg_parser.add_argument("-s",
                            "--start",
                            help="First date for trade analysis",
                            type=str,
                            default=DEFAULT_START)
    arg_parser.add_argument("-e",
                            "--end",
                            help="Last date for trade analysis",
                            type=str,
                            default=DEFAULT_END)

    group = arg_parser.add_mutually_exclusive_group()
    group.add_argument("--sleeper",
                       dest="platform_selection",
                       action="store_const",
                       const=common.PlatformSelection.SLEEPER,
                       help="Run analysis on Sleeper leagues (default)")
    group.add_argument("--fleaflicker",
                       dest="platform_selection",
                       action="store_const",
                       const=common.PlatformSelection.FLEAFLICKER,
                       help="Run analysis on Fleaflicker leagues")

    arg_parser.add_argument(
        "identifier",
        help="User account used to pull all of the leagues",
        type=str)

    arg_parser.set_defaults(
        platform_selection=common.PlatformSelection.SLEEPER)

    return arg_parser.parse_args()


def fetch_and_filter_trades(
    account_identifier: str,
    year: int = libCommon.DEFAULT_YEAR,
    league_regex_string: str = DEFAULT_LEAGUE_REGEX_STRING,
    start_date_string: str = DEFAULT_START,
    end_date_string: str = DEFAULT_END,
    platform_selection: common.PlatformSelection = DEFAULT_PLATFORM
) -> List[Trade]:
    if platform_selection == common.PlatformSelection.SLEEPER:
        platform = Sleeper()
    elif platform_selection == common.PlatformSelection.FLEAFLICKER:
        platform = Fleaflicker()

    user = platform.get_admin_user_by_identifier(account_identifier)
    leagues = platform.get_all_leagues_for_user(user, year, re.compile(league_regex_string))
    trades = []

    for league in leagues:
        trades.extend(platform.get_all_trades_for_league(league, year))

    filtered_trades = _filter_and_sort_trades_by_date(
        trades, parser.parse(start_date_string), parser.parse(end_date_string))

    return filtered_trades


def main(argv):
    args = _parse_user_provided_flags()
    filtered_trades = fetch_and_filter_trades(
        args.identifier, args.year, args.league_regex, args.start, args.end, args.platform_selection)

    if filtered_trades:
        print(format_trades(filtered_trades))


if __name__ == "__main__":
    main(sys.argv[1:])
