import pathlib
import re

def build():
    src_dir = pathlib.Path("src")
    
    # Files in dependency order
    files = [
        src_dir / "core" / "constants.py",
        src_dir / "core" / "models.py",
        src_dir / "core" / "parser.py",
        src_dir / "core" / "writer.py",
        src_dir / "utils" / "formatting.py",
        src_dir / "utils" / "plotting.py",
        src_dir / "utils" / "interactive_plot.py",
        src_dir / "gui" / "hex_view.py",
        src_dir / "gui" / "dialogs.py",
        src_dir / "gui" / "tree_view.py",
        src_dir / "gui" / "app.py",
    ]
    
    out = []
    
    # 1. Header
    out.append('"""')
    out.append('AMS2 EDF File Editor v0.5-testbuild — Monolithic Distribution Build')
    out.append('==========================================================')
    out.append('Single-file version for easy command-line use.')
    out.append('Auto-generated from modular src/ tree.')
    out.append('"""')
    
    # 2. Imports from stdlib and 3rd party
    out.append("import struct\nimport ctypes\nimport sys\nimport os\nimport logging\nimport csv")
    out.append("import tkinter as tk\nfrom tkinter import ttk, filedialog, messagebox, simpledialog")
    out.append("from dataclasses import dataclass\nfrom typing import Tuple, Optional, List, Union, Generator, Callable, Dict")
    out.append("from pathlib import Path")
    
    # Matplotlib imports used in interactive_plot.py
    out.append("try:")
    out.append("    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk")
    out.append("    from matplotlib.figure import Figure")
    out.append("    from matplotlib.lines import Line2D")
    out.append("except ImportError:")
    out.append("    pass")
    
    out.append("\n# Windows High DPI awareness (FR11) — must be called before any Tkinter init\ntry:\n    ctypes.windll.shcore.SetProcessDpiAwareness(1)\nexcept Exception:\n    pass\n")
    out.append("logger = logging.getLogger(__name__)\n\n")
    
    seen_imports = set()
    
    for f in files:
        if not f.exists():
            continue
        out.append(f"\n# {'='*70}\n# {f.name}\n# {'='*70}\n")
        content = f.read_text(encoding="utf-8")
        
        # Remove imports
        lines = content.split('\n')
        new_lines = []
        in_import = False
        for line in lines:
            if line.startswith("import ") or line.startswith("from "):
                if '(' in line and ')' not in line:
                    in_import = True
                continue
            if in_import:
                if ')' in line:
                    in_import = False
                continue
            if '__name__' in line and 'logging.getLogger' in line:
                continue
            new_lines.append(line)
        
        out.append('\n'.join(new_lines))
        
    out.append("\nif __name__ == '__main__':\n    app = EDFEditorApp()\n    app.mainloop()\n")
    
    pathlib.Path("ams2_edf_editor.py").write_text('\n'.join(out), encoding='utf-8')

if __name__ == "__main__":
    build()
