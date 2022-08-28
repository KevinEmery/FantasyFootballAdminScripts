from .league import League
from .team import Team


class WeeklyScore(object):
    def __init__(self, league: League, team: Team, week: int, score: float):
        self.league = league
        self.team = team
        self.week = week
        self.score = score
