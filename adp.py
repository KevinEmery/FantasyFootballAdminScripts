"""
   Copyright 2021 Kevin Emery

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
"""Script used to find the ADP of players across any  number of leagues

This script will iterate over all of the leagues that the provided user is in, 
looking at the draft for each league to find the ADP for every player that
was drafted in at least one of the drafts.
"""
import argparse
import typing
import re
import sys

from enum import Enum
from sleeper_wrapper import Drafts, League, User

INCLUDE_ALL = "all"


class OutputFormat(Enum):
    HUMAN_READABLE = 1
    CSV = 2


class DraftedPlayer:
    def __init__(self, player_id: str, first_name: str, last_name: str,
                 position: str, team: str):
        # Set these based on constructor data
        self.player_id = player_id
        self.first_name = first_name
        self.last_name = last_name
        self.position = position
        self.team = team

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


def create_output_for_player(player: DraftedPlayer, format: OutputFormat,
                             league_size: int) -> str:
    if format == OutputFormat.HUMAN_READABLE:
        return create_human_readable_output_for_player(player, league_size)
    elif format == OutputFormat.CSV:
        return create_csv_output_for_player(player)
    else:
        return "UNSUPPORTED FORMAT"


def create_human_readable_output_for_player(player: DraftedPlayer,
                                            league_size: int) -> str:
    player_name = player.first_name + " " + player.last_name
    if player.times_drafted == 0:
        template = "{player_name} went undrafted"
        return template.format(player_name=player_name)

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

    return template.format(player_name=player_name,
                           adp=adp,
                           min=minimum,
                           max=maximum,
                           n=player.times_drafted)


def convert_raw_adp_to_round_and_pick(raw_adp: float, league_size: int) -> str:
    adp = int(round(raw_adp))

    draft_round = adp // league_size + 1
    draft_pick = adp % league_size

    return str(draft_round) + "." + str(draft_pick)


def create_csv_output_for_player(player: DraftedPlayer) -> str:
    player_name = player.first_name + " " + player.last_name
    template = "{player_name},{n},{adp},{min},{max}"
    return template.format(player_name=player_name,
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
    parser.add_argument("username",
                        help="User account used to pull all of the leagues",
                        type=str)

    parser.set_defaults(output_format=OutputFormat.HUMAN_READABLE)
    return parser.parse_args()


def main(argv):
    # Parse all of the user-provided flags
    args = parse_user_provided_flags()

    # Convert the computed args into our more-verbose local fields
    account_username = args.username
    league_year = args.year
    position = args.position
    team = args.team
    max_results_to_print = args.max_results
    minimum_times_drafted = args.minimum_times_drafted
    league_size = args.league_size
    output_format = args.output_format
    league_regex = re.compile(args.league_regex)

    # Retrieve the user and all of their leagues
    admin_user = User(account_username)
    all_leagues = admin_user.get_all_leagues("nfl", league_year)

    # Map to store the drafted player results
    player_id_to_drafted_player = {}

    for league_object in all_leagues:
        league = League(league_object.get("league_id"))
        league_name = league.get_league().get("name")

        # Only look at leagues that match the provided regex
        if league_regex.match(league_name):

            draft_id = league.get_league().get("draft_id")
            draft = Drafts(draft_id)

            for pick in draft.get_all_picks():
                player_id = pick["player_id"]

                if player_id in player_id_to_drafted_player.keys():
                    drafted_player = player_id_to_drafted_player.get(player_id)
                else:
                    drafted_player = DraftedPlayer(
                        pick["player_id"], pick["metadata"]["first_name"],
                        pick["metadata"]["last_name"],
                        pick["metadata"]["position"], pick["metadata"]["team"])
                    player_id_to_drafted_player[player_id] = drafted_player

                drafted_player.add_draft_position(pick["pick_no"])

    # Print the results of all the parsing
    results_printed = 0
    for player_id in sorted(player_id_to_drafted_player,
                            key=player_id_to_drafted_player.get):

        # Short circuit if we've printed enough
        if max_results_to_print != -1 and results_printed >= max_results_to_print:
            break

        # Pull up the player
        drafted_player = player_id_to_drafted_player[player_id]

        # Filter on position
        if position != INCLUDE_ALL and drafted_player.position != position:
            continue

        # Filter on team
        if team != INCLUDE_ALL and drafted_player.team != team:
            continue

        # Filter out players who have been drafted fewer times than the specified minimum count
        if drafted_player.times_drafted < minimum_times_drafted:
            continue

        results_printed += 1
        print(
            create_output_for_player(drafted_player, output_format,
                                     league_size))


if __name__ == "__main__":
    main(sys.argv[1:])