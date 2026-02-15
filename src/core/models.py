from dataclasses import dataclass
from typing import Tuple, Optional, List, Union

@dataclass
class TorqueRow:
    rpm: float
    compression: float
    torque: Optional[float]
    offset: int
    kind: str  # '0rpm', 'row_i', 'row_f', 'endvar'

@dataclass
class TorqueTable:
    offset: int
    rows: List[TorqueRow]

@dataclass
class BoostRow:
    rpm: float
    t0: float
    t25: float
    t50: float
    t75: float
    t100: float
    offset: int
    kind: str # 'boost_0rpm', 'boost_row'

@dataclass
class BoostTable:
    offset: int
    rows: List[BoostRow]

@dataclass
class Parameter:
    name: str
    offset: int
    values: Tuple[Union[float, int], ...]
    fmt: Optional[Tuple[str, ...]] = None
