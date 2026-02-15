# Specification: AMS2-EDF-File-Editor v4 Refactor

## 1. Executive Summary
The goal of this project is to refactor the existing monolithic `EDF-File-Editor.py` script into a modular, maintainable Python package. The current single-file implementation has improved significantly but has become difficult to maintain and test. The v4 refactor will separate concerns into core logic, GUI, and utilities, enabling easier feature additions and robust testing.

## 2. Problem Statement
The current codebase consists of a single 1700+ line Python script (`EDF-File-Editor.py`) that handles file I/O, binary parsing, UI rendering (Tkinter), event handling, and plotting (Matplotlib). This tight coupling makes it:
-   Difficult to unit test core logic (parsing/writing) without initializing the GUI.
-   Hard to navigate and maintain.
-   Challenging to extend with new features (e.g., new file formats, different UIs).

## 3. Goals
-   **Modularize**: Split the code into logical modules (Core, GUI, Utils).
-   **Testability**: Implement unit tests for the core parsing and writing logic.
-   **Type Safety**: Add type hints to all functions and classes.
-   **Maintainability**: Improve code readability and documentation.
-   **Preserve Functionality**: Ensure all existing features (View, Edit, Plot, Save) work exactly as before.

## 4. Scope

### 4.1. Core Logic (`src/core`)
-   **Test Driven**: This is the primary testable environment. Every function developed here must be testable and covered by unit tests.
-   **Parsing**: Extract all binary parsing logic (`parse_torque_tables`, `parse_boost_tables`, `parse_params`).
-   **Data Models**: Replace raw tuples with dataclasses (`TorqueTable`, `BoostTable`, `Parameter`).
-   **Constants**: Centralize signatures and constants.
-   **Writing**: Implement logic to write changes back to binary data.

### 4.2. GUI (`src/gui`)
-   **Thin Layer**: The GUI will strictly be a presentation layer. No business logic is allowed here.
-   **Untested**: We acknowledge that Tkinter is hard to test. Therefore, this layer is explicitly excluded from automated testing.
-   **Main Window**: Refactor `EDFViewer` to handle only UI layout and event dispatching.
-   **Components**: Separate `TreeView` and `HexViewer` logic if possible.
-   **Interaction**: UI events must delegate immediately to Core logic.

### 4.3. Utilities (`src/utils`)
-   **Plotting**: Move Matplotlib integration to a separate module. Ensure plotting data preparation is testable even if the rendering itself isn't.
-   **Helpers**: logical helpers for file handling, etc.

## 5. Requirements

### 5.1. Functional Requirements
-   **FR1**: Must be able to open `.edf` and `.bin` files.
-   **FR2**: Must display Torque tables, Boost tables, and Parameters in a TreeView.
-   **FR3**: Must allow editing of Torque values and Parameters.
-   **FR4**: Must validate inputs (RPM, Torque, Compression) against plausible ranges.
-   **FR5**: Must allow saving modified data to a new file.
-   **FR6**: Must support Hex View with highlighting of selected elements.
-   **FR7**: Must support plotting of Torque/Power vs RPM and Compression.
-   **FR8**: Must detect engine layout based on known signatures.

### 5.2. Non-Functional Requirements
-   **NFR1**: All Core logic must be developed using Test-Driven Development (TDD).
-   **NFR2**: Core logic must be 100% independent of `tkinter`.
-   **NFR3**: Unit tests must cover 100% of the core parsing and writing logic.
-   **NFR4**: Code must be type-hinted (Python 3.9+).

## 6. Architecture & Design
The project will follow a layered architecture:
-   **Presentation Layer**: `src/gui` (Tkinter)
-   **Application Layer**: `src/main.py` (Orchestration)
-   **Domain Layer**: `src/core` (Parsing, Models, Logic)

## 7. Migration Strategy
1.  Set up new directory structure.
2.  Port constants and data models.
3.  Port parsing logic and write tests.
4.  Port GUI and hook up to new core logic.
5.  Port plotting logic.
6.  Verify against original script.
