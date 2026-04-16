"""
AMS2 EDF File Editor v0.5 — Monolithic Distribution Build
==========================================================
Single-file version for easy command-line use.
Auto-generated from modular src/ tree.
"""
import struct
import ctypes
import sys
import os
import logging
import csv
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from dataclasses import dataclass
from typing import Tuple, Optional, List, Union, Generator, Callable, Dict
from pathlib import Path
try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    from matplotlib.figure import Figure
    from matplotlib.lines import Line2D
except ImportError:
    pass

# Windows High DPI awareness (FR11) — must be called before any Tkinter init
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

logger = logging.getLogger(__name__)



# ======================================================================
# constants.py
# ======================================================================


# -------- Signatures (little-endian) --------
SIG_0RPM   = b'\x24\x8B\x0A\xB7\x71\x83\x02'  # byte, float, float
SIG_ROW_I  = b'\x24\x8B\x0A\xB7\x71\x93\x02'  # int32, float, float
SIG_ROW_F  = b'\x24\x8B\x0A\xB7\x71\xA3\x02'  # float, float, float
SIG_ENDVAR = b'\x24\x8B\x0A\xB7\x71\x93\x00'  # int32, float, byte (rare)

# Boost table signatures
SIG_BOOST_0RPM = b'\x24\x51\x5F\x5E\x83\x86\xAA'  # byte, 5 floats (throttle positions)
SIG_BOOST_ROW  = b'\x24\x51\x5F\x5E\x83\x96\xAA'  # int32, 5 floats (throttle positions)

# Torque table structures
ROW0_STRUCT   = struct.Struct('<Bff')
ROWI_STRUCT   = struct.Struct('<iff')
ROWF_STRUCT   = struct.Struct('<fff')
ENDVAR_STRUCT = struct.Struct('<ifB')

# Boost table structures
BOOST0_STRUCT = struct.Struct('<Bfffff')  # byte + 5 floats
BOOSTI_STRUCT = struct.Struct('<ifffff')  # int32 + 5 floats

# Common single/dual-value parameter markers (per JDougNY notes)
# Format codes: 'f' float, 'i' int, 'b' byte, tuples represent sequences
PARAMS = {
    b'\x22\x4A\xE2\xDD\x6C': ('FuelConsumption', ('f',)),
    b'\x22\xD2\xA2\x92\x32': ('FuelEstimate',    ('f',)),
    b'\x22\x46\x65\xAE\x87': ('EngineInertia',   ('f',)),
    b'\x22\x40\xF1\xD2\xB9': ('Unknown_EngineFreeRevs', ('f',)),  # Makes engine rev out of control
    b'\x24\x4D\x23\x97\x54\xA2': ('IdleRPMLogic', ('f','f')),   # alt 52: int,int
    b'\x24\x4D\x23\x97\x54\x52': ('IdleRPMLogic', ('i','i')),
    b'\x22\x21\x98\x99\xAE': ('LaunchEfficiency', ('f',)),
    b'\x24\x79\x02\xB6\xBD\xA2': ('LaunchRPMLogic', ('f','f')),
    b'\x24\xDE\xA7\x2E\xB7\x23\x00': ('RevLimitRange', ('f','f','b')),  # float variant per edf-hex-map.xml
    b'\x24\xDE\xA7\x2E\xB7\x13\x00': ('RevLimitRange', ('i','b','b')),
    b'\x20\xA5\x5C\xC1\xC4': ('RevLimitSetting', ('b',)),  # Byte with value
    b'\x28\xA5\x5C\xC1\xC4': ('RevLimitSetting_NoValue', ()),  # No value variant
    b'\x22\x19\x66\x8A\xF9': ('RevLimitLogic',   ('f',)),
    b'\x24\x83\x15\x2F\x20\x03\x00': ('EngineFuelMapRange', ('b','b','b')),
    b'\x20\xC4\x44\x73\xF5': ('EngineFuelMapSetting', ('b',)),
    b'\x24\xBF\x84\x7C\xF1\xA3\x00': ('EngineBrakingMapRange', ('f','f','b')),
    b'\x20\xBE\x71\xED\x67': ('EngineBrakingMapSetting', ('b',)),
    b'\x22\xAF\xD7\x8A\xDD': ('OptimumOilTemp', ('f',)),
    b'\x22\x54\x10\x6D\xB1': ('CombustionHeat', ('f',)),
    b'\x22\xF6\xE3\x9F\xD9': ('EngineSpeedHeat', ('f',)),
    b'\x22\xB3\x0F\x25\xFC': ('OilMinimumCooling', ('f',)),
    b'\x24\xA7\x00\xD2\x3A\xA2': ('OilWaterHeatTransfer', ('f','f')),
    b'\x22\x67\x17\x15\x86': ('WaterMinimumCooling', ('f',)),
    b'\x24\x6A\xDA\x2B\x3A\xA2': ('RadiatorCooling', ('f','f')),
    # Unknown chunk signatures
    b'\x21\x3F\x6B\x7B\xE7\x82\x00': ('Unknown_Chunk_213F6B', ('b','b')),
    b'\x20\x6D\x47\xC1\xB2': ('Unknown_Chunk_206D47', ('b',)),
    # Lifetime parameters
    b'\x24\xD3\x94\x64\xAF\xA2': ('LifetimeEngineRPM', ('f','f')),
    b'\x24\xD3\x94\x64\xAF\x52': ('LifetimeEngineRPM', ('i','i')),
    b'\x24\x0A\xCE\xA8\x58\xA2': ('LifetimeOilTemp', ('f','f')),
    b'\x24\x05\x71\xC7\x19\xA2': ('Unknown_LMP_RWD_P30_A', ('f','f')),  # Present in LMP_RWD_P30
    b'\x22\xF7\x5F\x82\x2B': ('LifetimeAvg', ('f',)),
    b'\x22\x52\x7B\x76\xCD': ('LifetimeVar', ('f',)),
    b'\x24\xC1\xF4\x54\x3C\x83\x02': ('Unknown_LMP_RWD_P30_B', ('b','f','f')),  # Present in LMP_RWD_P30
    b'\x24\xCE\xB1\x75\x25\xA3\x02': ('EngineEmission', ('f','f','f')),
    b'\x20\x11\x8B\xA3\x81': ('OnboardStarter?', ('b',)),
    b'\x26\xAF\x00\xB3\xBA': ('EDF_UNKN_005', ('b',)),
    b'\x24\x52\x17\xFB\x41\xA3\x02': ('StarterTiming', ('f','f','f')),
    b'\x22\x92\xC7\xCD\x7C': ('Unknown_Float_3', ('f',)),  # Unknown with float 3.00
    # Air restrictor
    b'\x24\xFC\x89\xE8\x9C\xA3\x00': ('AirRestrictorRange', ('f','f','b')),
    b'\x20\xC5\xB4\x08\xFE': ('AirRestrictorSetting', ('b',)),
    b'\x28\xC5\xB4\x08\xFE': ('AirRestrictorSetting_NoValue', ()),  # No value variant
    # Other unknowns
    b'\x20\x2B\x3E\xD3\x40': ('Unknown_Byte_2B3ED340', ('b',)),
    b'\x22\xBA\x65\xDD\x60': ('Unknown_Float_6e-06', ('f',)),
    b'\x22\x81\x92\x17\xE0': ('Unknown_Float_295', ('f',)),
    # Old WasteGate parameters (replaced by boost control)
    b'\x24\x63\x23\x3A\x14\xA3\x00': ('WasteGateRange_OLD', ('f','f','b')),
    b'\x20\xDF\x86\x64\xFC': ('WasteGateSetting_OLD', ('b',)),
    b'\x28\xDF\x86\x64\xFC': ('WasteGateSetting_OLD_NoValue', ()),
    b'\x23\x00\x00\x50\xC3': ('Unknown_2300005', ('b','b')),
    # Boost control (current)
    b'\x24\xD7\x74\x45\x1A\x83\x00': ('BoostRange', ('b','f','b')),
    b'\x20\xCA\x2F\xD1\x34': ('BoostSetting', ('b',)),
    b'\x28\xCA\x2F\xD1\x34': ('BoostSetting_NoValue', ()),  # No value variant
}

