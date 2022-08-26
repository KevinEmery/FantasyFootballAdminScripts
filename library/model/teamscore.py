from .team import Team


class TeamScore(object):
    def __init__(self, team: Team, week: int, weekly_score: float,
                 season_score: float):
        self.team = team
        self.week = week
        self.weekly_score = weekly_score
        self.season_score = season_score