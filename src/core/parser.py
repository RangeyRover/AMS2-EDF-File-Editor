import struct
from typing import List, Tuple, Optional, Generator, Union

from .constants import (
    SIG_0RPM, SIG_ROW_I, SIG_ROW_F, SIG_ENDVAR,
    SIG_BOOST_0RPM, SIG_BOOST_ROW,
    ROW0_STRUCT, ROWI_STRUCT, ROWF_STRUCT, ENDVAR_STRUCT,
    BOOST0_STRUCT, BOOSTI_STRUCT,
    PARAMS, ENGINE_LAYOUT_CODES
)
from .models import TorqueRow, TorqueTable, BoostRow, BoostTable, Parameter

def find_all(data: bytes, sub: bytes) -> Generator[int, None, None]:
    start = 0
    L = len(sub)
    while True:
        i = data.find(sub, start)
        if i == -1:
            return
        yield i
        start = i + L  # step to next occurrence (avoid overlap)

def read_by_fmt(data: bytes, pos: int, fmtseq: Tuple[str, ...]) -> Tuple[Optional[List[Union[float, int]]], int]:
    vals = []
    cur = pos
    for f in fmtseq:
        if f == 'f':
            if cur+4 > len(data): return None, pos
            vals.append(struct.unpack_from('<f', data, cur)[0])
            cur += 4
        elif f == 'i':
            if cur+4 > len(data): return None, pos
            vals.append(struct.unpack_from('<i', data, cur)[0])
            cur += 4
        elif f == 'b':
            if cur+1 > len(data): return None, pos
            vals.append(data[cur])
            cur += 1
        else:
            return None, pos
    return vals, cur

def plausible_rpm(x: float) -> bool:
    return 0 <= x <= 25000

def plausible_comp(x: float) -> bool:
    return -300 <= x <= 300

def plausible_torque(x: float) -> bool:
    return -4000 <= x <= 10000

def parse_torque_tables(data: bytes) -> List[TorqueTable]:
    tables = []
    for off0 in find_all(data, SIG_0RPM):
        rows = []
        p = off0 + len(SIG_0RPM)
        if p + ROW0_STRUCT.size > len(data): continue
        b0, comp0, tq0 = ROW0_STRUCT.unpack_from(data, p)
        # tolerate odd b0 values seen in the wild
        if not (plausible_comp(comp0) and plausible_torque(tq0)): continue
        
        rows.append(TorqueRow(0.0, comp0, tq0, off0, '0rpm'))
        
        q = p + ROW0_STRUCT.size
        while q < len(data):
            if data[q:q+len(SIG_0RPM)] == SIG_0RPM:
                # next table begins
                break
            if data[q:q+len(SIG_ROW_I)] == SIG_ROW_I:
                sig_off = q
                q += len(SIG_ROW_I)
                if q + ROWI_STRUCT.size > len(data): break
                rpm_i, comp, tq = ROWI_STRUCT.unpack_from(data, q)
                rpm = float(rpm_i)
                if not (plausible_rpm(rpm) and plausible_comp(comp) and plausible_torque(tq)): break
                rows.append(TorqueRow(rpm, comp, tq, sig_off, 'row_i'))
                q += ROWI_STRUCT.size
                continue
            if data[q:q+len(SIG_ROW_F)] == SIG_ROW_F:
                sig_off = q
                q += len(SIG_ROW_F)
                if q + ROWF_STRUCT.size > len(data): break
                rpm, comp, tq = ROWF_STRUCT.unpack_from(data, q)
                if not (plausible_rpm(rpm) and plausible_comp(comp) and plausible_torque(tq)): break
                rows.append(TorqueRow(rpm, comp, tq, sig_off, 'row_f'))
                q += ROWF_STRUCT.size
                continue
            if data[q:q+len(SIG_ENDVAR)] == SIG_ENDVAR:
                # terminal oddball, read & stop
                sig_off = q
                q += len(SIG_ENDVAR)
                if q + ENDVAR_STRUCT.size > len(data): break
                rpm_i, comp, b = ENDVAR_STRUCT.unpack_from(data, q)
                rows.append(TorqueRow(float(rpm_i), comp, None, sig_off, 'endvar'))
                q += ENDVAR_STRUCT.size
                break
            # no known row signature -> end this table
            break
        if len(rows) >= 2:  # must have at least 0rpm + one row
            # Sort by RPM just for display clarity (source order is generally increasing already)
            # rows.sort(key=lambda r: r.rpm) # Keep original order? No, sort is fine.
            # But wait, verification requires checking offsets. If we sort, we might lose order?
            # models.py says "rows: List[TorqueRow]".
            rows.sort(key=lambda r: r.rpm)
            tables.append(TorqueTable(off0, rows))
    return tables

