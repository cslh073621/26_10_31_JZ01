from typing import Any

from fanforge import __version__
from fanforge.models import (
    FEATURE_KEYS,
    KEY_ACTIONS,
    NESTED_KEYS,
    ROOT_KEYS,
    SECTION_KEYS,
)


def build_capability_catalog() -> dict[str, Any]:
    """Return the deterministic, machine-readable public feature contract."""
    return {
        "generator": {
            "name": "FanForge",
            "version": __version__,
            "template_selection_exposed": False,
        },
        "configuration_contract": {
            "strict_unknown_fields": True,
            "root_fields": sorted(ROOT_KEYS),
            "feature_modules": sorted(FEATURE_KEYS),
            "module_fields": {
                name: sorted(fields)
                for name, fields in sorted(SECTION_KEYS.items())
            },
            "nested_fields": {
                name: sorted(fields)
                for name, fields in sorted(NESTED_KEYS.items())
            },
            "pin_roles_are_feature_derived": True,
        },
        "target": {
            "mcu_models": ["HS16P2811"],
            "packages": ["SOP16"],
            "oscillator_hz_default": 16000000,
            "system_dividers": [1, 2, 4, 8],
            "timebase_interrupt_us": [125, 1000],
        },
        "motor_kinds": {
            "brushless_fixed_duty": {
                "required_pins": ["PWM_FAN", "FAN_ON", "AD_FAN"],
                "requires_fan_voltage_protection": True,
                "requires_125us_timebase": False,
                "runtime_contract": "fixed_pwm_with_10ms_start_stop",
            },
            "brushed_fixed_duty": {
                "required_pins": ["FAN_ON"],
                "requires_fan_voltage_protection": False,
                "requires_125us_timebase": False,
                "runtime_contract": "fan_on_pin_is_brushed_pwm",
            },
            "brushless_fixed_voltage_7_3": {
                "required_pins": ["PWM_FAN", "FAN_ON", "AD_FAN"],
                "requires_fan_voltage_protection": True,
                "requires_125us_timebase": True,
                "runtime_contract": "mature_7_plus_3_voltage_loop",
            },
            "brushed_brushless_compat_fixed_voltage_7_3": {
                "required_pins": ["PWM_FAN", "FAN_ON", "AD_FAN"],
                "requires_fan_voltage_protection": True,
                "requires_125us_timebase": True,
                "runtime_contract": "power_on_motor_detection_and_two_branches",
            },
        },
        "input_kinds": {
            "two_digital_keys_active_low": {
                "required_pins": ["KEY1", "KEY2"],
                "configurable_actions": False,
            },
            "digital_keys_active_low": {
                "required_pin_pattern": "KEY1..KEYN",
                "key_count": {"minimum": 1, "maximum": 4},
                "configurable_actions": True,
            },
            "two_ad_keys_active_low_ranges": {
                "required_pins": ["AD_KEY"],
                "key_count": 2,
                "configurable_actions": False,
            },
            "ad_keys_active_low_ranges": {
                "required_pins": ["AD_KEY"],
                "key_count": {"minimum": 1, "maximum": 4},
                "configurable_actions": True,
                "custom_adc_ranges": True,
            },
            "rotary_encoder_active_low": {
                "required_pins": ["ENC_A", "ENC_B", "SWI_KEY"],
                "requires_slide_switch": True,
                "continuous_gear_range": True,
            },
            "single_key_slide_resistor_active_low": {
                "required_pins": ["KEY", "SLIDER_ON", "AD_SLIDER"],
                "continuous_gear_range": True,
            },
        },
        "key_actions": list(KEY_ACTIONS),
        "charging_kinds": {
            "none": {"required_pins": []},
            "chrg_stdby_active_low": {
                "required_pins": ["CHRG", "STDBY"],
                "bias": "internal_pull_up",
            },
            "chrg_chrg_max_active_low_static": {
                "required_pins": ["CHRG", "CHRG_MAX"],
                "bias": "internal_pull_up",
                "signal_type": "static_active_low",
            },
            "insert_active_high_chrg_active_low": {
                "required_pins": ["INSERT", "CHRG"],
                "insert_bias": "internal_pull_down",
                "chrg_bias": "internal_pull_up",
            },
        },
        "display": {
            "profiles": {
                "standard_188_cooling_percent_style_a": {
                    "required_pin_pattern": "IO_LED_1..IO_LED_5",
                    "pin_count": 5,
                    "mapping": "fixed",
                },
                "custom_charlieplex_188": {
                    "required_pin_pattern": "IO_LED_1..IO_LED_N",
                    "pin_count": {"minimum": 5, "maximum": 7},
                    "mapping": "directed_positive_negative_pairs",
                },
            },
            "drive_modes": ["output_high_input_off"],
            "behavior_profiles": [
                "gear_3s_battery_3s_gear",
                "gear_event_battery_preview_idle",
            ],
            "idle_pages": ["gear", "battery"],
            "low_blink_targets": ["last_digit", "both_digits"],
            "charge_blink_targets": [
                "last_digit",
                "percent_icon",
                "charge_icon",
            ],
            "state_driven_icons": {
                "icon.percent": "battery_page",
                "icon.cooling": "cooling_output_on",
                "icon.charge": "inserted_when_selected_as_charge_target",
                "icon.fan": "fan_mode_nonzero",
                "icon.mist": "atomizer_mode_on",
            },
        },
        "optional_features": {
            "cooling": {
                "required_pins": ["COOL_EN"],
                "control_modes": ["toggle_while_fan_on", "follow_fan"],
                "presence_detection_supported": True,
            },
            "light": {
                "required_pins": ["LED_ON"],
                "mode_profiles": ["fan_sync", "on_off", "on_off_flash"],
                "presence_detection_supported": True,
            },
            "atomizer": {
                "required_pins": ["PWM_WH"],
                "dependencies": ["fan_required", "independent"],
                "default_frequency_hz": 108000,
                "default_duty_percent": 10,
            },
        },
        "fixed_safety_contracts": {
            "brushless_startup": "FAN_ON_then_wait_10ms_then_PWM_FAN",
            "brushless_shutdown": "PWM_FAN_off_then_wait_10ms_then_FAN_ON_off",
            "ad_fan_divider": "100k_to_10k",
            "ad_fan_reference": "2v",
            "ad_fan_overvoltage_mv": 16000,
            "non_insert_battery_upward_chase": False,
        },
        "not_implemented": [
            "rgb_ws2812",
            "multi_level_pwm_light",
            "shared_display_input_pin",
            "single_wire_communication",
            "dual_chip_display",
            "stepper_swing",
            "ip5402_waveform_charge_discharge",
            "rotary_encoder_without_slide_switch",
            "packages_other_than_sop16",
        ],
    }
