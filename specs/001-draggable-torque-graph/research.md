# Research: Draggable Torque Graph

**Branch**: `001-draggable-torque-graph` | **Date**: 2026-04-16

## R1: Matplotlib Event System for Drag Interaction

**Decision**: Use matplotlib's native `mpl_connect` event system with `button_press_event`, `motion_notify_event`, `button_release_event`.

**Rationale**: This is the documented, standard matplotlib pattern for draggable elements. The `picker` property enables configurable pixel-radius hit-testing. No external dependencies needed beyond existing matplotlib.

**Alternatives considered**:
- `pick_event` alone: Only fires on click, not during continuous drag — insufficient
- External libraries (plotly, bokeh): Would require complete plot rewrite — disproportionate effort
- Custom tkinter canvas drawing: Would lose matplotlib's axis scaling, zoom, annotation features

**Key implementation details**:
- `event.xdata` / `event.ydata` provide data coordinates (auto-scale with zoom — satisfies FR-017)
- `artist.contains(event)` returns `(bool, {'ind': [indices]})` — the `ind` array identifies WHICH point in a multi-point line was clicked
- For dual-axis plots (`twinx()`), `event.inaxes` identifies which axis was clicked — must filter to torque axis only
- `canvas.draw_idle()` coalesces redraw requests for performance (vs `canvas.draw()` which is immediate)
- Must keep strong reference to handler class to prevent garbage collection of event callbacks

## R2: Matplotlib + Tkinter Event Loop Coexistence

**Decision**: Embed matplotlib figure in a Tkinter `Toplevel` window using `FigureCanvasTkAgg` backend, eliminating `plt.show()`.

**Rationale**: `plt.show()` starts a competing event loop that conflicts with Tkinter's `mainloop()`. Embedding via `FigureCanvasTkAgg` shares the single Tkinter event loop, enabling:
- Real-time tree-view and hex-view updates from drag callbacks (FR-006, FR-007)
- Reliable window close detection for FR-035/036 (concurrent edit prevention)
- Standard Tkinter keybinding for Ctrl+Z undo (FR-012)

**Alternatives considered**:
- `plt.show(block=False)`: Fragile on Windows, requires polling, no reliable event interop
- Separate thread/process: Over-engineered, introduces IPC complexity for a desktop GUI

**Impact on existing code**:
- `plotting.py`'s `plot_torque_rpm()` / `plot_compression_rpm()` remain unchanged for non-interactive use
- New `interactive_plot.py` uses `Figure()` (not `plt.subplots()`) and `FigureCanvasTkAgg`

## R3: Proportional Compression Scaling

**Decision**: When torque changes from `T_old → T_new`, set `C_new = C_old × (T_new / T_old)`. Guard: if `T_old == 0`, leave compression unchanged.

**Rationale**: Maintains the physical ratio between torque and compression. Simple, predictable, and reversible via undo.

**Alternatives considered**:
- Additive scaling (C_new = C_old + delta): Doesn't preserve ratio, physically meaningless
- Independent (no coupling): User explicitly rejected this as default in clarification Q1
- Lookup table: No basis in EDF format — compression is a free float, not indexed

**Edge cases resolved**:
- `T_old == 0`: Freeze compression at current value (ratio undefined)
- Resulting `C_new` out of `[-300, 300]`: Clamp independently of torque clamping
- Both fields quantised to float32 before storage

## R4: Float32 Quantisation Strategy

**Decision**: Use `struct.pack('<f', val) → struct.unpack('<f', ...)` round-trip for quantisation.

**Rationale**: This is the exact encoding path already used by `write_torque_row()`. Using the same mechanism guarantees tooltip display matches stored value exactly.

**Alternatives considered**:
- `numpy.float32()`: Introduces numpy dependency — unnecessary
- Custom rounding: Error-prone, wouldn't match actual storage encoding

## R5: Undo Stack Architecture

**Decision**: Simple list-based stack of `DragTransaction` dataclass instances, capped at 50 entries, cleared on file load/close.

**Rationale**: Desktop single-user app with <120 typical data points. Full command pattern is over-engineered. List pop/push is O(1), memory trivial (<50 × 7 floats ≈ 2.8KB).

**Alternatives considered**:
- Full command pattern with redo: Scope creep — redo not in spec
- Memento pattern (full state snapshot): Overkill for per-field changes; would snapshot entire bytearray
- Application-level undo (tkinter): Doesn't cover matplotlib state
