# Feature Specification: Draggable Torque Graph

**Feature Branch**: `001-draggable-torque-graph`  
**Created**: 2026-04-16  
**Revised**: 2026-04-16 (v2 — incorporated data-safety and UX hardening feedback)  
**Status**: Draft  
**Input**: User description: "Make torque changes in the EDF tool torque graph user-draggable"

## Clarifications

### Session 2026-04-16

- Q: Should compression values change when torque is dragged, or remain independent? → A: Compression is independently draggable as a separate curve on the Compression vs RPM plot, AND by default when dragging torque, compression scales proportionally with the torque change.
- Q: Should the interactive plot be modal (blocking the editor) or non-modal, given the risk of conflicting edits via tree-view and drag simultaneously? → A: Keep non-modal but disable tree-view editing of torque/compression rows while the interactive plot is open.
- Q: Should the system warn when adjacent torque deltas exceed a threshold (FR-022)? → A: No — withdraw FR-022 entirely. User beware; users are responsible for their own curve shapes.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Drag Torque Points on Graph (Priority: P1)

A user opens an EDF file and launches the Torque/Power vs RPM plot from the Tools menu. On the graph, each torque data point (currently displayed as a circle marker) becomes interactive. The user clicks on a torque marker and drags it vertically to increase or decrease the torque value at that RPM. As the user drags, the marker follows the cursor and the torque curve redraws in real-time. When the user releases the mouse button, the dragged value is quantised to the nearest valid EDF encoding step and committed to the in-memory EDF data. The tree view refreshes to show the stored value, and the hex view reflects the binary change.

**Why this priority**: This is the core value proposition — direct visual manipulation of the torque curve eliminates the need to double-click individual rows, manually type numeric values, and mentally map numbers to curve shape. It transforms the editing workflow from numeric to visual.

**Independent Test**: Can be fully tested by opening any EDF file, plotting Torque/Power, dragging a single point up or down, and verifying the tree view and hex view both update with the new torque value.

**Acceptance Scenarios**:

1. **Given** an EDF file is loaded and the Torque/Power plot is open, **When** the user clicks on a torque data point marker, **Then** the marker becomes visually selected (e.g., enlarged or highlighted)
2. **Given** a torque marker is selected, **When** the user drags it vertically, **Then** the marker follows the cursor's Y-axis position and the connecting curve segments redraw in real-time
3. **Given** the user releases the mouse button after dragging, **Then** the new torque value is quantised to the nearest valid EDF encoding, written to in-memory EDF data, the tree view row updates, and the hex view reflects the change
4. **Given** the user drags a point, **When** they observe the Power curve (secondary axis), **Then** the power curve also updates to reflect the new torque value at that RPM
5. **Given** a dragged value is not exactly representable in EDF format, **When** the file is saved and reopened, **Then** the displayed value matches the quantised stored value exactly (no jitter)

---

### User Story 2 - Visual Feedback During Drag (Priority: P2)

While dragging a torque point, the user sees real-time feedback showing the **quantised (actual storable)** value at the cursor position, not the raw cursor-derived value. This helps the user set precise values without guessing. A tooltip or annotation near the cursor displays the torque value (in Nm) corresponding to the current vertical position, reflecting the value that will actually be written to the EDF binary.

**Why this priority**: Without numeric feedback, dragging is imprecise. Users tuning engine files need to hit specific torque targets, so visual feedback bridges the gap between graphical and numeric editing. Showing the quantised value prevents confusion where the tooltip says one thing but the stored value differs.

**Independent Test**: Can be tested by dragging any torque point and verifying a value readout appears near the cursor that updates continuously during the drag operation and matches the value that appears in the tree view after release.

**Acceptance Scenarios**:

1. **Given** the user is dragging a torque marker, **When** the cursor moves vertically, **Then** a value annotation near the cursor shows the quantised torque value in Nm, updating in real-time
2. **Given** the user is dragging a torque marker, **When** they hold the position steady, **Then** the displayed value remains stable and readable
3. **Given** the user releases after dragging, **When** they check the tree view, **Then** the tree view value matches exactly what the tooltip showed at the moment of release

---

### User Story 3 - Constrained Drag Axis (Priority: P2)

Dragging is constrained to vertical movement only (torque axis). The RPM value of each data point is fixed and cannot be changed by dragging. This prevents accidental horizontal shifts that would corrupt the RPM sequencing of the torque table.

