"""textwrap utilities."""
import unittest

_MIN_WIDTH = 5  # == len(textwrap.shorten(string.ascii_letters, len(string.ascii_letters) - 1)) == len('[...]')


def shorten_to_bytes_width(string: str, maximum_bytes: int) -> str:
    """Return shortened text for a given bytes width."""
    # Ref: Based on https://stackoverflow.com/a/56429867/

    maximum_bytes = max(_MIN_WIDTH, maximum_bytes)  # This prevents ValueError if maximum_bytes < _MIN_WIDTH

    placeholder: str = "[...]"
    encoded_placeholder = placeholder.encode().strip()

    # Get the UTF-8 bytes that represent the string and normalize the spaces.
    string = " ".join(string.split())
    encoded_string = string.encode()

    # If the input string is empty simply return an empty string.
    if not encoded_string:
        return ""

    # In case we don't need to shorten anything simply return
    if len(encoded_string) <= maximum_bytes:
        return string

    # We need to shorten the string, so we need to add the placeholder
    substring = encoded_string[: maximum_bytes - len(encoded_placeholder)]
    splitted = substring.rsplit(b" ", 1)  # Split at last space-character
    if len(splitted) == 2:
        return b" ".join([splitted[0], encoded_placeholder]).decode()
    return "[...]"


# pylint: disable=missing-class-docstring,missing-function-docstring
class TestShortener(unittest.TestCase):
    def test_example(self):
        text = "☺ Ilsa, le méchant ☺ ☺ gardien ☺"
        width = 27
        shortened = shorten_to_bytes_width(text, width)
        self.assertEqual(shortened, "☺ Ilsa, le méchant [...]")
        self.assertLessEqual(len(shortened.encode()), width)

    def test_stylized_irc_text(self):
        self.assertEqual(shorten_to_bytes_width(r"\x1dZZZ\x0f " * 100, 30), r"\x1dZZZ\x0f \x1dZZZ\x0f [...]")


# python -m unittest -v ircrssfeedbot.util.textwrap
