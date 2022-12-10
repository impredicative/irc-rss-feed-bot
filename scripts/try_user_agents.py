"""Read a URL using a variety of user agent strings."""
import time

import httpx
import requests

from ircrssfeedbot import config

TEST_URL = ""
READER = ["requests", "httpx"][0]

# pylint: disable=line-too-long
USER_AGENTS = [
    # Basic
    config.USER_AGENT_DEFAULT,
    "Mozilla/5.0",
    config.PACKAGE_NAME,
    # Promising
    "Googlebot-News",
    "FeedFetcher-Google; (+http://www.google.com/feedfetcher.html)",
    # https://support.google.com/webmasters/answer/1061943?hl=en
    "APIs-Google (+https://developers.google.com/webmasters/APIs-Google.html)",
    "Mediapartners-Google",
    "Mozilla/5.0 (Linux; Android 5.0; SM-G920A) AppleWebKit (KHTML, like Gecko) Chrome Mobile Safari (compatible; AdsBot-Google-Mobile; +http://www.google.com/mobile/adsbot.html)",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1 (compatible; AdsBot-Google-Mobile; +http://www.google.com/mobile/adsbot.html)",
    "AdsBot-Google (+http://www.google.com/adsbot.html)",
    "Googlebot-Image/1.0",
    "Googlebot-News",
    "Googlebot-Video/1.0",
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Safari/537.36",
    "Googlebot/2.1 (+http://www.google.com/bot.html)",
    "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.96 Mobile Safari/537.36 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "compatible; Mediapartners-Google/2.1; +http://www.google.com/bot.html",
    "AdsBot-Google-Mobile-Apps",
    "FeedFetcher-Google; (+http://www.google.com/feedfetcher.html)",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.118 Safari/537.36 (compatible; Google-Read-Aloud; +https://support.google.com/webmasters/answer/1061943)",
    # https://www.bing.com/webmaster/help/which-crawlers-does-bing-use-8c184ec0
    "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 7_0 like Mac OS X) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11A465 Safari/9537.53 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
    "Mozilla/5.0 (Windows Phone 8.1; ARM; Trident/7.0; Touch; rv:11.0; IEMobile/11.0; NOKIA; Lumia 530) like Gecko (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
    "msnbot/2.0b (+http://search.msn.com/msnbot.htm)",
    "msnbot-media/1.1 (+http://search.msn.com/msnbot.htm)",
    "Mozilla/5.0 (compatible; adidxbot/2.0; +http://www.bing.com/bingbot.htm)",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 7_0 like Mac OS X) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11A465 Safari/9537.53 (compatible; adidxbot/2.0; +http://www.bing.com/bingbot.htm)",
    "Mozilla/5.0 (Windows Phone 8.1; ARM; Trident/7.0; Touch; rv:11.0; IEMobile/11.0; NOKIA; Lumia 530) like Gecko (compatible; adidxbot/2.0; +http://www.bing.com/bingbot.htm)",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/534+ (KHTML, like Gecko) BingPreview/1.0b",
    "Mozilla/5.0 (Windows Phone 8.1; ARM; Trident/7.0; Touch; rv:11.0; IEMobile/11.0; NOKIA; Lumia 530) like Gecko BingPreview/1.0b",
]
# pylint: enable=line-too-long

USER_AGENTS = list(dict.fromkeys(USER_AGENTS))
for user_agent in USER_AGENTS:
    print(f"Trying {READER} with user agent: {user_agent!r}")
    if READER == "requests":
        response = requests.Session().get(TEST_URL, timeout=3, headers={"User-Agent": user_agent})
    elif READER == "httpx":
        response = httpx.Client().get(TEST_URL, timeout=3, headers={"User-Agent": user_agent})  # type: ignore
    else:
        assert False
    try:
        response.raise_for_status()
    except Exception as exc:
        print(f"Failed: {exc}")
    else:
        print("Succeeded.")
    print()
    time.sleep(1)
