import feedparser
import requests

from ircrssfeedbot import config
from ircrssfeedbot.util.urllib import url_to_netloc

# Customize:
URL = 'https://www.reddit.com/r/AGI/hot/.rss'

user_agent = config.USER_AGENT_OVERRIDES.get(url_to_netloc(URL), config.USER_AGENT_DEFAULT)
content = requests.Session().get(URL, timeout=config.REQUEST_TIMEOUT, headers={'User-Agent': user_agent}).content
entries = feedparser.parse(content.lstrip())['entries']

for index, entry in enumerate(entries):
    title, link = entry['title'], entry['link']
    post = f'#{index+1}: {title}\n{link}\n'
    if hasattr(entry, 'tags') and entry.tags:
        categories = ', '.join(t['term'] for t in entry.tags)
        post += f'{categories}\n'
    print(post)
