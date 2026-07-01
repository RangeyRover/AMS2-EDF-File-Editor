import struct
from typing import List, Tuple, Optional, Generator, Union

from .constants import (
    ROW0_STRUCT, ROW0_ALT_STRUCT, ROWI_STRUCT, ROWF_STRUCT, ENDVAR_STRUCT,
    BOOST_4F_STRUCT, BOOST_5F_STRUCT, BOOST_I_4F_STRUCT, BOOST_I_5F_STRUCT, BOOST_I_5B_STRUCT,
    P2P_FULL_STRUCT, P2P_ZERO_STRUCT,
    PARAMS, ENGINE_LAYOUT_CODES
)
from .models import TorqueRow, TorqueTable, BoostRow, BoostTable, P2PRow, P2PTable, Parameter

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

def plausible_comp(val):
    return -500.0 <= val <= 250.0  # Some older V8 engines have deep negative scaling

def plausible_torque(x: float) -> bool:
    return -4000 <= x <= 10000

def parse_torque_tables(data: bytes) -> List[TorqueTable]:
    from .constants import SIG_ROW_I_FLEX, HASH_TORQUE
    tables = []
    
    valid_starts = []
    
    # 1. Normal blocks: look for HASH_TORQUE preceded by 0x24
    for pos in find_all(data, HASH_TORQUE):
        if pos > 0 and data[pos-1] == 0x24:
            marker_pos = pos - 1
            if marker_pos + 7 <= len(data):
                suffix = data[pos+4:pos+6]
                valid_starts.append((marker_pos, suffix, None))
                
    # 2. Flexible anomaly blocks (explicit RPM before the 0x24 marker)
    for pos in find_all(data, SIG_ROW_I_FLEX):
        if pos >= 4:
            rpm_bytes = data[pos-4:pos]
            try:
                rpm, = struct.unpack('<I', rpm_bytes)
                if 0 < rpm <= 25000:
                    valid_starts.append((pos - 4, b'flex', SIG_ROW_I_FLEX))
            except struct.error:
                pass
                
    valid_starts.sort(key=lambda x: x[0])
    last_parsed_byte = 0
    
    for off0, suffix, exact_sig in valid_starts:
        if off0 < last_parsed_byte: continue
        
        rows = []
        q = 0
        
        if suffix == b'\x83\x02': # 0rpm
            p = off0 + 7
            if p + ROW0_STRUCT.size <= len(data):
                b0, comp0, tq0 = ROW0_STRUCT.unpack_from(data, p)
                if plausible_comp(comp0) and plausible_torque(tq0):
                    rows.append(TorqueRow(0.0, comp0, tq0, off0, '0rpm'))
                    q = p + ROW0_STRUCT.size
                else: continue
            else: continue
        elif suffix == b'\x03\x02': # 0rpm_alt
            p = off0 + 7
            if p + ROW0_ALT_STRUCT.size <= len(data):
                b0, b1, comp0 = ROW0_ALT_STRUCT.unpack_from(data, p)
                if plausible_comp(comp0):
                    rows.append(TorqueRow(0.0, comp0, None, off0, '0rpm_alt'))
                    q = p + ROW0_ALT_STRUCT.size
                else: continue
            else: continue
        elif suffix == b'flex': # row_i_flex
            p = off0 + 4 + len(exact_sig)
            if p + 9 <= len(data):
                b0, comp, tq = struct.unpack_from('<Bff', data, p)
                rpm_val = struct.unpack_from('<I', data, off0)[0]
                if plausible_comp(comp) and plausible_torque(tq):
                    row = TorqueRow(float(rpm_val), comp, tq, off0, 'row_i')
                    row.exact_signature = exact_sig + bytes([b0])
                    rows.append(row)
                    q = p + 9
                else: continue
            else: continue
        elif suffix == b'\x93\x02': # row_i_native
            p = off0 + 7
            if p + ROWI_STRUCT.size <= len(data):
                rpm_i, comp, tq = ROWI_STRUCT.unpack_from(data, p)
                rpm = float(rpm_i)
                if plausible_rpm(rpm) and plausible_comp(comp) and plausible_torque(tq):
                    rows.append(TorqueRow(rpm, comp, tq, off0, 'row_i'))
                    q = p + ROWI_STRUCT.size
                else: continue
            else: continue
        elif suffix == b'\xa3\x02': # row_f_native
            p = off0 + 7
            if p + ROWF_STRUCT.size <= len(data):
                rpm_i, comp, tq = ROWF_STRUCT.unpack_from(data, p)
                rpm = float(rpm_i)
                if plausible_rpm(rpm) and plausible_comp(comp) and plausible_torque(tq):
                    rows.append(TorqueRow(rpm, comp, tq, off0, 'row_f'))
                    q = p + ROWF_STRUCT.size
                else: continue
            else: continue
        else:
            continue
            
        while q < len(data):
            if data[q:q+1] == b'\x24' and data[q+1:q+5] == HASH_TORQUE:
                suf = data[q+5:q+7]
                if suf in (b'\x83\x02', b'\x03\x02'):
                    break # next table
                
                sig_off = q
                q += 7
                
                if suf == b'\x93\x02': # row_i
                    if q + ROWI_STRUCT.size > len(data): break
                    rpm_i, comp, tq = ROWI_STRUCT.unpack_from(data, q)
                    rpm = float(rpm_i)
                    if not (plausible_rpm(rpm) and plausible_comp(comp) and plausible_torque(tq)): break
                    rows.append(TorqueRow(rpm, comp, tq, sig_off, 'row_i'))
                    q += ROWI_STRUCT.size
                elif suf == b'\xa3\x02': # row_f
                    if q + ROWF_STRUCT.size > len(data): break
                    rpm, comp, tq = ROWF_STRUCT.unpack_from(data, q)
                    if not (plausible_rpm(rpm) and plausible_comp(comp) and plausible_torque(tq)): break
                    rows.append(TorqueRow(rpm, comp, tq, sig_off, 'row_f'))
                    q += ROWF_STRUCT.size
                elif suf == b'\x93\x00': # endvar
                    if q + ENDVAR_STRUCT.size > len(data): break
                    rpm_i, comp, b = ENDVAR_STRUCT.unpack_from(data, q)
                    rows.append(TorqueRow(float(rpm_i), comp, None, sig_off, 'endvar'))
                    q += ENDVAR_STRUCT.size
                    break
                else:
                    break
            else:
                if (q+4+len(SIG_ROW_I_FLEX)) <= len(data) and data[q+4:q+4+len(SIG_ROW_I_FLEX)] == SIG_ROW_I_FLEX:
                    sig_off = q
                    fuzz_sig = SIG_ROW_I_FLEX
                    rpm_i = struct.unpack_from('<I', data, sig_off)[0]
                    
                    q += 4 + len(fuzz_sig)
                    if q + 9 > len(data): break
                    b0, comp, tq = struct.unpack_from('<Bff', data, q)
                    
                    rpm = float(rpm_i)
                    if not (plausible_rpm(rpm) and plausible_comp(comp) and plausible_torque(tq)): break
                    
                    row = TorqueRow(rpm, comp, tq, sig_off, 'row_i')
                    row.exact_signature = fuzz_sig + bytes([b0])
                    rows.append(row)
                    q += 9
                else:
                    break
                    
        if len(rows) >= 2:
            rows.sort(key=lambda r: r.rpm)
            tables.append(TorqueTable(off0, rows))
            last_parsed_byte = q

    return tables

