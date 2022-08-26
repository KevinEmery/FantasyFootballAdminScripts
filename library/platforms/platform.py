from typing import List

from ..defaults import *

from ..model.draftedplayer import DraftedPlayer
from ..model.league import League
from ..model.user import User


class Platform:
    def get_user_by_identifier(self, username: str) -> User:
        pass

    def get_all_leagues_for_user(self,
                                 user: User,
                                 sport: str = SPORT,
                                 year: str = YEAR) -> List[League]:
        pass

    def get_drafted_players_for_league(self,
                                       league: League) -> List[DraftedPlayer]:
        pass