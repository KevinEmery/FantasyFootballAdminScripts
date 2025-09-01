"""
   Copyright 2025 Kevin Emery

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

from datetime import datetime
from typing import List, Tuple

from library.model.league import League
from library.model.user import User
from library.platforms.sleeper.sleeper import Sleeper

LOG_DIRECTORY_NAME = "./logs/"
LOG_PREFIX = "log_"

def print_descriptive_log(log_method: str, log_line: str = "", write_to_file: bool = True):
    log_template = "{time:<20}{log_method:40.40}\t{log_line}"
    formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_date = datetime.now().strftime("%Y_%m_%d")

    log_file_path = LOG_DIRECTORY_NAME + LOG_PREFIX + formatted_date
    formatted_log = log_template.format(time=formatted_time,
                                        log_method=log_method,
                                        log_line=log_line)

    print(formatted_log)

    if write_to_file:
        try:
            with open(log_file_path, 'a+') as f:
                f.write(formatted_log + "\n")
        except Exception as e:
            # This is non-critical infra, just log to console and move on.
            print("Error writing log to file")
            print(e)


def get_matching_sleeper_league(sleeper: Sleeper, league_name: str, identifier: str, year: int) -> Tuple[League, User, str]:
    user = sleeper.get_admin_user_by_identifier(identifier)

    # Error handling for user
    if user.user_id == "Error":
        print_descriptive_log(
            "get_matching_sleeper_league",
            "No user found for {username}".format(username=identifier))
        return None, None, "Sleeper account `{username}` not found. Please double-check and try again.".format(username=identifier)

    leagues = sleeper.get_all_leagues_for_user(
                                      user,
                                      year,
                                      name_substring=league_name,
                                      include_pre_draft=True)

    # Error handling for leagues
    if len(leagues) == 0:
        print_descriptive_log(
            "get_matching_sleeper_league",
            "No leagues matching {league_name} found for {user}".format(
                league_name=league_name, user=identifier))
        return (None,
                None,
                "`{username}` does not have any leagues matching `{league_name}`. Please double-check and try again.".format(username=identifier,
                                                                                                                             league_name=league_name))
    elif len(leagues) > 1:
        print_descriptive_log(
            "get_matching_sleeper_league",
            "{user} has more than one league matching {league_name}".
            format(league_name=league_name, user=identifier))
        return (None,
                None,
                "`{username}` has more than one league matching `{league_name}`. Please be more specific.\n\n__Matching Leagues__\n{league_list}".format(username=identifier,
                                                                                                                                                         league_name=league_name,
                                                                                                                                                         league_list=_create_markdown_list_of_league_names(leagues)))

    return leagues[0], user, None

def _create_markdown_list_of_league_names(leagues: List[League]) -> str:
    league_list = ""
    template = "- {league_name}\n"

    for league in leagues:
        league_list += template.format(league_name=league.name)

    return league_list
    
def create_sleeper_draft_url_from_id(id: int) -> str:
    template = "https://sleeper.com/draft/nfl/{id}"
    return template.format(id=id)