import argparse
import re
import sys

from datetime import datetime
from dateutil import parser
from enum import Enum
from typing import List

import common

from library.model.league import League
from library.model.player import Player
from library.model.trade import Trade
from library.model.user import User

from library.platforms.platform import Platform
from library.platforms.fleaflicker.fleaflicker import Fleaflicker
from library.platforms.sleeper.sleeper import Sleeper

# Needs to be large enough for longest player name plus a couple (MVS)
OUTPUT_COLUMN_WIDTH = 30


def filter_and_sort_trades_by_date(trades: List[Trade], start: datetime,
                                   end: datetime) -> List[Trade]:
    filtered_trades = list(
        filter(
            lambda trade: trade.trade_time < end and trade.trade_time > start,
            trades))
    filtered_trades.sort()
    return filtered_trades


# Format all of the league's trades using Discord markdown formatting
def print_league_trades(league: League, trades: List[Trade]):
    print("__**" + league.name + "**__\n")

    for trade in trades:
        # Switch based on the trade size. Two team trades have a better visualization but
        # it's hard to do that for trades with more than 2.
        if len(trade.details) == 2:
            print_two_team_trade(trade)
        else:
            print_larger_trade(trade)


def print_two_team_trade(trade: Trade):

    # Define the template variables
    manager_template = "**Team {number}: {manager}** - {roster_link}"
    date_template = "%m-%d-%Y"

    # Extract the information from the trade
    trade_detail = trade.details[0]

    team_a_adds = []
    team_b_adds = []

    for player in trade.details[0].added_players:
        team_a_adds.append(format_player_string(player))
    for pick in trade.details[0].added_draft_picks:
        team_a_adds.append(pick)
    if trade.details[0].faab_added > 0:
        team_a_adds.append(format_faab(trade_detail.faab_added))

    for player in trade.details[1].added_players:
        team_b_adds.append(format_player_string(player))
    for pick in trade.details[1].added_draft_picks:
        team_b_adds.append(pick)
    if trade.details[1].faab_added > 0:
        team_b_adds.append(format_faab(trade_detail.faab_added))

    # Output the trade itself
    print("Trade on " + trade.trade_time.strftime(date_template))
    print(
        manager_template.format(number="A",
                                manager=trade.details[0].team.manager.name,
                                roster_link=trade.details[0].team.roster_link))
    print(
        manager_template.format(number="B",
                                manager=trade.details[1].team.manager.name,
                                roster_link=trade.details[1].team.roster_link))

    # Preferred format, but looks bad on mobile
    # print_side_by_side_table(team_a_adds, team_b_adds)

    # Formats well on desktop and mobile
    print_two_separate_tables(team_a_adds, team_b_adds)


def print_side_by_side_table(team_a_adds: List[str], team_b_adds: List[str]):
    # Define the templates
    header_template = "|{team_a:^{column_width}}|{team_b:^{column_width}}|"
    row_template = "|{player_a:^{column_width}}|{player_b:^{column_width}}|"

    # Print the table
    print("```")
    print("=" * (OUTPUT_COLUMN_WIDTH * 2 + 3))
    print(
        header_template.format(team_a="Team A Gained",
                               team_b="Team B Gained",
                               column_width=OUTPUT_COLUMN_WIDTH))
    print("|" + "=" * (OUTPUT_COLUMN_WIDTH * 2 + 1) + "|")

    for i in range(0, max(len(team_a_adds), len(team_b_adds))):
        player_a = ''
        player_b = ''
        if i < len(team_a_adds):
            player_a = team_a_adds[i]
        if i < len(team_b_adds):
            player_b = team_b_adds[i]
        print(
            row_template.format(player_a=player_a,
                                player_b=player_b,
                                column_width=OUTPUT_COLUMN_WIDTH))

    print("=" * (OUTPUT_COLUMN_WIDTH * 2 + 3))
    print("```\n")


def print_two_separate_tables(team_a_adds: List[str], team_b_adds: List[str]):
    print("```")
    print_single_team_adds("Team A Gained", team_a_adds)
    print_single_team_adds("Team B Gained", team_b_adds)
    print("```\n")


