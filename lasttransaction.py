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

from typing import List

from library.model.league import League
from library.model.team import Team
from library.model.transaction import Transaction
from library.model.user import User

from library.platforms.platform import Platform
from library.platforms.fleaflicker.fleaflicker import Fleaflicker
from library.platforms.sleeper.sleeper import Sleeper


def print_recent_transaction_data(league_name: str,
                                  transactions: List[Transaction]):

    print(league_name)
    for transaction in transactions:
        print(format_most_recent_transaction(transaction))
    print("")


def format_most_recent_transaction(transaction: Transaction) -> str:
    template = "{username:<20}type: {type:<15}date: {formatted_date}"
    formatted_date = transaction.time.strftime("%m-%d-%Y")

    return template.format(username=transaction.team.manager.name,
                           type=transaction.transaction_type,
                           formatted_date=formatted_date)


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
                        help="User identifier used to pull all of the leagues",
                        type=str)

    parser.set_defaults(platform_selection=common.PlatformSelection.SLEEPER)
    return parser.parse_args()


def main(argv):
    args = parse_user_provided_flags()
    identifier = args.identifier
    year = args.year
    league_regex = re.compile(args.league_regex)

    # Set platform based on user choice
    if args.platform_selection == common.PlatformSelection.SLEEPER:
        platform = Sleeper()
    elif args.platform_selection == common.PlatformSelection.FLEAFLICKER:
        platform = Fleaflicker()

    user = platform.get_admin_user_by_identifier(identifier)
    leagues = platform.get_all_leagues_for_user(user, year, league_regex)

    for league in leagues:
        team_to_last_transaction = platform.get_last_transaction_for_teams_in_league(
            league)

        print_recent_transaction_data(
            league.name, sorted(team_to_last_transaction.values(),
                                reverse=True))


if __name__ == "__main__":
    main(sys.argv[1:])
