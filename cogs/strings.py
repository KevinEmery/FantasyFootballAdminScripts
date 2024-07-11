"""
   Copyright 2024 Kevin Emery

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

FTA_ADP_THREAD_CONTENT = "The data here is for the FTA league format. \
These leagues are 14-team, 0.5 PPR Leagues that start \
1 QB, 2 RBs, 3 WRs, 1 TE, 1 W/R/T Flex, 1 K, and 1 DEF.\n\n"

NARFFL_ADP_THREAD_CONTENT = "The data here is for the NarFFL league format. \
These leagues are 12-team, 1.0 PPR Leagues that start \
1 QB, 2 RBs, 2 WRs, 1 TE, 1 W/R/T Flex, 1 K, and 1 DEF.\n\n"

ADP_GLOSSARY = "__**Glossary Terms**__\
```\n\
Av:  The average draft position across all drafts\n\
Min: The earliest a player was drafted\n\
Max: The latest a player was drafted\n\
(#): Number of times a player has been drafted\
```\n\
The designation \"X.Y\" represents a selection in Round X, at Pick Y"

LEADERBOARD_SEASON_SCORE_TEAM_TEMPLATE = "{rank}. **[{team_name}](<{roster_link}>)** (_{league}_)  - **{score}**\n"
LEADERBOARD_WEEKLY_SCORE_TEAM_TEMPLATE = "{rank}. **[{team_name}](<{roster_link}>)** (_{league}_)  - Week {week} - **{score}**\n"
LEADERBOARD_UNORDERED_WEEKLY_SCORE_TEMPLATE = "- **[{team_name}](<{roster_link}>)** (_{league}_)  - Week {week} - **{score}**\n"

FTA_LEADERBARD_MAIN_POST_CONTENT_HEADER = "Here are your top-scoring teams across all leagues, as well as the highest single-week score this year so far.\n\n\
At the end of the regular season, the top-three season-long scorers and the top single-week score for the year are awarded prizes.\n\n"

NARFFL_LEADERBOARD_LEVEL_SPECIFIC_POST_TEMPLATE = "Here are the top-scoring teams looking at the NarFFL {level} leagues"
NARFFL_TOP_FARM_LEAGUE_SCORES_CONTENT = "These are the top single-week scores in each individual Farm League. \
At the end of the year, the team with the highest single-week score during the regular season (excluding the Champion) earns a promotion to Minors. \
This is meant to serve as an unofficial sneak-preview of what that bar will be in each league."
