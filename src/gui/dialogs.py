import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from ..core.models import TorqueRow, Parameter, P2PRow
from ..core.constants import PARAM_META
from ..utils.formatting import format_float

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
        self.app = parent
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
        ttk.Button(btn_frame, text="Help", command=lambda: self.app.show_help_dialog(self.row)).pack(side='left', padx=5)
        
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
        
        self.app = parent
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
                fmt_char = self.param.fmt[i] if self.param.fmt and i < len(self.param.fmt) else ''
                if fmt_char == 'f':
                    type_str = "Float32"
                elif fmt_char == 'i':
                    type_str = "Int32"
                elif fmt_char == 'B':
                    type_str = "Byte"
                else:
                    type_str = "Float" if isinstance(val, float) else "Int"
                    
                field_label = f"Value {i+1} ({type_str}):"
                
            ttk.Label(self, text=field_label).pack()
            if isinstance(val, float):
                display = format_float(val, 6)
            else:
                display = str(val)
            v = tk.StringVar(value=display)
            self.vars.append(v)
            ttk.Entry(self, textvariable=v, width=_ENTRY_WIDTH).pack()
            
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="Save", command=self.on_save).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Help", command=lambda: self.app.show_help_dialog(self.param)).pack(side='left', padx=5)
        
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

class EditP2PDialog(tk.Toplevel):
    def __init__(self, parent, row: P2PRow, callback):
        super().__init__(parent)
        self.row = row
        self.callback = callback
        self.title("Edit P2P Row")
        self.transient(parent)
        self.grab_set()
        
        self.result: bool = False
        self.app = parent
        self._setup_ui()
        
        self.update_idletasks()
        self.minsize(self.winfo_reqwidth(), self.winfo_reqheight())
        
    def _setup_ui(self):
        pad = {'padx': 10, 'pady': 5}
        
        # Mode
        ttk.Label(self, text="Mode (Byte):").pack(**pad)
        self.mode_var = tk.StringVar(value=str(self.row.mode))
        ttk.Entry(self, textvariable=self.mode_var, width=_ENTRY_WIDTH).pack(**pad)
        
        # RPM
        ttk.Label(self, text="RPM Index (Byte):").pack(**pad)
        self.rpm_var = tk.StringVar(value=str(int(self.row.rpm)))
        ttk.Entry(self, textvariable=self.rpm_var, width=_ENTRY_WIDTH).pack(**pad)
        
        # Throttle
        ttk.Label(self, text="Throttle Index (Byte):").pack(**pad)
        self.thr_var = tk.StringVar(value=str(int(self.row.throttle)))
        ttk.Entry(self, textvariable=self.thr_var, width=_ENTRY_WIDTH).pack(**pad)
        
        # Multiplier
        ttk.Label(self, text="Multiplier (Float):").pack(**pad)
        self.mult_var = tk.StringVar(value=format_float(self.row.multiplier, 6))
        ttk.Entry(self, textvariable=self.mult_var, width=_ENTRY_WIDTH).pack(**pad)
        
        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="Save", command=self.on_save).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Help", command=lambda: self.app.show_help_dialog(self.row)).pack(side='left', padx=5)
        
    def on_save(self):
        try:
            new_mode = int(self.mode_var.get())
            new_rpm = int(self.rpm_var.get())
            new_thr = int(self.thr_var.get())
            new_mult = float(self.mult_var.get())
            
            # bounds checking for byte
            if not (0 <= new_mode <= 255): raise ValueError("Mode must be 0-255")
            if not (0 <= new_rpm <= 255): raise ValueError("RPM Index must be 0-255")
            if not (0 <= new_thr <= 255): raise ValueError("Throttle Index must be 0-255")
            
            self.row.mode = new_mode
            self.row.rpm = float(new_rpm)
            self.row.throttle = float(new_thr)
            self.row.multiplier = new_mult
            
            self.result = True
            if self.callback:
                self.callback(self.row)
            self.destroy()
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid value: {e}")

MARKER_MAP = {
    0x20: ("1 byte value", 1),
    0x21: ("uint32 LE", 4),
    0x22: ("float32 LE", 4),
    0x26: ("1 byte (special)", 1),
    0x28: ("no data (null/absent)", 0),
    0xE0: ("no data (section)", 0),
    0x24: ("compound (suffix-defined)", -1)
}

