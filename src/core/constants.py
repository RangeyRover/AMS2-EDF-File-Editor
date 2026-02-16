import struct

# -------- Signatures (little-endian) --------
SIG_0RPM   = b'\x24\x8B\x0A\xB7\x71\x83\x02'  # byte, float, float
SIG_ROW_I  = b'\x24\x8B\x0A\xB7\x71\x93\x02'  # int32, float, float
SIG_ROW_F  = b'\x24\x8B\x0A\xB7\x71\xA3\x02'  # float, float, float
SIG_ENDVAR = b'\x24\x8B\x0A\xB7\x71\x93\x00'  # int32, float, byte (rare)

# Boost table signatures
SIG_BOOST_0RPM = b'\x24\x51\x5F\x5E\x83\x86\xAA'  # byte, 5 floats (throttle positions)
SIG_BOOST_ROW  = b'\x24\x51\x5F\x5E\x83\x96\xAA'  # int32, 5 floats (throttle positions)

# Torque table structures
ROW0_STRUCT   = struct.Struct('<Bff')
ROWI_STRUCT   = struct.Struct('<iff')
ROWF_STRUCT   = struct.Struct('<fff')
ENDVAR_STRUCT = struct.Struct('<ifB')

# Boost table structures
BOOST0_STRUCT = struct.Struct('<Bfffff')  # byte + 5 floats
BOOSTI_STRUCT = struct.Struct('<ifffff')  # int32 + 5 floats

