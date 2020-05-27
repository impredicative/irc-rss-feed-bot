"""bs4 utilities."""
from bs4 import BeautifulSoup


def html_to_text(text: str) -> str:
    """Return extracted text from the given HTML string."""
    # Ref: https://stackoverflow.com/a/34532382/
    return BeautifulSoup(text, features="lxml").get_text()
