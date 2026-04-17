import pytest
from src.core.parser import parse_torque_tables
from src.core.writer import write_torque_row
from src.core.constants import SIG_0RPM_ALT

def test_f309_torque_table_parsing(synthetic_f309_torque_data):
    """
    T003: Verifies that parsing the alternate byte blob yields correct TorqueRow properties.
    """
    tables = parse_torque_tables(synthetic_f309_torque_data)
    
    assert len(tables) == 1, "Should identify one alternate torque table"
    table = tables[0]
    
    # Row 0 should be the 0RPM_ALT row
    row0 = table.rows[0]
    assert row0.kind == '0rpm_alt', "Row should be classified as alternate 0rpm"
    assert row0.rpm == 0, "RPM must be implied 0"
    assert row0.torque is None, "Torque must be missing (None)"
    assert abs(row0.compression - 10.0) < 0.001, "Compression must be correctly extracted"
    
    # Length of table should be 4
    assert len(table.rows) == 4

def test_f309_torque_table_serialization(synthetic_f309_torque_data):
    """
    T004: Verifies the serialization packs the alternate row preserving the 03 02 signature 
    and yielding exactly matched byte-for-byte outputs.
    """
    tables = parse_torque_tables(synthetic_f309_torque_data)
    assert len(tables) == 1
    table = tables[0]
    
    # We copy the synthetic data and rewrite the first row
    data = bytearray(synthetic_f309_torque_data)
    # Change the compression value to ensure it updates properly
    table.rows[0].compression = 15.0
    write_torque_row(data, table.rows[0])
    
    # The 13 bytes of the packed table should match the alternate signature and packed bytes
    expected_row0 = SIG_0RPM_ALT + b'\x00\x00\x00\x00pA' # 15.0 is 00 00 70 41 in little-endian float (<f)
    
    offset = table.rows[0].offset
    assert data[offset:offset+13] == expected_row0, "Alternate row signature and payload must be exactly preserved"
    
    # Also verify that replacing into the byte array produces identical binary lengths
    # (Checking that we don't accidentally upgrade the `<BBf` struct to `<Bff`)
    assert len(data) == len(synthetic_f309_torque_data)
