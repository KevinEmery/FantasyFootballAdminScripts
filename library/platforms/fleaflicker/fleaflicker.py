from datetime import datetime
from typing import Dict, List

from . import api

from ..platform import Platform

from ... import defaults
from ...model.draftedplayer import DraftedPlayer
from ...model.league import League
from ...model.player import Player
from ...model.team import Team
from ...model.trade import Trade
from ...model.tradedetail import TradeDetail
from ...model.user import User


class Fleaflicker(Platform):
    def __init__(self):
        self._league_id_to_team_id_to_user: Dict[str, Dict[int, User]] = {}

    def get_admin_user_by_identifier(self, identifier: str) -> User:
        # Fleaflicker doesn't require you to query by Admin User Id, instead
        # making it available via email. Construct a dummy user object here solely
        # comprised of their email
        return User("", "Admin User", identifier)

    def get_all_leagues_for_user(self,
                                 user: User,
                                 sport: str = defaults.SPORT,
                                 year: str = defaults.YEAR) -> List[League]:
        leagues = []

        raw_league_list = api.fetch_user_leagues(user, sport, year)

        for raw_league in raw_league_list:
            # Expensive up front but gives us user data for all operations
            self._store_team_and_user_data_for_league(str(raw_league["id"]))

            leagues.append(League(raw_league["name"], str(raw_league["id"])))

        return leagues

    def get_drafted_players_for_league(
            self,
            league: League,
            sport: str = defaults.SPORT,
            year: str = defaults.YEAR) -> List[DraftedPlayer]:
        drafted_players = []

        raw_draft_board = api.fetch_league_draft_board(league.league_id, sport,
                                                       year)
        raw_rosters = raw_draft_board["rosters"]
        for roster in raw_rosters:
            for lineup_entry in roster["lineup"]:
                if "player" in lineup_entry:
                    player_data = lineup_entry["player"]["proPlayer"]

                    player = self._build_player_from_pro_player(player_data)

                    draft_position = lineup_entry["draftedAt"]["overall"]

                    drafted_players.append(
                        DraftedPlayer(player, draft_position))

        return drafted_players

    def get_all_trades_for_league(self, league: League) -> List[Trade]:
        all_trades = []

        team_id_to_user = self._league_id_to_team_id_to_user[league.league_id]
        raw_trades = api.fetch_trades(league.league_id, defaults.SPORT)

        for trade_data in raw_trades:
            trade_time = datetime.fromtimestamp(
                int(trade_data["approvedOn"]) / 1000)

            # Ignore trades not made this year, Fleaflicker's API returns all trades throughout time
            if str(trade_time.year) != defaults.YEAR:
                continue

            trade_details = []

            for team_data in trade_data["teams"]:
                team_id = str(team_data["team"]["id"])
                user = team_id_to_user[team_id]

                team = Team(team_id, user,
                            self._build_roster_link(league.league_id, team_id))

                trade_detail = TradeDetail(team)

                # Fleaflicker's API doesn't return who you gave up in the
                # trade, just who you added or released to waivers. So we're
                # only going to track additions here
                if "playersObtained" in team_data:
                    for player_data in team_data["playersObtained"]:
                        pro_player = player_data["proPlayer"]

                        player = self._build_player_from_pro_player(pro_player)

                        trade_detail.add_player(player)

                if "picksObtained" in team_data:
                    for draft_pick in team_data["picksObtained"]:
                        trade_detail.add_draft_pick_with_slot(
                            str(draft_pick["season"]),
                            draft_pick["slot"]["round"],
                            draft_pick["slot"]["slot"])

                trade_details.append(trade_detail)

            all_trades.append(Trade(trade_time, trade_details))

        return all_trades

    def _build_player_from_pro_player(self, player_data: Dict[str,
                                                              str]) -> Player:
        player_id = player_data["id"]
        name = player_data["nameFull"]
        position = player_data["position"]
        team = player_data["proTeamAbbreviation"]

        if "injury" in player_data:
            status = player_data["injury"]["severity"]
        else:
            status = "HEALTHY"

        return Player(player_id, name, team, position, status)

    def _build_roster_link(self, league_id: str, team_id: str) -> str:
        template = "https://www.fleaflicker.com/nfl/leagues/{league_id}/teams/{team_id}"
        return template.format(league_id=league_id, team_id=team_id)

    def _store_team_and_user_data_for_league(self, league_id: str):

        raw_league_data = api.fetch_league_standings(league_id, defaults.SPORT)

        team_id_to_user = {}

        for division in raw_league_data["divisions"]:
            for team in division["teams"]:
                user = User(str(team["owners"][0]["id"]),
                            team["owners"][0]["displayName"])
                team_id_to_user[str(team["id"])] = user

        self._league_id_to_team_id_to_user[league_id] = team_id_to_user
