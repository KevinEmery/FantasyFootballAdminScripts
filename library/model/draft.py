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

from enum import Enum
from typing import Dict

class DraftType(Enum):
    SNAKE = 1
    LINEAR = 2
    AUCTION = 3


class Draft(object):
    def __init__(self, year: str, draft_id: str, draft_type: DraftType,
                 reversal_round: int, league_size: int,
                 team_id_to_draft_slot: Dict[str, int]):
        self.year = year
        self.draft_id = draft_id
        self.draft_type = draft_type
        self.reversal_round = reversal_round
        self.league_size = league_size
        self.team_id_to_draft_slot = team_id_to_draft_slot

    def get_pick_num_within_round(self, pick_owner_id: str,
                                  draft_round: int) -> int:
        draft_slot = self.team_id_to_draft_slot[pick_owner_id]

        # If the draft is linear, assume no reversal
        if self.draft_type == DraftType.LINEAR:
            return draft_slot
        elif self.draft_type == DraftType.SNAKE:
            if draft_round % 2 == 0:
                proposed_slot = self.league_size - draft_slot + 1
            else:
                proposed_slot = draft_slot

            if draft_round >= self.reversal_round and self.reversal_round is not 0:
                proposed_slot = self.league_size - proposed_slot + 1

            return proposed_slot
        else:
            print("Unsupported draft type")
            exit(-1)
