# Contracts & Interfaces

## Internal Interface: Plotting Parameters

### `DraggableTorquePlot.__init__` update
```python
def __init__(self, data_list, engine_layout_str, mode="torque", power_unit="HP"):
    """
    power_unit (str): Default unit to render secondary power axis. Valid options: ["kW", "HP"]
    """
```

## Internal Interface: Serialization Constants
```python
# Updated Signature Maps
SIG_0RPM_ALT = b'\x24\x8B\x0A\xB7\x71\x03\x02'

# Structure Unpacker Length
# Uses '<BBf' for new alignment: Byte, Byte, Float(compression)
ROW0_ALT_STRUCT = struct.Struct('<BBf')
```
