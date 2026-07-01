import subprocess
import os
import pytest

# This test can be slow, so we mark it specifically
@pytest.mark.slow
def test_pyinstaller_build_and_run():
    """Verify that PyInstaller correctly bundles the app and its imports resolve."""
    # Ensure we run from the project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    build_cmd = [
        "pyinstaller",
        "--onedir",
        "--noconfirm",
        "--name", "AMS2-EDF-Editor-Test",
        "run.py"
    ]
    
    # Run the build
    res = subprocess.run(build_cmd, cwd=project_root, capture_output=True, text=True)
    assert res.returncode == 0, f"PyInstaller build failed:\n{res.stderr}\n{res.stdout}"
    
    # Check if exe exists
    exe_path = os.path.join(project_root, "dist", "AMS2-EDF-Editor-Test", "AMS2-EDF-Editor-Test.exe")
    assert os.path.exists(exe_path), f"Executable not found at {exe_path}"
    
    # Run the exe with --dry-run
    res_run = subprocess.run([exe_path, "--dry-run"], cwd=project_root, capture_output=True, text=True)
    
    # The --dry-run flag should cause main.py to immediately exit 0 with a success log
    error_msg = f"App crashed on startup!\nSTDOUT:\n{res_run.stdout}\nSTDERR:\n{res_run.stderr}"
    assert res_run.returncode == 0, error_msg
    assert "Dry run successful" in res_run.stderr or "Dry run successful" in res_run.stdout, "Dry run log missing"
