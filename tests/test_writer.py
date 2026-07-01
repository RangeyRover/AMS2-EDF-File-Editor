import pytest
import struct
from src.core.models import TorqueRow, BoostRow, P2PRow, Parameter
from src.core.writer import write_torque_row, write_boost_row, write_p2p_row, write_param, scale_torque_tables
from src.core.parser import parse_torque_tables, parse_boost_tables, parse_p2p_tables
from src.core.constants import ROW0_STRUCT, ROWI_STRUCT, BOOST_I_5F_STRUCT, P2P_FULL_STRUCT

def test_write_torque_row_0rpm(synthetic_torque_data):
    data = bytearray(synthetic_torque_data)
    
    tables = parse_torque_tables(data)
    row0 = tables[0].rows[0]
    assert row0.kind == '0rpm'
    assert row0.torque == 100.0
    
    row0.torque = 123.45
    write_torque_row(data, row0)
    
    # 7 bytes for marker + hash + suffix
    data_offset = row0.offset + 7
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
    
    _, _, tq = ROWI_STRUCT.unpack_from(data, row1.offset + 7)
    assert tq == pytest.approx(999.99)

def test_write_boost_row(synthetic_boost_data):
    data = bytearray(synthetic_boost_data)
    tables = parse_boost_tables(data)
    row1 = tables[0].rows[1] # boost_row_5f
    assert row1.t100 == pytest.approx(2.1)
    
    row1.t100 = 3.5
    write_boost_row(data, row1)
    
    # 7 bytes for marker + hash + suffix
    unpacked = BOOST_I_5F_STRUCT.unpack_from(data, row1.offset + 7)
    assert unpacked[5] == pytest.approx(3.5)

def test_write_p2p_row(synthetic_p2p_data):
    data = bytearray(synthetic_p2p_data)
    tables = parse_p2p_tables(data)
    row0 = tables[0].rows[0] # p2p_full
    assert row0.multiplier == pytest.approx(1.5)
    
    row0.multiplier = 2.0
    write_p2p_row(data, row0)
    
    unpacked = P2P_FULL_STRUCT.unpack_from(data, row0.offset + 7)
    assert unpacked[3] == pytest.approx(2.0)

def test_write_param_float(synthetic_param_data):
    data = bytearray(synthetic_param_data)
    from src.core.parser import parse_params
    params = parse_params(data)
    p = next(x for x in params if x.name == 'EngineInertia')
    
    assert p.values[0] == pytest.approx(0.45)
    
    p.values = (0.99,)
    write_param(data, p)
    
    data_offset = p.offset + 5
    val = struct.unpack_from('<f', data, data_offset)[0]
    assert val == pytest.approx(0.99)

def test_scale_torque_tables(synthetic_torque_data):
    data = bytearray(synthetic_torque_data)
    tables = parse_torque_tables(data)
    
    scale_torque_tables(data, tables, 1.1)
    
    row0 = tables[0].rows[0]
    data_offset0 = row0.offset + 7
    _, _, tq0 = ROW0_STRUCT.unpack_from(data, data_offset0)
    assert tq0 == pytest.approx(110.0)
    
    row1 = tables[0].rows[1]
    _, _, tq1 = ROWI_STRUCT.unpack_from(data, row1.offset + 7)
    assert tq1 == pytest.approx(165.0)
