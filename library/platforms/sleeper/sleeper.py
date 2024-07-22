"""
   Copyright 2024 Kevin Emery

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

import json
import os
import re
import time

from datetime import datetime
from typing import Dict, List

from . import api

from ..platform import Platform

from ... import common
from ...model.draft import Draft
from ...model.draft import DraftType
from ...model.draftedplayer import DraftedPlayer
from ...model.inactiveroster import InactiveRoster
from ...model.league import League
from ...model.player import Player
from ...model.player import PlayerEncoder
from ...model.roster import Roster
from ...model.seasonscore import SeasonScore
from ...model.team import Team
from ...model.trade import Trade
from ...model.tradedetail import TradeDetail
from ...model.transaction import Transaction
from ...model.user import User
from ...model.weeklyscore import WeeklyScore

# Directory is relative to the directory where script is run
PLAYER_DATA_FILE_PATH = "./data/sleeper_player_data"

# Sleeper recommendation is a 24-hour refresh
PLAYER_DATA_REFRESH_INTERVAL_SECONDS = 24 * 60 * 60


class Sleeper(Platform):
    def __init__(self, force_player_data_refresh: bool = False):
        # Rather than do this lookup the first time we need it, just
        # proactively retrieve all player data up front
        self._player_id_to_player: Dict[str,
                                        Player] = self._initialize_player_data(
                                            force_player_data_refresh)
        self._owner_id_to_user: Dict[str, User] = {}
        self._league_id_to_roster_num_to_user: Dict[str, Dict[int, User]] = {}

    def get_admin_user_by_identifier(self, identifier: str) -> User:
        return api.get_user_from_identifier(identifier)

    def get_all_leagues_for_user(self,
                                 user: User,
                                 year: int = common.DEFAULT_YEAR,
                                 name_regex: re.Pattern = re.compile(".*"),
                                 name_substring: str = "",
                                 store_user_info: bool = True,
                                 include_pre_draft: bool = False) -> List[League]:
        leagues = []

        raw_response_json = api.get_all_leagues_for_user(user, str(year))

        # We can treat None as just an empty response. This can happen in error
        # cases where we don't get a valid user.
        if raw_response_json is None:
            return leagues

        for raw_league in raw_response_json:
            roster_counts = {}
            for position in raw_league["roster_positions"]:
                # Simplify the Flex listings to SF, IDP, and Flex
                if position == "SUPER_FLEX":
                    position = "SF"
                elif position == "IDP_FLEX":
                    position = "IDP_FLEX"
                elif "FLEX" in position:
                    position = "FLEX"

                if position not in roster_counts:
                    roster_counts[position] = 0

                roster_counts[position] = roster_counts[position] + 1

            scoring_settings = raw_league["scoring_settings"]

            if "rec" in scoring_settings:
                ppr = scoring_settings["rec"]
            else:
                ppr = 0.0

            if "bonus_rec_te" in scoring_settings:
                tep = scoring_settings["bonus_rec_te"]
            else:
                tep = 0.0

            league = League(raw_league["name"], raw_league["total_rosters"],
                            raw_league["league_id"], roster_counts, ppr, tep,
                            raw_league["draft_id"])

            if (raw_league["status"] != "pre_draft"
                    or include_pre_draft) and self._league_name_matches(
                        league.name, name_substring, name_regex):
                if store_user_info:
                    self._store_roster_and_user_data_for_league(league)
                leagues.append(league)

        return leagues


    def _league_name_matches(self, league_name: str, name_substring: str,
                             name_regex: re.Pattern) -> bool:
        return name_substring.lower() in league_name.lower() and name_regex.match(league_name)

    def get_drafted_players_for_league(
            self,
            league: League,
            year: int = common.DEFAULT_YEAR) -> List[DraftedPlayer]:
        drafted_players = []

        raw_draft_data = api.get_all_picks_for_draft(league.draft_id)

        for raw_draft_pick in raw_draft_data:
            drafted_players.append(
                DraftedPlayer(
                    self._player_id_to_player[raw_draft_pick["player_id"]],
                    raw_draft_pick["pick_no"]))

        return drafted_players

    def get_all_trades_for_league(self, league: League, year: int) -> List[Trade]:
        all_trades = []
        roster_num_to_user = self._league_id_to_roster_num_to_user[
            league.league_id]

        # Save off the draft data in order to attribute picks
        raw_draft = api.get_draft(league.draft_id)
        draft = self._create_draft_from_response(raw_draft)

        # Iterate through every week of the season (and then a couple more just to be sure)
        for i in range(1, 20):
            raw_transaction_data = api.get_league_transactions_for_week(
                league.league_id, i)

            # Guard against this coming back as None, and just skip the week
            if raw_transaction_data is None:
                continue

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
                    # Include draft slot if it's for the current year
                    if pick["season"] == draft.year:
                        # Owner id is the person who received the draft pick
                        roster_id_to_trade_detail[
                            pick["owner_id"]].add_draft_pick_with_slot(
                                pick["season"], pick["round"],
                                draft.get_pick_num_within_round(
                                    pick["roster_id"], pick["round"]))

                        # Previous owner is who is trading it away
                        roster_id_to_trade_detail[pick[
                            "previous_owner_id"]].lose_draft_pick_with_slot(
                                pick["season"], pick["round"],
                                draft.get_pick_num_within_round(
                                    pick["roster_id"], pick["round"]))

                    # Otherwise just do the generic year/round
                    else:
                        # Owner id is the person who received the draft pick
                        roster_id_to_trade_detail[
                            pick["owner_id"]].add_draft_pick(
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
                trade_id = transaction["transaction_id"]
                all_trades.append(Trade(trade_id, league, transaction_time, all_details))

        return all_trades

    def get_weekly_scores_for_league_and_week(self, league: League, week: int,
                                              year: int) -> List[WeeklyScore]:
        weekly_scores = []

        weekly_matchups = api.get_matchups_for_league_and_week(
            league.league_id, week)
        roster_num_to_user = self._league_id_to_roster_num_to_user[
            league.league_id]

        # Each "matchup" represents a single teams performance
        for matchup in weekly_matchups:
            roster_id = matchup["roster_id"]
            team = Team(roster_id, roster_num_to_user[roster_id],
                        self._create_roster_link(league.league_id, roster_id))
            weekly_scores.append(
                WeeklyScore(league, team, week, matchup.get("points")))

        return weekly_scores

    def get_season_scores_for_league(self, league: League,
                                     year: int) -> List[SeasonScore]:
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

            season_scores.append(SeasonScore(league, team, total_points_for))

        return season_scores

    def get_last_transaction_for_teams_in_league(
            self, league: League, year: int) -> Dict[Team, Transaction]:
        last_transaction_per_team = {}
        all_transactions = []
        roster_num_to_user = self._league_id_to_roster_num_to_user[
            league.league_id]

        # Iterate through every week of the season (and then a couple more
        # just to be sure),  gathering all of the transactions
        # A potential optimization would be to combine this step with the
        # "one per team" logic by starting at the end. But that assumes either
        # ordering within each week on the API or requires logic to order each
        # week, and frankly not doing that is just easier for now.
        for week in range(1, 20):
            raw_transactions = api.get_league_transactions_for_week(
                league.league_id, week)

            for raw_transaction in raw_transactions:
                transaction_time = datetime.fromtimestamp(
                    raw_transaction["status_updated"] / 1000)
                transaction_type = raw_transaction["type"]

                # Creates a transaction entry for each involved team, which is easier to parse
                # afterwards
                for roster_id in raw_transaction["roster_ids"]:
                    team = Team(
                        roster_id, roster_num_to_user[roster_id],
                        self._create_roster_link(league.league_id, roster_id))
                    all_transactions.append(
                        Transaction(transaction_time, transaction_type, team))

        # Sort the transactions last to first and grab each team's most recent
        all_transactions.sort(reverse=True)

        for transaction in all_transactions:
            if transaction.team not in last_transaction_per_team:
                last_transaction_per_team[transaction.team] = transaction

            if len(last_transaction_per_team) >= league.size:
                return last_transaction_per_team

        # Backfill data for any team that doesn't have a transaction
        for roster_id in range(1, league.size + 1):
            team = Team(roster_id, roster_num_to_user[roster_id],
                        self._create_roster_link(league.league_id, roster_id))
            if team not in last_transaction_per_team:
                last_transaction_per_team[team] = Transaction(
                    datetime.fromtimestamp(common.DEC_31_1999_SECONDS), "None",
                    team)

        return last_transaction_per_team

    def get_inactive_rosters_for_league_and_week(
            self,
            league: League,
            week: int,
            year: int,
            teams_to_ignore: List[str] = [],
            only_teams : List[str] = [],
            player_names_to_ignore: List[str] = []) -> List[InactiveRoster]:
        inactive_rosters = []
        roster_num_to_user = self._league_id_to_roster_num_to_user[
            league.league_id]
        teams_on_bye = common.TEAMS_ON_BYE[week]

        raw_matchups = api.get_matchups_for_league_and_week(
            league.league_id, week)
        for raw_matchup in raw_matchups:
            roster_id = raw_matchup["roster_id"]
            user = roster_num_to_user[roster_id]
            inactive_players = []

            starting_player_ids = raw_matchup["starters"]

            # I've run into a strange issue where someone's starters come back
            # as None. Log that to console and move on we'll need to manually check
            if starting_player_ids is None:
                template = "{league} - {username}'s starters list is None"
                print(template.format(league=league.name, username=user.name))
                continue

            for player_id in starting_player_ids:
                player = self._player_id_to_player[player_id]

                if player.name in player_names_to_ignore:
                    continue
                
                if player.team in teams_to_ignore:
                    continue
                
                if only_teams and player.team not in only_teams:
                    continue

                if player.is_inactive():
                    inactive_players.append(player)
                elif player.team in teams_on_bye:
                    player.status = "BYE"
                    inactive_players.append(player)

            if inactive_players:
                team = Team(
                    roster_id, user,
                    self._create_roster_link(league.league_id, roster_id))
                inactive_rosters.append(InactiveRoster(team, inactive_players))

        return inactive_rosters

    def get_team_for_user(self, league: League, user: User) -> Team:
        roster_num_to_user = self._league_id_to_roster_num_to_user[
            league.league_id]

        for roster_id, stored_user in roster_num_to_user.items():
            if user == stored_user:
                team = Team(
                    roster_id, user,
                    self._create_roster_link(league.league_id, roster_id))
                return team

        return Team(0, user, self._create_roster_link(league.league_id, 0))

    def get_roster_for_league_and_user(self, league: League, user: User) -> Roster:
        raw_rosters = api.get_rosters_for_league(league.league_id)

        for raw_roster in raw_rosters:
            if raw_roster["owner_id"] == user.user_id or raw_roster[
                    "co_owners"] and user.user_id in raw_roster["co_owners"]:
                roster_id = raw_roster["roster_id"]
                starters = []
                bench = []
                taxi = []
                team = Team(roster_id, user,
                            self._create_roster_link(league.league_id, roster_id))

                for player_id in raw_roster["players"]:
                    player = self._player_id_to_player[player_id]
                    if player_id in raw_roster["starters"]:
                        starters.append(player)
                    elif raw_roster[
                            "taxi"] is not None and player_id in raw_roster["taxi"]:
                        taxi.append(player)
                    else:
                        bench.append(player)

                return Roster(team, starters, bench, taxi)

        return None


    def _create_draft_from_response(self, raw_draft) -> Draft:
        raw_draft_type = raw_draft["type"]
        if raw_draft_type == "snake":
            draft_type = DraftType.SNAKE
        elif raw_draft_type == "linear":
            draft_type = DraftType.LINEAR
        elif raw_draft_type == "auction":
            draft_type = DraftType.AUCTION
        else:
            print("Unknown draft type: " + raw_draft_type)
            exit()

        league_size = raw_draft["settings"]["teams"]
        team_id_to_draft_slot = {}

        slot_to_roster_id = raw_draft["slot_to_roster_id"]
        for slot in range(1, league_size + 1):
            team_id_to_draft_slot[slot_to_roster_id[str(slot)]] = slot

        return Draft(raw_draft["season"], raw_draft["draft_id"], draft_type,
                     raw_draft["settings"]["reversal_round"], league_size,
                     team_id_to_draft_slot)

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

    def _initialize_player_data(self,
                                force_refresh: bool) -> Dict[str, Player]:
        if force_refresh or self._should_refresh_player_data():
            return self._retrieve_player_data_from_api()

        return self._retrieve_player_data_from_file()


    def _should_refresh_player_data(self) -> bool:
        if not os.path.exists(PLAYER_DATA_FILE_PATH):
            return True

        time_last_modified = int(os.path.getmtime(PLAYER_DATA_FILE_PATH))
        time_now = int(time.time())

        return time_now - time_last_modified > PLAYER_DATA_REFRESH_INTERVAL_SECONDS


    def _retrieve_player_data_from_api(self) -> Dict[str, Player]:
        # This should be happening infrequently enough that we don't see this log often.
        # If we see this more than expected, investigate
        print("Retrieving player data from the Sleeper API")
        player_id_to_player = {}

        raw_player_map = api.get_all_players()

        for player_id in raw_player_map:
            raw_player = raw_player_map[player_id]
            player_name = "{first} {last}".format(first=raw_player["first_name"],
                                                  last=raw_player["last_name"])

            player_id_to_player[player_id] = Player(player_id, player_name,
                                                    raw_player["team"],
                                                    raw_player["position"],
                                                    raw_player["injury_status"])

        # Insert a dummy missing player at ID 0
        player_id_to_player["0"] = Player("0", "Missing", "None", "None", "None")

        # Every time we pull data from the API, write it out to the file
        self._write_player_data_to_file(player_id_to_player)

        return player_id_to_player

    def _retrieve_player_data_from_file(self) -> Dict[str, Player]:
        # The assumption is made that if we get here, the file exists
        data = {}
        with open(PLAYER_DATA_FILE_PATH, 'r') as file:
            raw_data = json.load(file)

            for player_id, player_raw_data in raw_data.items():
                data[player_id] = Player(player_raw_data["player_id"],
                                         player_raw_data["name"],
                                         player_raw_data["team"],
                                         player_raw_data["position"],
                                         player_raw_data["status"])

        return data

            
    def _write_player_data_to_file(self, player_data: Dict[str, Player]):
        with open(PLAYER_DATA_FILE_PATH, 'w') as file:
            file.write(json.dumps(player_data, cls=PlayerEncoder))
