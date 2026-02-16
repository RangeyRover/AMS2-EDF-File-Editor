"""Shared formatting utilities for float display."""


def format_float(val: float, decimals: int = 6) -> str:
    """Format a float using fixed-point notation (never scientific).

    Args:
        val: The float value to format.
        decimals: Number of decimal places (default 6).

    Returns:
        A string like '123.456000', never '1.23e+02'.
    """
    return f"{val:.{decimals}f}"
