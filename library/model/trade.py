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

from datetime import datetime
from typing import List

from .tradedetail import TradeDetail


class Trade(object):
    def __init__(self, trade_time: datetime, details: List[TradeDetail]):
        self.trade_time = trade_time
        self.details = details

    def __lt__(self, other):
        return self.trade_time < other.trade_time