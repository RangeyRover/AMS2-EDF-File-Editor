# Research Findings: f309-power-units

## Findings

### 1. `f309.edfbin` Alternate Torque Format
- **Decision**: Update `parser.find_all` and `TorqueRow` model to recognize the `03 02` signature and handle a 6-byte unpacking sequence.
- **Rationale**: Based on binary hex analysis, files like `f309.edfbin` use `\x24\x8B\x0A\xB7\x71\x03\x02` for the 0RPM row, followed directly by a 6-byte struct (`B B f`), omitting the torque float target entirely. Updating the parser to accept both standard (`83 02`) and alternate (`03 02`) headers resolves the loading failure.
- **Alternatives considered**: None. The binary format explicitly demands this handler.

### 2. HP vs kW Display Mathematics
- **Decision**: Implement the math conversion in the plotting layer (`interactive_plot.py` and `app.py`) keeping the underlying `TorqueRow` bytes in unmodified base units. User selects a state toggle which drives the `1.34102` multiplication for power readout axes and tooltips.
- **Rationale**: HP = kW * 1.34102. Separating display units from storage units prevents file corruption during read/write cycles.
- **Alternatives considered**: Converting the base torque values, which was rejected because it would irreversibly mangle the physics hex layout.
