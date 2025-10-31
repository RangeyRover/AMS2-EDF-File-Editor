#!/usr/bin/env python3
# edf_tk_viewer.py
# Minimal Tkinter viewer for Madness-engine EDF/EDFBIN engine files
# Uses JDougNY's "Project CARS Engine translation" mapping (v1.01)
# Supports torque curves and a set of common parameter tags.
#
# Python 3.9+ recommended. No external deps except tkinter (standard lib).

import struct
import csv
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# -------- Signatures (little-endian) --------
SIG_0RPM   = b'\x24\x8B\x0A\xB7\x71\x83\x02'  # byte, float, float
SIG_ROW_I  = b'\x24\x8B\x0A\xB7\x71\x93\x02'  # int32, float, float
SIG_ROW_F  = b'\x24\x8B\x0A\xB7\x71\xA3\x02'  # float, float, float
SIG_ENDVAR = b'\x24\x8B\x0A\xB7\x71\x93\x00'  # int32, float, byte (rare)

# Boost table signatures
SIG_BOOST_0RPM = b'\x24\x51\x5F\x5E\x83\x86\xAA'  # byte, 5 floats (throttle positions)
SIG_BOOST_ROW  = b'\x24\x51\x5F\x5E\x83\x96\xAA'  # int32, 5 floats (throttle positions)

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
    b'\x22\x40\xF1\xD2\xB9': ('Unknown_EngineFreeRevs?', ('f',)),
    b'\x24\x4D\x23\x97\x54\xA2': ('IdleRPMLogic', ('f','f')),   # alt 52: int,int
    b'\x24\x4D\x23\x97\x54\x52': ('IdleRPMLogic', ('i','i')),
    b'\x22\x21\x98\x99\xAE': ('LaunchEfficiency', ('f',)),
    b'\x24\x79\x02\xB6\xBD\xA2': ('LaunchRPMLogic', ('f','f')),
    b'\x24\xDE\xA7\x2E\xB7\x23\x00': ('RevLimitRange', ('f','b','b')),  # alt 13 00: int,b,b
    b'\x24\xDE\xA7\x2E\xB7\x13\x00': ('RevLimitRange', ('i','b','b')),
    b'\x20\xA5\x5C\xC1\xC4': ('RevLimitSetting', ('b',)),  # Byte
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
    b'\x24\xD3\x94\x64\xAF\xA2': ('LifetimeEngineRPM', ('f','f')),
    b'\x24\xD3\x94\x64\xAF\x52': ('LifetimeEngineRPM', ('i','i')),
    b'\x24\x0A\xCE\xA8\x58\xA2': ('LifetimeOilTemp', ('f','f')),
    b'\x22\xF7\x5F\x82\x2B': ('LifetimeAvg', ('f',)),
    b'\x22\x52\x7B\x76\xCD': ('LifetimeVar', ('f',)),
    b'\x24\xCE\xB1\x75\x25\xA3\x02': ('EngineEmission', ('f','f','f')),
    b'\x20\x11\x8B\xA3\x81': ('OnboardStarter?', ('b',)),
    b'\x26\xAF\x00\xB3\xBA': ('EDF_UNKN_005', ('b',)),
    b'\x24\x52\x17\xFB\x41\xA3\x02': ('StarterTiming', ('f','f','f')),
    b'\x24\xFC\x89\xE8\x9C\xA3\x00': ('AirRestrictorRange', ('f','f','b')),
    b'\x20\x2B\x3E\xD3\x40': ('Unknown_Byte_2B3ED340', ('b',)),
    b'\x22\xBA\x65\xDD\x60': ('Unknown_Float_2265DD60', ('f',)),
    b'\x22\x81\x92\x17\xE0': ('Unknown_Float_229217E0', ('f',)),
    b'\x24\xD7\x74\x45\x1A\x83\x00': ('BoostRange', ('b','f','b')),
    b'\x20\xCA\x2F\xD1\x34': ('BoostSetting', ('b',)),
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

def find_all(data: bytes, sub: bytes):
    start = 0
    L = len(sub)
    while True:
        i = data.find(sub, start)
        if i == -1:
            return
        yield i
        start = i + L  # step to next occurrence (avoid overlap)

def read_by_fmt(data: bytes, pos: int, fmtseq):
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

def parse_torque_tables(data: bytes):
    tables = []
    for off0 in find_all(data, SIG_0RPM):
        rows = []
        p = off0 + len(SIG_0RPM)
        if p + ROW0_STRUCT.size > len(data): continue
        b0, comp0, tq0 = ROW0_STRUCT.unpack_from(data, p)
        # tolerate odd b0 values seen in the wild
        if not (plausible_comp(comp0) and plausible_torque(tq0)): continue
        rows.append((0.0, comp0, tq0, off0, '0rpm'))
        q = p + ROW0_STRUCT.size
        while q < len(data):
            if data[q:q+len(SIG_0RPM)] == SIG_0RPM:
                # next table begins
                break
            if data[q:q+len(SIG_ROW_I)] == SIG_ROW_I:
                q += len(SIG_ROW_I)
                if q + ROWI_STRUCT.size > len(data): break
                rpm_i, comp, tq = ROWI_STRUCT.unpack_from(data, q)
                rpm = float(rpm_i)
                if not (plausible_rpm(rpm) and plausible_comp(comp) and plausible_torque(tq)): break
                rows.append((rpm, comp, tq, q, 'row_i'))
                q += ROWI_STRUCT.size
                continue
            if data[q:q+len(SIG_ROW_F)] == SIG_ROW_F:
                q += len(SIG_ROW_F)
                if q + ROWF_STRUCT.size > len(data): break
                rpm, comp, tq = ROWF_STRUCT.unpack_from(data, q)
                if not (plausible_rpm(rpm) and plausible_comp(comp) and plausible_torque(tq)): break
                rows.append((rpm, comp, tq, q, 'row_f'))
                q += ROWF_STRUCT.size
                continue
            if data[q:q+len(SIG_ENDVAR)] == SIG_ENDVAR:
                # terminal oddball, read & stop
                q += len(SIG_ENDVAR)
                if q + ENDVAR_STRUCT.size > len(data): break
                rpm_i, comp, b = ENDVAR_STRUCT.unpack_from(data, q)
                rows.append((float(rpm_i), comp, None, q, 'endvar'))
                q += ENDVAR_STRUCT.size
                break
            # no known row signature -> end this table
            break
        if len(rows) >= 2:  # must have at least 0rpm + one row
            # Sort by RPM just for display clarity (source order is generally increasing already)
            tables.append((off0, sorted(rows, key=lambda r: r[0])))
    return tables

