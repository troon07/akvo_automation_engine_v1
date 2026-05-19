from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True)
class OfflineDetectionSettings:
    automation_id: str = "offline_detection"
    scheduler_interval_seconds: int = 60
    alert_type: str = "machine_offline"
    severity: str = "critical"
    offline_threshold: timedelta = timedelta(minutes=5)


@dataclass(frozen=True)
class CompressorRapidCyclingSettings:
    automation_id: str = "compressor_rapid_cycling"
    scheduler_interval_seconds: int = 120
    alert_type: str = "compressor_rapid_cycling"
    severity: str = "warning"
    lookback_window: timedelta = timedelta(minutes=10)
    transition_threshold: int = 3


@dataclass(frozen=True)
class FanCompressorSequenceSettings:
    automation_id: str = "fan_compressor_sequence_validation"
    scheduler_interval_seconds: int = 60
    startup_alert_type: str = "improper_startup_sequence"
    runtime_alert_type: str = "fan_compressor_mismatch"
    shutdown_alert_type: str = "improper_shutdown_sequence"
    startup_severity: str = "warning"
    runtime_severity: str = "critical"
    shutdown_severity: str = "warning"
    startup_fan_lead_time: timedelta = timedelta(minutes=5)
    shutdown_fan_run_time: timedelta = timedelta(minutes=2)
    lookback_window: timedelta = timedelta(minutes=10)


@dataclass(frozen=True)
class OperationalIntegrityValidationSettings:
    automation_id: str = "operational_integrity_validation"
    scheduler_interval_seconds: int = 60


@dataclass(frozen=True)
class SensorFreezeDetectionSettings:
    automation_id: str = "sensor_freeze_detection"
    scheduler_interval_seconds: int = 900
    alert_type: str = "sensor_freeze_detected"
    severity: str = "warning"


@dataclass(frozen=True)
class ContinuousPumpRuntimeDetectionSettings:
    automation_id: str = "continuous_pump_runtime_detection"
    scheduler_interval_seconds: int = 900
    alert_type: str = "continuous_pump_runtime_detected"
    severity: str = "warning"


OFFLINE_DETECTION = OfflineDetectionSettings()
COMPRESSOR_RAPID_CYCLING = CompressorRapidCyclingSettings()
FAN_COMPRESSOR_SEQUENCE = FanCompressorSequenceSettings()
OPERATIONAL_INTEGRITY_VALIDATION = OperationalIntegrityValidationSettings()
SENSOR_FREEZE_DETECTION = SensorFreezeDetectionSettings()
CONTINUOUS_PUMP_RUNTIME_DETECTION = ContinuousPumpRuntimeDetectionSettings()
