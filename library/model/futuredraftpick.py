"""
   Copyright 2024 Kevin Emery

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


class FutureDraftPick(object):
    def __init__(self, year: int, pick_round: int):
        self.year = year
        self.round = pick_round

    def __eq__(self, other):
        if not isinstance(other, FutureDraftPick):
            return NotImplemented

        return self.year == other.year and self.round == other.round

    def __hash__(self):
        return hash((self.year, self.round))

    def __lt__(self, other):
        if not isinstance(other, FutureDraftPick):
            return NotImplemented

        if self.year == other.year:
            return self.round < other.round
        else:
            return self.year < other.year

    def __str__(self) -> str:
        return "{year} {round}".format(year=self.year,
                                       round=self.get_round_with_suffix())

    def get_round_with_suffix(self) -> str:
        if self.round == 1:
            return str(self.round) + "st"
        elif self.round == 2:
            return str(self.round) + "nd"
        elif self.round == 3:
            return str(self.round) + "rd"
        else:
            return str(self.round) + "th"
