from typing import List

from .team import Team


class Transaction(object):
    def __init__(self, time: int, transaction_type: str, team: Team):
        self.time = time
        self.transaction_type = transaction_type
        self.team = team

    def __lt__(self, other):
        return self.time < other.time