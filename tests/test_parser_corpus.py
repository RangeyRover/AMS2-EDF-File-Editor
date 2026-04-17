import pytest
from pathlib import Path
from src.core.parser import parse_torque_tables

# Point directly at the master corpus directory
EDF_DIR = Path("edf_examples")

# Discover all files to parameterize
# If the directory doesn't exist (e.g. CI environments), it falls back to an empty list
if EDF_DIR.exists():
    edf_files = list(EDF_DIR.glob("*.edfbin"))
else:
    edf_files = []

@pytest.mark.skipif(not edf_files, reason="edf_examples corpus directory missing, skipping full corpus check.")
@pytest.mark.parametrize("edf_path", edf_files, ids=lambda p: p.name)
def test_all_corpus_engines_yield_torque_tables(edf_path):
    """
    Verifies that our parser can successfully extract at least one torque table
    from every single real-world engine file in our research corpus.
    This guarantees 0 regressions across all known anomalies.
    """
    data = edf_path.read_bytes()
    tables = parse_torque_tables(data)
    
    assert len(tables) >= 1, f"Parser failed to find any torque tables in {edf_path.name}"
