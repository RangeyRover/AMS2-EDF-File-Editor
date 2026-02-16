import pytest
from src.core.parser import (
    find_all, read_by_fmt, 
    parse_torque_tables, parse_boost_tables, parse_params,
    plausible_rpm, plausible_torque
)
from src.core.constants import SIG_0RPM

def test_find_all():
    data = b'\x01\x02\x03\x01\x02\x03\x00'
    res = list(find_all(data, b'\x01\x02'))
    assert res == [0, 3]

def test_find_all_no_overlap():
    data = b'\xAA\xAA\xAA'
    res = list(find_all(data, b'\xAA\xAA'))
    # Should only find index 0, not index 1 (overlap)
    assert res == [0]

def test_read_by_fmt():
    # Float (4), Int (4), Byte (1)
    # 1.0 = 00 00 80 3F
    # 65536 = 00 00 01 00
    # 255 = FF
    data = b'\x00\x00\x80\x3F\x00\x00\x01\x00\xFF'
    vals, next_pos = read_by_fmt(data, 0, ('f', 'i', 'b'))
    
    assert vals[0] == 1.0
    assert vals[1] == 65536
    assert vals[2] == 255
    assert next_pos == 9

def test_read_by_fmt_out_of_bounds():
    data = b'\x00'
    vals, next_pos = read_by_fmt(data, 0, ('f',))
    assert vals is None
    assert next_pos == 0

def test_plausible_checks():
    assert plausible_rpm(0) is True
    assert plausible_rpm(25000) is True
    assert plausible_rpm(-1) is False
    assert plausible_rpm(25001) is False
    
    assert plausible_torque(0) is True
    assert plausible_torque(10000) is True
    assert plausible_torque(-4001) is False

def test_parse_torque_tables(synthetic_torque_data):
    tables = parse_torque_tables(synthetic_torque_data)
    assert len(tables) == 1
    
    t = tables[0]
    # Check offset
    # SIG_0RPM starts at 10
    assert t.offset == 10
    
    rows = t.rows
    assert len(rows) == 4
    
    # Row 0: 0RPM
    assert rows[0].kind == '0rpm'
    assert rows[0].rpm == 0.0
    assert rows[0].torque == 100.0
    
    # Row 1: Int RPM
    assert rows[1].kind == 'row_i'
    assert rows[1].rpm == 1000.0
    assert rows[1].torque == 150.0
    
    # Row 2: Float RPM
    assert rows[2].kind == 'row_f'
    assert rows[2].rpm == 2000.5
    assert rows[2].torque == 200.0
    
    # Row 3: EndVar
    assert rows[3].kind == 'endvar'
    assert rows[3].rpm == 3000.0
    assert rows[3].torque is None

def test_parse_boost_tables(synthetic_boost_data):
    tables = parse_boost_tables(synthetic_boost_data)
    assert len(tables) == 1
    
    t = tables[0]
    assert t.offset == 20
    
    rows = t.rows
    assert len(rows) == 2
    
    # Row 0
    assert rows[0].rpm == 0
    assert rows[0].t100 == pytest.approx(2.0)
    
    # Row 1
    assert rows[1].rpm == 2000
    assert rows[1].t100 == pytest.approx(2.1)

def test_parse_params(synthetic_param_data):
    params = parse_params(synthetic_param_data)
    assert len(params) == 2
    
    # Sort to ensure consistent order
    params.sort(key=lambda x: x.offset)
    
    p1 = params[0]
    assert p1.name == 'EngineInertia'
    assert pytest.approx(p1.values[0]) == 0.45
    
    p2 = params[1]
    assert p2.name == 'RevLimitSetting'
    assert p2.values[0] == 1

def test_detect_engine_layout():
    from src.core.parser import detect_engine_layout
    
    # Signature for 'Straight 4': D7 2D 3B
    # Let's put it at the end
    data = b'\x00' * 10 + b'\xD7\x2D\x3B'
    
    label, offset = detect_engine_layout(data)
    assert label == 'Straight 4'
    assert offset == 10

def test_detect_engine_layout_not_found():
    from src.core.parser import detect_engine_layout
    data = b'\x00' * 10
    label, offset = detect_engine_layout(data)
    assert label == 'Unknown/Not found'
    assert offset is None
