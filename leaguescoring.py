import argparse
import re
import sys

from typing import List

import common

from library.model.league import League
from library.model.seasonscore import SeasonScore
from library.model.user import User
from library.model.weeklyscore import WeeklyScore

from library.platforms.platform import Platform
from library.platforms.fleaflicker.fleaflicker import Fleaflicker
from library.platforms.sleeper.sleeper import Sleeper


def print_weekly_scores_with_header(scores: List[WeeklyScore],
                                    header_text: str, count: int):
    if not scores:
        return

    print(header_text)
    for i in range(0, count):
        if i < len(scores):
            print(common.format_weekly_score_for_table(scores[i]))
        else:
            break
    print("")


def print_season_scores_with_header(scores: List[SeasonScore],
                                    header_text: str, count: int):
    if not scores:
        return

    print(header_text)
    for i in range(0, count):
        if i < len(scores):
            print(common.format_seasonal_score_for_table(scores[i]))
        else:
            break
    print("")


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

    parser.set_defaults(max=True,
                        min=True,
                        season=True,
                        weekly=True,
                        current_week=True)

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
    weekly_score_output_count = args.weekly_count
    seasonal_score_output_count = args.season_count
    find_weekly = args.weekly or args.current_week
    print_max_this_week = args.max and args.current_week
    print_min_this_week = args.min and args.current_week
    print_max_weekly = args.weekly and args.max
    print_min_weekly = args.weekly and args.min
    find_seasonal = args.season
    print_max_seasonal = args.season and args.max
    print_min_seasonal = args.season and args.min

    # Set platform based on user choice
    if args.platform_selection == common.PlatformSelection.SLEEPER:
        platform = Sleeper()
        raise Exception("Unimplemented")
    elif args.platform_selection == common.PlatformSelection.FLEAFLICKER:
        platform = Fleaflicker()

    # Lists containing all of the collated data
    weekly_scores = []
    seasonal_scores = []

    user = platform.get_admin_user_by_identifier(identifier)
    leagues = platform.get_all_leagues_for_user(user, year, league_regex)

    for league in leagues:
        # Iterate over each indiviudal week, since we need to grab the max weekly score for the league
        if find_weekly:
            for week_num in range(starting_week, ending_week + 1):
                weekly_scores.extend(
                    platform.get_weekly_scores_for_league_and_week(
                        league, week_num, year))

        if find_seasonal:
            # Grab the points-for in each league
            seasonal_scores.extend(
                platform.get_season_scores_for_league(league, year))

    # Sublists used for sorted results
    max_weekly_scores = []
    min_weekly_scores = []
    max_scores_this_week = []
    min_scores_this_week = []
    max_seasonal_points_for = []
    min_seasonal_points_for = []

    # Sort all of the lists
    if find_seasonal:
        max_seasonal_points_for = seasonal_scores.copy()
        max_seasonal_points_for.sort(
            key=lambda annual_score: annual_score.score, reverse=True)
        min_seasonal_points_for = seasonal_scores.copy()
        min_seasonal_points_for.sort(
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

    # Print out the results
    this_week_template = "{main_header}, Week {week_num}"
    if print_max_this_week:
        print_weekly_scores_with_header(
            max_scores_this_week,
            this_week_template.format(main_header="HIGHEST SCORES THIS WEEK",
                                      week_num=ending_week),
            weekly_score_output_count)
    if print_min_this_week:
        print_weekly_scores_with_header(
            min_scores_this_week,
            this_week_template.format(main_header="LOWEST SCORES THIS WEEK",
                                      week_num=ending_week),
            weekly_score_output_count)
    if print_max_weekly:
        print_weekly_scores_with_header(max_weekly_scores,
                                        "HIGHEST WEEKLY SCORES THIS SEASON",
                                        weekly_score_output_count)
    if print_min_weekly:
        print_weekly_scores_with_header(min_weekly_scores,
                                        "LOWEST WEEKLY SCORES THIS SEASON",
                                        weekly_score_output_count)
    if print_max_seasonal:
        print_season_scores_with_header(max_seasonal_points_for,
                                        "HIGHEST POINTS-FOR THIS SEASON",
                                        seasonal_score_output_count)
    if print_min_seasonal:
        print_season_scores_with_header(min_seasonal_points_for,
                                        "LOWEST POINTS-FOR THIS SEASON",
                                        seasonal_score_output_count)


if __name__ == "__main__":
    main(sys.argv[1:])