**Why this priority**: RPM values in EDF files define the curve's horizontal structure and are tied to the binary row format (integer or float RPM). Allowing horizontal drag would risk breaking table ordering and introducing invalid RPM values. Vertical-only constraint is essential for data safety.

**Independent Test**: Can be tested by dragging a point diagonally and verifying that only the torque (Y) value changes while the RPM (X) value remains unchanged in both the graph and the tree view.

**Acceptance Scenarios**:

1. **Given** the user drags a torque marker diagonally, **When** they release, **Then** only the torque value changes; the RPM value in the tree view remains identical to the original
2. **Given** the user attempts to drag horizontally, **When** the cursor moves left or right, **Then** the marker stays locked to its original X-axis (RPM) position

---

### User Story 4 - Multi-Table Awareness (Priority: P3)

When an EDF file contains multiple torque tables (common in multi-map engines), dragging a point on one table's curve only modifies that specific table. The user can visually distinguish which table each curve belongs to via colour coding (already implemented). Only markers on the curve the user clicks are draggable; nearby markers from other tables are not affected.

**Why this priority**: Prevents cross-table corruption. While less critical than basic drag functionality, it is essential for files with multiple torque maps.

**Independent Test**: Can be tested by loading a multi-table EDF file, dragging a point on Table 0's curve, and verifying Table 1's data remains unchanged in both the graph and tree view.

**Acceptance Scenarios**:

1. **Given** an EDF file with multiple torque tables is loaded and plotted, **When** the user drags a point on Table 0's curve, **Then** only Table 0's data is modified; Table 1 (and any others) remain unchanged
2. **Given** curves from different tables overlap visually, **When** the user clicks near an overlap area, **Then** only the nearest point on the visually topmost rendered curve is selected for dragging

---

### User Story 5 - Undo Drag Operations (Priority: P3)

After dragging a point to a new position, the user can press Ctrl+Z to revert the last drag operation, restoring the previous torque value for that data point. Multiple sequential drag operations can be undone in order (undo stack). Each drag action (mouse-down → movement → mouse-up) counts as a single undoable transaction regardless of how many intermediate positions the cursor passed through.

**Why this priority**: Drag interactions are inherently imprecise compared to typed values. A multi-level undo mechanism reduces the cost of mistakes and encourages experimentation with curve shapes.

**Independent Test**: Can be tested by dragging multiple points in sequence, pressing Ctrl+Z repeatedly, and verifying each drag reverts in reverse order across the graph, tree view, and hex view.

**Acceptance Scenarios**:

1. **Given** the user has dragged 3 torque points in sequence, **When** the user presses Ctrl+Z three times, **Then** each point returns to its pre-drag position in reverse order, with tree view and binary data reverting for each
2. **Given** no drag operation has been performed, **When** the user presses Ctrl+Z, **Then** nothing happens (no error, no change)
3. **Given** the user has performed a single drag (mouse-down, continuous movement across 50 pixel positions, mouse-up), **When** they press Ctrl+Z once, **Then** the entire drag reverts as one transaction (not 50 micro-steps)

---

### User Story 6 - Precision Drag with Modifier Keys (Priority: P3)

The user can hold modifier keys during drag to control precision. Shift+drag provides fine adjustment (reduced sensitivity), and Ctrl+drag snaps to defined increments (e.g., nearest 10 Nm). This allows both coarse curve shaping and precise value targeting.

**Why this priority**: Default drag sensitivity scales with zoom level, but users tuning engines often need to hit exact round numbers. Modifier keys provide this without cluttering the default interaction.

**Independent Test**: Can be tested by dragging a point normally, then with Shift held (verifying reduced movement), then with Ctrl held (verifying snap behaviour).

**Acceptance Scenarios**:

1. **Given** the user drags a point while holding Shift, **When** they move the cursor the same distance as a normal drag, **Then** the torque change is approximately 1/10th of what a normal drag would produce
2. **Given** the user drags a point while holding Ctrl, **When** they release, **Then** the value snaps to the nearest defined increment (e.g., nearest 10 Nm)

---

### Edge Cases

#### UI Edge Cases
- What happens when the user drags a point beyond the plausible torque range (-4,000 to 10,000 Nm)? → The drag should be clamped to the plausible range boundaries
- What happens when the user drags the 0 RPM row's torque? → The 0 RPM point should be draggable like any other point (its RPM remains locked at 0)
- How does the system handle `endvar` rows that have no torque value? → `endvar` markers (if plotted) should not be draggable
- What happens if the user closes the plot window while a drag is in progress? → The drag operation should be cancelled; no partial update should be written
- What happens when the user tries to drag while no file is loaded? → Not applicable — the plot cannot be opened without a loaded file (existing guard)
- How does the system behave if matplotlib is not installed? → Not applicable — the plot itself cannot open without matplotlib (existing guard)