ENGINE_LAYOUT_CODES = {
    b'\xD7\x50\x75\x68\xA3\x0A\x62': 'Single Cylinder (8B sequence)',
    b'\xC2\x2D\x3B': 'Flat 4 / 3 Rotor (per SMS)',
    b'\xD7\x2D\x3B': 'Straight 4',
    b'\xD7\x2C\x3B': 'Straight 5',
    b'\xD7\x2F\x3B': 'Straight 6',
    b'\xC2\x2F\x3B': 'Flat 6',
    b'\xD2\x21\x3B': 'V8 / Flat 8',
    b'\xD2\x28\x09\x2F': 'V12',
    b'\xD2\x28\x0B\x2F': 'V10',
}

# Human-readable field metadata for each parameter.
# Maps param name -> tuple of (label, type_display) per field.
PARAM_META = {
    'FuelConsumption':          (('Consumption', 'float'),),
    'FuelEstimate':             (('Estimate', 'float'),),
    'EngineInertia':            (('Inertia (kg·m²)', 'float'),),
    'Unknown_EngineFreeRevs':   (('Value', 'float'),),
    'IdleRPMLogic':             (('RPM Low', 'float/int'), ('RPM High', 'float/int')),
    'LaunchEfficiency':         (('Efficiency', 'float'),),
    'LaunchRPMLogic':           (('RPM 1', 'float'), ('RPM 2', 'float')),
    'RevLimitRange':            (('Limit (rpm)', 'float/int'), ('Max/Steps', 'float/int/byte'), ('Steps', 'byte')),
    'RevLimitSetting':          (('Setting', 'byte'),),
    'RevLimitSetting_NoValue':  (),
    'RevLimitLogic':            (('Value', 'float'),),
    'EngineFuelMapRange':       (('Min', 'byte'), ('Max', 'byte'), ('Steps', 'byte')),
    'EngineFuelMapSetting':     (('Map Index', 'byte'),),
    'EngineBrakingMapRange':    (('Min', 'float'), ('Max', 'float'), ('Steps', 'byte')),
    'EngineBrakingMapSetting':  (('Map Index', 'byte'),),
    'OptimumOilTemp':           (('Temp (°C)', 'float'),),
    'CombustionHeat':           (('Heat', 'float'),),
    'EngineSpeedHeat':          (('Heat', 'float'),),
    'OilMinimumCooling':        (('Cooling', 'float'),),
    'OilWaterHeatTransfer':     (('K1', 'float'), ('K2', 'float')),
    'WaterMinimumCooling':      (('Cooling', 'float'),),
    'RadiatorCooling':          (('K1', 'float'), ('K2', 'float')),
    'Unknown_Chunk_213F6B':     (('Byte 1', 'byte'), ('Byte 2', 'byte')),
    'Unknown_Chunk_206D47':     (('Value', 'byte'),),
    'LifetimeEngineRPM':        (('Avg (rpm)', 'float/int'), ('Max (rpm)', 'float/int')),
    'LifetimeOilTemp':          (('Avg (°C)', 'float'), ('Max (°C)', 'float')),
    'Unknown_LMP_RWD_P30_A':   (('Value 1', 'float'), ('Value 2', 'float')),
    'LifetimeAvg':              (('Average', 'float'),),
    'LifetimeVar':              (('Variance', 'float'),),
    'Unknown_LMP_RWD_P30_B':   (('Byte', 'byte'), ('Float 1', 'float'), ('Float 2', 'float')),
    'EngineEmission':           (('E1', 'float'), ('E2', 'float'), ('E3', 'float')),
    'OnboardStarter?':          (('Present', 'byte'),),
    'EDF_UNKN_005':             (('Value', 'byte'),),
    'StarterTiming':            (('T1', 'float'), ('T2', 'float'), ('T3', 'float')),
    'Unknown_Float_3':          (('Value', 'float'),),
    'AirRestrictorRange':       (('Min', 'float'), ('Max', 'float'), ('Steps', 'byte')),
    'AirRestrictorSetting':     (('Setting', 'byte'),),
    'AirRestrictorSetting_NoValue': (),
    'Unknown_Byte_2B3ED340':    (('Value', 'byte'),),
    'Unknown_Float_6e-06':      (('Value', 'float'),),
    'Unknown_Float_295':        (('Value', 'float'),),
    'WasteGateRange_OLD':       (('Min', 'float'), ('Max', 'float'), ('Steps', 'byte')),
    'WasteGateSetting_OLD':     (('Setting', 'byte'),),
    'WasteGateSetting_OLD_NoValue': (),
    'Unknown_2300005':          (('Byte 1', 'byte'), ('Byte 2', 'byte')),
    'BoostRange':               (('Min', 'byte'), ('Max (bar)', 'float'), ('Steps', 'byte')),
    'BoostSetting':             (('Setting', 'byte'),),
    'BoostSetting_NoValue':     (),
}


# ======================================================================
# models.py
# ======================================================================


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



# ======================================================================
# parser.py
# ======================================================================



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


# ======================================================================
# writer.py
# ======================================================================



def write_torque_row(data: bytearray, row: TorqueRow) -> None:
    """
    Writes all torque row values back to the binary data.
    Handles 0rpm, row_i, row_f, and endvar kinds.
    """
    if row.kind == '0rpm':
        if row.torque is None:
            return
        data_offset = row.offset + len(SIG_0RPM)
        # Preserve the leading byte
        b0 = data[data_offset]
        struct.pack_into('<Bff', data, data_offset, b0, row.compression, row.torque)

    elif row.kind == 'row_i':
        if row.torque is None:
            return
        data_offset = row.offset + len(SIG_ROW_I)
        struct.pack_into('<iff', data, data_offset, int(row.rpm), row.compression, row.torque)

    elif row.kind == 'row_f':
        if row.torque is None:
            return
        data_offset = row.offset + len(SIG_ROW_F)
        struct.pack_into('<fff', data, data_offset, row.rpm, row.compression, row.torque)

    elif row.kind == 'endvar':
        data_offset = row.offset + len(SIG_ENDVAR)
        # ENDVAR_STRUCT is <ifB: (int rpm, float compression, byte)
        # Preserve the trailing byte
        trailing_byte = data[data_offset + ENDVAR_STRUCT.size - 1]
        struct.pack_into('<ifB', data, data_offset, int(row.rpm), row.compression, trailing_byte)


def write_boost_row(data: bytearray, row: BoostRow) -> None:
    """
    Writes boost row values back to the binary data.
    Handles boost_0rpm and boost_row kinds.
    """
    if row.kind == 'boost_0rpm':
        data_offset = row.offset + len(SIG_BOOST_0RPM)
        # BOOST0_STRUCT is <Bfffff: (byte, 5 floats)
        # Preserve the leading byte
        b0 = data[data_offset]
        struct.pack_into('<Bfffff', data, data_offset, b0, row.t0, row.t25, row.t50, row.t75, row.t100)

    elif row.kind == 'boost_row':
        data_offset = row.offset + len(SIG_BOOST_ROW)
        # BOOSTI_STRUCT is <ifffff: (int rpm, 5 floats)
        struct.pack_into('<ifffff', data, data_offset, int(row.rpm), row.t0, row.t25, row.t50, row.t75, row.t100)


def write_param(data: bytearray, param: Parameter) -> None:
    """
    Writes the parameter values back to the binary data.
    """
    sig_len = 0
    fmt: Tuple[str, ...] = tuple()

    if param.fmt:
        fmt = param.fmt
        for sig, (pname, pfmt) in PARAMS.items():
            if pname == param.name:
                sig_len = len(sig)
                break
    else:
        for sig, (pname, pfmt) in PARAMS.items():
            if pname == param.name:
                sig_len = len(sig)
                fmt = pfmt
                break

    if not fmt:
        return

    data_offset = param.offset + sig_len

    cur = data_offset
    for i, f in enumerate(fmt):
        val = param.values[i]
        if f == 'f':
            struct.pack_into('<f', data, cur, float(val))
            cur += 4
        elif f == 'i':
            struct.pack_into('<i', data, cur, int(val))
            cur += 4
        elif f == 'b':
            struct.pack_into('B', data, cur, int(val))
            cur += 1


