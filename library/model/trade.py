from typing import List

from .tradedetail import TradeDetail


class Trade(object):
    def __init__(self, timestamp: int, details: List[TradeDetail]):
        self.timestamp = timestamp
        self.details = details