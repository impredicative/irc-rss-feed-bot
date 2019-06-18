# irc-rss-feed-bot
**irc-rss-feed-bot** is a Python 3.7 based IRC RSS and Atom feed posting bot.
It essentially posts the entries of RSS and Atom feeds in IRC channels, one entry per message.
More specifically, it posts the titles and shortened URLs of entries.

## Features
* Multiple channels on an IRC server are supported, with each channel having its own set of feeds.
For use with multiple servers, a separate instance of the bot process can be run for each server.
* Entries are posted only if the channel has not had any conversation for at least 15 minutes, thereby preventing the
interruption of any preexisting conversations.
* A SQLite database file records hashes of the entries that have been posted, thereby preventing them from being
reposted.
* ETag and TTL based compressed in-memory caches of URL content are conditionally used for preventing unnecessary URL
reads.
Any websites with a mismatched _strong_ ETag are probabilistically detected, and this caching is then disabled for them
for the duration of the process. Note that this detection is skipped for a _weak_ ETag.
The TTL cache is used only for URLs that are used by more than one feed each.

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
### Configuration: secret
Prepare a private `secrets.env` environment file using the sample below.
```ini
IRC_PASSWORD=YourActualPassword
BITLY_TOKENS=5e71a58b19582f48edcb0235637ac3536dd3b6dc,bd90119a7b617e81b293ddebbbfed3e955eac5af,42f309642a018e6b4d7cfba6854080719dccf0cc,0819552eb8b42e52dbc8b4c3e1654f5cd96c0dcc,430a002fe9d4e8f94097f7a5cd974ffce85eb605,71f9856bc96c6a8eabeac4f763daaec16896e183,81f6d477cfcef006a6dd35c4b947d1c1fdcbf445,06441b445c75d2251f0a56ae87506c69dc468af5,1e71089487fb70f42fff51b7ad49f192ffcb00f2
```

