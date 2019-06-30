from typing import Dict, Optional

import ircmessage


def style(text: str, **style_config: Optional[Dict[str, str]]) -> str:
    return ircmessage.style(text, **style_config, reset=True) if style_config else text