# Common single/dual-value parameter markers (per JDougNY notes)
# Format codes: 'f' float, 'i' int, 'b' byte, tuples represent sequences
PARAMS = {
    b'\x22\x4A\xE2\xDD\x6C': ('FuelConsumption', ('f',)),
    b'\x22\xD2\xA2\x92\x32': ('FuelEstimate',    ('f',)),
    b'\x22\x46\x65\xAE\x87': ('EngineInertia',   ('f',)),
    b'\x22\x40\xF1\xD2\xB9': ('Unknown_EngineFreeRevs', ('f',)),  # Makes engine rev out of control
    b'\x24\x4D\x23\x97\x54\xA2': ('IdleRPMLogic', ('f','f')),   # alt 52: int,int
    b'\x24\x4D\x23\x97\x54\x52': ('IdleRPMLogic', ('i','i')),
    b'\x22\x21\x98\x99\xAE': ('LaunchEfficiency', ('f',)),
    b'\x24\x79\x02\xB6\xBD\xA2': ('LaunchRPMLogic', ('f','f')),
    b'\x24\xDE\xA7\x2E\xB7\x23\x00': ('RevLimitRange', ('f','f','b')),  # float variant per edf-hex-map.xml
    b'\x24\xDE\xA7\x2E\xB7\x13\x00': ('RevLimitRange', ('i','b','b')),
    b'\x20\xA5\x5C\xC1\xC4': ('RevLimitSetting', ('b',)),  # Byte with value
    b'\x28\xA5\x5C\xC1\xC4': ('RevLimitSetting_NoValue', ()),  # No value variant
    b'\x22\x19\x66\x8A\xF9': ('RevLimitLogic',   ('f',)),
    b'\x24\x83\x15\x2F\x20\x03\x00': ('EngineFuelMapRange', ('b','b','b')),
    b'\x20\xC4\x44\x73\xF5': ('EngineFuelMapSetting', ('b',)),
    b'\x24\xBF\x84\x7C\xF1\xA3\x00': ('EngineBrakingMapRange', ('f','f','b')),
    b'\x20\xBE\x71\xED\x67': ('EngineBrakingMapSetting', ('b',)),
    b'\x22\xAF\xD7\x8A\xDD': ('OptimumOilTemp', ('f',)),
    b'\x22\x54\x10\x6D\xB1': ('CombustionHeat', ('f',)),
    b'\x22\xF6\xE3\x9F\xD9': ('EngineSpeedHeat', ('f',)),
    b'\x22\xB3\x0F\x25\xFC': ('OilMinimumCooling', ('f',)),
    b'\x24\xA7\x00\xD2\x3A\xA2': ('OilWaterHeatTransfer', ('f','f')),
    b'\x22\x67\x17\x15\x86': ('WaterMinimumCooling', ('f',)),
    b'\x24\x6A\xDA\x2B\x3A\xA2': ('RadiatorCooling', ('f','f')),
    # Unknown chunk signatures
    b'\x21\x3F\x6B\x7B\xE7\x82\x00': ('Unknown_Chunk_213F6B', ('b','b')),
    b'\x20\x6D\x47\xC1\xB2': ('Unknown_Chunk_206D47', ('b',)),
    # Lifetime parameters
    b'\x24\xD3\x94\x64\xAF\xA2': ('LifetimeEngineRPM', ('f','f')),
    b'\x24\xD3\x94\x64\xAF\x52': ('LifetimeEngineRPM', ('i','i')),
    b'\x24\x0A\xCE\xA8\x58\xA2': ('LifetimeOilTemp', ('f','f')),
    b'\x24\x05\x71\xC7\x19\xA2': ('Unknown_LMP_RWD_P30_A', ('f','f')),  # Present in LMP_RWD_P30
    b'\x22\xF7\x5F\x82\x2B': ('LifetimeAvg', ('f',)),
    b'\x22\x52\x7B\x76\xCD': ('LifetimeVar', ('f',)),
    b'\x24\xC1\xF4\x54\x3C\x83\x02': ('Unknown_LMP_RWD_P30_B', ('b','f','f')),  # Present in LMP_RWD_P30
    b'\x24\xCE\xB1\x75\x25\xA3\x02': ('EngineEmission', ('f','f','f')),
    b'\x20\x11\x8B\xA3\x81': ('OnboardStarter?', ('b',)),
    b'\x26\xAF\x00\xB3\xBA': ('EDF_UNKN_005', ('b',)),
    b'\x24\x52\x17\xFB\x41\xA3\x02': ('StarterTiming', ('f','f','f')),
    b'\x22\x92\xC7\xCD\x7C': ('Unknown_Float_3', ('f',)),  # Unknown with float 3.00
    # Air restrictor
    b'\x24\xFC\x89\xE8\x9C\xA3\x00': ('AirRestrictorRange', ('f','f','b')),
    b'\x20\xC5\xB4\x08\xFE': ('AirRestrictorSetting', ('b',)),
    b'\x28\xC5\xB4\x08\xFE': ('AirRestrictorSetting_NoValue', ()),  # No value variant
    # Other unknowns
    b'\x20\x2B\x3E\xD3\x40': ('Unknown_Byte_2B3ED340', ('b',)),
    b'\x22\xBA\x65\xDD\x60': ('Unknown_Float_6e-06', ('f',)),
    b'\x22\x81\x92\x17\xE0': ('Unknown_Float_295', ('f',)),
    # Old WasteGate parameters (replaced by boost control)
    b'\x24\x63\x23\x3A\x14\xA3\x00': ('WasteGateRange_OLD', ('f','f','b')),
    b'\x20\xDF\x86\x64\xFC': ('WasteGateSetting_OLD', ('b',)),
    b'\x28\xDF\x86\x64\xFC': ('WasteGateSetting_OLD_NoValue', ()),
    b'\x23\x00\x00\x50\xC3': ('Unknown_2300005', ('b','b')),
    # Boost control (current)
    b'\x24\xD7\x74\x45\x1A\x83\x00': ('BoostRange', ('b','f','b')),
    b'\x20\xCA\x2F\xD1\x34': ('BoostSetting', ('b',)),
    b'\x28\xCA\x2F\xD1\x34': ('BoostSetting_NoValue', ()),  # No value variant
}

ENGINE_LAYOUT_CODES = {
    b'\xD7\x50\x75\x68\xA3\x0A\x62': 'Single Cylinder (8B sequence)',
    b'\xC2\x2D\x3B': 'Flat 4 / 3 Rotor (per SMS)',
    b'\xD7\x2D\x3B': 'Straight 4',
    b'\xD7\x2C\x3B': 'Straight 5',
    b'\xD7\x2F\x3B': 'Straight 6',
    b'\xC2\x2F\x3B': 'Flat 6',
    b'\xD2\x21\x3B': 'V8 / Flat 8',
    b'\xD2\x28\x09\x2F': 'V12',
    b'\xD2\x28\x0B\x2F': 'V10',
}

