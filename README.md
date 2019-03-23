# irc-rss-feed-bot
**irc-rss-feed-bot** is a Python 3.7 based IRC RSS and Atom feed posting bot.
It essentially posts the entries of RSS and Atom feeds in IRC channels, one entry per message.
More specifically, it posts the titles and shortened URLs of entries.

## Features
* Multiple channels on an IRC server are supported, with each channel having its own set of feeds.
For multiple servers, run an instance of the bot process for each server.
* Entries are posted only if the channel has not had any conversation for at least 15 minutes, thereby preventing the
interruption of any preexisting conversations.
* A SQLite database file records the entries that have been posted, thereby preventing them from being reposted.

For more features, see the customizable [global settings](#global-settings) and
[feed-specific settings](#feed-specific-settings).

## Links
* Code: https://github.com/impredicative/irc-rss-feed-bot
* Container: https://hub.docker.com/r/ascensive/irc-rss-feed-bot

## Examples
```text
<Feed[bot]> [ArXiv:cs.AI] Concurrent Meta Reinforcement Learning → https://arxiv.org/abs/1903.02710v1
<Feed[bot]> [ArXiv:cs.AI] Attack Graph Obfuscation → https://arxiv.org/abs/1903.02601v1
<Feed[bot]> [InfoWorld] What is a devops engineer? And how do you become one? → https://j.mp/2NOgQ3g
<Feed[bot]> [InfoWorld] What is Jupyter Notebook? Data analysis made easier → https://j.mp/2NMailP
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
feeds:
  "#some_chan1":
    j:AJCN:
      url: https://academic.oup.com/rss/site_6122/3981.xml
      period: 24
      blacklist:
        title:
          - ^Calendar\ of\ Events$
    MedicalXpress:nutrition:
      url: https://medicalxpress.com/rss-feed/search/?search=nutrition
    r/FoodNerds:
      url: https://www.reddit.com/r/FoodNerds/new/.rss
      shorten: false
      sub:
        url:
          pattern: ^https://www\.reddit\.com/r/.+?/comments/(?P<id>.+?)/.+$
          repl: https://redd.it/\g<id>
  "##some_chan2":
    ArXiv:cs.AI:
      url: https://export.arxiv.org/rss/cs.AI
      period: 1.5
      shorten: false
      format:
        re:
          title: ^(?P<name>.+?)\.?\ \(arXiv:\d+\.\d+(?P<ver>v\d+)
        str:
          title: '{name}'
          url: '{url}{ver}'
    InfoWorld:
      url: https://www.infoworld.com/index.rss
    PwC:Trending:
      url: https://us-east1-ml-feeds.cloudfunctions.net/pwc/trending
      dedup: feed
```

#### Global settings

##### Mandatory
* **`host`**
* **`ssl_port`**
* **`nick`**
* **`nick_password`**
* **`tokens/bitly`**: URL shortening is enabled for each feed by default but can be disabled selectively.
Bitly tokens are required for shortening URLs.
The sample tokens are for illustration only and are invalid.
To obtain tokens, refer to these [instructions](https://github.com/impredicative/bitlyshortener#usage).
Providing multiple tokens, perhaps as many as 9 free ones or a single commercial one, is required.
Failing this, Bitly imposed rate limits for shortening URLs will lead to errors.
If there are errors, the batched new posts in a feed may get reprocessed the next time the feed is read.
It is safer to provide more tokens than are necessary.

##### Optional
* **`mode`**: This can for example be `+igR` for [Freenode](https://freenode.net/kb/answer/usermodes).
Setting it is recommended.

#### Feed-specific settings

##### Mandatory
* **`url`**: This is the URL of the feed. 

##### Optional
These are optional and are independent of each other:
* **`anew`**: If `true`, this skips posting all preexisting entries in a new feed, i.e. it starts anew.
A new feed is defined as one with no prior posts in its channel.
The default value is `false`, in which case only up to three of the most recent entries are posted.
The default exists to limit flooding a channel when one or more new feeds are added.
Either way, none of the future entries in the feed are affected, and they are all posted without reservation.
* **`blacklist/title`**: This is a list of regular expression patterns that result in a title being skipped if a
[search](https://docs.python.org/3/library/re.html#re.search) finds any of the patterns in the title.
* **`blacklist/url`**: Similar to `blacklist/title`.
* **`dedup`**: This indicates how to deduplicate posts for the feed, thereby preventing them from being reposted.
The default value is `channel` (per-channel), and an alternate possible value is `feed` (per-feed).
Note that per-feed deduplication is implicitly specific to its channel.
* **`https`**: If `true`, links that start with `http://` are changed to start with `https://` instead.
Its default value is `false`.
* **`period`**: This indicates how frequently to read the feed in hours on an average. Its default value is 1.
Conservative polling is recommended. A value below 0.25 is changed to a minimum of 0.25.
The first read is delayed by up to a uniformly distributed random 10% so as to better distribute the load of multiple
feeds.
Subsequent reads are varied by up to a uniformly distributed random ±5% for the same reason.
* **`shorten`**: This indicates whether to post shortened URLs for the feed.
The default value is `true`.
The alternative value `false` is recommended if the URL is naturally small, or if `sub` or `format` can be used to make
it small.

##### Conditional
The sample configuration above contains examples of these:
* **`format/re/title`**: This is a single regular expression pattern that is
[searched](https://docs.python.org/3/library/re.html#re.search) for in the title.
It is used to collect named [key-value pairs](https://docs.python.org/3/library/re.html#re.Match.groupdict) from the
match if there is one.
* **`format/re/url`**: Similar to `format/re/title`.
* **`format/str/title`**: The key-value pairs collected using `format/re/title` and `format/re/url`,
both of which are optional, are combined along with the default additions of both `title` and `url` as keys.
The key-value pairs are used to [format](https://docs.python.org/3/library/stdtypes.html#str.format_map) the provided
quoted title string.
The default value is `{title}`.
* **`format/str/url`**: Similar to `format/str/title`. The default value is `{url}`.
If this is specified, it is advisable to set `shorten` to `false` for the feed.

* **`sub/title/pattern`**: This is a single regular expression pattern that if found results in the entry
title being [substituted](https://docs.python.org/3/library/re.html#re.sub).
* **`sub/title/repl`**: If `sub/title/pattern` is found, the entry title is replaced with this replacement, otherwise it
is forwarded unchanged.
* **`sub/url/pattern`**: Similar to `sub/title/pattern`.
If a pattern is specified, it is advisable to set `shorten` to `false` for the feed.
* **`sub/url/repl`**: Similar to `sub/title/repl`.

#### Remarks
Refer to the sample configuration above for usage examples.
The order of execution of some of the above operations is: `blacklist`, `https`, `sub`, `format`, `shorten`.
A `posts.v1.db` database file is written by the bot in the same directory as `config.yaml`.
This database file must be preserved but not version controlled.

### Deployment
* Some but not all warning and error alerts are sent to `##{nick}-alerts`.
For example, if the nick is `Feed[bot]`, these alerts will be sent to `##Feed[bot]-alerts`.
It is recommended that the alerts channel be registered and monitored.

* It is recommended that the bot be auto-voiced (+V) in each channel.
Failing this, messages from the bot risk being silently dropped by the server.
This is despite the bot-enforced limit of two seconds per message across the server.

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
      - ./irc-rss-feed-bot:/config
```
In the YAML, customize the relative path, e.g. `./irc-rss-feed-bot` of the volume source.
This should be the directory containing `config.yaml`.
This directory must be writable by Docker using the UID defined in the Dockerfile; it is 999.
A simple way to ensure it is writable is to run a command such as `chmod a+w ./irc-rss-feed-bot` once on the host.

From the directory containing `docker-compose.yml`, run `docker-compose up -d irc-rss-feed-bot`.
Use `docker logs -f irc-rss-feed-bot` to see and follow informational logs.

### Maintenance
* If `config.yaml` is updated, the container must be restarted to use the updated file.
* Any external changes to the database should be made only when the bot is stopped, but no such changes are expected.
* The database file grows as new posts are made. For the most part this indefinite growth can be ignored.
Currently the standard approach for handling this, if necessary, is to stop the bot and delete the
database file if it has grown unacceptably large.
Restarting the bot will then create a new database file, and all configured feeds will be handled as new.
This deletion is however discouraged as a routine measure.