def parse_params(data: bytes):
    out = []
    for sig, (name, fmt) in PARAMS.items():
        for pos in find_all(data, sig):
            start = pos + len(sig)
            vals, endp = read_by_fmt(data, start, fmt)
            if vals is None:
                continue
            out.append((name, pos, tuple(vals)))
    return out

def detect_engine_layout(data: bytes):
    # search from the end for known tag sequences (3B-terminated families)
    tail = data[-64:] if len(data) > 64 else data
    for k, label in ENGINE_LAYOUT_CODES.items():
        i = tail.rfind(k)
        if i != -1:
            # compute absolute offset
            return label, len(data) - len(tail) + i
    return 'Unknown/Not found', None

def parse_boost_tables(data: bytes):
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
            
        rows.append((0, t0, t25, t50, t75, t100, off0, 'boost_0rpm'))
        q = p + BOOST0_STRUCT.size
        
        while q < len(data):
            # Check if we hit another boost table or end of data
            if data[q:q+len(SIG_BOOST_0RPM)] == SIG_BOOST_0RPM:
                break
            
            if data[q:q+len(SIG_BOOST_ROW)] == SIG_BOOST_ROW:
                q += len(SIG_BOOST_ROW)
                if q + BOOSTI_STRUCT.size > len(data): 
                    break
                
                rpm, t0, t25, t50, t75, t100 = BOOSTI_STRUCT.unpack_from(data, q)
                
                # Sanity checks
                if not (0 <= rpm <= 25000):
                    break
                if not all(0.5 <= v <= 3.0 for v in [t0, t25, t50, t75, t100]):
                    break
                
                rows.append((rpm, t0, t25, t50, t75, t100, q, 'boost_row'))
                q += BOOSTI_STRUCT.size
                continue
            
            # No more boost rows
            break
        
        if len(rows) >= 2:  # Must have at least 0rpm + one row
            tables.append((off0, sorted(rows, key=lambda r: r[0])))
    
    return tables

class EDFViewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("EDF Viewer (JDougNY mapping) - WITH PLOTTING 📊")
        self.geometry("1100x650")
        self._build_ui()
        self.data = None
        self.current_file = None
        self.tables = []
        self.boost_tables = []
        self.params = []
        self.layout_label = 'Unknown'
        self.modified = False

    def _format_param_value(self, val):
        """Format parameter values intelligently for display."""
        if isinstance(val, float):
            # For very small numbers, use more decimal places
            if abs(val) < 0.001 and val != 0:
                return f"{val:.8f}"
            # For normal floats
            elif abs(val) < 1000:
                return f"{val:.6g}"
            else:
                return f"{val:.2f}"
        else:
            return str(val)

    def _build_ui(self):
        menubar = tk.Menu(self)
        filem = tk.Menu(menubar, tearoff=0)
        filem.add_command(label="Open EDF...", command=self.open_file)
        filem.add_command(label="Export torque CSV...", command=self.export_csv, state='disabled')
        filem.add_command(label="Save Modified EDF...", command=self.save_modified_edf, state='disabled')
        filem.add_separator()
        filem.add_command(label="Plot Torque vs RPM", command=self.plot_torque_rpm)
        filem.add_command(label="Plot Torque vs Compression", command=self.plot_torque_compression)
        filem.add_command(label="Plot Both", command=self.plot_both)
        filem.add_separator()
        filem.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=filem)
        
        # Add Tools menu
        toolsm = tk.Menu(menubar, tearoff=0)
        toolsm.add_command(label="Scale Torque Values...", command=self.scale_torque)
        menubar.add_cascade(label="Tools", menu=toolsm)
        
        # Add Plot menu
        plotm = tk.Menu(menubar, tearoff=0)
        plotm.add_command(label="Plot Torque vs RPM", command=self.plot_torque_rpm, state='disabled')
        plotm.add_command(label="Plot Torque vs Compression", command=self.plot_torque_compression, state='disabled')
        plotm.add_command(label="Plot Both", command=self.plot_both, state='disabled')
        menubar.add_cascade(label="Plot", menu=plotm)
        
        self.config(menu=menubar)
        self._file_menu_export = filem
        self._file_menu_save_modified = filem
        self._plot_menu = plotm
        self._tools_menu = toolsm
        self._tools_menu = toolsm
        self.modified = False  # Track if data has been modified

        top = ttk.Frame(self)
        top.pack(fill='both', expand=True, padx=8, pady=8)

        left = ttk.Frame(top, width=260)
        left.pack(side='left', fill='y', padx=(0, 8))
        left.pack_propagate(False)  # Don't let children shrink the frame
        right = ttk.Frame(top)
        right.pack(side='right', fill='both', expand=True)

        # Info panel
        self.info = tk.StringVar(value="Open an EDF/EDFBIN file.")
        ttk.Label(left, textvariable=self.info, justify='left', wraplength=240).pack(anchor='nw', pady=(0,10))

        # Plot buttons panel
        plot_frame = ttk.LabelFrame(left, text="Plot Torque Curves", padding=5)
        plot_frame.pack(fill='x', pady=(0,10))
        
        self.btn_plot_rpm = ttk.Button(plot_frame, text="Torque vs RPM", 
                                       command=self.plot_torque_rpm)
        self.btn_plot_rpm.pack(fill='x', pady=2)
        
        self.btn_plot_comp = ttk.Button(plot_frame, text="Torque vs Compression", 
                                        command=self.plot_torque_compression)
        self.btn_plot_comp.pack(fill='x', pady=2)
        
        self.btn_plot_both = ttk.Button(plot_frame, text="Plot Both", 
                                        command=self.plot_both)
        self.btn_plot_both.pack(fill='x', pady=2)

        # Tree
        self.tree = ttk.Treeview(right, columns=('c1','c2','c3'), show='tree headings')
        self.tree.heading('#0', text='Item')
        self.tree.heading('c1', text='Value 1')
        self.tree.heading('c2', text='Value 2')
        self.tree.heading('c3', text='Value 3')
        self.tree.column('#0', width=380, stretch=True)
        self.tree.column('c1', width=140, anchor='e')
        self.tree.column('c2', width=140, anchor='e')
        self.tree.column('c3', width=140, anchor='e')
        self.tree.pack(fill='both', expand=True)
        
        # Bind double-click to edit parameters
        self.tree.bind('<Double-Button-1>', self.on_tree_double_click)
        
        # Store mapping of tree item IDs to parameter data for editing
        self.param_tree_items = {}  # tree_item_id -> (name, pos, vals, fmt)

        # Status
        self.status = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.status, anchor='w').pack(fill='x', padx=8, pady=(0,8))

    def open_file(self):
        path = filedialog.askopenfilename(title="Open EDF/EDFBIN", filetypes=[("EDF/EDFBIN","*.edf;*.edfx;*.bin;*.*")])
        if not path: return
        try:
            data = Path(path).read_bytes()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read file:\n{e}")
            return
        self.data = data
        self.current_file = path

        # Parse
        self.tables = parse_torque_tables(data)
        self.boost_tables = parse_boost_tables(data)
        self.params = parse_params(data)
        layout_label, layout_off = detect_engine_layout(data)

        # Populate UI
        self.tree.delete(*self.tree.get_children())
        root_file = self.tree.insert('', 'end', text=f"File: {Path(path).name}", values=('', '', ''))
        self.tree.insert(root_file, 'end', text="Byte count registers (addresses): 0x08-0x0B, 0x14-0x17, 0x24-0x27", values=('', '', ''))
        self.tree.insert(root_file, 'end', text=f"Engine layout: {layout_label}" + (f" (offset 0x{layout_off:X})" if layout_off is not None else ""), values=('', '', ''))

        # Torque tables
        tt_root = self.tree.insert(root_file, 'end', text=f"Torque tables found: {len(self.tables)}", values=('', '', ''))
        for t_idx, (off, rows) in enumerate(self.tables):
            tnode = self.tree.insert(tt_root, 'end', text=f"Table {t_idx} @ 0x{off:X} (rows={len(rows)})", values=('', '', ''))
            self.tree.insert(tnode, 'end', text="Columns: RPM, Compression (-Nm), Torque (Nm)", values=('', '', ''))
            for i, (rpm, comp, tq, ptr, kind) in enumerate(rows):
                tq_str = '' if tq is None else f"{tq:.3f}"
                self.tree.insert(tnode, 'end',
                                 text=f"Row {i:02d} [{kind}] @ 0x{ptr:X}",
                                 values=(f"{rpm:.1f}", f"{comp:.3f}", tq_str))

        # Boost tables
        bt_root = self.tree.insert(root_file, 'end', text=f"Boost tables found: {len(self.boost_tables)}", values=('', '', ''))
        for b_idx, (off, rows) in enumerate(self.boost_tables):
            bnode = self.tree.insert(bt_root, 'end', text=f"Boost Table {b_idx} @ 0x{off:X} (rows={len(rows)})", values=('', '', ''))
            self.tree.insert(bnode, 'end', text="Columns: RPM, Throttle 0%, 25%, 50%, 75%, 100% (bar)", values=('', '', ''))
            for i, (rpm, t0, t25, t50, t75, t100, ptr, kind) in enumerate(rows):
                self.tree.insert(bnode, 'end',
                                text=f"Row {i:02d} [{kind}] @ 0x{ptr:X} - {rpm} RPM",
                                values=(f"{t0:.3f}", f"{t25:.3f}", f"{t50:.3f}"))
                # Show remaining throttle values in a second row
                self.tree.insert(bnode, 'end',
                                text=f"  → Throttle 75%={t75:.3f}, 100%={t100:.3f}",
                                values=('', '', ''))

        # Params
        pr_root = self.tree.insert(root_file, 'end', text=f"Parameters found: {len(self.params)}", values=('', '', ''))
        for name, pos, vals in sorted(self.params, key=lambda x: (x[0], x[1])):
            v1 = self._format_param_value(vals[0]) if len(vals) > 0 else ''
            v2 = self._format_param_value(vals[1]) if len(vals) > 1 else ''
            v3 = self._format_param_value(vals[2]) if len(vals) > 2 else ''
            item_id = self.tree.insert(pr_root, 'end', text=f"{name} @ 0x{pos:X}", values=(v1, v2, v3))
            
            # Store parameter info for editing - need to find the format
            fmt = None
            for sig, (pname, pfmt) in PARAMS.items():
                if pname == name:
                    fmt = pfmt
                    break
            self.param_tree_items[item_id] = (name, pos, vals, fmt)

        # Calculate and display unknown bytes
        unknown_root = self.tree.insert(root_file, 'end', text="Unknown/Unparsed Data", values=('', '', ''))
        known_ranges = self._calculate_known_ranges()
        unknown_bytes = self._calculate_unknown_bytes(known_ranges)
        
        self.tree.insert(unknown_root, 'end', 
                        text=f"Total unknown bytes: {unknown_bytes} / {len(data)} ({unknown_bytes/len(data)*100:.1f}%)", 
                        values=('', '', ''))
        
        # Show ALL unknown regions (not just first 5)
        unknown_regions = self._get_unknown_regions(known_ranges, max_regions=999999)
        
        self.tree.insert(unknown_root, 'end',
                       text=f"Unknown regions found: {len(unknown_regions)}",
                       values=('', '', ''))
        
        for idx, (region_start, region_end) in enumerate(unknown_regions):
            region_size = region_end - region_start
            region_data = data[region_start:region_end]
            
            # Analyze patterns in this region
            hex_preview = region_data[:64].hex()
            if region_size > 64:
                hex_preview += "..."
            
            # Look for repeating patterns
            pattern_info = self._analyze_region_patterns(region_data)
            
            region_node = self.tree.insert(unknown_root, 'end',
                           text=f"Region {idx+1}: 0x{region_start:X}-0x{region_end:X} ({region_size} bytes)",
                           values=('', '', ''))
            
            self.tree.insert(region_node, 'end',
                           text=f"Hex: {hex_preview}",
                           values=('', '', ''))
            
            if pattern_info:
                self.tree.insert(region_node, 'end',
                               text=f"Pattern: {pattern_info}",
                               values=('', '', ''))

        self.tree.item(root_file, open=True)
        self.tree.item(tt_root, open=True)
        self.tree.item(pr_root, open=True)

        self.info.set(f"Loaded: {Path(path).name}\n"
                      f"Torque tables: {len(self.tables)}\n"
                      f"Boost tables: {len(self.boost_tables)}\n"
                      f"Params: {len(self.params)}\n"
                      f"Engine layout: {layout_label}")
        self.status.set("Ready")
        self._file_menu_export.entryconfig("Export torque CSV...", state='normal')
        
        # Enable plot menu items
        if self.tables:
            self._plot_menu.entryconfig("Plot Torque vs RPM", state='normal')
            self._plot_menu.entryconfig("Plot Torque vs Compression", state='normal')
            self._plot_menu.entryconfig("Plot Both", state='normal')

    def _calculate_known_ranges(self):
        """Calculate all byte ranges that we've parsed and know about."""
        ranges = []
        
        # Torque tables
        for off, rows in self.tables:
            for rpm, comp, tq, ptr, kind in rows:
                if kind == '0rpm':
                    # Signature + data
                    ranges.append((off, off + len(SIG_0RPM) + ROW0_STRUCT.size))
                elif kind == 'row_i':
                    # Signature before ptr + data
                    ranges.append((ptr - len(SIG_ROW_I), ptr + ROWI_STRUCT.size))
                elif kind == 'row_f':
                    # Signature before ptr + data
                    ranges.append((ptr - len(SIG_ROW_F), ptr + ROWF_STRUCT.size))
                elif kind == 'endvar':
                    ranges.append((ptr - len(SIG_ENDVAR), ptr + ENDVAR_STRUCT.size))
        
        # Boost tables
        for off, rows in self.boost_tables:
            for rpm, t0, t25, t50, t75, t100, ptr, kind in rows:
                if kind == 'boost_0rpm':
                    # Signature + data
                    ranges.append((off, off + len(SIG_BOOST_0RPM) + BOOST0_STRUCT.size))
                elif kind == 'boost_row':
                    # Signature before ptr + data
                    ranges.append((ptr - len(SIG_BOOST_ROW), ptr + BOOSTI_STRUCT.size))
        
        # Parameters
        for name, pos, vals, fmt in self.param_tree_items.values():
            # Find signature length for this parameter
            sig_len = 0
            for sig, (pname, pfmt) in PARAMS.items():
                if pname == name:
                    sig_len = len(sig)
                    break
            
            # Calculate data length
            data_len = 0
            for f in fmt:
                if f == 'f' or f == 'i':
                    data_len += 4
                elif f == 'b':
                    data_len += 1
            
            ranges.append((pos, pos + sig_len + data_len))
        
        # Merge overlapping ranges
        if ranges:
            ranges.sort()
            merged = [ranges[0]]
            for start, end in ranges[1:]:
                if start <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], end))
                else:
                    merged.append((start, end))
            return merged
        return []

    def _calculate_unknown_bytes(self, known_ranges):
        """Calculate total number of unknown bytes."""
        if not self.data:
            return 0
        
        known_bytes = sum(end - start for start, end in known_ranges)
        return len(self.data) - known_bytes

    def _get_unknown_regions(self, known_ranges, max_regions=10):
        """Get list of unknown byte regions."""
        if not self.data or not known_ranges:
            return [(0, len(self.data))] if self.data else []
        
        unknown = []
        file_size = len(self.data)
        
        # Check before first known range
        if known_ranges[0][0] > 0:
            unknown.append((0, known_ranges[0][0]))
        
        # Check gaps between known ranges
        for i in range(len(known_ranges) - 1):
            gap_start = known_ranges[i][1]
            gap_end = known_ranges[i + 1][0]
            if gap_end > gap_start:
                unknown.append((gap_start, gap_end))
        
        # Check after last known range
        if known_ranges[-1][1] < file_size:
            unknown.append((known_ranges[-1][1], file_size))
        
        return unknown[:max_regions]
    
    def _analyze_region_patterns(self, data):
        """Analyze patterns in unknown data region."""
        if len(data) < 4:
            return None
        
        patterns = []
        
        # Check for repeating signature-like patterns
        # Look for sequences like [24 04 45 49 29 04] that you mentioned
        sig_24_04 = b'\x24\x04\x45\x49\x29\x04'
        count_24_04 = data.count(sig_24_04)
        if count_24_04 > 1:
            patterns.append(f"Repeated signature [24 04 45 49 29 04]: {count_24_04}x")
        
        # Check for other common 4-byte patterns
        if len(data) >= 100:
            # Sample every 20 bytes to find structure size
            sample_positions = []
            test_sig = data[:4]
            pos = 0
            while pos < len(data):
                idx = data.find(test_sig, pos)
                if idx == -1:
                    break
                sample_positions.append(idx)
                pos = idx + 1
            
            if len(sample_positions) > 2:
                # Calculate distances between occurrences
                distances = [sample_positions[i+1] - sample_positions[i] 
                           for i in range(len(sample_positions)-1)]
                # Find most common distance
                if distances:
                    most_common_dist = max(set(distances), key=distances.count)
                    if distances.count(most_common_dist) > len(distances) * 0.5:
                        patterns.append(f"Structure size ~{most_common_dist} bytes (sig: {test_sig.hex()})")
        
        # Check for mostly null bytes
        null_count = data.count(b'\x00')
        if null_count > len(data) * 0.9:
            patterns.append(f"Mostly null ({null_count}/{len(data)} bytes)")
        
        # Check for mostly ASCII text
        try:
            decoded = data.decode('ascii')
            if decoded.isprintable():
                patterns.append(f"ASCII text: {decoded[:50]}")
        except:
            pass
        
        return " | ".join(patterns) if patterns else None

    def on_tree_double_click(self, event):
        """Handle double-click on tree items to edit parameters."""
        item_id = self.tree.focus()
        if item_id not in self.param_tree_items:
            return
        
        name, pos, vals, fmt = self.param_tree_items[item_id]
        
        if fmt is None:
            messagebox.showwarning("Cannot Edit", "Format unknown for this parameter.")
            return
        
        # Create edit dialog
        dialog = tk.Toplevel(self)
        dialog.title(f"Edit {name}")
        dialog.geometry("400x250")
        dialog.transient(self)
        dialog.grab_set()
        
        ttk.Label(dialog, text=f"Editing: {name}", font=('', 10, 'bold')).pack(pady=(10, 5))
        ttk.Label(dialog, text=f"Location: 0x{pos:X}", font=('', 9)).pack(pady=(0, 10))
        
        # Create entry fields for each value
        entries = []
        for i, (val, f) in enumerate(zip(vals, fmt)):
            frame = ttk.Frame(dialog)
            frame.pack(pady=5, padx=20, fill='x')
            
            type_str = {'f': 'Float', 'i': 'Integer', 'b': 'Byte'}[f]
            ttk.Label(frame, text=f"Value {i+1} ({type_str}):", width=20).pack(side='left')
            
            entry = ttk.Entry(frame, width=20)
            entry.pack(side='left', padx=10)
            if f == 'f':
                entry.insert(0, f"{val:.6g}")
            else:
                entry.insert(0, str(val))
            entries.append((entry, f))
        
        result = {'confirmed': False}
        
        def on_save():
            try:
                new_vals = []
                for entry, f in entries:
                    val_str = entry.get()
                    if f == 'f':
                        new_vals.append(float(val_str))
                    elif f == 'i':
                        new_vals.append(int(val_str))
                    elif f == 'b':
                        v = int(val_str)
                        if not 0 <= v <= 255:
                            raise ValueError("Byte must be 0-255")
                        new_vals.append(v)
                
                result['confirmed'] = True
                result['values'] = new_vals
                dialog.destroy()
            except ValueError as e:
                messagebox.showerror("Invalid Input", f"Error: {e}")
        
        def on_cancel():
            dialog.destroy()
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="Save", command=on_save, width=10).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Cancel", command=on_cancel, width=10).pack(side='left', padx=5)
        
        dialog.wait_window()
        
        if not result['confirmed']:
            return
        
        # Apply the changes
        self._apply_parameter_edit(name, pos, vals, result['values'], fmt)

    def _apply_parameter_edit(self, name, pos, old_vals, new_vals, fmt):
        """Apply parameter edit to the data."""
        # Convert to bytearray if needed
        if not isinstance(self.data, bytearray):
            self.data = bytearray(self.data)
            self.modified = True
        
        # Find signature length
        sig_len = 0
        for sig, (pname, pfmt) in PARAMS.items():
            if pname == name:
                sig_len = len(sig)
                break
        
        # Write new values at correct offset (after signature)
        write_pos = pos + sig_len
        for val, f in zip(new_vals, fmt):
            if f == 'f':
                struct.pack_into('<f', self.data, write_pos, val)
                write_pos += 4
            elif f == 'i':
                struct.pack_into('<i', self.data, write_pos, val)
                write_pos += 4
            elif f == 'b':
                self.data[write_pos] = val
                write_pos += 1
        
        self.modified = True
        
        # Update the display
        self.params = parse_params(self.data)
        self._refresh_tree_display()
        
        # Enable save
        self._file_menu_save_modified.entryconfig("Save Modified EDF...", state='normal')
        
        self.status.set(f"Modified {name} at 0x{pos:X}")
        messagebox.showinfo("Success", f"Parameter {name} updated successfully!")

    def _refresh_tree_display(self):
        """Refresh the tree display after modifications."""
        if not self.current_file:
            return
        
        self.tree.delete(*self.tree.get_children())
        self.param_tree_items.clear()
        
        layout_label, layout_off = detect_engine_layout(self.data)
        
        root_file = self.tree.insert('', 'end', text=f"File: {Path(self.current_file).name}{' [MODIFIED]' if self.modified else ''}", values=('', '', ''))
        self.tree.insert(root_file, 'end', text="Byte count registers (addresses): 0x08-0x0B, 0x14-0x17, 0x24-0x27", values=('', '', ''))
        self.tree.insert(root_file, 'end', text=f"Engine layout: {layout_label}" + (f" (offset 0x{layout_off:X})" if layout_off is not None else ""), values=('', '', ''))
        
        # Torque tables
        tt_root = self.tree.insert(root_file, 'end', text=f"Torque tables found: {len(self.tables)}", values=('', '', ''))
        for t_idx, (off, rows) in enumerate(self.tables):
            tnode = self.tree.insert(tt_root, 'end', text=f"Table {t_idx} @ 0x{off:X} (rows={len(rows)})", values=('', '', ''))
            self.tree.insert(tnode, 'end', text="Columns: RPM, Compression (-Nm), Torque (Nm)", values=('', '', ''))
            for i, (rpm, comp, tq, ptr, kind) in enumerate(rows):
                tq_str = '' if tq is None else f"{tq:.3f}"
                self.tree.insert(tnode, 'end',
                                text=f"Row {i:02d} [{kind}] @ 0x{ptr:X}",
                                values=(f"{rpm:.1f}", f"{comp:.3f}", tq_str))
        
        # Boost tables
        bt_root = self.tree.insert(root_file, 'end', text=f"Boost tables found: {len(self.boost_tables)}", values=('', '', ''))
        for b_idx, (off, rows) in enumerate(self.boost_tables):
            bnode = self.tree.insert(bt_root, 'end', text=f"Boost Table {b_idx} @ 0x{off:X} (rows={len(rows)})", values=('', '', ''))
            self.tree.insert(bnode, 'end', text="Columns: RPM, Throttle 0%, 25%, 50%, 75%, 100% (bar)", values=('', '', ''))
            for i, (rpm, t0, t25, t50, t75, t100, ptr, kind) in enumerate(rows):
                self.tree.insert(bnode, 'end',
                                text=f"Row {i:02d} [{kind}] @ 0x{ptr:X} - {rpm} RPM",
                                values=(f"{t0:.3f}", f"{t25:.3f}", f"{t50:.3f}"))
                self.tree.insert(bnode, 'end',
                                text=f"  → Throttle 75%={t75:.3f}, 100%={t100:.3f}",
                                values=('', '', ''))
        
        # Params
        pr_root = self.tree.insert(root_file, 'end', text=f"Parameters found: {len(self.params)}", values=('', '', ''))
        for name, pos, vals in sorted(self.params, key=lambda x: (x[0], x[1])):
            v1 = self._format_param_value(vals[0]) if len(vals) > 0 else ''
            v2 = self._format_param_value(vals[1]) if len(vals) > 1 else ''
            v3 = self._format_param_value(vals[2]) if len(vals) > 2 else ''
            item_id = self.tree.insert(pr_root, 'end', text=f"{name} @ 0x{pos:X}", values=(v1, v2, v3))
            
            fmt = None
            for sig, (pname, pfmt) in PARAMS.items():
                if pname == name:
                    fmt = pfmt
                    break
            self.param_tree_items[item_id] = (name, pos, vals, fmt)
        
        # Unknown bytes
        unknown_root = self.tree.insert(root_file, 'end', text="Unknown/Unparsed Data", values=('', '', ''))
        known_ranges = self._calculate_known_ranges()
        unknown_bytes = self._calculate_unknown_bytes(known_ranges)
        
        self.tree.insert(unknown_root, 'end', 
                        text=f"Total unknown bytes: {unknown_bytes} / {len(self.data)} ({unknown_bytes/len(self.data)*100:.1f}%)", 
                        values=('', '', ''))
        
        unknown_regions = self._get_unknown_regions(known_ranges, max_regions=999999)
        
        self.tree.insert(unknown_root, 'end',
                       text=f"Unknown regions found: {len(unknown_regions)}",
                       values=('', '', ''))
        
        for idx, (region_start, region_end) in enumerate(unknown_regions):
            region_size = region_end - region_start
            region_data = self.data[region_start:region_end]
            
            hex_preview = region_data[:64].hex()
            if region_size > 64:
                hex_preview += "..."
            
            pattern_info = self._analyze_region_patterns(region_data)
            
            region_node = self.tree.insert(unknown_root, 'end',
                           text=f"Region {idx+1}: 0x{region_start:X}-0x{region_end:X} ({region_size} bytes)",
                           values=('', '', ''))
            
            self.tree.insert(region_node, 'end',
                           text=f"Hex: {hex_preview}",
                           values=('', '', ''))
            
            if pattern_info:
                self.tree.insert(region_node, 'end',
                               text=f"Pattern: {pattern_info}",
                               values=('', '', ''))
        
        self.tree.item(root_file, open=True)
        self.tree.item(tt_root, open=True)
        self.tree.item(pr_root, open=True)

    def export_csv(self):
        if not self.tables:
            messagebox.showwarning("No data", "No torque tables parsed.")
            return
        path = filedialog.asksaveasfilename(title="Save torque CSV", defaultextension=".csv",
                                            filetypes=[("CSV","*.csv")])
        if not path: return
        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(['table_index','row_index','rpm','compression','torque','row_kind','payload_offset_hex','table_start_hex','source_file'])
                for t_idx, (off, rows) in enumerate(self.tables):
                    for r_idx, (rpm, comp, tq, ptr, kind) in enumerate(rows):
                        w.writerow([t_idx, r_idx, rpm, comp, '' if tq is None else tq, kind, f"0x{ptr:X}", f"0x{off:X}", self.current_file or ''])
            messagebox.showinfo("Saved", f"CSV saved:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save CSV:\n{e}")

    def scale_torque(self):
        if not self.tables:
            messagebox.showwarning("No data", "No torque tables to modify.")
            return
        
        # Create dialog to get percentage
        dialog = tk.Toplevel(self)
        dialog.title("Scale Torque")
        dialog.geometry("300x150")
        dialog.transient(self)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Enter percentage to scale torque:\n(e.g., 110 for +10%, 90 for -10%)", 
                  justify='center').pack(pady=10)
        
        entry = ttk.Entry(dialog, width=15)
        entry.pack(pady=5)
        entry.insert(0, "100")
        entry.select_range(0, tk.END)
        entry.focus()
        
        result = {'value': None}
        
        def apply_scale():
            try:
                percent = float(entry.get())
                if percent <= 0:
                    messagebox.showerror("Error", "Percentage must be positive")
                    return
                result['value'] = percent / 100.0
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid number")
        
        def cancel():
            dialog.destroy()
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Apply", command=apply_scale).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Cancel", command=cancel).pack(side='left', padx=5)
        
        entry.bind('<Return>', lambda e: apply_scale())
        entry.bind('<Escape>', lambda e: cancel())
        
        self.wait_window(dialog)
        
        if result['value'] is None:
            return
        
        scale_factor = result['value']
        
        print(f"=== SCALE TORQUE DEBUG ===")
        print(f"Scale factor: {scale_factor} ({scale_factor*100:.1f}%)")
        print(f"self.data type before: {type(self.data)}")
        print(f"self.data length: {len(self.data)}")
        print(f"Number of tables: {len(self.tables)}")
        
        # Make a copy of data as bytearray if not already modified
        if not self.modified:
            self.data = bytearray(self.data)
            self.modified = True
        elif not isinstance(self.data, bytearray):
            # Ensure it's a bytearray even if somehow it's bytes
            self.data = bytearray(self.data)
        
        print(f"self.data type after conversion: {type(self.data)}")
        print(f"self.modified: {self.modified}")
        
        # Scale torque values in memory and update structures
        modifications = 0
        for t_idx, (off, rows) in enumerate(self.tables):
            print(f"\n--- Table {t_idx} @ offset 0x{off:X} ---")
            print(f"  Rows in table: {len(rows)}")
            new_rows = []
            for row_idx, (rpm, comp, tq, ptr, kind) in enumerate(rows):
                if tq is not None:
                    new_tq = tq * scale_factor
                    print(f"  Row {row_idx} [{kind}] @ 0x{ptr:X}: RPM={rpm:.1f}, old_tq={tq:.3f}, new_tq={new_tq:.3f}")
                    
                    # Write back to binary data based on row type
                    # NOTE: ptr points to different locations depending on kind:
                    # - '0rpm': ptr points to START of signature (need to skip signature)
                    # - 'row_i'/'row_f': ptr points to data AFTER signature
                    
                    if kind == '0rpm':
                        # ptr is at the signature start, data is after 7-byte signature
                        data_offset = ptr + len(SIG_0RPM)
                        original = self.data[data_offset:data_offset+9]
                        print(f"    Signature offset: 0x{ptr:X}, Data offset: 0x{data_offset:X}")
                        print(f"    Original bytes: {original.hex()}")
                        
                        # 0rpm row: byte, float, float
                        b0 = self.data[data_offset]
                        struct.pack_into('<Bff', self.data, data_offset, b0, comp, new_tq)
                        
                        modified = self.data[data_offset:data_offset+9]
                        print(f"    Modified bytes: {modified.hex()}")
                        
                    elif kind == 'row_i':
                        # ptr already points to data after signature
                        original = self.data[ptr:ptr+12]
                        print(f"    Original bytes (row_i): {original.hex()}")
                        
                        # int32, float, float
                        struct.pack_into('<iff', self.data, ptr, int(rpm), comp, new_tq)
                        
                        modified = self.data[ptr:ptr+12]
                        print(f"    Modified bytes (row_i): {modified.hex()}")
                        
                    elif kind == 'row_f':
                        # ptr already points to data after signature
                        original = self.data[ptr:ptr+12]
                        print(f"    Original bytes (row_f): {original.hex()}")
                        
                        # float, float, float
                        struct.pack_into('<fff', self.data, ptr, rpm, comp, new_tq)
                        
                        modified = self.data[ptr:ptr+12]
                        print(f"    Modified bytes (row_f): {modified.hex()}")
                    
                    # endvar doesn't have torque, skip
                    new_rows.append((rpm, comp, new_tq, ptr, kind))
                    modifications += 1
                else:
                    print(f"  Row {row_idx} [{kind}] @ 0x{ptr:X}: RPM={rpm:.1f}, tq=None (skipped)")
                    new_rows.append((rpm, comp, tq, ptr, kind))
            # Update table with new values
            self.tables[t_idx] = (off, new_rows)
        
        print(f"\nTotal modifications: {modifications}")
        print(f"=== END DEBUG ===\n")
        
        # Refresh display
        self.tree.delete(*self.tree.get_children())
        root_file = self.tree.insert('', 'end', text=f"File: {Path(self.current_file).name} [MODIFIED]", values=('', '', ''))
        
        # Re-parse to get layout
        layout_label, layout_off = detect_engine_layout(self.data)
        self.tree.insert(root_file, 'end', text="Byte count registers (addresses): 0x08-0x0B, 0x14-0x17, 0x24-0x27", values=('', '', ''))
        self.tree.insert(root_file, 'end', text=f"Engine layout: {layout_label}" + (f" (offset 0x{layout_off:X})" if layout_off is not None else ""), values=('', '', ''))
        
        # Torque tables with new values
        tt_root = self.tree.insert(root_file, 'end', text=f"Torque tables found: {len(self.tables)}", values=('', '', ''))
        for t_idx, (off, rows) in enumerate(self.tables):
            tnode = self.tree.insert(tt_root, 'end', text=f"Table {t_idx} @ 0x{off:X} (rows={len(rows)})", values=('', '', ''))
            self.tree.insert(tnode, 'end', text="Columns: RPM, Compression (-Nm), Torque (Nm)", values=('', '', ''))
            for i, (rpm, comp, tq, ptr, kind) in enumerate(rows):
                tq_str = '' if tq is None else f"{tq:.3f}"
                self.tree.insert(tnode, 'end',
                                 text=f"Row {i:02d} [{kind}] @ 0x{ptr:X}",
                                 values=(f"{rpm:.1f}", f"{comp:.3f}", tq_str))
        
        # Re-add params
        pr_root = self.tree.insert(root_file, 'end', text=f"Parameters found: {len(self.params)}", values=('', '', ''))
        for name, pos, vals in sorted(self.params, key=lambda x: (x[0], x[1])):
            v1 = f"{vals[0]:.6g}" if len(vals) > 0 and isinstance(vals[0], float) else (str(vals[0]) if len(vals) > 0 else '')
            v2 = f"{vals[1]:.6g}" if len(vals) > 1 and isinstance(vals[1], float) else (str(vals[1]) if len(vals) > 1 else '')
            v3 = f"{vals[2]:.6g}" if len(vals) > 2 and isinstance(vals[2], float) else (str(vals[2]) if len(vals) > 2 else '')
            self.tree.insert(pr_root, 'end', text=f"{name} @ 0x{pos:X}", values=(v1, v2, v3))
        
        self.tree.item(root_file, open=True)
        self.tree.item(tt_root, open=True)
        
        self.info.set(f"Loaded: {Path(self.current_file).name}\n[MODIFIED]\n"
                      f"Torque scaled by {scale_factor*100:.1f}%\n"
                      f"Torque tables: {len(self.tables)}\n"
                      f"Params: {len(self.params)}")
        self.status.set(f"Scaled {modifications} torque values by {scale_factor*100:.1f}%")
        
        # Enable save option
        self._file_menu_save_modified.entryconfig("Save Modified EDF...", state='normal')
        
        messagebox.showinfo("Success", f"Scaled {modifications} torque values by {scale_factor*100:.1f}%\n\n"
                           "Use File > Save Modified EDF to save changes.")

    def save_modified_edf(self):
        print(f"\n=== SAVE MODIFIED EDF DEBUG ===")
        print(f"self.modified: {self.modified}")
        print(f"self.data type: {type(self.data)}")
        print(f"self.data length: {len(self.data) if self.data else 'None'}")
        
        if not self.modified:
            messagebox.showwarning("No changes", "No modifications have been made.")
            return
        
        # Suggest a filename
        if self.current_file:
            original_path = Path(self.current_file)
            suggested_name = original_path.stem + "_modified" + original_path.suffix
        else:
            suggested_name = "modified.edf"
        
        print(f"Suggested filename: {suggested_name}")
        
        path = filedialog.asksaveasfilename(
            title="Save Modified EDF",
            initialfile=suggested_name,
            defaultextension=".edf",
            filetypes=[("EDF files", "*.edf"), ("EDFBIN files", "*.bin"), ("All files", "*.*")]
        )
        
        if not path:
            print("User cancelled save dialog")
            return
        
        print(f"Saving to: {path}")
        
        try:
            with open(path, 'wb') as f:
                bytes_written = f.write(self.data)
            print(f"Bytes written: {bytes_written}")
            print(f"=== END SAVE DEBUG ===\n")
            messagebox.showinfo("Saved", f"Modified EDF saved to:\n{path}")
            self.status.set(f"Saved modified EDF: {Path(path).name}")
        except Exception as e:
            print(f"ERROR during save: {e}")
            print(f"=== END SAVE DEBUG ===\n")
            messagebox.showerror("Error", f"Failed to save file:\n{e}")

    def plot_torque_rpm(self):
        if not self.tables:
            messagebox.showwarning("No data", "No torque tables to plot.")
            return
        
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            messagebox.showerror("Error", "matplotlib is required for plotting.\nInstall it with: pip install matplotlib")
            return
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        for t_idx, (off, rows) in enumerate(self.tables):
            rpms = []
            torques = []
            for rpm, comp, tq, ptr, kind in rows:
                if tq is not None:  # Skip endvar rows without torque
                    rpms.append(rpm)
                    torques.append(tq)
            
            if rpms:
                ax.plot(rpms, torques, marker='o', label=f'Table {t_idx} @ 0x{off:X}', linewidth=2, markersize=4)
        
        ax.set_xlabel('RPM', fontsize=12)
        ax.set_ylabel('Torque (Nm)', fontsize=12)
        ax.set_title(f'Torque vs RPM - {Path(self.current_file).name if self.current_file else "EDF File"}', fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.legend()
        plt.tight_layout()
        plt.show()

    def plot_torque_compression(self):
        if not self.tables:
            messagebox.showwarning("No data", "No torque tables to plot.")
            return
        
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            messagebox.showerror("Error", "matplotlib is required for plotting.\nInstall it with: pip install matplotlib")
            return
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        for t_idx, (off, rows) in enumerate(self.tables):
            comps = []
            torques = []
            for rpm, comp, tq, ptr, kind in rows:
                if tq is not None:  # Skip endvar rows without torque
                    comps.append(comp)
                    torques.append(tq)
            
            if comps:
                ax.plot(comps, torques, marker='o', label=f'Table {t_idx} @ 0x{off:X}', linewidth=2, markersize=4)
        
        ax.set_xlabel('Compression (-Nm)', fontsize=12)
        ax.set_ylabel('Torque (Nm)', fontsize=12)
        ax.set_title(f'Torque vs Compression - {Path(self.current_file).name if self.current_file else "EDF File"}', fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.legend()
        plt.tight_layout()
        plt.show()

    def plot_both(self):
        if not self.tables:
            messagebox.showwarning("No data", "No torque tables to plot.")
            return
        
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            messagebox.showerror("Error", "matplotlib is required for plotting.\nInstall it with: pip install matplotlib")
            return
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        for t_idx, (off, rows) in enumerate(self.tables):
            rpms = []
            comps = []
            torques = []
            for rpm, comp, tq, ptr, kind in rows:
                if tq is not None:  # Skip endvar rows without torque
                    rpms.append(rpm)
                    comps.append(comp)
                    torques.append(tq)
            
            if rpms:
                label = f'Table {t_idx} @ 0x{off:X}'
                ax1.plot(rpms, torques, marker='o', label=label, linewidth=2, markersize=4)
                ax2.plot(comps, torques, marker='o', label=label, linewidth=2, markersize=4)
        
        # Configure left plot (RPM)
        ax1.set_xlabel('RPM', fontsize=12)
        ax1.set_ylabel('Torque (Nm)', fontsize=12)
        ax1.set_title('Torque vs RPM', fontsize=13)
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # Configure right plot (Compression)
        ax2.set_xlabel('Compression (-Nm)', fontsize=12)
        ax2.set_ylabel('Torque (Nm)', fontsize=12)
        ax2.set_title('Torque vs Compression', fontsize=13)
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        
        fig.suptitle(f'{Path(self.current_file).name if self.current_file else "EDF File"}', fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.show()

def main():
    app = EDFViewer()
    app.mainloop()

if __name__ == '__main__':
    main()
