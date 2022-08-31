"""
   Copyright 2022 Kevin Emery

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

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

    def add_draft_pick_with_slot(self, year: str, round: int, slot: int):
        template = "{year} {round}.{slot}"
        self.added_draft_picks.append(
            template.format(year=year, round=str(round), slot=str(slot)))

    def lose_draft_pick(self, year: str, round: int):
        self.lost_draft_picks.append(year + " " +
                                     self._append_round_suffix(round))

    def lose_draft_pick_with_slot(self, year: str, round: int, slot: int):
        template = "{year} {round}.{slot}"
        self.lost_draft_picks.append(
            template.format(year=year, round=str(round), slot=str(slot)))

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