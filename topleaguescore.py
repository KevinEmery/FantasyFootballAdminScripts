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

from library.model.weeklyscore import WeeklyScore

from library.platforms.fleaflicker.fleaflicker import Fleaflicker
from library.platforms.sleeper.sleeper import Sleeper

DEFAULT_YEAR = libCommon.DEFAULT_YEAR
DEFAULT_LEAGUE_REGEX_STRING = ".*"
DEFAULT_PLATFORM = common.PlatformSelection.SLEEPER

def get_top_weekly_score_for_each_league(account_identifier: str,
                                         starting_week: int,
                                         ending_week: int,
                                         year: int = DEFAULT_YEAR,
                                         league_regex_string: str = DEFAULT_LEAGUE_REGEX_STRING,
                                         platform_selection: common.PlatformSelection = DEFAULT_PLATFORM,) -> List[WeeklyScore]:

    if platform_selection == common.PlatformSelection.SLEEPER:
        platform = Sleeper()
    elif platform_selection == common.PlatformSelection.FLEAFLICKER:
        platform = Fleaflicker()

    league_regex = re.compile(league_regex_string)

    top_scores = []

    user = platform.get_admin_user_by_identifier(account_identifier)
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

    return top_scores


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
    league_regex_string = args.league_regex
    starting_week = args.start
    ending_week = args.end
    platform_selection = args.platform_selection

    top_scores = get_top_weekly_score_for_each_league(
        identifier, starting_week, ending_week, year, league_regex_string, platform_selection)

    common.print_weekly_scores_with_header(top_scores,
                                           "TOP WEEKLY SCORE IN EACH LEAGUE")


if __name__ == "__main__":
    main(sys.argv[1:])
