from .league import League
from .team import Team


class SeasonScore(object):
    def __init__(self, league: League, team: Team, score: float):
        self.league = league
        self.team = team
        self.score = score
