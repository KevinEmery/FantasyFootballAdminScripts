class League(object):
    def __init__(self, name: str, size: int, league_id: str, draft_id: str = "0"):
        self.league_id = league_id
        self.draft_id = draft_id
        self.name = name
        self.size = size