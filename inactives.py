import argparse
import re
import sys

import common

from typing import List

from library.model.inactiveroster import InactiveRoster
from library.model.league import League
from library.model.user import User

from library.platforms.platform import Platform
from library.platforms.fleaflicker.fleaflicker import Fleaflicker
from library.platforms.sleeper.sleeper import Sleeper


def print_inactive_rosters(league: League, rosters: List[InactiveRoster]):
    print("\n__**{league_name}**__".format(league_name=league.name))

    first_line_template = "\n**{user_name}**"
    last_transaction_template = "_Last transaction: {date}_"
    player_template = "{name}, {position} - {status}"
    date_format = "%m-%d-%Y"

    for roster in rosters:
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


def parse_user_provided_flags() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "-y",
        "--year",
        help="The year to run the analysis on, defaults to 2022",
        type=int,
        default=2022)
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
                       const=common.PlatformSelection.SLEEPER)
    group.add_argument("--fleaflicker",
                       dest="platform_selection",
                       action="store_const",
                       const=common.PlatformSelection.FLEAFLICKER)
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
    league_regex = re.compile(args.league_regex)
    week = args.week
    include_transactions = args.include_transactions
    player_names_to_ignore = args.players_to_ignore

    # Set platform based on user choice
    if args.platform_selection == common.PlatformSelection.SLEEPER:
        platform = Sleeper()
    elif args.platform_selection == common.PlatformSelection.FLEAFLICKER:
        platform = Fleaflicker()
        print("Not implemented for Fleaflicker")
        return -1

    user = platform.get_admin_user_by_identifier(identifier)
    leagues = platform.get_all_leagues_for_user(user, year, league_regex)

    for league in leagues:
        inactive_rosters = platform.get_inactive_rosters_for_league_and_week(
            league, week, player_names_to_ignore)

        if not inactive_rosters:
            continue

        if include_transactions:
            most_recent_transaction_per_roster = platform.get_last_transaction_for_teams_in_league(
                league)

            for roster in inactive_rosters:
                roster.last_transaction = most_recent_transaction_per_roster[
                    roster.team]

        print_inactive_rosters(league, inactive_rosters)


if __name__ == "__main__":
    main(sys.argv[1:])
