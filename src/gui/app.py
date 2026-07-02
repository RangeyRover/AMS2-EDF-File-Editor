import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import logging
import csv
import os

from ..core.parser import parse_torque_tables, parse_boost_tables, parse_p2p_tables, parse_params, detect_engine_layout
from ..core.writer import write_torque_row, write_param, scale_torque_tables
from ..core.docs_provider import DocumentationProvider
from ..utils import plotting
from .tree_view import EDFTreeView
from .hex_view import HexView

logger = logging.getLogger(__name__)

class EDFEditorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AMS2 EDF File Editor v0.5.5")
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
        tools_menu.add_command(label="Interactive P2P Editor", command=self.plot_p2p_interactive)
        tools_menu.add_command(label="Interactive Boost Editor", command=self.plot_boost_interactive)
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
        
        # Setup Docs Provider
        proj_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        xml_path = os.path.join(proj_root, "edf-hex-map.xml")
        txt_path = os.path.join(proj_root, "Translation_for_EngineEDFBIN_Shiimis_Rangeyrover_V1.5.txt")
        self.docs_provider = DocumentationProvider(xml_path, txt_path)
        
        # Bind events
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        self.tree.bind("<Button-3>", self.on_tree_right_click)
        
    def load_file(self):
        path = filedialog.askopenfilename(filetypes=[("EDF files", "*.edf *.edfbin"), ("All files", "*.*")])
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
            self.p2p_tables = parse_p2p_tables(self.data)
            self.params = parse_params(self.data)
            
            # Populate UI
            self.tree.populate(self.tables, self.boost, self.p2p_tables, self.params)
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
            filetypes=[("EDF files", "*.edf *.edfbin"), ("All files", "*.*")]
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
        self.p2p_tables = []
        self.params = []
        self.tree.populate([], [], [], [])
        self.hex_view.load_data(bytearray())
        
        self.current_file = None
        self._set_dirty(False)
        
        self.file_menu.entryconfig("Save", state='disabled')
        self.file_menu.entryconfig("Save As...", state='disabled')
        self.file_menu.entryconfig("Close", state='disabled')

    def on_tree_right_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id or item_id not in self.tree.item_map:
            return
            
        self.tree.selection_set(item_id)
        obj = self.tree.item_map[item_id]
        
        # Create a context menu
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Help / View Definition", command=lambda: self.show_help_dialog(obj))
        menu.tk_popup(event.x_root, event.y_root)
        
    def show_help_dialog(self, obj):
        from ..core.models import TorqueRow, BoostRow, P2PRow, Parameter
        from .dialogs import HelpDialog
        
        key = None
        if isinstance(obj, TorqueRow):
            key = "RPMTorque"
        elif isinstance(obj, BoostRow):
            key = "BoostTable"
        elif isinstance(obj, P2PRow):
            key = "P2PTable"
        elif isinstance(obj, Parameter):
            key = obj.name
            
        doc = None
        if key:
            # Check docs_provider
            doc = self.docs_provider.get_documentation(key)
            if not doc and key == "BoostTable":
                doc = "XML Definition:\n<boost-tables>\n  <row-struct name='row-i'>\n    <field name='rpm' type='int32'/>\n    <field name='t0' type='float'/>\n    ...\n  </row-struct>\n</boost-tables>"
            
        HelpDialog(self, obj, doc, key if key else "Unknown Element")

    def on_tree_double_click(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        
        item_id = sel[0]
        if item_id not in self.tree.item_map:
            return
            
        obj = self.tree.item_map[item_id]
        
        from .dialogs import EditTorqueDialog, EditParamDialog, EditP2PDialog
        from ..core.models import TorqueRow, Parameter, P2PRow
        
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
        elif isinstance(obj, P2PRow):
            if self._interactive_plot_open:
                messagebox.showinfo(
                    "Interactive Plot Active",
                    "Close the interactive plot before editing P2P rows in the tree view."
                )
                return
            EditP2PDialog(self, obj, self.on_row_update)
            
    def on_row_update(self, rows):
        from ..core.writer import write_torque_row, write_boost_row, write_p2p_row
        from ..core.models import TorqueRow, BoostRow, P2PRow

        if not isinstance(rows, list):
            rows = [rows]
            
        for row in rows:
            if isinstance(row, TorqueRow):
                write_torque_row(self.data, row)
            elif isinstance(row, BoostRow):
                write_boost_row(self.data, row)
            elif isinstance(row, P2PRow):
                write_p2p_row(self.data, row)
            
        self.hex_view.load_data(self.data)
        self.tree.populate(self.tables, self.boost, self.p2p_tables, self.params)
        self._set_dirty(True)

    def on_param_update(self, param):
        write_param(self.data, param)
        self.hex_view.load_data(self.data)
        self.tree.populate(self.tables, self.boost, self.p2p_tables, self.params)
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

    def plot_boost_interactive(self):
        """Launch an interactive drag-editable Boost plot."""
        if not self.data or not hasattr(self, 'boost') or not self.boost:
            messagebox.showwarning("No data", "No Boost tables found.")
            return
        if self._interactive_plot_open:
            messagebox.showinfo("Already open", "An interactive plot is already open.")
            return
        try:
            from ..utils.interactive_boost_plot import DraggableBoostPlot
            self._interactive_plot_open = True
            self._interactive_plot = DraggableBoostPlot(
                parent=self,
                tables=self.boost,
                data=self.data,
                filename=self.current_file or "EDF File",
                on_row_changed=self.on_row_update,
                on_close=self._on_interactive_plot_close,
            )
        except Exception as e:
            self._interactive_plot_open = False
            logger.exception("Boost Interactive plot failed")
            messagebox.showerror("Error", f"Boost plot failed: {e}")

    def plot_p2p_interactive(self):
        """Launch an interactive drag-editable P2P plot."""
        if not self.data or not hasattr(self, 'p2p_tables') or not self.p2p_tables:
            messagebox.showwarning("No data", "No P2P tables found.")
            return
        if self._interactive_plot_open:
            messagebox.showinfo("Already open", "An interactive plot is already open.")
            return
        try:
            from ..utils.interactive_p2p_plot import DraggableP2PPlot
            self._interactive_plot_open = True
            self._interactive_plot = DraggableP2PPlot(
                parent=self,
                tables=self.p2p_tables,
                data=self.data,
                filename=self.current_file or "EDF File",
                on_row_changed=self.on_row_update,
                on_close=self._on_interactive_plot_close,
            )
        except Exception as e:
            self._interactive_plot_open = False
            logger.exception("P2P Interactive plot failed")
            messagebox.showerror("Error", f"P2P plot failed: {e}")

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
        title = "AMS2 EDF File Editor v0.5.5"
        if self.current_file:
            title += f" - {self.current_file}"
        if self._dirty:
            title += " *"
        self.title(title)

if __name__ == "__main__":
    app = EDFEditorApp()
    app.mainloop()