def scale_torque_tables(data: bytearray, tables: List[TorqueTable], factor: float) -> None:
    """
    Scales all torque values in the provided tables by a factor.
    Updates both the binary data AND the table objects in-place.
    """
    for table in tables:
        for row in table.rows:
            if row.torque is not None:
                row.torque *= factor
                write_torque_row(data, row)


# ======================================================================
# formatting.py
# ======================================================================

"""Shared formatting utilities for float display."""



def format_float(val: float, decimals: int = 6) -> str:
    """Format a float using fixed-point notation (never scientific).

    Args:
        val: The float value to format.
        decimals: Number of decimal places (default 6).

    Returns:
        A string like '123.456000', never '1.23e+02'.
    """
    return f"{val:.{decimals}f}"


def quantise_f32(val: float) -> float:
    """Quantise a Python float64 to the nearest IEEE 754 float32 value.

    This ensures the value displayed to the user matches exactly what
    will be stored in the EDF binary (which uses 4-byte floats).

    Args:
        val: The float64 value to quantise.

    Returns:
        The nearest representable float32 value, as a Python float.
    """
    return struct.unpack('<f', struct.pack('<f', val))[0]


# ======================================================================
# plotting.py
# ======================================================================




# Color schemes shared across plot modes
TORQUE_COLORS = ['#1f77b4', '#2ca02c', '#9467bd', '#8c564b']
POWER_COLORS = ['#ff7f0e', '#ff9f3f', '#ffbf7f', '#ffd9a6']


def _ensure_matplotlib():
    """
    Attempts to import matplotlib. Raises ImportError if not found.
    """
    try:
        import matplotlib.pyplot as plt
        return plt
    except ImportError:
        logger.error("Matplotlib not found.")
        raise ImportError("matplotlib is required for plotting.\nInstall it with: pip install matplotlib")


def extract_curve_data(table: TorqueTable) -> Tuple[List[float], List[float], List[float], List[float]]:
    """Extract plottable data arrays from a single TorqueTable.

    Skips endvar rows (where torque is None).

    Args:
        table: A TorqueTable with rows to extract.

    Returns:
        Tuple of (rpms, torques, compressions, powers_kw).
        All lists are the same length. Power = Torque × RPM / 9549.3.
    """
    rpms = []
    torques = []
    compressions = []
    powers = []

    for row in table.rows:
        if row.torque is not None:
            rpms.append(row.rpm)
            torques.append(row.torque)
            compressions.append(row.compression)
            powers.append((row.torque * row.rpm) / 9549.3)

    return rpms, torques, compressions, powers


def plot_torque_rpm(tables: List[TorqueTable], filename: str = "EDF File"):
    """
    Plots Torque (Nm) and Power (kW) vs RPM.
    """
    if not tables:
        logger.warning("No tables to plot")
        return

    plt = _ensure_matplotlib()
    
    fig, ax1 = plt.subplots(figsize=(10, 6))
    
    # Create second y-axis for power
    ax2 = ax1.twinx()
    
    for t_idx, table in enumerate(tables):
        rpms, torques, _comps, powers = extract_curve_data(table)
        
        if rpms:
            torque_color = TORQUE_COLORS[t_idx % len(TORQUE_COLORS)]
            power_color = POWER_COLORS[t_idx % len(POWER_COLORS)]
            
            # Plot torque on left axis
            ax1.plot(rpms, torques, marker='o', label=f'Table {t_idx} Torque @ 0x{table.offset:X}', 
                            linewidth=2, markersize=4, color=torque_color)
            # Plot power on right axis (dashed line, orange shades)
            ax2.plot(rpms, powers, marker='s', label=f'Table {t_idx} Power @ 0x{table.offset:X}', 
                            linewidth=2, markersize=4, linestyle='--', color=power_color)
    
    ax1.set_xlabel('RPM', fontsize=12)
    ax1.set_ylabel('Torque (Nm)', fontsize=12, color='tab:blue')
    ax1.tick_params(axis='y', labelcolor='tab:blue')
    ax2.set_ylabel('Power (kW)', fontsize=12, color='tab:orange')
    ax2.tick_params(axis='y', labelcolor='tab:orange')
    
    ax1.set_title(f'Torque & Power vs RPM - {Path(filename).name}', fontsize=14)
    ax1.grid(True, alpha=0.3)
    
    # Combine legends from both axes
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='best')
    
    plt.tight_layout()
    plt.show()

