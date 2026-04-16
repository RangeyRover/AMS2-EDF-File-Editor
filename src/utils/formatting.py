"""Shared formatting utilities for float display."""

import struct


def format_float(val: float, decimals: int = 6) -> str:
    """Format a float using fixed-point notation (never scientific).

    Args:
        val: The float value to format.
        decimals: Number of decimal places (default 6).

    Returns:
        A string like '123.456000', never '1.23e+02'.
    """
    return f"{val:.{decimals}f}"


def quantise_f32(val: float) -> float:
    """Quantise a Python float64 to the nearest IEEE 754 float32 value.

    This ensures the value displayed to the user matches exactly what
    will be stored in the EDF binary (which uses 4-byte floats).

    Args:
        val: The float64 value to quantise.

    Returns:
        The nearest representable float32 value, as a Python float.
    """
    return struct.unpack('<f', struct.pack('<f', val))[0]
