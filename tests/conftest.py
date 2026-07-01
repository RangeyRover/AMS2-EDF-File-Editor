import pytest
import struct
from src.core.constants import (
    HASH_TORQUE, HASH_BOOST, HASH_P2P,
    ROW0_STRUCT, ROW0_ALT_STRUCT, ROWI_STRUCT, ROWF_STRUCT, ENDVAR_STRUCT,
    BOOST_5F_STRUCT, BOOST_I_5F_STRUCT,
    P2P_FULL_STRUCT, P2P_ZERO_STRUCT
)

@pytest.fixture
def synthetic_torque_data():
    """
    Creates a synthetic binary blob containing one Torque table.
    """
    data = bytearray()
    data.extend(b'\x00' * 10)
    
    # 1. 0RPM Row
    data.extend(b'\x24' + HASH_TORQUE + b'\x83\x02')
    data.extend(ROW0_STRUCT.pack(0, 10.0, 100.0))
    
    # 2. Row I
    data.extend(b'\x24' + HASH_TORQUE + b'\x93\x02')
    data.extend(ROWI_STRUCT.pack(1000, 10.0, 150.0))
    
    # 3. Row F
    data.extend(b'\x24' + HASH_TORQUE + b'\xA3\x02')
    data.extend(ROWF_STRUCT.pack(2000.5, 10.0, 200.0))
    
    # 4. EndVar
    data.extend(b'\x24' + HASH_TORQUE + b'\x93\x00')
    data.extend(ENDVAR_STRUCT.pack(3000, 10.0, 0))
    
    data.extend(b'\xFF' * 5)
    return bytes(data)

@pytest.fixture
def synthetic_boost_data():
    """
    Creates a synthetic binary blob containing one Boost table (5F variant).
    """
    data = bytearray()
    data.extend(b'\x00' * 20)
    
    # 1. Boost 0RPM
    data.extend(b'\x24' + HASH_BOOST + b'\x86\xAA')
    data.extend(BOOST_5F_STRUCT.pack(0, 1.0, 1.2, 1.5, 1.8, 2.0))
    
    # 2. Boost Row
    data.extend(b'\x24' + HASH_BOOST + b'\x96\xAA')
    data.extend(BOOST_I_5F_STRUCT.pack(2000, 1.1, 1.3, 1.6, 1.9, 2.1))
    
    return bytes(data)

@pytest.fixture
def synthetic_p2p_data():
    """
    Creates synthetic P2P data.
    """
    data = bytearray()
    data.extend(b'\x00' * 10)
    
    # Full Row
    data.extend(b'\x24' + HASH_P2P + b'\x04\x08')
    data.extend(P2P_FULL_STRUCT.pack(1, 2, 50, 1.5))
    
    # Zero Row
    data.extend(b'\x24' + HASH_P2P + b'\x04\x00')
    data.extend(P2P_ZERO_STRUCT.pack(1, 2, 50, 0))
    
    return bytes(data)

@pytest.fixture
def synthetic_param_data():
    """
    Creates synthetic parameter data.
    """
    data = bytearray()
    
    # EngineInertia (Float) - Signature: 22 46 65 AE 87
    sig_inertia = b'\x22\x46\x65\xAE\x87'
    data.extend(sig_inertia)
    data.extend(struct.pack('<f', 0.45))
    
    # RevLimitSetting (Byte) - Signature: 20 A5 5C C1 C4
    sig_revlim = b'\x20\xA5\x5C\xC1\xC4'
    data.extend(b'\x00' * 5) # spacing
    data.extend(sig_revlim)
    data.extend(struct.pack('B', 1))
    
    return bytes(data)

@pytest.fixture
def synthetic_multi_table_data():
    """
    Creates a synthetic binary blob containing TWO torque tables.
    """
    data = bytearray()
    data.extend(b'\x00' * 10)
    
    # Table 0: 0RPM + Row I + EndVar
    data.extend(b'\x24' + HASH_TORQUE + b'\x83\x02')
    data.extend(ROW0_STRUCT.pack(0, 5.0, 50.0))
    
    data.extend(b'\x24' + HASH_TORQUE + b'\x93\x02')
    data.extend(ROWI_STRUCT.pack(1000, 8.0, 120.0))
    
    data.extend(b'\x24' + HASH_TORQUE + b'\x93\x00')
    data.extend(ENDVAR_STRUCT.pack(2000, 6.0, 0))
    
    data.extend(b'\xAA' * 10)
    
    # Table 1: 0RPM + Row I + EndVar
    data.extend(b'\x24' + HASH_TORQUE + b'\x83\x02')
    data.extend(ROW0_STRUCT.pack(0, 3.0, 30.0))
    
    data.extend(b'\x24' + HASH_TORQUE + b'\x93\x02')
    data.extend(ROWI_STRUCT.pack(1500, 7.0, 180.0))
    
    data.extend(b'\x24' + HASH_TORQUE + b'\x93\x00')
    data.extend(ENDVAR_STRUCT.pack(3000, 4.0, 0))
    
    data.extend(b'\xFF' * 5)
    return bytes(data)

@pytest.fixture
def drag_transaction_fixture():
    from src.core.models import DragTransaction
    return DragTransaction(
        table_index=0,
        row_index=1,
        field="torque",
        start_torque=150.0,
        end_torque=200.0,
        start_compression=10.0,
        end_compression=13.333333015441895,
    )

@pytest.fixture
def synthetic_f309_torque_data():
    data = bytearray()
    data.extend(b'\x00' * 10)
    
    data.extend(b'\x24' + HASH_TORQUE + b'\x03\x02')
    data.extend(ROW0_ALT_STRUCT.pack(0, 0, 10.0))
    
    data.extend(b'\x24' + HASH_TORQUE + b'\x93\x02')
    data.extend(ROWI_STRUCT.pack(1000, 10.0, 150.0))
    
    data.extend(b'\x24' + HASH_TORQUE + b'\xA3\x02')
    data.extend(ROWF_STRUCT.pack(2000.5, 10.0, 200.0))
    
    data.extend(b'\x24' + HASH_TORQUE + b'\x93\x00')
    data.extend(ENDVAR_STRUCT.pack(3000, 10.0, 0))
    
    data.extend(b'\xFF' * 5)
    return bytes(data)

@pytest.fixture
def synthetic_orphan_rowi_torque_data():
    data = bytearray()
    data.extend(b'\x00' * 15)
    
    rpm = struct.pack('<I', 1350) 
    fuzz_sig = b'\x24' + HASH_TORQUE + b'\x03\x02'
    
    data.extend(rpm)
    data.extend(fuzz_sig)
    data.extend(b'\x00')
    
    comp_tq = struct.pack('<ff', 12.0, 180.0)
    data.extend(comp_tq)
    
    data.extend(b'\x24' + HASH_TORQUE + b'\xA3\x02')
    data.extend(ROWF_STRUCT.pack(2000.5, 10.0, 200.0))
    
    data.extend(b'\x24' + HASH_TORQUE + b'\x93\x00')
    data.extend(ENDVAR_STRUCT.pack(3000, 10.0, 0))
    
    data.extend(b'\xFF' * 5)
    return bytes(data)
