from typing import List

from .player import Player
from .team import Team
from .transaction import Transaction


class InactiveRoster(object):
    def __init__(self, team: Team, inactives: List[Player],
                 last_transaction: Transaction):
        self.team = team
        self.inactives = inactives
        self.last_transaction last_transaction