def parse_boost_tables(data: bytes) -> List[BoostTable]:
    from .constants import HASH_BOOST
    tables = []
    valid_0rpm = [b'\x06\xaa', b'\x06\x2a', b'\x86\xaa', b'\x86\x2a']
    last_parsed_byte = 0
    
    for pos in find_all(data, HASH_BOOST):
        if pos > 0 and data[pos-1] == 0x24:
            marker_pos = pos - 1
            if marker_pos < last_parsed_byte: continue
            if marker_pos + 7 <= len(data):
                suffix = data[pos+4:pos+6]
                if suffix in valid_0rpm:
                    rows = []
                    p = marker_pos + 7
                    
                    if suffix in (b'\x86\xaa', b'\x86\x2a'): # 5-float
                        if p + BOOST_5F_STRUCT.size > len(data): continue
                        b0, t0, t25, t50, t75, t100 = BOOST_5F_STRUCT.unpack_from(data, p)
                        kind = 'boost_0rpm_5f'
                        q = p + BOOST_5F_STRUCT.size
                    else: # 4-float
                        if p + BOOST_4F_STRUCT.size > len(data): continue
                        b0, t0, t25, t50, t75 = BOOST_4F_STRUCT.unpack_from(data, p)
                        t100 = None
                        kind = 'boost_0rpm_4f'
                        q = p + BOOST_4F_STRUCT.size
                        
                    if not all(0.5 <= v <= 3.0 for v in [t0, t25, t50, t75]):
                        continue
                        
                    rows.append(BoostRow(0.0, t0, t25, t50, t75, t100, marker_pos, kind))
                    
                    while q < len(data):
                        if data[q:q+1] == b'\x24' and data[q+1:q+5] == HASH_BOOST:
                            suf = data[q+5:q+7]
                            if suf in valid_0rpm:
                                break
                            
                            sig_off = q
                            q += 7
                            
                            if suf == b'\x96\xaa': # 5-float
                                if q + BOOST_I_5F_STRUCT.size > len(data): break
                                rpm, t0, t25, t50, t75, t100 = BOOST_I_5F_STRUCT.unpack_from(data, q)
                                kind = 'boost_row_5f'
                                q += BOOST_I_5F_STRUCT.size
                            elif suf == b'\x16\xaa': # 4-float
                                if q + BOOST_I_4F_STRUCT.size > len(data): break
                                rpm, b1, t0, t25, t50, t75 = BOOST_I_4F_STRUCT.unpack_from(data, q)
                                t100 = None
                                kind = 'boost_row_4f'
                                q += BOOST_I_4F_STRUCT.size
                            elif suf == b'\x16\x00': # 5-byte
                                if q + BOOST_I_5B_STRUCT.size > len(data): break
                                rpm, b1, b2, b3, b4, b5 = BOOST_I_5B_STRUCT.unpack_from(data, q)
                                t0=t25=t50=t75=t100=None
                                kind = 'boost_row_5b'
                                q += BOOST_I_5B_STRUCT.size
                            else:
                                break
                                
                            if rpm < 0 or rpm > 25000: break
                            rows.append(BoostRow(float(rpm), t0 if t0 else 0, t25 if t25 else 0, t50 if t50 else 0, t75 if t75 else 0, t100, sig_off, kind))
                        else:
                            break
                            
                    if len(rows) >= 2:
                        rows.sort(key=lambda r: r.rpm)
                        tables.append(BoostTable(marker_pos, rows))
                        last_parsed_byte = q
                        
    return tables

