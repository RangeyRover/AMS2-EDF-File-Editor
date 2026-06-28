# AMS2 EDF File Editor v0.5.5 (Hotfix)

## What's New
- **Extended File Support**: The file open and save dialogs now explicitly accept and filter for both `*.edf` and `*.edfbin` extensions, resolving workflow friction for natively extracted Madness engine `.edfbin` files.
- **Silent Parser Terminations**: Removed a leftover developer `print()` debug trace that was triggering when torque tables ended organically without an `ENDVAR` signature. The console will now remain silent during these perfectly normal transitions.
- **PyInstaller Bundling**: Implemented a root `run.py` entrypoint to ensure the `src` package is completely resolved inside compiled Windows Sandbox executables.
