# Quickstart: f309-power-units Implementer Guide

## Getting Started

1. **Understand Parse/Write Boundary**
   Locate `src/core/parser.py` and `src/core/writer.py`. You will need to introduce `SIG_0RPM_ALT = b'\x24\x8B\x0A\xB7\x71\x03\x02'` into `constants.py` and conditionally branch parsing/packing structures.
   
2. **Handle the Option Toggle**
   Locate `DraggableTorquePlot` inside `src/utils/interactive_plot.py`. Introduce `display_units='HP'` parameter.
   Use the `matplotlib` GUI widget logic or a custom button event handler (e.g. `RadioButtons` widget from `matplotlib.widgets`) to live-toggle the axes.

3. **Check the Tests**
   Write a mock byte stream mimicking `f309.edfbin`'s 0RPM row into `conftest.py` synthetic data generators, and ensure the test suite captures successful plotting and saving.