# Human-readable field metadata for each parameter.
# Maps param name -> tuple of (label, type_display) per field.
PARAM_META = {
    'FuelConsumption':          (('Consumption', 'float'),),
    'FuelEstimate':             (('Estimate', 'float'),),
    'EngineInertia':            (('Inertia (kg·m²)', 'float'),),
    'Unknown_EngineFreeRevs':   (('Value', 'float'),),
    'IdleRPMLogic':             (('RPM Low', 'float/int'), ('RPM High', 'float/int')),
    'LaunchEfficiency':         (('Efficiency', 'float'),),
    'LaunchRPMLogic':           (('RPM 1', 'float'), ('RPM 2', 'float')),
    'RevLimitRange':            (('Limit (rpm)', 'float/int'), ('Max/Steps', 'float/int/byte'), ('Steps', 'byte')),
    'RevLimitSetting':          (('Setting', 'byte'),),
    'RevLimitSetting_NoValue':  (),
    'RevLimitLogic':            (('Value', 'float'),),
    'EngineFuelMapRange':       (('Min', 'byte'), ('Max', 'byte'), ('Steps', 'byte')),
    'EngineFuelMapSetting':     (('Map Index', 'byte'),),
    'EngineBrakingMapRange':    (('Min', 'float'), ('Max', 'float'), ('Steps', 'byte')),
    'EngineBrakingMapSetting':  (('Map Index', 'byte'),),
    'OptimumOilTemp':           (('Temp (°C)', 'float'),),
    'CombustionHeat':           (('Heat', 'float'),),
    'EngineSpeedHeat':          (('Heat', 'float'),),
    'OilMinimumCooling':        (('Cooling', 'float'),),
    'OilWaterHeatTransfer':     (('K1', 'float'), ('K2', 'float')),
    'WaterMinimumCooling':      (('Cooling', 'float'),),
    'RadiatorCooling':          (('K1', 'float'), ('K2', 'float')),
    'Unknown_Chunk_213F6B':     (('Byte 1', 'byte'), ('Byte 2', 'byte')),
    'Unknown_Chunk_206D47':     (('Value', 'byte'),),
    'LifetimeEngineRPM':        (('Avg (rpm)', 'float/int'), ('Max (rpm)', 'float/int')),
    'LifetimeOilTemp':          (('Avg (°C)', 'float'), ('Max (°C)', 'float')),
    'Unknown_LMP_RWD_P30_A':   (('Value 1', 'float'), ('Value 2', 'float')),
    'LifetimeAvg':              (('Average', 'float'),),
    'LifetimeVar':              (('Variance', 'float'),),
    'Unknown_LMP_RWD_P30_B':   (('Byte', 'byte'), ('Float 1', 'float'), ('Float 2', 'float')),
    'EngineEmission':           (('E1', 'float'), ('E2', 'float'), ('E3', 'float')),
    'OnboardStarter?':          (('Present', 'byte'),),
    'EDF_UNKN_005':             (('Value', 'byte'),),
    'StarterTiming':            (('T1', 'float'), ('T2', 'float'), ('T3', 'float')),
    'Unknown_Float_3':          (('Value', 'float'),),
    'AirRestrictorRange':       (('Min', 'float'), ('Max', 'float'), ('Steps', 'byte')),
    'AirRestrictorSetting':     (('Setting', 'byte'),),
    'AirRestrictorSetting_NoValue': (),
    'Unknown_Byte_2B3ED340':    (('Value', 'byte'),),
    'Unknown_Float_6e-06':      (('Value', 'float'),),
    'Unknown_Float_295':        (('Value', 'float'),),
    'WasteGateRange_OLD':       (('Min', 'float'), ('Max', 'float'), ('Steps', 'byte')),
    'WasteGateSetting_OLD':     (('Setting', 'byte'),),
    'WasteGateSetting_OLD_NoValue': (),
    'Unknown_2300005':          (('Byte 1', 'byte'), ('Byte 2', 'byte')),
    'BoostRange':               (('Min', 'byte'), ('Max (bar)', 'float'), ('Steps', 'byte')),
    'BoostSetting':             (('Setting', 'byte'),),
    'BoostSetting_NoValue':     (),
}
