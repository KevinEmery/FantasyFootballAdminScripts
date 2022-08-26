from typing import List

from .api import *

from ..platform import Platform

from ...defaults import *
from ...model.draftedplayer import DraftedPlayer
from ...model.player import Player
from ...model.league import League
from ...model.user import User


class Fleaflicker(Platform):
    def get_admin_user_by_identifier(self, identifier: str) -> User:
        # Fleaflicker doesn't require you to query by Admin User Id, instead
        # making it available via email. Construct a dummy user object here solely
        # comprised of their email
        return User("", "Admin User", identifier)

    def get_all_leagues_for_user(self,
                                 user: User,
                                 sport: str = SPORT,
                                 year: str = YEAR) -> List[League]:
        leagues = []

        raw_league_list = fetch_user_leagues(user, sport, year)

        for raw_league in raw_league_list:
            leagues.append(League(raw_league["name"], str(raw_league["id"])))

        return leagues

    def get_drafted_players_for_league(
            self,
            league: League,
            sport: str = SPORT,
            year: str = YEAR) -> List[DraftedPlayer]:
        drafted_players = []

        raw_draft_board = fetch_league_draft_board(league.league_id, sport,
                                                   year)
        raw_rosters = raw_draft_board["rosters"]
        for roster in raw_rosters:
            for lineup_entry in roster["lineup"]:
                if "player" in lineup_entry:
                    player_data = lineup_entry["player"]["proPlayer"]

                    player_id = player_data["id"]
                    name = player_data["nameFull"]
                    position = player_data["position"]
                    team = player_data["proTeamAbbreviation"]

                    if "injury" in player_data:
                        status = player_data["injury"]["severity"]
                    else:
                        status = "HEALTHY"

                    draft_position = lineup_entry["draftedAt"]["overall"]

                    drafted_players.append(
                        DraftedPlayer(
                            Player(player_id, name, team, position, status),
                            draft_position))

        return drafted_players
