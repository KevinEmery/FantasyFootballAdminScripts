"""
   Copyright 2023 Kevin Emery

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

from ... import common
from ...model.user import User

BASE_URL = "https://api.sleeper.app/v1/"


def get_user_from_identifier(identifier: str) -> User:
    request_url = BASE_URL + "user/{identifier}".format(identifier=identifier)

    response_json = common._make_get_request_with_logging(request_url)

    # In the event of an error, this comes back as None. Doing this allows
    # us to more gracefully fail down the line instead of throwing errors here.
    if response_json is None:
        print("Error retrieving sleeper user: " + identifier)
        return User("Error", "Error")

    return User(response_json["user_id"], response_json["username"])


def get_all_leagues_for_user(user: User, year: int):
    request_url = BASE_URL + "user/{user_id}/leagues/nfl/{year}".format(
        user_id=user.user_id, year=str(year))

    return common._make_get_request_with_logging(request_url)

def get_league(league_id: str):
    request_url = request_url = BASE_URL + "league/{league_id}".format(league_id=league_id)

    return common._make_get_request_with_logging(request_url)

def get_all_picks_for_draft(draft_id: str):
    request_url = BASE_URL + "draft/{draft_id}/picks".format(draft_id=draft_id)

    return common._make_get_request_with_logging(request_url)


def get_draft(draft_id: str):
    request_url = BASE_URL + "draft/{draft_id}".format(draft_id=draft_id)

    return common._make_get_request_with_logging(request_url)


def get_league_transactions_for_week(league_id: str, week: str):
    request_url = BASE_URL + "league/{league_id}/transactions/{round}".format(
        league_id=league_id, round=week)

    return common._make_get_request_with_logging(request_url)


def get_rosters_for_league(league_id: str):
    request_url = BASE_URL + "league/{league_id}/rosters".format(
        league_id=league_id)

    return common._make_get_request_with_logging(request_url)


def get_matchups_for_league_and_week(league_id: str, week: int):
    request_url = BASE_URL + "league/{league_id}/matchups/{week}".format(
        league_id=league_id, week=str(week))

    return common._make_get_request_with_logging(request_url)


def get_traded_picks(league_id: str):
    request_url = BASE_URL + "league/{league_id}/traded_picks".format(
        league_id=league_id)

    return common._make_get_request_with_logging(request_url)


def get_all_players():
    request_url = BASE_URL + "players/nfl"

    return common._make_get_request_with_logging(request_url)
