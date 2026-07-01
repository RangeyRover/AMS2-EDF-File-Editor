import logging
import tkinter as tk
from tkinter import ttk
from typing import List, Callable
import numpy as np

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import matplotlib.cm as cm
import matplotlib.colors as mcolors

from ..core.models import P2PTable, P2PRow
from .formatting import quantise_f32

logger = logging.getLogger(__name__)
PICKER_TOLERANCE = 7
P2P_MIN, P2P_MAX = 0.0, 5.0 # Sensible defaults for multiplier

class DraggableP2PPlot:
    def __init__(
        self,
        parent: tk.Tk,
        tables: List[P2PTable],
        data: bytearray,
        filename: str,
        on_row_changed: Callable[[P2PRow], None],
        on_close: Callable[[], None],
    ):
        self.parent = parent
        self.tables = tables
        self.data = data
        self.filename = filename
        self.on_row_changed = on_row_changed
        self._on_close_callback = on_close
        
        self.current_table_idx = 0

        self._dragging = False
        self._drag_line = None
        self._drag_point_idx = None
        self._drag_row = None

        self._build_window()
        self._populate_throttle_list()
        self._plot_curves()
        self._connect_events()

    def _populate_throttle_list(self):
        # Find all unique throttles across all tables
        unique_throttles = set()
        for t in self.tables:
            for r in t.rows:
                unique_throttles.add(r.throttle)
                
        sorted_throttles = sorted(list(unique_throttles))
        self.throttle_listbox.delete(0, tk.END)
        for thr in sorted_throttles:
            self.throttle_listbox.insert(tk.END, f"{thr}%")
            
        # Select 100% by default if it exists, otherwise select the highest
        if sorted_throttles:
            try:
                idx = sorted_throttles.index(100.0)
            except ValueError:
                idx = len(sorted_throttles) - 1
            self.throttle_listbox.selection_set(idx)

    def _build_window(self):
        self.toplevel = tk.Toplevel(self.parent)
        self.toplevel.title(f"Interactive P2P Editor — {self.filename}")
        self.toplevel.geometry("1400x700")
        self.toplevel.protocol("WM_DELETE_WINDOW", self._on_window_close)
        
        control_frame = ttk.Frame(self.toplevel)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Label(control_frame, text="Table:").pack(side=tk.LEFT, padx=5)
        self.table_var = tk.StringVar(value="0")
        table_cb = ttk.Combobox(control_frame, textvariable=self.table_var, 
                                values=[str(i) for i in range(len(self.tables))], state="readonly", width=5)
        table_cb.pack(side=tk.LEFT, padx=5)
        table_cb.bind("<<ComboboxSelected>>", self._on_controls_changed)
        
        ttk.Label(control_frame, text="Visible Throttles:").pack(side=tk.LEFT, padx=(20, 5))
        
        # Frame for the listbox and scrollbar
        list_frame = ttk.Frame(control_frame)
        list_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.throttle_listbox = tk.Listbox(list_frame, selectmode=tk.MULTIPLE, yscrollcommand=scrollbar.set, height=3, exportselection=False)
        scrollbar.config(command=self.throttle_listbox.yview)
        
        self.throttle_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        
        self.throttle_listbox.bind("<<ListboxSelect>>", self._on_controls_changed)

        self.fig = Figure(figsize=(14, 6), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.toplevel)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.toolbar = NavigationToolbar2Tk(self.canvas, self.toplevel)
        self.toolbar.update()
        
        self.ax2d = self.fig.add_subplot(121)
        self.ax3d = self.fig.add_subplot(122, projection='3d')

    def _on_controls_changed(self, event=None):
        self.current_table_idx = int(self.table_var.get())
        self._plot_curves()

    def _plot_curves(self):
        self.ax2d.clear()
        self.ax3d.clear()
        
        table = self.tables[self.current_table_idx]
        
        # Group rows by throttle for 2D plot
        throttle_groups = {}
        for r in table.rows:
            if r.throttle not in throttle_groups:
                throttle_groups[r.throttle] = []
            throttle_groups[r.throttle].append(r)
            
        for thr in throttle_groups:
            throttle_groups[thr].sort(key=lambda r: r.rpm)
            
        throttle_vals = sorted(list(throttle_groups.keys()))
        
        # Create a colormap based on Throttle
        norm = mcolors.Normalize(vmin=min(throttle_vals) if throttle_vals else 0, vmax=max(throttle_vals) if throttle_vals else 100)
        cmap = cm.plasma
        
        self._line_map = {}
        
        # Get selected throttles from listbox
        selected_indices = self.throttle_listbox.curselection()
        selected_throttles = []
        for idx in selected_indices:
            val_str = self.throttle_listbox.get(idx)
            val = float(val_str.replace('%', ''))
            selected_throttles.append(val)
            
        for thr in throttle_vals:
            # Only plot the throttles selected by the user
            if thr not in selected_throttles:
                continue
                
            rows = throttle_groups[thr]
            rpms = [r.rpm for r in rows]
            vals = [r.multiplier for r in rows]
            
            line_color = cmap(norm(thr))
            line, = self.ax2d.plot(
                rpms, vals,
                marker='o', linewidth=1, markersize=4,
                color=line_color, picker=PICKER_TOLERANCE,
                label=f'{thr}%'
            )
            self._line_map[id(line)] = rows
                
        self.ax2d.set_xlabel('RPM', fontsize=12)
        self.ax2d.set_ylabel('P2P Multiplier', fontsize=12)
        self.ax2d.set_title(f'2D Drag View - Table {self.current_table_idx}', fontsize=13)
        self.ax2d.grid(True, alpha=0.3)
        self.ax2d.legend(title='Throttle', loc='best', fontsize=9)
        
        # 3D Plot: Surface
        unique_rpms = sorted(list(set(r.rpm for r in table.rows)))
        
        if throttle_vals and unique_rpms:
            R, T = np.meshgrid(unique_rpms, throttle_vals)
            M = np.zeros_like(R, dtype=float)
            
            for i, thr in enumerate(throttle_vals):
                for j, rpm in enumerate(unique_rpms):
                    row = next((r for r in table.rows if r.rpm == rpm and r.throttle == thr), None)
                    if row:
                        M[i, j] = row.multiplier
                        
            surface_colors = cmap(norm(T))
            self.ax3d.plot_surface(R, T, M, facecolors=surface_colors, alpha=0.8, edgecolor='k', linewidth=0.3)
            self.ax3d.set_xlabel('RPM')
            self.ax3d.set_ylabel('Throttle %')
            self.ax3d.set_zlabel('Multiplier')
            self.ax3d.set_title(f'3D Surface View - Table {self.current_table_idx}')
            
        self.fig.tight_layout()
        self.canvas.draw()

    def _connect_events(self):
        self._cid_press = self.canvas.mpl_connect('button_press_event', self._on_press)
        self._cid_motion = self.canvas.mpl_connect('motion_notify_event', self._on_motion)
        self._cid_release = self.canvas.mpl_connect('button_release_event', self._on_release)

    def _on_press(self, event):
        if event.inaxes != self.ax2d or event.button != 1: return
        
        best_line, best_idx = None, None
        for line in self.ax2d.get_lines():
            contains, info = line.contains(event)
            if contains and len(info['ind']) > 0:
                best_line = line
                best_idx = info['ind'][0]
                break
                
        if not best_line or id(best_line) not in self._line_map: return
        
        rows = self._line_map[id(best_line)]
        self._dragging = True
        self._drag_line = best_line
        self._drag_point_idx = best_idx
        self._drag_row = rows[best_idx]

    def _on_motion(self, event):
        if not self._dragging or event.inaxes != self.ax2d: return
        
        new_y = event.ydata
        new_y = max(P2P_MIN, min(P2P_MAX, new_y))
        new_y = quantise_f32(new_y)
        
        xdata = list(self._drag_line.get_xdata())
        ydata = list(self._drag_line.get_ydata())
        ydata[self._drag_point_idx] = new_y
        self._drag_line.set_data(xdata, ydata)
        self.canvas.draw_idle()

    def _on_release(self, event):
        if not self._dragging: return
        self._dragging = False
        
        ydata = self._drag_line.get_ydata()
        final_y = quantise_f32(ydata[self._drag_point_idx])
        
        old_val = self._drag_row.multiplier
        new_val = final_y
        rpm = self._drag_row.rpm
        drag_throttle = self._drag_row.throttle
        
        # Calculate proportional scaling ratio
        ratio = new_val / old_val if old_val != 0 else 0
        
        modified_rows = []
        
        # Find all rows at this RPM
        table = self.tables[self.current_table_idx]
        for row in table.rows:
            if row.rpm == rpm:
                if row.throttle == drag_throttle:
                    row.multiplier = new_val
                else:
                    if old_val != 0:
                        row.multiplier = quantise_f32(row.multiplier * ratio)
                    else:
                        # If old_val was 0, fall back to linear scaling relative to dragged throttle
                        scale_factor = (row.throttle / drag_throttle) if drag_throttle != 0 else 1.0
                        row.multiplier = quantise_f32(new_val * scale_factor)
                modified_rows.append(row)
                
        # We can pass the whole list to the main app! (Which we updated to handle lists)
        self.on_row_changed(modified_rows)
        
        # Redraw 3D to reflect new data
        self._plot_curves()
        
    def show(self):
        self.toplevel.focus_set()
        
    def _on_window_close(self):
        if self._on_close_callback:
            self._on_close_callback()
        self.toplevel.destroy()
