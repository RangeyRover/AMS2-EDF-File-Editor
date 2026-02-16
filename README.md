# EDF File Editor

Minimal desktop viewer/editor for **Madness-engine** `EDF/EDFBIN` engine files. Quickly inspect, plot, and lightly edit torque curves and common engine parameters using JDougNY's *Project CARS Engine translation* mapping (v1.01).

> **Why**: Open an EDF, see what's inside, export a curve to CSV, tweak values (or scale the whole torque table), and save a copy — no hex editor required.

---

## Features

- **Open** `*.edf` files
- **Parse & display**
  - **Torque tables** (RPM, compression, torque) with plausibility checks
  - **Turbo boost tables** (RPM vs throttle 0/25/50/75/100%)
  - **51 common parameters** with human-readable labels, types, and units
  - **Engine layout** hint (best‑effort from 9 known code sequences)
  - **Hex view** with highlighting for selected items
- **Plotting** (optional, via `matplotlib`)
  - Torque & Power **vs RPM** (dual-axis)
  - Compression **vs RPM**
- **Editing**
  - Double‑click parameters to edit — dialogs show **field labels and types** (e.g., `Inertia (kg·m²) [float]:`)
  - Double-click torque rows to edit RPM, compression, torque
  - **Scale torque** globally by a percentage
- **Export/Save**
  - Export torque tables to **CSV**
  - **Save** (overwrite) or **Save As** to a new file (Ctrl+S)
  - **Close** file to reset UI
- **Verified lossless** — round-trip tested: mutate → save → reopen → reinstate → byte-identical ✅

![EDF Main Window](https://raw.githubusercontent.com/RangeyRover/AMS2-EDF-File-Editor/refs/heads/main/EDF-Main%20Window.png)
![EDF PlotWindow](https://raw.githubusercontent.com/RangeyRover/AMS2-EDF-File-Editor/refs/heads/main/EDF-Plots.png)

---

## Requirements

- **Python 3.9+**
- Standard library: `tkinter`, `struct`, `csv`, `pathlib`
- **Optional for plots**: `pip install matplotlib`

---

## Quick Start

### Monolithic (single file — easiest)
```bash
python ams2_edf_editor.py
```

### Modular (package structure)
```bash
python run.py
```

### Running Tests
```bash
pip install pytest
pytest tests/ -v
```

1. **File → Open EDF…**
2. Explore torque/boost tables and parameters in the tree
3. (Optional) **Tools → Plot Torque/Power** (requires `matplotlib`)
4. **Edit** a value: double‑click → change → **Save**
5. **Tools → Scale Torque Tables…** to apply a global percentage
6. **Tools → Export CSV…**
7. **File → Save** or **File → Save As…**

> Changes are applied to an **in‑memory** copy until you save.

---

## What the parser understands

### Torque tables
- Detects **0‑RPM** rows and subsequent rows (`int32/float/float` or `float/float/float`)
- Handles `endvar` terminal rows
- Plausibility checks: RPM `0–25,000`, Torque `−4,000–10,000 Nm`
- Shows **hex offsets** for traceability

### Boost tables
- Throttle columns: **0/25/50/75/100%** per RPM
- Typical values: **0.5–3.0 bar**

### Parameters (51 signatures)
- Known signatures → names with **labels and type annotations**
- Groups: fuel, idle/launch RPM, rev limit, engine maps, cooling, oil/water, lifetime stats, emissions, starter, air restrictor, boost/wastegate
- Each field shows its **label**, **type** (float/int/byte), and **unit** where known

### Engine layout detection
- 9 known patterns: Single Cylinder, Flat 4/6, Straight 4/5/6, V8/V10/V12

---

## Menus

### File
| Item | Shortcut | Description |
|------|----------|-------------|
| Open EDF… | | Load an EDF file |
| Save | Ctrl+S | Overwrite current file |
| Save As… | | Save to a new path |
| Close | | Close file, reset UI |
| Exit | | Quit |

### Tools
| Item | Description |
|------|-------------|
| Plot Torque/Power | Dual-axis torque + power vs RPM |
| Plot Compression | Compression vs RPM |
| Scale Torque Tables… | Global percentage scaling |
| Export CSV… | Torque tables to CSV |

### Tree interactions
- Double‑click **torque rows** or **parameters** to edit
- Single‑click highlights the item's bytes in the hex view

---

## CSV Export

Columns: `table_index`, `row_index`, `rpm`, `compression`, `torque`, `row_kind`, `payload_offset_hex`, `source_file`

---

## Project Structure

```
├── ams2_edf_editor.py     # Monolithic single-file (846 lines)
├── run.py                 # Launcher for modular version
├── edf-hex-map.xml        # Binary format reference
├── spec.md                # Functional requirements
├── src/
│   ├── core/
│   │   ├── constants.py   # Signatures, PARAMS, PARAM_META
│   │   ├── models.py      # TorqueRow, BoostRow, Parameter
│   │   ├── parser.py      # Torque, boost, param parsers
│   │   └── writer.py      # Binary write-back
│   ├── gui/
│   │   ├── app.py         # Main application window
│   │   ├── dialogs.py     # Edit dialogs with labels
│   │   ├── hex_view.py    # Hex viewer with highlighting
│   │   └── tree_view.py   # TreeView with type annotations
│   └── utils/
│       ├── formatting.py  # Float display (never scientific)
│       └── plotting.py    # Matplotlib charts
└── tests/                 # 30 unit tests (pytest)
```

---

## Troubleshooting

- **No plots** → `pip install matplotlib`
- **"No torque tables parsed"** → file variant may differ; inspect hex view
- **Edits didn't save** → use **File → Save** or **Save As…**

---

## Roadmap Ideas

- Per‑table/selection scaling
- Side‑by‑side file comparison & delta plots
- Editable **boost** tables
- Signature discovery helpers
- Dark mode/UI theming

---

## Acknowledgements
- **JDougNY** — *Project CARS Engine translation* mapping (v1.01)