COMPOUND_SUFFIX_MAP = {
    "04 08": ("byte, byte, byte, float", 7),
    "93 02": ("int32, float, float", 12),
    "A3 02": ("float, float, float", 12),
    "04 00": ("byte, byte, byte", 3),
    "96 AA": ("int32, 5 floats", 24),
    "A2": ("float, float", 8),
    "83 02": ("byte, float, float", 9),
    "52": ("int32, int32", 8),
    "03 00": ("byte, byte, byte", 3),
    "A3 00": ("float, float, byte", 9),
    "16 AA": ("int32, byte, 4 floats", 21),
    "83 00": ("byte, float, byte", 6),
    "86 AA": ("byte, 5 floats", 21),
    "23 00": ("float, byte, byte", 6),
    "06 AA": ("byte, 4 floats", 17),
    "16 00": ("int32, 5 bytes", 9),
    "03 02": ("byte, byte, float", 6),
    "93 00": ("int32, float, byte", 9),
    "06 2A": ("byte, 4 floats", 17),
    "86 2A": ("byte, 5 floats", 21)
}

class HelpDialog(tk.Toplevel):
    def __init__(self, parent, obj, doc_string: str, title_context: str):
        super().__init__(parent)
        self.title(f"EDF Binary Field Layout: {title_context}")
        self.transient(parent)
        self.geometry("750x650")
        
        # Analyze Binary Layout
        data = parent.data
        offset = obj.offset
        
        marker_byte = data[offset]
        hash_bytes = data[offset+1:offset+5]
        hash_str = " ".join([f"{b:02X}" for b in hash_bytes])
        hash_le = f"0x{hash_bytes[3]:02X}{hash_bytes[2]:02X}{hash_bytes[1]:02X}{hash_bytes[0]:02X}"
        
        marker_info, data_len = MARKER_MAP.get(marker_byte, ("Unknown", 0))
        
        suffix_bytes = []
        suffix_str = ""
        types_desc = marker_info
        
        if marker_byte == 0x24:
            s1 = f"{data[offset+5]:02X}"
            s2 = f"{data[offset+5]:02X} {data[offset+6]:02X}"
            
            if s2 in COMPOUND_SUFFIX_MAP:
                suffix_bytes = [data[offset+5], data[offset+6]]
                suffix_str = s2
                types_desc, data_len = COMPOUND_SUFFIX_MAP[s2]
            elif s1 in COMPOUND_SUFFIX_MAP:
                suffix_bytes = [data[offset+5]]
                suffix_str = s1
                types_desc, data_len = COMPOUND_SUFFIX_MAP[s1]
            else:
                types_desc = "Unknown Compound"
                
        total_len = 1 + 4 + len(suffix_bytes) + data_len
        if offset + total_len > len(data):
            total_len = len(data) - offset
            
        h0, h1, h2, h3 = [f"{b:02X}" for b in hash_bytes]
        
        header_cols = ["[marker]", "[hash_b0]", "[hash_b1]", "[hash_b2]", "[hash_b3]"]
        value_cols = [f"{marker_byte:02X}".center(8), h0.center(9), h1.center(9), h2.center(9), h3.center(9)]
        
        if marker_byte == 0x24:
            suf_head = "[suffix]"
            suf_val = suffix_str
            w = max(len(suf_head), len(suf_val))
            header_cols.append(suf_head.center(w))
            value_cols.append(suf_val.center(w))
            
        header_cols.append("[data...]")
        
        data_start = offset + 1 + 4 + len(suffix_bytes)
        data_end = offset + total_len
        data_hex = " ".join(f"{b:02X}" for b in data[data_start:data_end])
        if len(data_hex) > 20:
            data_hex = data_hex[:17] + "..."
        value_cols.append(data_hex)
        
        header_row = " ".join(header_cols)
        value_row = " ".join(value_cols)
        
        layout_text = f"""EDF Binary Field Layout
=====================================================================

{header_row}
{value_row}

[{marker_byte:02X}]        : Marker -> {marker_info}
[{h0}{h1}{h2}{h3}]  : Hash ID -> (Decoded LE: {hash_le})"""

        if marker_byte == 0x24:
            layout_text += f"\n[{suffix_str.replace(' ', '').center(8)}] : Suffix -> Types: {types_desc}"
            
        layout_text += f"\n\n[Data Payload] : {data_len} bytes"
        
        from ..core.models import TorqueRow, BoostRow, P2PRow, Parameter
        if isinstance(obj, TorqueRow):
            layout_text += f"\n   -> int32 (RPM)         : {obj.rpm}"
            layout_text += f"\n   -> float (Compression) : {format_float(obj.compression, 6)}"
            if obj.torque is not None:
                layout_text += f"\n   -> float (Torque)      : {format_float(obj.torque, 6)}"
        elif isinstance(obj, BoostRow):
            if hasattr(obj, 'rpm') and obj.kind.startswith('boost_row'):
                layout_text += f"\n   -> int32 (RPM)         : {obj.rpm}"
            elif obj.kind.startswith('boost_0rpm'):
                layout_text += f"\n   -> byte  (0 RPM Mark)  : 0"
                
            layout_text += f"\n   -> float (Throttle 0%) : {format_float(obj.t0, 6)}"
            layout_text += f"\n   -> float (Throttle 25%): {format_float(obj.t25, 6)}"
            layout_text += f"\n   -> float (Throttle 50%): {format_float(obj.t50, 6)}"
            layout_text += f"\n   -> float (Throttle 75%): {format_float(obj.t75, 6)}"
            if obj.t100 is not None:
                layout_text += f"\n   -> float (Throttle 100%): {format_float(obj.t100, 6)}"
        elif isinstance(obj, P2PRow):
            if obj.kind == 'p2p_full':
                layout_text += f"\n   -> byte  (Mode)        : {obj.mode}"
                layout_text += f"\n   -> byte  (RPM Index)   : {int(obj.rpm)}"
                layout_text += f"\n   -> byte  (Thr Index)   : {int(obj.throttle)}"
                layout_text += f"\n   -> float (Multiplier)  : {format_float(obj.multiplier, 6)}"
            elif obj.kind == 'p2p_zero':
                layout_text += f"\n   -> byte  (Mode)        : {obj.mode}"
                layout_text += f"\n   -> byte  (RPM Index)   : {int(obj.rpm)}"
                layout_text += f"\n   -> byte  (Thr Index)   : {int(obj.throttle)}"
            else:
                layout_text += f"\n   -> byte  (Mode)        : {obj.mode}"
                layout_text += f"\n   -> byte  (RPM Index)   : {int(obj.rpm)}"
                layout_text += f"\n   -> byte  (Thr Index)   : {int(obj.throttle)}"
        elif isinstance(obj, Parameter):
            for i, v in enumerate(obj.values):
                v_type = "float32" if isinstance(v, float) else "uint32" if marker_byte == 0x21 else "byte" if marker_byte in (0x20, 0x26) else "int/byte"
                v_str = format_float(v, 6) if isinstance(v, float) else str(v)
                layout_text += f"\n   -> {v_type:<7} (Value {i+1})    : {v_str}"
                
        layout_text += "\n"
        
        layout_frame = ttk.LabelFrame(self, text="Binary Structure & Data Mapping", padding=10)
        layout_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        lt = tk.Text(layout_frame, height=20, bg='black', fg='lightgreen', font=('Consolas', 10))
        lt.pack(fill=tk.BOTH, expand=True)
        lt.insert("1.0", layout_text)
        lt.config(state=tk.DISABLED)
        
        # Lower section: Source Documentation
        doc_frame = ttk.LabelFrame(self, text="Translation Origin", padding=10)
        doc_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        doc_text = tk.Text(doc_frame, height=4, wrap=tk.WORD)
        doc_text.pack(fill=tk.BOTH, expand=True)
        if not doc_string:
            doc_string = "No explicit documentation block found for this element."
        doc_text.insert("1.0", doc_string)
        doc_text.config(state=tk.DISABLED)
        
        # Close button
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="Close", command=self.destroy).pack()