#### Data & Integrity Edge Cases
- What happens during rapid drag events (event flooding)? → System should throttle/coalesce intermediate events; only the final position on mouse-up triggers a commit
- What happens if the user switches table selection mid-drag? → The drag should complete on the originally-selected point; table switching should be ignored until mouse-up
- What happens if undo is pressed after a file reload? → Undo stack should be cleared when a file is loaded or reloaded; no cross-session undo
- What happens if the write-back to EDF memory fails (e.g., invalid offset or corrupted data)? → System must revert the visual state to the pre-drag position and present an error without corrupting the dataset
- What happens when a dragged torque value lands between valid EDF encoding steps (quantisation boundary)? → System rounds to the nearest valid encoding; the tooltip and graph show the quantised value, not the raw cursor value
- What happens if the user drags a torque point and the proportional compression scaling produces an out-of-range compression value? → Compression should be clamped to the plausible compression range (-300 to 300 Nm) independently of the torque clamp
- What happens if the user opens the interactive plot while a tree-view edit dialog is already open? → The edit dialog should be allowed to complete; FR-035 only prevents new edit dialogs from being opened while the plot is active

## Requirements *(mandatory)*

### Functional Requirements

#### Core Drag Interaction
- **FR-001**: System MUST make torque data point markers on the Torque/Power vs RPM plot clickable and draggable using mouse interaction
- **FR-002**: System MUST constrain drag movement to the vertical axis only (torque values); RPM values MUST remain unchanged during drag
- **FR-003**: System MUST update the torque curve line segments in real-time as the user drags a point
- **FR-004**: System MUST update the derived Power curve in real-time during drag to reflect the new torque value
- **FR-005**: System MUST write the new torque value to the in-memory EDF binary data when the user releases the mouse button (drop)
- **FR-006**: System MUST refresh the tree view to reflect updated torque values after a drag-and-drop operation
- **FR-007**: System MUST refresh the hex view to reflect the binary change after a drag-and-drop operation

#### Compression Drag Behaviour
- **FR-031**: When the user drags a torque point, the compression value for that row MUST by default scale proportionally with the torque change (i.e., if torque changes by X%, compression changes by X%)
- **FR-032**: The Compression vs RPM plot MUST also support independent drag interaction — compression data point markers on the Compression plot are clickable and vertically draggable, modifying only the compression value for that row
- **FR-033**: Compression drag on the Compression vs RPM plot MUST NOT affect the torque value for the same row
- **FR-034**: Compression values modified by drag (whether proportional or independent) MUST be quantised to the nearest valid EDF float32 encoding before writing to memory

#### Quantisation & Encoding Safety
- **FR-015**: System MUST quantise dragged torque values to the nearest valid EDF encoding step before writing to memory (torque is stored as IEEE 754 float32 in the EDF binary format)
- **FR-016**: System MUST display the quantised (actual stored) value in the tooltip during drag, not the raw cursor-derived value

#### Visual Feedback & Selection
- **FR-008**: System MUST display the current quantised torque value (in Nm) near the cursor during drag operations
- **FR-013**: System MUST visually indicate which data point is selected/being dragged (e.g., enlarged marker, colour change, or highlight)
- **FR-025**: System MUST use a configurable pixel-radius hitbox (default 5–10px) for selecting markers on click
- **FR-026**: If multiple points from different tables fall within the hitbox, system MUST select the visually topmost (last-rendered) point

#### Drag Behaviour & Sensitivity
- **FR-017**: Drag sensitivity MUST scale proportionally with the current Y-axis zoom level so that the same cursor movement produces consistent visual displacement regardless of zoom
- **FR-018**: System SHOULD support modifier keys: Shift = fine adjustment (÷10 sensitivity); Ctrl = snap to defined increment (e.g., nearest 10 Nm)

#### Range & Integrity Constraints
- **FR-009**: System MUST clamp dragged torque values to the plausible range (-4,000 to 10,000 Nm)
- **FR-010**: System MUST ensure that dragging a point on one torque table does not affect data in other torque tables
- **FR-011**: System MUST NOT allow dragging of `endvar` row markers (rows without torque values)
- **FR-021**: System MUST NOT reorder RPM rows under any drag condition — row sequence in the binary must remain unchanged

