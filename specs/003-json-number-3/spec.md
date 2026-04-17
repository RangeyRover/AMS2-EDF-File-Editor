# Feature Specification: Non-Zero RPM Torque Table Anchor Generation

## 1. Problem Statement
The AMS2 EDF File Editor currently relies on locating static "0 RPM" signatures (`SIG_0RPM`: 9 bytes, or `SIG_0RPM_ALT`: 6 bytes) to identify the starting boundary of a torque table. However, analytical scans across `154` engine format edge cases have revealed that roughly 10% of physical engines (e.g. `BMW_LMR`, `aston_martin_db11_rac`, `Chevrolet_Camaro_GT4R`, `pors_919`) entirely omit the 0-RPM header row.

Instead, their torque tables begin immediately at idle operating RPMs (e.g., 1076 RPM). These engines open directly into the `ROW_I_STRUCT` structure (a `uint32` RPM > 0, an 8-byte spacer signature, followed by two floats for compression and torque). Because the parser statically drops tables lacking a 0 RPM row, these engines are mistakenly interpreted as having "0 torque tables". We need to refactor the parser to detect these tables by identifying the first incidence of a native `ROW_I_STRUCT` when a 0-RPM header is absent.

## 2. Target Audience
- Engine tuners operating on GT1, GTE, GT3, or bespoke hybrid engines (like Porsche 919) that don't map to standard consumer engines starting at 0 RPM.
- Simulatable physics reverse engineers exploring non-standard telemetry definitions.

## 3. User Scenarios
**Scenario 1: Opening a non-zero RPM engine**
- The user hits *File -> Open* and selects an advanced GT engine like `aston_martin_db11_rac.edfbin`.
- The UI mounts the parameters exactly as before. 
- The torque table is successfully parsed and made visible, starting immediately at its idle RPM anchor (e.g. 1361).
- The torque graph charts the engine dynamics from idle-to-rev-limit.
- Dragging, interpolating, saving, and unpacking algorithms gracefully handle the `TorqueTable`, proving entirely transparent to the user.

## 4. Functional Requirements
- **FR.1:** The Core Parser must gracefully scan for either `SIG_0RPM`, `SIG_0RPM_ALT`, or an orphan `ROW_I_STRUCT` sequence matching the `\x24\x8b\x0a\xb7\x71` static pattern.
- **FR.2:** If the token begins dynamically at `ROW_I_STRUCT`, the `TorqueTable` definition logic must successfully encapsulate and treat this very first row as `table.rows[0]` with `kind = 'row_i'`.
- **FR.3:** The file writer must respect the original sequence. If a torque table started as a non-zero RPM `row_i` struct during parsing, it must serialize directly back into the `row_i` struct block without injecting a synthetic 0-RPM row.
- **FR.4:** The graphical plotter (`interactive_plot.py`) must draw curves linearly even if the X-Axis starts at a non-zero integer. No hard-coded `x=0` intercepts may exist inside the visualization layer.

## 5. Success Criteria
- **100% Parsing Viability**: The script must successfully parse 100% of the 14 edge-case `.edfbin` files containing missing 0-RPM prefixes, extracting their full torque hierarchies.
- **Zero-Regression Serializer**: Hex-validations must prove that any byte-size offset or table layout remains completely preserved when written back. Re-injecting modifications into a missing-header engine must remain perfectly playable.

## 6. Assumptions & Constraints
- The `\x24\x8b\x0a\xb7\x71` 5-byte common string is reliable across all missing-header engines.
- The UI plotter calculates power curves natively and automatically handles offset sequences gracefully. 

## 7. Dependencies
- No new external SDKs or external tooling is required, exclusively native Python structured struct unpacking.
