"""FR14: JSON-ledger round-trip integration test.

1. Load original EDF
2. Parse all entities, record {old_value, new_value} in a ledger
3. Write mutated values → save modified.edf
4. Reopen modified.edf → re-parse
5. Reinstate old_values from ledger → save reinstated.edf
6. Assert reinstated.edf == original (byte-perfect)

Mutation: floats * 1.01, ints + 1, bytes unchanged.
"""
import json
import os
import struct
import tempfile
import pytest
from typing import List, Dict, Any

from src.core.parser import parse_torque_tables, parse_boost_tables, parse_params
from src.core.writer import write_torque_row, write_boost_row, write_param
from src.core.models import TorqueRow, TorqueTable, BoostRow, BoostTable, Parameter

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_EDF_FILE = os.path.join(_PROJECT_ROOT, "012d6b90.edf")

pytestmark = pytest.mark.skipif(
    not os.path.isfile(_EDF_FILE),
    reason=f"EDF fixture not found: {_EDF_FILE}"
)

# ---------------------------------------------------------------------------
# Ledger helpers
# ---------------------------------------------------------------------------

def _record_torque(tables: List[TorqueTable]) -> List[Dict[str, Any]]:
    """Record all torque values and compute mutations. Returns ledger entries."""
    ledger = []
    for ti, table in enumerate(tables):
        for ri, row in enumerate(table.rows):
            entry = {
                "entity": "torque", "table": ti, "row": ri,
                "kind": row.kind, "offset": row.offset,
                "old_rpm": row.rpm, "old_comp": row.compression, "old_tq": row.torque,
            }
            # Compute new values
            if row.kind == '0rpm':
                entry["new_rpm"] = row.rpm  # always 0, don't touch
            elif row.kind in ('row_i', 'endvar'):
                entry["new_rpm"] = float(int(row.rpm) + 1)
            else:  # row_f
                entry["new_rpm"] = row.rpm * 1.01

            entry["new_comp"] = row.compression * 1.01
            entry["new_tq"] = row.torque * 1.01 if row.torque is not None else None
            ledger.append(entry)
    return ledger


def _record_boost(boost_tables: List[BoostTable]) -> List[Dict[str, Any]]:
    """Record all boost values and compute mutations."""
    ledger = []
    for bi, table in enumerate(boost_tables):
        for ri, row in enumerate(table.rows):
            entry = {
                "entity": "boost", "table": bi, "row": ri,
                "kind": row.kind, "offset": row.offset,
                "old_rpm": row.rpm,
                "old_t0": row.t0, "old_t25": row.t25, "old_t50": row.t50,
                "old_t75": row.t75, "old_t100": row.t100,
            }
            if row.kind == 'boost_0rpm':
                entry["new_rpm"] = row.rpm  # always 0
            else:
                entry["new_rpm"] = float(int(row.rpm) + 1)

            entry["new_t0"]  = row.t0  * 1.01
            entry["new_t25"] = row.t25 * 1.01
            entry["new_t50"] = row.t50 * 1.01
            entry["new_t75"] = row.t75 * 1.01
            entry["new_t100"]= row.t100* 1.01
            ledger.append(entry)
    return ledger


def _record_params(params: List[Parameter]) -> List[Dict[str, Any]]:
    """Record all parameter values and compute mutations."""
    ledger = []
    for pi, p in enumerate(params):
        if not p.values:
            continue
        old_vals = list(p.values)
        new_vals = []
        for i, v in enumerate(old_vals):
            fmt_char = p.fmt[i] if p.fmt and i < len(p.fmt) else None
            if fmt_char == 'f':
                new_vals.append(v * 1.01)
            elif fmt_char == 'i':
                new_vals.append(v + 1)
            else:  # 'b' or unknown — don't touch
                new_vals.append(v)
        ledger.append({
            "entity": "param", "index": pi,
            "name": p.name, "offset": p.offset,
            "old_values": old_vals, "new_values": new_vals,
            "fmt": list(p.fmt) if p.fmt else [],
        })
    return ledger


# ---------------------------------------------------------------------------
# Apply helpers
# ---------------------------------------------------------------------------

def _apply_torque(data: bytearray, tables: List[TorqueTable],
                  ledger: List[Dict], use_new: bool) -> None:
    """Apply new or old values from ledger to torque tables and write."""
    rpm_key   = "new_rpm"  if use_new else "old_rpm"
    comp_key  = "new_comp" if use_new else "old_comp"
    tq_key    = "new_tq"   if use_new else "old_tq"
    for entry in ledger:
        if entry["entity"] != "torque":
            continue
        row = tables[entry["table"]].rows[entry["row"]]
        row.rpm = entry[rpm_key]
        row.compression = entry[comp_key]
        row.torque = entry[tq_key]
        write_torque_row(data, row)


