"""Interactive drag-editable torque/compression plot.

This module provides the DraggableTorquePlot class, which embeds a
matplotlib figure in a Tkinter Toplevel window with full drag-to-edit
support for torque and compression curves.

Key features:
  - Click-and-drag torque/compression markers vertically
  - Real-time curve + power recalculation during drag
  - Float32 quantisation on every frame
  - Undo stack (Ctrl+Z) with atomic transactions
  - Modifier keys: Shift = fine (÷10), Ctrl = snap to 10 Nm
  - Proportional compression scaling on torque drag
"""

import logging
import tkinter as tk
from typing import List, Callable, Optional, Dict, Tuple

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.widgets import RadioButtons

from ..core.models import TorqueTable, TorqueRow, DragTransaction
from .plotting import extract_curve_data, TORQUE_COLORS, POWER_COLORS
from .formatting import quantise_f32

logger = logging.getLogger(__name__)

# Clamping ranges (from spec FR-009)
TORQUE_MIN, TORQUE_MAX = -4000.0, 10000.0
COMPRESSION_MIN, COMPRESSION_MAX = -300.0, 300.0

# Undo stack depth (from spec FR-024)
UNDO_STACK_MAX = 50

# Hit-test tolerance in pixels (from spec FR-025)
PICKER_TOLERANCE = 7


