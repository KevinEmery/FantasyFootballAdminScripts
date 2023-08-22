# FantasyFootballAdminScripts
Repository containing several Python scripts designed to parse and display information from a user's fantasy football leagues.

These scripts are designed with the idea that there is a single user account in all of the leagues you want to analyze. That account doesn't need to be an owner of a team, and in fact most of my personal applications today are running it on users who don't have a team but instead are just in the leagues to help oversee them. The scripts as currently written are not designed accept a league ID or set of league IDs for manual analysis, instead pulling them from the provided uer account.

The primary use case is for people administering multiple leagues who want to pull information about all of the teams, but it can also be a useful analysis tool for your own leagues.

As a secondary item to the scripts, `discord_bot.py` also contains the source code for a basic Discord bot that I use to leverage several of the scripts in a few sets of leagues that I organize.

## Supported Platforms

Currently these scripts support API calls to either Sleeper or Fleaflicker. Adding additional platforms only requires adding the platform implementation to `/library/platforms` and adding the new platform into the argument parser logic within each top-level script

## Scripts

### inactives.py

#### Description

This script looks through the starting lineups for each team in the league to find every team that is currently starting a player who could be considered inactive. This can be used both before the week to see who might need a little prodding and after a week is complete to see what teams in the league didn't fully set their rosters.

One limitation of this is that the player status is pulled in real time - the platform APIs don't allow for pulling the historical status of a player, so you can't run the script in Week 5 to see who started inactive players in Week 2.

#### Usage

```
usage: inactives.py [-h] [-y YEAR] [-r LEAGUE_REGEX]
                    [--include_transactions | --exclude_transactions]
                    [--sleeper | --fleaflicker]
                    [--players_to_ignore PLAYERS_TO_IGNORE [PLAYERS_TO_IGNORE ...]]
                    identifier week

positional arguments:
  identifier            User account used to pull all of the leagues
  week                  The week to run analysis on

optional arguments:
  -h, --help            show this help message and exit
  -y YEAR, --year YEAR  The year to run the analysis on, defaults to 2023
  -r LEAGUE_REGEX, --league_regex LEAGUE_REGEX
                        Regular expression used to select which leagues to
                        analyze
  --include_transactions
                        Include last transaction data in the report (default)
  --exclude_transactions
  --sleeper             Run analysis on Sleeper leagues (default)
  --fleaflicker         Run analysis on Fleaflicker leagues
  --players_to_ignore PLAYERS_TO_IGNORE [PLAYERS_TO_IGNORE ...]
                        List of player names to ignore
```

### leaguescoring.py

#### Description

This script is used to find various summary statistics around how teams are performing, both within an individual week as well as on the season as a whole, across all of the leagues. It will currently report the top N teams with the highest and lowest individual week scores, as well as the best/worst performing teams on the season. Notably this doesn't take into account a team's record, but instead only surfaces their total points.

#### Usage

```
usage: leaguescoring.py [-h] [-wc WEEKLY_COUNT] [-sc SEASON_COUNT] [-y YEAR]
                        [-r LEAGUE_REGEX] [--max | --no-max]
                        [--min | --no-min] [--season | --no-season]
                        [--weekly | --no-weekly]
                        [--current-week | --no-current-week]
                        [--sleeper | --fleaflicker]
                        identifier [start] end

positional arguments:
  identifier            User identifier used to pull all of the leagues
  start                 the starting week for data collection (default: 1)
  end                   the ending week for data collection

optional arguments:
  -h, --help            show this help message and exit
  -wc WEEKLY_COUNT, --weekly_count WEEKLY_COUNT
                        number of weekly data points to display (default: 5)
  -sc SEASON_COUNT, --season_count SEASON_COUNT
                        number of season data points to display (default: 5)
  -y YEAR, --year YEAR  The year to run the analysis on, defaults to 2023
  -r LEAGUE_REGEX, --league_regex LEAGUE_REGEX
                        Regular expression used to select which leagues to
                        analyze
  --max                 Include the 'max' statistics (default)
  --no-max
  --min                 Include the 'min' statistics (default)
  --no-min
  --season              Include the 'season' statistics (default)
  --no-season
  --weekly              Include the 'weekly' statistics (default)
  --no-weekly
  --current-week        Include the 'current week' statistics (default)
  --no-current-week
  --sleeper             Run analysis on Sleeper leagues (default)
  --fleaflicker         Run analysis on Fleaflicker leagues
```

### topleaguescore.py

#### Description

This script is used to find the top weekly score for a team in each league. Unlike `leaguescoring.py`, this is not a league used for comparison between leagues but instead solely looks for the top single-week scoring within the league

#### Usage

