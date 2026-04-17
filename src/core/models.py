from dataclasses import dataclass
from typing import Tuple, Optional, List, Union
from .constants import (
    SIG_0RPM, SIG_0RPM_ALT, SIG_ROW_I, SIG_ROW_F, SIG_ENDVAR,
    SIG_BOOST_0RPM, SIG_BOOST_ROW,
    ROW0_STRUCT, ROW0_ALT_STRUCT, ROWI_STRUCT, ROWF_STRUCT, ENDVAR_STRUCT,
    BOOST0_STRUCT, BOOSTI_STRUCT, PARAMS
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
        if self.kind == '0rpm': return len(SIG_0RPM) + ROW0_STRUCT.size
        if self.kind == '0rpm_alt': return len(SIG_0RPM_ALT) + ROW0_ALT_STRUCT.size
        if self.kind == 'row_i': 
            sig_len = len(self.exact_signature) if self.exact_signature else len(SIG_ROW_I)
            return sig_len + ROWI_STRUCT.size
        if self.kind == 'row_f': return len(SIG_ROW_F) + ROWF_STRUCT.size
        if self.kind == 'endvar': return len(SIG_ENDVAR) + ENDVAR_STRUCT.size
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
    t100: float
    offset: int
    kind: str # 'boost_0rpm', 'boost_row'
    
    @property
    def size(self) -> int:
        if self.kind == 'boost_0rpm': return len(SIG_BOOST_0RPM) + BOOST0_STRUCT.size
        if self.kind == 'boost_row': return len(SIG_BOOST_ROW) + BOOSTI_STRUCT.size
        return 0

@dataclass
class BoostTable:
    offset: int
    rows: List[BoostRow]
    
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

