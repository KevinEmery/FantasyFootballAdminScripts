import requests

from typing import Any, Dict, List

from ...model.user import User

BASE_URL = "https://api.sleeper.app/v1/"


def get_user_from_username(username: str) -> User:
    request_url = BASE_URL + "user/{username}".format(username=username)

    response_string = requests.get(request_url)
    response_json = response_string.json()
    return User(response_json["user_id"], response_json["username"])


def get_all_leagues_for_user(user: User, sport: str, year: str) -> List[str]:
    request_url = BASE_URL + "user/{user_id}/leagues/{sport}/{year}".format(
        user_id=user.user_id, sport=sport, year=year)

    response = requests.get(request_url)
    return response.json()


def get_all_picks_for_draft(draft_id: str) -> List[str]:
    request_url = BASE_URL + "draft/{draft_id}/picks".format(draft_id=draft_id)

    response = requests.get(request_url)
    return response.json()


def get_all_players(sport: str) -> Dict[str, Dict[str, Any]]:
    request_url = BASE_URL + "players/{sport}".format(sport=sport)

    response = requests.get(request_url)
    return response.json()
