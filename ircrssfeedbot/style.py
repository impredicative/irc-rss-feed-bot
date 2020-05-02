"""Style text using one of a variety of stylers.

The supported stylers are: asterisk, irc, unicode
"""
from typing import Any, Callable, Dict, Union

import dressup
import ircmessage


def _asterisk_style(text: str, **_kwargs: Any) -> str:
    return f"*{text}*"


def _dressup_style(text: str, bold: bool = False, italics: bool = False) -> str:
    """Style the given text with the given options using `dressup`."""
    if not (bold or italics):
        return text
    unicode_type = "math sans"
    if bold:
        unicode_type += " bold"
    if italics:
        unicode_type += " italic"
    return dressup.convert(text, unicode_type=unicode_type)


def _ircmessage_style(text: str, **style_config: Union[bool, str]) -> str:
    """Style the given text with the given options using `ircmessage`."""
    return ircmessage.style(text, **style_config, reset=True) if (style_config and any(style_config.values())) else text


_STYLERS: Dict[str, Callable[..., str]] = {
    "asterisk": _asterisk_style,
    "irc": _ircmessage_style,
    "unicode": _dressup_style,
}


def style(text: str, styler: str, **kwargs: Any) -> str:
    """Style the given text using the indicated styler and options."""
    return _STYLERS[styler](text, **kwargs)
