"""Unit tests for src.utils.formatting."""
import pytest
from src.utils.formatting import format_float


class TestFormatFloat:
    """FR9: All floats must use fixed-point notation, never scientific."""

    def test_positive_integer_like(self):
        assert format_float(100.0, 3) == "100.000"

    def test_negative_value(self):
        assert format_float(-45.678, 3) == "-45.678"

    def test_zero(self):
        assert format_float(0.0, 3) == "0.000"

    def test_large_value_no_scientific(self):
        # 25000.0 must NOT become "2.5e+04"
        result = format_float(25000.0, 1)
        assert result == "25000.0"
        assert "e" not in result
        assert "E" not in result

    def test_small_value_no_scientific(self):
        # 0.00001 must NOT become "1e-05"
        result = format_float(0.00001, 6)
        assert result == "0.000010"
        assert "e" not in result
        assert "E" not in result

    def test_very_small_value_no_scientific(self):
        result = format_float(1.23e-10, 12)
        assert "e" not in result
        assert "E" not in result

    def test_default_decimals_is_six(self):
        result = format_float(3.14)
        assert result == "3.140000"

    def test_custom_decimals(self):
        assert format_float(1.5, 0) == "2"  # rounds
        assert format_float(1.5, 1) == "1.5"
        assert format_float(1.5, 4) == "1.5000"

    def test_32bit_float_precision(self):
        # Simulates a value round-tripped through 32-bit float packing
        import struct
        original = 0.45
        packed = struct.pack('<f', original)
        unpacked = struct.unpack('<f', packed)[0]
        result = format_float(unpacked, 6)
        assert "e" not in result
        assert result.startswith("0.4")
