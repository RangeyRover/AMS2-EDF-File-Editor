# AMS2 EDF File Editor v4 (Refactored)

Modular Python package for editing Automobilista 2 `.edf` engine definition files.

## Features
-   **Core Logic**: Robust parsing and writing of Torque/Boost tables and Parameters.
-   **GUI**: Modern Tkinter interface with TreeView and Hex highlighting.
-   **Plotting**: Tools to visualize Torque/Power and Compression curves.
-   **TDD**: Core logic is covered by comprehensive unit tests.

## Installation
Ensure you have Python 3.8+ installed.

1.  Clone/Download this repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage
Run the application from the root directory:
```bash
python src/main.py
# OR
python -m src.main
```

## Running Tests
Run the test suite using `pytest`:
```bash
pytest tests/
```

## Structure
-   `src/core`: Parsing, Writing, Data Models.
-   `src/gui`: Application, Dialogs, Components.
-   `src/utils`: Plotting logic.
-   `tests/`: Unit tests.

## Acknowledgements
Original script by [Author Name/Source]. Refactored for maintainability and extensibility.
