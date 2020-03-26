"""str utilities."""


class Float(float):
    """Directional percentage representation of float."""

    def _percent(self, precision: int) -> str:
        indicator = "↑" if self > 0 else ("↓" if self < 0 else "")
        return f"{indicator}{abs(self):.{precision}%}"

    @property
    def decipercent(self):
        """Return the directional formatted string with a precision of a tenth of a percent."""
        return self._percent(1)

    @property
    def percent(self) -> str:
        """Return the directional formatted string with a precision of a whole percent."""
        return self._percent(0)
