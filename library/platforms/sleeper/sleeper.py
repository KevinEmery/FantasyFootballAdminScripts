import re

from datetime import datetime
from typing import Dict, List

from . import api

from ..platform import Platform

from ... import defaults
from ...model.draftedplayer import DraftedPlayer
from ...model.league import League
from ...model.player import Player
from ...model.seasonscore import SeasonScore
from ...model.team import Team
from ...model.trade import Trade
from ...model.tradedetail import TradeDetail
from ...model.user import User
from ...model.weeklyscore import WeeklyScore


class Sleeper(Platform):
    def __init__(self):
        # Rather than do this lookup the first time we need it, just
        # proactively retrieve all player data up front
        self._player_id_to_player: Dict[
            str, Player] = self._initialize_player_data()
        self._owner_id_to_user: Dict[str, User] = {}
        self._league_id_to_roster_num_to_user: Dict[str, Dict[int, User]] = {}

    def get_admin_user_by_identifier(self, identifier: str) -> User:
        return api.get_user_from_identifier(identifier)

    def get_all_leagues_for_user(
        self,
        user: User,
        year: str = defaults.YEAR,
        name_regex: re.Pattern = re.compile(".*")
    ) -> List[League]:
        leagues = []

        raw_response_json = api.get_all_leagues_for_user(user, year)

        for raw_league in raw_response_json:
            league = League(raw_league["name"], raw_league["league_id"],
                            raw_league["draft_id"])

            if raw_league["status"] != "pre_draft" and name_regex.match(
                    league.name):
                self._store_roster_and_user_data_for_league(league)
                leagues.append(league)

        return leagues

    def get_drafted_players_for_league(
            self,
            league: League,
            year: str = defaults.YEAR) -> List[DraftedPlayer]:
        drafted_players = []

        raw_draft_data = api.get_all_picks_for_draft(league.draft_id)

        for raw_draft_pick in raw_draft_data:
            drafted_players.append(
                DraftedPlayer(
                    self._player_id_to_player[raw_draft_pick["player_id"]],
                    raw_draft_pick["pick_no"]))

        return drafted_players

    def get_all_trades_for_league(self, league: League) -> List[Trade]:
        all_trades = []
        roster_num_to_user = self._league_id_to_roster_num_to_user[
            league.league_id]

        # Iterate through every week of the season (and then a couple more just to be sure)
        for i in range(1, 20):
            raw_transaction_data = api.get_league_transactions_for_week(
                league.league_id, i)

            for transaction in raw_transaction_data:
                if transaction["type"] != "trade":
                    continue
                roster_id_to_trade_detail = {}

                # Initialize the list of trade details
                for roster_id in transaction["roster_ids"]:
                    team = Team(
                        roster_id, roster_num_to_user[roster_id],
                        self._create_roster_link(league.league_id, roster_id))
                    roster_id_to_trade_detail[roster_id] = TradeDetail(team)

                # Process adds
                adds = transaction["adds"]
                if adds is not None:
                    for player_id, roster_id in adds.items():
                        roster_id_to_trade_detail[roster_id].add_player(
                            self._player_id_to_player[player_id])

                # Process drops
                drops = transaction["drops"]
                if drops is not None:
                    for player_id, roster_id in drops.items():
                        roster_id_to_trade_detail[roster_id].lose_player(
                            self._player_id_to_player[player_id])

                # Process faab
                faab_changes = transaction["waiver_budget"]
                for line_item in faab_changes:
                    roster_id_to_trade_detail[line_item["sender"]].lose_faab(
                        line_item["amount"])
                    roster_id_to_trade_detail[line_item["receiver"]].add_faab(
                        line_item["amount"])

                # Process draft picks
                draft_picks = transaction["draft_picks"]
                for pick in draft_picks:
                    # Owner id is the person who received the draft pick
                    roster_id_to_trade_detail[pick["owner_id"]].add_draft_pick(
                        pick["season"], pick["round"])

                    # Previous owner is who is trading it away
                    roster_id_to_trade_detail[
                        pick["previous_owner_id"]].lose_draft_pick(
                            pick["season"], pick["round"])

                all_details = []
                for roster_id in roster_id_to_trade_detail:
                    all_details.append(roster_id_to_trade_detail[roster_id])

                transaction_time = datetime.fromtimestamp(
                    transaction["status_updated"] / 1000)
                all_trades.append(Trade(transaction_time, all_details))

        return all_trades

    def get_weekly_scores_for_league_and_week(self, league: League, week: int,
                                              year: str) -> List[WeeklyScore]:
        weekly_scores = []    

        weekly_matchups = api.get_matchups_for_league_and_week(league.league_id, week)
        roster_num_to_user = self._league_id_to_roster_num_to_user[
            league.league_id]

        # Each "matchup" represents a single teams performance
        for matchup in weekly_matchups:
            roster_id = matchup["roster_id"]
            team = Team(roster_id, roster_num_to_user[roster_id],
                        self._create_roster_link(league.league_id, roster_id))
            weekly_scores.append(WeeklyScore(league, team, week, matchup.get("points")))

        return weekly_scores

    def get_season_scores_for_league(self, league: League,
                                     year: str) -> List[SeasonScore]:
        season_scores = []
        raw_league_rosters = api.get_rosters_for_league(league.league_id)
        roster_num_to_user = self._league_id_to_roster_num_to_user[
            league.league_id]

        for roster in raw_league_rosters:
            roster_id = roster["roster_id"]
            team = Team(roster_id, roster_num_to_user[roster_id],
                        self._create_roster_link(league.league_id, roster_id))

            total_points_for = float(roster["settings"]["fpts"])
            try:
                total_points_for += float(
                    roster["settings"]["fpts_decimal"]) / 100
            except Exception:
                # Decimal field may not be pressent, skip
                total_points_for += 0.00

            season_scores.append(
                SeasonScore(league, team, total_points_for))

        return season_scores

    def _create_roster_link(self, league_id: str, roster_id: int) -> str:
        template = "https://sleeper.app/roster/{league_id}/{roster_id}"
        return template.format(league_id=league_id, roster_id=str(roster_id))

    def _store_roster_and_user_data_for_league(self, league: League):
        raw_league_rosters = api.get_rosters_for_league(league.league_id)

        roster_num_to_user = {}

        for roster in raw_league_rosters:
            owner_id = roster["owner_id"]

            if owner_id not in self._owner_id_to_user:
                user = api.get_user_from_identifier(owner_id)
                self._owner_id_to_user[owner_id] = user

            user = self._owner_id_to_user[owner_id]
            roster_num_to_user[roster["roster_id"]] = user

        self._league_id_to_roster_num_to_user[
            league.league_id] = roster_num_to_user

    def _initialize_player_data(self) -> Dict[str, Player]:
        player_id_to_player = {}

        raw_player_map = api.get_all_players()

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
