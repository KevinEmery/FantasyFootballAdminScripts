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
from datetime import datetime


# ID of my personal dev server
DEV_SERVER_GUILD_ID = 1134308260812423168

def print_descriptive_log(log_method: str, log_line: str = ""):
    log_template = "{time:<20}{log_method:40.40}\t{log_line}"
    formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(
        log_template.format(time=formatted_time,
                            log_method=log_method,
                            log_line=log_line))