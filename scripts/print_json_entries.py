"""Print entries from a JSON document parsed using jmespath."""
import html
import json

import jmespath
import requests

from ircrssfeedbot import config
from ircrssfeedbot.feed import ensure_list
from ircrssfeedbot.util.urllib import url_to_netloc

# pylint: disable=invalid-name

# Customize:
URL = "https://www.reddit.com/r/Nootropics/hot/.json?limit=98"
JMES = 'data.children[*].data | [?(not_null(link_flair_text) && score > `5`)].{title: join(``, [`[`, link_flair_text, `] `, title]), link: join(``, [`https://redd.it/`, id]), category: link_flair_text} | [?category == `Scientific Study` || category ==`News Article`]'

user_agent = config.USER_AGENT_OVERRIDES.get(url_to_netloc(URL), config.USER_AGENT_DEFAULT)
content = requests.Session().get(URL, timeout=config.REQUEST_TIMEOUT, headers={"User-Agent": user_agent}).content
data = json.loads(content)
entries = jmespath.search(JMES, data)

for index, entry in enumerate(entries):
    title, link = entry["title"].strip(), entry["link"].strip()
    post = f"#{index+1}: {title}\n{link}\n"
    categories = ", ".join(html.unescape(c.strip()) for c in ensure_list(entry.get("category", [])))
    if categories:
        post += f"{categories}\n"
    print(post)
