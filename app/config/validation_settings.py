from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationSettings:
    humidity_min: float = 0.0
    humidity_max: float = 100.0
    voltage_min: float = 180.0
    voltage_max: float = 260.0
    compressor_min_watts: float = 100.0
    compressor_min_current: float = 1.0


VALIDATION_SETTINGS = ValidationSettings()
