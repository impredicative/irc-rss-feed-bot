"""Style text using one of a variety of stylers.

The supported stylers are: asterisk, irc, unicode
"""
import logging
from typing import Any, Callable, Dict, Union

import dressup
import ircmessage

log = logging.getLogger(__name__)


def _asterisk_style(text: str, **_kwargs: Any) -> str:
    return f"*{text}*"


def _dressup_style(text: str, bold: bool = False, italics: bool = False) -> str:
    """Style the given text with the given options using `dressup`."""
    if not (bold or italics):
        return text

    # Define unicode type
    unicode_type = "math sans"
    if bold:
        unicode_type += " bold"
    if italics:
        unicode_type += " italic"

    # Style
    try:
        return dressup.convert(text, unicode_type=unicode_type)
    except Exception as exc:
        log.exception(f"Error using dressup with {unicode_type=} to format {text!r}: {exc}")


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
