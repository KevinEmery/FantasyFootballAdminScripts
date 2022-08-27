from datetime import datetime
from typing import List

from .tradedetail import TradeDetail


class Trade(object):
    def __init__(self, trade_time: datetime, details: List[TradeDetail]):
        self.trade_time = trade_time
        self.details = details

    def __lt__(self, other):
        return self.trade_time < other.trade_time