import html

import hext
import requests

from ircrssfeedbot import config
from ircrssfeedbot.feed import ensure_list
from ircrssfeedbot.util.urllib import url_to_netloc

# Customize:
URL = 'https://ergo-log.com'
HEXT = '<p id="kopindex"><a href:prepend("https://ergo-log.com/"):link @text:title @text=~".+"/></p>'

user_agent = config.USER_AGENT_OVERRIDES.get(url_to_netloc(URL), config.USER_AGENT_DEFAULT)
content = requests.Session().get(URL, timeout=config.REQUEST_TIMEOUT, headers={'User-Agent': user_agent}).content
entries = hext.Rule(HEXT).extract(hext.Html(content.decode()))

for index, entry in enumerate(entries):
    title, link = html.unescape(entry['title'].strip()), entry['link'].strip()
    post = f'#{index+1}: {title}\n{link}\n'
    categories = ', '.join(html.unescape(c.strip()) for c in ensure_list(entry.get('category', [])))
    if categories:
        post += f'{categories}\n'
    print(post)
