import requests

from typing import Any, Dict, List

from ...model.user import User

BASE_URL = "https://api.sleeper.app/v1/"


def get_user_from_identifier(identifier: str) -> User:
    request_url = BASE_URL + "user/{identifier}".format(identifier=identifier)

    response_string = requests.get(request_url)
    response_json = response_string.json()
    return User(response_json["user_id"], response_json["username"])


def get_all_leagues_for_user(user: User, year: str) -> List[str]:
    request_url = BASE_URL + "user/{user_id}/leagues/nfl/{year}".format(
        user_id=user.user_id, year=year)

    response = requests.get(request_url)
    return response.json()


def get_all_picks_for_draft(draft_id: str) -> List[str]:
    request_url = BASE_URL + "draft/{draft_id}/picks".format(draft_id=draft_id)

    response = requests.get(request_url)
    return response.json()


def get_league_transactions_for_week(league_id: str, week: str) -> List[str]:
    request_url = BASE_URL + "league/{league_id}/transactions/{round}".format(
        league_id=league_id, round=week)

    response = requests.get(request_url)
    return response.json()


def get_rosters_for_league(league_id: str) -> List[str]:
    request_url = BASE_URL + "league/{league_id}/rosters".format(
        league_id=league_id)

    response = requests.get(request_url)
    return response.json()

def get_matchups_for_league_and_week(league_id: str, week: int) -> List[str]:
    request_url = BASE_URL + "league/{league_id}/matchups/{week}".format(league_id=league_id, week=str(week))

    response = requests.get(request_url)
    return response.json()


def get_all_players() -> Dict[str, Dict[str, Any]]:
    request_url = BASE_URL + "players/nfl"

    response = requests.get(request_url)
    return response.json()
