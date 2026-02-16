from dataclasses import dataclass
from typing import Tuple, Optional, List, Union
from .constants import (
    SIG_0RPM, SIG_ROW_I, SIG_ROW_F, SIG_ENDVAR,
    SIG_BOOST_0RPM, SIG_BOOST_ROW,
    ROW0_STRUCT, ROWI_STRUCT, ROWF_STRUCT, ENDVAR_STRUCT,
    BOOST0_STRUCT, BOOSTI_STRUCT, PARAMS
)

@dataclass
class TorqueRow:
    rpm: float
    compression: float
    torque: Optional[float]
    offset: int
    kind: str  # '0rpm', 'row_i', 'row_f', 'endvar'

    @property
    def size(self) -> int:
        if self.kind == '0rpm': return len(SIG_0RPM) + ROW0_STRUCT.size
        if self.kind == 'row_i': return len(SIG_ROW_I) + ROWI_STRUCT.size
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

