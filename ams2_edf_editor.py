"""
AMS2 EDF File Editor v0.4 — Monolithic Distribution Build
==========================================================
Single-file version for easy command-line use:
    python ams2_edf_editor.py

Requires: Python 3.10+, tkinter (bundled with Python on Windows)
Optional: matplotlib (for torque/power plots)
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
from typing import Tuple, Optional, List, Union, Generator
from pathlib import Path

# Windows High DPI awareness (FR11) — must be called before any Tkinter init
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

logger = logging.getLogger(__name__)

# ===========================================================================
#  CONSTANTS
# ===========================================================================

SIG_0RPM   = b'\x24\x8B\x0A\xB7\x71\x83\x02'
SIG_ROW_I  = b'\x24\x8B\x0A\xB7\x71\x93\x02'
SIG_ROW_F  = b'\x24\x8B\x0A\xB7\x71\xA3\x02'
SIG_ENDVAR = b'\x24\x8B\x0A\xB7\x71\x93\x00'

SIG_BOOST_0RPM = b'\x24\x51\x5F\x5E\x83\x86\xAA'
SIG_BOOST_ROW  = b'\x24\x51\x5F\x5E\x83\x96\xAA'

ROW0_STRUCT   = struct.Struct('<Bff')
ROWI_STRUCT   = struct.Struct('<iff')
ROWF_STRUCT   = struct.Struct('<fff')
ENDVAR_STRUCT = struct.Struct('<ifB')

BOOST0_STRUCT = struct.Struct('<Bfffff')
BOOSTI_STRUCT = struct.Struct('<ifffff')

PARAMS = {
    b'\x22\x4A\xE2\xDD\x6C': ('FuelConsumption', ('f',)),
    b'\x22\xD2\xA2\x92\x32': ('FuelEstimate',    ('f',)),
    b'\x22\x46\x65\xAE\x87': ('EngineInertia',   ('f',)),
    b'\x22\x40\xF1\xD2\xB9': ('Unknown_EngineFreeRevs', ('f',)),
    b'\x24\x4D\x23\x97\x54\xA2': ('IdleRPMLogic', ('f','f')),
    b'\x24\x4D\x23\x97\x54\x52': ('IdleRPMLogic', ('i','i')),
    b'\x22\x21\x98\x99\xAE': ('LaunchEfficiency', ('f',)),
    b'\x24\x79\x02\xB6\xBD\xA2': ('LaunchRPMLogic', ('f','f')),
    b'\x24\xDE\xA7\x2E\xB7\x23\x00': ('RevLimitRange', ('f','f','b')),
    b'\x24\xDE\xA7\x2E\xB7\x13\x00': ('RevLimitRange', ('i','b','b')),
    b'\x20\xA5\x5C\xC1\xC4': ('RevLimitSetting', ('b',)),
    b'\x28\xA5\x5C\xC1\xC4': ('RevLimitSetting_NoValue', ()),
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
    b'\x21\x3F\x6B\x7B\xE7\x82\x00': ('Unknown_Chunk_213F6B', ('b','b')),
    b'\x20\x6D\x47\xC1\xB2': ('Unknown_Chunk_206D47', ('b',)),
    b'\x24\xD3\x94\x64\xAF\xA2': ('LifetimeEngineRPM', ('f','f')),
    b'\x24\xD3\x94\x64\xAF\x52': ('LifetimeEngineRPM', ('i','i')),
    b'\x24\x0A\xCE\xA8\x58\xA2': ('LifetimeOilTemp', ('f','f')),
    b'\x24\x05\x71\xC7\x19\xA2': ('Unknown_LMP_RWD_P30_A', ('f','f')),
    b'\x22\xF7\x5F\x82\x2B': ('LifetimeAvg', ('f',)),
    b'\x22\x52\x7B\x76\xCD': ('LifetimeVar', ('f',)),
    b'\x24\xC1\xF4\x54\x3C\x83\x02': ('Unknown_LMP_RWD_P30_B', ('b','f','f')),
    b'\x24\xCE\xB1\x75\x25\xA3\x02': ('EngineEmission', ('f','f','f')),
    b'\x20\x11\x8B\xA3\x81': ('OnboardStarter?', ('b',)),
    b'\x26\xAF\x00\xB3\xBA': ('EDF_UNKN_005', ('b',)),
    b'\x24\x52\x17\xFB\x41\xA3\x02': ('StarterTiming', ('f','f','f')),
    b'\x22\x92\xC7\xCD\x7C': ('Unknown_Float_3', ('f',)),
    b'\x24\xFC\x89\xE8\x9C\xA3\x00': ('AirRestrictorRange', ('f','f','b')),
    b'\x20\xC5\xB4\x08\xFE': ('AirRestrictorSetting', ('b',)),
    b'\x28\xC5\xB4\x08\xFE': ('AirRestrictorSetting_NoValue', ()),
    b'\x20\x2B\x3E\xD3\x40': ('Unknown_Byte_2B3ED340', ('b',)),
    b'\x22\xBA\x65\xDD\x60': ('Unknown_Float_6e-06', ('f',)),
    b'\x22\x81\x92\x17\xE0': ('Unknown_Float_295', ('f',)),
    b'\x24\x63\x23\x3A\x14\xA3\x00': ('WasteGateRange_OLD', ('f','f','b')),
    b'\x20\xDF\x86\x64\xFC': ('WasteGateSetting_OLD', ('b',)),
    b'\x28\xDF\x86\x64\xFC': ('WasteGateSetting_OLD_NoValue', ()),
    b'\x23\x00\x00\x50\xC3': ('Unknown_2300005', ('b','b')),
    b'\x24\xD7\x74\x45\x1A\x83\x00': ('BoostRange', ('b','f','b')),
    b'\x20\xCA\x2F\xD1\x34': ('BoostSetting', ('b',)),
    b'\x28\xCA\x2F\xD1\x34': ('BoostSetting_NoValue', ()),
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

# ===========================================================================
#  MODELS
# ===========================================================================

@dataclass
class TorqueRow:
    rpm: float
    compression: float
    torque: Optional[float]
    offset: int
    kind: str

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
    kind: str

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

# ===========================================================================
#  FORMATTING
# ===========================================================================

def format_float(val: float, decimals: int = 6) -> str:
    return f"{val:.{decimals}f}"

# ===========================================================================
#  PARSER
# ===========================================================================

def find_all(data: bytes, sub: bytes) -> Generator[int, None, None]:
    start = 0
    L = len(sub)
    while True:
        i = data.find(sub, start)
        if i == -1:
            return
        yield i
        start = i + L

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

def plausible_rpm(x): return 0 <= x <= 25000
def plausible_comp(x): return -300 <= x <= 300
def plausible_torque(x): return -4000 <= x <= 10000

def parse_torque_tables(data: bytes) -> List[TorqueTable]:
    tables = []
    for off0 in find_all(data, SIG_0RPM):
        rows = []
        p = off0 + len(SIG_0RPM)
        if p + ROW0_STRUCT.size > len(data): continue
        b0, comp0, tq0 = ROW0_STRUCT.unpack_from(data, p)
        if not (plausible_comp(comp0) and plausible_torque(tq0)): continue
        rows.append(TorqueRow(0.0, comp0, tq0, off0, '0rpm'))
        q = p + ROW0_STRUCT.size
        while q < len(data):
            if data[q:q+len(SIG_0RPM)] == SIG_0RPM: break
            if data[q:q+len(SIG_ROW_I)] == SIG_ROW_I:
                sig_off = q; q += len(SIG_ROW_I)
                if q + ROWI_STRUCT.size > len(data): break
                rpm_i, comp, tq = ROWI_STRUCT.unpack_from(data, q)
                rpm = float(rpm_i)
                if not (plausible_rpm(rpm) and plausible_comp(comp) and plausible_torque(tq)): break
                rows.append(TorqueRow(rpm, comp, tq, sig_off, 'row_i'))
                q += ROWI_STRUCT.size; continue
            if data[q:q+len(SIG_ROW_F)] == SIG_ROW_F:
                sig_off = q; q += len(SIG_ROW_F)
                if q + ROWF_STRUCT.size > len(data): break
                rpm, comp, tq = ROWF_STRUCT.unpack_from(data, q)
                if not (plausible_rpm(rpm) and plausible_comp(comp) and plausible_torque(tq)): break
                rows.append(TorqueRow(rpm, comp, tq, sig_off, 'row_f'))
                q += ROWF_STRUCT.size; continue
            if data[q:q+len(SIG_ENDVAR)] == SIG_ENDVAR:
                sig_off = q; q += len(SIG_ENDVAR)
                if q + ENDVAR_STRUCT.size > len(data): break
                rpm_i, comp, b = ENDVAR_STRUCT.unpack_from(data, q)
                rows.append(TorqueRow(float(rpm_i), comp, None, sig_off, 'endvar'))
                q += ENDVAR_STRUCT.size; break
            break
        if len(rows) >= 2:
            rows.sort(key=lambda r: r.rpm)
            tables.append(TorqueTable(off0, rows))
    return tables

def parse_boost_tables(data: bytes) -> List[BoostTable]:
    tables = []
    for off0 in find_all(data, SIG_BOOST_0RPM):
        rows = []
        p = off0 + len(SIG_BOOST_0RPM)
        if p + BOOST0_STRUCT.size > len(data): continue
        b0, t0, t25, t50, t75, t100 = BOOST0_STRUCT.unpack_from(data, p)
        if not all(0.5 <= v <= 3.0 for v in [t0, t25, t50, t75, t100]): continue
        rows.append(BoostRow(0, t0, t25, t50, t75, t100, off0, 'boost_0rpm'))
        q = p + BOOST0_STRUCT.size
        while q < len(data):
            if data[q:q+len(SIG_BOOST_0RPM)] == SIG_BOOST_0RPM: break
            if data[q:q+len(SIG_BOOST_ROW)] == SIG_BOOST_ROW:
                sig_off = q; q += len(SIG_BOOST_ROW)
                if q + BOOSTI_STRUCT.size > len(data): break
                rpm, t0, t25, t50, t75, t100 = BOOSTI_STRUCT.unpack_from(data, q)
                if not (0 <= rpm <= 25000): break
                if not all(0.5 <= v <= 3.0 for v in [t0, t25, t50, t75, t100]): break
                rows.append(BoostRow(rpm, t0, t25, t50, t75, t100, sig_off, 'boost_row'))
                q += BOOSTI_STRUCT.size; continue
            break
        if len(rows) >= 2:
            rows.sort(key=lambda r: r.rpm)
            tables.append(BoostTable(off0, rows))
    return tables

def parse_params(data: bytes) -> List[Parameter]:
    out = []
    for sig, (name, fmt) in PARAMS.items():
        for pos in find_all(data, sig):
            start = pos + len(sig)
            if len(fmt) == 0:
                out.append(Parameter(name, pos, (), fmt))
            else:
                vals, endp = read_by_fmt(data, start, fmt)
                if vals is None: continue
                out.append(Parameter(name, pos, tuple(vals), fmt))
    return out

def detect_engine_layout(data: bytes) -> Tuple[str, Optional[int]]:
    tail = data[-64:] if len(data) > 64 else data
    for k, label in ENGINE_LAYOUT_CODES.items():
        i = tail.rfind(k)
        if i != -1:
            return label, len(data) - len(tail) + i
    return 'Unknown/Not found', None

# ===========================================================================
#  WRITER
# ===========================================================================

def write_torque_row(data: bytearray, row: TorqueRow) -> None:
    if row.kind == '0rpm':
        if row.torque is None: return
        p = row.offset + len(SIG_0RPM)
        b0 = data[p]
        struct.pack_into('<Bff', data, p, b0, row.compression, row.torque)
    elif row.kind == 'row_i':
        if row.torque is None: return
        p = row.offset + len(SIG_ROW_I)
        struct.pack_into('<iff', data, p, int(row.rpm), row.compression, row.torque)
    elif row.kind == 'row_f':
        if row.torque is None: return
        p = row.offset + len(SIG_ROW_F)
        struct.pack_into('<fff', data, p, row.rpm, row.compression, row.torque)
    elif row.kind == 'endvar':
        p = row.offset + len(SIG_ENDVAR)
        trailing_byte = data[p + ENDVAR_STRUCT.size - 1]
        struct.pack_into('<ifB', data, p, int(row.rpm), row.compression, trailing_byte)

def write_boost_row(data: bytearray, row: BoostRow) -> None:
    if row.kind == 'boost_0rpm':
        p = row.offset + len(SIG_BOOST_0RPM)
        b0 = data[p]
        struct.pack_into('<Bfffff', data, p, b0, row.t0, row.t25, row.t50, row.t75, row.t100)
    elif row.kind == 'boost_row':
        p = row.offset + len(SIG_BOOST_ROW)
        struct.pack_into('<ifffff', data, p, int(row.rpm), row.t0, row.t25, row.t50, row.t75, row.t100)

def write_param(data: bytearray, param: Parameter) -> None:
    sig_len = 0
    fmt: Tuple[str, ...] = tuple()
    if param.fmt:
        fmt = param.fmt
        for sig, (pname, pfmt) in PARAMS.items():
            if pname == param.name:
                sig_len = len(sig); break
    else:
        for sig, (pname, pfmt) in PARAMS.items():
            if pname == param.name:
                sig_len = len(sig); fmt = pfmt; break
    if not fmt: return
    cur = param.offset + sig_len
    for i, f in enumerate(fmt):
        val = param.values[i]
        if f == 'f':
            struct.pack_into('<f', data, cur, float(val)); cur += 4
        elif f == 'i':
            struct.pack_into('<i', data, cur, int(val)); cur += 4
        elif f == 'b':
            struct.pack_into('B', data, cur, int(val)); cur += 1

def scale_torque_tables(data: bytearray, tables: List[TorqueTable], factor: float) -> None:
    for table in tables:
        for row in table.rows:
            if row.torque is not None:
                row.torque *= factor
                write_torque_row(data, row)

# ===========================================================================
#  PLOTTING (optional — requires matplotlib)
# ===========================================================================

def _ensure_matplotlib():
    try:
        import matplotlib.pyplot as plt
        return plt
    except ImportError:
        logger.error("Matplotlib not found.")
        raise ImportError("matplotlib is required for plotting.\nInstall it with: pip install matplotlib")

def plot_torque_rpm(tables: List[TorqueTable], filename: str = "EDF File"):
    if not tables: return
    plt = _ensure_matplotlib()
    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax2 = ax1.twinx()
    tc = ['#1f77b4', '#2ca02c', '#9467bd', '#8c564b']
    pc = ['#ff7f0e', '#ff9f3f', '#ffbf7f', '#ffd9a6']
    for t_idx, table in enumerate(tables):
        rpms, torques, powers = [], [], []
        for row in table.rows:
            if row.torque is not None:
                rpms.append(row.rpm); torques.append(row.torque)
                powers.append((row.torque * row.rpm) / 9549.3)
        if rpms:
            ax1.plot(rpms, torques, marker='o', label=f'Table {t_idx} Torque @ 0x{table.offset:X}', linewidth=2, markersize=4, color=tc[t_idx % len(tc)])
            ax2.plot(rpms, powers, marker='s', label=f'Table {t_idx} Power @ 0x{table.offset:X}', linewidth=2, markersize=4, linestyle='--', color=pc[t_idx % len(pc)])
    ax1.set_xlabel('RPM', fontsize=12); ax1.set_ylabel('Torque (Nm)', fontsize=12, color='tab:blue')
    ax1.tick_params(axis='y', labelcolor='tab:blue')
    ax2.set_ylabel('Power (kW)', fontsize=12, color='tab:orange'); ax2.tick_params(axis='y', labelcolor='tab:orange')
    ax1.set_title(f'Torque & Power vs RPM - {Path(filename).name}', fontsize=14); ax1.grid(True, alpha=0.3)
    l1, lb1 = ax1.get_legend_handles_labels(); l2, lb2 = ax2.get_legend_handles_labels()
    ax1.legend(l1 + l2, lb1 + lb2, loc='best'); plt.tight_layout(); plt.show()

def plot_compression_rpm(tables: List[TorqueTable], filename: str = "EDF File"):
    if not tables: return
    plt = _ensure_matplotlib()
    fig, ax = plt.subplots(figsize=(10, 6))
    for t_idx, table in enumerate(tables):
        rpms, comps = [], []
        for row in table.rows:
            if row.torque is not None:
                rpms.append(row.rpm); comps.append(row.compression)
        if rpms:
            ax.plot(rpms, comps, marker='o', label=f'Table {t_idx} @ 0x{table.offset:X}', linewidth=2, markersize=4)
    ax.set_xlabel('RPM', fontsize=12); ax.set_ylabel('Compression (-Nm)', fontsize=12)
    ax.set_title(f'Compression vs RPM - {Path(filename).name}', fontsize=14)
    ax.grid(True, alpha=0.3); ax.legend(); plt.tight_layout(); plt.show()

# ===========================================================================
#  HEX VIEW
# ===========================================================================

class HexView(tk.Text):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.config(state='disabled', font=("Courier", 10))
        self.tag_configure("highlight", background="yellow", foreground="black")

    def load_data(self, data: bytes):
        self.config(state='normal')
        self.delete('1.0', tk.END)
        lines = []
        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            hex_part = []
            for j, b in enumerate(chunk):
                hex_part.append(f"{b:02X}")
                if j == 7: hex_part.append("")
            hex_str = " ".join(hex_part).ljust(49)
            ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            lines.append(f"{i:08X}  {hex_str}  |{ascii_part}|")
        self.insert('1.0', "\n".join(lines))
        self.config(state='disabled')

    def highlight_range(self, start: int, end: int):
        self.tag_remove("highlight", "1.0", tk.END)
        if start >= end: return
        current_off = start
        while current_off < end:
            line_idx = (current_off // 16) + 1
            col_idx = current_off % 16
            line_start_off = (line_idx - 1) * 16
            line_end_off = line_start_off + 16
            chunk_end = min(end, line_end_off)
            def get_text_col(byte_idx):
                col = 10 + (byte_idx * 3)
                if byte_idx >= 8: col += 1
                return col
            for b_idx in range(col_idx, chunk_end - line_start_off):
                c_start = get_text_col(b_idx)
                c_end = c_start + 2
                self.tag_add("highlight", f"{line_idx}.{c_start}", f"{line_idx}.{c_end}")
            current_off = chunk_end
        self.see(f"{(start // 16) + 1}.0")

# ===========================================================================
#  TREE VIEW
# ===========================================================================

class EDFTreeView(ttk.Treeview):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        style = ttk.Style()
        style.configure("Treeview", rowheight=28)
        self['columns'] = ("col1", "col2", "col3")
        self.heading("#0", text="Item", anchor=tk.W)
        self.heading("col1", text="Value 1", anchor=tk.W)
        self.heading("col2", text="Value 2", anchor=tk.W)
        self.heading("col3", text="Value 3", anchor=tk.W)
        self.column("#0", width=300)
        self.column("col1", width=150)
        self.column("col2", width=150)
        self.column("col3", width=150)
        self.item_map = {}

    def clear(self):
        self.delete(*self.get_children())
        self.item_map.clear()

    def populate(self, tables, boost_tables, params):
        self.clear()
        tt_root = self.insert('', 'end', text=f"Torque tables found: {len(tables)}", open=True)
        bt_root = self.insert('', 'end', text=f"Boost tables found: {len(boost_tables)}", open=True)
        pr_root = self.insert('', 'end', text=f"Parameters found: {len(params)}", open=True)
        for t_idx, table in enumerate(tables):
            tnode = self.insert(tt_root, 'end', text=f"Table {t_idx} @ 0x{table.offset:X} (rows={len(table.rows)})", values=('','',''))
            self.insert(tnode, 'end', text="Columns: RPM, Compression (-Nm), Torque (Nm)", values=('','',''))
            for i, row in enumerate(table.rows):
                tq_str = '' if row.torque is None else format_float(row.torque, 3)
                item_id = self.insert(tnode, 'end', text=f"Row {i:02d} [{row.kind}] @ 0x{row.offset:X}", values=(format_float(row.rpm, 1), format_float(row.compression, 3), tq_str))
                self.item_map[item_id] = row
        for b_idx, table in enumerate(boost_tables):
            bnode = self.insert(bt_root, 'end', text=f"Boost Table {b_idx} @ 0x{table.offset:X} (rows={len(table.rows)})", values=('','',''))
            self.insert(bnode, 'end', text="Columns: RPM, Throttle 0%, 25%, 50%, 75%, 100% (bar)", values=('','',''))
            for i, row in enumerate(table.rows):
                item_id = self.insert(bnode, 'end', text=f"Row {i:02d} [{row.kind}] @ 0x{row.offset:X}", values=(format_float(row.t0, 3), format_float(row.t25, 3), format_float(row.t50, 3)))
                self.insert(bnode, 'end', text=f"  → Throttle 75%={format_float(row.t75, 3)}, 100%={format_float(row.t100, 3)}", values=('','',''))
                self.item_map[item_id] = row
        sorted_params = sorted(params, key=lambda x: x.offset)
        for param in sorted_params:
            vals = param.values
            meta = PARAM_META.get(param.name, ())
            def _fmt_field(v, idx, _meta=meta):
                if idx < len(_meta):
                    label, type_str = _meta[idx]
                    if isinstance(v, float): return f"{label}= {format_float(v, 6)} ({type_str})"
                    else: return f"{label}= {v} ({type_str})"
                else:
                    if isinstance(v, float): return format_float(v, 6)
                    return str(v)
            v1 = _fmt_field(vals[0], 0) if len(vals) > 0 else ''
            v2 = _fmt_field(vals[1], 1) if len(vals) > 1 else ''
            v3 = _fmt_field(vals[2], 2) if len(vals) > 2 else ''
            item_id = self.insert(pr_root, 'end', text=f"{param.name} @ 0x{param.offset:X}", values=(v1, v2, v3))
            self.item_map[item_id] = param

# ===========================================================================
#  DIALOGS
# ===========================================================================

_ENTRY_WIDTH = 40

class EditTorqueDialog(tk.Toplevel):
    def __init__(self, parent, row: TorqueRow, callback):
        super().__init__(parent)
        self.row = row; self.callback = callback
        self.title("Edit Torque Row"); self.transient(parent); self.grab_set()
        self.result = False; self._setup_ui()
        self.update_idletasks(); self.minsize(self.winfo_reqwidth(), self.winfo_reqheight())

    def _setup_ui(self):
        pad = {'padx': 10, 'pady': 5}
        ttk.Label(self, text="RPM:").pack(**pad)
        self.rpm_var = tk.StringVar(value=format_float(self.row.rpm, 1))
        rpm_entry = ttk.Entry(self, textvariable=self.rpm_var, width=_ENTRY_WIDTH); rpm_entry.pack(**pad)
        if self.row.kind == '0rpm': rpm_entry.config(state='disabled')
        ttk.Label(self, text="Compression:").pack(**pad)
        self.comp_var = tk.StringVar(value=format_float(self.row.compression, 6))
        ttk.Entry(self, textvariable=self.comp_var, width=_ENTRY_WIDTH).pack(**pad)
        ttk.Label(self, text="Torque:").pack(**pad)
        self.tq_var = tk.StringVar(value=format_float(self.row.torque, 6) if self.row.torque is not None else "")
        ttk.Entry(self, textvariable=self.tq_var, width=_ENTRY_WIDTH).pack(**pad)
        btn_frame = ttk.Frame(self); btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="Save", command=self.on_save).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side='left', padx=5)

    def on_save(self):
        try:
            self.row.rpm = float(self.rpm_var.get())
            self.row.compression = float(self.comp_var.get())
            self.row.torque = float(self.tq_var.get()) if self.tq_var.get() else None
            self.result = True
            if self.callback: self.callback(self.row)
            self.destroy()
        except ValueError:
            messagebox.showerror("Error", "Invalid numeric value")

class EditParamDialog(tk.Toplevel):
    def __init__(self, parent, param: Parameter, callback):
        super().__init__(parent)
        self.param = param; self.callback = callback
        self.title(f"Edit {param.name}"); self.transient(parent); self.grab_set()
        self._setup_ui()
        self.update_idletasks(); self.minsize(self.winfo_reqwidth(), self.winfo_reqheight())

    def _setup_ui(self):
        ttk.Label(self, text=f"Parameter: {self.param.name}").pack(pady=10)
        meta = PARAM_META.get(self.param.name, ())
        self.vars = []
        for i, val in enumerate(self.param.values):
            if i < len(meta):
                label_text, type_str = meta[i]
                field_label = f"{label_text} [{type_str}]:"
            else:
                field_label = f"Value {i+1}:"
            ttk.Label(self, text=field_label).pack()
            if isinstance(val, float): display = format_float(val, 6)
            else: display = str(val)
            v = tk.StringVar(value=display); self.vars.append(v)
            ttk.Entry(self, textvariable=v, width=_ENTRY_WIDTH).pack()
        ttk.Button(self, text="Save", command=self.on_save).pack(pady=20)

    def on_save(self):
        try:
            new_vals = []
            for i, v in enumerate(self.vars):
                current = self.param.values[i]
                val_str = v.get()
                if isinstance(current, int): new_vals.append(int(val_str))
                else: new_vals.append(float(val_str))
            self.param.values = tuple(new_vals)
            if self.callback: self.callback(self.param)
            self.destroy()
        except ValueError:
            messagebox.showerror("Error", "Invalid value")

# ===========================================================================
#  APPLICATION
# ===========================================================================

class EDFEditorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AMS2 EDF File Editor v0.4")
        self.geometry("1200x800")
        self.current_file = None; self.data = None
        self._setup_menu(); self._setup_layout()

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
        tools_menu.add_command(label="Plot Torque/Power", command=self.plot_torque)
        tools_menu.add_command(label="Plot Compression", command=self.plot_compression)
        tools_menu.add_separator()
        tools_menu.add_command(label="Scale Torque Tables...", command=self.scale_torque_dialog)
        tools_menu.add_command(label="Export CSV...", command=self.export_csv)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        self.config(menu=menubar)
        self.bind_all('<Control-s>', lambda e: self.save_file())

    def _setup_layout(self):
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL); paned.pack(fill=tk.BOTH, expand=True)
        left_frame = ttk.Frame(paned); paned.add(left_frame, weight=1)
        self.tree = EDFTreeView(left_frame); self.tree.pack(fill=tk.BOTH, expand=True)
        right_frame = ttk.Frame(paned); paned.add(right_frame, weight=1)
        self.hex_view = HexView(right_frame); self.hex_view.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Double-1>", self.on_tree_double_click)

    def load_file(self):
        path = filedialog.askopenfilename(filetypes=[("EDF files", "*.edf"), ("All files", "*.*")])
        if not path: return
        try:
            with open(path, 'rb') as f: self.data = bytearray(f.read())
            self.current_file = path
            self.title(f"AMS2 EDF File Editor v0.4 - {path}")
            self.tables = parse_torque_tables(self.data)
            self.boost = parse_boost_tables(self.data)
            self.params = parse_params(self.data)
            self.tree.populate(self.tables, self.boost, self.params)
            self.hex_view.load_data(self.data)
            self._enable_save()
        except Exception as e:
            logger.exception("Failed to load file")
            messagebox.showerror("Error", f"Failed to load file: {e}")

    def _enable_save(self):
        self.file_menu.entryconfig("Save", state='normal')
        self.file_menu.entryconfig("Save As...", state='normal')
        self.file_menu.entryconfig("Close", state='normal')

    def save_file(self):
        if not self.data or not self.current_file: return
        try:
            with open(self.current_file, 'wb') as f: f.write(self.data)
            messagebox.showinfo("Success", f"Saved to {self.current_file}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

    def save_file_as(self):
        if not self.data: return
        path = filedialog.asksaveasfilename(defaultextension=".edf", filetypes=[("EDF files", "*.edf"), ("All files", "*.*")])
        if not path: return
        try:
            with open(path, 'wb') as f: f.write(self.data)
            self.current_file = path
            self.title(f"AMS2 EDF File Editor v0.4 - {path}")
            messagebox.showinfo("Success", f"Saved to {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

    def close_file(self):
        self.data = None; self.current_file = None
        self.tables = []; self.boost = []; self.params = []
        self.tree.populate([], [], [])
        self.hex_view.load_data(bytearray())
        self.title("AMS2 EDF File Editor v0.4")
        self.file_menu.entryconfig("Save", state='disabled')
        self.file_menu.entryconfig("Save As...", state='disabled')
        self.file_menu.entryconfig("Close", state='disabled')

    def on_tree_double_click(self, event):
        sel = self.tree.selection()
        if not sel: return
        item_id = sel[0]
        if item_id not in self.tree.item_map: return
        obj = self.tree.item_map[item_id]
        if isinstance(obj, TorqueRow): EditTorqueDialog(self, obj, self.on_row_update)
        elif isinstance(obj, Parameter): EditParamDialog(self, obj, self.on_param_update)

    def on_row_update(self, row):
        write_torque_row(self.data, row)
        self.hex_view.load_data(self.data)
        self.tree.populate(self.tables, self.boost, self.params)

    def on_param_update(self, param):
        write_param(self.data, param)
        self.hex_view.load_data(self.data)
        self.tree.populate(self.tables, self.boost, self.params)

    def on_tree_select(self, event):
        sel = self.tree.selection()
        if not sel: return
        item_id = sel[0]
        if item_id in self.tree.item_map:
            obj = self.tree.item_map[item_id]
            if hasattr(obj, 'offset') and hasattr(obj, 'size'):
                self.hex_view.highlight_range(obj.offset, obj.offset + obj.size)

    def plot_torque(self):
        if not self.data or not hasattr(self, 'tables'):
            messagebox.showwarning("No data", "No file loaded."); return
        try: plot_torque_rpm(self.tables, self.current_file)
        except ImportError as e: messagebox.showerror("Error", str(e))
        except Exception as e: messagebox.showerror("Error", f"Plotting failed: {e}")

    def plot_compression(self):
        if not self.data or not hasattr(self, 'tables'):
            messagebox.showwarning("No data", "No file loaded."); return
        try: plot_compression_rpm(self.tables, self.current_file)
        except ImportError as e: messagebox.showerror("Error", str(e))
        except Exception as e: messagebox.showerror("Error", f"Plotting failed: {e}")

    def export_csv(self):
        if not self.data or not hasattr(self, 'tables'):
            messagebox.showwarning("No data", "No file loaded."); return
        path = filedialog.asksaveasfilename(title="Save torque CSV", defaultextension=".csv", filetypes=[("CSV","*.csv")])
        if not path: return
        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(['table_index','row_index','rpm','compression','torque','row_kind','payload_offset_hex','source_file'])
                for t_idx, table in enumerate(self.tables):
                    for r_idx, row in enumerate(table.rows):
                        tq_val = '' if row.torque is None else row.torque
                        w.writerow([t_idx, r_idx, row.rpm, row.compression, tq_val, row.kind, f"0x{row.offset:X}", self.current_file or ''])
            messagebox.showinfo("Saved", f"CSV saved:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save CSV: {e}")

    def scale_torque_dialog(self):
        if not self.data or not hasattr(self, 'tables'):
            messagebox.showwarning("No data", "No file loaded."); return
        percent = simpledialog.askfloat("Scale Torque", "Enter percentage to scale torque:\n(e.g., 110 for +10%, 90 for -10%)", parent=self, minvalue=0.1, maxvalue=1000.0)
        if percent is None: return
        scale_torque_tables(self.data, self.tables, percent / 100.0)
        self.hex_view.load_data(self.data)
        self.tree.populate(self.tables, self.boost, self.params)
        messagebox.showinfo("Success", f"Scaled torque by {percent}%")

# ===========================================================================
#  ENTRY POINT
# ===========================================================================

if __name__ == "__main__":
    app = EDFEditorApp()
    app.mainloop()
