from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fanforge.errors import ConfigError


ADC_FIXED_REFERENCE_MV = {
    "2v": 2000,
    "3v": 3000,
    "4v": 4000,
}


def _voltage_target_adc(
    voltage_mv: int,
    reference: str,
    divider_high_ohm: int,
    divider_low_ohm: int,
    measurement_multiplier: int,
) -> int:
    """Convert a physical AD_FAN target to the generated comparison units."""
    try:
        reference_mv = ADC_FIXED_REFERENCE_MV[reference]
    except KeyError as exc:
        raise ConfigError(
            "fixed-voltage target conversion requires a fixed 2v, 3v, or 4v "
            "ADC reference"
        ) from exc
    numerator = (
        voltage_mv
        * divider_low_ohm
        * 4095
        * measurement_multiplier
    )
    denominator = reference_mv * (divider_high_ohm + divider_low_ohm)
    return (numerator + denominator // 2) // denominator

DISPLAY_SEGMENT_BITS = {
    "hundreds.0": (0, 0x01),
    "hundreds.1": (0, 0x02),
    "icon.percent": (0, 0x04),
    "icon.cooling": (0, 0x08),
    "icon.charge": (0, 0x10),
    "icon.fan": (0, 0x20),
    "icon.mist": (0, 0x40),
    "icon.aux": (0, 0x80),
    "tens.a": (1, 0x01),
    "tens.b": (1, 0x02),
    "tens.c": (1, 0x04),
    "tens.d": (1, 0x08),
    "tens.e": (1, 0x10),
    "tens.f": (1, 0x20),
    "tens.g": (1, 0x40),
    "ones.a": (2, 0x01),
    "ones.b": (2, 0x02),
    "ones.c": (2, 0x04),
    "ones.d": (2, 0x08),
    "ones.e": (2, 0x10),
    "ones.f": (2, 0x20),
    "ones.g": (2, 0x40),
}

DISPLAY_REQUIRED_DIGIT_SIGNALS = (
    "hundreds.0",
    "hundreds.1",
    "tens.a",
    "tens.b",
    "tens.c",
    "tens.d",
    "tens.e",
    "tens.f",
    "tens.g",
    "ones.a",
    "ones.b",
    "ones.c",
    "ones.d",
    "ones.e",
    "ones.f",
    "ones.g",
)

KEY_ACTIONS = (
    "none",
    "fan_cycle",
    "fan_power_toggle",
    "fan_step_up",
    "fan_step_down",
    "cooling_toggle",
    "light_cycle",
    "atomizer_toggle",
)

STANDARD_188_STYLE_A_CONNECTIONS = (
    ("ones.b", 2, 1),
    ("ones.d", 3, 1),
    ("ones.f", 4, 1),
    ("ones.g", 5, 1),
    ("ones.a", 1, 2),
    ("tens.b", 3, 2),
    ("tens.d", 4, 2),
    ("tens.e", 5, 2),
    ("ones.c", 1, 3),
    ("tens.a", 2, 3),
    ("tens.c", 4, 3),
    ("tens.f", 5, 3),
    ("ones.e", 1, 4),
    ("hundreds.1", 2, 4),
    ("hundreds.0", 3, 4),
    ("tens.g", 5, 4),
    ("icon.percent", 2, 5),
    ("icon.cooling", 3, 5),
)

ROOT_KEYS = {
    "schema_version",
    "project",
    "mcu",
    "timebase",
    "pins",
    "features",
}

FEATURE_KEYS = {
    "motor",
    "fan_voltage_protection",
    "battery_monitor",
    "ad_key",
    "digital_key",
    "slide_switch",
    "encoder",
    "slide_resistor",
    "charging",
    "cooling",
    "light",
    "atomizer",
    "display",
    "classic_product",
}

SECTION_KEYS = {
    "project": {"name", "self_test_ms"},
    "mcu": {"model", "package", "oscillator_hz", "system_divider"},
    "timebase": {"interrupt_us", "t1_prescaler"},
    "motor": {
        "kind",
        "pwm_frequency_hz",
        "pwm_clock_source",
        "pwm_prescaler",
        "run_duty_percent",
        "duty_curve",
        "voltage_curve",
        "brushed",
        "detection",
    },
    "fan_voltage_protection": {
        "enabled",
        "adc_reference",
        "adc_clock",
        "discard_samples",
        "average_samples",
        "overvoltage_limit",
        "overvoltage_adc_threshold",
        "consecutive_confirmations",
    },
    "battery_monitor": {"enabled", "business"},
    "ad_key": {
        "enabled",
        "adc_reference",
        "adc_clock",
        "discard_samples",
        "average_samples",
        "double_click_ms",
        "keys",
    },
    "digital_key": {"enabled", "double_click_ms", "keys"},
    "slide_switch": {
        "enabled",
        "active_level",
        "pull",
        "zero_battery_disable_pull_wake",
    },
    "encoder": {
        "enabled",
        "pull",
        "filter_us",
        "clockwise_increases",
        "normal_step",
        "acceleration_window_ms",
        "acceleration_events",
        "accelerated_step",
    },
    "slide_resistor": {
        "enabled",
        "adc_reference",
        "adc_clock",
        "discard_samples",
        "accumulation_samples",
        "low_gear_adc_sum",
        "high_gear_adc_sum",
        "low_gear_at_high_adc",
        "deadband_gears",
        "confirmation_count",
        "supply_active_level",
    },
    "charging": {"enabled", "kind"},
    "cooling": {
        "enabled",
        "presence_detection",
        "control_mode",
        "allow_while_charging",
    },
    "light": {"enabled", "presence_detection", "mode_profile"},
    "atomizer": {
        "enabled",
        "pwm_frequency_hz",
        "pwm_clock_source",
        "pwm_prescaler",
        "duty_percent",
        "dependency",
        "allow_while_charging",
    },
    "display": {
        "enabled",
        "profile",
        "drive_mode",
        "pin_count",
        "connections",
        "behavior",
    },
    "classic_product": {
        "enabled",
        "input_kind",
        "gear_steps",
        "gear_range",
        "long_adjust",
        "charging_kind",
        "cooling_enabled",
        "charge_max_gear",
        "display_hardware",
        "display_policy",
        "low_blink_target",
        "charge_blink_target",
        "sleep_enabled",
    },
}

NESTED_KEYS = {
    "motor.duty_curve": {"base_count", "gear_divisor"},
    "motor.voltage_curve": {
        "target_mode",
        "target_adc_base",
        "target_adc_step",
        "target_adc_max",
        "target_voltage_min_mv",
        "target_voltage_step_mv",
        "target_voltage_max_mv",
        "target_calibration_offset_mv",
        "measurement_multiplier",
        "error_window_adc",
        "pwm_min_count",
        "pwm_max_count",
        "slow_adjust_ms",
    },
    "motor.brushed": {
        "pwm_frequency_hz",
        "duty_base_count",
        "duty_gear_divisor",
    },
    "motor.detection": {"samples", "high_threshold"},
    "fan_voltage_protection.overvoltage_limit": {
        "voltage_mv",
        "divider_high_ohm",
        "divider_low_ohm",
        "adc_reference",
    },
    "battery_monitor.business": {
        "enabled",
        "thresholds",
        "compensation",
        "timing_ms",
    },
    "battery_monitor.business.thresholds": {
        "zero_shutdown",
        "low",
        "p0",
        "p5",
        "p10",
        "p50",
        "p80",
        "p100",
    },
    "battery_monitor.business.compensation": {
        "fan_segments",
        "brushed_fan_segments",
        "cooling",
        "brushed_cooling",
    },
    "battery_monitor.business.timing_ms": {
        "charge_active",
        "charge_full",
        "discharge",
        "low_discharge",
    },
    "ad_key.keys[]": {
        "name",
        "min",
        "max",
        "short_action",
        "double_action",
        "long_action",
    },
    "digital_key.keys[]": {
        "name",
        "short_action",
        "double_action",
        "long_action",
    },
    "display.behavior": {
        "profile",
        "gear_event_ms",
        "normal_battery_preview_ms",
        "normal_idle_page",
        "charging_idle_page",
    },
    "display.connections[]": {"positive", "negative"},
    "classic_product.gear_range": {"minimum", "maximum"},
}


def _require_dict(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise ConfigError(f"'{key}' must be an object")
    return value


def _reject_unknown_keys(
    value: dict[str, Any],
    allowed: set[str],
    path: str,
) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ConfigError(
            f"unknown {path} field(s): {', '.join(unknown)}"
        )


def _require_str(parent: dict[str, Any], key: str) -> str:
    value = parent.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"'{key}' must be a non-empty string")
    return value


def _require_int(parent: dict[str, Any], key: str) -> int:
    value = parent.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ConfigError(f"'{key}' must be an integer")
    return value


def _require_bool(parent: dict[str, Any], key: str) -> bool:
    value = parent.get(key)
    if not isinstance(value, bool):
        raise ConfigError(f"'{key}' must be true or false")
    return value


def _require_int_tuple(parent: dict[str, Any], key: str) -> tuple[int, ...]:
    value = parent.get(key)
    if not isinstance(value, list) or not value:
        raise ConfigError(f"'{key}' must be a non-empty integer array")
    if any(not isinstance(item, int) or isinstance(item, bool) for item in value):
        raise ConfigError(f"'{key}' must contain integers only")
    return tuple(value)


@dataclass(frozen=True)
class McuConfig:
    model: str
    package: str
    oscillator_hz: int
    system_divider: int

    @property
    def fcpu_hz(self) -> int:
        return self.oscillator_hz // self.system_divider


@dataclass(frozen=True)
class TimebaseConfig:
    interrupt_us: int
    t1_prescaler: int | None


@dataclass(frozen=True)
class MotorConfig:
    kind: str
    pwm_frequency_hz: int
    pwm_clock_source: str
    pwm_prescaler: int | None
    run_duty_percent: int | None
    duty_base_count: int | None
    duty_gear_divisor: int | None
    voltage_target_base: int | None
    voltage_target_step: int | None
    voltage_target_max: int | None
    voltage_target_mode: str | None
    voltage_target_calibration_offset_mv: int | None
    voltage_target_min_mv: int | None
    voltage_target_step_mv: int | None
    voltage_target_max_mv: int | None
    voltage_measurement_multiplier: int | None
    voltage_error_window: int | None
    voltage_pwm_min_count: int | None
    voltage_pwm_max_count: int | None
    voltage_slow_adjust_ms: int | None
    brushed_pwm_frequency_hz: int | None
    brushed_duty_base_count: int | None
    brushed_duty_gear_divisor: int | None
    detection_samples: int | None
    detection_high_threshold: int | None


@dataclass(frozen=True)
class FanProtectionConfig:
    enabled: bool
    adc_reference: str
    overvoltage_adc_reference: str
    adc_clock: str
    discard_samples: int
    average_samples: int
    overvoltage_adc_threshold: int
    overvoltage_voltage_mv: int | None
    divider_high_ohm: int | None
    divider_low_ohm: int | None
    consecutive_confirmations: int


@dataclass(frozen=True)
class BatteryMonitorConfig:
    enabled: bool
    business_enabled: bool
    curve: "BatteryCurveConfig | None"


@dataclass(frozen=True)
class AdKeyBandConfig:
    name: str
    minimum_adc: int
    maximum_adc: int
    short_action: str
    double_action: str
    long_action: str


@dataclass(frozen=True)
class AdKeyConfig:
    enabled: bool
    adc_reference: str
    adc_clock: str
    discard_samples: int
    average_samples: int
    threshold_profile: str
    double_click_ms: int
    key_bands: tuple[AdKeyBandConfig, ...]


@dataclass(frozen=True)
class DigitalKeyActionConfig:
    name: str
    short_action: str
    double_action: str
    long_action: str


@dataclass(frozen=True)
class DigitalKeyConfig:
    enabled: bool
    double_click_ms: int
    keys: tuple[DigitalKeyActionConfig, ...]


@dataclass(frozen=True)
class SlideSwitchConfig:
    enabled: bool
    active_level: str
    pull: str
    zero_battery_disable_pull_wake: bool


@dataclass(frozen=True)
class EncoderConfig:
    enabled: bool
    pull: str
    filter_us: int
    clockwise_increases: bool
    normal_step: int
    acceleration_window_ms: int
    acceleration_events: int
    accelerated_step: int


@dataclass(frozen=True)
class SlideResistorConfig:
    enabled: bool
    adc_reference: str
    adc_clock: str
    discard_samples: int
    accumulation_samples: int
    low_gear_adc_sum: int
    high_gear_adc_sum: int
    low_gear_at_high_adc: bool
    deadband_gears: int
    confirmation_count: int
    supply_active_level: str


@dataclass(frozen=True)
class ChargingConfig:
    enabled: bool
    kind: str


@dataclass(frozen=True)
class CoolingConfig:
    enabled: bool
    presence_detection: bool
    control_mode: str
    allow_while_charging: bool


@dataclass(frozen=True)
class LightConfig:
    enabled: bool
    presence_detection: bool
    mode_profile: str


@dataclass(frozen=True)
class AtomizerConfig:
    enabled: bool
    pwm_frequency_hz: int
    pwm_clock_source: str
    pwm_prescaler: int | None
    duty_percent: int
    dependency: str
    allow_while_charging: bool


@dataclass(frozen=True)
class DisplayConnectionConfig:
    signal: str
    positive_pin_index: int
    negative_pin_index: int


@dataclass(frozen=True)
class DisplayConfig:
    enabled: bool
    profile: str
    drive_mode: str
    pin_count: int
    connections: tuple[DisplayConnectionConfig, ...]
    behavior_profile: str
    gear_event_ms: int
    normal_battery_preview_ms: int
    normal_idle_page: str
    charging_idle_page: str


@dataclass(frozen=True)
class BatteryCurveConfig:
    zero_shutdown: int
    low_threshold: int
    adc_0: int
    adc_5: int
    adc_10: int
    adc_50: int
    adc_80: int
    adc_100: int
    fan_compensation: tuple[int, int, int, int, int]
    brushed_fan_compensation: tuple[int, int, int, int, int] | None
    cooling_compensation: int
    brushed_cooling_compensation: int | None
    charge_active_period_ms: int
    charge_full_period_ms: int
    discharge_period_ms: int
    low_discharge_period_ms: int


@dataclass(frozen=True)
class ClassicProductConfig:
    enabled: bool
    input_kind: str
    gear_mode: str
    gear_steps: tuple[int, ...]
    minimum_gear: int
    maximum_gear: int
    long_adjust: bool
    charging_kind: str
    cooling_enabled: bool
    charge_max_gear: int
    display_hardware: str
    display_policy: str
    low_blink_target: str
    charge_blink_target: str
    sleep_enabled: bool


@dataclass(frozen=True)
class ProjectConfig:
    source_path: Path
    schema_version: int
    project_name: str
    mcu: McuConfig
    timebase: TimebaseConfig
    pins: dict[str, int]
    motor: MotorConfig
    fan_protection: FanProtectionConfig
    battery_monitor: BatteryMonitorConfig
    ad_key: AdKeyConfig
    digital_key: DigitalKeyConfig
    slide_switch: SlideSwitchConfig
    encoder: EncoderConfig
    slide_resistor: SlideResistorConfig
    charging: ChargingConfig
    cooling: CoolingConfig
    light: LightConfig
    atomizer: AtomizerConfig
    display: DisplayConfig
    classic_product: ClassicProductConfig
    self_test_ms: int

    @classmethod
    def from_dict(cls, source_path: Path, raw: dict[str, Any]) -> "ProjectConfig":
        _reject_unknown_keys(raw, ROOT_KEYS, "configuration")
        schema_version = _require_int(raw, "schema_version")
        if schema_version != 1:
            raise ConfigError("only schema_version 1 is supported")

        project = _require_dict(raw, "project")
        mcu = _require_dict(raw, "mcu")
        timebase = _require_dict(raw, "timebase")
        pins = _require_dict(raw, "pins")
        features = _require_dict(raw, "features")
        _reject_unknown_keys(features, FEATURE_KEYS, "features")
        motor = _require_dict(features, "motor")
        protection = _require_dict(features, "fan_voltage_protection")
        battery_monitor_raw = features.get("battery_monitor", {"enabled": False})
        if not isinstance(battery_monitor_raw, dict):
            raise ConfigError("'battery_monitor' must be an object")
        ad_key_raw = features.get("ad_key", {"enabled": False})
        if not isinstance(ad_key_raw, dict):
            raise ConfigError("'ad_key' must be an object")
        digital_key_raw = features.get(
            "digital_key", {"enabled": False}
        )
        if not isinstance(digital_key_raw, dict):
            raise ConfigError("'digital_key' must be an object")
        slide_switch_raw = features.get(
            "slide_switch", {"enabled": False}
        )
        if not isinstance(slide_switch_raw, dict):
            raise ConfigError("'slide_switch' must be an object")
        encoder_raw = features.get("encoder", {"enabled": False})
        if not isinstance(encoder_raw, dict):
            raise ConfigError("'encoder' must be an object")
        slide_resistor_raw = features.get(
            "slide_resistor", {"enabled": False}
        )
        if not isinstance(slide_resistor_raw, dict):
            raise ConfigError("'slide_resistor' must be an object")
        classic_raw = features.get("classic_product", {"enabled": False})
        if not isinstance(classic_raw, dict):
            raise ConfigError("'classic_product' must be an object")
        charging_raw = features.get("charging")
        if charging_raw is not None and not isinstance(charging_raw, dict):
            raise ConfigError("'charging' must be an object")
        cooling_raw = features.get("cooling")
        if cooling_raw is not None and not isinstance(cooling_raw, dict):
            raise ConfigError("'cooling' must be an object")
        light_raw = features.get("light", {"enabled": False})
        if not isinstance(light_raw, dict):
            raise ConfigError("'light' must be an object")
        atomizer_raw = features.get("atomizer", {"enabled": False})
        if not isinstance(atomizer_raw, dict):
            raise ConfigError("'atomizer' must be an object")
        display_raw = features.get("display")
        if display_raw is not None and not isinstance(display_raw, dict):
            raise ConfigError("'display' must be an object")

        section_values = {
            "project": project,
            "mcu": mcu,
            "timebase": timebase,
            "motor": motor,
            "fan_voltage_protection": protection,
            "battery_monitor": battery_monitor_raw,
            "ad_key": ad_key_raw,
            "digital_key": digital_key_raw,
            "slide_switch": slide_switch_raw,
            "encoder": encoder_raw,
            "slide_resistor": slide_resistor_raw,
            "classic_product": classic_raw,
            "charging": charging_raw,
            "cooling": cooling_raw,
            "light": light_raw,
            "atomizer": atomizer_raw,
            "display": display_raw,
        }
        for section_name, section_value in section_values.items():
            if section_value is not None:
                _reject_unknown_keys(
                    section_value,
                    SECTION_KEYS[section_name],
                    section_name,
                )

        model = _require_str(mcu, "model").upper()
        package = _require_str(mcu, "package").upper()
        oscillator_hz = _require_int(mcu, "oscillator_hz")
        system_divider = _require_int(mcu, "system_divider")
        if oscillator_hz <= 0:
            raise ConfigError("'oscillator_hz' must be positive")
        if system_divider not in (1, 2, 4, 8):
            raise ConfigError("'system_divider' must be one of 1, 2, 4, 8")
        if oscillator_hz % system_divider:
            raise ConfigError("'oscillator_hz' must be divisible by 'system_divider'")

        interrupt_us = _require_int(timebase, "interrupt_us")
        if interrupt_us not in (100, 125, 1000):
            raise ConfigError("'interrupt_us' must be 100, 125, or 1000")
        t1_prescaler_raw = timebase.get("t1_prescaler", "auto")
        if t1_prescaler_raw == "auto":
            t1_prescaler = None
        elif isinstance(t1_prescaler_raw, int) and t1_prescaler_raw in (1, 2, 4, 8):
            t1_prescaler = t1_prescaler_raw
        else:
            raise ConfigError("'t1_prescaler' must be auto, 1, 2, 4, or 8")

        pin_bindings: dict[str, int] = {}
        battery_monitor_enabled = _require_bool(battery_monitor_raw, "enabled")
        ad_key_enabled = _require_bool(ad_key_raw, "enabled")
        digital_key_enabled = _require_bool(digital_key_raw, "enabled")
        slide_switch_enabled = _require_bool(slide_switch_raw, "enabled")
        encoder_enabled = _require_bool(encoder_raw, "enabled")
        slide_resistor_enabled = _require_bool(
            slide_resistor_raw, "enabled"
        )
        classic_enabled = _require_bool(classic_raw, "enabled")
        if classic_enabled:
            classic_input_kind = _require_str(classic_raw, "input_kind")
            if classic_input_kind not in (
                "two_digital_keys_active_low",
                "digital_keys_active_low",
                "two_ad_keys_active_low_ranges",
                "ad_keys_active_low_ranges",
                "rotary_encoder_active_low",
                "single_key_slide_resistor_active_low",
            ):
                raise ConfigError(
                    "'classic_product.input_kind' must be "
                    "two_digital_keys_active_low or "
                    "digital_keys_active_low or "
                    "two_ad_keys_active_low_ranges or "
                    "ad_keys_active_low_ranges or "
                    "rotary_encoder_active_low or "
                    "single_key_slide_resistor_active_low"
                )
        else:
            classic_input_kind = "none"

        legacy_charging_kind = classic_raw.get("charging_kind")
        if legacy_charging_kind is not None and (
            not isinstance(legacy_charging_kind, str)
            or not legacy_charging_kind.strip()
        ):
            raise ConfigError(
                "'classic_product.charging_kind' must be a non-empty string"
            )
        if charging_raw is None:
            if classic_enabled:
                if legacy_charging_kind is None:
                    raise ConfigError(
                        "classic product requires 'features.charging' or "
                        "legacy 'classic_product.charging_kind'"
                    )
                charging_kind = legacy_charging_kind
            else:
                charging_kind = "none"
        else:
            charging_enabled = _require_bool(charging_raw, "enabled")
            if charging_enabled:
                charging_kind = _require_str(charging_raw, "kind")
            else:
                charging_kind = charging_raw.get("kind", "none")
                if charging_kind != "none":
                    raise ConfigError(
                        "disabled charging module must use kind=none"
                    )
            if (
                legacy_charging_kind is not None
                and legacy_charging_kind != charging_kind
            ):
                raise ConfigError(
                    "'features.charging.kind' conflicts with legacy "
                    "'classic_product.charging_kind'"
                )
        if charging_kind not in (
            "none",
            "chrg_stdby_active_low",
            "chrg_chrg_max_active_low_static",
            "insert_active_high_chrg_active_low",
        ):
            raise ConfigError(
                "'charging.kind' must be none, chrg_stdby_active_low, "
                "chrg_chrg_max_active_low_static, or "
                "insert_active_high_chrg_active_low"
            )
        charging_enabled = charging_kind != "none"
        if charging_enabled and not classic_enabled:
            raise ConfigError("charging requires classic_product.enabled=true")

        legacy_cooling_enabled = classic_raw.get("cooling_enabled")
        if legacy_cooling_enabled is not None and not isinstance(
            legacy_cooling_enabled, bool
        ):
            raise ConfigError(
                "'classic_product.cooling_enabled' must be true or false"
            )
        if cooling_raw is None:
            cooling_enabled = bool(
                legacy_cooling_enabled if classic_enabled else False
            )
            cooling_presence_detection = cooling_enabled
            cooling_control_mode = "toggle_while_fan_on"
            cooling_allow_while_charging = False
        else:
            cooling_enabled = _require_bool(cooling_raw, "enabled")
            cooling_presence_detection = cooling_raw.get(
                "presence_detection", cooling_enabled
            )
            cooling_control_mode = cooling_raw.get(
                "control_mode", "toggle_while_fan_on"
            )
            cooling_allow_while_charging = cooling_raw.get(
                "allow_while_charging", False
            )
            if (
                legacy_cooling_enabled is not None
                and legacy_cooling_enabled != cooling_enabled
            ):
                raise ConfigError(
                    "'features.cooling.enabled' conflicts with legacy "
                    "'classic_product.cooling_enabled'"
                )
        if not isinstance(cooling_presence_detection, bool):
            raise ConfigError(
                "'cooling.presence_detection' must be true or false"
            )
        if cooling_control_mode not in (
            "toggle_while_fan_on",
            "follow_fan",
        ):
            raise ConfigError(
                "'cooling.control_mode' must be toggle_while_fan_on "
                "or follow_fan"
            )
        if not isinstance(cooling_allow_while_charging, bool):
            raise ConfigError(
                "'cooling.allow_while_charging' must be true or false"
            )
        if cooling_presence_detection and not cooling_enabled:
            raise ConfigError(
                "cooling presence detection requires cooling.enabled=true"
            )
        if cooling_enabled and not classic_enabled:
            raise ConfigError("cooling requires classic_product.enabled=true")

        light_enabled = _require_bool(light_raw, "enabled")
        light_presence_detection = light_raw.get(
            "presence_detection", light_enabled
        )
        light_mode_profile = light_raw.get("mode_profile", "fan_sync")
        if not isinstance(light_presence_detection, bool):
            raise ConfigError(
                "'light.presence_detection' must be true or false"
            )
        if light_mode_profile not in (
            "fan_sync",
            "on_off",
            "on_off_flash",
        ):
            raise ConfigError(
                "'light.mode_profile' must be fan_sync, on_off, "
                "or on_off_flash"
            )
        if light_presence_detection and not light_enabled:
            raise ConfigError(
                "light presence detection requires light.enabled=true"
            )
        if light_enabled and not classic_enabled:
            raise ConfigError("light requires classic_product.enabled=true")

        atomizer_enabled = _require_bool(atomizer_raw, "enabled")
        atomizer_pwm_frequency_hz = atomizer_raw.get(
            "pwm_frequency_hz", 108000
        )
        atomizer_pwm_clock_source = atomizer_raw.get(
            "pwm_clock_source", "fosc"
        )
        atomizer_pwm_prescaler_raw = atomizer_raw.get(
            "pwm_prescaler", "auto"
        )
        atomizer_duty_percent = atomizer_raw.get("duty_percent", 10)
        atomizer_dependency = atomizer_raw.get(
            "dependency", "fan_required"
        )
        atomizer_allow_while_charging = atomizer_raw.get(
            "allow_while_charging", True
        )
        if (
            not isinstance(atomizer_pwm_frequency_hz, int)
            or isinstance(atomizer_pwm_frequency_hz, bool)
            or atomizer_pwm_frequency_hz <= 0
        ):
            raise ConfigError(
                "'atomizer.pwm_frequency_hz' must be positive"
            )
        if atomizer_pwm_clock_source not in ("fosc", "fcpu_div2"):
            raise ConfigError(
                "'atomizer.pwm_clock_source' must be fosc or fcpu_div2"
            )
        if atomizer_pwm_prescaler_raw == "auto":
            atomizer_pwm_prescaler = None
        elif (
            isinstance(atomizer_pwm_prescaler_raw, int)
            and not isinstance(atomizer_pwm_prescaler_raw, bool)
            and atomizer_pwm_prescaler_raw
            in (1, 2, 4, 8, 16, 32, 64, 128)
        ):
            atomizer_pwm_prescaler = atomizer_pwm_prescaler_raw
        else:
            raise ConfigError(
                "'atomizer.pwm_prescaler' must be auto or one of "
                "1,2,4,8,16,32,64,128"
            )
        if (
            not isinstance(atomizer_duty_percent, int)
            or isinstance(atomizer_duty_percent, bool)
            or not 1 <= atomizer_duty_percent <= 99
        ):
            raise ConfigError(
                "'atomizer.duty_percent' must be between 1 and 99"
            )
        if atomizer_dependency not in (
            "fan_required",
            "independent",
        ):
            raise ConfigError(
                "'atomizer.dependency' must be fan_required or independent"
            )
        if not isinstance(atomizer_allow_while_charging, bool):
            raise ConfigError(
                "'atomizer.allow_while_charging' must be true or false"
            )
        if atomizer_enabled and not classic_enabled:
            raise ConfigError(
                "atomizer requires classic_product.enabled=true"
            )

        legacy_display_hardware = classic_raw.get("display_hardware")
        if legacy_display_hardware is not None and (
            not isinstance(legacy_display_hardware, str)
            or not legacy_display_hardware.strip()
        ):
            raise ConfigError(
                "'classic_product.display_hardware' must be a non-empty string"
            )
        if display_raw is None:
            if classic_enabled:
                if legacy_display_hardware is None:
                    raise ConfigError(
                        "classic product requires 'features.display' or "
                        "legacy 'classic_product.display_hardware'"
                    )
                display_profile = legacy_display_hardware
                if (
                    display_profile
                    != "standard_188_cooling_percent_style_a"
                ):
                    raise ConfigError(
                        "unsupported legacy classic display hardware profile"
                    )
                display_enabled = True
                display_drive_mode = "output_high_input_off"
                display_pin_count = 5
                display_connections = tuple(
                    DisplayConnectionConfig(
                        signal=signal,
                        positive_pin_index=positive,
                        negative_pin_index=negative,
                    )
                    for signal, positive, negative
                    in STANDARD_188_STYLE_A_CONNECTIONS
                )
            else:
                display_enabled = False
                display_profile = "none"
                display_drive_mode = "none"
                display_pin_count = 0
                display_connections = ()
        else:
            display_enabled = _require_bool(display_raw, "enabled")
            if not display_enabled:
                display_profile = display_raw.get("profile", "none")
                if display_profile != "none":
                    raise ConfigError(
                        "disabled display module must use profile=none"
                    )
                display_drive_mode = "none"
                display_pin_count = 0
                display_connections = ()
            else:
                display_profile = _require_str(display_raw, "profile")
                display_drive_mode = display_raw.get(
                    "drive_mode", "output_high_input_off"
                )
                if display_drive_mode != "output_high_input_off":
                    raise ConfigError(
                        "initial display module supports only "
                        "drive_mode=output_high_input_off"
                    )
                if display_profile == "standard_188_cooling_percent_style_a":
                    display_pin_count = display_raw.get("pin_count", 5)
                    if display_pin_count != 5:
                        raise ConfigError(
                            "standard style-A display requires pin_count=5"
                        )
                    if "connections" in display_raw:
                        raise ConfigError(
                            "standard style-A display mapping is fixed; use "
                            "profile=custom_charlieplex_188 to override it"
                        )
                    display_connections = tuple(
                        DisplayConnectionConfig(
                            signal=signal,
                            positive_pin_index=positive,
                            negative_pin_index=negative,
                        )
                        for signal, positive, negative
                        in STANDARD_188_STYLE_A_CONNECTIONS
                    )
                elif display_profile == "custom_charlieplex_188":
                    display_pin_count = _require_int(
                        display_raw, "pin_count"
                    )
                    if not 5 <= display_pin_count <= 7:
                        raise ConfigError(
                            "'display.pin_count' must be between 5 and 7"
                        )
                    connections_raw = _require_dict(
                        display_raw, "connections"
                    )
                    unknown_signals = (
                        set(connections_raw) - set(DISPLAY_SEGMENT_BITS)
                    )
                    if unknown_signals:
                        raise ConfigError(
                            "unknown display signals: "
                            + ", ".join(sorted(unknown_signals))
                        )
                    missing_signals = (
                        set(DISPLAY_REQUIRED_DIGIT_SIGNALS)
                        - set(connections_raw)
                    )
                    if missing_signals:
                        raise ConfigError(
                            "custom display is missing digit signals: "
                            + ", ".join(sorted(missing_signals))
                        )
                    parsed_connections: list[
                        DisplayConnectionConfig
                    ] = []
                    used_pairs: set[tuple[int, int]] = set()
                    for signal in DISPLAY_SEGMENT_BITS:
                        connection_raw = connections_raw.get(signal)
                        if connection_raw is None:
                            continue
                        if not isinstance(connection_raw, dict):
                            raise ConfigError(
                                f"'display.connections.{signal}' must be "
                                "an object"
                            )
                        _reject_unknown_keys(
                            connection_raw,
                            NESTED_KEYS["display.connections[]"],
                            f"display.connections.{signal}",
                        )
                        positive = _require_int(
                            connection_raw, "positive"
                        )
                        negative = _require_int(
                            connection_raw, "negative"
                        )
                        if (
                            not 1 <= positive <= display_pin_count
                            or not 1 <= negative <= display_pin_count
                            or positive == negative
                        ):
                            raise ConfigError(
                                f"display signal '{signal}' has invalid "
                                "positive/negative pin indices"
                            )
                        pair = (positive, negative)
                        if pair in used_pairs:
                            raise ConfigError(
                                "display directed LED pair is assigned more "
                                f"than once: LED{positive}+ / LED{negative}-"
                            )
                        used_pairs.add(pair)
                        parsed_connections.append(
                            DisplayConnectionConfig(
                                signal=signal,
                                positive_pin_index=positive,
                                negative_pin_index=negative,
                            )
                        )
                    display_connections = tuple(parsed_connections)
                else:
                    raise ConfigError(
                        "'display.profile' must be "
                        "standard_188_cooling_percent_style_a or "
                        "custom_charlieplex_188"
                    )
            if (
                legacy_display_hardware is not None
                and legacy_display_hardware != display_profile
            ):
                raise ConfigError(
                    "'features.display.profile' conflicts with legacy "
                    "'classic_product.display_hardware'"
                )
        if classic_enabled and not display_enabled:
            raise ConfigError(
                "classic product requires display.enabled=true"
            )
        if display_enabled and not classic_enabled:
            raise ConfigError(
                "display requires classic_product.enabled=true"
            )
        legacy_display_policy = classic_raw.get("display_policy")
        if legacy_display_policy is not None and (
            not isinstance(legacy_display_policy, str)
            or not legacy_display_policy.strip()
        ):
            raise ConfigError(
                "'classic_product.display_policy' must be a non-empty string"
            )
        display_behavior_raw = (
            display_raw.get("behavior")
            if display_raw is not None
            else None
        )
        if display_behavior_raw is not None and not isinstance(
            display_behavior_raw, dict
        ):
            raise ConfigError("'display.behavior' must be an object")
        if display_behavior_raw is not None:
            _reject_unknown_keys(
                display_behavior_raw,
                NESTED_KEYS["display.behavior"],
                "display.behavior",
            )
        if not classic_enabled:
            display_behavior_profile = "none"
            display_gear_event_ms = 0
            display_battery_preview_ms = 0
            display_normal_idle_page = "gear"
            display_charging_idle_page = "battery"
        elif display_behavior_raw is None:
            display_behavior_profile = (
                legacy_display_policy
                or "gear_3s_battery_3s_gear"
            )
            if (
                display_behavior_profile
                != "gear_3s_battery_3s_gear"
            ):
                raise ConfigError(
                    "unsupported legacy classic display policy"
                )
            display_gear_event_ms = 3000
            display_battery_preview_ms = 3000
            display_normal_idle_page = "gear"
            display_charging_idle_page = "battery"
        else:
            display_behavior_profile = _require_str(
                display_behavior_raw, "profile"
            )
            if (
                display_behavior_profile
                != "gear_event_battery_preview_idle"
            ):
                raise ConfigError(
                    "'display.behavior.profile' must be "
                    "gear_event_battery_preview_idle"
                )
            display_gear_event_ms = _require_int(
                display_behavior_raw, "gear_event_ms"
            )
            display_battery_preview_ms = _require_int(
                display_behavior_raw, "normal_battery_preview_ms"
            )
            display_normal_idle_page = _require_str(
                display_behavior_raw, "normal_idle_page"
            )
            display_charging_idle_page = _require_str(
                display_behavior_raw, "charging_idle_page"
            )
            if (
                display_gear_event_ms < 10
                or display_gear_event_ms > 120000
                or display_gear_event_ms % 10
            ):
                raise ConfigError(
                    "'display.behavior.gear_event_ms' must be a 10ms "
                    "multiple within 10..120000"
                )
            if (
                display_battery_preview_ms < 0
                or display_battery_preview_ms > 120000
                or display_battery_preview_ms % 10
            ):
                raise ConfigError(
                    "'display.behavior.normal_battery_preview_ms' must be "
                    "zero or a 10ms multiple no greater than 120000"
                )
            if display_normal_idle_page not in ("gear", "battery"):
                raise ConfigError(
                    "'display.behavior.normal_idle_page' must be gear or "
                    "battery"
                )
            if display_charging_idle_page not in ("gear", "battery"):
                raise ConfigError(
                    "'display.behavior.charging_idle_page' must be gear or "
                    "battery"
                )
            if (
                display_normal_idle_page == "battery"
                and display_battery_preview_ms
            ):
                raise ConfigError(
                    "normal battery preview must be zero when the normal "
                    "idle page is already battery"
                )
            if (
                legacy_display_policy is not None
                and legacy_display_policy != display_behavior_profile
            ):
                raise ConfigError(
                    "'display.behavior.profile' conflicts with legacy "
                    "'classic_product.display_policy'"
                )

        if motor.get("kind") == "brushed_fixed_duty":
            required_pin_roles = ["FAN_ON"]
        else:
            required_pin_roles = ["PWM_FAN", "FAN_ON", "AD_FAN"]
        if atomizer_enabled:
            required_pin_roles.append("PWM_WH")
        if ad_key_enabled:
            required_pin_roles.append("AD_KEY")
        if slide_switch_enabled:
            required_pin_roles.append("SWI_KEY")
        if encoder_enabled:
            required_pin_roles.extend(("ENC_A", "ENC_B"))
        if slide_resistor_enabled:
            required_pin_roles.extend(("AD_SLIDER", "SLIDER_ON"))
        if classic_enabled:
            if classic_input_kind == "two_digital_keys_active_low":
                required_pin_roles.extend(("KEY1", "KEY2"))
            elif classic_input_kind == "digital_keys_active_low":
                digital_key_entries = digital_key_raw.get("keys", [])
                if isinstance(digital_key_entries, list):
                    required_pin_roles.extend(
                        str(item.get("name", "")).upper()
                        for item in digital_key_entries
                        if (
                            isinstance(item, dict)
                            and str(item.get("name", "")).upper()
                            in ("KEY1", "KEY2", "KEY3", "KEY4")
                        )
                    )
            elif (
                classic_input_kind
                == "single_key_slide_resistor_active_low"
            ):
                required_pin_roles.append("KEY")
            if charging_kind == "chrg_stdby_active_low":
                required_pin_roles.extend(("CHRG", "STDBY"))
            elif charging_kind == "chrg_chrg_max_active_low_static":
                required_pin_roles.extend(("CHRG", "CHRG_MAX"))
            elif charging_kind == "insert_active_high_chrg_active_low":
                required_pin_roles.extend(("INSERT", "CHRG"))
            required_pin_roles.extend(
                f"IO_LED_{index}"
                for index in range(1, display_pin_count + 1)
            )
            if cooling_enabled:
                required_pin_roles.append("COOL_EN")
            if light_enabled:
                required_pin_roles.append("LED_ON")
        for role in required_pin_roles:
            pin_bindings[role] = _require_int(pins, role)

        ad_key_adc_reference = _require_str(
            {
                "adc_reference": ad_key_raw.get("adc_reference", "vdd")
            },
            "adc_reference",
        ).lower()
        if ad_key_adc_reference not in ("2v", "3v", "4v", "vdd"):
            raise ConfigError(
                "'ad_key.adc_reference' must be 2v, 3v, 4v, or vdd"
            )
        ad_key_adc_clock = _require_str(
            {"adc_clock": ad_key_raw.get("adc_clock", "fcpu")},
            "adc_clock",
        ).lower()
        if ad_key_adc_clock not in (
            "fcpu",
            "fcpu_div2",
            "fcpu_div8",
            "fcpu_div16",
        ):
            raise ConfigError(
                "'ad_key.adc_clock' must be fcpu, fcpu_div2, "
                "fcpu_div8, or fcpu_div16"
            )
        ad_key_discard_samples = ad_key_raw.get("discard_samples", 2)
        ad_key_average_samples = ad_key_raw.get("average_samples", 8)
        ad_key_double_click_ms = ad_key_raw.get("double_click_ms", 350)
        if (
            not isinstance(ad_key_discard_samples, int)
            or isinstance(ad_key_discard_samples, bool)
            or ad_key_discard_samples < 0
        ):
            raise ConfigError(
                "'ad_key.discard_samples' must be a non-negative integer"
            )
        if (
            not isinstance(ad_key_average_samples, int)
            or isinstance(ad_key_average_samples, bool)
            or ad_key_average_samples < 1
            or ad_key_average_samples > 16
            or ad_key_average_samples & (ad_key_average_samples - 1)
        ):
            raise ConfigError(
                "'ad_key.average_samples' must be 1, 2, 4, 8, or 16"
            )

        ad_key_input_kinds = (
            "two_ad_keys_active_low_ranges",
            "ad_keys_active_low_ranges",
        )
        if (
            ad_key_enabled
            and classic_input_kind in ad_key_input_kinds
            and "keys" not in ad_key_raw
        ):
            key_bands_raw = [
                {"name": "KEY1", "min": 0, "max": 100},
                {"name": "KEY2", "min": 610, "max": 810},
            ]
            ad_key_threshold_profile = "default_two_key"
        else:
            key_bands_raw = ad_key_raw.get("keys", [])
            ad_key_threshold_profile = (
                "custom" if key_bands_raw else "none"
            )
        if not isinstance(key_bands_raw, list):
            raise ConfigError("'ad_key.keys' must be an array")
        key_bands: list[AdKeyBandConfig] = []
        for item in key_bands_raw:
            if not isinstance(item, dict):
                raise ConfigError("'ad_key.keys' entries must be objects")
            _reject_unknown_keys(
                item,
                NESTED_KEYS["ad_key.keys[]"],
                "ad_key.keys[]",
            )
            name = _require_str(item, "name").upper()
            if name not in ("KEY1", "KEY2", "KEY3", "KEY4"):
                raise ConfigError(
                    "'ad_key.keys[].name' must be KEY1, KEY2, KEY3, or KEY4"
                )
            minimum_adc = _require_int(item, "min")
            maximum_adc = _require_int(item, "max")
            if not 0 <= minimum_adc <= maximum_adc <= 4095:
                raise ConfigError(
                    "AD key ranges must satisfy 0 <= min <= max <= 4095"
                )
            short_action = item.get("short_action")
            double_action = item.get("double_action")
            long_action = item.get("long_action")
            if short_action is not None and (
                not isinstance(short_action, str)
                or short_action not in KEY_ACTIONS
            ):
                raise ConfigError(
                    "'ad_key.keys[].short_action' must be none, "
                    "fan_cycle, fan_power_toggle, fan_step_up, "
                    "fan_step_down, "
                    "cooling_toggle, light_cycle, or atomizer_toggle"
                )
            if double_action is not None and (
                not isinstance(double_action, str)
                or double_action not in KEY_ACTIONS
            ):
                raise ConfigError(
                    "'ad_key.keys[].double_action' must be none, "
                    "fan_cycle, fan_power_toggle, fan_step_up, "
                    "fan_step_down, cooling_toggle, light_cycle, "
                    "or atomizer_toggle"
                )
            if long_action is not None and (
                not isinstance(long_action, str)
                or long_action not in KEY_ACTIONS
            ):
                raise ConfigError(
                    "'ad_key.keys[].long_action' must be none, "
                    "fan_cycle, fan_power_toggle, fan_step_up, "
                    "fan_step_down, cooling_toggle, light_cycle, "
                    "or atomizer_toggle"
                )
            key_bands.append(
                AdKeyBandConfig(
                    name=name,
                    minimum_adc=minimum_adc,
                    maximum_adc=maximum_adc,
                    short_action=short_action or "",
                    double_action=double_action or "",
                    long_action=long_action or "",
                )
            )
        if len({item.name for item in key_bands}) != len(key_bands):
            raise ConfigError("AD key names must be unique")
        sorted_key_bands = sorted(
            key_bands, key=lambda item: (item.minimum_adc, item.maximum_adc)
        )
        if any(
            left.maximum_adc >= right.minimum_adc
            for left, right in zip(sorted_key_bands, sorted_key_bands[1:])
        ):
            raise ConfigError("AD key ranges must not overlap")
        if not ad_key_enabled and key_bands:
            raise ConfigError("'ad_key.keys' requires 'ad_key.enabled=true'")
        if (
            not isinstance(ad_key_double_click_ms, int)
            or isinstance(ad_key_double_click_ms, bool)
            or ad_key_double_click_ms < 100
            or ad_key_double_click_ms > 1000
            or ad_key_double_click_ms % 10
        ):
            raise ConfigError(
                "'ad_key.double_click_ms' must be a 10ms multiple "
                "within 100..1000"
            )

        digital_key_double_click_ms = digital_key_raw.get(
            "double_click_ms", 350
        )
        if (
            not isinstance(digital_key_double_click_ms, int)
            or isinstance(digital_key_double_click_ms, bool)
            or digital_key_double_click_ms < 100
            or digital_key_double_click_ms > 1000
            or digital_key_double_click_ms % 10
        ):
            raise ConfigError(
                "'digital_key.double_click_ms' must be a 10ms multiple "
                "within 100..1000"
            )
        digital_keys_raw = digital_key_raw.get("keys", [])
        if not isinstance(digital_keys_raw, list):
            raise ConfigError("'digital_key.keys' must be an array")
        digital_keys: list[DigitalKeyActionConfig] = []
        for item in digital_keys_raw:
            if not isinstance(item, dict):
                raise ConfigError(
                    "'digital_key.keys' entries must be objects"
                )
            _reject_unknown_keys(
                item,
                NESTED_KEYS["digital_key.keys[]"],
                "digital_key.keys[]",
            )
            name = _require_str(item, "name").upper()
            if name not in ("KEY1", "KEY2", "KEY3", "KEY4"):
                raise ConfigError(
                    "'digital_key.keys[].name' must be "
                    "KEY1, KEY2, KEY3, or KEY4"
                )
            actions: dict[str, str] = {}
            for field in (
                "short_action",
                "double_action",
                "long_action",
            ):
                action = item.get(field, "none")
                if not isinstance(action, str) or action not in KEY_ACTIONS:
                    raise ConfigError(
                        f"'digital_key.keys[].{field}' must be "
                        + ", ".join(KEY_ACTIONS)
                    )
                actions[field] = action
            if all(action == "none" for action in actions.values()):
                raise ConfigError(
                    f"{name} requires a short, double, or long action"
                )
            digital_keys.append(
                DigitalKeyActionConfig(
                    name=name,
                    short_action=actions["short_action"],
                    double_action=actions["double_action"],
                    long_action=actions["long_action"],
                )
            )
        if len({item.name for item in digital_keys}) != len(digital_keys):
            raise ConfigError("digital key names must be unique")
        if digital_key_enabled:
            if (
                len(digital_keys) < 1
                or len(digital_keys) > 4
                or sorted(item.name for item in digital_keys)
                != [
                    f"KEY{index}"
                    for index in range(1, len(digital_keys) + 1)
                ]
            ):
                raise ConfigError(
                    "enabled digital_key requires contiguous "
                    "KEY1..KEY4 actions"
                )
        elif digital_keys:
            raise ConfigError(
                "'digital_key.keys' requires 'digital_key.enabled=true'"
            )

        slide_switch_active_level = _require_str(
            {
                "active_level": slide_switch_raw.get(
                    "active_level", "low"
                )
            },
            "active_level",
        ).lower()
        slide_switch_pull = _require_str(
            {"pull": slide_switch_raw.get("pull", "up")},
            "pull",
        ).lower()
        zero_battery_disable_pull_wake = slide_switch_raw.get(
            "zero_battery_disable_pull_wake", True
        )
        if not isinstance(zero_battery_disable_pull_wake, bool):
            raise ConfigError(
                "'slide_switch.zero_battery_disable_pull_wake' "
                "must be true or false"
            )
        if slide_switch_enabled and (
            slide_switch_active_level != "low"
            or slide_switch_pull != "up"
        ):
            raise ConfigError(
                "initial slide-switch profile supports only active-low "
                "input with internal pull-up"
            )
        if slide_switch_enabled and not classic_enabled:
            raise ConfigError(
                "initial slide-switch profile requires classic_product"
            )

        encoder_pull = _require_str(
            {"pull": encoder_raw.get("pull", "up")},
            "pull",
        ).lower()
        encoder_filter_us = encoder_raw.get("filter_us", 1000)
        clockwise_increases = encoder_raw.get("clockwise_increases", True)
        encoder_normal_step = encoder_raw.get("normal_step", 1)
        encoder_acceleration_window_ms = encoder_raw.get(
            "acceleration_window_ms", 500
        )
        encoder_acceleration_events = encoder_raw.get(
            "acceleration_events", 3
        )
        encoder_accelerated_step = encoder_raw.get("accelerated_step", 5)
        if encoder_enabled and encoder_pull != "up":
            raise ConfigError(
                "initial encoder profile supports only internal pull-up"
            )
        if (
            not isinstance(encoder_filter_us, int)
            or isinstance(encoder_filter_us, bool)
            or not 125 <= encoder_filter_us <= 10000
        ):
            raise ConfigError("'encoder.filter_us' must be 125..10000")
        if not isinstance(clockwise_increases, bool):
            raise ConfigError(
                "'encoder.clockwise_increases' must be true or false"
            )
        for name, value in (
            ("normal_step", encoder_normal_step),
            ("acceleration_events", encoder_acceleration_events),
            ("accelerated_step", encoder_accelerated_step),
        ):
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or not 1 <= value <= 199
            ):
                raise ConfigError(f"'encoder.{name}' must be 1..199")
        if encoder_accelerated_step < encoder_normal_step:
            raise ConfigError(
                "'encoder.accelerated_step' cannot be less than normal_step"
            )
        if (
            not isinstance(encoder_acceleration_window_ms, int)
            or isinstance(encoder_acceleration_window_ms, bool)
            or encoder_acceleration_window_ms < 10
            or encoder_acceleration_window_ms % 10
        ):
            raise ConfigError(
                "'encoder.acceleration_window_ms' must be a positive "
                "multiple of 10ms"
            )
        if encoder_enabled and not classic_enabled:
            raise ConfigError(
                "initial encoder profile requires classic_product"
            )

        slide_resistor_adc_reference = _require_str(
            {
                "adc_reference": slide_resistor_raw.get(
                    "adc_reference", "vdd"
                )
            },
            "adc_reference",
        ).lower()
        slide_resistor_adc_clock = _require_str(
            {
                "adc_clock": slide_resistor_raw.get(
                    "adc_clock", "fcpu"
                )
            },
            "adc_clock",
        ).lower()
        slide_resistor_discard_samples = slide_resistor_raw.get(
            "discard_samples", 2
        )
        slide_resistor_accumulation_samples = slide_resistor_raw.get(
            "accumulation_samples", 8
        )
        low_gear_adc_sum = slide_resistor_raw.get(
            "low_gear_adc_sum", 31129
        )
        high_gear_adc_sum = slide_resistor_raw.get(
            "high_gear_adc_sum", 1638
        )
        low_gear_at_high_adc = slide_resistor_raw.get(
            "low_gear_at_high_adc", True
        )
        deadband_gears = slide_resistor_raw.get("deadband_gears", 3)
        confirmation_count = slide_resistor_raw.get(
            "confirmation_count", 3
        )
        supply_active_level = _require_str(
            {
                "supply_active_level": slide_resistor_raw.get(
                    "supply_active_level", "high"
                )
            },
            "supply_active_level",
        ).lower()
        if slide_resistor_enabled and (
            slide_resistor_adc_reference != "vdd"
            or slide_resistor_adc_clock != "fcpu"
            or supply_active_level != "high"
        ):
            raise ConfigError(
                "initial slide-resistor profile requires VDD reference, "
                "Fcpu ADC clock, and active-high supply"
            )
        if (
            not isinstance(slide_resistor_discard_samples, int)
            or isinstance(slide_resistor_discard_samples, bool)
            or slide_resistor_discard_samples < 0
        ):
            raise ConfigError(
                "'slide_resistor.discard_samples' must be non-negative"
            )
        if (
            not isinstance(slide_resistor_accumulation_samples, int)
            or isinstance(slide_resistor_accumulation_samples, bool)
            or slide_resistor_accumulation_samples not in (1, 2, 4, 8, 16)
        ):
            raise ConfigError(
                "'slide_resistor.accumulation_samples' must be "
                "1, 2, 4, 8, or 16"
            )
        if slide_resistor_enabled and (
            slide_resistor_discard_samples != 2
            or slide_resistor_accumulation_samples != 8
        ):
            raise ConfigError(
                "initial slide-resistor profile requires 2 discarded "
                "samples and an 8-sample sum"
            )
        maximum_slider_sum = (
            4095 * slide_resistor_accumulation_samples
        )
        if (
            not isinstance(low_gear_adc_sum, int)
            or isinstance(low_gear_adc_sum, bool)
            or not isinstance(high_gear_adc_sum, int)
            or isinstance(high_gear_adc_sum, bool)
            or not 0 <= low_gear_adc_sum <= maximum_slider_sum
            or not 0 <= high_gear_adc_sum <= maximum_slider_sum
            or low_gear_adc_sum == high_gear_adc_sum
        ):
            raise ConfigError(
                "slide-resistor endpoints must be different values within "
                "0..4095 * accumulation_samples"
            )
        if not isinstance(low_gear_at_high_adc, bool):
            raise ConfigError(
                "'slide_resistor.low_gear_at_high_adc' must be true or false"
            )
        if slide_resistor_enabled and (
            low_gear_at_high_adc
            != (low_gear_adc_sum > high_gear_adc_sum)
        ):
            raise ConfigError(
                "'slide_resistor.low_gear_at_high_adc' does not match "
                "the configured endpoint values"
            )
        for name, value, maximum in (
            ("deadband_gears", deadband_gears, 199),
            ("confirmation_count", confirmation_count, 255),
        ):
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or not 1 <= value <= maximum
            ):
                raise ConfigError(
                    f"'slide_resistor.{name}' must be 1..{maximum}"
                )
        if slide_resistor_enabled and not classic_enabled:
            raise ConfigError(
                "initial slide-resistor profile requires classic_product"
            )

        motor_kind = _require_str(motor, "kind")
        if motor_kind not in (
            "brushless_fixed_duty",
            "brushed_fixed_duty",
            "brushless_fixed_voltage_7_3",
            "brushed_brushless_compat_fixed_voltage_7_3",
        ):
            raise ConfigError(
                "'motor.kind' must be brushless_fixed_duty or "
                "brushed_fixed_duty or "
                "brushless_fixed_voltage_7_3 or "
                "brushed_brushless_compat_fixed_voltage_7_3"
            )
        fixed_voltage_kind = motor_kind in (
            "brushless_fixed_voltage_7_3",
            "brushed_brushless_compat_fixed_voltage_7_3",
        )
        if motor_kind == "brushed_fixed_duty" and not classic_enabled:
            raise ConfigError(
                "pure brushed motor currently requires classic_product"
            )
        if fixed_voltage_kind and interrupt_us != 100:
            raise ConfigError(
                "fixed-voltage 7+3 motor kinds require a 100us T1 interrupt"
            )
        pwm_frequency_hz = _require_int(motor, "pwm_frequency_hz")
        if pwm_frequency_hz <= 0:
            raise ConfigError("'pwm_frequency_hz' must be positive")
        pwm_clock_source = _require_str(motor, "pwm_clock_source").lower()
        if pwm_clock_source not in ("fosc", "fcpu_div2"):
            raise ConfigError("'pwm_clock_source' must be 'fosc' or 'fcpu_div2'")
        pwm_prescaler_raw = motor.get("pwm_prescaler", "auto")
        valid_pwm_dividers = (1, 2, 4, 8, 16, 32, 64, 128)
        if pwm_prescaler_raw == "auto":
            pwm_prescaler = None
        elif (
            isinstance(pwm_prescaler_raw, int)
            and pwm_prescaler_raw in valid_pwm_dividers
        ):
            pwm_prescaler = pwm_prescaler_raw
        else:
            raise ConfigError(
                "'pwm_prescaler' must be auto or one of 1,2,4,8,16,32,64,128"
            )
        run_duty_percent = None
        if motor_kind in (
            "brushless_fixed_duty",
            "brushed_fixed_duty",
        ):
            run_duty_percent = _require_int(motor, "run_duty_percent")
            if not 1 <= run_duty_percent <= 99:
                raise ConfigError("'run_duty_percent' must be between 1 and 99")
        duty_curve_raw = motor.get("duty_curve")
        duty_base_count = None
        duty_gear_divisor = None
        if duty_curve_raw is not None:
            if not isinstance(duty_curve_raw, dict):
                raise ConfigError("'motor.duty_curve' must be an object")
            _reject_unknown_keys(
                duty_curve_raw,
                NESTED_KEYS["motor.duty_curve"],
                "motor.duty_curve",
            )
            duty_base_count = _require_int(duty_curve_raw, "base_count")
            duty_gear_divisor = _require_int(duty_curve_raw, "gear_divisor")
            if duty_base_count < 0:
                raise ConfigError("'base_count' cannot be negative")
            if duty_gear_divisor <= 0:
                raise ConfigError("'gear_divisor' must be positive")

        voltage_target_base = None
        voltage_target_step = None
        voltage_target_max = None
        voltage_target_mode = None
        voltage_target_calibration_offset_mv = None
        voltage_target_min_mv = None
        voltage_target_step_mv = None
        voltage_target_max_mv = None
        voltage_measurement_multiplier = None
        voltage_error_window = None
        voltage_pwm_min_count = None
        voltage_pwm_max_count = None
        voltage_slow_adjust_ms = None
        raw_voltage_target_base = None
        raw_voltage_target_step = None
        raw_voltage_target_max = None
        raw_voltage_target_offset_mv = 0
        if fixed_voltage_kind:
            voltage_curve = _require_dict(motor, "voltage_curve")
            _reject_unknown_keys(
                voltage_curve,
                NESTED_KEYS["motor.voltage_curve"],
                "motor.voltage_curve",
            )
            voltage_target_mode = voltage_curve.get("target_mode", "raw_adc")
            if voltage_target_mode not in ("raw_adc", "physical_voltage"):
                raise ConfigError(
                    "'target_mode' must be raw_adc or physical_voltage"
                )
            raw_fields = {
                "target_adc_base",
                "target_adc_step",
                "target_adc_max",
            }
            physical_fields = {
                "target_voltage_min_mv",
                "target_voltage_step_mv",
                "target_voltage_max_mv",
            }
            if voltage_target_mode == "raw_adc":
                if any(field in voltage_curve for field in physical_fields):
                    raise ConfigError(
                        "raw_adc target mode cannot define physical-voltage "
                        "target fields"
                    )
                raw_voltage_target_base = _require_int(
                    voltage_curve, "target_adc_base"
                )
                raw_voltage_target_step = _require_int(
                    voltage_curve, "target_adc_step"
                )
                raw_voltage_target_max = _require_int(
                    voltage_curve, "target_adc_max"
                )
                raw_voltage_target_offset_mv = voltage_curve.get(
                    "target_calibration_offset_mv", 0
                )
            else:
                if any(field in voltage_curve for field in raw_fields):
                    raise ConfigError(
                        "physical_voltage target mode cannot define raw ADC "
                        "target fields"
                    )
                voltage_target_min_mv = _require_int(
                    voltage_curve, "target_voltage_min_mv"
                )
                voltage_target_step_mv = _require_int(
                    voltage_curve, "target_voltage_step_mv"
                )
                voltage_target_max_mv = _require_int(
                    voltage_curve, "target_voltage_max_mv"
                )
                raw_voltage_target_offset_mv = _require_int(
                    voltage_curve, "target_calibration_offset_mv"
                )
            if (
                not isinstance(raw_voltage_target_offset_mv, int)
                or isinstance(raw_voltage_target_offset_mv, bool)
            ):
                raise ConfigError(
                    "'target_calibration_offset_mv' must be an integer"
                )
            if raw_voltage_target_offset_mv < 0:
                raise ConfigError(
                    "'target_calibration_offset_mv' cannot be negative"
                )
            voltage_measurement_multiplier = _require_int(
                voltage_curve, "measurement_multiplier"
            )
            voltage_error_window = _require_int(
                voltage_curve, "error_window_adc"
            )
            voltage_pwm_min_count = _require_int(
                voltage_curve, "pwm_min_count"
            )
            voltage_pwm_max_count = _require_int(
                voltage_curve, "pwm_max_count"
            )
            voltage_slow_adjust_ms = voltage_curve.get("slow_adjust_ms", 0)
            if (
                not isinstance(voltage_slow_adjust_ms, int)
                or isinstance(voltage_slow_adjust_ms, bool)
            ):
                raise ConfigError("'slow_adjust_ms' must be an integer")
            if voltage_slow_adjust_ms == 0:
                voltage_slow_adjust_ms = None
            elif voltage_slow_adjust_ms < 10 or voltage_slow_adjust_ms % 10:
                raise ConfigError(
                    "'slow_adjust_ms' must be 0 or a positive 10ms multiple"
                )
            if voltage_target_mode == "raw_adc" and (
                raw_voltage_target_base < 1
                or raw_voltage_target_step < 1
                or raw_voltage_target_max < raw_voltage_target_base
            ):
                raise ConfigError("fixed-voltage ADC targets must be positive")
            if voltage_target_mode == "physical_voltage" and (
                voltage_target_min_mv < 1
                or voltage_target_step_mv < 1
                or voltage_target_max_mv <= voltage_target_min_mv
            ):
                raise ConfigError(
                    "physical fixed-voltage targets must be increasing"
                )
            if voltage_measurement_multiplier not in (1, 2, 4):
                raise ConfigError(
                    "'measurement_multiplier' must be 1, 2, or 4"
                )
            if voltage_error_window < 1:
                raise ConfigError("'error_window_adc' must be positive")
            if not 1 <= voltage_pwm_min_count < voltage_pwm_max_count:
                raise ConfigError(
                    "fixed-voltage PWM min/max counts are invalid"
                )

        brushed_pwm_frequency_hz = None
        brushed_duty_base_count = None
        brushed_duty_gear_divisor = None
        detection_samples = None
        detection_high_threshold = None
        if motor_kind == "brushed_brushless_compat_fixed_voltage_7_3":
            brushed = _require_dict(motor, "brushed")
            detection = _require_dict(motor, "detection")
            _reject_unknown_keys(
                brushed,
                NESTED_KEYS["motor.brushed"],
                "motor.brushed",
            )
            _reject_unknown_keys(
                detection,
                NESTED_KEYS["motor.detection"],
                "motor.detection",
            )
            brushed_pwm_frequency_hz = _require_int(
                brushed, "pwm_frequency_hz"
            )
            brushed_duty_base_count = _require_int(
                brushed, "duty_base_count"
            )
            brushed_duty_gear_divisor = _require_int(
                brushed, "duty_gear_divisor"
            )
            detection_samples = _require_int(detection, "samples")
            detection_high_threshold = _require_int(
                detection, "high_threshold"
            )
            if brushed_pwm_frequency_hz <= 0:
                raise ConfigError("brushed PWM frequency must be positive")
            if brushed_duty_base_count < 0:
                raise ConfigError("brushed duty base cannot be negative")
            if brushed_duty_gear_divisor <= 0:
                raise ConfigError("brushed duty divisor must be positive")
            if not 1 <= detection_samples <= 20:
                raise ConfigError("motor detection samples must be 1..20")
            if not 1 <= detection_high_threshold <= detection_samples:
                raise ConfigError(
                    "motor detection high threshold must be within samples"
                )

        protection_enabled = _require_bool(protection, "enabled")
        if motor_kind == "brushed_fixed_duty" and protection_enabled:
            raise ConfigError(
                "pure brushed motor must disable fan voltage protection"
            )
        if motor_kind != "brushed_fixed_duty" and not protection_enabled:
            raise ConfigError(
                "brushless generation requires fan voltage protection"
            )
        if not protection_enabled:
            protection = {
                "enabled": False,
                "adc_reference": "2v",
                "adc_clock": "fcpu",
                "discard_samples": 2,
                "average_samples": 8,
                "overvoltage_adc_threshold": 4095,
                "consecutive_confirmations": 13,
            }
        adc_reference = _require_str(protection, "adc_reference").lower()
        if adc_reference not in ("2v", "3v", "4v", "vdd"):
            raise ConfigError(
                "'adc_reference' must be 2v, 3v, 4v, or vdd"
            )
        adc_clock = _require_str(protection, "adc_clock").lower()
        if adc_clock not in ("fcpu", "fcpu_div2", "fcpu_div8", "fcpu_div16"):
            raise ConfigError(
                "'adc_clock' must be fcpu, fcpu_div2, fcpu_div8, or fcpu_div16"
            )
        discard_samples = _require_int(protection, "discard_samples")
        average_samples = _require_int(protection, "average_samples")
        if discard_samples < 0:
            raise ConfigError("'discard_samples' cannot be negative")
        if average_samples < 1 or average_samples > 16:
            raise ConfigError("'average_samples' must be between 1 and 16")
        if average_samples & (average_samples - 1):
            raise ConfigError(
                "version 0.4 requires 'average_samples' to be a power of two"
            )
        max_sum = 4095 * average_samples
        if max_sum > 65535:
            raise ConfigError(
                "ADC accumulation would overflow u16; reduce 'average_samples'"
            )
        overvoltage_voltage_mv = None
        divider_high_ohm = None
        divider_low_ohm = None
        overvoltage_limit = protection.get("overvoltage_limit")
        if overvoltage_limit is not None:
            if not isinstance(overvoltage_limit, dict):
                raise ConfigError("'overvoltage_limit' must be an object")
            _reject_unknown_keys(
                overvoltage_limit,
                NESTED_KEYS[
                    "fan_voltage_protection.overvoltage_limit"
                ],
                "fan_voltage_protection.overvoltage_limit",
            )
            overvoltage_voltage_mv = _require_int(
                overvoltage_limit, "voltage_mv"
            )
            divider_high_ohm = _require_int(
                overvoltage_limit, "divider_high_ohm"
            )
            divider_low_ohm = _require_int(
                overvoltage_limit, "divider_low_ohm"
            )
            overvoltage_adc_reference = _require_str(
                overvoltage_limit, "adc_reference"
            ).lower()
            if overvoltage_voltage_mv <= 0:
                raise ConfigError(
                    "'overvoltage_limit.voltage_mv' must be positive"
                )
            if divider_high_ohm <= 0 or divider_low_ohm <= 0:
                raise ConfigError(
                    "overvoltage divider resistors must be positive"
                )
            if overvoltage_adc_reference not in ADC_FIXED_REFERENCE_MV:
                raise ConfigError(
                    "physical overvoltage protection requires a fixed "
                    "2v, 3v, or 4v ADC reference"
                )
            numerator = (
                overvoltage_voltage_mv * divider_low_ohm * 4095
            )
            denominator = (
                (divider_high_ohm + divider_low_ohm)
                * ADC_FIXED_REFERENCE_MV[overvoltage_adc_reference]
            )
            overvoltage_adc_threshold = (
                numerator + denominator // 2
            ) // denominator
        else:
            overvoltage_adc_reference = adc_reference
            overvoltage_adc_threshold = _require_int(
                protection, "overvoltage_adc_threshold"
            )
        if overvoltage_adc_reference != adc_reference:
            raise ConfigError(
                "AD_FAN regulation and overvoltage protection must use the "
                "same ADC reference"
            )
        if not 1 <= overvoltage_adc_threshold <= 4095:
            raise ConfigError(
                "calculated overvoltage ADC threshold must be between 1 and "
                "4095; check voltage, divider, and ADC reference"
            )
        consecutive_confirmations = _require_int(
            protection, "consecutive_confirmations"
        )
        if not 2 <= consecutive_confirmations <= 255:
            raise ConfigError(
                "'consecutive_confirmations' must be between 2 and 255; single-result shutdown is forbidden"
            )

        if fixed_voltage_kind:
            if (
                divider_high_ohm is None
                or divider_low_ohm is None
                or adc_reference == "vdd"
            ):
                if raw_voltage_target_offset_mv:
                    raise ConfigError(
                        "fixed-voltage target calibration requires the same "
                        "fixed-reference divider metadata as AD_FAN"
                    )
                if voltage_target_mode == "physical_voltage":
                    raise ConfigError(
                        "physical fixed-voltage targets require a fixed ADC "
                        "reference and divider metadata"
                    )
            if voltage_target_mode == "raw_adc":
                voltage_target_base = raw_voltage_target_base
                voltage_target_step = raw_voltage_target_step
                voltage_target_max = raw_voltage_target_max
                if raw_voltage_target_offset_mv:
                    offset_adc = _voltage_target_adc(
                        raw_voltage_target_offset_mv,
                        adc_reference,
                        divider_high_ohm,
                        divider_low_ohm,
                        voltage_measurement_multiplier,
                    )
                    voltage_target_base += offset_adc
                    voltage_target_max += offset_adc
            else:
                target_offset = raw_voltage_target_offset_mv
                voltage_target_base = _voltage_target_adc(
                    voltage_target_min_mv + target_offset,
                    adc_reference,
                    divider_high_ohm,
                    divider_low_ohm,
                    voltage_measurement_multiplier,
                )
                voltage_target_step = _voltage_target_adc(
                    voltage_target_step_mv,
                    adc_reference,
                    divider_high_ohm,
                    divider_low_ohm,
                    voltage_measurement_multiplier,
                )
                voltage_target_max = _voltage_target_adc(
                    voltage_target_max_mv + target_offset,
                    adc_reference,
                    divider_high_ohm,
                    divider_low_ohm,
                    voltage_measurement_multiplier,
                )
            max_measured_adc = 4095 * voltage_measurement_multiplier
            if not 1 <= voltage_target_base <= max_measured_adc:
                raise ConfigError(
                    "fixed-voltage minimum target must fit the measured ADC "
                    "range"
                )
            if not 1 <= voltage_target_step <= max_measured_adc:
                raise ConfigError(
                    "fixed-voltage target step must fit the measured ADC "
                    "range"
                )
            if not 1 <= voltage_target_max <= max_measured_adc:
                raise ConfigError(
                    "fixed-voltage maximum target must fit the measured ADC "
                    "range"
                )
            if voltage_target_max < voltage_target_base:
                raise ConfigError(
                    "fixed-voltage maximum target must not be below minimum"
                )

        battery_curve = None
        battery_business_enabled = False
        battery_business_raw = battery_monitor_raw.get("business")
        if battery_business_raw is not None:
            if not isinstance(battery_business_raw, dict):
                raise ConfigError("'battery_monitor.business' must be an object")
            _reject_unknown_keys(
                battery_business_raw,
                NESTED_KEYS["battery_monitor.business"],
                "battery_monitor.business",
            )
            battery_business_enabled = _require_bool(
                battery_business_raw, "enabled"
            )
        if battery_business_enabled:
            thresholds = _require_dict(battery_business_raw, "thresholds")
            compensation = _require_dict(battery_business_raw, "compensation")
            timing = _require_dict(battery_business_raw, "timing_ms")
            _reject_unknown_keys(
                thresholds,
                NESTED_KEYS["battery_monitor.business.thresholds"],
                "battery_monitor.business.thresholds",
            )
            _reject_unknown_keys(
                compensation,
                NESTED_KEYS["battery_monitor.business.compensation"],
                "battery_monitor.business.compensation",
            )
            _reject_unknown_keys(
                timing,
                NESTED_KEYS["battery_monitor.business.timing_ms"],
                "battery_monitor.business.timing_ms",
            )
            threshold_values = tuple(
                _require_int(thresholds, name)
                for name in (
                    "zero_shutdown",
                    "low",
                    "p0",
                    "p5",
                    "p10",
                    "p50",
                    "p80",
                    "p100",
                )
            )
            (
                zero_shutdown,
                low_threshold,
                adc_0,
                adc_5,
                adc_10,
                adc_50,
                adc_80,
                adc_100,
            ) = threshold_values
            if not (
                0 < zero_shutdown <= adc_0 < adc_5 < adc_10
                < adc_50 < adc_80 < adc_100 <= 65535
            ):
                raise ConfigError(
                    "battery thresholds must be monotonic: "
                    "zero<=p0<p5<p10<p50<p80<p100"
                )
            if not zero_shutdown < low_threshold < adc_100:
                raise ConfigError(
                    "battery low threshold must be between zero and p100"
                )
            fan_compensation_raw = _require_int_tuple(
                compensation, "fan_segments"
            )
            if len(fan_compensation_raw) != 5 or any(
                item < 0 for item in fan_compensation_raw
            ):
                raise ConfigError(
                    "'fan_segments' must contain five non-negative values"
                )
            brushed_fan_compensation = None
            brushed_compensation_raw = compensation.get(
                "brushed_fan_segments"
            )
            if brushed_compensation_raw is not None:
                if (
                    not isinstance(brushed_compensation_raw, list)
                    or len(brushed_compensation_raw) != 5
                    or any(
                        not isinstance(item, int)
                        or isinstance(item, bool)
                        or item < 0
                        for item in brushed_compensation_raw
                    )
                ):
                    raise ConfigError(
                        "'brushed_fan_segments' must contain five "
                        "non-negative integers"
                    )
                brushed_fan_compensation = tuple(brushed_compensation_raw)
            if (
                motor_kind
                == "brushed_brushless_compat_fixed_voltage_7_3"
                and brushed_fan_compensation is None
            ):
                raise ConfigError(
                    "compatible motor battery logic requires "
                    "'brushed_fan_segments'"
                )
            cooling_compensation = _require_int(compensation, "cooling")
            if cooling_compensation < 0:
                raise ConfigError("'cooling' compensation cannot be negative")
            brushed_cooling_compensation = compensation.get(
                "brushed_cooling"
            )
            if brushed_cooling_compensation is not None and (
                not isinstance(brushed_cooling_compensation, int)
                or isinstance(brushed_cooling_compensation, bool)
                or brushed_cooling_compensation < 0
            ):
                raise ConfigError(
                    "'brushed_cooling' compensation must be non-negative"
                )
            if (
                motor_kind
                == "brushed_brushless_compat_fixed_voltage_7_3"
                and brushed_cooling_compensation is None
            ):
                raise ConfigError(
                    "compatible motor battery logic requires "
                    "'brushed_cooling'"
                )
            timing_values = tuple(
                _require_int(timing, name)
                for name in (
                    "charge_active",
                    "charge_full",
                    "discharge",
                    "low_discharge",
                )
            )
            if any(item <= 0 for item in timing_values):
                raise ConfigError("battery timing values must be positive")
            battery_curve = BatteryCurveConfig(
                zero_shutdown=zero_shutdown,
                low_threshold=low_threshold,
                adc_0=adc_0,
                adc_5=adc_5,
                adc_10=adc_10,
                adc_50=adc_50,
                adc_80=adc_80,
                adc_100=adc_100,
                fan_compensation=fan_compensation_raw,
                brushed_fan_compensation=brushed_fan_compensation,
                cooling_compensation=cooling_compensation,
                brushed_cooling_compensation=(
                    brushed_cooling_compensation
                ),
                charge_active_period_ms=timing_values[0],
                charge_full_period_ms=timing_values[1],
                discharge_period_ms=timing_values[2],
                low_discharge_period_ms=timing_values[3],
            )

        if classic_enabled:
            if not battery_monitor_enabled or not battery_business_enabled:
                raise ConfigError(
                    "classic_product requires battery_monitor business logic"
                )
            input_kind = classic_input_kind
            digital_input_kinds = (
                "two_digital_keys_active_low",
                "digital_keys_active_low",
            )
            if (
                input_kind in digital_input_kinds
                and (
                    ad_key_enabled
                    or encoder_enabled
                    or slide_resistor_enabled
                )
            ):
                raise ConfigError(
                    "digital classic input cannot also enable AD_KEY, "
                    "encoder, or slide resistor"
                )
            if input_kind == "two_digital_keys_active_low":
                if digital_key_enabled and sorted(
                    item.name for item in digital_keys
                ) != ["KEY1", "KEY2"]:
                    raise ConfigError(
                        "legacy two-digital-key input requires "
                        "KEY1 and KEY2 actions"
                    )
            elif input_kind == "digital_keys_active_low":
                if not digital_key_enabled:
                    raise ConfigError(
                        "digital_keys_active_low input requires "
                        "digital_key.enabled=true"
                    )
            if input_kind in digital_input_kinds and digital_key_enabled:
                for item in digital_keys:
                    actions = (
                        item.short_action,
                        item.double_action,
                        item.long_action,
                    )
                    if "cooling_toggle" in actions and not cooling_enabled:
                        raise ConfigError(
                            "cooling_toggle requires cooling_enabled=true"
                        )
                    if (
                        "cooling_toggle" in actions
                        and cooling_control_mode
                        != "toggle_while_fan_on"
                    ):
                        raise ConfigError(
                            "cooling_toggle requires "
                            "cooling.control_mode=toggle_while_fan_on"
                        )
                    if "light_cycle" in actions and not light_enabled:
                        raise ConfigError(
                            "light_cycle requires light.enabled=true"
                        )
                    if "atomizer_toggle" in actions and not atomizer_enabled:
                        raise ConfigError(
                            "atomizer_toggle requires "
                            "atomizer.enabled=true"
                        )
            elif digital_key_enabled:
                raise ConfigError(
                    "digital_key requires "
                    "two_digital_keys_active_low or "
                    "digital_keys_active_low input"
                )
            if (
                input_kind in ad_key_input_kinds
                and not ad_key_enabled
            ):
                raise ConfigError(
                    "AD classic input requires 'ad_key.enabled=true'"
                )
            if input_kind == "two_ad_keys_active_low_ranges" and (
                sorted(item.name for item in key_bands) != ["KEY1", "KEY2"]
            ):
                raise ConfigError(
                    "initial AD classic input requires KEY1 and KEY2 ranges"
                )
            if (
                input_kind == "two_ad_keys_active_low_ranges"
                and any(
                    item.short_action or item.long_action
                    for item in key_bands
                )
            ):
                raise ConfigError(
                    "legacy two-key AD input keeps fixed actions; use "
                    "ad_keys_active_low_ranges to configure key actions"
                )
            if (
                input_kind == "ad_keys_active_low_ranges"
                and (
                    len(key_bands) < 1
                    or len(key_bands) > 4
                    or sorted(item.name for item in key_bands)
                    != [f"KEY{index}" for index in range(1, len(key_bands) + 1)]
                )
            ):
                raise ConfigError(
                    "general AD classic input requires contiguous "
                    "KEY1..KEY4 ranges"
                )
            if (
                input_kind in ad_key_input_kinds
                and (encoder_enabled or slide_resistor_enabled)
            ):
                raise ConfigError(
                    "AD classic input cannot also enable encoder or "
                    "slide resistor"
                )
            if (
                input_kind == "rotary_encoder_active_low"
                and not encoder_enabled
            ):
                raise ConfigError(
                    "rotary classic input requires 'encoder.enabled=true'"
                )
            if (
                input_kind != "rotary_encoder_active_low"
                and encoder_enabled
            ):
                raise ConfigError(
                    "enabled encoder requires rotary_encoder_active_low input"
                )
            if (
                input_kind == "rotary_encoder_active_low"
                and not slide_switch_enabled
            ):
                raise ConfigError(
                    "initial rotary encoder profile requires slide_switch"
                )
            if (
                input_kind == "single_key_slide_resistor_active_low"
                and not slide_resistor_enabled
            ):
                raise ConfigError(
                    "slide-resistor classic input requires "
                    "'slide_resistor.enabled=true'"
                )
            if (
                input_kind != "single_key_slide_resistor_active_low"
                and slide_resistor_enabled
            ):
                raise ConfigError(
                    "enabled slide resistor requires "
                    "single_key_slide_resistor_active_low input"
                )
            if (
                input_kind == "single_key_slide_resistor_active_low"
                and (slide_switch_enabled or encoder_enabled or ad_key_enabled)
            ):
                raise ConfigError(
                    "initial slide-resistor profile cannot combine "
                    "slide switch, encoder, or AD keys"
                )
            continuous_input_kinds = (
                "rotary_encoder_active_low",
                "single_key_slide_resistor_active_low",
            )
            gear_range_raw = classic_raw.get("gear_range")
            if input_kind in continuous_input_kinds:
                gear_mode = "continuous"
                if gear_range_raw is not None:
                    if not isinstance(gear_range_raw, dict):
                        raise ConfigError("'gear_range' must be an object")
                    _reject_unknown_keys(
                        gear_range_raw,
                        NESTED_KEYS["classic_product.gear_range"],
                        "classic_product.gear_range",
                    )
                    if "gear_steps" in classic_raw:
                        raise ConfigError(
                            "continuous inputs must use 'gear_range', not both "
                            "'gear_range' and 'gear_steps'"
                        )
                    minimum_gear = _require_int(
                        gear_range_raw, "minimum"
                    )
                    maximum_gear = _require_int(
                        gear_range_raw, "maximum"
                    )
                elif "gear_steps" in classic_raw:
                    # Backward compatibility: old continuous profiles used
                    # only the first and last entries of gear_steps.
                    legacy_gear_steps = _require_int_tuple(
                        classic_raw, "gear_steps"
                    )
                    if (
                        legacy_gear_steps[0] < 1
                        or legacy_gear_steps[-1] > 199
                        or any(
                            left >= right
                            for left, right in zip(
                                legacy_gear_steps,
                                legacy_gear_steps[1:],
                            )
                        )
                    ):
                        raise ConfigError(
                            "legacy continuous 'gear_steps' must be "
                            "strictly increasing within 1..199"
                        )
                    minimum_gear = legacy_gear_steps[0]
                    maximum_gear = legacy_gear_steps[-1]
                else:
                    raise ConfigError(
                        "continuous encoder/slide-resistor input requires "
                        "'gear_range'"
                    )
                if not 1 <= minimum_gear < maximum_gear <= 199:
                    raise ConfigError(
                        "'gear_range' must satisfy "
                        "1 <= minimum < maximum <= 199"
                    )
                gear_steps = (minimum_gear, maximum_gear)
            else:
                if gear_range_raw is not None:
                    raise ConfigError(
                        "discrete key inputs must use 'gear_steps', "
                        "not 'gear_range'"
                    )
                gear_mode = "configured_steps"
                gear_steps = _require_int_tuple(classic_raw, "gear_steps")
                if (
                    gear_steps[0] < 1
                    or gear_steps[-1] > 199
                    or any(
                        left >= right
                        for left, right in zip(
                            gear_steps, gear_steps[1:]
                        )
                    )
                ):
                    raise ConfigError(
                        "'gear_steps' must be strictly increasing "
                        "within 1..199"
                    )
                minimum_gear = gear_steps[0]
                maximum_gear = gear_steps[-1]
            long_adjust = _require_bool(classic_raw, "long_adjust")
            if digital_key_enabled and any(
                item.long_action in ("fan_step_up", "fan_step_down")
                for item in digital_keys
            ) and not long_adjust:
                raise ConfigError(
                    "continuous digital key long adjustment requires "
                    "long_adjust=true"
                )
            if (
                input_kind == "rotary_encoder_active_low"
                and long_adjust
            ):
                raise ConfigError(
                    "rotary encoder profile requires long_adjust=false"
                )
            if (
                input_kind == "single_key_slide_resistor_active_low"
                and long_adjust
            ):
                raise ConfigError(
                    "slide-resistor profile requires long_adjust=false"
                )
            if input_kind in ad_key_input_kinds:
                resolved_key_bands: list[AdKeyBandConfig] = []
                for item in key_bands:
                    short_action = item.short_action
                    double_action = item.double_action
                    long_action = item.long_action
                    if not short_action:
                        if item.name == "KEY1":
                            short_action = "fan_cycle"
                        elif (
                            item.name == "KEY2"
                            and cooling_enabled
                            and cooling_control_mode
                            == "toggle_while_fan_on"
                        ):
                            short_action = "cooling_toggle"
                        else:
                            short_action = "none"
                    if not long_action:
                        if item.name == "KEY1" and long_adjust:
                            long_action = "fan_step_up"
                        elif item.name == "KEY2" and long_adjust:
                            long_action = "fan_step_down"
                        else:
                            long_action = "none"
                    if not double_action:
                        double_action = "none"
                    if (
                        item.name in ("KEY3", "KEY4")
                        and short_action == "none"
                        and double_action == "none"
                        and long_action == "none"
                    ):
                        raise ConfigError(
                            f"{item.name} requires an explicit short_action, "
                            "double_action, or long_action"
                        )
                    if (
                        "cooling_toggle"
                        in (short_action, double_action, long_action)
                        and not cooling_enabled
                    ):
                        raise ConfigError(
                            "cooling_toggle requires cooling_enabled=true"
                        )
                    if (
                        "cooling_toggle"
                        in (short_action, double_action, long_action)
                        and cooling_control_mode != "toggle_while_fan_on"
                    ):
                        raise ConfigError(
                            "cooling_toggle requires "
                            "cooling.control_mode=toggle_while_fan_on"
                        )
                    if (
                        "light_cycle"
                        in (short_action, double_action, long_action)
                        and not light_enabled
                    ):
                        raise ConfigError(
                            "light_cycle requires light.enabled=true"
                        )
                    if (
                        "atomizer_toggle"
                        in (short_action, double_action, long_action)
                        and not atomizer_enabled
                    ):
                        raise ConfigError(
                            "atomizer_toggle requires "
                            "atomizer.enabled=true"
                        )
                    if (
                        long_action in ("fan_step_up", "fan_step_down")
                        and not long_adjust
                    ):
                        raise ConfigError(
                            "continuous AD key long adjustment requires "
                            "long_adjust=true"
                        )
                    resolved_key_bands.append(
                        AdKeyBandConfig(
                            name=item.name,
                            minimum_adc=item.minimum_adc,
                            maximum_adc=item.maximum_adc,
                            short_action=short_action,
                            double_action=double_action,
                            long_action=long_action,
                        )
                    )
                key_bands = resolved_key_bands
            action_keys = (
                key_bands
                if input_kind in ad_key_input_kinds
                else digital_keys
                if digital_key_enabled
                else []
            )
            if (
                light_enabled
                and light_mode_profile in ("on_off", "on_off_flash")
                and not any(
                    item.short_action == "light_cycle"
                    for item in action_keys
                )
            ):
                raise ConfigError(
                    "independent light mode requires a key with "
                    "short_action=light_cycle"
                )
            if atomizer_enabled and not any(
                "atomizer_toggle"
                in (
                    item.short_action,
                    item.double_action,
                    item.long_action,
                )
                for item in action_keys
            ):
                raise ConfigError(
                    "atomizer requires a key action mapped to "
                    "atomizer_toggle"
                )
            charge_max_gear = _require_int(classic_raw, "charge_max_gear")
            if gear_mode == "configured_steps":
                if charge_max_gear not in gear_steps:
                    raise ConfigError(
                        "'charge_max_gear' must be one of the configured "
                        "gear steps"
                    )
            elif not minimum_gear <= charge_max_gear <= maximum_gear:
                raise ConfigError(
                    "'charge_max_gear' must be inside 'gear_range'"
                )
            if slide_resistor_enabled:
                slider_range = abs(low_gear_adc_sum - high_gear_adc_sum)
                slider_gear_count = maximum_gear - minimum_gear
                if slider_gear_count < 1:
                    raise ConfigError(
                        "slide-resistor gear range must contain at least "
                        "two values"
                    )
                slider_step = slider_range // slider_gear_count
                if slider_step < 1:
                    raise ConfigError(
                        "slide-resistor ADC endpoint range is too small"
                    )
                if slider_step * deadband_gears > slider_range:
                    raise ConfigError(
                        "slide-resistor deadband exceeds the ADC range"
                    )
            if encoder_enabled and (
                encoder_normal_step > maximum_gear - minimum_gear
                or encoder_accelerated_step > maximum_gear - minimum_gear
            ):
                raise ConfigError(
                    "encoder step cannot exceed the configured gear range"
                )
            display_hardware = display_profile
            display_policy = display_behavior_profile
            low_blink_target = _require_str(classic_raw, "low_blink_target")
            if low_blink_target not in ("last_digit", "both_digits"):
                raise ConfigError(
                    "'low_blink_target' must be last_digit or both_digits"
                )
            charge_blink_target = _require_str(
                classic_raw, "charge_blink_target"
            )
            if charge_blink_target not in (
                "last_digit",
                "percent_icon",
                "charge_icon",
            ):
                raise ConfigError(
                    "'charge_blink_target' must be last_digit, percent_icon, "
                    "or charge_icon"
                )
            mapped_display_signals = {
                item.signal for item in display_connections
            }
            if (
                charge_blink_target == "percent_icon"
                and "icon.percent" not in mapped_display_signals
            ):
                raise ConfigError(
                    "percent_icon charging blink requires icon.percent in "
                    "the display mapping"
                )
            if (
                charge_blink_target == "charge_icon"
                and "icon.charge" not in mapped_display_signals
            ):
                raise ConfigError(
                    "charge_icon charging blink requires icon.charge in "
                    "the display mapping"
                )
            sleep_enabled = _require_bool(classic_raw, "sleep_enabled")
            if (
                motor_kind in (
                    "brushless_fixed_duty",
                    "brushed_fixed_duty",
                )
                and (duty_base_count is None or duty_gear_divisor is None)
            ):
                raise ConfigError(
                    "classic_product requires motor.duty_curve"
                )
        else:
            if digital_key_enabled:
                raise ConfigError(
                    "digital_key requires classic_product.enabled=true"
                )
            input_kind = "none"
            gear_mode = "none"
            gear_steps = ()
            minimum_gear = 0
            maximum_gear = 0
            long_adjust = False
            charging_kind = "none"
            cooling_enabled = False
            charge_max_gear = 0
            display_hardware = "none"
            display_policy = "none"
            low_blink_target = "last_digit"
            charge_blink_target = "last_digit"
            sleep_enabled = False

        self_test_ms = _require_int(project, "self_test_ms")
        if self_test_ms < 0 or self_test_ms % 10:
            raise ConfigError("'self_test_ms' must be a non-negative multiple of 10")
        if self_test_ms // 10 > 255:
            raise ConfigError("'self_test_ms' cannot exceed 2550ms in version 0.4")

        unused_pin_roles = sorted(set(pins) - set(required_pin_roles))
        if unused_pin_roles:
            raise ConfigError(
                "unused or unsupported pin role(s): "
                f"{', '.join(unused_pin_roles)}"
            )

        return cls(
            source_path=source_path,
            schema_version=schema_version,
            project_name=_require_str(project, "name"),
            mcu=McuConfig(
                model=model,
                package=package,
                oscillator_hz=oscillator_hz,
                system_divider=system_divider,
            ),
            timebase=TimebaseConfig(
                interrupt_us=interrupt_us,
                t1_prescaler=t1_prescaler,
            ),
            pins=pin_bindings,
            motor=MotorConfig(
                kind=motor_kind,
                pwm_frequency_hz=pwm_frequency_hz,
                pwm_clock_source=pwm_clock_source,
                pwm_prescaler=pwm_prescaler,
                run_duty_percent=run_duty_percent,
                duty_base_count=duty_base_count,
                duty_gear_divisor=duty_gear_divisor,
                voltage_target_base=voltage_target_base,
                voltage_target_step=voltage_target_step,
                voltage_target_max=voltage_target_max,
                voltage_target_mode=voltage_target_mode,
                voltage_target_calibration_offset_mv=(
                    raw_voltage_target_offset_mv
                    if fixed_voltage_kind
                    else None
                ),
                voltage_target_min_mv=voltage_target_min_mv,
                voltage_target_step_mv=voltage_target_step_mv,
                voltage_target_max_mv=voltage_target_max_mv,
                voltage_measurement_multiplier=voltage_measurement_multiplier,
                voltage_error_window=voltage_error_window,
                voltage_pwm_min_count=voltage_pwm_min_count,
                voltage_pwm_max_count=voltage_pwm_max_count,
                voltage_slow_adjust_ms=voltage_slow_adjust_ms,
                brushed_pwm_frequency_hz=brushed_pwm_frequency_hz,
                brushed_duty_base_count=brushed_duty_base_count,
                brushed_duty_gear_divisor=brushed_duty_gear_divisor,
                detection_samples=detection_samples,
                detection_high_threshold=detection_high_threshold,
            ),
            fan_protection=FanProtectionConfig(
                enabled=protection_enabled,
                adc_reference=adc_reference,
                overvoltage_adc_reference=overvoltage_adc_reference,
                adc_clock=adc_clock,
                discard_samples=discard_samples,
                average_samples=average_samples,
                overvoltage_adc_threshold=overvoltage_adc_threshold,
                overvoltage_voltage_mv=overvoltage_voltage_mv,
                divider_high_ohm=divider_high_ohm,
                divider_low_ohm=divider_low_ohm,
                consecutive_confirmations=consecutive_confirmations,
            ),
            battery_monitor=BatteryMonitorConfig(
                enabled=battery_monitor_enabled,
                business_enabled=battery_business_enabled,
                curve=battery_curve,
            ),
            ad_key=AdKeyConfig(
                enabled=ad_key_enabled,
                adc_reference=ad_key_adc_reference,
                adc_clock=ad_key_adc_clock,
                discard_samples=ad_key_discard_samples,
                average_samples=ad_key_average_samples,
                threshold_profile=ad_key_threshold_profile,
                double_click_ms=ad_key_double_click_ms,
                key_bands=tuple(key_bands),
            ),
            digital_key=DigitalKeyConfig(
                enabled=digital_key_enabled,
                double_click_ms=digital_key_double_click_ms,
                keys=tuple(digital_keys),
            ),
            slide_switch=SlideSwitchConfig(
                enabled=slide_switch_enabled,
                active_level=slide_switch_active_level,
                pull=slide_switch_pull,
                zero_battery_disable_pull_wake=(
                    zero_battery_disable_pull_wake
                ),
            ),
            encoder=EncoderConfig(
                enabled=encoder_enabled,
                pull=encoder_pull,
                filter_us=encoder_filter_us,
                clockwise_increases=clockwise_increases,
                normal_step=encoder_normal_step,
                acceleration_window_ms=(
                    encoder_acceleration_window_ms
                ),
                acceleration_events=encoder_acceleration_events,
                accelerated_step=encoder_accelerated_step,
            ),
            slide_resistor=SlideResistorConfig(
                enabled=slide_resistor_enabled,
                adc_reference=slide_resistor_adc_reference,
                adc_clock=slide_resistor_adc_clock,
                discard_samples=slide_resistor_discard_samples,
                accumulation_samples=(
                    slide_resistor_accumulation_samples
                ),
                low_gear_adc_sum=low_gear_adc_sum,
                high_gear_adc_sum=high_gear_adc_sum,
                low_gear_at_high_adc=low_gear_at_high_adc,
                deadband_gears=deadband_gears,
                confirmation_count=confirmation_count,
                supply_active_level=supply_active_level,
            ),
            charging=ChargingConfig(
                enabled=charging_enabled,
                kind=charging_kind,
            ),
            cooling=CoolingConfig(
                enabled=cooling_enabled,
                presence_detection=cooling_presence_detection,
                control_mode=cooling_control_mode,
                allow_while_charging=cooling_allow_while_charging,
            ),
            light=LightConfig(
                enabled=light_enabled,
                presence_detection=light_presence_detection,
                mode_profile=light_mode_profile,
            ),
            atomizer=AtomizerConfig(
                enabled=atomizer_enabled,
                pwm_frequency_hz=atomizer_pwm_frequency_hz,
                pwm_clock_source=atomizer_pwm_clock_source,
                pwm_prescaler=atomizer_pwm_prescaler,
                duty_percent=atomizer_duty_percent,
                dependency=atomizer_dependency,
                allow_while_charging=atomizer_allow_while_charging,
            ),
            display=DisplayConfig(
                enabled=display_enabled,
                profile=display_profile,
                drive_mode=display_drive_mode,
                pin_count=display_pin_count,
                connections=display_connections,
                behavior_profile=display_behavior_profile,
                gear_event_ms=display_gear_event_ms,
                normal_battery_preview_ms=display_battery_preview_ms,
                normal_idle_page=display_normal_idle_page,
                charging_idle_page=display_charging_idle_page,
            ),
            classic_product=ClassicProductConfig(
                enabled=classic_enabled,
                input_kind=input_kind,
                gear_mode=gear_mode,
                gear_steps=gear_steps,
                minimum_gear=minimum_gear,
                maximum_gear=maximum_gear,
                long_adjust=long_adjust,
                charging_kind=charging_kind,
                cooling_enabled=cooling_enabled,
                charge_max_gear=charge_max_gear,
                display_hardware=display_hardware,
                display_policy=display_policy,
                low_blink_target=low_blink_target,
                charge_blink_target=charge_blink_target,
                sleep_enabled=sleep_enabled,
            ),
            self_test_ms=self_test_ms,
        )


