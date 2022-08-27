import argparse
import re
import sys

import common

from enum import Enum

from library.model.draftedplayer import DraftedPlayer
from library.model.player import Player
from library.model.user import User

from library.platforms.platform import Platform
from library.platforms.fleaflicker.fleaflicker import Fleaflicker
from library.platforms.sleeper.sleeper import Sleeper

INCLUDE_ALL = "all"


class OutputFormat(Enum):
    HUMAN_READABLE = 1
    CSV = 2


class AggregatedPlayerData(object):
    def __init__(self, player: Player):
        self.player = player

        # Initialize the data storage fields, designed to be updated as data comes in
        self.draft_positions = []
        self.times_drafted = 0
        self.average_draft_position = 0.0
        self.min_draft_position = 10000
        self.max_draft_position = 0
        self.sum_draft_positions = 0

    def add_draft_position(self, draft_position: int):
        self.draft_positions.append(draft_position)
        self._compute_adp_stats(draft_position)

    def _compute_adp_stats(self, new_draft_position: int):
        self.times_drafted += 1
        self.sum_draft_positions += new_draft_position
        self.average_draft_position = float(
            self.sum_draft_positions) / self.times_drafted

        if new_draft_position < self.min_draft_position:
            self.min_draft_position = new_draft_position
        if new_draft_position > self.max_draft_position:
            self.max_draft_position = new_draft_position

    def __lt__(self, other):
        return self.average_draft_position < other.average_draft_position

    def __str__(self):
        return self.player.name + " " + str(self.average_draft_position)


def create_output_for_player(player: AggregatedPlayerData,
                             format: OutputFormat, league_size: int) -> str:
    if format == OutputFormat.HUMAN_READABLE:
        return create_human_readable_output_for_player(player, league_size)
    elif format == OutputFormat.CSV:
        return create_csv_output_for_player(player)
    else:
        return "UNSUPPORTED FORMAT"


def create_human_readable_output_for_player(player: AggregatedPlayerData,
                                            league_size: int) -> str:
    if player.times_drafted == 0:
        template = "{player_name} went undrafted"
        return template.format(player_name=player.player.name)

    if league_size == 0:
        template = "{player_name:<30}ADP: {adp:5.1f}   Min: {min:<3}   Max: {max:<3}   N= {n}"
        adp = player.average_draft_position
        minimum = player.min_draft_position
        maximum = player.max_draft_position
    else:
        template = "{player_name:<30}ADP: {adp:<5}   Min: {min:<5}   Max: {max:<5}   N= {n}"
        adp = convert_raw_adp_to_round_and_pick(player.average_draft_position,
                                                league_size)
        minimum = convert_raw_adp_to_round_and_pick(player.min_draft_position,
                                                    league_size)
        maximum = convert_raw_adp_to_round_and_pick(player.max_draft_position,
                                                    league_size)

    return template.format(player_name=player.player.name,
                           adp=adp,
                           min=minimum,
                           max=maximum,
                           n=player.times_drafted)


def convert_raw_adp_to_round_and_pick(raw_adp: float, league_size: int) -> str:
    adp = int(round(raw_adp))

    draft_round = adp // league_size + 1
    draft_pick = adp % league_size

    # If a player is picked in the last pick of round x it should be x.<league_size> so we need to tweak
    # the numbers here. In a 14-team league Pick 42 is 3.14, not 4.0
    if draft_pick == 0:
        draft_pick = league_size
        draft_round -= 1

    return str(draft_round) + "." + str(draft_pick)


def create_csv_output_for_player(player: AggregatedPlayerData) -> str:
    template = "{player_name},{n},{adp},{min},{max}"
    return template.format(player_name=player.player.name,
                           adp=player.average_draft_position,
                           min=player.min_draft_position,
                           max=player.max_draft_position,
                           n=player.times_drafted)


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
    parser.add_argument(
        "-p",
        "--position",
        help="Which NFL position to print data about (default: all)",
        type=str,
        default=INCLUDE_ALL)
    parser.add_argument(
        "-t",
        "--team",
        help="Which NFL team to print data about (default: all)",
        type=str,
        default=INCLUDE_ALL)
    parser.add_argument(
        "-n",
        "--max_results",
        help="Maximum number of players to display (default: all)",
        type=int,
        default=-1)
    parser.add_argument(
        "-c",
        "--minimum_times_drafted",
        help=
        "Minimum number of times a player needs to be drafted (default: 1)",
        type=int,
        default=1)
    parser.add_argument("-s",
                        "--league_size",
                        help="Number of teams in the league",
                        type=int,
                        default=0)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--human_readable",
                       dest="output_format",
                       action="store_const",
                       const=OutputFormat.HUMAN_READABLE)
    group.add_argument("--csv",
                       dest="output_format",
                       action="store_const",
                       const=OutputFormat.CSV)

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

    parser.set_defaults(output_format=OutputFormat.HUMAN_READABLE,
                        platform_selection=common.PlatformSelection.SLEEPER)
    return parser.parse_args()


def main(argv):
    # Parse all of the user-provided flags
    args = parse_user_provided_flags()

    # Convert the computed args into our more-verbose local fields
    account_identifier = args.identifier
    year = args.year
    position = args.position
    team = args.team
    max_results_to_print = args.max_results
    minimum_times_drafted = args.minimum_times_drafted
    league_size = args.league_size
    output_format = args.output_format
    league_regex = re.compile(args.league_regex)

    # Set platform based on user choice
    if args.platform_selection == common.PlatformSelection.SLEEPER:
        platform = Sleeper()
    elif args.platform_selection == common.PlatformSelection.FLEAFLICKER:
        platform = Fleaflicker()

    user = platform.get_admin_user_by_identifier(account_identifier)
    leagues = platform.get_all_leagues_for_user(user, year, league_regex)

    player_data = {}

    for league in leagues:
        drafted_players = platform.get_drafted_players_for_league(league)

        for drafted_player in drafted_players:
            player_id = drafted_player.player.player_id

            if player_id not in player_data:
                player_data[player_id] = AggregatedPlayerData(
                    drafted_player.player)

            player_data[player_id].add_draft_position(
                drafted_player.draft_position)

    results_printed = 0
    for player_id in sorted(player_data, key=player_data.get):

        # Short circuit if we've printed enough
        if max_results_to_print != -1 and results_printed >= max_results_to_print:
            break

        # Pull up the player
        individual_player_data = player_data[player_id]

        # Filter on position
        if position != INCLUDE_ALL and individual_player_data.player.position != position:
            continue

        # Filter on team
        if team != INCLUDE_ALL and individual_player_data.player.team != team:
            continue

        # Filter out players who have been drafted fewer times than the specified minimum count
        if individual_player_data.times_drafted < minimum_times_drafted:
            continue

        results_printed += 1
        print(
            create_output_for_player(individual_player_data, output_format,
                                     league_size))


if __name__ == "__main__":
    main(sys.argv[1:])