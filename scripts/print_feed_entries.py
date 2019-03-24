import feedparser, requests

url = 'https://feeds.feedburner.com/blogspot/gJZg'

content = requests.get(url).content
entries = feedparser.parse(content)['entries']

for index, entry in enumerate(entries):
    title, link = entry['title'], entry['link']
    print(f'#{index+1}: {title}\n{link}\n')
