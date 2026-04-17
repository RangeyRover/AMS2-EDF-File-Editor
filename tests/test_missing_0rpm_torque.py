import pytest
from src.core.parser import parse_torque_tables
from src.core.writer import write_torque_row
import struct

def test_missing_0rpm_torque_table_parsing(synthetic_orphan_rowi_torque_data):
    """
    T002: Verifies that parsing the orphaned ROW_I block yields a valid TorqueTable
    without crashing due to the missing 0RPM header.
    """
    tables = parse_torque_tables(synthetic_orphan_rowi_torque_data)
    
    assert len(tables) == 1, "Should identify one implicitly anchored torque table"
    table = tables[0]
    
    # Row 0 should be interpreted as a row_i native struct using the exact wildcard
    row0 = table.rows[0]
    assert row0.kind == 'row_i', "Initial row must be a row_i struct"
    assert row0.rpm == 1350, "RPM must be correctly parsed from the start"
    assert row0.torque == 180.0, "Torque must be 180.0"
    assert row0.compression == 12.0, "Compression must be correctly extracted"
    
    # In models.py we expect exact_signature to be injected
    assert hasattr(row0, 'exact_signature'), "Row must stash its exact byte match"
    assert row0.exact_signature == b'\x24\x8b\x0a\xb7\x71\x03\x02\x00', "Byte anomaly signature (+b0) must be flawlessly preserved"
    
    # Total rows in the fixture should be 3
    assert len(table.rows) == 3

def test_missing_0rpm_torque_table_serialization(synthetic_orphan_rowi_torque_data):
    """
    T003: Verifies the serialization packs the anomalous row using exact_signature
    and yields exactly matched byte-for-byte outputs.
    """
    tables = parse_torque_tables(synthetic_orphan_rowi_torque_data)
    assert len(tables) == 1
    table = tables[0]
    
    # We copy the synthetic data and rewrite the first row
    data = bytearray(synthetic_orphan_rowi_torque_data)
    
    # Mutate to prove it actually updates
    table.rows[0].compression = 15.0
    write_torque_row(data, table.rows[0])
    
    # The 20 bytes of the packed row_i (4-byte RPM, 8-byte sig+b0, 4-byte float, 4-byte float)
    # The signature we put in the fixture was '\x24\x8b\x0a\xb7\x71\x03\x02\x00'
    expected_fuzz_sig = b'\x24\x8b\x0a\xb7\x71\x03\x02\x00'
    expected_rpm = struct.pack('<I', 1350)
    expected_comp_tq = struct.pack('<ff', 15.0, 180.0)
    
    expected_row0 = expected_rpm + expected_fuzz_sig + expected_comp_tq
    
    offset = table.rows[0].offset
    assert data[offset:offset+20] == expected_row0, "Anomalous row signature and payload must be exactly preserved"
    
    # Replacing back into bytearray shouldn't change its total length
    assert len(data) == len(synthetic_orphan_rowi_torque_data)
