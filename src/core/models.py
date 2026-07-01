from dataclasses import dataclass
from typing import Tuple, Optional, List, Union
from .constants import (
    ROW0_STRUCT, ROW0_ALT_STRUCT, ROWI_STRUCT, ROWF_STRUCT, ENDVAR_STRUCT,
    BOOST_4F_STRUCT, BOOST_5F_STRUCT, BOOST_I_4F_STRUCT, BOOST_I_5F_STRUCT, BOOST_I_5B_STRUCT,
    P2P_FULL_STRUCT, P2P_ZERO_STRUCT, PARAMS
)

@dataclass
class TorqueRow:
    rpm: float
    compression: float
    torque: Optional[float]
    offset: int
    kind: str  # '0rpm', '0rpm_alt', 'row_i', 'row_f', 'endvar'
    exact_signature: Optional[bytes] = None  # Caches anomalous explicit row_i signatures

    @property
    def size(self) -> int:
        if self.kind == '0rpm': return 7 + ROW0_STRUCT.size
        elif self.kind == '0rpm_alt': return 7 + ROW0_ALT_STRUCT.size
        elif self.kind == 'row_i': 
            if self.exact_signature:
                return 4 + len(self.exact_signature) + 8 # 4 for rpm, 8 for comp+tq
            return 7 + ROWI_STRUCT.size
        elif self.kind == 'row_f': return 7 + ROWF_STRUCT.size
        elif self.kind == 'endvar': return 7 + ENDVAR_STRUCT.size
        return 0

@dataclass
class TorqueTable:
    offset: int
    rows: List[TorqueRow]
    
    @property
    def size(self) -> int:
        return sum(r.size for r in self.rows)

@dataclass
class BoostRow:
    rpm: float
    t0: float
    t25: float
    t50: float
    t75: float
    t100: Optional[float]
    offset: int
    kind: str # 'boost_0rpm_5f', 'boost_0rpm_4f', 'boost_row_5f', 'boost_row_4f', 'boost_row_5b'
    
    @property
    def size(self) -> int:
        marker_hash_len = 5 # \x24 + 4 byte hash
        if self.kind == 'boost_0rpm_5f': return marker_hash_len + 2 + BOOST_5F_STRUCT.size # suffix is 2 bytes
        if self.kind == 'boost_0rpm_4f': return marker_hash_len + 2 + BOOST_4F_STRUCT.size
        if self.kind == 'boost_row_5f': return marker_hash_len + 2 + BOOST_I_5F_STRUCT.size
        if self.kind == 'boost_row_4f': return marker_hash_len + 2 + BOOST_I_4F_STRUCT.size
        if self.kind == 'boost_row_5b': return marker_hash_len + 2 + BOOST_I_5B_STRUCT.size
        return 0

@dataclass
class BoostTable:
    offset: int
    rows: List[BoostRow]
    
    @property
    def size(self) -> int:
        return sum(r.size for r in self.rows)

@dataclass
class P2PRow:
    mode: int       # N
    rpm: float      # X
    throttle: float # Y
    multiplier: float # V
    offset: int
    kind: str       # 'p2p_full', 'p2p_zero'
    pad: int = 0    # Preserved 4th byte in p2p_zero

    @property
    def size(self) -> int:
        marker_hash_len = 5 # \x24 + 4 byte hash
        if self.kind == 'p2p_full': return marker_hash_len + 2 + P2P_FULL_STRUCT.size
        if self.kind == 'p2p_zero': return marker_hash_len + 2 + P2P_ZERO_STRUCT.size
        return 0

@dataclass
class P2PTable:
    offset: int
    rows: List[P2PRow]

    @property
    def size(self) -> int:
        return sum(r.size for r in self.rows)

@dataclass
class Parameter:
    name: str
    offset: int
    values: Tuple[Union[float, int], ...]
    fmt: Optional[Tuple[str, ...]] = None
    
    @property
    def size(self) -> int:
        # Need to find signature length
        # This is slightly inefficient but safe
        sig_len = 0
        fmt_seq = self.fmt
        
        for sig, (pname, pfmt) in PARAMS.items():
            if pname == self.name:
                sig_len = len(sig)
                if not fmt_seq: fmt_seq = pfmt
                break
        
        data_size = 0
        if fmt_seq:
            for f in fmt_seq:
                if f == 'f': data_size += 4
                elif f == 'i': data_size += 4
                elif f == 'b': data_size += 1
        
        return sig_len + data_size


@dataclass
class DragTransaction:
    """Atomic record of a single drag operation for undo.

    Created on mouse-up, pushed onto the undo stack.
    Consumed on Ctrl+Z to restore previous values.
    """
    table_index: int              # Index of the TorqueTable in the tables list
    row_index: int                # Index of the TorqueRow within the table
    field: str                    # "torque" or "compression" — primary drag target
    start_torque: float           # Torque value before drag (float32-quantised)
    end_torque: float             # Torque value after drag (float32-quantised)
    start_compression: float      # Compression value before drag (float32-quantised)
    end_compression: float        # Compression value after drag (float32-quantised)

