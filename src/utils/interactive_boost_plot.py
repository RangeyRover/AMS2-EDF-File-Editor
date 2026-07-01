import logging
import tkinter as tk
from tkinter import ttk
from typing import List, Callable, Optional, Dict, Tuple
import numpy as np

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.cm as cm
import matplotlib.colors as mcolors

from ..core.models import BoostTable, BoostRow
from .formatting import quantise_f32

logger = logging.getLogger(__name__)
PICKER_TOLERANCE = 7
BOOST_MIN, BOOST_MAX = 0.0, 5.0

class DraggableBoostPlot:
    def __init__(
        self,
        parent: tk.Tk,
        tables: List[BoostTable],
        data: bytearray,
        filename: str,
        on_row_changed: Callable[[BoostRow], None],
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
        self._drag_attr = None

        self._build_window()
        self._plot_curves()
        self._connect_events()

    def _build_window(self):
        self.toplevel = tk.Toplevel(self.parent)
        self.toplevel.title(f"Interactive Boost Editor — {self.filename}")
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
        
        labels = ['0%', '25%', '50%', '75%', '100%']
        throttle_vals = [0, 25, 50, 75, 100]
        
        # Create a colormap based on Throttle (0-100)
        norm = mcolors.Normalize(vmin=0, vmax=100)
        cmap = cm.plasma
        
        self._line_map = {}
        
        table = self.tables[self.current_table_idx]
        rpms = [r.rpm for r in table.rows]
        
        for i, attr in enumerate(['t0', 't25', 't50', 't75', 't100']):
            vals = [getattr(r, attr) for r in table.rows]
            valid_rpms = [rpm for rpm, v in zip(rpms, vals) if v is not None]
            valid_vals = [v for v in vals if v is not None]
            valid_rows = [r for r, v in zip(table.rows, vals) if v is not None]
            
            if valid_rpms:
                line_color = cmap(norm(throttle_vals[i]))
                line, = self.ax2d.plot(
                    valid_rpms, valid_vals,
                    marker='o', linewidth=2, markersize=6,
                    color=line_color, picker=PICKER_TOLERANCE,
                    label=f'Throttle {labels[i]}'
                )
                self._line_map[id(line)] = (valid_rows, i, attr)
                
        self.ax2d.set_xlabel('RPM', fontsize=12)
        self.ax2d.set_ylabel('Boost Pressure (bar)', fontsize=12)
        self.ax2d.set_title(f'2D Drag View - Table {self.current_table_idx}', fontsize=13)
        self.ax2d.grid(True, alpha=0.3)
        self.ax2d.legend(loc='best', fontsize=9)
        
        # 3D Plot: Surface
        # Extract available throttles
        available_throttles = []
        for i, attr in enumerate(['t0', 't25', 't50', 't75', 't100']):
            if any(getattr(r, attr) is not None for r in table.rows):
                available_throttles.append(throttle_vals[i])
                
        if available_throttles and rpms:
            R, T = np.meshgrid(rpms, available_throttles)
            M = np.zeros_like(R, dtype=float)
            
            for i, thr in enumerate(available_throttles):
                attr = ['t0', 't25', 't50', 't75', 't100'][throttle_vals.index(thr)]
                for j, rpm in enumerate(rpms):
                    row = next((r for r in table.rows if r.rpm == rpm), None)
                    if row:
                        val = getattr(row, attr)
                        M[i, j] = val if val is not None else 0.0
                        
            # Map Throttle (T) to facecolors
            surface_colors = cmap(norm(T))
            self.ax3d.plot_surface(R, T, M, facecolors=surface_colors, alpha=0.8, edgecolor='k', linewidth=0.5)
            self.ax3d.set_xlabel('RPM')
            self.ax3d.set_ylabel('Throttle %')
            self.ax3d.set_zlabel('Boost (bar)')
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
        
        rows, thr_idx, attr = self._line_map[id(best_line)]
        self._dragging = True
        self._drag_line = best_line
        self._drag_point_idx = best_idx
        self._drag_row = rows[best_idx]
        self._drag_attr = attr

    def _on_motion(self, event):
        if not self._dragging or event.inaxes != self.ax2d: return
        
        new_y = event.ydata
        new_y = max(BOOST_MIN, min(BOOST_MAX, new_y))
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
        
        setattr(self._drag_row, self._drag_attr, final_y)
        self.on_row_changed(self._drag_row)
        
        # Redraw 3D to reflect new data
        self._plot_curves()
        
    def show(self):
        self.toplevel.focus_set()
        
    def _on_window_close(self):
        if self._on_close_callback:
            self._on_close_callback()
        self.toplevel.destroy()
