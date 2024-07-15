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

from json import JSONEncoder

class Player(object):
    def __init__(self, player_id: str, name: str, team: str, position: str,
                 status: str):
        self.player_id = player_id
        self.name = name
        self.team = team
        self.position = position
        self.status = status

    def is_inactive(self):
        return self.status is not None and self.status != "" and self.status != "Questionable"

    def __eq__(self, other):
        return self.player_id == other.player_id

    def __hash__(self):
        return hash(self.player_id)

class PlayerEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Player):
            return obj.__dict__
        return super().default(obj)