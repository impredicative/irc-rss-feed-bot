"""Print entries from an HTML page parsed using hext."""

import hext
import requests

from ircrssfeedbot import config
from ircrssfeedbot.util.urllib import url_to_netloc

# pylint: disable=invalid-name

# Customize:
URL = ""
HEXT = """

"""

user_agent = config.USER_AGENT_OVERRIDES.get(url_to_netloc(URL), config.USER_AGENT_DEFAULT)
print(f"User agent is: {user_agent}")
content = requests.Session().get(URL, timeout=config.REQUEST_TIMEOUT, headers={"User-Agent": user_agent}).content
entries = hext.Rule(HEXT).extract(hext.Html(content.decode()), max_searches=100_000)

for index, entry in enumerate(entries):
    post = f"#{index+1}: {entry}\n"
    print(post)
