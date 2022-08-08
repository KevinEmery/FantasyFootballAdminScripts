import argparse
import re
import sys
from datetime import datetime
from typing import Dict, List

from sleeper_wrapper import League, User

from sleeper_utils import is_league_inactive, create_roster_id_to_username_dict
from user_store import UserStore

class LeagueTransaction:
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
    all_transactions = []
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
    most_recent_transaction_per_roster = {}
    league_size = league.get_league().get("total_rosters")

    for transaction in transactions:
        # This can happen if the commish has forced a transaction
        if transaction.involved_rosters is None:
            continue

        for roster in transaction.involved_rosters:
            if roster not in most_recent_transaction_per_roster.keys():
                most_recent_transaction_per_roster[roster] = transaction

        if len(most_recent_transaction_per_roster) >= league_size:
            break

    for i in range(1, league_size + 1):
        if i not in most_recent_transaction_per_roster.keys():
            most_recent_transaction_per_roster[i] = LeagueTransaction(946684800000, "None", [i])

    return most_recent_transaction_per_roster

def get_most_recent_transaction_per_roster(league: League, week: int) -> Dict[int, LeagueTransaction]:
    league_transactions = fetch_all_league_transactions(
                league, week)
    league_transactions.sort(reverse=True)
    most_recent_transaction_per_roster = determine_most_recent_transaction_for_each_roster(
        league, league_transactions)

    return most_recent_transaction_per_roster

def format_most_recent_transaction(username: str, transaction: LeagueTransaction) -> str:
    template = "{username:<20}type: {type:<15}date: {formatted_date}"
    formatted_date = datetime.fromtimestamp(transaction.timestamp).strftime("%m-%d-%Y")

    return template.format(username=username, type=transaction.transaction_type, formatted_date=formatted_date)



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
    parser.add_argument("week", help="The last week to look at transactions", type=int)

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

    inactive_rosters = []

    # Iterate through each league to find the inactive owners in each
    for league_object in all_leagues:
        league = League(league_object.get("league_id"))
        league_name = league.get_league().get("name")
        league_transactions = []

        if is_league_inactive(league):
            continue

        # Only look at leagues that match the provided regex
        if league_regex.match(league_name):
            print(league_name)
            user_store.store_users_for_league(league)

            most_recent_transaction_per_roster = get_most_recent_transaction_per_roster(league, week)
            roster_id_to_username = create_roster_id_to_username_dict(league, user_store)
            for key in most_recent_transaction_per_roster.keys():
                print(format_most_recent_transaction(roster_id_to_username[key], most_recent_transaction_per_roster[key]))
            print("")


if __name__ == "__main__":
    main(sys.argv[1:])
