from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationSettings:
    humidity_min: float = 0.0
    humidity_max: float = 100.0
    voltage_min: float = 180.0
    voltage_max: float = 260.0
    compressor_min_watts: float = 100.0
    compressor_min_current: float = 1.0
    freeze_detection_window_hours: int = 2
    humidity_variance_threshold: float = 0.2
    minimum_freeze_sample_count: int = 20
    continuous_pump_runtime_window_minutes: int = 45
    minimum_continuous_pump_samples: int = 15


VALIDATION_SETTINGS = ValidationSettings()
