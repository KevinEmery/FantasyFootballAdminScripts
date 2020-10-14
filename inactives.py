from sleeper_wrapper import League, User, Players
from typing import Callable, Dict, List

import argparse
import sys

BYE_WEEKS_2020 = {
    4: ["PIT", "TEN"],
    5: ["DET", "GB"],
    6: ["LV", "NE", "NO", "SEA"],
    7: ["BAL", "IND", "JAX", "MIN"],
    8: ["ARI", "DEN", "HOU", "WAS"],
    9: ["CIN", "CLE", "LAR", "PHI"],
    10: ["ATL", "DAL", "KC", "LAC"],
    11: ["BUF", "CHI", "MIA", "NYG", "NYJ", "SF"],
    13: ["CAR", "TB"]
}

# This should be used on a week-to-week basis to exclude players from the
# report. Intent here is to clean up cases where a player was given a status
# just before or during the game, as this doesn't represent an inactive owner.
# NOTE: Player ids must be passed as strings
PLAYER_IDS_TO_IGNORE = []

# Map storing the user id and username, to avoid multiple server calls for
# the same information
user_id_to_username = {}


# Container class to hold the status
class Player:
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
    def __init__(self, user_name: str, league_name: str,
                 inactives: List[Player]):
        self.user_name = user_name
        self.league_name = league_name
        self.inactives = inactives

    def __str__(self):
        return_string = ""
        first_line_template = "{user_name}, {league_name}\n"
        return_string += first_line_template.format(
            user_name=self.user_name, league_name=self.league_name)
        for player in self.inactives:
            return_string += str(player) + "\n"

        return return_string


def add_users_to_user_map(users: List[User]):
    for user in users:
        user_id_to_username[user.get("user_id")] = user.get("display_name")


def get_username_from_user_id(user_id: str) -> str:
    try:
        return user_id_to_username[user_id]
    except KeyError:
        print("Error retrieving user: " + str(user_id))
        return "No User"


def is_league_inactive(rosters) -> bool:
    """Determines if a league is inactive based on the rosters

    This is used as a mildly hacky helper method. It looks through the
    rosters of every time, and if there are any players on any of them
    it classifies the league as active. However if all the player
    lists are empty, it says the league is inactive and returns True

    """
    for roster in rosters:
        if roster.get("players"):
            return False

    return True


def find_all_inactive_players_for_week(all_players: Dict[int,
                                                         Players], week: int,
                                       include_covid: bool) -> List[Player]:
    # Iterate over the set of players, and pick out the subset that are inactive for any reason

    inactive_players = []
    teams_on_bye = []
    status_to_ignore = ["Questionable"]

    if week in BYE_WEEKS_2020.keys():
        teams_on_bye = BYE_WEEKS_2020.get(week)

    if not include_covid:
        status_to_ignore.append("COV")

    for player_id, player_data in all_players.items():
        if player_id in PLAYER_IDS_TO_IGNORE:
            continue
        status = player_data.get("injury_status")
        team = player_data.get("team")
        player_inactive = False

        if team in teams_on_bye:
            player_inactive = True
            status = "BYE"
        elif status is not None and status != "" and status not in status_to_ignore:
            player_inactive = True

        if player_inactive:
            inactive_players.append(
                Player(player_data.get("full_name"), player_id,
                       player_data.get("position"), status,
                       player_data.get("team")))

    return inactive_players


def find_inactive_starters_for_league_and_week(league: League, week: int,
                                               inactives: List[Player]):
    rosters = league.get_rosters()

    # Short circuit to avoid problems if the league is empty
    if is_league_inactive(rosters):
        return []

    roster_id_to_username = {}
    inactive_rosters = []

    # Create a mapping of the roster id to the username
    for roster in rosters:
        roster_id_to_username[roster.get(
            "roster_id")] = get_username_from_user_id(roster.get("owner_id"))

    # Each "matchup" represents a single teams performance
    weekly_matchups = league.get_matchups(week)
    for matchup in weekly_matchups:
        starters = matchup.get("starters")
        tmp_inactives = []
        # I don't like this, we should iterate over the starters and find them in the inactive list instead
        for player in inactives:
            if player.player_id in starters:
                tmp_inactives.append(player)
        if tmp_inactives:
            inactive_rosters.append(
                InactiveRoster(roster_id_to_username[matchup.get("roster_id")],
                               league.get_league().get("name"), tmp_inactives))

    return inactive_rosters


def parse_user_provided_flags() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-y",
                        "--year",
                        help="The year to run the analysis on",
                        type=int,
                        default=2020)
    parser.add_argument("username",
                        help="User account used to pull all of the leagues",
                        type=str)
    parser.add_argument("week", help="The week to run analysis on", type=int)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--include-covid",
                       dest="include_covid",
                       action="store_true",
                       help="Include COVID players in inactives")
    group.add_argument("--exclude-covid",
                       dest="include_covid",
                       action="store_false")
    parser.set_defaults(include_covid=False)

    return parser.parse_args()


def main(argv):
    args = parse_user_provided_flags()
    user = args.username
    year = args.year
    week = args.week
    include_covid = args.include_covid

    # Iterate through each league, printing the report
    nfl_players = Players()
    inactive_players = find_all_inactive_players_for_week(
        nfl_players.get_all_players(), week, include_covid)
    inactive_offensive_players = list(
        filter(lambda player: player.position in ["QB", "WR", "RB", "TE"],
               inactive_players))

    # Empty starting slots fill in as id 0, so add an entry for that
    # 0th player in order to report the empty spot
    inactive_offensive_players.append(
        Player("Missing Player", "0", "None", "MISSING", "NONE"))

    # Retrieve all of the leagues
    admin_user = User(user)
    all_leagues = admin_user.get_all_leagues("nfl", year)

    inactive_rosters = []

    for league_object in all_leagues:
        league = League(league_object.get("league_id"))
        add_users_to_user_map(league.get_users())

        inactive_rosters.extend(
            find_inactive_starters_for_league_and_week(
                league, week, inactive_offensive_players))

    for roster in inactive_rosters:
        print(roster)


if __name__ == "__main__":
    main(sys.argv[1:])
