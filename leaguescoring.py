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

import common
import library.common as libCommon

from typing import List

from library.model.seasonscore import SeasonScore
from library.model.weeklyscore import WeeklyScore

from library.platforms.fleaflicker.fleaflicker import Fleaflicker
from library.platforms.sleeper.sleeper import Sleeper


DEFAULT_LEAGUE_REGEX_STRING = ".*"
DEFAULT_PLATFORM = common.PlatformSelection.SLEEPER


class ScoringResults(object):
    def __init__(self):
        self.max_weekly_scores: List[WeeklyScore] = []
        self.min_weekly_scores: List[WeeklyScore] = []
        self.max_scores_this_week: List[WeeklyScore] = []
        self.min_scores_this_week: List[WeeklyScore] = []
        self.max_season_scores: List[SeasonScore] = []
        self.min_season_scores: List[SeasonScore] = []


def get_scoring_results(
    account_identifier: str,
    starting_week: int,
    ending_week: int,
    get_weekly_results: bool,
    get_current_weeks_results: bool,
    get_season_results: bool,
    get_max_scores: bool,
    get_min_scores: bool,
    year: int = libCommon.DEFAULT_YEAR,
    league_regex_string: str = DEFAULT_LEAGUE_REGEX_STRING,
    platform_selection: common.PlatformSelection = DEFAULT_PLATFORM,
) -> ScoringResults:

    # Lists containing the raw data from the backend
    weekly_scores = []
    season_scores = []
    results = ScoringResults()
    
    # Set platform based on user choice
    if platform_selection == common.PlatformSelection.SLEEPER:
        platform = Sleeper()
    elif platform_selection == common.PlatformSelection.FLEAFLICKER:
        platform = Fleaflicker()

    find_weekly = get_weekly_results or get_current_weeks_results
    find_max_this_week = get_max_scores and get_current_weeks_results
    find_min_this_week = get_min_scores and get_current_weeks_results
    find_max_weekly = get_weekly_results and get_max_scores
    find_min_weekly = get_weekly_results and get_min_scores
    find_season = get_season_results
    find_max_season = get_season_results and get_max_scores
    find_min_season = get_season_results and get_min_scores

    user = platform.get_admin_user_by_identifier(account_identifier)
    leagues = platform.get_all_leagues_for_user(user, year, re.compile(league_regex_string))

    for league in leagues:
        # Iterate over each indiviudal week, since we need to grab the max weekly score for the league
        if find_weekly:
            for week_num in range(starting_week, ending_week + 1):
                weekly_scores.extend(
                    platform.get_weekly_scores_for_league_and_week(
                        league, week_num, year))

        if find_season:
            # Grab the points-for in each league
            season_scores.extend(
                platform.get_season_scores_for_league(league, year))

    # Sort all of the lists
    if find_season:
        max_season_scores = season_scores.copy()
        max_season_scores.sort(
            key=lambda annual_score: annual_score.score, reverse=True)
        min_season_scores = season_scores.copy()
        min_season_scores.sort(
            key=lambda annual_score: annual_score.score)
    if find_weekly:
        max_weekly_scores = weekly_scores.copy()
        max_weekly_scores.sort(key=lambda weekly_score: weekly_score.score,
                               reverse=True)
        min_weekly_scores = weekly_scores.copy()
        min_weekly_scores.sort(key=lambda weekly_score: weekly_score.score)
        max_scores_this_week = list(
            filter(lambda weekly_score: weekly_score.week == ending_week,
                   max_weekly_scores.copy()))
        min_scores_this_week = list(
            filter(lambda weekly_score: weekly_score.week == ending_week,
                   min_weekly_scores.copy()))

    # Construct the results object based on the specified flags
    if find_max_this_week:
        results.max_scores_this_week = max_scores_this_week
    if find_min_this_week:
        results.min_scores_this_week = min_scores_this_week
    if find_max_weekly:
        results.max_weekly_scores = max_weekly_scores
    if find_min_weekly:
        results.min_weekly_scores = min_weekly_scores
    if find_max_season:
        results.max_season_scores = max_season_scores
    if find_min_season:
        results.min_season_scores = min_season_scores

    return results


def parse_user_provided_flags() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "-wc",
        "--weekly_count",
        help="number of weekly data points to display (default: 5)",
        type=int,
        default=5)
    parser.add_argument(
        "-sc",
        "--season_count",
        help="number of season data points to display (default: 5)",
        type=int,
        default=5)
    parser.add_argument(
        "-y",
        "--year",
        help="The year to run the analysis on, defaults to 2024",
        type=int,
        default=libCommon.DEFAULT_YEAR)
    parser.add_argument(
        "-r",
        "--league_regex",
        help="Regular expression used to select which leagues to analyze",
        type=str,
        default=DEFAULT_LEAGUE_REGEX_STRING)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--max",
                       dest="max",
                       action="store_true",
                       help="Include the 'max' statistics (default)")
    group.add_argument("--no-max", dest="max", action="store_false")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--min",
                       dest="min",
                       action="store_true",
                       help="Include the 'min' statistics (default)")
    group.add_argument("--no-min", dest="min", action="store_false")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--season",
                       dest="season",
                       action="store_true",
                       help="Include the 'season' statistics (default)")
    group.add_argument("--no-season", dest="season", action="store_false")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--weekly",
                       dest="weekly",
                       action="store_true",
                       help="Include the 'weekly' statistics (default)")
    group.add_argument("--no-weekly", dest="weekly", action="store_false")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--current-week",
                       dest="current_week",
                       action="store_true",
                       help="Include the 'current week' statistics (default)")
    group.add_argument("--no-current-week",
                       dest="current_week",
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

    parser.set_defaults(max=True,
                        min=True,
                        season=True,
                        weekly=True,
                        current_week=True,
                        platform_selection=DEFAULT_PLATFORM)

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
    get_weekly = args.weekly
    get_season = args.season
    get_min = args.min
    get_max = args.max
    get_current_week = args.current_week
    weekly_score_output_count = args.weekly_count
    seasonal_score_output_count = args.season_count
    platform_selection = args.platform_selection

    results = get_scoring_results(identifier, starting_week, ending_week, get_weekly,
                                  get_current_week, get_season, get_max, get_min, year, league_regex_string, platform_selection)

    # Print out the results
    this_week_template = "{main_header}, Week {week_num}"
    if results.max_scores_this_week:
        common.print_weekly_scores_with_header(
            results.max_scores_this_week,
            this_week_template.format(main_header="HIGHEST SCORES THIS WEEK",
                                      week_num=ending_week),
            weekly_score_output_count)
    if results.min_scores_this_week:
        common.print_weekly_scores_with_header(
            results.min_scores_this_week,
            this_week_template.format(main_header="LOWEST SCORES THIS WEEK",
                                      week_num=ending_week),
            weekly_score_output_count)
    if results.max_weekly_scores:
        common.print_weekly_scores_with_header(
            results.max_weekly_scores, "HIGHEST WEEKLY SCORES THIS SEASON",
            weekly_score_output_count)
    if results.min_weekly_scores:
        common.print_weekly_scores_with_header(
            results.min_weekly_scores, "LOWEST WEEKLY SCORES THIS SEASON",
            weekly_score_output_count)
    if results.max_season_scores:
        common.print_season_scores_with_header(
            results.max_season_scores, "HIGHEST POINTS-FOR THIS SEASON",
            seasonal_score_output_count)
    if results.min_season_scores:
        common.print_season_scores_with_header(
            results.min_season_scores, "LOWEST POINTS-FOR THIS SEASON",
            seasonal_score_output_count)


if __name__ == "__main__":
    main(sys.argv[1:])
