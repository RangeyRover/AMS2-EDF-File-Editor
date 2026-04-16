# Data Model: Draggable Torque Graph

**Branch**: `001-draggable-torque-graph` | **Date**: 2026-04-16

## Existing Entities (Unchanged)

### TorqueRow
```
Fields:
  rpm: float              # RPM value (locked during drag — FR-002)
  compression: float      # Compression in Nm (modifiable — FR-031/032)
  torque: Optional[float] # Torque in Nm (primary drag target — FR-001)
  offset: int             # Byte offset in EDF binary
  kind: str               # '0rpm' | 'row_i' | 'row_f' | 'endvar'

Constraints:
  - rpm: [0, 25000] — immutable during drag
  - compression: [-300, 300] — clamped during drag (FR-009 analogue)
  - torque: [-4000, 10000] — clamped during drag (FR-009)
  - kind == 'endvar' → torque is None → NOT draggable (FR-011)
  - All float fields stored as IEEE 754 float32 in binary

Properties:
  size: int — computed from kind + struct size
```

### TorqueTable
```
Fields:
  offset: int               # Byte offset of table start in EDF binary
  rows: List[TorqueRow]     # Sorted by RPM

Constraints:
  - Row order MUST NOT change during drag (FR-021)
  - Cross-table isolation: drag on Table N must not touch Table M bytes (FR-010)

Properties:
  size: int — sum of row sizes
```

### Parameter, BoostRow, BoostTable
```
No changes — these entities are not involved in drag operations.
```

## New Entity

### DragTransaction
```
Location: src/core/models.py

Fields:
  table_index: int           # Index of the TorqueTable in the tables list
  row_index: int             # Index of the TorqueRow within the table
  field: str                 # "torque" | "compression" — which was the primary drag target
  start_torque: float        # Torque value before drag (float32-quantised)
  end_torque: float          # Torque value after drag (float32-quantised)
  start_compression: float   # Compression value before drag (float32-quantised)
  end_compression: float     # Compression value after drag (float32-quantised)

Constraints:
  - All float values are float32-quantised (FR-015, FR-034)
  - One transaction per mouse-down→up cycle (FR-023)
  - Stack capped at 50 (FR-024)
  - Stack cleared on file load/close (Assumption)

Lifecycle:
  Created: on mouse-up (commit)
  Consumed: on Ctrl+Z (undo — pops from stack, restores start_* values)
  Destroyed: when stack exceeds 50 (oldest trimmed) or file loaded/closed
```

## Relationships

```
EDFEditorApp
  ├── has-many TorqueTable (self.tables)
  │     └── has-many TorqueRow (table.rows)
  ├── has-many BoostTable (self.boost) [unchanged]
  ├── has-many Parameter (self.params) [unchanged]
  ├── has-one bytearray (self.data) — the EDF binary
  └── has-one DraggableTorquePlot (when interactive plot open)
        ├── references TorqueTable[] (read + modify rows)
        ├── references bytearray (via on_row_changed callback)
        └── has-many DragTransaction (undo stack)
```

## State Transitions

### DraggableTorquePlot State Machine
```
┌──────┐   click on point   ┌──────────┐   mouse-up   ┌────────┐
│ IDLE │ ──────────────────→ │ DRAGGING │ ───────────→ │ COMMIT │
└──────┘                     └──────────┘              └────────┘
   ↑                              │                        │
   │                              │ Escape / window close  │
   │                              ▼                        │
   │                         ┌────────┐                    │
   │                         │ CANCEL │                    │
   │                         └────────┘                    │
   │                              │                        │
   └──────────────────────────────┴────────────────────────┘
                          → back to IDLE
```

### Interactive Plot Lifecycle
```
Plot opened → _interactive_plot_open = True → tree edit disabled (FR-035)
Plot closed → _interactive_plot_open = False → tree edit re-enabled (FR-036)
                                             → undo stack discarded
```

## Validation Rules (from spec)

| Field | Rule | FR |
|-------|------|-----|
| Dragged torque | Clamp to [-4000, 10000] | FR-009 |
| Dragged compression | Clamp to [-300, 300] | FR-009 analogue |
| All floats before write | Quantise to float32 | FR-015, FR-034 |
| RPM during drag | Immutable | FR-002, FR-021 |
| endvar rows | Not draggable | FR-011 |
| Undo stack depth | ≤ 50 | FR-024 |