@dataclass(frozen=True)
class GpioRequest:
    owner: str
    role: str
    physical_pin: int
    mode: str
    initial_level: int | None
    pull: str
    wake: bool = False
    runtime_change: bool = False
    sleep_mode: str | None = None
    sleep_level: int | None = None
    sleep_pull: str | None = None
    zero_battery_sleep_mode: str | None = None
    zero_battery_sleep_level: int | None = None
    zero_battery_sleep_pull: str | None = None
    zero_battery_wake: bool | None = None


@dataclass(frozen=True)
class PwmRequest:
    owner: str
    role: str
    physical_pin: int
    target_frequency_hz: int
    clock_source: str
    prescaler: int | None


@dataclass(frozen=True)
class AdcRequest:
    owner: str
    role: str
    source_kind: str
    physical_pin: int | None
    reference: str
    clock: str
    discard_samples: int
    average_samples: int
    secondary_average_samples: int
    result_name: str
    scan_order: int
    reset_semantics: str
    ready_flag_name: str | None = None
    result_mode: str = "average"


@dataclass(frozen=True)
class TimeRequest:
    owner: str
    role: str
    period_ms: int
    phase: str
    reset_semantics: str


@dataclass(frozen=True)
class TimeSignalPlan:
    period_ms: int
    parent_period_ms: int | None
    ticks_per_period: int
    phase: str
    reset_semantics: str
    flag_name: str | None
    counter_name: str | None
    request_roles: tuple[str, ...]
    internal: bool


