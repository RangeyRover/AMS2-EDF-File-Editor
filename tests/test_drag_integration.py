"""Integration tests for drag → write → verify pipeline.

Tests the full chain: modify TorqueRow → write_torque_row → verify bytes.
Does not require a GUI — operates directly on in-memory data.
"""
import struct
import pytest
from src.core.parser import parse_torque_tables
from src.core.writer import write_torque_row
from src.core.models import TorqueRow
from src.utils.formatting import quantise_f32


class TestDragUpdatesBinary:
    """Test that drag-simulated row updates persist to binary (FR-005)."""

    def test_torque_change_persists(self, synthetic_torque_data):
        """Modify torque on a row and verify binary changes."""
        data = bytearray(synthetic_torque_data)
        tables = parse_torque_tables(data)
        assert len(tables) > 0

        # Pick row 1 (Row I @ RPM=1000)
        row = tables[0].rows[1]
        assert row.torque == pytest.approx(150.0)
        original_rpm = row.rpm

        # Simulate drag: change torque
        new_torque = quantise_f32(175.5)
        row.torque = new_torque
        write_torque_row(data, row)

        # Re-parse and verify
        tables2 = parse_torque_tables(data)
        row2 = tables2[0].rows[1]
        assert row2.torque == pytest.approx(new_torque)
        assert row2.rpm == pytest.approx(original_rpm)  # RPM unchanged (FR-002)

    def test_compression_change_persists(self, synthetic_torque_data):
        """Modify compression on a row and verify binary changes."""
        data = bytearray(synthetic_torque_data)
        tables = parse_torque_tables(data)
        row = tables[0].rows[1]
        original_torque = row.torque

        # Simulate compression drag
        new_comp = quantise_f32(15.5)
        row.compression = new_comp
        write_torque_row(data, row)

        # Re-parse and verify
        tables2 = parse_torque_tables(data)
        row2 = tables2[0].rows[1]
        assert row2.compression == pytest.approx(new_comp)
        assert row2.torque == pytest.approx(original_torque)  # Torque unchanged (FR-033)

    def test_rpm_bytes_unchanged_after_drag(self, synthetic_torque_data):
        """RPM bytes must remain byte-identical after any drag (SC-003)."""
        data = bytearray(synthetic_torque_data)
        tables = parse_torque_tables(data)
        row = tables[0].rows[1]

        # Snapshot RPM bytes before drag
        # Row I struct: Int(RPM), Float(Comp), Float(Torque) — RPM is first 4 bytes after signature
        from src.core.constants import SIG_ROW_I
        rpm_offset = row.offset + len(SIG_ROW_I)
        rpm_bytes_before = bytes(data[rpm_offset:rpm_offset + 4])

        # Simulate drag
        row.torque = quantise_f32(300.0)
        write_torque_row(data, row)

        # Verify RPM bytes unchanged
        rpm_bytes_after = bytes(data[rpm_offset:rpm_offset + 4])
        assert rpm_bytes_before == rpm_bytes_after


class TestCrossTableIsolation:
    """Test that dragging on one table doesn't affect another (FR-010, SC-005)."""

    def test_table1_unchanged_after_table0_drag(self, synthetic_multi_table_data):
        """Drag on Table 0 must produce zero byte changes in Table 1's region."""
        data = bytearray(synthetic_multi_table_data)
        tables = parse_torque_tables(data)

        if len(tables) < 2:
            pytest.skip("Multi-table fixture produced fewer than 2 tables")

        # Snapshot Table 1's entire binary region
        t1_start = tables[1].offset
        t1_end = t1_start + tables[1].size
        t1_bytes_before = bytes(data[t1_start:t1_end])

        # Modify Table 0
        row = tables[0].rows[0]
        row.torque = quantise_f32(999.0)
        row.compression = quantise_f32(99.0)
        write_torque_row(data, row)

        # Verify Table 1 unchanged
        t1_bytes_after = bytes(data[t1_start:t1_end])
        assert t1_bytes_before == t1_bytes_after, "Table 1 binary region changed after Table 0 drag"


class TestQuantisationRoundTrip:
    """Test float32 quantisation round-trip consistency (SC-006)."""

    def test_drag_save_reopen_matches(self, synthetic_torque_data):
        """Quantised value → write → reparse should yield identical value."""
        data = bytearray(synthetic_torque_data)
        tables = parse_torque_tables(data)
        row = tables[0].rows[1]

        # Drag to a value that's NOT exactly float32
        target = 123.456789  # float64
        quantised = quantise_f32(target)
        row.torque = quantised
        write_torque_row(data, row)

        # Re-parse (simulates save → reopen)
        tables2 = parse_torque_tables(data)
        row2 = tables2[0].rows[1]

        # Must be EXACTLY equal (not approx) — no jitter
        assert row2.torque == quantised
