"""ircmessage utilities."""
from typing import Dict, Optional

import ircmessage


def style(text: str, **style_config: Optional[Dict[str, str]]) -> str:
    """Style the given text and options using ircmessage."""
    return ircmessage.style(text, **style_config, reset=True) if (style_config and any(style_config.values())) else text
