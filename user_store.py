from sleeper_wrapper import League, User
from typing import Dict, List


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
