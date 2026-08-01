"""Significant-figure rounding.

Its own module so both `normalise` and `sizing` can use it without either
importing the other.
"""

from math import floor, log10


def round_sig(value: float, digits: int = 2) -> float:
    """Round to N significant figures, returning an int where that is exact."""
    if not value:
        return 0
    exponent = floor(log10(abs(value)))
    factor = 10 ** (digits - 1 - exponent)
    result = round(value * factor) / factor
    return int(result) if result == int(result) else result
