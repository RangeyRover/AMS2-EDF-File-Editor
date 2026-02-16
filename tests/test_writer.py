import pytest
import struct
from src.core.models import TorqueRow, Parameter
from src.core.writer import write_torque_row, write_param, scale_torque_tables
from src.core.parser import parse_torque_tables
from src.core.constants import SIG_0RPM, SIG_ROW_I, ROW0_STRUCT, ROWI_STRUCT

def test_write_torque_row_0rpm(synthetic_torque_data):
    # Create a mutable copy
    data = bytearray(synthetic_torque_data)
    
    # Parse to get the row
    tables = parse_torque_tables(data)
    row0 = tables[0].rows[0]
    assert row0.kind == '0rpm'
    assert row0.torque == 100.0
    
    # Modify row object
    row0.torque = 123.45
    
    # Write back
    write_torque_row(data, row0)
    
    # Verify in binary
    # 0rpm offset points to Signature. Data is len(SIG) after.
    # struct is <Bff. Torque is the last float.
    data_offset = row0.offset + len(SIG_0RPM)
    # unpack B, f, f
    _, _, tq = ROW0_STRUCT.unpack_from(data, data_offset)
    assert tq == pytest.approx(123.45)

def test_write_torque_row_row_i(synthetic_torque_data):
    data = bytearray(synthetic_torque_data)
    tables = parse_torque_tables(data)
    row1 = tables[0].rows[1] # row_i
    assert row1.kind == 'row_i'
    assert row1.torque == 150.0
    
    row1.torque = 999.99
    
    write_torque_row(data, row1)
    
    # row_i offset points to Signature.
    # struct is <iff.
    _, _, tq = ROWI_STRUCT.unpack_from(data, row1.offset + len(SIG_ROW_I))
    assert tq == pytest.approx(999.99)

def test_write_param_float(synthetic_param_data):
    data = bytearray(synthetic_param_data)
    # Parse manually or verify logic
    # EngineInertia is first. float at offset + len(SIG)
    # Parse to get object
    from src.core.parser import parse_params
    params = parse_params(data)
    # Sort to find EngineInertia
    p = next(x for x in params if x.name == 'EngineInertia')
    
    assert p.values[0] == pytest.approx(0.45)
    
    # Update value
    p.values = (0.99,)
    
    write_param(data, p)
    
    # Verify binary
    # Offset points to Signature. Data is len(SIG) after.
    # We implicitly know SIG length from the parser or constant, but wait.
    # The Parameter object has `offset` (start of signature).
    # We need to skip signature to find data.
    # Writer needs to look up signature length? 
    # Or maybe parser should have stored data_offset?
    # v0.2 parser stored `pos` which is start of signature.
    # v0.2 writer used `PARAMS` lookup to get signature length.
    
    # Verify
    # 22 46 65 AE 87 (5 bytes)
    data_offset = p.offset + 5
    val = struct.unpack_from('<f', data, data_offset)[0]
    assert val == pytest.approx(0.99)

def test_scale_torque_tables(synthetic_torque_data):
    data = bytearray(synthetic_torque_data)
    tables = parse_torque_tables(data)
    
    # Scale by +10%
    scale_torque_tables(data, tables, 1.1)
    
    # Verify values in data
    # Row 0 (100 -> 110)
    row0 = tables[0].rows[0]
    data_offset0 = row0.offset + len(SIG_0RPM)
    _, _, tq0 = ROW0_STRUCT.unpack_from(data, data_offset0)
    assert tq0 == pytest.approx(110.0)
    
    # Row 1 (150 -> 165)
    row1 = tables[0].rows[1]
    _, _, tq1 = ROWI_STRUCT.unpack_from(data, row1.offset + len(SIG_ROW_I))
    assert tq1 == pytest.approx(165.0)
    
