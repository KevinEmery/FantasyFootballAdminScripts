import argparse
import re
import sys

import common

from library.model.league import League
from library.model.user import User
from library.model.weeklyscore import WeeklyScore

from library.platforms.platform import Platform
from library.platforms.fleaflicker.fleaflicker import Fleaflicker
from library.platforms.sleeper.sleeper import Sleeper


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
    group.add_argument("--sleeper",
                       dest="platform_selection",
                       action="store_const",
                       const=common.PlatformSelection.SLEEPER)
    group.add_argument("--fleaflicker",
                       dest="platform_selection",
                       action="store_const",
                       const=common.PlatformSelection.FLEAFLICKER)
    parser.add_argument("identifier",
                        help="User identifier used to pull all of the leagues",
                        type=str)
    parser.add_argument(
        "start",
        help="the starting week for data collection (default: 1)",
        type=int,
        default=1,
        nargs='?')
    parser.add_argument("end",
                        help="the ending week for data collection",
                        type=int)

    parser.set_defaults(platform_selection=common.PlatformSelection.SLEEPER)

    return parser.parse_args()


def main(argv):
    # Parse all of the user-provided flags
    args = parse_user_provided_flags()

    # Convert the computed args into our more-verbose local fields
    identifier = args.identifier
    year = args.year
    league_regex = re.compile(args.league_regex)
    starting_week = args.start
    ending_week = args.end

    # Set platform based on user choice
    if args.platform_selection == common.PlatformSelection.SLEEPER:
        platform = Sleeper()
    elif args.platform_selection == common.PlatformSelection.FLEAFLICKER:
        platform = Fleaflicker()

    # Lists containing all of the collated data
    top_scores = []

    user = platform.get_admin_user_by_identifier(identifier)
    leagues = platform.get_all_leagues_for_user(user, year, league_regex)

    for league in leagues:
        weekly_scores = []
        for week_num in range(starting_week, ending_week + 1):
            weekly_scores.extend(
                platform.get_weekly_scores_for_league_and_week(
                    league, week_num, year))

        weekly_scores.sort(key=lambda weekly_score: weekly_score.score,
                           reverse=True)

        if len(weekly_scores) > 0:
            top_scores.append(weekly_scores[0])

    top_scores.sort(key=lambda weekly_score: weekly_score.league.name)
    common.print_weekly_scores_with_header(top_scores,
                                           "TOP WEEKLY SCORE IN EACH LEAGUE")


if __name__ == "__main__":
    main(sys.argv[1:])