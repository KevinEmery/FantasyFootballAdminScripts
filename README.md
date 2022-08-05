# Scripts-for-Sleeper-FantasyFootball
Repository for a handful of Python scripts designed to parse information from Sleeper fantasy football leagues

As they're written today, these scripts are designed with the idea that there is one single account in all of the leagues you want to analyze. That account doesn't need to be an owner of a team (and in fact most of my personal applications today are running it on users who don't have a team, but instead are just in the leagues to help run them), but they need to be in the league as it's from that user that the full list of leagues to be analyzed is pulled.

The primary use case is for people administering multiple leagues who want to pull information about all of the teams.

## Scripts

### inactives.py

#### Description

This script looks through the starting lineups for each team in the league to find every team that is currently starting a player who could be considered inactive (basically having any status that's not "questionable"). This can be used both before the week to see who might need a little prodding and after a week is complete to see what teams in the league didn't fully set their rosters.

One limitation of this is that the player status is pulled in real time - the Sleeper API doesn't currently allow for pulling the historical status of a player, so you can't run the script in Week 5 to see who started inactive players in Week 2.

#### Usage

```
usage: inactives.py [-h] [-y YEAR] [-r LEAGUE_REGEX]
                    [--include-covid | --exclude-covid]
                    [--include-missing | --exclude-missing]
                    username week

positional arguments:
  username              User account used to pull all of the leagues
  week                  The week to run analysis on

optional arguments:
  -h, --help            show this help message and exit
  -y YEAR, --year YEAR  The year to run the analysis on, defaults to 2022
  -r LEAGUE_REGEX, --league_regex LEAGUE_REGEX
                        Regular expression used to select which leagues to
                        analyze
  --include-covid       Include COVID players in the report (default)
  --exclude-covid
  --include-missing     Include missing players in the report (default)
  --exclude-missing
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
                        username [start] end

positional arguments:
  username              User account used to pull all of the leagues
  start                 the starting week for data collection (default: 1)
  end                   the ending week for data collection

optional arguments:
  -h, --help            show this help message and exit
  -wc WEEKLY_COUNT, --weekly_count WEEKLY_COUNT
                        number of weekly data points to display (default: 5)
  -sc SEASON_COUNT, --season_count SEASON_COUNT
                        number of season data points to display (default: 5)
  -y YEAR, --year YEAR  The year to run the analysis on, defaults to 2022
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
```

### adp.py

#### Description

This script is used to find the average draft position (ADP) of players in all leagues for a specific user in a specific year. That list can be filtered by a variety of different factors (league name, position, and/or team) to generate customized reports. Most useful when looking across a number of leagues but also if you just want quick reference for all players from a given position/team for a single league.

#### Usage

```
usage: adp.py [-h] [-y YEAR] [-r LEAGUE_REGEX] [-p POSITION] [-t TEAM]
              [-n MAX_RESULTS] [-c MINIMUM_TIMES_DRAFTED] [-s LEAGUE_SIZE]
              [--human_readable | --csv]
              username

positional arguments:
  username              User account used to pull all of the leagues

optional arguments:
  -h, --help            show this help message and exit
  -y YEAR, --year YEAR  The year to run the analysis on, defaults to 2022
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
  ```

## Dependencies

[sleeper-api-wrapper](https://github.com/SwapnikKatkoori/sleeper-api-wrapper)

 - Used for all interactions with the Sleeper API

## License

This project is licensed under the terms of the Apache License 2.0