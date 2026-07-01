# Implementation Plan: P2P and Boost Table Interactive Editing

**Branch**: `feature/boost-table-variants` | **Date**: 2026-06-30 | **Spec**: [kitty-specs/001-p2p-boost-editing/spec.md]

## Summary

Implement full parsing, writing, and interactive editing support for the Push-to-Pass (P2P) tables and the 7 variants of the Boost table, mirroring the functionality currently available for Torque and Compression tables. 
We will implement an industry-standard dual-view approach (3D visualizer + 2D multi-line editor) to handle the multidimensional nature of these maps.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: Tkinter, matplotlib
**Target Platform**: Desktop (Windows)
**Project Type**: GUI Application

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- The new features will be isolated to the `experimental_definitions` and `debug` namespaces or integrated gracefully into `core` without breaking existing torque editing capabilities.

## Technical Implementation Details

### Core Data Structures
- **`src/core/constants.py`**
  - Add signatures for all 7 boost variants (e.g., `SIG_BOOST_0RPM_4F`, `SIG_BOOST_ROW_5B`, etc.).
  - Add signatures for P2P (`SIG_P2P_FULL`, `SIG_P2P_ZERO`).
  - Add `struct.Struct` instances for parsing these byte payloads.

- **`src/core/models.py`**
  - Update `BoostRow` to gracefully handle missing variables in 4-float or 5-byte variants (e.g., storing `None`).
  - Add `P2PRow` and `P2PTable` dataclasses to store the 4D values (N, X, Y, V).

### Parser & Writer Architecture Upgrade
- **`src/core/parser.py`**
  - **Programmatic Hash Recognition**: Instead of lazy byte-matching entire long signatures (e.g. `\x24\x8b\x0a\xb7\x71\x83\x02`), the parser will be upgraded to understand the fundamental EDF framework: `[marker][hash][suffix][data]`.
  - The parser will scan for valid markers (`0x24`), extract the 4-byte hash, and compare it programmatically against known tables (Torque=`8b0ab771`, Boost=`515f5e83`, P2P=`29494504`).
  - Upon a hash match, it will decode the suffix dynamically to determine the row's data structure (e.g. 4-float vs 5-float variants) rather than relying on hardcoded monolithic signature matching.
- **`src/core/writer.py`**
  - Update `write_boost_row` and implement `write_p2p_row` to pack the correct struct based on the dynamically decoded row variant.

### GUI Updates
- **`src/gui/app.py`**
  - Parse the P2P tables on file load and pass them to the TreeView.
  - Add new menu items under Tools: `Interactive Boost Editor` and `Interactive P2P Editor`.
- **`src/gui/tree_view.py`**
  - Add logic to display P2P nodes (showing N, X, Y, V).
  - Update Boost display to handle variants where some throttle values are missing.
- **`src/utils/interactive_plot.py`**
  - Following ECU tuning industry standards, multidimensional maps like Boost and P2P will use a dual-view approach:
    1. **3D Surface View (Visualization)**: A rotatable 3D surface map (RPM vs Throttle vs Target/Multiplier) to visualize the overall curve. Uses `mpl_toolkits.mplot3d`.
    2. **2D Multi-Line Editor (Editing)**: The active editing interface will be a 2D line graph displaying multiple curves (one for each Throttle position). Nodes can be dragged vertically to adjust values.
  - **P2P Table Handling**: P2P includes a `Mode/Gear [N]` dimension. We will add a Tkinter Combobox to select the Mode. The 3D surface and 2D editor will then display the map for that specific Mode.

## Verification Plan

### Manual Verification
- Open a base game F-USA G4 file.
- Verify the P2P table is found and has 441 entries.
- Open the Interactive P2P Editor, select a mode, and drag a point. Check that both 2D and 3D plots reflect the change.
- Save the file and reload it to ensure the binary was overwritten correctly without corrupting the file size or surrounding data.
- Open a file with anomalous boost tables (e.g., one that uses the 4-float variant) and verify it reads/writes correctly.