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

import requests
import time

DEC_31_1999_SECONDS = 946684800
DEFAULT_YEAR = 2026

# Byes are currently listed for 2025
TEAMS_ON_BYE = {
    1: [],
    2: [],
    3: [],
    4: [],
    5: ["CAR", "KC"],
    6: ["CIN", "DET", "MIA", "MIN"],
    7: ["BUF", "JAX", "LAC", "WAS"],
    8: ["HOU", "NO", "NYG", "SF"],
    9: ["PIT", "TEN"],
    10: ["CHI", "DEN", "PHI", "TB"],
    11: ["ATL", "CLE", "GB", "LAR", "NE", "SEA"],
    12: [],
    13: ["BAL", "IND", "LV", "NYJ"],
    14: ["ARI", "DAL"],
    15: [],
    16: [],
    17: [],
    18: []
}


def _make_get_request_with_logging(request_url: str, should_retry: bool = True, retry_wait_seconds: int = 15):
    try:
        response = requests.get(request_url)
        if response.json() is None:
            raise Exception("Request to {url} came back with an empty response. Failing".format(url=request_url))
        return response.json()
    except Exception as e:
        print("Request URL: {url}".format(url=request_url))
        print("Exception: {e}".format(e=e))

        # Give another go for the failed request, in hopes that it's transient
        if should_retry:
            print("Retrying failed request")
            time.sleep(retry_wait_seconds)
            return _make_get_request_with_logging(request_url, False, retry_wait_seconds)
