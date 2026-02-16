import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import logging
import csv

from ..core.parser import parse_torque_tables, parse_boost_tables, parse_params, detect_engine_layout
from ..core.writer import write_torque_row, write_param, scale_torque_tables
from ..utils import plotting
from .tree_view import EDFTreeView
from .hex_view import HexView

logger = logging.getLogger(__name__)

class EDFEditorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AMS2 EDF File Editor v0.4")
        self.geometry("1200x800")
        
        self.current_file = None
        self.data = None
        
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
        tools_menu.add_command(label="Plot Torque/Power", command=self.plot_torque)
        tools_menu.add_command(label="Plot Compression", command=self.plot_compression)
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
            self.title(f"AMS2 EDF File Editor v0.4 - {path}")
            
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
            self.title(f"AMS2 EDF File Editor v0.4 - {path}")
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
        self.title("AMS2 EDF File Editor v0.4")
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

    def on_param_update(self, param):
        write_param(self.data, param)
        self.hex_view.load_data(self.data)
        self.tree.populate(self.tables, self.boost, self.params)

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
        
        messagebox.showinfo("Success", f"Scaled torque by {percent}%")

if __name__ == "__main__":
    app = EDFEditorApp()
    app.mainloop()
