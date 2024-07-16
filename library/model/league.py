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

from typing import Dict

class League(object):
    def __init__(self, name: str, size: int, league_id: str, roster_counts: Dict[str, int], draft_id: str = "0"):
        self.league_id = league_id
        self.draft_id = draft_id
        self.name = name
        self.size = size
        self.roster_counts = roster_counts

    def get_roster_count_string(self) -> str:
        return_string = ""
        template = "{count} {position}, "

        for position, count in self.roster_counts.items():
            return_string += template.format(count=count, position=position)

        return return_string[:-2]
