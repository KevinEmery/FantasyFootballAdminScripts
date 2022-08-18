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
"""Script to display all of the trades in one or more leagues

This script will iterate over all specified leagues for the given user and output
a Discord-formatted list of the trades within the provided date range
"""

import argparse
import re
import sys
from datetime import datetime
from dateutil import parser
from typing import Dict, List

from sleeper_wrapper import League, Players, User

from sleeper_utils import is_league_inactive, create_roster_id_to_username_dict
from user_store import UserStore

# Needs to be large enough for longest player name plus a couple (MVS)
OUTPUT_COLUMN_WIDTH = 30


class TeamTradeDetails:
    def __init__(self, roster_id: int):
        self.roster_id = roster_id
        self.adds = []
        self.losses = []
        self.draft_picks_added = []
        self.draft_picks_lost = []
        self.faab_added = 0
        self.faab_lost = 0

    def add_player(self, player_id: str):
        self.adds.append(player_id)

    def lose_player(self, player_id: str):
        self.losses.append(player_id)

    def _append_round_suffix(self, round: int) -> str:
        if round == 1:
            return str(round) + "st"
        elif round == 2:
            return str(round) + "nd"
        elif round == 3:
            return str(round) + "rd"
        elif round == 4 or round == 5 or round == 6:
            return str(round) + "th"
        else:
            return "Round " + str(round)

    def add_draft_pick(self, season: str, round: int):
        self.draft_picks_added.append(season + " " +
                                      self._append_round_suffix(round))

    def lose_draft_pick(self, season: str, round: int):
        self.draft_picks_lost.append(season + " " +
                                     self._append_round_suffix(round))

    def add_faab(self, faab: int):
        self.faab_added = faab

    def lose_faab(self, faab: int):
        self.faab_lost = faab

    # Only used for debugging
    def __str__(self):
        return_string = ""
        return_string += "Roster " + str(self.roster_id) + "\n"
        return_string += "--Added--\n"
        for add in self.adds:
            return_string += add + "\n"
        for add in self.draft_picks_added:
            return_string += add + "\n"
        if self.faab_added > 0:
            return_string += "$" + str(self.faab_added) + "\n"
        return_string += "--Lost--\n"
        for loss in self.losses:
            return_string += loss + "\n"
        for loss in self.draft_picks_lost:
            return_string += loss + "\n"
        if self.faab_lost > 0:
            return_string += "$" + str(self.faab_lost) + "\n"
        return_string += "\n"
        return return_string


class Trade:
    def __init__(self, timestamp_in_millis: int, involved_rosters: List[int],
                 adds: Dict[str, int], drops: Dict[str, int],
                 draft_picks: List[Dict[str, str]], faab: List[Dict[str,
                                                                    int]]):
        self.trade_time = datetime.fromtimestamp(timestamp_in_millis / 1000)
        self.roster_id_to_detail = {}

        # Create a roster entry for each involved team
        for roster_id in involved_rosters:
            self.roster_id_to_detail[roster_id] = TeamTradeDetails(roster_id)

        # Process the trade components
        self._process_adds(adds)
        self._process_drops(drops)
        self._process_draft_picks(draft_picks)
        self._process_faab(faab)

    # Record every add in the trade onto the appropriate roster
    def _process_adds(self, adds: Dict[str, int]):
        if adds is not None:
            for player_id, roster_id in adds.items():
                self.roster_id_to_detail[roster_id].add_player(player_id)

    # Record every drop in the trade onto the appropriate roster
    def _process_drops(self, drops: Dict[str, int]):
        if drops is not None:
            for player_id, roster_id in drops.items():
                self.roster_id_to_detail[roster_id].lose_player(player_id)

    # Record every draft pick in the trade onto the appropriate roster
    def _process_draft_picks(self, draft_picks: List[Dict[str, str]]):
        for pick in draft_picks:
            # Owner id is the person who received the draft pick
            self.roster_id_to_detail[pick["owner_id"]].add_draft_pick(
                pick["season"], pick["round"])

            # Previous owner is who is trading it away
            self.roster_id_to_detail[
                pick["previous_owner_id"]].lose_draft_pick(
                    pick["season"], pick["round"])

    def _process_faab(self, faab: List[Dict[str, int]]):
        for line_item in faab:
            self.roster_id_to_detail[line_item["sender"]].lose_faab(
                line_item["amount"])
            self.roster_id_to_detail[line_item["receiver"]].add_faab(
                line_item["amount"])

    def __lt__(self, other):
        return self.trade_time < other.trade_time

    # Only used for debugging
    def __str__(self):
        return_string = ""
        for key, team_trade_detail in self.roster_id_to_detail.items():
            return_string += str(team_trade_detail)
        return return_string


