
from typing import List

from .inactiveroster import InactiveRoster
from .league import League

class LeagueInactivity(object):
    def __init__(self, league: League, rosters: List[InactiveRoster]):
        self.league = league
        self.rosters = rosters