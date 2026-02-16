import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from ..core.models import TorqueRow, Parameter
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