def fetch_all_league_trades(league: League) -> List[Trade]:
    all_trades = []

    # Iterate through every week of the season (and then a couple more just to be sure)
    for i in range(1, 20):
        weekly_transactions = league.get_transactions(i)

        for transaction in weekly_transactions:
            if transaction.get("type") == "trade":
                all_trades.append(
                    Trade(transaction.get("status_updated"),
                          transaction.get("consenter_ids"),
                          transaction.get("adds"), transaction.get("drops"),
                          transaction.get("draft_picks"),
                          transaction.get("waiver_budget")))

    return all_trades


def filter_and_sort_trades_by_date(trades: List[Trade], start: datetime,
                                   end: datetime) -> List[Trade]:
    filtered_trades = list(
        filter(
            lambda trade: trade.trade_time < end and trade.trade_time > start,
            trades))
    filtered_trades.sort()
    return filtered_trades


# Format all of the league's trades using Discord markdown formatting
def print_league_trades(league: League, trades: List[Trade],
                        roster_id_map: Dict[int, str],
                        player_map: Dict[str, Dict[str, str]]):
    print("__**" + league.get_league().get("name") + "**__\n")

    for trade in trades:
        league_id = league.get_league().get("league_id")

        # Switch based on the trade size. Two team trades have a better visualization but
        # it's hard to do that for trades with more than 2.
        if len(trade.roster_id_to_detail) == 2:
            print_two_team_trade(league_id, trade, roster_id_map, player_map)
        else:
            print_larger_trade(league_id, trade, roster_id_map, player_map)


def print_two_team_trade(league_id: str, trade: Trade,
                         roster_id_map: Dict[int, str],
                         player_map: Dict[str, Dict[str, str]]):

    # Define the template variables
    manager_template = "**Team {number}: {manager}** - {roster_link}"
    date_template = "%m-%d-%Y"

    # Extract the information from the trade
    trade_rosters = list(trade.roster_id_to_detail.keys())
    trade_detail = list(trade.roster_id_to_detail.values())[0]

    team_a_adds = []
    team_b_adds = []

    for player_id in trade_detail.adds:
        team_a_adds.append(format_player_string(player_id, player_map))
    for pick in trade_detail.draft_picks_added:
        team_a_adds.append(pick)
    if trade_detail.faab_added > 0:
        team_a_adds.append(format_faab(trade_detail.faab_added))

    for player_id in trade_detail.losses:
        team_b_adds.append(format_player_string(player_id, player_map))
    for pick in trade_detail.draft_picks_lost:
        team_b_adds.append(pick)
    if trade_detail.faab_lost > 0:
        team_b_adds.append(format_faab(trade_detail.faab_lost))

    # Output the trade itself
    print("Trade on " + trade.trade_time.strftime(date_template))
    print(
        manager_template.format(number="A",
                                manager=roster_id_map[trade_rosters[0]],
                                roster_link=create_roster_link(
                                    league_id, trade_rosters[0])))
    print(
        manager_template.format(number="B",
                                manager=roster_id_map[trade_rosters[1]],
                                roster_link=create_roster_link(
                                    league_id, trade_rosters[1])))

    # Preferred format, but looks bad on mobile
    print_side_by_side_table(team_a_adds, team_b_adds)

    # Formats well on desktop and mobile
    # print_two_separate_tables(team_a_adds, team_b_adds)


def print_side_by_side_table(team_a_adds: List[str], team_b_adds: List[str]):
    # Define the templates
    header_template = "|{team_a:^{column_width}}|{team_b:^{column_width}}|"
    row_template = "|{player_a:^{column_width}}|{player_b:^{column_width}}|"

    # Print the table
    print("```")
    print("=" * (OUTPUT_COLUMN_WIDTH * 2 + 3))
    print(
        header_template.format(team_a="Team A Gained",
                               team_b="Team B Gained",
                               column_width=OUTPUT_COLUMN_WIDTH))
    print("|" + "=" * (OUTPUT_COLUMN_WIDTH * 2 + 1) + "|")

    for i in range(0, max(len(team_a_adds), len(team_b_adds))):
        player_a = ''
        player_b = ''
        if i < len(team_a_adds):
            player_a = team_a_adds[i]
        if i < len(team_b_adds):
            player_b = team_b_adds[i]
        print(
            row_template.format(player_a=player_a,
                                player_b=player_b,
                                column_width=OUTPUT_COLUMN_WIDTH))

    print("=" * (OUTPUT_COLUMN_WIDTH * 2 + 3))
    print("```\n")


