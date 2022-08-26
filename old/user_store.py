"""
   Copyright 2020 Kevin Emery

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

from typing import Dict, List

from sleeper_wrapper import League, User


class UserStore:
    """Utility class that stores Sleeper's user object for retrieval later

    Sleeper's API often only reports the user's ID, and if you want to map
    that to a human readable format a lookup against their API is required.
    This class serves as a thin, in-memory storage layer to avoid duplicating
    any lookups that need to occur.
    """
    def __init__(self):
        self._user_id_to_username: Dict[str, User] = {}

    def store_users_for_league(self, league: League):
        league_users = league.get_users()
        for user in league_users:
            self._user_id_to_username[user.get("user_id")] = user

    def get_username(self, user_id: str) -> str:
        try:
            return self._user_id_to_username[user_id].get("display_name")
        except KeyError:
            print("Error retrieving user: " + str(user_id))
            return "No User"
