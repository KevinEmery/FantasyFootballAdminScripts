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
"""Script used to find the last transaction date for every user in a set of leagues

This script will iterate over all of the leagues that the provided user is in,
retrieving and report the last transaction date for every person in each league
"""

import argparse
import re
import sys
from datetime import datetime
from typing import Dict, List

from sleeper_wrapper import League, User

from sleeper_utils import is_league_inactive, create_roster_id_to_username_dict
from user_store import UserStore

DEC_31_1999_MILLIS = 946684800000


class LeagueTransaction:
    """Data class to hold the relevant information about a transaction

    Attributes
    ----------
    timestamp_in_millis : int
        Timestamp in milliseconds that the transaction occurred
    transaction_type: str
        The string representation of what kind of transaction it was (waiver, free agent, trade)
    involved_rosters: [int]
        List of roster ids involved in the transaction. Not guaranteed to be non-empty
    """
    def __init__(self, timestamp_in_millis: int, transaction_type: str,
                 involved_rosters: [int]):
        self.timestamp = timestamp_in_millis / 1000
        self.transaction_type = transaction_type
        self.involved_rosters = involved_rosters

    def __str__(self):
        template = "{transaction_type}, {date} - {involved_rosters}"
        readable_date = datetime.fromtimestamp(self.timestamp)
        return template.format(transaction_type=self.transaction_type,
                               date=readable_date,
                               involved_rosters=self.involved_rosters)

    def __lt__(self, other):
        return self.timestamp < other.timestamp


def fetch_all_league_transactions(league: League,
                                  week: int) -> List[LeagueTransaction]:
    """Retrieves all of the league's transactions, distilling them into our custom data class

    This is meant to be a fairly thin method that extracts the information we
    need to do our analysis from the larger transaction object that's 
    returned through Sleeper's API

    Parameters
    ----------
    league : League
        The League object being analyzed
    week : int
        The final week to pull transactions from

    Returns
    -------
    List[LeagueTransaction]
        A list of the transactions in the league
    """
    all_transactions = []

    # All preseason transactions count as Week 1, so this grabs from Week 1 through week
    for i in range(1, week + 1):
        weekly_transactions = league.get_transactions(i)

        for transaction in weekly_transactions:
            all_transactions.append(
                LeagueTransaction(transaction.get("status_updated"),
                                  transaction.get("type"),
                                  transaction.get("consenter_ids")))

    return all_transactions


def determine_most_recent_transaction_for_each_roster(
        league: League,
        transactions: List[LeagueTransaction]) -> Dict[int, LeagueTransaction]:
    """Finds each roster's most recent transaction

    Given a list of transactions sorted from most recent to oldest, this method returns
    each roster's most recent transaction so that it can be returned out to the caller.

    This assumes roster ids go from 1 to N where N is the number of teams in the league

    Parameters
    ----------
    league : League
        The League object being analyzed
    transactions: List[LeagueTransaction]
        Sorted list of transactions with the most recent transaction first.

    Returns
    -------
    Dict[int, LeagueTransaction]
        Map of roster id to that roster's most recent transaction
    """
    most_recent_transaction_per_roster = {}
    league_size = league.get_league().get("total_rosters")

    for transaction in transactions:
        # This can happen if the commish has forced a transaction
        if transaction.involved_rosters is None:
            continue

        # Each transaction can have one or more rosters involved (like a trade), so
        # we may need to track this transaction for multiple rosters
        for roster in transaction.involved_rosters:

            # Only track the transaction if we haven't already stored one for this roster
            if roster not in most_recent_transaction_per_roster.keys():
                most_recent_transaction_per_roster[roster] = transaction

        # If we get here then every roster has a transaction and we can abort early
        if len(most_recent_transaction_per_roster) >= league_size:
            break

    # If a team hasn't made any transactions then they won't be in the map. For clarity,
    # this adds a dummy transaction into the list for the roster signifying the lack of transaction
    for i in range(1, league_size + 1):
        if i not in most_recent_transaction_per_roster.keys():
            most_recent_transaction_per_roster[i] = LeagueTransaction(
                DEC_31_1999_MILLIS, "None", [i])

    return most_recent_transaction_per_roster


def get_most_recent_transaction_per_roster(
        league: League, week: int) -> Dict[int, LeagueTransaction]:
    league_transactions = fetch_all_league_transactions(league, week)
    league_transactions.sort(reverse=True)
    most_recent_transaction_per_roster = determine_most_recent_transaction_for_each_roster(
        league, league_transactions)

    return most_recent_transaction_per_roster


def print_recent_transaction_data(league_name: str,
                                  transactions: Dict[int, LeagueTransaction],
                                  roster_id_map: Dict[int, str]):

    print(league_name)
    for roster_id in transactions.keys():
        print(
            format_most_recent_transaction(roster_id_map[roster_id],
                                           transactions[roster_id]))
    print("")


def format_most_recent_transaction(username: str,
                                   transaction: LeagueTransaction) -> str:
    template = "{username:<20}type: {type:<15}date: {formatted_date}"
    formatted_date = datetime.fromtimestamp(
        transaction.timestamp).strftime("%m-%d-%Y")

    return template.format(username=username,
                           type=transaction.transaction_type,
                           formatted_date=formatted_date)


def parse_user_provided_flags() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "-y",
        "--year",
        help="The year to run the analysis on, defaults to 2022",
        type=int,
        default=2022)
    parser.add_argument(
        "-r",
        "--league_regex",
        help="Regular expression used to select which leagues to analyze",
        type=str,
        default=".*")
    parser.add_argument("username",
                        help="User account used to pull all of the leagues",
                        type=str)
    parser.add_argument("week",
                        help="The last week to look at transactions",
                        type=int)

    return parser.parse_args()


def main(argv):
    args = parse_user_provided_flags()
    user = args.username
    year = args.year
    league_regex = re.compile(args.league_regex)
    week = args.week

    # Retrieve all of the leagues
    admin_user = User(user)
    all_leagues = admin_user.get_all_leagues("nfl", year)
    user_store = UserStore()

    # Iterate through each league to find the inactive owners in each
    for league_object in all_leagues:
        league = League(league_object.get("league_id"))
        league_name = league.get_league().get("name")
        league_transactions = []

        if is_league_inactive(league):
            continue

        # Only look at leagues that match the provided regex
        if league_regex.match(league_name):
            user_store.store_users_for_league(league)

            # Retrieve the last transaction data, username information, and print the results
            most_recent_transaction_per_roster = get_most_recent_transaction_per_roster(
                league, week)
            roster_id_to_username = create_roster_id_to_username_dict(
                league, user_store)
            print_recent_transaction_data(league_name,
                                          most_recent_transaction_per_roster,
                                          roster_id_to_username)


if __name__ == "__main__":
    main(sys.argv[1:])
