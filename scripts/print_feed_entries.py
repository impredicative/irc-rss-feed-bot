import feedparser, requests

url = 'https://libraries.io/pypi/pandas/versions.atom'

content = requests.get(url).content
entries = feedparser.parse(content)['entries']

for entry in entries:
    title, link = entry['title'], entry['link']
    print(f'{title}\n{link}\n')
