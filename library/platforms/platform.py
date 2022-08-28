import re

from typing import List

from ..model.draftedplayer import DraftedPlayer
from ..model.league import League
from ..model.seasonscore import SeasonScore
from ..model.trade import Trade
from ..model.user import User
from ..model.weeklyscore import WeeklyScore


class Platform:
    def get_admin_user_by_identifier(self, identifier: str) -> User:
        pass

    def get_all_leagues_for_user(self, user: User, year: str,
                                 name_regex: re.Pattern) -> List[League]:
        pass

    def get_drafted_players_for_league(self,
                                       league: League) -> List[DraftedPlayer]:
        pass

    def get_all_trades_for_league(self, League: League) -> List[Trade]:
        pass

    def get_weekly_scores_for_league_and_week(self, league: League, week: int,
                                              year: str) -> List[WeeklyScore]:
        pass

    def get_season_scores_for_league(self, league: League,
                                     year: str) -> List[SeasonScore]:
        pass