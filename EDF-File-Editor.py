#!/usr/bin/env python3
# EDF/EDFBIN viewer with integrated hex viewer
# Based on JDougNY's "Project CARS Engine translation" mapping (v1.01)
# Supports torque curves and a set of common parameter tags.
#
# Python 3.9+ recommended. No external deps except tkinter (standard lib).

import struct
import csv
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

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
    b'\x22\x40\xF1\xD2\xB9': ('Unknown_EngineFreeRevs', ('f',)),  # Makes engine rev out of control
    b'\x24\x4D\x23\x97\x54\xA2': ('IdleRPMLogic', ('f','f')),   # alt 52: int,int
    b'\x24\x4D\x23\x97\x54\x52': ('IdleRPMLogic', ('i','i')),
    b'\x22\x21\x98\x99\xAE': ('LaunchEfficiency', ('f',)),
    b'\x24\x79\x02\xB6\xBD\xA2': ('LaunchRPMLogic', ('f','f')),
    b'\x24\xDE\xA7\x2E\xB7\x23\x00': ('RevLimitRange', ('f','b','b')),  # alt 13 00: int,b,b
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
            if len(fmt) == 0:
                # No value variant (e.g., RevLimitSetting_NoValue)
                out.append((name, pos, ()))
            else:
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
        self.title("EDF Viewer (JDougNY mapping) - WITH HEX VIEW 📊")
        self.geometry("1400x750")
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
        # Configure tree row height
        style = ttk.Style(self)
        style.configure("Treeview", rowheight=25)
        
        menubar = tk.Menu(self)
        filem = tk.Menu(menubar, tearoff=0)
        filem.add_command(label="Open EDF...", command=self.open_file)
        filem.add_command(label="Export torque CSV...", command=self.export_csv, state='disabled')
        filem.add_command(label="Save Modified EDF...", command=self.save_modified_edf, state='disabled')
        filem.add_separator()
        filem.add_command(label="Plot Torque vs RPM", command=self.plot_torque_rpm)
        filem.add_command(label="Plot Compression vs RPM", command=self.plot_torque_compression)
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
        plotm.add_command(label="Plot Compression vs RPM", command=self.plot_torque_compression, state='disabled')
        plotm.add_command(label="Plot Both", command=self.plot_both, state='disabled')
        menubar.add_cascade(label="Plot", menu=plotm)
        
        self.config(menu=menubar)
        self._file_menu_export = filem
        self._file_menu_save_modified = filem
        self._plot_menu = plotm
        self._tools_menu = toolsm

        # ===== Paned layout (left / middle / right) =====
        pw = ttk.Panedwindow(self, orient='horizontal')
        pw.pack(fill='both', expand=True, padx=8, pady=8)

        # -- Left panel (info) --
        left = ttk.Frame(pw, width=280)
        pw.add(left, weight=0)

        # Info panel
        self.info = tk.StringVar(value="Open an EDF/EDFBIN file.\n\nClick on tree items to see hex data.")
        ttk.Label(left, textvariable=self.info, justify='left', wraplength=260).pack(anchor='nw', pady=(0,10))

        # Plot buttons panel
        plot_frame = ttk.LabelFrame(left, text="Plot Torque Curves", padding=5)
        plot_frame.pack(fill='x', pady=(0,10))
        
        self.btn_plot_rpm = ttk.Button(plot_frame, text="Torque vs RPM", 
                                       command=self.plot_torque_rpm)
        self.btn_plot_rpm.pack(fill='x', pady=2)
        
        self.btn_plot_comp = ttk.Button(plot_frame, text="Compression vs RPM", 
                                        command=self.plot_torque_compression)
        self.btn_plot_comp.pack(fill='x', pady=2)
        
        self.btn_plot_both = ttk.Button(plot_frame, text="Plot Both", 
                                        command=self.plot_both)
        self.btn_plot_both.pack(fill='x', pady=2)

        # -- Middle panel (Tree with scrollbars) --
        middle = ttk.Frame(pw)
        pw.add(middle, weight=3)

        tree_frame = ttk.Frame(middle)
        tree_frame.pack(fill='both', expand=True)

        self.tree = ttk.Treeview(tree_frame, columns=('c1','c2','c3'), show='tree headings')
        self.tree.heading('#0', text='Item')
        self.tree.heading('c1', text='Value 1')
        self.tree.heading('c2', text='Value 2')
        self.tree.heading('c3', text='Value 3')
        self.tree.column('#0', width=380, stretch=True)
        self.tree.column('c1', width=140, anchor='e')
        self.tree.column('c2', width=140, anchor='e')
        self.tree.column('c3', width=140, anchor='e')

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        # Bind tree selection to hex viewer
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        self.tree.bind('<Double-Button-1>', self.on_tree_double_click)
        
        # Store mapping of tree item IDs to parameter data for editing
        self.param_tree_items = {}  # tree_item_id -> (name, pos, vals, fmt)

        # -- Right panel (Hex viewer with scrollbars) --
        right = ttk.Frame(pw, width=520)
        pw.add(right, weight=2)

        hex_label = ttk.Label(right, text="Hex View", font=("", 10, "bold"))
        hex_label.pack(anchor='nw', pady=(0, 5))

        hex_frame = ttk.Frame(right)
        hex_frame.pack(fill='both', expand=True)

        self.hex_text = tk.Text(hex_frame, wrap=tk.NONE, font=("Courier", 9),
                                width=60, bg="#f5f5f5", relief=tk.SUNKEN, bd=1)
        hex_vsb = ttk.Scrollbar(hex_frame, orient="vertical", command=self.hex_text.yview)
        hex_hsb = ttk.Scrollbar(hex_frame, orient="horizontal", command=self.hex_text.xview)
        self.hex_text.configure(yscrollcommand=hex_vsb.set, xscrollcommand=hex_hsb.set)

        hex_frame.grid_rowconfigure(0, weight=1)
        hex_frame.grid_columnconfigure(0, weight=1)
        self.hex_text.grid(row=0, column=0, sticky='nsew')
        hex_vsb.grid(row=0, column=1, sticky='ns')
        hex_hsb.grid(row=1, column=0, sticky='ew')

        # Hex highlighting tags
        self.hex_text.tag_configure('highlight', background='#ffff00', foreground='#000000')
        self.hex_text.tag_configure('table_highlight', background='#90ee90', foreground='#000000')
        self.hex_text.tag_configure('param_highlight', background='#ffa500', foreground='#000000')
        self.hex_text.tag_configure('editing', background='#ff6b6b', foreground='#ffffff')
        
        # Bind left-click for hex editing
        self.hex_text.bind('<Button-1>', self.on_hex_click)
        
        self.hex_text.config(state='disabled')
        
        # Track if warning has been shown
        self.hex_edit_warning_shown = False

        # Status
        self.status = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.status, anchor='w').pack(fill='x', padx=8, pady=(0,8))

    def update_hex_view(self):
        """Generate and display hex view of the file"""
        if not self.data:
            return
        
        self.hex_text.config(state='normal')
        self.hex_text.delete('1.0', tk.END)
        
        # Generate hex dump (16 bytes per line)
        lines = []
        for i in range(0, len(self.data), 16):
            # Offset
            offset = f"{i:08X}  "
            
            # Hex bytes
            hex_part = ""
            ascii_part = ""
            for j in range(16):
                if i + j < len(self.data):
                    byte = self.data[i + j]
                    hex_part += f"{byte:02X} "
                    # ASCII representation
                    ascii_part += chr(byte) if 32 <= byte < 127 else '.'
                else:
                    hex_part += "   "
                    ascii_part += " "
                
                # Add extra space in the middle
                if j == 7:
                    hex_part += " "
            
            lines.append(f"{offset}{hex_part} |{ascii_part}|")
        
        self.hex_text.insert('1.0', '\n'.join(lines))
        self.hex_text.config(state='disabled')

    def highlight_hex_range(self, start_offset: int, end_offset: int, tag: str = 'highlight'):
        """Highlight a byte range in the hex view"""
        if not self.data:
            return
        
        self.hex_text.config(state='normal')
        
        # Remove previous highlights
        self.hex_text.tag_remove('highlight', '1.0', tk.END)
        self.hex_text.tag_remove('table_highlight', '1.0', tk.END)
        self.hex_text.tag_remove('param_highlight', '1.0', tk.END)
        
        # Calculate positions for highlighting
        for offset in range(start_offset, min(end_offset, len(self.data))):
            line_num = offset // 16
            byte_in_line = offset % 16
            
            # Calculate text position for hex part
            col_start = 10 + (byte_in_line * 3)
            if byte_in_line >= 8:
                col_start += 1  # Extra space after 8th byte
            
            # Highlight hex bytes
            hex_start = f"{line_num + 1}.{col_start}"
            hex_end = f"{line_num + 1}.{col_start + 2}"
            self.hex_text.tag_add(tag, hex_start, hex_end)
            
            # Highlight ASCII representation
            ascii_col = 61 + byte_in_line
            ascii_start = f"{line_num + 1}.{ascii_col}"
            ascii_end = f"{line_num + 1}.{ascii_col + 1}"
            self.hex_text.tag_add(tag, ascii_start, ascii_end)
        
        # Scroll to show the highlighted range
        if start_offset < len(self.data):
            line_num = start_offset // 16
            self.hex_text.see(f"{line_num + 1}.0")
        
        self.hex_text.config(state='disabled')

    def on_tree_select(self, event=None):
        """Handle tree selection to highlight corresponding hex bytes"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = selection[0]
        tags = self.tree.item(item, 'tags')
        if not tags:
            return
        
        tag = tags[0]
        
        # Parse tag to determine what to highlight
        if tag.startswith("torque_table:"):
            # Highlight entire torque table
            table_idx = int(tag.split(':')[1])
            if table_idx < len(self.tables):
                off, rows = self.tables[table_idx]
                if rows:
                    # Highlight from table start to last row end
                    last_row = rows[-1]
                    rpm, comp, tq, ptr, kind = last_row
                    # Calculate end based on row type
                    if kind == '0rpm':
                        end = ptr + len(SIG_0RPM) + ROW0_STRUCT.size
                    elif kind == 'row_i':
                        end = ptr + ROWI_STRUCT.size
                    elif kind == 'row_f':
                        end = ptr + ROWF_STRUCT.size
                    elif kind == 'endvar':
                        end = ptr + ENDVAR_STRUCT.size
                    else:
                        end = ptr + 12
                    
                    self.highlight_hex_range(off, end, 'table_highlight')
        
        elif tag.startswith("torque_row:"):
            # Highlight individual torque row
            parts = tag.split(':')
            table_idx = int(parts[1])
            row_idx = int(parts[2])
            
            if table_idx < len(self.tables):
                off, rows = self.tables[table_idx]
                if row_idx < len(rows):
                    rpm, comp, tq, ptr, kind = rows[row_idx]
                    
                    if kind == '0rpm':
                        # Signature + data
                        self.highlight_hex_range(ptr, ptr + len(SIG_0RPM) + ROW0_STRUCT.size, 'highlight')
                    elif kind == 'row_i':
                        # Signature before ptr + data
                        self.highlight_hex_range(ptr - len(SIG_ROW_I), ptr + ROWI_STRUCT.size, 'highlight')
                    elif kind == 'row_f':
                        # Signature before ptr + data
                        self.highlight_hex_range(ptr - len(SIG_ROW_F), ptr + ROWF_STRUCT.size, 'highlight')
                    elif kind == 'endvar':
                        self.highlight_hex_range(ptr - len(SIG_ENDVAR), ptr + ENDVAR_STRUCT.size, 'highlight')
        
        elif tag.startswith("boost_table:"):
            # Highlight entire boost table
            table_idx = int(tag.split(':')[1])
            if table_idx < len(self.boost_tables):
                off, rows = self.boost_tables[table_idx]
                if rows:
                    last_row = rows[-1]
                    rpm, t0, t25, t50, t75, t100, ptr, kind = last_row
                    if kind == 'boost_0rpm':
                        end = ptr + len(SIG_BOOST_0RPM) + BOOST0_STRUCT.size
                    else:
                        end = ptr + BOOSTI_STRUCT.size
                    
                    self.highlight_hex_range(off, end, 'table_highlight')
        
        elif tag.startswith("param:"):
            # Highlight parameter
            param_idx = int(tag.split(':')[1])
            if param_idx < len(self.params):
                name, pos, vals = self.params[param_idx]
                
                # Find signature for this parameter
                sig_len = 0
                fmt = None
                for sig, (pname, pfmt) in PARAMS.items():
                    if pname == name:
                        sig_len = len(sig)
                        fmt = pfmt
                        break
                
                if fmt:
                    # Calculate total data size
                    data_size = sum(4 if f in ('f', 'i') else 1 for f in fmt)
                    # Highlight signature + data
                    self.highlight_hex_range(pos, pos + sig_len + data_size, 'param_highlight')

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
        self.param_tree_items.clear()
        
        root_file = self.tree.insert('', 'end', text=f"File: {Path(path).name}", values=('', '', ''))
        self.tree.insert(root_file, 'end', text="Byte count registers (addresses): 0x08-0x0B, 0x14-0x17, 0x24-0x27", values=('', '', ''))
        self.tree.insert(root_file, 'end', text=f"Engine layout: {layout_label}" + (f" (offset 0x{layout_off:X})" if layout_off is not None else ""), values=('', '', ''))

        # Torque tables
        tt_root = self.tree.insert(root_file, 'end', text=f"Torque tables found: {len(self.tables)}", values=('', '', ''))
        for t_idx, (off, rows) in enumerate(self.tables):
            tnode = self.tree.insert(tt_root, 'end', 
                                    text=f"Table {t_idx} @ 0x{off:X} (rows={len(rows)})", 
                                    values=('', '', ''),
                                    tags=(f"torque_table:{t_idx}",))
            self.tree.insert(tnode, 'end', text="Columns: RPM, Compression (-Nm), Torque (Nm)", values=('', '', ''))
            for i, (rpm, comp, tq, ptr, kind) in enumerate(rows):
                tq_str = '' if tq is None else f"{tq:.3f}"
                self.tree.insert(tnode, 'end',
                                 text=f"Row {i:02d} [{kind}] @ 0x{ptr:X}",
                                 values=(f"{rpm:.1f}", f"{comp:.3f}", tq_str),
                                 tags=(f"torque_row:{t_idx}:{i}",))

        # Boost tables
        bt_root = self.tree.insert(root_file, 'end', text=f"Boost tables found: {len(self.boost_tables)}", values=('', '', ''))
        for b_idx, (off, rows) in enumerate(self.boost_tables):
            bnode = self.tree.insert(bt_root, 'end', 
                                    text=f"Boost Table {b_idx} @ 0x{off:X} (rows={len(rows)})", 
                                    values=('', '', ''),
                                    tags=(f"boost_table:{b_idx}",))
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
        for param_idx, (name, pos, vals) in enumerate(sorted(self.params, key=lambda x: (x[0], x[1]))):
            v1 = self._format_param_value(vals[0]) if len(vals) > 0 else ''
            v2 = self._format_param_value(vals[1]) if len(vals) > 1 else ''
            v3 = self._format_param_value(vals[2]) if len(vals) > 2 else ''
            item_id = self.tree.insert(pr_root, 'end', 
                                      text=f"{name} @ 0x{pos:X}", 
                                      values=(v1, v2, v3),
                                      tags=(f"param:{param_idx}",))
            
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
                      f"Engine layout: {layout_label}\n\n"
                      f"Click items to view hex data.")
        self.status.set("Ready")
        self._file_menu_export.entryconfig("Export torque CSV...", state='normal')
        
        # Enable plot menu items
        if self.tables:
            self._plot_menu.entryconfig("Plot Torque vs RPM", state='normal')
            self._plot_menu.entryconfig("Plot Compression vs RPM", state='normal')
            self._plot_menu.entryconfig("Plot Both", state='normal')
        
        # Generate hex view
        self.update_hex_view()

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
                # Always use fixed-point notation for floats, never scientific
                entry.insert(0, f"{val:.6f}")
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
            tnode = self.tree.insert(tt_root, 'end', 
                                    text=f"Table {t_idx} @ 0x{off:X} (rows={len(rows)})", 
                                    values=('', '', ''),
                                    tags=(f"torque_table:{t_idx}",))
            self.tree.insert(tnode, 'end', text="Columns: RPM, Compression (-Nm), Torque (Nm)", values=('', '', ''))
            for i, (rpm, comp, tq, ptr, kind) in enumerate(rows):
                tq_str = '' if tq is None else f"{tq:.3f}"
                self.tree.insert(tnode, 'end',
                                 text=f"Row {i:02d} [{kind}] @ 0x{ptr:X}",
                                 values=(f"{rpm:.1f}", f"{comp:.3f}", tq_str),
                                 tags=(f"torque_row:{t_idx}:{i}",))
        
        # Boost tables
        bt_root = self.tree.insert(root_file, 'end', text=f"Boost tables found: {len(self.boost_tables)}", values=('', '', ''))
        for b_idx, (off, rows) in enumerate(self.boost_tables):
            bnode = self.tree.insert(bt_root, 'end', 
                                    text=f"Boost Table {b_idx} @ 0x{off:X} (rows={len(rows)})", 
                                    values=('', '', ''),
                                    tags=(f"boost_table:{b_idx}",))
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
        for param_idx, (name, pos, vals) in enumerate(sorted(self.params, key=lambda x: (x[0], x[1]))):
            v1 = self._format_param_value(vals[0]) if len(vals) > 0 else ''
            v2 = self._format_param_value(vals[1]) if len(vals) > 1 else ''
            v3 = self._format_param_value(vals[2]) if len(vals) > 2 else ''
            item_id = self.tree.insert(pr_root, 'end', 
                                      text=f"{name} @ 0x{pos:X}", 
                                      values=(v1, v2, v3),
                                      tags=(f"param:{param_idx}",))
            
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
        
        # Make a copy of data as bytearray if not already modified
        if not self.modified:
            self.data = bytearray(self.data)
            self.modified = True
        elif not isinstance(self.data, bytearray):
            # Ensure it's a bytearray even if somehow it's bytes
            self.data = bytearray(self.data)
        
        # Scale torque values in memory and update structures
        modifications = 0
        for t_idx, (off, rows) in enumerate(self.tables):
            new_rows = []
            for row_idx, (rpm, comp, tq, ptr, kind) in enumerate(rows):
                if tq is not None:
                    new_tq = tq * scale_factor
                    
                    # Write back to binary data based on row type
                    if kind == '0rpm':
                        # ptr is at the signature start, data is after 7-byte signature
                        data_offset = ptr + len(SIG_0RPM)
                        b0 = self.data[data_offset]
                        struct.pack_into('<Bff', self.data, data_offset, b0, comp, new_tq)
                        
                    elif kind == 'row_i':
                        # ptr already points to data after signature
                        struct.pack_into('<iff', self.data, ptr, int(rpm), comp, new_tq)
                        
                    elif kind == 'row_f':
                        # ptr already points to data after signature
                        struct.pack_into('<fff', self.data, ptr, rpm, comp, new_tq)
                    
                    # endvar doesn't have torque, skip
                    new_rows.append((rpm, comp, new_tq, ptr, kind))
                    modifications += 1
                else:
                    new_rows.append((rpm, comp, tq, ptr, kind))
            # Update table with new values
            self.tables[t_idx] = (off, new_rows)
        
        # Refresh display
        self._refresh_tree_display()
        
        self.info.set(f"Loaded: {Path(self.current_file).name}\n[MODIFIED]\n"
                      f"Torque scaled by {scale_factor*100:.1f}%\n"
                      f"Torque tables: {len(self.tables)}\n"
                      f"Params: {len(self.params)}\n\n"
                      f"Click items to view hex data.")
        self.status.set(f"Scaled {modifications} torque values by {scale_factor*100:.1f}%")
        
        # Enable save option
        self._file_menu_save_modified.entryconfig("Save Modified EDF...", state='normal')
        
        # Update hex view
        self.update_hex_view()
        
        messagebox.showinfo("Success", f"Scaled {modifications} torque values by {scale_factor*100:.1f}%\n\n"
                           "Use File > Save Modified EDF to save changes.")

    def save_modified_edf(self):
        if not self.modified:
            messagebox.showwarning("No changes", "No modifications have been made.")
            return
        
        # Suggest a filename
        if self.current_file:
            original_path = Path(self.current_file)
            suggested_name = original_path.stem + "_modified" + original_path.suffix
        else:
            suggested_name = "modified.edf"
        
        path = filedialog.asksaveasfilename(
            title="Save Modified EDF",
            initialfile=suggested_name,
            defaultextension=".edf",
            filetypes=[("EDF files", "*.edf"), ("EDFBIN files", "*.bin"), ("All files", "*.*")]
        )
        
        if not path:
            return
        
        try:
            with open(path, 'wb') as f:
                f.write(self.data)
            messagebox.showinfo("Saved", f"Modified EDF saved to:\n{path}")
            self.status.set(f"Saved modified EDF: {Path(path).name}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file:\n{e}")

    def on_hex_click(self, event):
        """Handle left-click in hex view for inline byte editing"""
        if not self.data:
            return
        
        # Show warning dialog once
        if not self.hex_edit_warning_shown:
            result = messagebox.askokcancel(
                "Direct Hex Editing",
                "⚠️ WARNING ⚠️\n\n"
                "You are about to enable direct hex editing.\n\n"
                "• This bypasses all validation\n"
                "• Invalid edits can corrupt the file\n"
                "• Use tree view editing when possible\n\n"
                "Click in the hex area to edit bytes directly.\n"
                "Type 2 hex digits and press Enter to apply.\n\n"
                "Proceed?",
                icon='warning'
            )
            if not result:
                return
            self.hex_edit_warning_shown = True
        
        # Get the position clicked
        index = self.hex_text.index(f"@{event.x},{event.y}")
        line, col = map(int, index.split('.'))
        
        # Line format: "00000000  XX XX XX XX XX XX XX XX  XX XX XX XX XX XX XX XX  |................|"
        
        # Only allow editing in hex area (cols 10-58), not ASCII area
        if not (10 <= col <= 58):
            return
        
        # Account for the extra space after 8th byte
        if col > 34:
            adjusted_col = col - 1
        else:
            adjusted_col = col
        
        # Calculate byte position in line (each byte is "XX " = 3 chars)
        byte_in_line = (adjusted_col - 10) // 3
        
        # Ensure we're clicking on a hex digit, not a space
        rel_pos = (adjusted_col - 10) % 3
        if rel_pos >= 2:  # Clicked on space between bytes
            return
        
        # Calculate absolute offset in file
        offset = (line - 1) * 16 + byte_in_line
        
        if offset >= len(self.data):
            return
        
        # Start inline editing
        self.edit_hex_byte_inline(line, byte_in_line, offset)
    
    def edit_hex_byte_inline(self, line, byte_in_line, offset):
        """Edit a byte inline in the hex view"""
        current_byte = self.data[offset]
        
        # Calculate text position
        col_start = 10 + (byte_in_line * 3)
        if byte_in_line >= 8:
            col_start += 1  # Extra space after 8th byte
        
        # Enable editing temporarily
        self.hex_text.config(state='normal')
        
        # Select the byte
        start_pos = f"{line}.{col_start}"
        end_pos = f"{line}.{col_start + 2}"
        self.hex_text.tag_add('editing', start_pos, end_pos)
        self.hex_text.mark_set('insert', start_pos)
        self.hex_text.see(start_pos)
        
        # Create a small entry widget overlay
        bbox = self.hex_text.bbox(start_pos)
        if not bbox:
            self.hex_text.config(state='disabled')
            return
        
        x, y, width, height = bbox
        
        entry = tk.Entry(self.hex_text, width=2, font=("Courier", 9), 
                        justify='center', relief=tk.FLAT,
                        bg='#ff6b6b', fg='#ffffff', insertbackground='#ffffff')
        entry.place(x=x, y=y, width=width*2.5, height=height)
        entry.insert(0, f"{current_byte:02X}")
        entry.select_range(0, tk.END)
        entry.focus()
        
        def save_edit(event=None):
            try:
                new_value = int(entry.get(), 16)
                if not 0 <= new_value <= 255:
                    raise ValueError("Byte must be 0x00-0xFF")
                
                # Apply the edit
                if not isinstance(self.data, bytearray):
                    self.data = bytearray(self.data)
                
                self.data[offset] = new_value
                self.modified = True
                
                # Update the hex display
                self.hex_text.delete(start_pos, end_pos)
                self.hex_text.insert(start_pos, f"{new_value:02X}")
                
                # Update ASCII representation
                ascii_col = 61 + byte_in_line
                ascii_pos = f"{line}.{ascii_col}"
                ascii_char = chr(new_value) if 32 <= new_value < 127 else '.'
                self.hex_text.delete(ascii_pos, f"{line}.{ascii_col + 1}")
                self.hex_text.insert(ascii_pos, ascii_char)
                
                # Re-parse structures
                self.tables = parse_torque_tables(self.data)
                self.boost_tables = parse_boost_tables(self.data)
                self.params = parse_params(self.data)
                
                # Refresh tree
                self._refresh_tree_display()
                
                # Enable save
                self._file_menu_save_modified.entryconfig("Save Modified EDF...", state='normal')
                
                self.status.set(f"Modified 0x{offset:08X}: 0x{current_byte:02X} → 0x{new_value:02X}")
                
            except ValueError as e:
                messagebox.showerror("Invalid Value", f"Invalid hex value: {entry.get()}\nMust be 00-FF")
            finally:
                entry.destroy()
                self.hex_text.tag_remove('editing', '1.0', tk.END)
                self.hex_text.config(state='disabled')
        
        def cancel_edit(event=None):
            entry.destroy()
            self.hex_text.tag_remove('editing', '1.0', tk.END)
            self.hex_text.config(state='disabled')
        
        entry.bind('<Return>', save_edit)
        entry.bind('<KP_Enter>', save_edit)
        entry.bind('<Escape>', cancel_edit)
        entry.bind('<FocusOut>', cancel_edit)

    def plot_torque_rpm(self):
        if not self.tables:
            messagebox.showwarning("No data", "No torque tables to plot.")
            return
        
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            messagebox.showerror("Error", "matplotlib is required for plotting.\nInstall it with: pip install matplotlib")
            return
        
        fig, ax1 = plt.subplots(figsize=(10, 6))
        
        # Create second y-axis for power
        ax2 = ax1.twinx()
        
        # Color schemes
        torque_colors = ['#1f77b4', '#2ca02c', '#9467bd', '#8c564b']  # Blues/greens for torque
        power_colors = ['#ff7f0e', '#ff9f3f', '#ffbf7f', '#ffd9a6']   # Orange shades for power
        
        for t_idx, (off, rows) in enumerate(self.tables):
            rpms = []
            torques = []
            powers = []
            for rpm, comp, tq, ptr, kind in rows:
                if tq is not None:  # Skip endvar rows without torque
                    rpms.append(rpm)
                    torques.append(tq)
                    # Power (kW) = Torque (Nm) × RPM × 2π / 60000
                    # Simplified: Power (kW) = Torque (Nm) × RPM / 9549.3
                    power_kw = (tq * rpm) / 9549.3
                    powers.append(power_kw)
            
            if rpms:
                torque_color = torque_colors[t_idx % len(torque_colors)]
                power_color = power_colors[t_idx % len(power_colors)]
                
                # Plot torque on left axis
                line1 = ax1.plot(rpms, torques, marker='o', label=f'Table {t_idx} Torque @ 0x{off:X}', 
                                linewidth=2, markersize=4, color=torque_color)
                # Plot power on right axis (dashed line, orange shades)
                line2 = ax2.plot(rpms, powers, marker='s', label=f'Table {t_idx} Power @ 0x{off:X}', 
                                linewidth=2, markersize=4, linestyle='--', color=power_color)
        
        ax1.set_xlabel('RPM', fontsize=12)
        ax1.set_ylabel('Torque (Nm)', fontsize=12, color='tab:blue')
        ax1.tick_params(axis='y', labelcolor='tab:blue')
        ax2.set_ylabel('Power (kW)', fontsize=12, color='tab:orange')
        ax2.tick_params(axis='y', labelcolor='tab:orange')
        
        ax1.set_title(f'Torque & Power vs RPM - {Path(self.current_file).name if self.current_file else "EDF File"}', fontsize=14)
        ax1.grid(True, alpha=0.3)
        
        # Combine legends from both axes
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='best')
        
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
            rpms = []
            comps = []
            for rpm, comp, tq, ptr, kind in rows:
                if tq is not None:  # Skip endvar rows without torque
                    rpms.append(rpm)
                    comps.append(comp)
            
            if rpms:
                ax.plot(rpms, comps, marker='o', label=f'Table {t_idx} @ 0x{off:X}', linewidth=2, markersize=4)
        
        ax.set_xlabel('RPM', fontsize=12)
        ax.set_ylabel('Compression (-Nm)', fontsize=12)
        ax.set_title(f'Compression vs RPM - {Path(self.current_file).name if self.current_file else "EDF File"}', fontsize=14)
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
        
        fig, (ax1, ax3) = plt.subplots(1, 2, figsize=(16, 6))
        
        # Create second y-axis for power on left plot
        ax2 = ax1.twinx()
        
        # Color schemes
        torque_colors = ['#1f77b4', '#2ca02c', '#9467bd', '#8c564b']  # Blues/greens for torque
        power_colors = ['#ff7f0e', '#ff9f3f', '#ffbf7f', '#ffd9a6']   # Orange shades for power
        
        for t_idx, (off, rows) in enumerate(self.tables):
            rpms = []
            comps = []
            torques = []
            powers = []
            for rpm, comp, tq, ptr, kind in rows:
                if tq is not None:  # Skip endvar rows without torque
                    rpms.append(rpm)
                    comps.append(comp)
                    torques.append(tq)
                    # Power (kW) = Torque (Nm) × RPM / 9549.3
                    power_kw = (tq * rpm) / 9549.3
                    powers.append(power_kw)
            
            if rpms:
                label = f'Table {t_idx} @ 0x{off:X}'
                torque_color = torque_colors[t_idx % len(torque_colors)]
                power_color = power_colors[t_idx % len(power_colors)]
                
                # Left plot: Torque and Power
                ax1.plot(rpms, torques, marker='o', label=f'Table {t_idx} Torque', 
                        linewidth=2, markersize=4, color=torque_color)
                ax2.plot(rpms, powers, marker='s', label=f'Table {t_idx} Power', 
                        linewidth=2, markersize=4, linestyle='--', color=power_color)
                # Right plot: Compression
                ax3.plot(rpms, comps, marker='o', label=label, linewidth=2, markersize=4)
        
        # Configure left plot (Torque & Power vs RPM)
        ax1.set_xlabel('RPM', fontsize=12)
        ax1.set_ylabel('Torque (Nm)', fontsize=12, color='tab:blue')
        ax1.tick_params(axis='y', labelcolor='tab:blue')
        ax2.set_ylabel('Power (kW)', fontsize=12, color='tab:orange')
        ax2.tick_params(axis='y', labelcolor='tab:orange')
        ax1.set_title('Torque & Power vs RPM', fontsize=13)
        ax1.grid(True, alpha=0.3)
        
        # Combine legends from both y-axes
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='best', fontsize=9)
        
        # Configure right plot (Compression vs RPM)
        ax3.set_xlabel('RPM', fontsize=12)
        ax3.set_ylabel('Compression (-Nm)', fontsize=12)
        ax3.set_title('Compression vs RPM', fontsize=13)
        ax3.grid(True, alpha=0.3)
        ax3.legend()
        
        fig.suptitle(f'{Path(self.current_file).name if self.current_file else "EDF File"}', fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.show()

def main():
    app = EDFViewer()
    app.mainloop()

if __name__ == '__main__':
    main()