#### Undo & Transaction Model
- **FR-012**: System MUST support undo operations (Ctrl+Z) that revert drag changes
- **FR-023**: A single drag action (mouse-down → move → mouse-up) MUST be recorded as one undoable transaction, regardless of intermediate cursor positions
- **FR-024**: System SHOULD support an undo stack of at least 50 operations

#### Unit System
- **FR-027**: System MUST use a consistent and documented unit system across all surfaces: Torque in Nm, RPM in revolutions per minute, Power in kW (derived as Torque × RPM / 9549.3)

#### Dirty State & Save Boundary
- **FR-028**: Drag operations MUST mark the file as having unsaved changes (dirty state), consistent with existing edit operations
- **FR-029**: System MUST NOT persist drag changes to disk until the user performs an explicit save action (File → Save or Ctrl+S)

#### Failure Handling
- **FR-014**: System MUST cancel any in-progress drag operation if the plot window is closed, with no partial data updates
- **FR-030**: If a write-back to EDF memory fails (e.g., invalid offset), system MUST revert the visual state to the pre-drag position and present an error without corrupting the dataset

#### Concurrent Edit Prevention
- **FR-035**: While an interactive drag-enabled plot window is open, the system MUST disable double-click editing of torque and compression values in the tree view (parameter editing remains enabled)
- **FR-036**: When the interactive plot window is closed, tree-view editing of torque and compression values MUST be re-enabled immediately

#### Future Scope (Deferred)
- **FR-019 (Future)**: System SHOULD support multi-point selection and drag (e.g., box-select or Ctrl+click to select multiple points, then drag as a group)
- **FR-020 (Future)**: System SHOULD support curve smoothing operations after drag (e.g., averaging between neighbours)

### Key Entities

- **TorqueRow**: Represents a single RPM/compression/torque data point in a torque table. Contains `rpm`, `compression`, `torque`, `offset`, and `kind` fields. The `torque` field is stored as IEEE 754 float32 in the EDF binary and is the value modified by drag operations. Rows with `kind == 'endvar'` have `torque = None` and are not draggable.
- **TorqueTable**: A collection of TorqueRows sorted by RPM. Each table is plotted as a separate coloured curve. The `offset` field identifies the table's position in the binary file.
- **Plot Figure**: The interactive graph window showing Torque & Power vs RPM curves. This is the surface where drag operations occur.
- **DragTransaction**: Represents a single atomic drag operation for undo purposes. Contains: `row_reference` (which TorqueRow was modified), `field` ("torque" or "compression" — which value was the primary drag target), `start_torque` / `end_torque`, `start_compression` / `end_compression` (captures both values since torque drag proportionally affects compression), and `timestamp`. A new DragTransaction is created on mouse-up and pushed onto the undo stack.

## Assumptions

- Torque values in EDF files are stored as IEEE 754 float32 (4 bytes), which provides approximately 7 decimal digits of precision. Quantisation for float32 is inherent — the spec requires rounding to the nearest representable float32 value.
- The existing `plausible_torque()` range (-4,000 to 10,000 Nm) is the correct clamping boundary for all drag operations.
- The existing colour scheme for multi-table curves provides sufficient visual distinction for table identification during drag.
- Undo stack is cleared on file open/close/reload — no cross-session undo history.
- Modifier key behaviour (FR-018) uses standard platform conventions (Shift, Ctrl) and does not conflict with existing keybindings.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can modify a torque value by dragging a point on the graph and see the change reflected in the tree view within 1 second of releasing the mouse button
- **SC-002**: For datasets with ≤ 200 data points, the torque curve and power curve both update visually during drag within 50ms of cursor movement; for larger datasets, the system should degrade gracefully (lower frame rate) without blocking the UI or dropping the drag interaction
- **SC-003**: RPM values remain byte-identical in the binary data after any drag operation — only torque and/or compression bytes change
- **SC-004**: A user can reshape an entire torque curve (all points) using drag operations alone, save the file, and reopen it to verify all changes persisted correctly
- **SC-005**: Dragging a point on Table 0 in a multi-table file produces zero byte changes in Table 1's binary region
- **SC-006**: The round-trip lossless property is preserved: drag-edit → save → reopen → values match the quantised dragged positions exactly (no float jitter between what was shown and what was stored)
- **SC-007**: A user can undo at least 50 sequential drag operations and verify each reverts correctly
