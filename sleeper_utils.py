def is_league_inactive(rosters) -> bool:
    """Determines if a league is inactive based on the rosters

    This is used as a mildly hacky helper method. It looks through the
    rosters of every time, and if there are any players on any of them
    it classifies the league as active. However if all the player
    lists are empty, it says the league is inactive and returns True
    """
    for roster in rosters:
        if roster.get("players"):
            return False

    return True