def plot_compression_rpm(tables: List[TorqueTable], filename: str = "EDF File"):
    """
    Plots Compression vs RPM.
    """
    if not tables:
        logger.warning("No tables to plot")
        return

    plt = _ensure_matplotlib()
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    for t_idx, table in enumerate(tables):
        rpms, _torques, comps, _powers = extract_curve_data(table)
        
        if rpms:
            ax.plot(rpms, comps, marker='o', label=f'Table {t_idx} @ 0x{table.offset:X}', linewidth=2, markersize=4)
    
    ax.set_xlabel('RPM', fontsize=12)
    ax.set_ylabel('Compression (-Nm)', fontsize=12)
    ax.set_title(f'Compression vs RPM - {Path(filename).name}', fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()
    plt.show()

def plot_both(tables: List[TorqueTable], filename: str = "EDF File"):
    """
    Plots both (Torque/Power vs RPM) and (Compression vs RPM) side-by-side.
    """
    if not tables:
        logger.warning("No tables to plot")
        return

    plt = _ensure_matplotlib()
    
    fig, (ax1, ax3) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Create second y-axis for power on left plot
    ax2 = ax1.twinx()
    
    for t_idx, table in enumerate(tables):
        rpms, torques, comps, powers = extract_curve_data(table)
        
        if rpms:
            label = f'Table {t_idx} @ 0x{table.offset:X}'
            torque_color = TORQUE_COLORS[t_idx % len(TORQUE_COLORS)]
            power_color = POWER_COLORS[t_idx % len(POWER_COLORS)]
            
            # Left plot: Torque and Power
            ax1.plot(rpms, torques, marker='o', label=f'Table {t_idx} Torque', 
                    linewidth=2, markersize=4, color=torque_color)
            ax2.plot(rpms, powers, marker='s', label=f'Table {t_idx} Power', 
                    linewidth=2, markersize=4, linestyle='--', color=power_color)
            # Right plot: Compression
            ax3.plot(rpms, comps, marker='o', label=label, linewidth=2, markersize=4)
    
    # Configure left plot
    ax1.set_xlabel('RPM', fontsize=12)
    ax1.set_ylabel('Torque (Nm)', fontsize=12, color='tab:blue')
    ax1.tick_params(axis='y', labelcolor='tab:blue')
    ax2.set_ylabel('Power (kW)', fontsize=12, color='tab:orange')
    ax2.tick_params(axis='y', labelcolor='tab:orange')
    ax1.set_title('Torque & Power vs RPM', fontsize=13)
    ax1.grid(True, alpha=0.3)
    
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='best', fontsize=9)
    
    # Configure right plot
    ax3.set_xlabel('RPM', fontsize=12)
    ax3.set_ylabel('Compression (-Nm)', fontsize=12)
    ax3.set_title('Compression vs RPM', fontsize=13)
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    fig.suptitle(f'{Path(filename).name}', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.show()



# ======================================================================
# interactive_plot.py
# ======================================================================

"""Interactive drag-editable torque/compression plot.

This module provides the DraggableTorquePlot class, which embeds a
matplotlib figure in a Tkinter Toplevel window with full drag-to-edit
support for torque and compression curves.

Key features:
  - Click-and-drag torque/compression markers vertically
  - Real-time curve + power recalculation during drag
  - Float32 quantisation on every frame
  - Undo stack (Ctrl+Z) with atomic transactions
  - Modifier keys: Shift = fine (÷10), Ctrl = snap to 10 Nm
  - Proportional compression scaling on torque drag
"""





# Clamping ranges (from spec FR-009)
TORQUE_MIN, TORQUE_MAX = -4000.0, 10000.0
COMPRESSION_MIN, COMPRESSION_MAX = -300.0, 300.0

# Undo stack depth (from spec FR-024)
UNDO_STACK_MAX = 50

# Hit-test tolerance in pixels (from spec FR-025)
PICKER_TOLERANCE = 7


class DraggableTorquePlot:
    """Interactive plot window for dragging torque/compression points.

    Creates a Tkinter Toplevel with an embedded matplotlib figure.
    Points are draggable vertically; changes propagate to the EDF
    binary via the on_row_changed callback on mouse-up.

    Args:
        parent: The main Tk application window.
        tables: List of parsed TorqueTable objects.
        data: The in-memory EDF bytearray.
        filename: Filename for the title bar.
        on_row_changed: Callback(row: TorqueRow) invoked after each drag commit.
        on_close: Callback() invoked when the plot window is closed.
        mode: "torque" or "compression" — which curve is draggable.
    """

    def __init__(
        self,
        parent: tk.Tk,
        tables: List[TorqueTable],
        data: bytearray,
        filename: str,
        on_row_changed: Callable[[TorqueRow], None],
        on_close: Callable[[], None],
        mode: str = "torque",
    ):
        self.parent = parent
        self.tables = tables
        self.data = data
        self.filename = filename
        self.on_row_changed = on_row_changed
        self._on_close_callback = on_close
        self.mode = mode

        # ── Drag state ──────────────────────────────────────────────
        self._dragging = False
        self._drag_line: Optional[Line2D] = None      # The line artist being dragged
        self._drag_point_idx: Optional[int] = None     # Index within the line's data arrays
        self._drag_table_idx: Optional[int] = None     # Which table owns this line
        self._drag_row: Optional[TorqueRow] = None     # The TorqueRow being modified
        self._drag_start_x: Optional[float] = None     # Original RPM (locked during drag)
        self._drag_start_y: Optional[float] = None     # Original value before drag
        self._drag_start_torque: Optional[float] = None
        self._drag_start_compression: Optional[float] = None
        self._original_markersize: Optional[float] = None

        # ── Undo stack ──────────────────────────────────────────────
        self._undo_stack: List[DragTransaction] = []

        # ── Line → table mapping ───────────────────────────────────
        # Maps line artist id → (table_index, list of draggable TorqueRow refs)
        self._line_table_map: Dict[int, Tuple[int, List[TorqueRow]]] = {}

        # ── Build window ────────────────────────────────────────────
        self._build_window()
        self._plot_curves()
        self._connect_events()

    # ════════════════════════════════════════════════════════════════
    # Window construction
    # ════════════════════════════════════════════════════════════════

    def _build_window(self):
        """Create the Toplevel, Figure, Canvas, and Toolbar."""
        self.toplevel = tk.Toplevel(self.parent)
        mode_label = "Torque & Power" if self.mode == "torque" else "Compression"
        self.toplevel.title(f"Interactive {mode_label} — {self.filename}")
        self.toplevel.geometry("1100x650")
        self.toplevel.protocol("WM_DELETE_WINDOW", self._on_window_close)

        self.fig = Figure(figsize=(10, 6), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.toplevel)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.toolbar = NavigationToolbar2Tk(self.canvas, self.toplevel)
        self.toolbar.update()

        # Undo keybinding
        self.toplevel.bind('<Control-z>', lambda e: self._undo())

        # Annotation for value tooltip (initially hidden)
        self._annotation = None  # Created after axes exist

    def _plot_curves(self):
        """Draw the initial curves with picker-enabled markers."""
        self.fig.clear()

        if self.mode == "torque":
            self._plot_torque_mode()
        else:
            self._plot_compression_mode()

        self.canvas.draw()

    def _plot_torque_mode(self):
        """Plot Torque & Power vs RPM with draggable torque markers."""
        self.ax1 = self.fig.add_subplot(111)
        self.ax2 = self.ax1.twinx()

        for t_idx, table in enumerate(self.tables):
            rpms, torques, _comps, powers = extract_curve_data(table)
            # Build list of draggable rows (skip endvar)
            draggable_rows = [r for r in table.rows if r.torque is not None]

            if rpms:
                tc = TORQUE_COLORS[t_idx % len(TORQUE_COLORS)]
                pc = POWER_COLORS[t_idx % len(POWER_COLORS)]

                # Torque line — DRAGGABLE (picker enabled)
                line_t, = self.ax1.plot(
                    rpms, torques,
                    marker='o', linewidth=2, markersize=6,
                    color=tc, picker=PICKER_TOLERANCE,
                    label=f'Table {t_idx} Torque',
                )
                self._line_table_map[id(line_t)] = (t_idx, draggable_rows)

                # Power line — NOT draggable (no picker)
                self.ax2.plot(
                    rpms, powers,
                    marker='s', linewidth=2, markersize=4,
                    linestyle='--', color=pc,
                    label=f'Table {t_idx} Power',
                )

        self.ax1.set_xlabel('RPM', fontsize=12)
        self.ax1.set_ylabel('Torque (Nm)', fontsize=12, color='tab:blue')
        self.ax1.tick_params(axis='y', labelcolor='tab:blue')
        self.ax2.set_ylabel('Power (kW)', fontsize=12, color='tab:orange')
        self.ax2.tick_params(axis='y', labelcolor='tab:orange')
        self.ax1.set_title(f'Interactive Torque & Power — drag points vertically', fontsize=13)
        self.ax1.grid(True, alpha=0.3)

        lines1, labels1 = self.ax1.get_legend_handles_labels()
        lines2, labels2 = self.ax2.get_legend_handles_labels()
        self.ax1.legend(lines1 + lines2, labels1 + labels2, loc='best', fontsize=9)

        # Create annotation (hidden)
        self._annotation = self.ax1.annotate(
            '', xy=(0, 0), fontsize=10, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.85),
            visible=False,
        )

    def _plot_compression_mode(self):
        """Plot Compression vs RPM with draggable compression markers."""
        self.ax1 = self.fig.add_subplot(111)
        self.ax2 = None  # No secondary axis for compression

        for t_idx, table in enumerate(self.tables):
            rpms, _torques, comps, _powers = extract_curve_data(table)
            draggable_rows = [r for r in table.rows if r.torque is not None]

            if rpms:
                line_c, = self.ax1.plot(
                    rpms, comps,
                    marker='o', linewidth=2, markersize=6,
                    picker=PICKER_TOLERANCE,
                    label=f'Table {t_idx} Compression',
                )
                self._line_table_map[id(line_c)] = (t_idx, draggable_rows)

        self.ax1.set_xlabel('RPM', fontsize=12)
        self.ax1.set_ylabel('Compression (-Nm)', fontsize=12)
        self.ax1.set_title('Interactive Compression — drag points vertically', fontsize=13)
        self.ax1.grid(True, alpha=0.3)
        self.ax1.legend(loc='best', fontsize=9)

        self._annotation = self.ax1.annotate(
            '', xy=(0, 0), fontsize=10, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', alpha=0.85),
            visible=False,
        )

    # ════════════════════════════════════════════════════════════════
    # Event handling
    # ════════════════════════════════════════════════════════════════

    def _connect_events(self):
        """Connect matplotlib events to handler methods."""
        self._cid_press = self.canvas.mpl_connect('button_press_event', self._on_press)
        self._cid_motion = self.canvas.mpl_connect('motion_notify_event', self._on_motion)
        self._cid_release = self.canvas.mpl_connect('button_release_event', self._on_release)

    def _disconnect_events(self):
        """Disconnect matplotlib events."""
        for cid in (self._cid_press, self._cid_motion, self._cid_release):
            try:
                self.canvas.mpl_disconnect(cid)
            except Exception:
                pass

    def _on_press(self, event):
        """Handle mouse button press — select a draggable point."""
        valid_axes = [self.ax1]
        if getattr(self, "ax2", None) is not None:
            valid_axes.append(self.ax2)

        if event.inaxes not in valid_axes:
            return
        if event.button != 1:  # Left click only
            return

        # Hide annotation from previous drag
        if self._annotation:
            self._annotation.set_visible(False)

        # Find which line's point was clicked (topmost = last checked wins → FR-026)
        best_line = None
        best_idx = None

        for line in self.ax1.get_lines():
            if id(line) not in self._line_table_map:
                continue  # Skip non-draggable lines (e.g., power)

            contains, info = line.contains(event)
            if contains and 'ind' in info and len(info['ind']) > 0:
                # Take the nearest index
                best_line = line
                best_idx = info['ind'][0]

        if best_line is None:
            return

        # Resolve table and row
        table_idx, draggable_rows = self._line_table_map[id(best_line)]
        if best_idx >= len(draggable_rows):
            return

        row = draggable_rows[best_idx]

        # Don't allow dragging endvar rows (FR-011)
        if row.torque is None:
            return

        # Enter DRAGGING state
        self._dragging = True
        self._drag_line = best_line
        self._drag_point_idx = best_idx
        self._drag_table_idx = table_idx
        self._drag_row = row
        self._drag_start_x = best_line.get_xdata()[best_idx]
        self._drag_start_y = best_line.get_ydata()[best_idx]
        self._drag_start_torque = row.torque
        self._drag_start_compression = row.compression

        # Visual selection indicator (FR-013): enlarge marker
        self._original_markersize = best_line.get_markersize()
        best_line.set_markersize(self._original_markersize * 2)
        self.canvas.draw_idle()

    def _on_motion(self, event):
        """Handle mouse movement — update marker position during drag."""
        if not self._dragging:
            return
        valid_axes = [self.ax1]
        if getattr(self, "ax2", None) is not None:
            valid_axes.append(self.ax2)

        if event.inaxes not in valid_axes:
            return

        # Determine raw new Y value based on ax1 coords (since event.ydata might be ax2)
        _, new_y = self.ax1.transData.inverted().transform((event.x, event.y))

        # Apply modifier keys (FR-018)
        if hasattr(event, 'key') and event.key:
            if 'shift' in event.key:
                # Fine mode: reduce movement by 10x
                delta = new_y - self._drag_start_y
                new_y = self._drag_start_y + delta / 10.0
            elif 'control' in event.key:
                # Snap mode: round to nearest 10
                new_y = round(new_y / 10.0) * 10.0

        # Clamp (FR-009)
        if self.mode == "torque":
            new_y = max(TORQUE_MIN, min(TORQUE_MAX, new_y))
        else:
            new_y = max(COMPRESSION_MIN, min(COMPRESSION_MAX, new_y))

        # Quantise to float32 (FR-015)
        new_y = quantise_f32(new_y)

        # Update marker position — vertical only, RPM frozen (FR-002)
        xdata = list(self._drag_line.get_xdata())
        ydata = list(self._drag_line.get_ydata())
        ydata[self._drag_point_idx] = new_y
        # X stays at original RPM — never event.xdata
        self._drag_line.set_data(xdata, ydata)

        # If torque mode, recompute power curve on ax2
        if self.mode == "torque" and self.ax2 is not None:
            rpm = xdata[self._drag_point_idx]
            self._update_power_curve(self._drag_table_idx, self._drag_point_idx, rpm, new_y)

        # Update annotation (FR-008, FR-016)
        self._update_annotation(xdata[self._drag_point_idx], new_y, new_y)

        self.canvas.draw_idle()

    def _on_release(self, event):
        """Handle mouse button release — commit the drag."""
        if not self._dragging:
            return

        # Get final value from line data
        ydata = list(self._drag_line.get_ydata())
        final_y = ydata[self._drag_point_idx]
        final_y = quantise_f32(final_y)

        # Restore marker size (FR-013)
        if self._original_markersize is not None:
            self._drag_line.set_markersize(self._original_markersize)

        # Hide annotation
        if self._annotation:
            self._annotation.set_visible(False)

        # Compute new values
        row = self._drag_row
        old_torque = self._drag_start_torque
        old_compression = self._drag_start_compression

        if self.mode == "torque":
            new_torque = final_y
            # Proportional compression scaling (FR-031)
            if old_torque != 0:
                ratio = new_torque / old_torque
                new_compression = quantise_f32(old_compression * ratio)
            else:
                new_compression = old_compression  # T_old == 0 → freeze compression
            # Clamp compression independently
            new_compression = max(COMPRESSION_MIN, min(COMPRESSION_MAX, new_compression))
            new_compression = quantise_f32(new_compression)
        else:
            new_torque = old_torque  # Compression mode doesn't change torque (FR-033)
            new_compression = final_y

        # Create undo transaction (FR-023)
        txn = DragTransaction(
            table_index=self._drag_table_idx,
            row_index=self._find_row_index(self._drag_row),
            field=self.mode,
            start_torque=old_torque,
            end_torque=new_torque,
            start_compression=old_compression,
            end_compression=new_compression,
        )
        self._undo_stack.append(txn)
        if len(self._undo_stack) > UNDO_STACK_MAX:
            self._undo_stack = self._undo_stack[-UNDO_STACK_MAX:]

        # Update the TorqueRow in-place
        row.torque = new_torque
        row.compression = new_compression

        # Commit to binary via callback (FR-005, FR-006, FR-007)
        try:
            self.on_row_changed(row)
        except Exception as e:
            # FR-030: revert on write failure
            logger.error(f"Write-back failed: {e}")
            row.torque = old_torque
            row.compression = old_compression
            self._undo_stack.pop()
            self._replot_line(self._drag_table_idx)
            self.canvas.draw_idle()
            return

        # Exit DRAGGING state
        self._dragging = False
        self._drag_line = None
        self._drag_point_idx = None
        self._drag_table_idx = None
        self._drag_row = None

        self.canvas.draw_idle()

    # ════════════════════════════════════════════════════════════════
    # Undo
    # ════════════════════════════════════════════════════════════════

    def _undo(self):
        """Revert the last drag operation (FR-012)."""
        if not self._undo_stack:
            return

        txn = self._undo_stack.pop()

        # Find the row
        table = self.tables[txn.table_index]
        draggable_rows = [r for r in table.rows if r.torque is not None]
        if txn.row_index >= len(draggable_rows):
            return
        row = draggable_rows[txn.row_index]

        # Restore values
        row.torque = txn.start_torque
        row.compression = txn.start_compression

        # Commit reverted values to binary
        try:
            self.on_row_changed(row)
        except Exception as e:
            logger.error(f"Undo write-back failed: {e}")

        # Replot the affected table's line
        self._replot_line(txn.table_index)
        self.canvas.draw_idle()

    # ════════════════════════════════════════════════════════════════
    # Helpers
    # ════════════════════════════════════════════════════════════════

    def _find_row_index(self, row: TorqueRow) -> int:
        """Find the index of a row within its table's draggable rows."""
        if self._drag_table_idx is None:
            return 0
        table = self.tables[self._drag_table_idx]
        draggable = [r for r in table.rows if r.torque is not None]
        for i, r in enumerate(draggable):
            if r is row:
                return i
        return 0

    def _update_annotation(self, x: float, y: float, value: float):
        """Show/update the value annotation near the cursor."""
        if self._annotation is None:
            return
        unit = "Nm" if self.mode == "torque" else "-Nm"
        self._annotation.set_text(f"{value:.1f} {unit}")
        self._annotation.xy = (x, y)
        # Offset slightly so annotation doesn't cover the point
        self._annotation.xyann = (15, 15)
        self._annotation.set_visible(True)

    def _update_power_curve(self, table_idx: int, point_idx: int, rpm: float, torque: float):
        """Recompute and update the power curve for the given table."""
        # Find the power line for this table on ax2
        if self.ax2 is None:
            return

        power_lines = [l for l in self.ax2.get_lines()]
        if table_idx >= len(power_lines):
            return

        power_line = power_lines[table_idx]
        ydata = list(power_line.get_ydata())
        if point_idx < len(ydata):
            ydata[point_idx] = (torque * rpm) / 9549.3
            power_line.set_ydata(ydata)

    def _replot_line(self, table_idx: int):
        """Replot a specific table's line from current TorqueRow data."""
        table = self.tables[table_idx]
        rpms, torques, comps, powers = extract_curve_data(table)

        # Find the torque/compression line for this table
        for line in self.ax1.get_lines():
            if id(line) in self._line_table_map:
                t_idx, _ = self._line_table_map[id(line)]
                if t_idx == table_idx:
                    if self.mode == "torque":
                        line.set_data(rpms, torques)
                    else:
                        line.set_data(rpms, comps)
                    break

        # Update power line if in torque mode
        if self.mode == "torque" and self.ax2 is not None:
            power_lines = [l for l in self.ax2.get_lines()]
            if table_idx < len(power_lines):
                power_lines[table_idx].set_data(rpms, powers)

    def _on_window_close(self):
        """Handle plot window close — cancel drag, cleanup, notify app."""
        # FR-014: cancel in-progress drag
        if self._dragging and self._drag_row is not None:
            # Revert to pre-drag values
            self._drag_row.torque = self._drag_start_torque
            self._drag_row.compression = self._drag_start_compression
            self._dragging = False

        self._disconnect_events()
        self._on_close_callback()
        self.toplevel.destroy()


