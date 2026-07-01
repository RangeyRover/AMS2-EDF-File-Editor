# Specification: P2P and Boost Table Interactive Editing

## Overview

The AMS2 EDF File Editor currently parses and interactively edits Torque and Compression curves. With the recent discovery of the exact struct payloads for Push-to-Pass (P2P) tables and various Boost map variants within the `EDFBIN` format, the editor must be updated to fully support editing these multi-dimensional maps.

## Scope

- Parse the P2P table (`h_29494504`) and all 7 known variants of the Boost table (`h_515f5e83`).
- Display the data in the existing TreeView interface.
- Provide a dedicated, industry-standard interactive graphical editor for multi-dimensional engine maps (3D surface viewing + 2D multi-line drag editing).
- Save modified tables back into the EDF binary safely.

## Requirements

### P2P Support
1. Identify `h_29494504` blocks and read all 441 sequential entries.
2. Support both `04 08` (14-byte) and `04 00` (11-byte) suffixes.
3. The interactive editor must allow filtering by `Mode/Gear [N]` (e.g. Mode 0 or 2) and plotting the RPM vs Throttle surface.

### Boost Support
1. Extend existing boost parser to identify 7 new variants using compound suffixes (e.g., `96 AA`, `86 AA`, `16 AA`, `06 AA`, etc.).
2. Gracefully handle variants that omit the 100% throttle float or pad with bytes.
3. The interactive editor must visualize the 5 throttle states (0%, 25%, 50%, 75%, 100%) against RPM.

### Visualization & Interaction
1. **3D Visualizer**: A read-only `mplot3d` rotatable surface showing the full map shape.
2. **2D Editor**: Draggable points on 2D slices (e.g., lines for each throttle position) to adjust the Z-axis (Multiplier/Target) values interactively.
3. Quantize all drag edits to float32 to match the game engine's precision, identically to existing Torque editor logic.