class DraggableTorquePlot:
    """Interactive plot window for dragging torque/compression points.

    Creates a Tkinter Toplevel with an embedded matplotlib figure.
    Points are draggable vertically; changes propagate to the EDF
    binary via the on_row_changed callback on mouse-up.

    Args:
        parent: The main Tk application window.
        tables: List of parsed TorqueTable objects.
        data: The in-memory EDF bytearray.
        filename: Filename for the title bar.
        on_row_changed: Callback(row: TorqueRow) invoked after each drag commit.
        on_close: Callback() invoked when the plot window is closed.
        mode: "torque" or "compression" — which curve is draggable.
    """

    def __init__(
        self,
        parent: tk.Tk,
        tables: List[TorqueTable],
        data: bytearray,
        filename: str,
        on_row_changed: Callable[[TorqueRow], None],
        on_close: Callable[[], None],
        mode: str = "torque",
    ):
        self.parent = parent
        self.tables = tables
        self.data = data
        self.filename = filename
        self.on_row_changed = on_row_changed
        self._on_close_callback = on_close
        self.mode = mode

        # ── Drag state ──────────────────────────────────────────────
        self._dragging = False
        self._drag_line: Optional[Line2D] = None      # The line artist being dragged
        self._drag_point_idx: Optional[int] = None     # Index within the line's data arrays
        self._drag_table_idx: Optional[int] = None     # Which table owns this line
        self._drag_row: Optional[TorqueRow] = None     # The TorqueRow being modified
        self._drag_start_x: Optional[float] = None     # Original RPM (locked during drag)
        self._drag_start_y: Optional[float] = None     # Original value before drag
        self._drag_start_torque: Optional[float] = None
        self._drag_start_compression: Optional[float] = None
        self._original_markersize: Optional[float] = None

        # ── Display Options ─────────────────────────────────────────
        self.display_units = "HP"  # 'HP' or 'kW'

        # ── Undo stack ──────────────────────────────────────────────
        self._undo_stack: List[DragTransaction] = []

        # ── Line → table mapping ───────────────────────────────────
        # Maps line artist id → (table_index, list of draggable TorqueRow refs)
        self._line_table_map: Dict[int, Tuple[int, List[TorqueRow]]] = {}

        # ── Build window ────────────────────────────────────────────
        self._build_window()
        self._plot_curves()
        self._connect_events()

    # ════════════════════════════════════════════════════════════════
    # Window construction
    # ════════════════════════════════════════════════════════════════

    def _build_window(self):
        """Create the Toplevel, Figure, Canvas, and Toolbar."""
        self.toplevel = tk.Toplevel(self.parent)
        mode_label = "Torque & Power" if self.mode == "torque" else "Compression"
        self.toplevel.title(f"Interactive {mode_label} — {self.filename}")
        self.toplevel.geometry("1100x650")
        self.toplevel.protocol("WM_DELETE_WINDOW", self._on_window_close)

        self.fig = Figure(figsize=(10, 6), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.toplevel)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.toolbar = NavigationToolbar2Tk(self.canvas, self.toplevel)
        self.toolbar.update()

        # Undo keybinding
        self.toplevel.bind('<Control-z>', lambda e: self._undo())

        # Annotation for value tooltip (initially hidden)
        self._annotation = None  # Created after axes exist

    def _plot_curves(self):
        """Draw the initial curves with picker-enabled markers."""
        self.fig.clear()

        if self.mode == "torque":
            self._plot_torque_mode()
        else:
            self._plot_compression_mode()

        self.canvas.draw()

    def _plot_torque_mode(self):
        """Plot Torque & Power vs RPM with draggable torque markers."""
        self.ax1 = self.fig.add_subplot(111)
        self.ax2 = self.ax1.twinx()

        for t_idx, table in enumerate(self.tables):
            rpms, torques, _comps, powers = extract_curve_data(table)
            # Build list of draggable rows (skip endvar)
            draggable_rows = [r for r in table.rows if r.torque is not None]

            if rpms:
                tc = TORQUE_COLORS[t_idx % len(TORQUE_COLORS)]
                pc = POWER_COLORS[t_idx % len(POWER_COLORS)]

                # Torque line — DRAGGABLE (picker enabled)
                line_t, = self.ax1.plot(
                    rpms, torques,
                    marker='o', linewidth=2, markersize=6,
                    color=tc, picker=PICKER_TOLERANCE,
                    label=f'Table {t_idx} Torque',
                )
                self._line_table_map[id(line_t)] = (t_idx, draggable_rows)

                # Power line — NOT draggable (no picker)
                self.ax2.plot(
                    rpms, [p * self._get_power_multiplier() for p in powers],
                    marker='s', linewidth=2, markersize=4,
                    linestyle='--', color=pc,
                    label=f'Table {t_idx} Power',
                )

        self.ax1.set_xlabel('RPM', fontsize=12)
        self.ax1.set_ylabel('Torque (Nm)', fontsize=12, color='tab:blue')
        self.ax1.tick_params(axis='y', labelcolor='tab:blue')
        self.ax2.set_ylabel(f'Power ({self.display_units})', fontsize=12, color='tab:orange')
        self.ax2.tick_params(axis='y', labelcolor='tab:orange')
        self.ax1.set_title(f'Interactive Torque & Power — drag points vertically', fontsize=13)
        self.ax1.grid(True, alpha=0.3)

        lines1, labels1 = self.ax1.get_legend_handles_labels()
        lines2, labels2 = self.ax2.get_legend_handles_labels()
        self.ax1.legend(lines1 + lines2, labels1 + labels2, loc='best', fontsize=9)

        # Create annotation (hidden)
        self._annotation = self.ax1.annotate(
            '', xy=(0, 0), fontsize=10, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.85),
            visible=False,
        )

        # Add RadioButtons for Unit Toggling
        self.rax = self.fig.add_axes([0.02, 0.9, 0.08, 0.08])
        self.radio = RadioButtons(self.rax, ('HP', 'kW'))
        self.radio.on_clicked(self._unit_changed)

    def _get_power_multiplier(self) -> float:
        return 1.34102 if self.display_units == 'HP' else 1.0

    def _unit_changed(self, label):
        self.display_units = label
        self.ax2.set_ylabel(f'Power ({self.display_units})', fontsize=12, color='tab:orange')
        self._update_all_power_curves()
        self.canvas.draw_idle()

    def _update_all_power_curves(self):
        if self.mode != "torque" or self.ax2 is None:
            return
        mult = self._get_power_multiplier()
        power_lines = [l for l in self.ax2.get_lines()]
        for t_idx, table in enumerate(self.tables):
            if t_idx < len(power_lines):
                rpms, _, _, powers = extract_curve_data(table)
                power_lines[t_idx].set_data(rpms, [p * mult for p in powers])

    def _plot_compression_mode(self):
        """Plot Compression vs RPM with draggable compression markers."""
        self.ax1 = self.fig.add_subplot(111)
        self.ax2 = None  # No secondary axis for compression

        for t_idx, table in enumerate(self.tables):
            rpms, _torques, comps, _powers = extract_curve_data(table)
            draggable_rows = [r for r in table.rows if r.torque is not None]

            if rpms:
                line_c, = self.ax1.plot(
                    rpms, comps,
                    marker='o', linewidth=2, markersize=6,
                    picker=PICKER_TOLERANCE,
                    label=f'Table {t_idx} Compression',
                )
                self._line_table_map[id(line_c)] = (t_idx, draggable_rows)

        self.ax1.set_xlabel('RPM', fontsize=12)
        self.ax1.set_ylabel('Compression (-Nm)', fontsize=12)
        self.ax1.set_title('Interactive Compression — drag points vertically', fontsize=13)
        self.ax1.grid(True, alpha=0.3)
        self.ax1.legend(loc='best', fontsize=9)

        self._annotation = self.ax1.annotate(
            '', xy=(0, 0), fontsize=10, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', alpha=0.85),
            visible=False,
        )

    # ════════════════════════════════════════════════════════════════
    # Event handling
    # ════════════════════════════════════════════════════════════════

    def _connect_events(self):
        """Connect matplotlib events to handler methods."""
        self._cid_press = self.canvas.mpl_connect('button_press_event', self._on_press)
        self._cid_motion = self.canvas.mpl_connect('motion_notify_event', self._on_motion)
        self._cid_release = self.canvas.mpl_connect('button_release_event', self._on_release)

    def _disconnect_events(self):
        """Disconnect matplotlib events."""
        for cid in (self._cid_press, self._cid_motion, self._cid_release):
            try:
                self.canvas.mpl_disconnect(cid)
            except Exception:
                pass

    def _on_press(self, event):
        """Handle mouse button press — select a draggable point."""
        valid_axes = [self.ax1]
        if getattr(self, "ax2", None) is not None:
            valid_axes.append(self.ax2)

        if event.inaxes not in valid_axes:
            return
        if event.button != 1:  # Left click only
            return

        # Hide annotation from previous drag
        if self._annotation:
            self._annotation.set_visible(False)

        # Find which line's point was clicked (topmost = last checked wins → FR-026)
        best_line = None
        best_idx = None

        for line in self.ax1.get_lines():
            if id(line) not in self._line_table_map:
                continue  # Skip non-draggable lines (e.g., power)

            contains, info = line.contains(event)
            if contains and 'ind' in info and len(info['ind']) > 0:
                # Take the nearest index
                best_line = line
                best_idx = info['ind'][0]

        if best_line is None:
            return

        # Resolve table and row
        table_idx, draggable_rows = self._line_table_map[id(best_line)]
        if best_idx >= len(draggable_rows):
            return

        row = draggable_rows[best_idx]

        # Don't allow dragging endvar rows (FR-011)
        if row.torque is None:
            return

        # Enter DRAGGING state
        self._dragging = True
        self._drag_line = best_line
        self._drag_point_idx = best_idx
        self._drag_table_idx = table_idx
        self._drag_row = row
        self._drag_start_x = best_line.get_xdata()[best_idx]
        self._drag_start_y = best_line.get_ydata()[best_idx]
        self._drag_start_torque = row.torque
        self._drag_start_compression = row.compression

        # Visual selection indicator (FR-013): enlarge marker
        self._original_markersize = best_line.get_markersize()
        best_line.set_markersize(self._original_markersize * 2)
        self.canvas.draw_idle()

    def _on_motion(self, event):
        """Handle mouse movement — update marker position during drag."""
        if not self._dragging:
            return
        valid_axes = [self.ax1]
        if getattr(self, "ax2", None) is not None:
            valid_axes.append(self.ax2)

        if event.inaxes not in valid_axes:
            return

        # Determine raw new Y value based on ax1 coords (since event.ydata might be ax2)
        _, new_y = self.ax1.transData.inverted().transform((event.x, event.y))

        # Apply modifier keys (FR-018)
        if hasattr(event, 'key') and event.key:
            if 'shift' in event.key:
                # Fine mode: reduce movement by 10x
                delta = new_y - self._drag_start_y
                new_y = self._drag_start_y + delta / 10.0
            elif 'control' in event.key:
                # Snap mode: round to nearest 10
                new_y = round(new_y / 10.0) * 10.0

        # Clamp (FR-009)
        if self.mode == "torque":
            new_y = max(TORQUE_MIN, min(TORQUE_MAX, new_y))
        else:
            new_y = max(COMPRESSION_MIN, min(COMPRESSION_MAX, new_y))

        # Quantise to float32 (FR-015)
        new_y = quantise_f32(new_y)

        # Update marker position — vertical only, RPM frozen (FR-002)
        xdata = list(self._drag_line.get_xdata())
        ydata = list(self._drag_line.get_ydata())
        ydata[self._drag_point_idx] = new_y
        # X stays at original RPM — never event.xdata
        self._drag_line.set_data(xdata, ydata)

        # If torque mode, recompute power curve on ax2
        if self.mode == "torque" and self.ax2 is not None:
            rpm = xdata[self._drag_point_idx]
            self._update_power_curve(self._drag_table_idx, self._drag_point_idx, rpm, new_y)

        # Update annotation (FR-008, FR-016)
        self._update_annotation(xdata[self._drag_point_idx], new_y, new_y)

        self.canvas.draw_idle()

    def _on_release(self, event):
        """Handle mouse button release — commit the drag."""
        if not self._dragging:
            return

        # Get final value from line data
        ydata = list(self._drag_line.get_ydata())
        final_y = ydata[self._drag_point_idx]
        final_y = quantise_f32(final_y)

        # Restore marker size (FR-013)
        if self._original_markersize is not None:
            self._drag_line.set_markersize(self._original_markersize)

        # Hide annotation
        if self._annotation:
            self._annotation.set_visible(False)

        # Compute new values
        row = self._drag_row
        old_torque = self._drag_start_torque
        old_compression = self._drag_start_compression

        if self.mode == "torque":
            new_torque = final_y
            # Proportional compression scaling (FR-031)
            if old_torque != 0:
                ratio = new_torque / old_torque
                new_compression = quantise_f32(old_compression * ratio)
            else:
                new_compression = old_compression  # T_old == 0 → freeze compression
            # Clamp compression independently
            new_compression = max(COMPRESSION_MIN, min(COMPRESSION_MAX, new_compression))
            new_compression = quantise_f32(new_compression)
        else:
            new_torque = old_torque  # Compression mode doesn't change torque (FR-033)
            new_compression = final_y

        # Create undo transaction (FR-023)
        txn = DragTransaction(
            table_index=self._drag_table_idx,
            row_index=self._find_row_index(self._drag_row),
            field=self.mode,
            start_torque=old_torque,
            end_torque=new_torque,
            start_compression=old_compression,
            end_compression=new_compression,
        )
        self._undo_stack.append(txn)
        if len(self._undo_stack) > UNDO_STACK_MAX:
            self._undo_stack = self._undo_stack[-UNDO_STACK_MAX:]

        # Update the TorqueRow in-place
        row.torque = new_torque
        row.compression = new_compression

        # Commit to binary via callback (FR-005, FR-006, FR-007)
        try:
            self.on_row_changed(row)
        except Exception as e:
            # FR-030: revert on write failure
            logger.error(f"Write-back failed: {e}")
            row.torque = old_torque
            row.compression = old_compression
            self._undo_stack.pop()
            self._replot_line(self._drag_table_idx)
            self.canvas.draw_idle()
            return

        # Exit DRAGGING state
        self._dragging = False
        self._drag_line = None
        self._drag_point_idx = None
        self._drag_table_idx = None
        self._drag_row = None

        self.canvas.draw_idle()

    # ════════════════════════════════════════════════════════════════
    # Undo
    # ════════════════════════════════════════════════════════════════

    def _undo(self):
        """Revert the last drag operation (FR-012)."""
        if not self._undo_stack:
            return

        txn = self._undo_stack.pop()

        # Find the row
        table = self.tables[txn.table_index]
        draggable_rows = [r for r in table.rows if r.torque is not None]
        if txn.row_index >= len(draggable_rows):
            return
        row = draggable_rows[txn.row_index]

        # Restore values
        row.torque = txn.start_torque
        row.compression = txn.start_compression

        # Commit reverted values to binary
        try:
            self.on_row_changed(row)
        except Exception as e:
            logger.error(f"Undo write-back failed: {e}")

        # Replot the affected table's line
        self._replot_line(txn.table_index)
        self.canvas.draw_idle()

    # ════════════════════════════════════════════════════════════════
    # Helpers
    # ════════════════════════════════════════════════════════════════

    def _find_row_index(self, row: TorqueRow) -> int:
        """Find the index of a row within its table's draggable rows."""
        if self._drag_table_idx is None:
            return 0
        table = self.tables[self._drag_table_idx]
        draggable = [r for r in table.rows if r.torque is not None]
        for i, r in enumerate(draggable):
            if r is row:
                return i
        return 0

    def _update_annotation(self, x: float, y: float, value: float):
        """Show/update the value annotation near the cursor."""
        if self._annotation is None:
            return
        unit = "Nm" if self.mode == "torque" else "-Nm"
        self._annotation.set_text(f"{value:.1f} {unit}")
        self._annotation.xy = (x, y)
        # Offset slightly so annotation doesn't cover the point
        self._annotation.xyann = (15, 15)
        self._annotation.set_visible(True)

    def _update_power_curve(self, table_idx: int, point_idx: int, rpm: float, torque: float):
        """Recompute and update the power curve for the given table."""
        # Find the power line for this table on ax2
        if self.ax2 is None:
            return

        power_lines = [l for l in self.ax2.get_lines()]
        if table_idx >= len(power_lines):
            return

        power_line = power_lines[table_idx]
        ydata = list(power_line.get_ydata())
        if point_idx < len(ydata):
            ydata[point_idx] = ((torque * rpm) / 9549.3) * self._get_power_multiplier()
            power_line.set_ydata(ydata)

    def _replot_line(self, table_idx: int):
        """Replot a specific table's line from current TorqueRow data."""
        table = self.tables[table_idx]
        rpms, torques, comps, powers = extract_curve_data(table)

        # Find the torque/compression line for this table
        for line in self.ax1.get_lines():
            if id(line) in self._line_table_map:
                t_idx, _ = self._line_table_map[id(line)]
                if t_idx == table_idx:
                    if self.mode == "torque":
                        line.set_data(rpms, torques)
                    else:
                        line.set_data(rpms, comps)
                    break

        # Update power line if in torque mode
        if self.mode == "torque" and self.ax2 is not None:
            mult = self._get_power_multiplier()
            power_lines = [l for l in self.ax2.get_lines()]
            if table_idx < len(power_lines):
                power_lines[table_idx].set_data(rpms, [p * mult for p in powers])

    def _on_window_close(self):
        """Handle plot window close — cancel drag, cleanup, notify app."""
        # FR-014: cancel in-progress drag
        if self._dragging and self._drag_row is not None:
            # Revert to pre-drag values
            self._drag_row.torque = self._drag_start_torque
            self._drag_row.compression = self._drag_start_compression
            self._dragging = False

        self._disconnect_events()
        self._on_close_callback()
        self.toplevel.destroy()
