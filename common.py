import re

from enum import Enum
from typing import List

from library.model.league import League


class PlatformSelection(Enum):
    SLEEPER = 1
    FLEAFLICKER = 2