@dataclass(frozen=True)
class TimeResourcePlan:
    base_period_ms: int
    signals: tuple[TimeSignalPlan, ...]
    role_flags: dict[str, str]
    role_counters: dict[str, str | None]


@dataclass(frozen=True)
class ResourceRequests:
    gpio: tuple[GpioRequest, ...]
    pwm: tuple[PwmRequest, ...]
    adc: tuple[AdcRequest, ...]
    time: tuple[TimeRequest, ...]


@dataclass(frozen=True)
class TimerPlan:
    source_hz: int
    prescaler: int
    timer_hz: int
    target_us: int
    count: int
    reload_value: int
    actual_us: float
    t1con: int
    subticks_per_ms: int


@dataclass(frozen=True)
class PwmPlan:
    owner: str
    role: str
    timer: str
    physical_pin: int
    gpio_name: str
    channel: int
    route_code: int
    route_register: str
    route_mask: int
    source_hz: int
    clock_source: str
    prescaler: int
    period_register: int
    actual_frequency_hz: float
    error_percent: float
    t3c1: int
    duty_register: str
    duty_high_register: str
    enable_symbol: str


@dataclass(frozen=True)
class AdcChannelPlan:
    source_kind: str
    source_name: str
    physical_pin: int | None
    gpio_name: str | None
    channel: int
    adpcon_register: str | None
    adpcon_mask: int
    adm_value: int
    vrefh_value: int
    adr_value: int
    discard_samples: int
    average_samples: int
    secondary_average_samples: int
    result_name: str
    result_mode: str
    secondary_sum_name: str | None
    secondary_count_name: str | None
    ready_flag_names: tuple[str, ...]
    request_roles: tuple[str, ...]
    scan_order: int
    reset_semantics: str


