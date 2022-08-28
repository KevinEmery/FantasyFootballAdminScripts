from enum import Enum

from library.model.seasonscore import SeasonScore
from library.model.weeklyscore import WeeklyScore


class PlatformSelection(Enum):
    SLEEPER = 1
    FLEAFLICKER = 2


def format_weekly_score_for_table(score: WeeklyScore) -> str:
    template = "{username:.<20}{points:06.2f}, Week {week:<2} ({league_name})"
    return template.format(league_name=score.league.name,
                           username=score.team.manager.name,
                           week=score.week,
                           points=score.score)


def format_seasonal_score_for_table(score: SeasonScore) -> str:
    template = "{username:.<20}{points_for:06.2f} ({league_name})"
    return template.format(league_name=score.league.name,
                           username=score.team.manager.name,
                           points_for=score.score)