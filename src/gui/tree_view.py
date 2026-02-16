import tkinter as tk
from tkinter import ttk
from typing import List, Optional

from ..core.models import TorqueTable, BoostTable, Parameter
from ..core.constants import PARAM_META
from ..utils.formatting import format_float

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
