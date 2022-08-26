from typing import Dict, List

from .api import *

from ..platform import Platform

from ...defaults import *
from ...model.draftedplayer import DraftedPlayer
from ...model.league import League
from ...model.player import Player
from ...model.trade import Trade
from ...model.user import User


class Sleeper(Platform):
    def __init__(self):
        # Rather than do this lookup the first time we need it, just
        # proactively retrieve all player data up front
        self._player_id_to_player: Dict[
            str, Player] = self._initialize_player_data()

    def get_user_by_identifier(self, username: str) -> User:
        return get_user_from_username(username)

    def get_all_leagues_for_user(self,
                                 user: User,
                                 sport: str = SPORT,
                                 year: str = YEAR) -> List[League]:
        leagues = []

        raw_response_json = get_all_leagues_for_user(user, sport, year)

        for raw_league in raw_response_json:
            league = League(raw_league["name"], raw_league["league_id"],
                            raw_league["draft_id"])

            if raw_league["status"] != "pre_draft":
                leagues.append(league)

        return leagues

    def get_drafted_players_for_league(self,
                                       league: League) -> List[DraftedPlayer]:
        drafted_players = []

        raw_draft_data = get_all_picks_for_draft(league.draft_id)

        for raw_draft_pick in raw_draft_data:
            drafted_players.append(
                DraftedPlayer(
                    self._player_id_to_player[raw_draft_pick["player_id"]],
                    raw_draft_pick["pick_no"]))

        return drafted_players

    def _initialize_player_data(self, sport: str = SPORT) -> Dict[str, Player]:
        player_id_to_player = {}

        raw_player_map = get_all_players(sport)

        for player_id in raw_player_map:
            raw_player = raw_player_map[player_id]
            player_name = "{first} {last}".format(
                first=raw_player["first_name"], last=raw_player["last_name"])

            player_id_to_player[player_id] = Player(
                player_id, player_name, raw_player["team"],
                raw_player["position"], raw_player["injury_status"])

        # Insert a dummy missing player at ID 0
        player_id_to_player["0"] = Player("0", "Missing Player", "None",
                                          "MISSING", "NONE")

        return player_id_to_player