def print_two_separate_tables(team_a_adds: List[str], team_b_adds: List[str]):
    print("```")
    print_single_team_adds("Team A Gained", team_a_adds)
    print_single_team_adds("Team B Gained", team_b_adds)
    print("```\n")


def print_single_team_adds(header_text: str, players: List[str]):

    # Define the templates
    template = "|{text:^{column_width}}|"

    # Print the table
    print("=" * (OUTPUT_COLUMN_WIDTH + 2))
    print(template.format(text=header_text, column_width=OUTPUT_COLUMN_WIDTH))
    print("|" + "=" * OUTPUT_COLUMN_WIDTH + "|")

    for i in range(0, len(players)):
        print(
            template.format(text=players[i], column_width=OUTPUT_COLUMN_WIDTH))

    print("=" * (OUTPUT_COLUMN_WIDTH + 2))


def print_larger_trade(league_id: str, trade: Trade, roster_id_map: Dict[int,
                                                                         str],
                       player_map: Dict[str, Dict[str, str]]):
    print("\n\nTrade on " + trade.trade_time.strftime("%m-%d-%Y"))
    for roster_id, trade_detail in trade.roster_id_to_detail.items():
        print("**Team Manager: " + roster_id_map[roster_id] + "**")
        print("Roster link: " + create_roster_link(league_id, roster_id))
        print("*Traded For*")
        for player_id in trade_detail.adds:
            print("    " + format_player_string(player_id, player_map))
        for pick in trade_detail.draft_picks_added:
            print("    " + pick)
        if trade_detail.faab_added > 0:
            print("    " + format_faab(trade_detail.faab_added))
        print("*Traded Away*")
        for player_id in trade_detail.losses:
            print("    " + format_player_string(player_id, player_map))
        for pick in trade_detail.draft_picks_lost:
            print("    " + pick)
        if trade_detail.faab_lost > 0:
            print("    " + format_faab(trade_detail.faab_lost))
        print("")


def create_roster_link(league_id: str, roster_id: int) -> str:
    template = "https://sleeper.app/roster/{league_id}/{roster_id}"
    return template.format(league_id=league_id, roster_id=str(roster_id))


def format_player_string(player_id: str, player_map) -> str:
    player = player_map[player_id]
    template = "{first} {last} ({position})"
    return template.format(first=player["first_name"],
                           last=player["last_name"],
                           position=player["position"])


def format_faab(faab: int) -> str:
    template = "${number} FAAB"
    return template.format(number=faab)


def parse_user_provided_flags() -> argparse.Namespace:
    arg_parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter)
    arg_parser.add_argument(
        "-y",
        "--year",
        help="The year to run the analysis on, defaults to 2022",
        type=int,
        default=2022)
    arg_parser.add_argument(
        "-r",
        "--league_regex",
        help="Regular expression used to select which leagues to analyze",
        type=str,
        default=".*")
    arg_parser.add_argument("-s",
                            "--start",
                            help="First date for trade analysis",
                            type=str,
                            default="12-31-1999")
    arg_parser.add_argument("-e",
                            "--end",
                            help="Last date for trade analysis",
                            type=str,
                            default="12-31-2099")
    arg_parser.add_argument(
        "username",
        help="User account used to pull all of the leagues",
        type=str)

    return arg_parser.parse_args()


def main(argv):
    args = parse_user_provided_flags()
    user = args.username
    year = args.year
    league_regex = re.compile(args.league_regex)
    start_date = parser.parse(args.start)
    end_date = parser.parse(args.end)

    # Retrieve all of the leagues
    admin_user = User(user)
    all_leagues = admin_user.get_all_leagues("nfl", year)
    user_store = UserStore()

    # Get all players
    nfl_players = Players()
    player_id_to_player = nfl_players.get_all_players()

    # Iterate through each league to find the inactive owners in each
    for league_object in all_leagues:
        league = League(league_object.get("league_id"))
        league_name = league.get_league().get("name")

        if is_league_inactive(league):
            continue

        # Only look at leagues that match the provided regex
        if league_regex.match(league_name):
            league_trades = fetch_all_league_trades(league)
            filtered_league_trades = filter_and_sort_trades_by_date(
                league_trades, start_date, end_date)

            if filtered_league_trades:
                # Retrieve information used during display and then print the results
                user_store.store_users_for_league(league)
                roster_id_to_username = create_roster_id_to_username_dict(
                    league, user_store)

                print_league_trades(league, filtered_league_trades,
                                    roster_id_to_username, player_id_to_player)


if __name__ == "__main__":
    main(sys.argv[1:])
