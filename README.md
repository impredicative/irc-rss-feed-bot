# irc-rss-feed-bot
**irc-rss-feed-bot** is a Python-based IRC RSS/Atom feed posting bot.
It essentially posts the entries of RSS/Atom feeds in IRC channels, one entry per message.

## Features
* Multiple channels on an IRC server are supported, with each channel having its own set of feeds.
To use with multiple servers, use an instance per server.
* A SQLite database file records the entries that have already been posted, thereby preventing them from being reposted.
* Entries are posted to a channel only if the channel has not had any conversation for at least 15 minutes, thereby
preventing the interruption of any preexisting conversations.
* Poll frequency of each feed is individually customizable.
* Entry URLs are shortened by default using [`bitlyshortener`](https://github.com/impredicative/bitlyshortener/).

## Links
* Code: https://github.com/impredicative/irc-rss-feed-bot
* Container: https://hub.docker.com/r/ascensive/irc-rss-feed-bot

## Examples
```text
<Feed[bot]> <ArXiv:cs.AI> Concurrent Meta Reinforcement Learning (v1) | https://arxiv.org/abs/1903.02710v1
<Feed[bot]> <ArXiv:cs.AI> Attack Graph Obfuscation (v1) | https://arxiv.org/abs/1903.02601v1
<Feed[bot]> <InfoWorld> What is a devops engineer? And how do you become one? | https://j.mp/2NOgQ3g
<Feed[bot]> <InfoWorld> What is Jupyter Notebook? Data analysis made easier | https://j.mp/2NMailP
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
feeds:
  "#some_chan1":
    ArXiv:cs.AI:
      url: https://export.arxiv.org/rss/cs.AI
      shorten: no
    DeepMind:
      url: https://deepmind.com/blog/feed/basic/
  "#some_chan2":
    j:AJCN:
      url: https://academic.oup.com/rss/site_6122/3981.xml
      freq: 24
    MedicalXpress:nutrition:
      url: https://medicalxpress.com/rss-feed/search/?search=nutrition
```

Global settings:
* `mode`: This is optional and can for example be `+igR` for [Freenode](https://freenode.net/kb/answer/usermodes).
Setting it is recommended.
* `tokens/bitly`: Bitly tokens are required for shortening URLs. They are mandatory.
To obtain them, refer to these [instructions](https://github.com/impredicative/bitlyshortener#usage).
Providing multiple tokens, perhaps as many as ten free ones or a single commercial one, is required.
Failing this, Bitly imposed rate limits will lead to errors, and groups of posts will be skipped.

Feed-specific settings:
* `freq` indicates how frequently to poll the feed in hours. It is 1 by default. Conservative polling is recommended.
* `shorten` indicates whether to use Bitly to shorten URls. It is "yes" by default and can otherwise be "no".
Setting this is recommended only for feeds with naturally short URLs.

### Deployment
* Some but not all warning and error alerts are sent to `##{nick}-alerts`.
For example, if the nick is `Feed[bot]`, these alerts will be sent to `##Feed[bot]-alerts`.
It is recommended that the alerts channel be registered even if it is not monitored.

* It is required that the bot be auto-voiced (+V) in each channel.
Failing this, rapid-fire messages from the bot can easily be dropped by the server.

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

If `config.yaml` is updated, the container must be restarted to use the updated file.