def print_single_team_adds(header_text: str, players: List[str]):

    # Define the templates
    template = "|{text:^{column_width}}|"

    # Print the table
    print("=" * (OUTPUT_COLUMN_WIDTH + 2))
    print(template.format(text=header_text, column_width=OUTPUT_COLUMN_WIDTH))
    print("|" + "=" * OUTPUT_COLUMN_WIDTH + "|")

    for i in range(0, len(players)):
        print(
            template.format(text=players[i], column_width=OUTPUT_COLUMN_WIDTH))

    print("=" * (OUTPUT_COLUMN_WIDTH + 2))


def print_larger_trade(trade: Trade):
    print("Trade on " + trade.trade_time.strftime("%m-%d-%Y"))
    for trade_detail in trade.details:
        print("**Team Manager: " + trade_detail.team.manager.name + "**")
        print("Roster link: " + trade_detail.team.roster_link)
        if len(trade_detail.added_players) > 0 or len(
                trade_detail.added_draft_picks
        ) > 0 or trade_detail.faab_added > 0:
            print("*Traded For*")
        for player in trade_detail.added_players:
            print("    " + format_player_string(player))
        for pick in trade_detail.added_draft_picks:
            print("    " + pick)
        if trade_detail.faab_added > 0:
            print("    " + format_faab(trade_detail.faab_added))
        if len(trade_detail.lost_players) > 0 or len(
                trade_detail.lost_draft_picks
        ) > 0 or trade_detail.faab_lost > 0:
            print("*Traded Away*")
        for player in trade_detail.lost_players:
            print("    " + format_player_string(player))
        for pick in trade_detail.lost_draft_picks:
            print("    " + pick)
        if trade_detail.faab_lost > 0:
            print("    " + format_faab(trade_detail.faab_lost))
        print("")


def format_player_string(player: Player) -> str:
    template = "{name} ({position})"
    return template.format(name=player.name, position=player.position)


def format_faab(faab: int) -> str:
    template = "${number} FAAB"
    return template.format(number=faab)


def parse_user_provided_flags() -> argparse.Namespace:
    arg_parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter)
    arg_parser.add_argument(
        "-y",
        "--year",
        help="The year to run the analysis on, defaults to 2022",
        type=int,
        default=2022)
    arg_parser.add_argument(
        "-r",
        "--league_regex",
        help="Regular expression used to select which leagues to analyze",
        type=str,
        default=".*")
    arg_parser.add_argument("-s",
                            "--start",
                            help="First date for trade analysis",
                            type=str,
                            default="12-31-1999")
    arg_parser.add_argument("-e",
                            "--end",
                            help="Last date for trade analysis",
                            type=str,
                            default="12-31-2099")
    group = arg_parser.add_mutually_exclusive_group()
    group.add_argument("--sleeper",
                       dest="platform_selection",
                       action="store_const",
                       const=common.PlatformSelection.SLEEPER)
    group.add_argument("--fleaflicker",
                       dest="platform_selection",
                       action="store_const",
                       const=common.PlatformSelection.FLEAFLICKER)

    arg_parser.add_argument(
        "identifier",
        help="User account used to pull all of the leagues",
        type=str)

    arg_parser.set_defaults(
        platform_selection=common.PlatformSelection.SLEEPER)

    return arg_parser.parse_args()


def main(argv):
    args = parse_user_provided_flags()
    identifier = args.identifier
    year = args.year
    league_regex = re.compile(args.league_regex)
    start_date = parser.parse(args.start)
    end_date = parser.parse(args.end)

    # Set platform based on user choice
    if args.platform_selection == common.PlatformSelection.SLEEPER:
        platform = Sleeper()
    elif args.platform_selection == common.PlatformSelection.FLEAFLICKER:
        platform = Fleaflicker()

    user = platform.get_admin_user_by_identifier(identifier)
    all_leagues = platform.get_all_leagues_for_user(user)
    leagues_to_analyze = common.filter_leagues_by_league_name(
        all_leagues, league_regex)

    for league in leagues_to_analyze:
        league_trades = platform.get_all_trades_for_league(league)
        filtered_league_trades = filter_and_sort_trades_by_date(
            league_trades, start_date, end_date)

        if filtered_league_trades:
            print_league_trades(league, filtered_league_trades)


if __name__ == "__main__":
    main(sys.argv[1:])
