# irc-rss-feed-bot
**irc-rss-feed-bot** is a Python 3.7 based IRC RSS and Atom feed posting bot.
It essentially posts the entries of RSS and Atom feeds in IRC channels, one entry per message.
More specifically, it posts the titles and shortened URLs of entries.

## Features
* Multiple channels on an IRC server are supported, with each channel having its own set of feeds.
For multiple servers, use an instance per server.
* Entry URLs are all shortened using [`bitlyshortener`](https://github.com/impredicative/bitlyshortener/).
* A SQLite database file records the entries that have been posted, thereby preventing them from being reposted.
Deduplication of a post can be per-feed or per-channel, with the default being per-feed.
* Entries are posted only if the channel has not had any conversation for at least 15 minutes, thereby preventing the
interruption of any preexisting conversations.
* Poll frequency of each feed is individually customizable.
* For each new feed with no history in the database, only up to three of its most recent entries are posted.
The rest are never posted but are nevertheless saved in the database.
This is done to limit flooding a channel when one or more new feeds are added.
Future entries of the feed are all posted without reservation.

## Links
* Code: https://github.com/impredicative/irc-rss-feed-bot
* Container: https://hub.docker.com/r/ascensive/irc-rss-feed-bot

## Examples
```text
<Feed[bot]> ⧘ArXiv:cs.AI⧙ Concurrent Meta Reinforcement Learning (v1) → https://j.mp/2J6RNda
<Feed[bot]> ⧘ArXiv:cs.AI⧙ Attack Graph Obfuscation (v1) → https://j.mp/2TJ2UNp
<Feed[bot]> ⧘InfoWorld⧙ What is a devops engineer? And how do you become one? → https://j.mp/2NOgQ3g
<Feed[bot]> ⧘InfoWorld⧙ What is Jupyter Notebook? Data analysis made easier → https://j.mp/2NMailP
```

## Usage
### Configuration
* Prepare a private but version-controlled `config.yaml` file using the sample below.
```yaml
host: chat.freenode.net
ssl_port: 6697
nick: Feed[bot]
nick_password: the_correct_password
mode:
tokens:
  bitly:
    - 5e71a58b19582f48edcb0235637ac3536dd3b6dc
    - bd90119a7b617e81b293ddebbbfed3e955eac5af
    - 42f309642a018e6b4d7cfba6854080719dccf0cc
    - 0819552eb8b42e52dbc8b4c3e1654f5cd96c0dcc
    - 430a002fe9d4e8f94097f7a5cd974ffce85eb605
    - 71f9856bc96c6a8eabeac4f763daaec16896e183
    - 81f6d477cfcef006a6dd35c4b947d1c1fdcbf445
    - 06441b445c75d2251f0a56ae87506c69dc468af5
    - 1e71089487fb70f42fff51b7ad49f192ffcb00f2
    - d67d83ab3af6ea840f712bc7a9f48a89393a66c3
feeds:
  "#some_chan1":
    j:AJCN:
      url: https://academic.oup.com/rss/site_6122/3981.xml
      freq: 24
    MedicalXpress:nutrition:
      url: https://medicalxpress.com/rss-feed/search/?search=nutrition
  "##some_chan2":
    ArXiv:cs.AI:
      url: https://export.arxiv.org/rss/cs.AI
      dedup: channel
    InfoWorld:
      url: https://www.infoworld.com/index.rss
```

Global settings:
* `mode`: This is optional and can for example be `+igR` for [Freenode](https://freenode.net/kb/answer/usermodes).
Setting it is recommended.
* `tokens/bitly`: Bitly tokens are required for shortening URLs. They are mandatory.
The sample tokens are for illustration only and are invalid.
To obtain tokens, refer to these [instructions](https://github.com/impredicative/bitlyshortener#usage).
Providing multiple tokens, perhaps as many as 10 to 20 free ones or a single commercial one, is required.
Failing this, Bitly imposed rate limits for shortening URLs will lead to errors.
If there are errors, the batched new posts in a feed may get reprocessed the next time the feed is read.

Feed-specific settings:
* `dedup` indicates how to deduplicate posts for the feed, thereby preventing them from being reposted.
The default value is `feed`, and an alternate possible value is `channel`.
Per-feed deduplication is nevertheless implicitly specific to its channel.
* `freq` indicates how frequently to poll the feed in hours. Its default value is 1.
Conservative polling is recommended.

A `posts.v1.db` database file is written by the bot in the same directory as `config.yaml`.
This database file must be preserved but not version controlled.

### Deployment
* Some but not all warning and error alerts are sent to `##{nick}-alerts`.
For example, if the nick is `Feed[bot]`, these alerts will be sent to `##Feed[bot]-alerts`.
It is recommended that the alerts channel be registered and monitored.

* It is required that the bot be auto-voiced (+V) in each channel.
Failing this, rapid-fire messages from the bot can easily be silently dropped by the server.

* It is recommended that the bot be run as a Docker container using using Docker ≥18.09.3, possibly with
Docker Compose ≥1.24.0-rc1, etc.
To run the bot using Docker Compose, create or add to a version-controlled `docker-compose.yml` file:
```yaml
version: '3.7'
services:
  irc-rss-feed-bot:
    container_name: irc-rss-feed-bot
    image: ascensive/irc-rss-feed-bot:latest
    restart: always
    logging:
      options:
        max-size: 10m
        max-file: "3"
    volumes:
      - ./irc-rss-feed-bot:/config:ro
```
In the YAML, customize the relative path, e.g. `./irc-rss-feed-bot` of the volume source.
This should be the directory containing `config.yaml`.

From the directory containing `docker-compose.yml`, run `docker-compose up -d irc-rss-feed-bot`.

### Maintenance

If `config.yaml` is updated, the container must be restarted to use the updated file.

Any external changes to the database should be made only when the bot is stopped, but no such changes are expected.
