# Data Model: f309-power-units

## Key Entities & Fields

### `src.core.models.TorqueRow`
The foundational structure representing a row mapped from EDF bytes will be updated to handle the shortened alternate signature gracefully.

**Fields Updated**:
- `torque: Optional[float]` - Must tolerate `None` explicitly when `field == '0rpm_alt'`.

**Validation Rules**:
- Standard rows must retain `rpm`, `comp`, and `torque`.
- Alternate 6-byte 0RPM rows (`file_variant = f309`) explicitly map `torque` to zero/None for the starting sequence.

### `src.gui.app.py` & `src.utils.interactive_plot.py`
The graphical state manager handling live power interpolation.

**Fields Introduced/Updated**:
- `display_unit: str` (Enum: `kW` | `HP`) - Determines the active multiplier state.
- `power_multiplier: float` (1.0 for `kW`, 1.34102 for `HP`) - Dynamically scales the Y2 axis limits and the annotation tooltips during node dragging.
