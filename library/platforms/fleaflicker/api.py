import requests

from typing import Any, Dict, List

from ...model.user import User

BASE_URL = "https://www.fleaflicker.com/api/"


def fetch_user_leagues(user: User, sport: str, year: str) -> List[str]:
    request_url = BASE_URL + "FetchUserLeagues?sport={sport}&season={year}".format(
        sport=sport.upper(), year=year)

    if user.user_id != "":
        request_url += "&user_id={id}".format(id=user.user_id)
    elif user.email != "":
        request_url += "&email={email}".format(email=user.email)
    else:
        raise Exception("User {user} must have either id or email set".format(
            user.name))

    response = requests.get(request_url)
    return response.json()["leagues"]


def fetch_league_standings(league_id: str, sport: str) -> List[str]:
    request_url = BASE_URL + "FetchLeagueStandings?sport={sport}&league_id={league_id}".format(
        sport=sport.upper(), league_id=league_id)

    response = requests.get(request_url)
    return response.json()


def fetch_league_draft_board(league_id: str, sport: str,
                             year: str) -> List[str]:
    request_url = BASE_URL + "FetchLeagueDraftBoard?sport={sport}&season={year}&league_id={league_id}".format(
        sport=sport.upper(), year=year, league_id=league_id)

    response = requests.get(request_url)
    return response.json()


def fetch_trades(league_id: str, sport: str) -> List[str]:
    request_url = BASE_URL + "FetchTrades?sport={sport}&league_id={league_id}&filter=TRADES_COMPLETED".format(
        sport=sport.upper(), league_id=league_id)

    response = requests.get(request_url)
    return response.json()["trades"]