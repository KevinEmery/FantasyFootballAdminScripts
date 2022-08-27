from typing import List

from ..model.draftedplayer import DraftedPlayer
from ..model.league import League
from ..model.trade import Trade
from ..model.user import User


class Platform:
    def get_admin_user_by_identifier(self, identifier: str) -> User:
        pass

    def get_all_leagues_for_user(self, user: User, sport: str,
                                 year: str) -> List[League]:
        pass

    def get_drafted_players_for_league(self,
                                       league: League) -> List[DraftedPlayer]:
        pass

    def get_all_trades_for_league(self, League:League) -> List[Trade]:
        pass