```
usage: topleaguescore.py [-h] [-y YEAR] [-r LEAGUE_REGEX]
                         [--sleeper | --fleaflicker]
                         identifier [start] end

positional arguments:
  identifier            User identifier used to pull all of the leagues
  start                 the starting week for data collection (default: 1)
  end                   the ending week for data collection

optional arguments:
  -h, --help            show this help message and exit
  -y YEAR, --year YEAR  The year to run the analysis on, defaults to 2023
  -r LEAGUE_REGEX, --league_regex LEAGUE_REGEX
                        Regular expression used to select which leagues to
                        analyze
  --sleeper             Run analysis on Sleeper leagues (default)
  --fleaflicker         Run analysis on Fleaflicker leagues
```

### adp.py

#### Description

This script is used to find the average draft position (ADP) of players in all leagues for a specific user in a specific year. That list can be filtered by a variety of different factors (league name, position, and/or team) to generate customized reports. Most useful when looking across a number of leagues but also if you just want quick reference for all players from a given position/team for a single league.

#### Usage

```
usage: adp.py [-h] [-y YEAR] [-r LEAGUE_REGEX] [-p POSITION] [-t TEAM]
              [-n MAX_RESULTS] [-c MINIMUM_TIMES_DRAFTED] [-s LEAGUE_SIZE]
              [--human_readable | --csv] [--sleeper | --fleaflicker]
              identifier

positional arguments:
  identifier            User account used to pull all of the leagues

optional arguments:
  -h, --help            show this help message and exit
  -y YEAR, --year YEAR  The year to run the analysis on, defaults to 2023
  -r LEAGUE_REGEX, --league_regex LEAGUE_REGEX
                        Regular expression used to select which leagues to
                        analyze
  -p POSITION, --position POSITION
                        Which NFL position to print data about (default: all)
  -t TEAM, --team TEAM  Which NFL team to print data about (default: all)
  -n MAX_RESULTS, --max_results MAX_RESULTS
                        Maximum number of players to display (default: all)
  -c MINIMUM_TIMES_DRAFTED, --minimum_times_drafted MINIMUM_TIMES_DRAFTED
                        Minimum number of times a player needs to be drafted
                        (default: 1)
  -s LEAGUE_SIZE, --league_size LEAGUE_SIZE
                        Number of teams in the league
  --human_readable
  --csv
  --sleeper             Run analysis on Sleeper leagues (default)
  --fleaflicker         Run analysis on Fleaflicker leagues
  ```

### lasttransaction.py

#### Description

This script is used to find the last transaction date for each manager across all of the leagues a specific user is in. This is meant as another tool in a toolbox designed to see if managers in a league are remaining active.

#### Usage

```
usage: lasttransaction.py [-h] [-y YEAR] [-r LEAGUE_REGEX]
                          [--sleeper | --fleaflicker]
                          identifier

positional arguments:
  identifier            User identifier used to pull all of the leagues

optional arguments:
  -h, --help            show this help message and exit
  -y YEAR, --year YEAR  The year to run the analysis on, defaults to 2023
  -r LEAGUE_REGEX, --league_regex LEAGUE_REGEX
                        Regular expression used to select which leagues to
                        analyze
  --sleeper             Run analysis on Sleeper leagues (default)
  --fleaflicker         Run analysis on Fleaflicker leagues
```

### trades.py

#### Description

This script is used to print out all of the trades that have occurred in the leagues for a specific user. Unlike most of the other scripts here this isn't intended to be used for specific pieces of analysis, but rather just an easy way to extract all trades so they can be shared more widely.

The output of this is pre-formatted with Discord markdown for ease of use.

#### Usage

```
usage: trades.py [-h] [-y YEAR] [-r LEAGUE_REGEX] [-s START] [-e END]
                 [--sleeper | --fleaflicker]
                 identifier

positional arguments:
  identifier            User account used to pull all of the leagues

optional arguments:
  -h, --help            show this help message and exit
  -y YEAR, --year YEAR  The year to run the analysis on, defaults to 2023
  -r LEAGUE_REGEX, --league_regex LEAGUE_REGEX
                        Regular expression used to select which leagues to
                        analyze
  -s START, --start START
                        First date for trade analysis
  -e END, --end END     Last date for trade analysis
  --sleeper             Run analysis on Sleeper leagues (default)
  --fleaflicker         Run analysis on Fleaflicker leagues
```

## Required Python Libraries

In order to run this scripts, in addition to the base packages that come with Python, the following libraries are required.

 - [requests](https://pypi.org/project/requests/), which is used for all HTTP request handling
 - [python-dateutil](https://pypi.org/project/python-dateutil/), which is used to parse user input into a manageable `datetime` object

 Separately, if you're looking to run the bot contained in `discord_bot.py`, you will need the following library

 - [discord.py](https://discordpy.readthedocs.io/en/stable/), used to handle the registration and interactions with Discord

## License

This project is licensed under the terms of the Apache License 2.0