Bitly tokens are required for shortening URLs.
URL shortening is enabled for all feeds by default but can be disabled selectively per feed.
The sample tokens above are for illustration only and are invalid.
To obtain tokens, refer to [these instructions](https://github.com/impredicative/bitlyshortener#usage).
Providing multiple comma-separated tokens, perhaps as many as 9 free ones or a single commercial one, is required.
Failing this, Bitly imposed rate limits for shortening URLs will lead to errors.
If there are errors, the batched new entries in a feed may get reprocessed the next time the feed is read.
It is safer to provide more tokens than are necessary.

### Configuration: non-secret
Prepare a version-controlled `config.yaml` file using the sample below.
A full-fledged real-world example is also
[available](https://github.com/impredicative/freenode-bots/blob/master/irc-rss-feed-bot/config.yaml).
```yaml
host: chat.freenode.net
ssl_port: 6697
nick: MyFeed[bot]
alerts_channel: '##mybot-alerts'
mode:
feeds:
  "##mybot-alerts":
    irc-rss-feed-bot:
      url: https://github.com/impredicative/irc-rss-feed-bot/releases.atom
      period: 12
      shorten: false
  "#some_chan1":
    j:AJCN:
      url: https://academic.oup.com/rss/site_6122/3981.xml
      period: 12
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
    ArXiv:cs.AI: &ArXiv
      url: https://export.arxiv.org/rss/cs.AI
      period: 1.5
      https: true
      shorten: false
      group: ArXiv:cs
      format:
        re:
          title: '^(?P<name>.+?)\.?\ \(arXiv:.+(?P<ver>v\d+)\ '
        str:
          title: '{name}'
          url: '{url}{ver}'
    ArXiv:cs.NE:
      <<: *ArXiv
      url: https://export.arxiv.org/rss/cs.NE
    ArXiv:stat.ML:
      <<: *ArXiv
      url: https://export.arxiv.org/rss/stat.ML
      group: null
    BioRxiv:
      url: https://connect.biorxiv.org/biorxiv_xml.php?subject=all
      alert: false
      https: true
    InfoWorld:
      url: https://www.infoworld.com/index.rss
    KDnuggets:
      url: https://us-east1-ml-feeds.cloudfunctions.net/kdnuggets
      new: all
    libraries.io/pypi/scikit-learn:
      url: https://libraries.io/pypi/scikit-learn/versions.atom
      new: none
      period: 8
      shorten: false
    PwC:Trending:
      url: https://us-east1-ml-feeds.cloudfunctions.net/pwc/trending
      period: 0.5
      dedup: feed
    YT:3Blue1Brown: &YT
      url: https://www.youtube.com/feeds/videos.xml?channel_id=UCYO_jab_esuFRV4b17AJtAw
      period: 12
      shorten: false
      sub:
        url:
          pattern: ^https://www\.youtube\.com/watch\?v=(?P<id>.+?)$
          repl: https://youtu.be/\g<id>
    YT:AGI:
      url: https://www.youtube.com/results?search_query=%22artificial+general+intelligence%22&sp=CAISBBABGAI%253D
      hext: <a href:filter("/watch\?v=(.+)"):prepend("https://youtu.be/"):link href^="/watch?v=" title:title/>
      period: 12
      shorten: false
      blacklist:
        title:
          - \bWikipedia\ audio\ article\b
    YT:LexFridman:
      <<: *YT
      url: https://www.youtube.com/feeds/videos.xml?channel_id=UCSHZKyawb77ixDdsGog4iWA
      whitelist:
        title:
          - \bAGI\b
```

#### Global settings

##### Mandatory
* **`host`**
* **`ssl_port`**
* **`nick`**

##### Optional
* **`alerts_channel`**: Some but not all warning and error alerts are sent to the this channel.
Its default value is `##{nick}-alerts`. The key `{nick}`, if present in the value, is formatted with the actual nick.
For example, if the nick is `MyFeed[bot]`, alerts will by default be sent to `##MyFeed[bot]-alerts`.
Since a channel name starts with #, the name if provided **must be quoted**.
It is recommended that the alerts channel be registered and monitored.
* **`mode`**: This can for example be `+igR` for [Freenode](https://freenode.net/kb/answer/usermodes).
Setting it is recommended.
* **`once`**: If `true`, each feed is queued only once. The default is `false`. This can be useful for testing purposes.

#### Feed-specific settings
A feed is defined under a channel as in the sample configuration. The feed's key represents its name.

The order of execution of the interacting operations is: `blacklist`, `whitelist`, `https`, `sub`, `format`, `shorten`.
Refer to the sample configuration for usage examples.

YAML [anchors and references](https://en.wikipedia.org/wiki/YAML#Advanced_components) can be used to reuse nodes.
Examples of this are in the sample.

##### Mandatory
* **`url`**: This is the URL of the feed. 

##### Optional
These are optional and are independent of each other:
* **`alert`**: If `false`, an alert is not sent if an error occurs when reading or processing the feed.
Its default value is `true`. This can be useful for feeds that are known to fail intermittently.
* **`blacklist/category`**: This is a list of regular expression patterns that result in an entry being skipped if a
[search](https://docs.python.org/3/library/re.html#re.search) finds any of the patterns in any of the categories of the
entry.
* **`blacklist/title`**: This is a list of regular expression patterns that result in an entry being skipped if a
[search](https://docs.python.org/3/library/re.html#re.search) finds any of the patterns in the title.
* **`blacklist/url`**: Similar to `blacklist/title`.
* **`dedup`**: This indicates how to deduplicate posts for the feed, thereby preventing them from being reposted.
The default value is `channel` (per-channel), and an alternate possible value is `feed` (per-feed).
Note that per-feed deduplication is implicitly specific to its channel.
* **`group`**: If a string, this delays the processing of a feed that has just been read until all other feeds having
the same group are also read.
This encourages multiple feeds having the same group to be be posted in succession, except if interrupted by
conversation.
It is however possible that unrelated feeds of any channel gets posted between ones having the same group.
To explicitly specify the absence of a group when using a YAML reference, the value can be specified as `null`.
It is recommended that feeds in the same group have the same `period`.
* **`hext`**: This is a string representing the [hext](https://hext.thomastrapp.com/documentation) DSL for extracting a
list of entries from a web page that is not a feed.
Before using, it can be tested in the form [here](https://hext.thomastrapp.com/).
Each extracted entry must at minimum include a `title`, a valid `link`, and zero or more values for `category`.
Some sites require a custom user agent for successful scraping; such a customization can be requested by creating an
issue.
* **`https`**: If `true`, links that start with `http://` are changed to start with `https://` instead.
Its default value is `false`.
* **`new`**: This indicates up to how many entries of a new feed to post.
A new feed is defined as one with no prior posts in its channel.
The default value is `some` which is interpreted as 3.
The default is intended to limit flooding a channel when one or more new feeds are added.
A string value of `none` is interpreted as 0 and will skip all entries for a new feed.
A value of `all` will skip no entries for a new feed; it is not recommended and should be used sparingly if at all.
In any case, future entries in the feed are not affected by this option on subsequent reads,
and they are all forwarded without a limit.
* **`period`**: This indicates how frequently to read the feed in hours on an average. Its default value is 1.
Conservative polling is recommended. Any value below 0.5 is changed to a minimum of 0.5.
To make service restarts safer by preventing excessive reads, the first read is delayed by half the period.
To better distribute the load of reading multiple feeds, a uniformly distributed random ±5% is applied to the period for
each read.
* **`shorten`**: This indicates whether to post shortened URLs for the feed.
The default value is `true`.
The alternative value `false` is recommended if the URL is naturally small, or if `sub` or `format` can be used to make
it small.
* **`whitelist/category`**: This is a list of regular expression patterns that result in an entry being skipped unless a
[search](https://docs.python.org/3/library/re.html#re.search) finds any of the patterns in any of the categories of the
entry.
* **`whitelist/explain`**: This applies only to `whitelist/title`.
It can be useful for understanding which portion of a post's title matched the whitelist.
If `true`, the matching text of each posted title is enclosed by asterisks.
For example, "This is a \*matching sample\* title". The default value is `false`.
* **`whitelist/title`**: This is a list of regular expression patterns that result in an entry being skipped unless a
[search](https://docs.python.org/3/library/re.html#re.search) finds any of the patterns in the title.
* **`whitelist/url`**: Similar to `whitelist/title`.

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

### Deployment
* As a reminder, it is recommended that the alerts channel be registered and monitored.

* It is recommended that the bot be auto-voiced (+V) in each channel.
Failing this, messages from the bot risk being silently dropped by the server.
This is despite the bot-enforced limit of two seconds per message across the server.

* It is recommended that the bot be run as a Docker container using using Docker ≥18.09.2, possibly with
Docker Compose ≥1.24.0.
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
    env_file:
      - ./irc-rss-feed-bot/secrets.env
```

* In the above service definition in `docker-compose.yml`:
  * `image`: For better reproducibility, use a specific
  [versioned tag](https://hub.docker.com/r/ascensive/irc-rss-feed-bot/tags), e.g. `0.2.5` instead of `latest`.
  * `volumes`: Customize the relative path to the previously created `config.yaml` file, e.g. `./irc-rss-feed-bot`.
  This volume source directory must be writable by the container using the UID defined in the Dockerfile; it is 999.
  A simple way to ensure it is writable is to run a command such as `chmod a+w ./irc-rss-feed-bot` once on the host.
  * `env_file`: Customize the relative path to `secrets.env`.

* From the directory containing `docker-compose.yml`, run `docker-compose up -d irc-rss-feed-bot`.
Use `docker logs -f irc-rss-feed-bot` to see and follow informational logs.

### Maintenance
* If `config.yaml` is updated, the container must be restarted to use the updated file.
* If `secrets.env` or the service definition in `docker-compose.yml` are updated, the container must be recreated
(and not merely restarted) to use the updated file.
* A `posts.v2.db` database file is written by the bot in the same directory as `config.yaml`.
This database file must be preserved with routine backups. After restoring a backup, before starting the container,
ensure the database file is writable by running a command such as `chmod a+w ./irc-rss-feed-bot/posts.v2.db`.
* The database file grows as new posts are made. For the most part this indefinite growth can be ignored.
Currently the standard approach for handling this, if necessary, is to stop the bot and delete the
database file if it has grown unacceptably large.
Restarting the bot will then create a new database file, and all configured feeds will be handled as new.
This deletion is however discouraged as a routine measure.
