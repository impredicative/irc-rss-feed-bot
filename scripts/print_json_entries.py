import html
import json

import jmespath
import requests

from ircrssfeedbot import config
from ircrssfeedbot.feed import ensure_list
from ircrssfeedbot.util.urllib import url_to_netloc

# Customize:
URL = 'https://www.reddit.com/r/MachineLearning/hot/.json?limit=50'
JMES = 'data.children[*].data | [?score >= `100`].{title: title, link: join(``, [`https://redd.it/`, id])}'

user_agent = config.USER_AGENT_OVERRIDES.get(url_to_netloc(URL), config.USER_AGENT_DEFAULT)
content = requests.Session().get(URL, timeout=config.REQUEST_TIMEOUT, headers={'User-Agent': user_agent}).content
data = json.loads(content)
entries = jmespath.search(JMES, data)

for index, entry in enumerate(entries):
    title, link = entry['title'], entry['link']
    post = f'#{index+1}: {title}\n{link}\n'
    categories = ', '.join(html.unescape(c.strip()) for c in ensure_list(entry.get('category', [])))
    if categories:
        post += f'{categories}\n'
    print(post)