def parse_p2p_tables(data: bytes) -> List[P2PTable]:
    from .constants import HASH_P2P
    tables = []
    last_parsed_byte = 0
    
    for pos in find_all(data, HASH_P2P):
        if pos > 0 and data[pos-1] == 0x24:
            marker_pos = pos - 1
            if marker_pos < last_parsed_byte: continue
            if marker_pos + 7 <= len(data):
                rows = []
                q = marker_pos
                while q < len(data):
                    if data[q:q+1] == b'\x24' and data[q+1:q+5] == HASH_P2P:
                        suf = data[q+5:q+7]
                        sig_off = q
                        q += 7
                        
                        if suf == b'\x04\x08':
                            if q + P2P_FULL_STRUCT.size > len(data): break
                            mode, rpm_x, thr_y, mult_v = P2P_FULL_STRUCT.unpack_from(data, q)
                            kind = 'p2p_full'
                            pad = 0
                            q += P2P_FULL_STRUCT.size
                        elif suf == b'\x04\x00':
                            if q + P2P_ZERO_STRUCT.size > len(data): break
                            mode, rpm_x, thr_y, pad = P2P_ZERO_STRUCT.unpack_from(data, q)
                            mult_v = 0.0
                            kind = 'p2p_zero'
                            q += P2P_ZERO_STRUCT.size
                        else:
                            break
                            
                        if mode not in (0, 1, 2, 3, 4, 5): break
                        if not (0 <= rpm_x <= 100): break
                        if not (0 <= thr_y <= 100): break
                        
                        rows.append(P2PRow(mode, float(rpm_x), float(thr_y), float(mult_v), sig_off, kind, pad))
                    else:
                        break
                        
                if len(rows) > 0:
                    tables.append(P2PTable(marker_pos, rows))
                    last_parsed_byte = q
                    
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
