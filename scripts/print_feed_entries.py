"""Print entries from an RSS or Atom feed parsed using feedparser."""
from typing import List, Set

import feedparser
import requests

from ircrssfeedbot import config
from ircrssfeedbot.util.lxml import sanitize_xml
from ircrssfeedbot.util.urllib import url_to_netloc

# pylint: disable=invalid-name

# Customize:

URL = "https://tools.cdc.gov/api/v2/resources/media/316422.rss"
BLACKLISTED_CATEGORIES: Set[str] = set([])
BLACKLISTED_TITLE_TERMS: List[str] = []

user_agent = config.USER_AGENT_OVERRIDES.get(url_to_netloc(URL), config.USER_AGENT_DEFAULT)
content = requests.Session().get(URL, timeout=config.REQUEST_TIMEOUT, headers={"User-Agent": user_agent}).content
content = sanitize_xml(content)
entries = feedparser.parse(content.lstrip())["entries"]

for index, entry in enumerate(entries):
    title, link = entry["title"], (entry.get("link") or entry["links"][0]["href"])
    if any(term in title for term in BLACKLISTED_TITLE_TERMS):
        continue
    post = f"#{index+1}: {title}\n{link}\n"
    if hasattr(entry, "tags") and entry.tags:
        categories = [t["term"] for t in entry.tags]
        if set(categories) & BLACKLISTED_CATEGORIES:
            continue
        categories_str = ", ".join(categories)
        post += f"{categories_str}\n"
    print(post)
