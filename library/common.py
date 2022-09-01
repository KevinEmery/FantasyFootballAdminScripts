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

import requests

DEC_31_1999_SECONDS = 946684800
DEFAULT_YEAR = "2022"

TEAMS_ON_BYE = {
    1: [],
    2: [],
    3: [],
    4: [],
    5: [],
    6: ["DET", "LV", "TEN", "HOU"],
    7: ["BUF", "LAR", "MIN", "PHI"],
    8: ["KC", "LAC"],
    9: ["CLE", "DAL", "DEN", "NYG", "PIT", "SF"],
    10: ["BAL", "CIN", "NE", "NYJ"],
    11: ["JAX", "MIA", "SEA", "TB"],
    12: [],
    13: ["ARI", "CAR"],
    14: ["ATL", "CHI", "GB", "IND", "NO", "WAS"],
    15: [],
    16: [],
    17: [],
    18: []
}


def _make_get_request_with_logging(request_url):
    try:
        response = requests.get(request_url)
        return response.json()
    except Exception as e:
        print("Request URL: {url}".format(url=request_url))
        print("Exception: {e}".format(e=e))
        print("Raw Response\n{response}".format(response=str(response)))
