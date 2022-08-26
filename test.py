from library.model.league import League
from library.platforms.platform import Platform
from library.platforms.sleeper.sleeper import Sleeper

league = League("test_id", "test_name")
platform: Platform = Sleeper()

print(platform.get_all_trades(league))