import argparse
import re
import sys

import common
import library.common as libCommon

from library.platforms.fleaflicker.fleaflicker import Fleaflicker
from library.platforms.sleeper.sleeper import Sleeper

def create_sleeper_draft_url_from_id(id: int) -> str:
    template = "https://sleeper.com/draft/nfl/{id}"
    return template.format(id=id)

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
    # Parse all of the user-provided flags
    args = parse_user_provided_flags()


    # Convert the computed args into our more-verbose local fields
    identifier = args.identifier
    year = args.year
    league_regex_string = args.league_regex
    platform_selection = args.platform_selection

    if platform_selection == common.PlatformSelection.SLEEPER:
        platform = Sleeper()
    elif platform_selection == common.PlatformSelection.FLEAFLICKER:
        platform = Fleaflicker()

    league_regex = re.compile(league_regex_string)

    user = platform.get_admin_user_by_identifier(identifier)
    leagues = platform.get_all_leagues_for_user(user, year, league_regex)

    league_format = "{league_name}\n{draft_link}"
    for league in leagues:
        print(league_format.format(league_name=league.name, draft_link=create_sleeper_draft_url_from_id(league.draft_id)))


if __name__ == "__main__":
    main(sys.argv[1:])
