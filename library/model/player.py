class Player(object):
    def __init__(self, player_id: str, name: str, team: str, position: str):
        self.player_id = player_id
        self.name = name
        self.team = team
        self.position = position