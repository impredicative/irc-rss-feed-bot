import textwrap
import unittest

_MIN_WIDTH = 5  # == len(textwrap.shorten(string.ascii_letters, len(string.ascii_letters) - 1)) == len('[...]')


def shorten_to_bytes_width(text: str, width: int) -> str:
    # Ref: https://stackoverflow.com/a/56401167/
    width = max(_MIN_WIDTH, width)  # This prevents ValueError if width < _MIN_WIDTH
    text = textwrap.shorten(text, width)  # After this line, len(text.encode()) >= width
    while len(text.encode()) > width:
        text = textwrap.shorten(text, len(text) - 1)
    assert len(text.encode()) <= width
    return text


class TestShortener(unittest.TestCase):
    def test_example(self):
        text = "☺ Ilsa, le méchant ☺ ☺ gardien ☺"
        width = 27
        shortened = shorten_to_bytes_width(text, width)
        self.assertEqual(shortened, "☺ Ilsa, le méchant [...]")
        self.assertLessEqual(len(shortened.encode()), width)


# python -m unittest -v ircrssfeedbot.util.textwrap
