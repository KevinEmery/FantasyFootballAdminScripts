"""
   Copyright 2022 Kevin Emery

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
"""Script used to determine what owners started inactive players

This script will iterate over all of the leagues that the provided user is in,
fetching the starting rosters and comparing the players who started for each 
team against the list of players who were not active based on the currently 
available data. That data is then collated and output as list of teams who
started potentially inactive players.
"""

import argparse
import re
import sys
from datetime import datetime
from typing import Callable, Dict, List

from sleeper_wrapper import League, User, Players

from sleeper_utils import is_league_inactive, create_roster_id_to_username_dict
from transactions import LeagueTransaction, get_most_recent_transaction_per_roster
from user_store import UserStore

BYE_WEEKS_2022 = {
    6: ["DET", "LV", "TEN", "HOU"],
    7: ["BUF", "LAR", "MIN", "PHI"],
    8: ["KC", "LAC"],
    9: ["CLE", "DAL", "DEN", "NYG", "PIT", "SF"],
    10: ["BAL", "CIN", "NE", "NYJ"],
    11: ["JAX", "MIA", "SEA", "TB"],
    13: ["ARI", "CAR"],
    14: ["ATL", "CHI", "GB", "IND", "NO", "WAS"]
}

# This should be used on a week-to-week basis to exclude players from the
# report. Intent here is to clean up cases where a player was given a status
# just before or during the game, as this doesn't represent an inactive owner.
# NOTE: Player ids must be passed as strings
PLAYER_IDS_TO_IGNORE = []


class Player:
    """Basic information about a player and their health/playing status

    Attributes
    ----------
    name : str
        Full name of the player
    player_id : str
        ID of the player in Sleeper's dataset
    position : str
        Primary position for the player
    injury_status : str
        The injury status of the player (if any)
    team : str
        The 2-3 letter abbreviation for the player's current team
    """
    def __init__(self, name: str, player_id: str, position: str,
                 injury_status: str, team: str):
        self.name = name
        self.player_id = player_id
        self.position = position
        self.injury_status = injury_status
        self.team = team

    def __str__(self):
        template = "{name}, {position} - {injury_status} ({id})"
        return template.format(name=self.name,
                               position=self.position,
                               injury_status=self.injury_status,
                               id=self.player_id)


class InactiveRoster:
    """Object representing an inactive roster to be reported

    Attributes
    ----------
    user_name : str
        Username of the owner of the team
    league_name : str
        Name of the league for this team, making it easier to identify
        the source of information
    inactives : List[Player]
        The list of inactive players this team has currently starting
    last_transaction: LeagueTransaction
        (Optional) Last transaction the user performed
    """
    def __init__(self,
                 user_name: str,
                 league_name: str,
                 inactives: List[Player],
                 last_transaction: LeagueTransaction = None):
        self.user_name = user_name
        self.league_name = league_name
        self.inactives = inactives
        self.last_transaction = last_transaction

    def __str__(self):
        return_string = ""
        first_line_template = "{user_name}, {league_name}\n"
        last_transaction_template = "Last transaction: {date}\n"
        date_format = "%m-%d-%Y"

        return_string += first_line_template.format(
            user_name=self.user_name, league_name=self.league_name)
        if self.last_transaction is not None:
            date = datetime.fromtimestamp(self.last_transaction.timestamp).strftime(date_format)
            return_string += last_transaction_template.format(
                date=date)

        for player in self.inactives:
            return_string += str(player) + "\n"

        return return_string


def find_all_inactive_players_for_week(all_players: Dict[int,
                                                         Players], week: int,
                                       include_covid: bool) -> List[Player]:
    """Finds a list of all inactive NFL players in a given week

    This pares down the list of all NFL players into a smaller list containing
    only the players with a non-healthy player status. Because the goal of the
    script is to find inactive owners, Questionable is always ignored and COVID
    statuses can be selectively ignored or included.

    Parameters
    ----------
    all_players : Dict[int, Players]
        Dictionary containing every player in the NFL
    week : int
        The week we're looking up, used to pull the teams on bye
    include_covid : bool
        Whether or not we should include players with the COVID status in the
        list of inactive players

    Returns
    -------
    List[Player]
        A list of the all players that were deemed inactive
    """

    # Initialize the fields used for output or in determining active vs inactive
    inactive_players = []
    teams_on_bye = []
    status_to_ignore = ["Questionable"]

    if week in BYE_WEEKS_2022.keys():
        teams_on_bye = BYE_WEEKS_2022.get(week)

    if not include_covid:
        status_to_ignore.append("COV")

    # Iterate over each player, checking their status
    for player_id, player_data in all_players.items():
        if player_id in PLAYER_IDS_TO_IGNORE:
            continue

        status = player_data.get("injury_status")
        team = player_data.get("team")
        player_inactive = False

        # Special case byes, as the status on the actual player is irrelevant
        if team in teams_on_bye:
            player_inactive = True
            status = "BYE"
        elif status is not None and status != "" and status not in status_to_ignore:
            player_inactive = True

        if player_inactive:
            inactive_players.append(
                Player(player_data.get("full_name"), player_id,
                       player_data.get("position"), status, team))

    return inactive_players


def find_inactive_starters_for_league_and_week(
    league: League, week: int, inactives: List[Player], user_store: UserStore,
    roster_id_to_last_transaction: Dict[int, LeagueTransaction]
) -> List[InactiveRoster]:
    """Finds all of the teams with inactive starters within a league

    This is where the bulk of the business logic lives, iterating over each
    player in the starting lineup to see if their inactive, and if so adding
    that team into the final output of "inactives"

    Parameters
    ----------
    league : League
        League object under analysis, used to pull the starters for each team
    week : int
        The week we're looking at, to ensure we pull the correct starters
    inactives : List[Player]
        List of all inactive Players based on their current status
    roster_id_to_last_transaction : Dict[int, LeagueTransaction]
        Dict of roster id to their last transaction
    user_store : UserStore
        Storage object used to retrieve the username for a specific team

    Returns
    -------
    List[InactiveRoster]
        A list of the all the rosters in the league with >0 inactive players
    """

    # Short circuit to avoid problems if the league is empty
    if is_league_inactive(league):
        return []

    inactive_rosters = []
    roster_id_to_username = create_roster_id_to_username_dict(
        league, user_store)

    # Each "matchup" represents a single teams performance, so look at all of them
    weekly_matchups = league.get_matchups(week)
    for matchup in weekly_matchups:
        starters = matchup.get("starters")
        username = roster_id_to_username[matchup.get("roster_id")]

        # I'm running into a strange issue where someone's starters are coming
        # back as None. Log that to console and move on for now, you'll have
        # to manually check their roster.
        if starters is None:
            msg = "{league} - {username}'s starters list is None"
            print(
                msg.format(league=league.get_league().get("name"),
                           username=username))
            continue

        tmp_inactives = []
        for starter_id in starters:
            # Get the first player in inactives that matches the starter id, or None
            try:
                inactive_player = [
                    p for p in inactives if p.player_id == starter_id
                ][0]
            except IndexError:
                inactive_player = None
            if inactive_player is not None:
                tmp_inactives.append(inactive_player)

        if tmp_inactives:
            last_transaction = None
            if roster_id_to_last_transaction is not None:
                last_transaction = roster_id_to_last_transaction[matchup.get(
                    "roster_id")]

            inactive_rosters.append(
                InactiveRoster(username,
                               league.get_league().get("name"), tmp_inactives, last_transaction))

    return inactive_rosters


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
    parser.add_argument("username",
                        help="User account used to pull all of the leagues",
                        type=str)
    parser.add_argument("week", help="The week to run analysis on", type=int)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--include-covid",
                       dest="include_covid",
                       action="store_true",
                       help="Include COVID players in the report (default)")
    group.add_argument("--exclude-covid",
                       dest="include_covid",
                       action="store_false")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--include-missing",
                       dest="include_missing",
                       action="store_true",
                       help="Include missing players in the report (default)")
    group.add_argument("--exclude-missing",
                       dest="include_missing",
                       action="store_false")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--include-transactions",
        dest="include_transactions",
        action="store_true",
        help="Include last transaction data in the report (default)")
    group.add_argument("--exclude-transactions",
                       dest="include_transactions",
                       action="store_false")
    parser.set_defaults(include_covid=True,
                        include_missing=True,
                        include_transactions=True)

    return parser.parse_args()


def main(argv):
    args = parse_user_provided_flags()
    user = args.username
    year = args.year
    league_regex = re.compile(args.league_regex)
    week = args.week
    include_covid = args.include_covid
    include_missing = args.include_missing
    include_transactions = args.include_transactions

    # Retrieve the list of all inactive players
    nfl_players = Players()
    inactive_players = find_all_inactive_players_for_week(
        nfl_players.get_all_players(), week, include_covid)

    if include_missing:
        # Empty starting slots fill in as id 0, so add an entry for that
        # 0th player in order to report the empty spot
        inactive_players.append(
            Player("Missing Player", "0", "None", "MISSING", "NONE"))

    # Retrieve all of the leagues
    admin_user = User(user)
    all_leagues = admin_user.get_all_leagues("nfl", year)
    user_store = UserStore()

    inactive_rosters = []

    # Iterate through each league to find the inactive owners in each
    for league_object in all_leagues:
        league = League(league_object.get("league_id"))
        league_name = league.get_league().get("name")

        # Only look at leagues that match the provided regex
        if league_regex.match(league_name):
            user_store.store_users_for_league(league)
            most_recent_transaction_per_roster = None

            if include_transactions:
                most_recent_transaction_per_roster = get_most_recent_transaction_per_roster(
                    league, week)

            inactive_rosters.extend(
                find_inactive_starters_for_league_and_week(
                    league, week, inactive_players, user_store,
                    most_recent_transaction_per_roster))

    # Print out the final inactive rosters
    print("")
    for roster in inactive_rosters:
        print(roster)


if __name__ == "__main__":
    main(sys.argv[1:])