@dataclass(frozen=True)
class AdcResourcePlan:
    channels: tuple[AdcChannelPlan, ...]
    discard_samples: int
    average_samples: int
    conversion_wait_limit: int
    role_results: dict[str, str]
    scan_cycle_ms: int
    sample_period_us: int = 1000
    channel_scan_cycle_us: int = 0
    high_rate_enabled: bool = False
    high_rate_samples_per_channel: int = 0
    high_rate_discard_samples: int = 0
    high_rate_group_size: int = 0
    high_rate_group_count: int = 0
    high_rate_valid_samples: int = 0


@dataclass(frozen=True)
class GpioPlan:
    trisa: int
    trisc: int
    porta: int
    portc: int
    pahcon: int
    padcon: int
    pchcon: int
    pcdcon: int
    runtime_change_mask_a: int
    adpcon: int
    adpcon1: int
    sleep_trisa: int
    sleep_trisc: int
    sleep_porta: int
    sleep_portc: int
    sleep_pahcon: int
    sleep_padcon: int
    sleep_pchcon: int
    sleep_pcdcon: int
    wake_mask_a: int
    zero_battery_sleep_trisa: int
    zero_battery_sleep_trisc: int
    zero_battery_sleep_porta: int
    zero_battery_sleep_portc: int
    zero_battery_sleep_pahcon: int
    zero_battery_sleep_padcon: int
    zero_battery_sleep_pchcon: int
    zero_battery_sleep_pcdcon: int
    zero_battery_wake_mask_a: int
    has_zero_battery_sleep_override: bool


@dataclass(frozen=True)
class GenerationPlan:
    config: ProjectConfig
    requests: ResourceRequests
    timer: TimerPlan
    pwm: PwmPlan
    alternate_pwm: PwmPlan | None
    auxiliary_pwm: tuple[PwmPlan, ...]
    adc: AdcResourcePlan
    gpio: GpioPlan
    time_resources: TimeResourcePlan
    resolved_pins: dict[str, str]
