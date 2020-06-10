"""bs4 utilities."""
import unittest

from bs4 import BeautifulSoup


def html_to_text(text: str) -> str:
    """Return extracted text from the given HTML string."""
    # Ref: https://stackoverflow.com/a/34532382/
    return BeautifulSoup(text, features="html.parser").get_text()


# pylint: disable=line-too-long,missing-class-docstring,missing-function-docstring
class TestHtmlToText(unittest.TestCase):
    def test_examples(self):
        examples = {
            "<b>Hello world!</b>": "Hello world!",
            '<a href="google.com">some text</a>': "some text",
            '<span class="small-caps">l</span>-arginine minimizes immunosuppression and prothrombin time and enhances the genotoxicity of 5-fluorouracil in rats': "l-arginine minimizes immunosuppression and prothrombin time and enhances the genotoxicity of 5-fluorouracil in rats",
            "Attenuation of diabetic nephropathy by dietary fenugreek (<em>Trigonella foenum-graecum</em>) seeds and onion (<em>Allium cepa</em>) <em>via</em> suppression of glucose transporters and renin-angiotensin system": "Attenuation of diabetic nephropathy by dietary fenugreek (Trigonella foenum-graecum) seeds and onion (Allium cepa) via suppression of glucose transporters and renin-angiotensin system",
        }
        for html, expected_text in examples.items():
            with self.subTest(html=html):
                self.assertEqual(expected_text, html_to_text(html))


# python -m unittest -v ircrssfeedbot.util.bs4
