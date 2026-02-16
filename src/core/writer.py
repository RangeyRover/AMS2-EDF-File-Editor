import struct
from typing import List, Tuple, cast

from .models import TorqueRow, TorqueTable, BoostRow, BoostTable, Parameter
from .constants import (
    SIG_0RPM, SIG_ROW_I, SIG_ROW_F, SIG_ENDVAR,
    SIG_BOOST_0RPM, SIG_BOOST_ROW,
    ROW0_STRUCT, ROWI_STRUCT, ROWF_STRUCT, ENDVAR_STRUCT,
    BOOST0_STRUCT, BOOSTI_STRUCT,
    PARAMS
)

def write_torque_row(data: bytearray, row: TorqueRow) -> None:
    """
    Writes all torque row values back to the binary data.
    Handles 0rpm, row_i, row_f, and endvar kinds.
    """
    if row.kind == '0rpm':
        if row.torque is None:
            return
        data_offset = row.offset + len(SIG_0RPM)
        # Preserve the leading byte
        b0 = data[data_offset]
        struct.pack_into('<Bff', data, data_offset, b0, row.compression, row.torque)

    elif row.kind == 'row_i':
        if row.torque is None:
            return
        data_offset = row.offset + len(SIG_ROW_I)
        struct.pack_into('<iff', data, data_offset, int(row.rpm), row.compression, row.torque)

    elif row.kind == 'row_f':
        if row.torque is None:
            return
        data_offset = row.offset + len(SIG_ROW_F)
        struct.pack_into('<fff', data, data_offset, row.rpm, row.compression, row.torque)

    elif row.kind == 'endvar':
        data_offset = row.offset + len(SIG_ENDVAR)
        # ENDVAR_STRUCT is <ifB: (int rpm, float compression, byte)
        # Preserve the trailing byte
        trailing_byte = data[data_offset + ENDVAR_STRUCT.size - 1]
        struct.pack_into('<ifB', data, data_offset, int(row.rpm), row.compression, trailing_byte)


def write_boost_row(data: bytearray, row: BoostRow) -> None:
    """
    Writes boost row values back to the binary data.
    Handles boost_0rpm and boost_row kinds.
    """
    if row.kind == 'boost_0rpm':
        data_offset = row.offset + len(SIG_BOOST_0RPM)
        # BOOST0_STRUCT is <Bfffff: (byte, 5 floats)
        # Preserve the leading byte
        b0 = data[data_offset]
        struct.pack_into('<Bfffff', data, data_offset, b0, row.t0, row.t25, row.t50, row.t75, row.t100)

    elif row.kind == 'boost_row':
        data_offset = row.offset + len(SIG_BOOST_ROW)
        # BOOSTI_STRUCT is <ifffff: (int rpm, 5 floats)
        struct.pack_into('<ifffff', data, data_offset, int(row.rpm), row.t0, row.t25, row.t50, row.t75, row.t100)


def write_param(data: bytearray, param: Parameter) -> None:
    """
    Writes the parameter values back to the binary data.
    """
    sig_len = 0
    fmt: Tuple[str, ...] = tuple()

    if param.fmt:
        fmt = param.fmt
        for sig, (pname, pfmt) in PARAMS.items():
            if pname == param.name:
                sig_len = len(sig)
                break
    else:
        for sig, (pname, pfmt) in PARAMS.items():
            if pname == param.name:
                sig_len = len(sig)
                fmt = pfmt
                break

    if not fmt:
        return

    data_offset = param.offset + sig_len

    cur = data_offset
    for i, f in enumerate(fmt):
        val = param.values[i]
        if f == 'f':
            struct.pack_into('<f', data, cur, float(val))
            cur += 4
        elif f == 'i':
            struct.pack_into('<i', data, cur, int(val))
            cur += 4
        elif f == 'b':
            struct.pack_into('B', data, cur, int(val))
            cur += 1


def scale_torque_tables(data: bytearray, tables: List[TorqueTable], factor: float) -> None:
    """
    Scales all torque values in the provided tables by a factor.
    Updates both the binary data AND the table objects in-place.
    """
    for table in tables:
        for row in table.rows:
            if row.torque is not None:
                row.torque *= factor
                write_torque_row(data, row)
