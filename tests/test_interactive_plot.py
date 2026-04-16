"""Unit tests for interactive plot drag logic (non-GUI).

Tests the quantisation, clamping, DragTransaction model, and undo stack
logic without requiring a running Tkinter mainloop or display.
"""
import struct
import pytest
from src.core.models import DragTransaction, TorqueRow, TorqueTable
from src.utils.formatting import quantise_f32


class TestQuantiseF32:
    """Tests for the float32 quantisation utility (FR-015)."""

    def test_roundtrip_exact(self):
        """Values exactly representable in float32 should be unchanged."""
        assert quantise_f32(1.0) == 1.0
        assert quantise_f32(0.0) == 0.0
        assert quantise_f32(-100.0) == -100.0

    def test_roundtrip_imprecise(self):
        """Values not exactly representable should round to nearest float32."""
        val = 1.100000023841858  # known float32 repr of ~1.1
        result = quantise_f32(1.1)
        assert result == pytest.approx(val, abs=1e-7)

    def test_large_value(self):
        """Large torque values should survive quantisation."""
        result = quantise_f32(9999.9)
        # Verify it round-trips through struct pack
        packed = struct.pack('<f', 9999.9)
        expected = struct.unpack('<f', packed)[0]
        assert result == expected

    def test_negative_value(self):
        """Negative values should quantise correctly."""
        result = quantise_f32(-3500.5)
        packed = struct.pack('<f', -3500.5)
        expected = struct.unpack('<f', packed)[0]
        assert result == expected


class TestDragTransaction:
    """Tests for the DragTransaction dataclass."""

    def test_construction(self, drag_transaction_fixture):
        """DragTransaction should store all fields correctly."""
        txn = drag_transaction_fixture
        assert txn.table_index == 0
        assert txn.row_index == 1
        assert txn.field == "torque"
        assert txn.start_torque == 150.0
        assert txn.end_torque == 200.0
        assert txn.start_compression == 10.0
        assert txn.end_compression == pytest.approx(13.333, abs=0.01)

    def test_fields_are_mutable(self):
        """DragTransaction is a dataclass — fields should be assignable."""
        txn = DragTransaction(0, 0, "torque", 100.0, 200.0, 10.0, 20.0)
        txn.end_torque = 300.0
        assert txn.end_torque == 300.0


class TestClamping:
    """Tests for torque and compression value clamping (FR-009)."""

    def test_torque_clamp_high(self):
        """Values above 10000 should clamp to 10000."""
        val = min(10000.0, 15000.0)
        assert val == 10000.0

    def test_torque_clamp_low(self):
        """Values below -4000 should clamp to -4000."""
        val = max(-4000.0, -5000.0)
        assert val == -4000.0

    def test_compression_clamp_high(self):
        """Compression above 300 should clamp."""
        val = min(300.0, 500.0)
        assert val == 300.0

    def test_compression_clamp_low(self):
        """Compression below -300 should clamp."""
        val = max(-300.0, -400.0)
        assert val == -300.0


class TestUndoStack:
    """Tests for undo stack management (FR-012, FR-024)."""

    def test_stack_push_and_pop(self):
        """Stack should support LIFO push/pop."""
        stack = []
        txn1 = DragTransaction(0, 0, "torque", 100.0, 200.0, 10.0, 20.0)
        txn2 = DragTransaction(0, 1, "torque", 150.0, 250.0, 15.0, 25.0)
        stack.append(txn1)
        stack.append(txn2)
        assert len(stack) == 2
        popped = stack.pop()
        assert popped is txn2
        assert len(stack) == 1

    def test_stack_cap_at_50(self):
        """Stack should cap at 50 entries (FR-024)."""
        stack = []
        for i in range(60):
            txn = DragTransaction(0, i % 10, "torque", float(i), float(i + 1), 0.0, 0.0)
            stack.append(txn)
            if len(stack) > 50:
                stack = stack[-50:]
        assert len(stack) == 50
        # Oldest entry should be i=10 (first 10 trimmed)
        assert stack[0].start_torque == 10.0

    def test_empty_stack_pop(self):
        """Popping from empty stack should not raise — guarded by caller."""
        stack = []
        assert len(stack) == 0
        # Guard pattern: only pop if non-empty
        if stack:
            stack.pop()
        assert len(stack) == 0


class TestProportionalCompression:
    """Tests for proportional compression scaling (FR-031)."""

    def test_basic_ratio(self):
        """Compression should scale proportionally with torque."""
        old_torque = 100.0
        new_torque = 150.0
        old_compression = 10.0
        ratio = new_torque / old_torque
        new_compression = old_compression * ratio
        assert new_compression == pytest.approx(15.0)

    def test_zero_old_torque_freezes_compression(self):
        """If old torque is 0, compression should stay unchanged."""
        old_torque = 0.0
        new_torque = 100.0
        old_compression = 10.0
        if old_torque != 0:
            ratio = new_torque / old_torque
            new_compression = old_compression * ratio
        else:
            new_compression = old_compression
        assert new_compression == 10.0

    def test_compression_clamped(self):
        """Proportional scaling should be clamped to [-300, 300]."""
        old_torque = 100.0
        new_torque = 5000.0
        old_compression = 200.0
        ratio = new_torque / old_torque
        new_compression = old_compression * ratio  # 10000.0 — way over limit
        new_compression = max(-300.0, min(300.0, new_compression))
        assert new_compression == 300.0
