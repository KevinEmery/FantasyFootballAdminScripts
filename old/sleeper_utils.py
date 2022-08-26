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

from sleeper_wrapper import League

from user_store import UserStore

def is_league_inactive(league: League) -> bool:
    """Determines if a league is inactive based on the rosters

    This is used as a mildly hacky helper method. It looks through the
    rosters of every team, and if there are any players on any of them
    it classifies the league as active. However if all the player
    lists are empty, it says the league is inactive and returns True
    """
    for roster in league.get_rosters():
        if roster.get("players"):
            return False

    return True

def create_roster_id_to_username_dict(league: League, user_store: UserStore) -> Dict[int, str]:
    """Provides an easily accessible mapping from roster id to username

    Sleeper stores several pieces of league information by roster id,
    which is challenging when you're looking to print out human-readable
    information that uses username instead of roster id. This helper
    accepts a league object and a UserStore populated with a league's data,
    returning the map of roster_id to username for that league.
    """
    rosters = league.get_rosters()
    roster_id_to_username = {}

    for roster in rosters:
        roster_id_to_username[roster.get(
            "roster_id")] = user_store.get_username(roster.get("owner_id"))

    return roster_id_to_username
