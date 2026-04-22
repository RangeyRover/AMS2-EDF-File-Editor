# AMS2 EDF File Editor v0.5.4 (Hotfix)

## What's New
This hotfix canonises the "Unknown" parameter discoveries from `v0.5.3` by directly updating the Editor's parser logic and XML definitions. 

When you parse an engine file, the GUI will now natively display the explicit parameters instead of cryptic unknowns!

### Upgraded UI Parameter Definitions:
- **`RadiatorMaxTemp`** (formerly `Unknown_Chunk_206D47` / `115` max water temp threshold)
- **`Peak_BHP_Target_Override`** (formerly `Unknown_Float_295` / Explicit horsepower scaling factor)
- **`Engine_Pumping_Loss_Friction`** (formerly `Unknown_Float_6e-06` / Micro-float friction curve)
- **`Restrictor_Plate_Bypass_Count`** (formerly `Unknown_Byte_2B3ED340` / Values `1`, `2`, `4`)
- **`Engine_Rebuild_Milestones`** (formerly `Unknown_LMP_RWD_P30_A` / Distance targets e.g. `60,000`)
- **`Ignition_Starter_Map`** (formerly `Unknown_LMP_RWD_P30_B` / Ignition cuts/torques)
- **`Reserved_Boolean_Flag`** (formerly `EDF_UNKN_005` / Re-added to the XML payload to prevent silent parsing drops)

### Under the Hood
- Both `constants.py` and `edf-hex-map.xml` have been meticulously synchronised. 
- The translation documentation has been bumped to `v1.5` and `.gitignored` to prevent bloating the source tracking.

### Assets
- `AMS2-EDF-Editor-v0.5.4.exe` (Single Portable Executable)
- `AMS2-EDF-Editor-v0.5.4-portable.zip` (Portable Directory version for faster startup)
