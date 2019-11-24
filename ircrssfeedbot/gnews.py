import functools
import base64
import re

# Ref: https://stackoverflow.com/a/59023463/

_ENCODED_URL_RE = re.compile(r'^https://news\.google\.com/__i/rss/rd/articles/(?P<encoded_url>[^?]+)')
_DECODED_URL_RE = re.compile(rb'^\x08\x13"[^h]+(?P<primary_url>[^\xd2]+)\xd2\x01')


@functools.lru_cache(2048)
def _decode_google_news_url(url: str) -> str:
    match = _ENCODED_URL_RE.match(url)
    encoded_text = match.groupdict()['encoded_url']  # type: ignore
    encoded_text += '==='  # Fix incorrect padding. Ref: https://stackoverflow.com/a/49459036/
    decoded_text = base64.urlsafe_b64decode(encoded_text)

    match = _DECODED_URL_RE.match(decoded_text)
    primary_url = match.groupdict()['primary_url']  # type: ignore
    primary_url = primary_url.decode()
    return primary_url


def decode_google_news_url(url: str) -> str:  # Not cached because not all Google News URLs are encoded.
    return _decode_google_news_url(url) if url.startswith('https://news.google.com/') else url
