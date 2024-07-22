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

from typing import List

from .team import Team
from .player import Player


class Roster(object):
    def __init__(self, team: Team, starters: List[Player], bench: List[Player],
                 taxi: List[Player]):
        self.team = team
        self.starters = starters
        self.bench = bench
        self.taxi = taxi