from typing import List

from .team import Team


class Transaction(object):
    def __init__(self, timestamp: int, transaction_type: str,
                 teams: List[Team]):
        self.timestamp = timestamp
        self.transaction_type = transaction_type
        self.teams = teams