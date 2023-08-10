"""
   Copyright 2023 Kevin Emery

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

import common
import library.common as libCommon

from typing import List

from library.model.leagueinactivity import LeagueInactivity

from library.platforms.fleaflicker.fleaflicker import Fleaflicker
from library.platforms.sleeper.sleeper import Sleeper

DEFAULT_YEAR = libCommon.DEFAULT_YEAR
DEFAULT_LEAGUE_REGEX_STRING = ".*"
DEFAULT_PLATFORM = common.PlatformSelection.SLEEPER


def print_league_inactivity(leagues_with_inactivity: List[LeagueInactivity]):
    for inactive_league in leagues_with_inactivity:
        print("__**{league_name}**__".format(league_name=inactive_league.league.name))

        first_line_template = "**{user_name}**"
        last_transaction_template = "_Last transaction: {date}_"
        player_template = "{name}, {position} - {status}"
        date_format = "%m-%d-%Y"

        for roster in inactive_league.rosters:
            print(first_line_template.format(user_name=roster.team.manager.name))
            if roster.last_transaction is not None:
                print(
                    last_transaction_template.format(
                        date=roster.last_transaction.time.strftime(date_format)))

            for player in roster.inactive_players:
                print(
                    player_template.format(name=player.name,
                                           position=player.position,
                                           status=player.status))
            print("")


def get_all_league_inactivity(
    account_identifier: str,
    week: int,
    year: int = DEFAULT_YEAR,
    league_regex_string: str = DEFAULT_LEAGUE_REGEX_STRING,
    include_transactions: bool = True,
    teams_to_ignore: List[str] = [],
    only_teams: List[str] = [],
    player_names_to_ignore: List[str] = [],
    platform_selection: common.PlatformSelection = DEFAULT_PLATFORM,
) -> List[LeagueInactivity]:

    # Set platform based on user choice
    if platform_selection == common.PlatformSelection.SLEEPER:
        platform = Sleeper()
    elif platform_selection == common.PlatformSelection.FLEAFLICKER:
        platform = Fleaflicker()

    league_regex = re.compile(league_regex_string)

    leagues_with_inactivity = []

    user = platform.get_admin_user_by_identifier(account_identifier)
    leagues = platform.get_all_leagues_for_user(user, year, league_regex)

    for league in leagues:
        inactive_rosters = platform.get_inactive_rosters_for_league_and_week(
            league, week, year, teams_to_ignore, only_teams, player_names_to_ignore)

        if not inactive_rosters:
            continue

        if include_transactions:
            most_recent_transaction_per_roster = platform.get_last_transaction_for_teams_in_league(
                league)

            for roster in inactive_rosters:
                roster.last_transaction = most_recent_transaction_per_roster[
                    roster.team]

        leagues_with_inactivity.append(LeagueInactivity(league, inactive_rosters))

    return leagues_with_inactivity


def parse_user_provided_flags() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "-y",
        "--year",
        help="The year to run the analysis on, defaults to 2023",
        type=int,
        default=2023)
    parser.add_argument(
        "-r",
        "--league_regex",
        help="Regular expression used to select which leagues to analyze",
        type=str,
        default=".*")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--include_transactions",
        dest="include_transactions",
        action="store_true",
        help="Include last transaction data in the report (default)")
    group.add_argument("--exclude_transactions",
                       dest="include_transactions",
                       action="store_false")

    group = parser.add_mutually_exclusive_group()
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

    parser.add_argument("identifier",
                        help="User account used to pull all of the leagues",
                        type=str)
    parser.add_argument("week", help="The week to run analysis on", type=int)
    parser.add_argument("--players_to_ignore",
                        nargs='+',
                        type=str,
                        help="List of player names to ignore",
                        default=[])

    parser.set_defaults(include_transactions=True,
                        platform_selection=common.PlatformSelection.SLEEPER)

    return parser.parse_args()


def main(argv):
    args = parse_user_provided_flags()
    identifier = args.identifier
    year = args.year
    league_regex = args.league_regex
    week = args.week
    include_transactions = args.include_transactions
    platform_selection = args.platform_selection
    player_names_to_ignore = args.players_to_ignore

    inactive_leagues = get_all_league_inactivity(identifier, week, year=year,
                                                 league_regex_string=league_regex,
                                                 include_transactions=include_transactions,
                                                 player_names_to_ignore=player_names_to_ignore,
                                                 platform_selection=platform_selection)

    print_league_inactivity(inactive_leagues)


if __name__ == "__main__":
    main(sys.argv[1:])