def _apply_boost(data: bytearray, boost_tables: List[BoostTable],
                 ledger: List[Dict], use_new: bool) -> None:
    """Apply new or old values from ledger to boost tables and write."""
    rpm_key = "new_rpm" if use_new else "old_rpm"
    for entry in ledger:
        if entry["entity"] != "boost":
            continue
        row = boost_tables[entry["table"]].rows[entry["row"]]
        row.rpm  = entry[rpm_key]
        row.t0   = entry["new_t0"   if use_new else "old_t0"]
        row.t25  = entry["new_t25"  if use_new else "old_t25"]
        row.t50  = entry["new_t50"  if use_new else "old_t50"]
        row.t75  = entry["new_t75"  if use_new else "old_t75"]
        row.t100 = entry["new_t100" if use_new else "old_t100"]
        write_boost_row(data, row)


def _apply_params(data: bytearray, params: List[Parameter],
                  ledger: List[Dict], use_new: bool) -> None:
    """Apply new or old values from ledger to params and write."""
    vals_key = "new_values" if use_new else "old_values"
    for entry in ledger:
        if entry["entity"] != "param":
            continue
        p = params[entry["index"]]
        p.values = tuple(entry[vals_key])
        write_param(data, p)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRoundTrip:
    """Byte-perfect round-trip using JSON ledger for deterministic reinstatement."""

    def _run_roundtrip(self, parse_fn, record_fn, apply_fn, entity_name):
        """Generic round-trip runner for a single entity type."""
        with open(_EDF_FILE, 'rb') as f:
            original = f.read()

        # --- Pass 1: mutate and save ---
        data1 = bytearray(original)
        entities1 = parse_fn(data1)
        if not entities1:
            pytest.skip(f"No {entity_name} found in EDF file")

        ledger = record_fn(entities1)
        apply_fn(data1, entities1, ledger, use_new=True)

        with tempfile.NamedTemporaryFile(suffix='.edf', delete=False) as tmp:
            tmp.write(data1)
            modified_path = tmp.name

        try:
            # --- Pass 2: reopen, reinstate, and save ---
            with open(modified_path, 'rb') as f:
                data2 = bytearray(f.read())

            entities2 = parse_fn(data2)
            assert len(entities2) == len(entities1), (
                f"Re-parse found {len(entities2)} {entity_name} (expected {len(entities1)}). "
                f"Mutation may have broken plausibility checks."
            )

            apply_fn(data2, entities2, ledger, use_new=False)

            # --- Compare ---
            if data2 != bytearray(original):
                # Dump ledger for investigation
                ledger_path = os.path.join(_PROJECT_ROOT, f"test_roundtrip_{entity_name}_ledger.json")
                with open(ledger_path, 'w') as lf:
                    json.dump(ledger, lf, indent=2, default=str)

                for i in range(len(original)):
                    if data2[i] != original[i]:
                        pytest.fail(
                            f"{entity_name} round-trip failed at 0x{i:X}. "
                            f"Expected 0x{original[i]:02X}, got 0x{data2[i]:02X}. "
                            f"Ledger saved to {ledger_path}"
                        )
        finally:
            os.unlink(modified_path)

    def test_torque_round_trip(self):
        self._run_roundtrip(
            parse_torque_tables, _record_torque, _apply_torque, "torque"
        )

    def test_boost_round_trip(self):
        self._run_roundtrip(
            parse_boost_tables, _record_boost, _apply_boost, "boost"
        )

    def test_params_round_trip(self):
        self._run_roundtrip(
            parse_params, _record_params, _apply_params, "param"
        )

    def test_full_round_trip(self):
        """ALL entities round-trip together."""
        with open(_EDF_FILE, 'rb') as f:
            original = f.read()

        # --- Pass 1: mutate all and save ---
        data1 = bytearray(original)
        tables = parse_torque_tables(data1)
        boost  = parse_boost_tables(data1)
        params = parse_params(data1)

        tq_ledger = _record_torque(tables)
        bo_ledger = _record_boost(boost)
        pm_ledger = _record_params(params)

        _apply_torque(data1, tables, tq_ledger, use_new=True)
        _apply_boost(data1, boost, bo_ledger, use_new=True)
        _apply_params(data1, params, pm_ledger, use_new=True)

        with tempfile.NamedTemporaryFile(suffix='.edf', delete=False) as tmp:
            tmp.write(data1)
            modified_path = tmp.name

        try:
            # --- Pass 2: reopen, reinstate all, save ---
            with open(modified_path, 'rb') as f:
                data2 = bytearray(f.read())

            tables2 = parse_torque_tables(data2)
            boost2  = parse_boost_tables(data2)
            params2 = parse_params(data2)

            _apply_torque(data2, tables2, tq_ledger, use_new=False)
            _apply_boost(data2, boost2, bo_ledger, use_new=False)
            _apply_params(data2, params2, pm_ledger, use_new=False)

            if data2 != bytearray(original):
                # Dump all ledgers
                all_ledger = tq_ledger + bo_ledger + pm_ledger
                ledger_path = os.path.join(_PROJECT_ROOT, "test_roundtrip_full_ledger.json")
                with open(ledger_path, 'w') as lf:
                    json.dump(all_ledger, lf, indent=2, default=str)

                for i in range(len(original)):
                    if data2[i] != original[i]:
                        pytest.fail(
                            f"Full round-trip failed at 0x{i:X}. "
                            f"Expected 0x{original[i]:02X}, got 0x{data2[i]:02X}. "
                            f"Ledger saved to {ledger_path}"
                        )
        finally:
            os.unlink(modified_path)