# ======================================================================
# hex_view.py
# ======================================================================


class HexView(tk.Text):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.config(state='disabled', font=("Courier", 10))
        self.tag_configure("highlight", background="yellow", foreground="black")
        
    def load_data(self, data: bytes):
        self.config(state='normal')
        self.delete('1.0', tk.END)
        
        # Format:
        # Offset   Hex................................  Ascii
        # 00000000 00 01 02 03 04 05 06 07  08 09 0A 0B 0C 0D 0E 0F  |................|
        
        lines = []
        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            
            # Hex part
            hex_part = []
            for j, b in enumerate(chunk):
                hex_part.append(f"{b:02X}")
                if j == 7: # Extra space
                    hex_part.append("")
            
            # Pad hex part if last line is short
            if len(chunk) < 16:
                padding = 16 - len(chunk)
                # 3 chars per byte + 1 space for 8th byte if missing
                # Actually simplest way is just to fill hex_part list
                pass
            
            hex_str = " ".join(hex_part).ljust(49) # 16*3 + 1 = 49
            
            # Ascii part
            ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            
            lines.append(f"{i:08X}  {hex_str}  |{ascii_part}|")
            
        self.insert('1.0', "\n".join(lines))
        self.config(state='disabled')
        
    def highlight_range(self, start: int, end: int):
        self.tag_remove("highlight", "1.0", tk.END)
        
        if start >= end:
            return
            
        # Convert offset to line.col
        # Each line represents 16 bytes
        # Line 1 corresponds to offset 0-15
        
        current_off = start
        while current_off < end:
            line_idx = (current_off // 16) + 1
            col_idx = current_off % 16
            
            # Calculate range on this line
            line_start_off = (line_idx - 1) * 16
            line_end_off = line_start_off + 16
            
            chunk_end = min(end, line_end_off)
            
            # Calculate text column positions
            # Offset (8) + 2 spaces = 10 chars
            # Each byte is 3 chars ("XX ")
            # Extra space after 8th byte (index 7)
            
            def get_text_col(byte_idx):
                col = 10 + (byte_idx * 3)
                if byte_idx >= 8:
                    col += 1
                return col
                
            start_col = get_text_col(col_idx)
            end_col = get_text_col(chunk_end - line_start_off)  # End is exclusive implies we want up to the start of next byte?
            # Actually we highlight the hex digits. "XX " is 3 chars. highlighting "XX" is 2 chars.
            # So end_col should be carefully calculated.
            
            # Simpler: highlight "XX " for each byte in range
            for b_idx in range(col_idx, chunk_end - line_start_off):
                c_start = get_text_col(b_idx)
                c_end = c_start + 2 # Highlight just the 2 digits
                self.tag_add("highlight", f"{line_idx}.{c_start}", f"{line_idx}.{c_end}")
            
            current_off = chunk_end
        
        self.see(f"{(start // 16) + 1}.0")


# ======================================================================
# dialogs.py
# ======================================================================



# Minimum entry width to fit any plausible float
_ENTRY_WIDTH = 40

class EditTorqueDialog(tk.Toplevel):
    def __init__(self, parent, row: TorqueRow, callback):
        super().__init__(parent)
        self.row = row
        self.callback = callback
        self.title("Edit Torque Row")
        self.transient(parent)
        self.grab_set()
        
        self.result: bool = False
        self._setup_ui()
        
        # Let Tkinter compute the natural size, then lock the minimum
        self.update_idletasks()
        self.minsize(self.winfo_reqwidth(), self.winfo_reqheight())
        
    def _setup_ui(self):
        pad = {'padx': 10, 'pady': 5}
        
        # RPM
        ttk.Label(self, text="RPM:").pack(**pad)
        self.rpm_var = tk.StringVar(value=format_float(self.row.rpm, 1))
        rpm_entry = ttk.Entry(self, textvariable=self.rpm_var, width=_ENTRY_WIDTH)
        rpm_entry.pack(**pad)
        if self.row.kind == '0rpm':
            rpm_entry.config(state='disabled')
            
        # Compression
        ttk.Label(self, text="Compression:").pack(**pad)
        self.comp_var = tk.StringVar(value=format_float(self.row.compression, 6))
        ttk.Entry(self, textvariable=self.comp_var, width=_ENTRY_WIDTH).pack(**pad)
        
        # Torque
        ttk.Label(self, text="Torque:").pack(**pad)
        self.tq_var = tk.StringVar(value=format_float(self.row.torque, 6) if self.row.torque is not None else "")
        ttk.Entry(self, textvariable=self.tq_var, width=_ENTRY_WIDTH).pack(**pad)
        
        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="Save", command=self.on_save).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side='left', padx=5)
        
    def on_save(self):
        try:
            new_rpm = float(self.rpm_var.get())
            new_comp = float(self.comp_var.get())
            new_tq = float(self.tq_var.get()) if self.tq_var.get() else None
            
            self.row.rpm = new_rpm
            self.row.compression = new_comp
            self.row.torque = new_tq
            
            self.result = True
            if self.callback:
                self.callback(self.row)
            self.destroy()
        except ValueError:
            messagebox.showerror("Error", "Invalid numeric value")

