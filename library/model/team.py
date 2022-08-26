from .user import User


class Team(object):
    def __init__(self, team_id: str, manager: User, roster_link: str):
        self.team_id = team_id
        self.manager = manager
        self.roster_link = roster_link