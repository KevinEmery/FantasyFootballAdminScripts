from typing import List

from .player import Player
from .team import Team


class TradeDetail(object):
    def __init__(self, team: Team):
        self.team = team
        self.added_players: List[Player] = []
        self.lost_players: List[Player] = []
        self.added_draft_picks: List[str] = []
        self.lost_draft_picks: List[str] = []
        self.faab_added: int = 0
        self.faab_lost: int = 0

    def add_player(self, player: Player):
        self.added_players.append(player)

    def lose_player(self, player: Player):
        self.lost_players.append(player)

    def add_draft_pick(self, year: str, round: int):
        self.added_draft_picks.append(year + " " +
                                      self._append_round_suffix(round))

    def lose_draft_pick(self, year: str, round: int):
        self.draft_picks_lost.append(year + " " +
                                     self._append_round_suffix(round))

    def add_faab(self, faab: int):
        self.faab_added += faab

    def lose_faab(self, faab: int):
        self.faab_lost += faab

    def _append_round_suffix(self, round: int) -> str:
        if round == 1:
            return str(round) + "st"
        elif round == 2:
            return str(round) + "nd"
        elif round == 3:
            return str(round) + "rd"
        elif round == 4 or round == 5 or round == 6:
            return str(round) + "th"
        else:
            return "Round " + str(round)