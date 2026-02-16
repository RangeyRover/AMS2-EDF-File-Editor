import sys
import os
import logging
import ctypes

# Windows High DPI awareness (FR11) — must be called before any Tkinter init
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# Ensure the project root (parent of src/) is on sys.path
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.gui.app import EDFEditorApp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def main():
    app = EDFEditorApp()
    app.mainloop()

if __name__ == "__main__":
    main()
