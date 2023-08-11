"""
   Copyright 2023 Kevin Emery

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

from datetime import datetime
from typing import Dict, List

import re

from . import api

from ..platform import Platform

from ... import common
from ...model.draftedplayer import DraftedPlayer
from ...model.inactiveroster import InactiveRoster
from ...model.league import League
from ...model.player import Player
from ...model.seasonscore import SeasonScore
from ...model.team import Team
from ...model.trade import Trade
from ...model.tradedetail import TradeDetail
from ...model.transaction import Transaction
from ...model.user import User
from ...model.weeklyscore import WeeklyScore


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
                                 year: str = common.DEFAULT_YEAR,
                                 name_regex: re.Pattern = re.compile(".*"),
                                 store_user_info: bool = True) -> List[League]:
        leagues = []

        # Even when pulling past data, we can only check the current year's leagues.
        raw_league_list = api.fetch_user_leagues(user, common.DEFAULT_YEAR)

        for raw_league in raw_league_list:
            league = League(raw_league["name"], raw_league["capacity"],
                            str(raw_league["id"]))

            if name_regex.match(league.name):
                if store_user_info:
                    self._store_team_and_user_data_for_league(
                        league.league_id, year)
                leagues.append(league)

        return leagues

    def get_drafted_players_for_league(
            self,
            league: League,
            year: str = common.DEFAULT_YEAR) -> List[DraftedPlayer]:
        drafted_players = []

        raw_draft_board = api.fetch_league_draft_board(league.league_id, year)
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

    def get_all_trades_for_league(self, league: League, year: str) -> List[Trade]:
        all_trades = []

        team_id_to_user = self._league_id_to_team_id_to_user[league.league_id]
        raw_trades = api.fetch_trades(league.league_id)

        for trade_data in raw_trades:
            trade_time = datetime.fromtimestamp(
                int(trade_data["approvedOn"]) / 1000)

            # Ignore trades not made this year, Fleaflicker's API returns all trades throughout time
            if str(trade_time.year) != year:
                continue

            trade_id = trade_data["id"]

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
                        if "slot" in draft_pick["slot"]:
                            trade_detail.add_draft_pick_with_slot(
                                str(draft_pick["season"]),
                                draft_pick["slot"]["round"],
                                draft_pick["slot"]["slot"])
                        else:
                            trade_detail.add_draft_pick(
                                str(draft_pick["season"]),
                                draft_pick["slot"]["round"])

                trade_details.append(trade_detail)

            all_trades.append(Trade(trade_id, league, trade_time, trade_details))

        return all_trades

    def get_weekly_scores_for_league_and_week(self, league: League, week: int,
                                              year: str) -> List[WeeklyScore]:
        weekly_scores = []
        team_id_to_user = self._league_id_to_team_id_to_user[league.league_id]

        raw_league_scoreboard = api.fetch_league_scoreboard(
            league.league_id, week, year)

        for game in raw_league_scoreboard["games"]:
            raw_home = game["home"]
            raw_away = game["away"]
            home_id = str(raw_home["id"])
            away_id = str(raw_away["id"])

            home_team = Team(
                home_id, team_id_to_user[home_id],
                self._build_roster_link(league.league_id, home_id))
            away_team = Team(
                away_id, team_id_to_user[away_id],
                self._build_roster_link(league.league_id, away_id))

            weekly_scores.append(
                WeeklyScore(league, home_team, week,
                            float(game["homeScore"]["score"]["formatted"])))
            weekly_scores.append(
                WeeklyScore(league, away_team, week,
                            float(game["awayScore"]["score"]["formatted"])))

        return weekly_scores

    def get_season_scores_for_league(self, league: League,
                                     year: str) -> List[SeasonScore]:
        season_scores = []
        team_id_to_user = self._league_id_to_team_id_to_user[league.league_id]

        # The scoreboard returns season-long information regardless of the week
        raw_league_scoreboard = api.fetch_league_scoreboard(
            league.league_id, 1, year)

        for game in raw_league_scoreboard["games"]:
            raw_home = game["home"]
            raw_away = game["away"]
            home_id = str(raw_home["id"])
            away_id = str(raw_away["id"])

            home_team = Team(
                home_id, team_id_to_user[home_id],
                self._build_roster_link(league.league_id, home_id))
            away_team = Team(
                away_id, team_id_to_user[away_id],
                self._build_roster_link(league.league_id, away_id))

            season_scores.append(
                SeasonScore(
                    league, home_team,
                    float(raw_home["pointsFor"]["formatted"].replace(",",
                                                                     ""))))
            season_scores.append(
                SeasonScore(
                    league, away_team,
                    float(raw_away["pointsFor"]["formatted"].replace(",",
                                                                     ""))))

        return season_scores

    def get_last_transaction_for_teams_in_league(
            self, league: League, year: int) -> Dict[Team, Transaction]:
        transactions = {}
        team_id_to_user = self._league_id_to_team_id_to_user[league.league_id]

        for team_id in team_id_to_user:
            raw_transactions = api.fetch_league_transactions_for_team(
                league.league_id, team_id)
            most_recent_raw_transaction = raw_transactions["items"][0]
            transaction_object = most_recent_raw_transaction["transaction"]

            transaction_time = datetime.fromtimestamp(
                int(most_recent_raw_transaction["timeEpochMilli"]) / 1000)

            team = Team(team_id, team_id_to_user[team_id],
                        self._build_roster_link(league.league_id, team_id))

            # If the year isn't the current year then just return a default transaction,
            # the team doesn't have one this year
            if transaction_time.year != year:
                transaction = Transaction(
                    datetime.fromtimestamp(common.DEC_31_1999_SECONDS), "NONE",
                    team)
            else:
                # This is the default, and if it's not set in the response then we assume
                # that the transaction is an add
                transaction_type = "TRANSACTION_ADD"
                if "type" in transaction_object:
                    transaction_type = transaction_object["type"]

                if transaction_type.startswith("TRANSACTION_"):
                    transaction_type = transaction_type[12:]

                transaction = Transaction(transaction_time, transaction_type,
                                          team)

            transactions[team] = transaction

        return transactions

    def get_inactive_rosters_for_league_and_week(
            self,
            league: League,
            week: int,
            year: int,
            teams_to_ignore: List[str] = [],
            only_teams: List[str] = [],
            player_names_to_ignore: List[str] = []) -> List[InactiveRoster]:

        inactive_rosters = []
        team_id_to_user = self._league_id_to_team_id_to_user[league.league_id]
        teams_on_bye = common.TEAMS_ON_BYE[week]

        # In order to pull lineups, we have to pull game ids from the scoreboard
        raw_league_scoreboard = api.fetch_league_scoreboard(
            league.league_id, week, year)

        game_ids = []
        for game in raw_league_scoreboard["games"]:
            game_ids.append(game["id"])

        # Each game is a matchup home/away.
        for game_id in game_ids:
            raw_box_score = api.fetch_league_box_score(league.league_id, week, game_id)

            game = raw_box_score["game"]

            home_id = str(game["home"]["id"])
            home_inactives = []
            home_team = Team(home_id, team_id_to_user[home_id], self._build_roster_link(league.league_id, home_id))

            away_id = str(game["away"]["id"])
            away_inactives = []
            away_team = Team(away_id, team_id_to_user[away_id], self._build_roster_link(league.league_id, away_id))

            for grouping in raw_box_score["lineups"]:
                # Starters has a definite group, assume all else is just... not starters.
                try:
                    group = grouping["group"]
                except Exception as e:
                    group = "NOT_START"

                # Within the list of starters, it's split into a "slot" and each team has a player under that slot
                for slot in grouping["slots"]:
                    if group == "START":
                        # If there isn't a starter in the spot, then "home"/"away" just aren't there
                        if "home" in slot:
                            home_player = self._build_player_from_pro_player(slot["home"]["proPlayer"])
                        else:
                            home_player = Player("0", "Missing", "None", slot["position"]["label"], "Missing")
                            
                        if "away" in slot:
                            away_player = self._build_player_from_pro_player(slot["away"]["proPlayer"])
                        else:
                            away_player = Player("0", "Missing", "None", slot["position"]["label"], "Missing")

                        if self._should_player_be_reported_as_inactive(home_player, teams_to_ignore, only_teams, player_names_to_ignore, teams_on_bye):
                            home_inactives.append(home_player)

                        if self._should_player_be_reported_as_inactive(away_player, teams_to_ignore, only_teams, player_names_to_ignore, teams_on_bye):
                            away_inactives.append(away_player)

            if home_inactives:
                inactive_rosters.append(InactiveRoster(home_team, home_inactives))
            if away_inactives:
                inactive_rosters.append(InactiveRoster(away_team, away_inactives))

        return inactive_rosters

    def _should_player_be_reported_as_inactive(self, player: Player,
                                               teams_to_ignore: List[str],
                                               only_teams: List[str],
                                               player_names_to_ignore: List[str],
                                               teams_on_bye: List[str]) -> bool:
        if player.name in player_names_to_ignore:
            return False

        if player.team in teams_to_ignore:
            return False

        if only_teams and player.team not in only_teams:
            return False

        if player.team in teams_on_bye:
            player.status = "BYE"

        if player.is_inactive():
            return True

    def _build_player_from_pro_player(self, player_data: Dict[str,
                                                              str]) -> Player:
        player_id = player_data["id"]
        name = player_data["nameFull"]
        position = player_data["position"]
        team = player_data["proTeamAbbreviation"]

        if "injury" in player_data:
            status = player_data["injury"]["typeFull"]
        else:
            status = ""

        return Player(player_id, name, team, position, status)

    def _build_roster_link(self, league_id: str, team_id: str) -> str:
        template = "https://www.fleaflicker.com/nfl/leagues/{league_id}/teams/{team_id}"
        return template.format(league_id=league_id, team_id=team_id)

    def _store_team_and_user_data_for_league(self, league_id: str, year: str):
        raw_league_data = api.fetch_league_standings(league_id, year)

        # Sometimes the API returns bad data. Attempt a retry here
        if "divisions" not in raw_league_data:
            print("Fleaflicker standings did not have divisions, retrying request")
            raw_league_data = api.fetch_league_standings(league_id, year)

        team_id_to_user = {}

        for division in raw_league_data["divisions"]:
            for team in division["teams"]:
                if "owners" in team:
                    user = User(str(team["owners"][0]["id"]),
                                team["owners"][0]["displayName"])
                else:
                    user = User("0", "No user")
                team_id_to_user[str(team["id"])] = user

        self._league_id_to_team_id_to_user[league_id] = team_id_to_user
