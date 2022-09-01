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

from ... import common
from ...model.user import User

BASE_URL = "https://www.fleaflicker.com/api/"


def fetch_user_leagues(user: User, year: str):
    request_url = BASE_URL + "FetchUserLeagues?sport=NFL&season={year}".format(
        year=year)

    if user.user_id != "":
        request_url += "&user_id={id}".format(id=user.user_id)
    elif user.email != "":
        request_url += "&email={email}".format(email=user.email)
    else:
        raise Exception("User {user} must have either id or email set".format(
            user.name))

    return common._make_get_request_with_logging(request_url)["leagues"]


def fetch_league_standings(league_id: str, year: str):
    request_url = BASE_URL + "FetchLeagueStandings?sport=NFL&league_id={league_id}&season={year}".format(
        league_id=league_id, year=year)

    return common._make_get_request_with_logging(request_url)


def fetch_league_draft_board(league_id: str, year: str):
    request_url = BASE_URL + "FetchLeagueDraftBoard?sport=NFL&season={year}&league_id={league_id}".format(
        year=year, league_id=league_id)

    return common._make_get_request_with_logging(request_url)


def fetch_trades(league_id: str):
    request_url = BASE_URL + "FetchTrades?sport=NFL&league_id={league_id}&filter=TRADES_COMPLETED".format(
        league_id=league_id)

    return common._make_get_request_with_logging(request_url)["trades"]


def fetch_league_transactions(league_id: str, result_offset: int = 0):
    request_url = BASE_URL + "FetchLeagueTransactions?league_id={league_id}&result_offset={result_offset}".format(
        league_id=league_id, result_offset=result_offset)

    return common._make_get_request_with_logging(request_url)


def fetch_league_transactions_for_team(league_id: str,
                                       team_id: str,
                                       result_offset: int = 0):
    request_url = BASE_URL + "FetchLeagueTransactions?league_id={league_id}&team_id={team_id}&result_offset={result_offset}".format(
        league_id=league_id, team_id=team_id, result_offset=result_offset)

    return common._make_get_request_with_logging(request_url)


def fetch_league_scoreboard(league_id: str, week: int, year: str):
    request_url = BASE_URL + "FetchLeagueScoreboard?sport=NFL&league_id={league_id}&scoring_period={week}&season={year}".format(
        league_id=league_id, week=str(week), year=year)

    return common._make_get_request_with_logging(request_url)