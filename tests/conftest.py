import pytest
import struct
from src.core.constants import (
    SIG_0RPM, SIG_ROW_I, SIG_ROW_F, SIG_ENDVAR,
    SIG_BOOST_0RPM, SIG_BOOST_ROW,
    ROW0_STRUCT, ROWI_STRUCT, ROWF_STRUCT, ENDVAR_STRUCT,
    BOOST0_STRUCT, BOOSTI_STRUCT
)

@pytest.fixture
def synthetic_torque_data():
    """
    Creates a synthetic binary blob containing one Torque table.
    Table structure:
    - 0RPM Row
    - Row I (Int RPM)
    - Row F (Float RPM)
    - EndVar Row
    """
    data = bytearray()
    
    # Padding
    data.extend(b'\x00' * 10)
    
    # 1. 0RPM Row (Offset 10)
    data.extend(SIG_0RPM)
    # Struct: Byte, Float(Comp), Float(Torque)
    # 0, 10.0, 100.0
    data.extend(ROW0_STRUCT.pack(0, 10.0, 100.0))
    
    # 2. Row I (Offset 10 + 7 + 9 = 26)
    data.extend(SIG_ROW_I)
    # Struct: Int(RPM), Float(Comp), Float(Torque)
    # 1000, 10.0, 150.0
    data.extend(ROWI_STRUCT.pack(1000, 10.0, 150.0))
    
    # 3. Row F (Offset 26 + 7 + 12 = 45)
    data.extend(SIG_ROW_F)
    # Struct: Float(RPM), Float(Comp), Float(Torque)
    # 2000.5, 10.0, 200.0
    data.extend(ROWF_STRUCT.pack(2000.5, 10.0, 200.0))
    
    # 4. EndVar (Offset 45 + 7 + 12 = 64)
    data.extend(SIG_ENDVAR)
    # Struct: Int(RPM), Float(Comp), Byte
    # 3000, 10.0, 0
    data.extend(ENDVAR_STRUCT.pack(3000, 10.0, 0))
    
    # Trailing bytes
    data.extend(b'\xFF' * 5)
    
    return bytes(data)

@pytest.fixture
def synthetic_boost_data():
    """
    Creates a synthetic binary blob containing one Boost table.
    """
    data = bytearray()
    data.extend(b'\x00' * 20)
    
    # 1. Boost 0RPM
    data.extend(SIG_BOOST_0RPM)
    # Struct: Byte, 5 floats
    data.extend(BOOST0_STRUCT.pack(0, 1.0, 1.2, 1.5, 1.8, 2.0))
    
    # 2. Boost Row
    data.extend(SIG_BOOST_ROW)
    # Struct: Int, 5 floats
    data.extend(BOOSTI_STRUCT.pack(2000, 1.1, 1.3, 1.6, 1.9, 2.1))
    
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
