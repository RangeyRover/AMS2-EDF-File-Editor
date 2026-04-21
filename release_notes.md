# AMS2 EDF File Editor v0.5.3

## What's New
This release focuses on reverse-engineering the hidden Madness Engine physics constants by statistically mapping parameter placement and values across all 476 extracted AMS2 vehicles. 

### Newly Discovered Parameter Hypotheses
* **`Unknown_Chunk_206D47`** has been reclassified as **`RadiatorMaxTemp`**. Analysis shows it sits strictly at `115°C` for GTs, `110°C` for Formula cars, and `70°C` for Karts.
* **`Unknown_Float_295`** aligns perfectly with maximum BHP limits (e.g. `455.0` for Super Speedway stock cars, `655.0` for Garage 56 LM variants). It is speculated to act as an overriding **Hardcoded Horsepower/Restrictor Target**.
* **`Unknown_Float_6e-06`** (magnitude ~`8.85e-06`) is mapped directly next to `EngineDisplacement` and acts as a dynamic **Engine Pumping Loss (Friction)** or Injector scale.
* **`Unknown_EngineFreeRevs`** is placed securely between `EngineInertia` and `IdleRPMLogic`, functioning as a tiny frictional coefficient (~`0.01`) for **Coasting Friction / Throttle Damping**.
* **`Unknown_LMP_RWD_P30_A`** features massive `(150000.0, 70000.0)` variants directly adjacent to `LifetimeEngineRPM`, likely representing **Engine Mileage/Rebuild Milestones**.

*(These remain annotated as "Speculation" in the XML/constants, but have massive statistical backing).*

### Bug Fixes & Refinements
* Removed the PCars2-era `EDF_UKNN_010` (`2300005`) as it no longer exists in any AMS2 engine file.
* Git builds now globally `.gitignore` all `*.spec` compilation files to maintain a clean workspace.

### Assets
- `AMS2-EDF-Editor-v0.5.3.exe` (Single Portable Executable)
- `AMS2-EDF-Editor-v0.5.3-portable.zip` (Portable Directory version for faster startup)
