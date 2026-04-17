# Feature Specification: f309-power-units

**Feature Branch**: `002-json-number-1`  
**Created**: 2026-04-17  
**Status**: Draft  
**Input**: User description: "using our new knowledge update the program to accomodate f309, also add a feature where the user can select the power in KW or HP, the game uses hp so users tend to prefere hp, i think this is just maths in the graph."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Seamlessly Load Alternate EDF Torque Tables (Priority: P1)

Users should be able to load variant EDF files (such as f309.edfbin) containing alternative torque table structures without errors, and plot their performance identical to standard files.

**Why this priority**: Without this functionality, alternative EDF files are silently ignored by the parser, leading to missing data and broken analysis workflows.

**Independent Test**: Can be fully tested by opening an alternate EDF file (like `f309.edfbin`), navigating to the Torque plot, and verifying that the torque curve and drag nodes render correctly without causing errors or empty datasets. Also tested by saving the file and ensuring it retains its alternative byte layout.

**Acceptance Scenarios**:

1. **Given** an alternate EDF file with the `03 02` 0RPM signature is loaded, **When** the parser reads the bytes, **Then** it correctly unpacks the 6-byte 0RPM row (extracting compression without failure).
2. **Given** an alternate EDF file is edited and saved, **When** the writer stores the file, **Then** it encodes the 0RPM row as a 6-byte struct, preserving the `03 02` signature rather than reverting it to `83 02`.

---

### User Story 2 - Toggle Power Unit Display (HP vs kW) (Priority: P2)

Users should be able to choose whether the engine power derived from the torque table is displayed in Kilowatts (kW) or Horsepower (HP) on the graphical plot (both static and interactive), providing a more intuitive reading depending on their preference.

**Why this priority**: The game uses horsepower natively, but standard engineering curves often display kW. Allowing the user to toggle units makes the tool much more user-friendly.

**Independent Test**: Can be tested by opening any EDF torque plot and toggling a UI switch/radio button between kW and HP, confirming the secondary Y-axis (Power) numerical scale and tooltip values dynamically update by a mathematical factor (1.34102).

**Acceptance Scenarios**:

1. **Given** the interactive torque plot is open, **When** the user clicks a "Unit: HP / kW" toggle, **Then** the secondary Y-axis (Power) updates automatically to reflect the correct numerical transformation.
2. **Given** the plot is displaying HP, **When** the user drags a torque node, **Then** the live power calculation continues to display correct HP values and tooltips for the newly interpolated torque levels.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST identify torque tables beginning with the alternate 0 RPM signature `\x24\x8B\x0A\xB7\x71\x03\x02`.
- **FR-002**: System MUST unpack the alternate 0 RPM row as a 6-byte sequence containing a byte, padding, and a float (compression), omitting torque.
- **FR-003**: System MUST serialize the alternate 0 RPM row back to the exact 6-byte sequence when saving changes to the torque table.
- **FR-004**: System MUST present a UI toggle or selection mechanism on the interactive torque plot to switch power units between kW and HP.
- **FR-005**: System MUST perform the conversion internally (Power(HP) = Power(kW) * 1.34102) seamlessly for display on the graph axis and data tooltips without mutating the underlying torque byte representations.
- **FR-006**: System MUST persist the selected unit preference throughout the session.

### Key Entities

- **TorqueRow**: Needs to gracefully handle missing torque initialization for the alternate 0RPM row.
- **Plotting Variables**: Requires unit state (`kW` vs `HP`) and dynamic mathematical scaling applied to the power traces.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of torque tables within alternate files (e.g. `f309.edfbin`) are correctly identified, plotted, and saved without data corruption.
- **SC-002**: Power values displayed when set to HP match the exact conversion mapping (kW * 1.341022) across all plot data points.
- **SC-003**: User can switch power units on the interactive plot instantly without reloading the file, restarting the plot, or refreshing the entire parent UI.
