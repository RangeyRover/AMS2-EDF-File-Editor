"""Launch the AMS2 EDF File Editor."""
import sys
import os
import ctypes

# Windows High DPI awareness (FR11) — must be called before any Tkinter init
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.gui.app import EDFEditorApp

if __name__ == "__main__":
    app = EDFEditorApp()
    app.mainloop()
