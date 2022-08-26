from .player import Player


class DraftedPlayer(object):
    def __init__(self, player: Player, draft_position: int):
        self.player = player
        self.draft_position = draft_position