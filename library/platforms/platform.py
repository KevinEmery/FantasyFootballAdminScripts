import re

from typing import Dict, List

from .. import common
from ..model.draftedplayer import DraftedPlayer
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

    def get_all_leagues_for_user(self,
                                 user: User,
                                 year: str = common.DEFAULT_YEAR,
                                 name_regex: re.Pattern = ".*",
                                 store_user_info: bool = True) -> List[League]:
        pass

    def get_drafted_players_for_league(
            self,
            league: League,
            year: str = common.DEFAULT_YEAR) -> List[DraftedPlayer]:
        pass

    def get_all_trades_for_league(self, League: League) -> List[Trade]:
        pass

    def get_weekly_scores_for_league_and_week(self, league: League, week: int,
                                              year: str) -> List[WeeklyScore]:
        pass

    def get_season_scores_for_league(self, league: League,
                                     year: str) -> List[SeasonScore]:
        pass

    def get_last_transaction_for_teams_in_league(
            self, league: League) -> Dict[Team, Transaction]:
        pass