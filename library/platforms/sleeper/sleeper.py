from typing import List

from ..platform import Platform

from ...model.league import League
from ...model.trade import Trade


class Sleeper(Platform):
    def get_all_trades(self, league: League) -> List[Trade]:
        return [1, 2]
