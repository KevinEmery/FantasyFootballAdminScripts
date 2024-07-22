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

import re

from typing import Dict, List

from .. import common
from ..model.draftedplayer import DraftedPlayer
from ..model.inactiveroster import InactiveRoster
from ..model.league import League
from ..model.seasonscore import SeasonScore
from ..model.team import Team
from ..model.trade import Trade
from ..model.transaction import Transaction
from ..model.user import User
from ..model.weeklyscore import WeeklyScore


class Platform:
    def get_admin_user_by_identifier(self, identifier: str) -> User:
        pass

    def get_all_leagues_for_user(
            self,
            user: User,
            year: int = common.DEFAULT_YEAR,
            name_regex: re.Pattern = re.compile(".*"),
            name_substring: str = "",
            store_user_info: bool = True,
            include_pre_draft: bool = False) -> List[League]:
        pass

    def get_drafted_players_for_league(
            self,
            league: League,
            year: int = common.DEFAULT_YEAR) -> List[DraftedPlayer]:
        pass

    def get_all_trades_for_league(self, League: League,
                                  year: int) -> List[Trade]:
        pass

    def get_weekly_scores_for_league_and_week(self, league: League, week: int,
                                              year: int) -> List[WeeklyScore]:
        pass

    def get_season_scores_for_league(self, league: League,
                                     year: int) -> List[SeasonScore]:
        pass

    def get_last_transaction_for_teams_in_league(
            self, league: League, year: int) -> Dict[Team, Transaction]:
        pass

    def get_inactive_rosters_for_league_and_week(
            self,
            league: League,
            week: int,
            year: int,
            teams_to_ignore: List[str] = [],
            only_teams: List[str] = [],
            player_names_to_ignore: List[str] = []) -> List[InactiveRoster]:
        pass

    def get_team_for_user(self, league: League, user: User) -> Team:
        pass
