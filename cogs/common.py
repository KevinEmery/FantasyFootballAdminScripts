"""
   Copyright 2025 Kevin Emery

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

LOG_DIRECTORY_NAME = "./logs/"
LOG_PREFIX = "log_"

def print_descriptive_log(log_method: str, log_line: str = "", write_to_file: bool = True):
    log_template = "{time:<20}{log_method:40.40}\t{log_line}"
    formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_date = datetime.now().strftime("%Y_%m_%d")

    log_file_path = LOG_DIRECTORY_NAME + LOG_PREFIX + formatted_date
    formatted_log = log_template.format(time=formatted_time,
                                        log_method=log_method,
                                        log_line=log_line)

    print(formatted_log)

    if write_to_file:
        try:
            with open(log_file_path, 'a+') as f:
                f.write(formatted_log + "\n")
        except Exception as e:
            # This is non-critical infra, just log to console and move on.
            print("Error writing log to file")
            print(e)
    