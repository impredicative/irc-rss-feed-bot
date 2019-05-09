import feedparser, requests

from ircrssfeedbot import config

# Customize:
URL = 'https://www.reddit.com/r/AGI/hot/.rss'

content = requests.get(URL, timeout=config.REQUEST_TIMEOUT, headers={'User-Agent': config.USER_AGENT}).content
entries = feedparser.parse(content)['entries']

for index, entry in enumerate(entries):
    title, link = entry['title'], entry['link']
    post = f'#{index+1}: {title}\n{link}\n'
    if hasattr(entry, 'tags') and entry.tags:
        categories = ', '.join(t['term'] for t in entry.tags)
        post += f'{categories}\n'
    print(post)
