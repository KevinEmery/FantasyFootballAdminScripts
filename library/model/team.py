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

from .user import User


class Team(object):
    def __init__(self, team_id: str, manager: User, roster_link: str):
        self.team_id = team_id
        self.manager = manager
        self.roster_link = roster_link

    def __eq__(self, other):
        return self.team_id == other.team_id

    def __hash__(self):
        return hash((self.team_id, self.manager, self.roster_link))