def parse_boost_tables(data: bytes) -> List[BoostTable]:
    """Parse turbo boost control lookup tables."""
    tables = []
    for off0 in find_all(data, SIG_BOOST_0RPM):
        rows = []
        p = off0 + len(SIG_BOOST_0RPM)
        if p + BOOST0_STRUCT.size > len(data): 
            continue
        
        # Parse 0rpm row: byte (should be 0) + 5 floats for throttle positions
        b0, t0, t25, t50, t75, t100 = BOOST0_STRUCT.unpack_from(data, p)
        
        # Sanity check: throttle values should be between 0.5 and 3.0 typically (0.5-2.0 bar boost)
        if not all(0.5 <= v <= 3.0 for v in [t0, t25, t50, t75, t100]):
            continue
            
        rows.append(BoostRow(0, t0, t25, t50, t75, t100, off0, 'boost_0rpm'))
        q = p + BOOST0_STRUCT.size
        
        while q < len(data):
            # Check if we hit another boost table or end of data
            if data[q:q+len(SIG_BOOST_0RPM)] == SIG_BOOST_0RPM:
                break
            
            if data[q:q+len(SIG_BOOST_ROW)] == SIG_BOOST_ROW:
                sig_off = q
                q += len(SIG_BOOST_ROW)
                if q + BOOSTI_STRUCT.size > len(data): 
                    break
                
                rpm, t0, t25, t50, t75, t100 = BOOSTI_STRUCT.unpack_from(data, q)
                
                # Sanity checks
                if not (0 <= rpm <= 25000):
                    break
                if not all(0.5 <= v <= 3.0 for v in [t0, t25, t50, t75, t100]):
                    break
                
                rows.append(BoostRow(rpm, t0, t25, t50, t75, t100, sig_off, 'boost_row'))
                q += BOOSTI_STRUCT.size
                continue
            
            # No more boost rows
            break
        
        if len(rows) >= 2:  # Must have at least 0rpm + one row
            rows.sort(key=lambda r: r.rpm)
            tables.append(BoostTable(off0, rows))
    
    return tables

def parse_params(data: bytes) -> List[Parameter]:
    out = []
    for sig, (name, fmt) in PARAMS.items():
        for pos in find_all(data, sig):
            start = pos + len(sig)
            if len(fmt) == 0:
                # No value variant (e.g., RevLimitSetting_NoValue)
                out.append(Parameter(name, pos, (), fmt))
            else:
                vals, endp = read_by_fmt(data, start, fmt)
                if vals is None:
                    continue
                out.append(Parameter(name, pos, tuple(vals), fmt))
    return out

def detect_engine_layout(data: bytes) -> Tuple[str, Optional[int]]:
    # search from the end for known tag sequences (3B-terminated families)
    tail = data[-64:] if len(data) > 64 else data
    for k, label in ENGINE_LAYOUT_CODES.items():
        i = tail.rfind(k)
        if i != -1:
            # compute absolute offset
            return label, len(data) - len(tail) + i
    return 'Unknown/Not found', None