class EditParamDialog(tk.Toplevel):
    def __init__(self, parent, param: Parameter, callback):
        super().__init__(parent)
        self.param = param
        self.callback = callback
        self.title(f"Edit {param.name}")
        self.transient(parent)
        self.grab_set()
        
        self._setup_ui()
        
        # Let Tkinter compute the natural size, then lock the minimum
        self.update_idletasks()
        self.minsize(self.winfo_reqwidth(), self.winfo_reqheight())
        
    def _setup_ui(self):
        ttk.Label(self, text=f"Parameter: {self.param.name}").pack(pady=10)
        meta = PARAM_META.get(self.param.name, ())
        
        self.vars = []
        for i, val in enumerate(self.param.values):
            # Build label from PARAM_META if available
            if i < len(meta):
                label_text, type_str = meta[i]
                field_label = f"{label_text} [{type_str}]:"
            else:
                field_label = f"Value {i+1}:"
            ttk.Label(self, text=field_label).pack()
            if isinstance(val, float):
                display = format_float(val, 6)
            else:
                display = str(val)
            v = tk.StringVar(value=display)
            self.vars.append(v)
            ttk.Entry(self, textvariable=v, width=_ENTRY_WIDTH).pack()
            
        ttk.Button(self, text="Save", command=self.on_save).pack(pady=20)
        
    def on_save(self):
        try:
            new_vals = []
            for i, v in enumerate(self.vars):
                current = self.param.values[i]
                val_str = v.get()
                if isinstance(current, int):
                    new_vals.append(int(val_str))
                else:
                    new_vals.append(float(val_str))
            
            self.param.values = tuple(new_vals)
            if self.callback:
                self.callback(self.param)
            self.destroy()
        except ValueError:
            messagebox.showerror("Error", "Invalid value")


