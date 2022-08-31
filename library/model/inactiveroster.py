from typing import List

from .player import Player
from .team import Team
from .transaction import Transaction


class InactiveRoster(object):
    def __init__(self,
                 team: Team,
                 inactive_players: List[Player],
                 last_transaction: Transaction = None):
        self.team = team
        self.inactive_players = inactive_players
        self.last_transaction = last_transaction