# ======================================================================
# tree_view.py
# ======================================================================



class EDFTreeView(ttk.Treeview):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        
        # Increase row height to prevent clipping on High DPI displays
        style = ttk.Style()
        style.configure("Treeview", rowheight=28)
        
        # Columns must be declared BEFORE configuring headings
        self['columns'] = ("col1", "col2", "col3")
        
        self.heading("#0", text="Item", anchor=tk.W)
        self.heading("col1", text="Value 1", anchor=tk.W)
        self.heading("col2", text="Value 2", anchor=tk.W)
        self.heading("col3", text="Value 3", anchor=tk.W)
        
        self.column("#0", width=300)
        self.column("col1", width=150)
        self.column("col2", width=150)
        self.column("col3", width=150)
        
        # Mapping from item_id to data object (for editing)
        self.item_map = {} 
        
    def clear(self):
        self.delete(*self.get_children())
        self.item_map.clear()
        
    def populate(self, tables: List[TorqueTable], boost_tables: List[BoostTable], params: List[Parameter]):
        self.clear()
        
        # Root nodes
        tt_root = self.insert('', 'end', text=f"Torque tables found: {len(tables)}", open=True)
        bt_root = self.insert('', 'end', text=f"Boost tables found: {len(boost_tables)}", open=True)
        pr_root = self.insert('', 'end', text=f"Parameters found: {len(params)}", open=True)
        
        # Torque Tables
        for t_idx, table in enumerate(tables):
            tnode = self.insert(tt_root, 'end', 
                                text=f"Table {t_idx} @ 0x{table.offset:X} (rows={len(table.rows)})", 
                                values=('', '', ''))
            
            self.insert(tnode, 'end', text="Columns: RPM, Compression (-Nm), Torque (Nm)", values=('', '', ''))
            
            for i, row in enumerate(table.rows):
                tq_str = '' if row.torque is None else format_float(row.torque, 3)
                item_id = self.insert(tnode, 'end',
                                     text=f"Row {i:02d} [{row.kind}] @ 0x{row.offset:X}",
                                     values=(format_float(row.rpm, 1), format_float(row.compression, 3), tq_str))
                self.item_map[item_id] = row

        # Boost Tables
        for b_idx, table in enumerate(boost_tables):
            bnode = self.insert(bt_root, 'end', 
                                text=f"Boost Table {b_idx} @ 0x{table.offset:X} (rows={len(table.rows)})", 
                                values=('', '', ''))
            
            self.insert(bnode, 'end', text="Columns: RPM, Throttle 0%, 25%, 50%, 75%, 100% (bar)", values=('', '', ''))
            
            for i, row in enumerate(table.rows):
                item_id = self.insert(bnode, 'end',
                                     text=f"Row {i:02d} [{row.kind}] @ 0x{row.offset:X}",
                                     values=(format_float(row.t0, 3), format_float(row.t25, 3), format_float(row.t50, 3)))
                self.insert(bnode, 'end',
                           text=f"  → Throttle 75%={format_float(row.t75, 3)}, 100%={format_float(row.t100, 3)}",
                           values=('', '', ''))
                self.item_map[item_id] = row

        # Parameters — with labels and type annotations
        sorted_params = sorted(params, key=lambda x: x.offset)
        for param in sorted_params:
            vals = param.values
            meta = PARAM_META.get(param.name, ())
            
            def _fmt_field(v, idx):
                """Format a value with its label and type from PARAM_META."""
                if idx < len(meta):
                    label, type_str = meta[idx]
                    if isinstance(v, float):
                        return f"{label}= {format_float(v, 6)} ({type_str})"
                    else:
                        return f"{label}= {v} ({type_str})"
                else:
                    if isinstance(v, float):
                        return format_float(v, 6)
                    return str(v)
            
            v1 = _fmt_field(vals[0], 0) if len(vals) > 0 else ''
            v2 = _fmt_field(vals[1], 1) if len(vals) > 1 else ''
            v3 = _fmt_field(vals[2], 2) if len(vals) > 2 else ''
            
            item_id = self.insert(pr_root, 'end', 
                                 text=f"{param.name} @ 0x{param.offset:X}", 
                                 values=(v1, v2, v3))
            self.item_map[item_id] = param


# ======================================================================
# app.py
# ======================================================================




class EDFEditorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AMS2 EDF File Editor v0.5")
        self.geometry("1200x800")
        
        self.current_file = None
        self.data = None
        self._interactive_plot_open = False
        self._interactive_plot = None
        self._dirty = False
        
        self._setup_menu()
        self._setup_layout()
        
    def _setup_menu(self):
        menubar = tk.Menu(self)
        
        self.file_menu = tk.Menu(menubar, tearoff=0)
        self.file_menu.add_command(label="Open EDF...", command=self.load_file)
        self.file_menu.add_command(label="Save", command=self.save_file, state='disabled')
        self.file_menu.add_command(label="Save As...", command=self.save_file_as, state='disabled')
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Close", command=self.close_file, state='disabled')
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=self.file_menu)
        
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Interactive Torque/Power", command=self.plot_torque_interactive)
        tools_menu.add_command(label="Interactive Compression", command=self.plot_compression_interactive)
        tools_menu.add_separator()
        tools_menu.add_command(label="Plot Torque/Power (static)", command=self.plot_torque)
        tools_menu.add_command(label="Plot Compression (static)", command=self.plot_compression)
        tools_menu.add_separator()
        tools_menu.add_command(label="Scale Torque Tables...", command=self.scale_torque_dialog)
        tools_menu.add_command(label="Export CSV...", command=self.export_csv)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        
        self.config(menu=menubar)
        
        # Keyboard shortcut
        self.bind_all('<Control-s>', lambda e: self.save_file())
        
    def _setup_layout(self):
        # Split: Left (Tree), Right (Hex)
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Left frame
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        self.tree = EDFTreeView(left_frame)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Right frame
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        
        self.hex_view = HexView(right_frame)
        self.hex_view.pack(fill=tk.BOTH, expand=True)
        
        # Bind events
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        
    def load_file(self):
        path = filedialog.askopenfilename(filetypes=[("EDF files", "*.edf"), ("All files", "*.*")])
        if not path:
            return
            
        try:
            with open(path, 'rb') as f:
                self.data = bytearray(f.read())
            
            self.current_file = path
            self._set_dirty(False)
            
            # Parse
            self.tables = parse_torque_tables(self.data)
            self.boost = parse_boost_tables(self.data)
            self.params = parse_params(self.data)
            
            # Populate UI
            self.tree.populate(self.tables, self.boost, self.params)
            self.hex_view.load_data(self.data)
            
            # Enable save
            self._enable_save()
            
        except Exception as e:
            logger.exception("Failed to load file")
            messagebox.showerror("Error", f"Failed to load file: {e}")
            
    def _enable_save(self):
        """Enable Save and Save As menu items after a file is loaded."""
        self.file_menu.entryconfig("Save", state='normal')
        self.file_menu.entryconfig("Save As...", state='normal')
        self.file_menu.entryconfig("Close", state='normal')

    def save_file(self):
        """Save to the current file (overwrite original)."""
        if not self.data or not self.current_file:
            return
        try:
            with open(self.current_file, 'wb') as f:
                f.write(self.data)
            self._set_dirty(False)
            messagebox.showinfo("Success", f"Saved to {self.current_file}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

    def save_file_as(self):
        """Save to a new file path."""
        if not self.data:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".edf",
            filetypes=[("EDF files", "*.edf"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, 'wb') as f:
                f.write(self.data)
            self.current_file = path
            self._set_dirty(False)
            messagebox.showinfo("Success", f"Saved to {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

    def close_file(self):
        """Close the current EDF file and reset the UI."""
        self.data = None
        self.current_file = None
        self.tables = []
        self.boost = []
        self.params = []
        self.tree.populate([], [], [])
        self.hex_view.load_data(bytearray())
        
        self.current_file = None
        self._set_dirty(False)
        
        self.file_menu.entryconfig("Save", state='disabled')
        self.file_menu.entryconfig("Save As...", state='disabled')
        self.file_menu.entryconfig("Close", state='disabled')

    def on_tree_double_click(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        
        item_id = sel[0]
        if item_id not in self.tree.item_map:
            return
            
        obj = self.tree.item_map[item_id]
        
        from .dialogs import EditTorqueDialog, EditParamDialog
        from ..core.models import TorqueRow, Parameter
        
        if isinstance(obj, TorqueRow):
            # FR-035: block tree-view editing while interactive plot is open
            if self._interactive_plot_open:
                messagebox.showinfo(
                    "Interactive Plot Active",
                    "Close the interactive plot before editing torque rows in the tree view."
                )
                return
            EditTorqueDialog(self, obj, self.on_row_update)
        elif isinstance(obj, Parameter):
            EditParamDialog(self, obj, self.on_param_update)
            
    def on_row_update(self, row):
        # callback from dialog
        # 1. Write to binary
        write_torque_row(self.data, row)
        # 2. Refresh UI
        # We need to refresh the tree item and hex view
        # For simplicity, reload hex view entirely? Efficient enough for 2MB files.
        self.hex_view.load_data(self.data)
        # Refresh tree item logic?
        # self.tree.item(item_id, values=...)
        # We need to find item_id for this row object.
        # TreeView doesn't support reverse lookup easily unless we store it.
        # But we can just Repopulate or ask TreeView to refresh specific item if we pass ID.
        # Dialog doesn't know ID.
        # We could pass ID to dialog?
        # Or just repopulate entire tree? (Slower but safer)
        # Or update data and re-populate.
        self.tree.populate(self.tables, self.boost, self.params)
        self._set_dirty(True)

    def on_param_update(self, param):
        write_param(self.data, param)
        self.hex_view.load_data(self.data)
        self.tree.populate(self.tables, self.boost, self.params)
        self._set_dirty(True)

    def on_tree_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        
        item_id = sel[0]
        # Check if item has associated data object
        if item_id in self.tree.item_map:
            obj = self.tree.item_map[item_id]
            # Verify object has offset and size (Paranoia check, or type check)
            if hasattr(obj, 'offset') and hasattr(obj, 'size'):
                start = obj.offset
                end = start + obj.size
                self.hex_view.highlight_range(start, end)
        else:
            # Maybe it's a table node?
            # Table nodes are parents. We stored them in the loop but didn't put them in the map?
            # Let's check tree_view.py
            # "tnode = self.insert(tt_root, ..." -> map update? No.
            # Only rows and params are in map.
            # Could add table highlighting if desired.
            pass

    def plot_torque(self):
        if not self.data or not hasattr(self, 'tables'):
            messagebox.showwarning("No data", "No file loaded.")
            return
        try:
            plotting.plot_torque_rpm(self.tables, self.current_file)
        except ImportError as e:
             messagebox.showerror("Error", str(e))
        except Exception as e:
            logger.exception("Plotting failed")
            messagebox.showerror("Error", f"Plotting failed: {e}")

    def plot_compression(self):
        if not self.data or not hasattr(self, 'tables'):
            messagebox.showwarning("No data", "No file loaded.")
            return
        try:
            plotting.plot_compression_rpm(self.tables, self.current_file)
        except ImportError as e:
             messagebox.showerror("Error", str(e))
        except Exception as e:
            logger.exception("Plotting failed")
            messagebox.showerror("Error", f"Plotting failed: {e}")

    def plot_torque_interactive(self):
        """Launch an interactive drag-editable Torque/Power plot."""
        if not self.data or not hasattr(self, 'tables'):
            messagebox.showwarning("No data", "No file loaded.")
            return
        if self._interactive_plot_open:
            messagebox.showinfo("Already open", "An interactive plot is already open.")
            return
        try:
            from ..utils.interactive_plot import DraggableTorquePlot
            self._interactive_plot_open = True
            self._interactive_plot = DraggableTorquePlot(
                parent=self,
                tables=self.tables,
                data=self.data,
                filename=self.current_file or "EDF File",
                on_row_changed=self.on_row_update,
                on_close=self._on_interactive_plot_close,
                mode="torque",
            )
        except ImportError as e:
            self._interactive_plot_open = False
            messagebox.showerror("Error", str(e))
        except Exception as e:
            self._interactive_plot_open = False
            logger.exception("Interactive plot failed")
            messagebox.showerror("Error", f"Interactive plot failed: {e}")

    def plot_compression_interactive(self):
        """Launch an interactive drag-editable Compression plot."""
        if not self.data or not hasattr(self, 'tables'):
            messagebox.showwarning("No data", "No file loaded.")
            return
        if self._interactive_plot_open:
            messagebox.showinfo("Already open", "An interactive plot is already open.")
            return
        try:
            from ..utils.interactive_plot import DraggableTorquePlot
            self._interactive_plot_open = True
            self._interactive_plot = DraggableTorquePlot(
                parent=self,
                tables=self.tables,
                data=self.data,
                filename=self.current_file or "EDF File",
                on_row_changed=self.on_row_update,
                on_close=self._on_interactive_plot_close,
                mode="compression",
            )
        except ImportError as e:
            self._interactive_plot_open = False
            messagebox.showerror("Error", str(e))
        except Exception as e:
            self._interactive_plot_open = False
            logger.exception("Interactive plot failed")
            messagebox.showerror("Error", f"Interactive plot failed: {e}")

    def _on_interactive_plot_close(self):
        """Callback from DraggableTorquePlot when its window is closed (FR-036)."""
        self._interactive_plot_open = False
        self._interactive_plot = None

    def export_csv(self):
        if not self.data or not hasattr(self, 'tables'):
            messagebox.showwarning("No data", "No file loaded.")
            return
            
        path = filedialog.asksaveasfilename(title="Save torque CSV", defaultextension=".csv",
                                            filetypes=[("CSV","*.csv")])
        if not path: return
        
        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(['table_index','row_index','rpm','compression','torque','row_kind','payload_offset_hex','source_file'])
                for t_idx, table in enumerate(self.tables):
                    for r_idx, row in enumerate(table.rows):
                        tq_val = '' if row.torque is None else row.torque
                        # Offset is signature offset now
                        w.writerow([t_idx, r_idx, row.rpm, row.compression, tq_val, row.kind, f"0x{row.offset:X}", self.current_file or ''])
            messagebox.showinfo("Saved", f"CSV saved:\n{path}")
        except Exception as e:
            logger.exception("CSV export failed")
            messagebox.showerror("Error", f"Failed to save CSV: {e}")

    def scale_torque_dialog(self):
        if not self.data or not hasattr(self, 'tables'):
            messagebox.showwarning("No data", "No file loaded.")
            return
            
        percent = simpledialog.askfloat("Scale Torque", "Enter percentage to scale torque:\n(e.g., 110 for +10%, 90 for -10%)",
                                        parent=self, minvalue=0.1, maxvalue=1000.0)
        
        if percent is None:
            return
            
        factor = percent / 100.0
        
        scale_torque_tables(self.data, self.tables, factor)
        
        # Refresh UI
        self.hex_view.load_data(self.data)
        self.tree.populate(self.tables, self.boost, self.params)
        self._set_dirty(True)
        
        messagebox.showinfo("Success", f"Scaled torque by {percent}%")

    def _set_dirty(self, dirty: bool):
        """Update the dirty state and the window title."""
        self._dirty = dirty
        title = "AMS2 EDF File Editor v0.5"
        if self.current_file:
            title += f" - {self.current_file}"
        if self._dirty:
            title += " *"
        self.title(title)

if __name__ == "__main__":
    app = EDFEditorApp()
    app.mainloop()


if __name__ == '__main__':
    app = EDFEditorApp()
    app.mainloop()
