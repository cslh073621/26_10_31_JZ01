import copy
import json
import re
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from fanforge.capabilities import build_capability_catalog
from fanforge.cli import main as cli_main
from fanforge.emitter import (
    plan_as_dict,
    render_acceptance_checklist,
    render_main_c,
    render_report,
    write_generation,
)
from fanforge.errors import ConfigError, ResourceConflictError
from fanforge.models import (
    FEATURE_KEYS,
    NESTED_KEYS,
    ROOT_KEYS,
    SECTION_KEYS,
    AdcRequest,
    ProjectConfig,
    TimeRequest,
)
from fanforge.planner import (
    build_generation_plan,
    load_chip_database,
    plan_adc_resources,
    plan_time_resources,
)


ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "configs" / "hs2811_brushless_minimal.json"
CLASSIC_CONFIG_PATH = (
    ROOT / "configs" / "hs2811_classic_two_key_cooling_188.json"
)
CLASSIC_200K_CONFIG_PATH = (
    ROOT
    / "configs"
    / "hs2811_classic_two_key_cooling_188_icon_blink_200k.json"
)
CLASSIC_199_CONFIG_PATH = (
    ROOT
    / "configs"
    / "hs2811_classic_two_key_cooling_188_199_no_long.json"
)
CLASSIC_FIXED_VOLTAGE_CONFIG_PATH = (
    ROOT / "configs" / "hs2811_classic_fixed_voltage_7_3.json"
)
F824_FIXED_VOLTAGE_CONFIG_PATH = (
    ROOT / "configs" / "hs2811_f824_fixed_voltage_7_3_regression.json"
)
CLASSIC_COMPAT_CONFIG_PATH = (
    ROOT / "configs" / "hs2811_classic_brushed_brushless_compat.json"
)
CLASSIC_BRUSHED_CONFIG_PATH = (
    ROOT / "configs" / "hs2811_classic_brushed_fixed_duty_188.json"
)
CLASSIC_AD_KEY_CONFIG_PATH = (
    ROOT / "configs" / "hs2811_classic_two_ad_key_cooling_188.json"
)
CLASSIC_DEFAULT_AD_KEY_CONFIG_PATH = (
    ROOT
    / "configs"
    / "hs2811_classic_default_two_ad_key_cooling_188.json"
)
CLASSIC_FOUR_AD_KEY_CONFIG_PATH = (
    ROOT / "configs" / "hs2811_classic_four_ad_key_cooling_188.json"
)
CLASSIC_SLIDE_SWITCH_CONFIG_PATH = (
    ROOT
    / "configs"
    / "hs2811_classic_slide_switch_two_key_cooling_188.json"
)
CLASSIC_ENCODER_CONFIG_PATH = (
    ROOT
    / "configs"
    / "hs2811_classic_slide_switch_encoder_188.json"
)
CLASSIC_SLIDER_CONFIG_PATH = (
    ROOT
    / "configs"
    / "hs2811_classic_single_key_slide_resistor_cooling_188.json"
)
CLASSIC_LIGHT_FAN_SYNC_CONFIG_PATH = (
    ROOT
    / "configs"
    / "hs2811_classic_two_key_cooling_light_fan_sync_188.json"
)
CLASSIC_LIGHT_ON_OFF_CONFIG_PATH = (
    ROOT
    / "configs"
    / "hs2811_classic_four_ad_key_cooling_light_on_off_188.json"
)
CLASSIC_LIGHT_FLASH_CONFIG_PATH = (
    ROOT
    / "configs"
    / "hs2811_classic_four_ad_key_cooling_light_on_off_flash_188.json"
)
CLASSIC_DOUBLE_CLICK_CONFIG_PATH = (
    ROOT
    / "configs"
    / "hs2811_classic_four_ad_key_double_click_cooling_light_188.json"
)
CLASSIC_INSERT_CHRG_CONFIG_PATH = (
    ROOT
    / "configs"
    / "hs2811_classic_two_key_insert_chrg_cooling_188.json"
)
CLASSIC_CHRG_MAX_STATIC_CONFIG_PATH = (
    ROOT
    / "configs"
    / "hs2811_classic_two_key_chrg_chrg_max_static_cooling_188.json"
)
CLASSIC_NO_CHARGING_CONFIG_PATH = (
    ROOT
    / "configs"
    / "hs2811_classic_two_key_no_charging_188.json"
)
CLASSIC_CUSTOM_DISPLAY_CONFIG_PATH = (
    ROOT
    / "configs"
    / "hs2811_classic_two_key_insert_chrg_cooling_three_icon_188.json"
)
CLASSIC_CUSTOM_DISPLAY_BEHAVIOR_CONFIG_PATH = (
    ROOT
    / "configs"
    / "hs2811_classic_two_key_insert_chrg_cooling_gear3_battery5_188.json"
)
CLASSIC_ATOMIZER_CONFIG_PATH = (
    ROOT / "configs" / "hs2811_classic_two_ad_key_atomizer_188.json"
)
CLASSIC_ATOMIZER_ICON_CONFIG_PATH = (
    ROOT
    / "configs"
    / "hs2811_classic_two_ad_key_atomizer_fan_mist_icons_188.json"
)
CLASSIC_DIGITAL_KEY_ATOMIZER_CONFIG_PATH = (
    ROOT
    / "configs"
    / "hs2811_classic_two_digital_key_atomizer_cooling_188.json"
)
CLASSIC_FOUR_DIGITAL_KEY_CONFIG_PATH = (
    ROOT / "configs" / "hs2811_classic_four_digital_key_188.json"
)
CLASSIC_MAX_SUPPORTED_CONFIG_PATH = (
    ROOT
    / "configs"
    / "hs2811_classic_max_supported_single_chip_188.json"
)
SHOWCASE_CONFIGS = tuple(sorted((ROOT / "configs").glob("*.json")))


def load_raw() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def make_plan(raw: dict | None = None):
    data = load_raw() if raw is None else raw
    config = ProjectConfig.from_dict(CONFIG_PATH, data)
    return build_generation_plan(config)


def make_classic_plan(raw: dict | None = None):
    data = (
        json.loads(CLASSIC_CONFIG_PATH.read_text(encoding="utf-8"))
        if raw is None
        else raw
    )
    config = ProjectConfig.from_dict(CLASSIC_CONFIG_PATH, data)
    return build_generation_plan(config)


def make_plan_from_path(config_path: Path):
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    config = ProjectConfig.from_dict(config_path, raw)
    return build_generation_plan(config)


def make_ad_classic_plan(raw: dict | None = None):
    data = (
        json.loads(CLASSIC_AD_KEY_CONFIG_PATH.read_text(encoding="utf-8"))
        if raw is None
        else raw
    )
    config = ProjectConfig.from_dict(CLASSIC_AD_KEY_CONFIG_PATH, data)
    return build_generation_plan(config)


def make_ad_classic_plan_from_path(config_path: Path):
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    config = ProjectConfig.from_dict(config_path, raw)
    return build_generation_plan(config)


def make_slide_switch_classic_plan(raw: dict | None = None):
    data = (
        json.loads(
            CLASSIC_SLIDE_SWITCH_CONFIG_PATH.read_text(encoding="utf-8")
        )
        if raw is None
        else raw
    )
    config = ProjectConfig.from_dict(CLASSIC_SLIDE_SWITCH_CONFIG_PATH, data)
    return build_generation_plan(config)


def make_encoder_classic_plan(raw: dict | None = None):
    data = (
        json.loads(CLASSIC_ENCODER_CONFIG_PATH.read_text(encoding="utf-8"))
        if raw is None
        else raw
    )
    config = ProjectConfig.from_dict(CLASSIC_ENCODER_CONFIG_PATH, data)
    return build_generation_plan(config)


def make_slider_classic_plan(raw: dict | None = None):
    data = (
        json.loads(CLASSIC_SLIDER_CONFIG_PATH.read_text(encoding="utf-8"))
        if raw is None
        else raw
    )
    config = ProjectConfig.from_dict(CLASSIC_SLIDER_CONFIG_PATH, data)
    return build_generation_plan(config)


class GeneratorTests(unittest.TestCase):
    def test_capability_catalog_exposes_fixed_core_and_missing_features(self):
        catalog = build_capability_catalog()

        self.assertFalse(
            catalog["generator"]["template_selection_exposed"]
        )
        self.assertTrue(
            catalog["configuration_contract"]["strict_unknown_fields"]
        )
        self.assertEqual(
            catalog["configuration_contract"]["root_fields"],
            sorted(ROOT_KEYS),
        )
        self.assertEqual(
            catalog["configuration_contract"]["feature_modules"],
            sorted(FEATURE_KEYS),
        )
        self.assertEqual(
            catalog["configuration_contract"]["module_fields"]["motor"],
            sorted(SECTION_KEYS["motor"]),
        )
        self.assertEqual(
            catalog["configuration_contract"]["nested_fields"][
                "battery_monitor.business.thresholds"
            ],
            sorted(
                NESTED_KEYS[
                    "battery_monitor.business.thresholds"
                ]
            ),
        )
        self.assertEqual(catalog["target"]["packages"], ["SOP16"])
        self.assertEqual(
            catalog["motor_kinds"]["brushless_fixed_duty"][
                "required_pins"
            ],
            ["PWM_FAN", "FAN_ON", "AD_FAN"],
        )
        self.assertEqual(
            catalog["charging_kinds"][
                "insert_active_high_chrg_active_low"
            ]["insert_bias"],
            "internal_pull_down",
        )
        self.assertEqual(
            catalog["charging_kinds"][
                "chrg_chrg_max_active_low_static"
            ]["required_pins"],
            ["CHRG", "CHRG_MAX"],
        )
        self.assertIn(
            "rgb_ws2812", catalog["not_implemented"]
        )
        self.assertIn(
            "ip5402_waveform_charge_discharge",
            catalog["not_implemented"],
        )

    def test_capabilities_cli_writes_deterministic_json(self):
        with tempfile.TemporaryDirectory() as first_dir, (
            tempfile.TemporaryDirectory()
        ) as second_dir:
            first = Path(first_dir) / "capabilities.json"
            second = Path(second_dir) / "capabilities.json"
            self.assertEqual(
                cli_main(["capabilities", "--out", str(first)]), 0
            )
            self.assertEqual(
                cli_main(["capabilities", "--out", str(second)]), 0
            )
            self.assertEqual(first.read_bytes(), second.read_bytes())
            parsed = json.loads(first.read_text(encoding="utf-8"))
            self.assertEqual(parsed, build_capability_catalog())

    def test_generate_cli_refuses_overwrite_without_force(self):
        with tempfile.TemporaryDirectory() as output_dir:
            output = Path(output_dir)
            args = [
                "generate",
                str(CLASSIC_CONFIG_PATH),
                "--out",
                str(output),
            ]

            self.assertEqual(cli_main(args), 0)
            original = (output / "main.c.in").read_bytes()
            self.assertEqual(cli_main(args), 2)
            self.assertEqual((output / "main.c.in").read_bytes(), original)
            self.assertEqual(cli_main([*args, "--force"]), 0)
            self.assertEqual((output / "main.c.in").read_bytes(), original)

    def test_unknown_feature_module_is_rejected_not_ignored(self):
        raw = json.loads(
            CLASSIC_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["rgb"] = {
            "enabled": True,
            "signal_pin": "RGB_SIGN",
        }

        with self.assertRaisesRegex(
            ConfigError, "unknown features field.*rgb"
        ):
            make_classic_plan(raw)

    def test_unused_pin_role_is_rejected_not_ignored(self):
        raw = json.loads(
            CLASSIC_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["pins"]["RGB_SIGN"] = 9

        with self.assertRaisesRegex(
            ConfigError, "unused or unsupported pin role.*RGB_SIGN"
        ):
            make_classic_plan(raw)

    def test_unknown_root_field_is_rejected_not_ignored(self):
        raw = json.loads(
            CLASSIC_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["template"] = "unreviewed"

        with self.assertRaisesRegex(
            ConfigError, "unknown configuration field.*template"
        ):
            make_classic_plan(raw)

    def test_unknown_module_parameter_is_rejected_not_defaulted(self):
        raw = json.loads(
            CLASSIC_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["motor"]["pwm_frequncy_hz"] = 120000

        with self.assertRaisesRegex(
            ConfigError,
            "unknown motor field.*pwm_frequncy_hz",
        ):
            make_classic_plan(raw)

    def test_unknown_charging_parameter_is_rejected(self):
        raw = json.loads(
            CLASSIC_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["charging"] = {
            "enabled": True,
            "kind": "chrg_stdby_active_low",
            "filter_ms": 100,
        }

        with self.assertRaisesRegex(
            ConfigError, "unknown charging field.*filter_ms"
        ):
            make_classic_plan(raw)

    def test_unknown_battery_threshold_is_rejected(self):
        raw = json.loads(
            CLASSIC_CONFIG_PATH.read_text(encoding="utf-8")
        )
        thresholds = raw["features"]["battery_monitor"]["business"][
            "thresholds"
        ]
        thresholds["p_100"] = thresholds["p100"]

        with self.assertRaisesRegex(
            ConfigError,
            "unknown battery_monitor.business.thresholds field.*p_100",
        ):
            make_classic_plan(raw)

    def test_unknown_ad_key_entry_field_is_rejected(self):
        raw = json.loads(
            CLASSIC_FOUR_AD_KEY_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["ad_key"]["keys"][0]["short_aciton"] = "fan_cycle"

        with self.assertRaisesRegex(
            ConfigError,
            r"unknown ad_key\.keys\[\] field.*short_aciton",
        ):
            build_generation_plan(
                ProjectConfig.from_dict(
                    CLASSIC_FOUR_AD_KEY_CONFIG_PATH, raw
                )
            )

    def test_unknown_motor_curve_field_is_rejected(self):
        raw = json.loads(
            CLASSIC_FIXED_VOLTAGE_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["motor"]["voltage_curve"][
            "target_adc_bsae"
        ] = 1616

        with self.assertRaisesRegex(
            ConfigError,
            "unknown motor.voltage_curve field.*target_adc_bsae",
        ):
            build_generation_plan(
                ProjectConfig.from_dict(
                    CLASSIC_FIXED_VOLTAGE_CONFIG_PATH, raw
                )
            )

    def test_unknown_display_connection_field_is_rejected(self):
        raw = json.loads(
            CLASSIC_CUSTOM_DISPLAY_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["display"]["connections"]["ones.a"][
            "positive_pin"
        ] = 1

        with self.assertRaisesRegex(
            ConfigError,
            "unknown display.connections.ones.a field.*positive_pin",
        ):
            build_generation_plan(
                ProjectConfig.from_dict(
                    CLASSIC_CUSTOM_DISPLAY_CONFIG_PATH, raw
                )
            )

    def test_max_supported_single_chip_profile_uses_all_io_without_conflict(
        self,
    ):
        plan = make_plan_from_path(CLASSIC_MAX_SUPPORTED_CONFIG_PATH)
        source = render_main_c(plan)

        self.assertEqual(
            set(plan.config.pins.values()), set(range(2, 16))
        )
        self.assertEqual(plan.pwm.timer, "T4")
        self.assertEqual(plan.pwm.gpio_name, "PA7")
        atomizer_pwm = next(
            item for item in plan.auxiliary_pwm
            if item.role == "PWM_WH"
        )
        self.assertEqual(atomizer_pwm.timer, "T3")
        self.assertEqual(atomizer_pwm.gpio_name, "PC5")
        self.assertIn("void wh_deal(void)", source)
        self.assertIn("bit YOUWU_COOL;", source)
        self.assertIn("bit YOUWU_LED;", source)
        self.assertIn("u8 key2_click_cnt;", source)
        self.assertIn("double_click_window_350ms_flag", source)
        self.assertIn("&& !light_mode", source)
        self.assertIn("&& !wh_mode", source)

    def test_atomizer_uses_t3_108khz_and_moves_fan_to_t4_250khz(self):
        plan = make_plan_from_path(CLASSIC_ATOMIZER_CONFIG_PATH)
        source = render_main_c(plan)
        report = render_report(plan)

        self.assertEqual(plan.pwm.timer, "T4")
        self.assertEqual(plan.pwm.gpio_name, "PA7")
        self.assertEqual(plan.pwm.period_register, 63)
        self.assertEqual(len(plan.auxiliary_pwm), 1)
        atomizer = plan.auxiliary_pwm[0]
        self.assertEqual(atomizer.timer, "T3")
        self.assertEqual(atomizer.gpio_name, "PC5")
        self.assertEqual(atomizer.channel, 4)
        self.assertEqual(atomizer.period_register, 147)
        self.assertAlmostEqual(
            atomizer.actual_frequency_hz, 108108.108108, places=5
        )
        self.assertIn("PWMSEL1 = 0x0A;", source)
        self.assertIn("#define WH_DUTY              15", source)
        self.assertIn("void wh_deal(void)", source)
        self.assertIn("T4PWMEN = 1;", source)
        self.assertIn("T3PWM4EN = 1;", source)
        self.assertIn("wh_mode = !wh_mode;", source)
        self.assertIn("&& !wh_mode", source)
        self.assertIn("Auxiliary PWM: `PWM_WH`", report)

    def test_fan_and_mist_icons_follow_existing_runtime_states(self):
        plan = make_plan_from_path(CLASSIC_ATOMIZER_ICON_CONFIG_PATH)
        source = render_main_c(plan)
        show_start = source.index("\nvoid show_mode_deal(void)\n{")
        show_end = source.index("\nvoid KEY_CHECK(void)\n{", show_start)
        show_body = source[show_start:show_end]

        self.assertIn("if(fan_mode)", show_body)
        self.assertIn("d0 |= 0x20;", show_body)
        self.assertIn("if(wh_mode)", show_body)
        self.assertIn("d0 |= 0x40;", show_body)
        self.assertLess(
            show_body.index("if(fan_mode)"),
            show_body.index("if(wh_mode)"),
        )

    def test_different_frequency_pwm_requests_cannot_share_only_t3(self):
        raw = json.loads(
            CLASSIC_ATOMIZER_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["pins"]["PWM_FAN"] = 7
        raw["pins"]["FAN_ON"] = 8
        with self.assertRaisesRegex(
            ResourceConflictError, "frequency conflict"
        ):
            make_plan_from_path_data = ProjectConfig.from_dict(
                CLASSIC_ATOMIZER_CONFIG_PATH, raw
            )
            build_generation_plan(make_plan_from_path_data)

    def test_same_frequency_t3_pwm_channels_can_share_timer(self):
        raw = json.loads(
            CLASSIC_ATOMIZER_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["pins"]["PWM_FAN"] = 7
        raw["pins"]["FAN_ON"] = 8
        raw["features"]["atomizer"]["pwm_frequency_hz"] = 250000
        config = ProjectConfig.from_dict(CLASSIC_ATOMIZER_CONFIG_PATH, raw)
        plan = build_generation_plan(config)
        source = render_main_c(plan)

        self.assertEqual(plan.pwm.timer, "T3")
        self.assertEqual(plan.auxiliary_pwm[0].timer, "T3")
        self.assertEqual(plan.pwm.period_register, 63)
        self.assertEqual(plan.auxiliary_pwm[0].period_register, 63)
        self.assertIn("PWMSEL1 = 0x02;", source)
        self.assertNotIn("T4C0 =", source)

    def test_atomizer_requires_an_explicit_ad_key_action(self):
        raw = json.loads(
            CLASSIC_ATOMIZER_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["ad_key"]["keys"][1]["short_action"] = "none"
        with self.assertRaisesRegex(ConfigError, "atomizer_toggle"):
            ProjectConfig.from_dict(CLASSIC_ATOMIZER_CONFIG_PATH, raw)

    def test_digital_keys_share_the_mature_configurable_action_path(self):
        plan = make_plan_from_path(
            CLASSIC_DIGITAL_KEY_ATOMIZER_CONFIG_PATH
        )
        config = plan.config
        source = render_main_c(plan)
        report = render_report(plan)

        self.assertTrue(config.digital_key.enabled)
        self.assertFalse(config.ad_key.enabled)
        requests = {
            (item.owner, item.role): item.period_ms
            for item in plan.requests.time
        }
        self.assertEqual(
            requests[("input.key2", "double_click_window")], 350
        )
        self.assertIn("#define KEY1         PA6", source)
        self.assertIn("#define KEY2         PA1", source)
        self.assertNotIn("AD_KEY_VALUE", source)
        self.assertIn("if(key2_short_flag)", source)
        self.assertIn("if(!key2_click_cnt)", source)
        self.assertIn("if(!KEY1 && ++key1_delay > 2)", source)
        self.assertIn("if(!KEY2 && ++key2_delay > 2)", source)
        self.assertNotIn("if(!KEY1 && ++key1_delay > 5)", source)
        self.assertNotIn("if(!KEY2 && ++key2_delay > 5)", source)
        self.assertIn(
            "if(key2_click_cnt && double_click_window_350ms_flag)",
            source,
        )
        self.assertIn("COOL_EN = !COOL_EN;", source)
        self.assertIn("wh_mode = !wh_mode;", source)
        self.assertIn("&& KEY1 && KEY2", source)
        self.assertIn(
            "Digital KEY1 actions: short=`fan_cycle`", report
        )
        self.assertIn(
            "Digital KEY2 actions: short=`atomizer_toggle`", report
        )

    def test_digital_key_double_click_window_is_validated(self):
        raw = json.loads(
            CLASSIC_DIGITAL_KEY_ATOMIZER_CONFIG_PATH.read_text(
                encoding="utf-8"
            )
        )
        raw["features"]["digital_key"]["double_click_ms"] = 355
        with self.assertRaisesRegex(ConfigError, "10ms multiple"):
            ProjectConfig.from_dict(
                CLASSIC_DIGITAL_KEY_ATOMIZER_CONFIG_PATH, raw
            )

    def test_digital_key_action_requires_its_feature(self):
        raw = json.loads(
            CLASSIC_DIGITAL_KEY_ATOMIZER_CONFIG_PATH.read_text(
                encoding="utf-8"
            )
        )
        raw["features"]["atomizer"]["enabled"] = False
        raw["pins"].pop("PWM_WH")
        with self.assertRaisesRegex(ConfigError, "atomizer_toggle"):
            ProjectConfig.from_dict(
                CLASSIC_DIGITAL_KEY_ATOMIZER_CONFIG_PATH, raw
            )

    def test_general_digital_key_generates_four_key_complete_path(self):
        plan = make_plan_from_path(CLASSIC_FOUR_DIGITAL_KEY_CONFIG_PATH)
        source = render_main_c(plan)

        self.assertEqual(
            [item.name for item in plan.config.digital_key.keys],
            ["KEY1", "KEY2", "KEY3", "KEY4"],
        )
        for key_name in ("KEY1", "KEY2", "KEY3", "KEY4"):
            state = key_name.lower()
            self.assertIn(f"#define {key_name}", source)
            self.assertIn(f"bit {state}_down_flag;", source)
            self.assertIn(f"u8 {state}_delay;", source)
            self.assertIn(f"if({key_name} && !{state}_down_flag)", source)
            self.assertIn(f"{state}_short_flag = 0;", source)
        self.assertIn("&& KEY1 && KEY2 && KEY3 && KEY4", source)
        self.assertIn("WUACON = 0xFC;", source)

    def test_general_digital_key_accepts_one_key(self):
        raw = json.loads(
            CLASSIC_FOUR_DIGITAL_KEY_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["digital_key"]["keys"] = [
            {
                "name": "KEY1",
                "short_action": "fan_cycle",
                "double_action": "none",
                "long_action": "none",
            }
        ]
        for key_name in ("KEY2", "KEY3", "KEY4"):
            raw["pins"].pop(key_name)
        raw["features"]["classic_product"]["long_adjust"] = False

        config = ProjectConfig.from_dict(
            CLASSIC_FOUR_DIGITAL_KEY_CONFIG_PATH, raw
        )
        source = render_main_c(build_generation_plan(config))

        self.assertIn("#define KEY1", source)
        self.assertNotIn("#define KEY2", source)
        self.assertIn("&& KEY1", source)
        self.assertNotIn("&& KEY1 && KEY2", source)

    def test_general_digital_key_requires_contiguous_names(self):
        raw = json.loads(
            CLASSIC_FOUR_DIGITAL_KEY_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["digital_key"]["keys"] = [
            raw["features"]["digital_key"]["keys"][0],
            raw["features"]["digital_key"]["keys"][2],
        ]
        with self.assertRaisesRegex(ConfigError, "contiguous KEY1..KEY4"):
            ProjectConfig.from_dict(
                CLASSIC_FOUR_DIGITAL_KEY_CONFIG_PATH, raw
            )

    def test_legacy_two_digital_key_rejects_extra_keys(self):
        raw = json.loads(
            CLASSIC_DIGITAL_KEY_ATOMIZER_CONFIG_PATH.read_text(
                encoding="utf-8"
            )
        )
        raw["features"]["digital_key"]["keys"].append(
            {
                "name": "KEY3",
                "short_action": "fan_step_up",
                "double_action": "none",
                "long_action": "none",
            }
        )
        with self.assertRaisesRegex(ConfigError, "legacy two-digital-key"):
            ProjectConfig.from_dict(
                CLASSIC_DIGITAL_KEY_ATOMIZER_CONFIG_PATH, raw
            )

    def test_compatible_brushed_pwm_and_atomizer_share_t3_safely(self):
        raw = json.loads(
            CLASSIC_COMPAT_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["pins"].pop("KEY1")
        raw["pins"].pop("KEY2")
        raw["pins"]["AD_KEY"] = 3
        raw["pins"]["PWM_FAN"] = 2
        raw["pins"]["PWM_WH"] = 6
        raw["pins"]["COOL_EN"] = 9
        raw["features"]["ad_key"] = {
            "enabled": True,
            "adc_reference": "vdd",
            "adc_clock": "fcpu",
            "discard_samples": 2,
            "average_samples": 8,
            "keys": [
                {
                    "name": "KEY1",
                    "min": 0,
                    "max": 100,
                    "short_action": "fan_cycle",
                    "long_action": "none",
                },
                {
                    "name": "KEY2",
                    "min": 610,
                    "max": 810,
                    "short_action": "atomizer_toggle",
                    "long_action": "none",
                },
            ],
        }
        raw["features"]["atomizer"] = {
            "enabled": True,
            "pwm_frequency_hz": 108000,
            "pwm_clock_source": "fosc",
            "pwm_prescaler": "auto",
            "duty_percent": 10,
            "dependency": "fan_required",
            "allow_while_charging": True,
        }
        classic = raw["features"]["classic_product"]
        classic["input_kind"] = "ad_keys_active_low_ranges"
        classic["long_adjust"] = False
        config = ProjectConfig.from_dict(CLASSIC_COMPAT_CONFIG_PATH, raw)
        plan = build_generation_plan(config)
        source = render_main_c(plan)

        self.assertEqual(plan.pwm.timer, "T4")
        self.assertEqual(plan.alternate_pwm.timer, "T3")
        self.assertEqual(plan.alternate_pwm.period_register, 147)
        self.assertEqual(plan.auxiliary_pwm[0].timer, "T3")
        self.assertEqual(plan.auxiliary_pwm[0].period_register, 147)
        self.assertIn("if(!T3PWM4EN)", source)
        self.assertIn("if(!T3PWM2EN)", source)
        self.assertIn("PWMSEL1 = 0x0A;", source)

    def test_all_showcase_configs_generate_without_unresolved_slots(self):
        for config_path in SHOWCASE_CONFIGS:
            with self.subTest(config=config_path.name):
                raw = json.loads(config_path.read_text(encoding="utf-8"))
                config = ProjectConfig.from_dict(config_path, raw)
                source = render_main_c(build_generation_plan(config))
                self.assertNotIn("@@", source)
                self.assertEqual(source.count("{"), source.count("}"))
                self.assertNotIn("typedef union", source)
                self.assertNotIn("bit_flag", source)
                self.assertRegex(
                    source,
                    r"if\(PAIF\)\s*\{\s*PORTA;\s*PAIF = 0;",
                )
                self.assertRegex(
                    source,
                    r"PAIE = 0;\s*(?:WUACON = 0;\s*)?"
                    r"PORTA;\s*PAIF = 0;\s*Init_System\(\);",
                )

    def test_all_showcase_sources_are_render_deterministic(self):
        for config_path in SHOWCASE_CONFIGS:
            with self.subTest(config=config_path.name):
                plan = make_plan_from_path(config_path)
                self.assertEqual(render_main_c(plan), render_main_c(plan))

    def test_default_pwm_resolves_pa7_t3pwm3_250khz(self):
        plan = make_plan()
        self.assertEqual(plan.pwm.gpio_name, "PA7")
        self.assertEqual(plan.pwm.channel, 3)
        self.assertEqual(plan.pwm.route_register, "PWMSEL")
        self.assertEqual(plan.pwm.route_mask, 0xC0)
        self.assertEqual(plan.pwm.period_register, 63)
        self.assertEqual(plan.pwm.actual_frequency_hz, 250000)
        self.assertEqual(plan.pwm.t3c1, 0x17)

    def test_pc4_pwm0_zero_route_code_is_valid(self):
        config_path = (
            ROOT / "configs" / "hs2811_brushless_pwm0_pc4_zero_route_250k.json"
        )
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        config = ProjectConfig.from_dict(config_path, raw)
        plan = build_generation_plan(config)
        source = render_main_c(plan)
        self.assertEqual(plan.pwm.gpio_name, "PC4")
        self.assertEqual(plan.pwm.channel, 0)
        self.assertEqual(plan.pwm.route_mask, 0x00)
        self.assertIn("PWMSEL = 0x00;", source)
        self.assertIn("T3PWM0EN = 1;", source)

    def test_120khz_is_calculated_not_hard_coded(self):
        raw = copy.deepcopy(load_raw())
        raw["features"]["motor"]["pwm_frequency_hz"] = 120000
        plan = make_plan(raw)
        self.assertEqual(plan.pwm.period_register, 132)
        self.assertAlmostEqual(plan.pwm.actual_frequency_hz, 120300.75187969924)
        self.assertLess(plan.pwm.error_percent, 0.26)

    def test_t1_direct_1ms_plan(self):
        plan = make_plan()
        self.assertEqual(plan.timer.source_hz, 8000000)
        self.assertEqual(plan.timer.prescaler, 1)
        self.assertEqual(plan.timer.count, 8000)
        self.assertEqual(plan.timer.reload_value, 0xE0C0)
        self.assertEqual(plan.timer.t1con, 0x01)
        self.assertEqual(plan.timer.actual_us, 1000)

    def test_fixed_voltage_100us_timebase_derives_one_real_ms(self):
        plan = make_plan_from_path(CLASSIC_FIXED_VOLTAGE_CONFIG_PATH)
        source = render_main_c(plan)

        self.assertEqual(plan.timer.target_us, 100)
        self.assertEqual(plan.timer.count, 800)
        self.assertEqual(plan.timer.reload_value, 0xFCE0)
        self.assertEqual(plan.timer.subticks_per_ms, 10)
        self.assertIn("if(t1_subtick_cnt >= 10)", source)
        self.assertIn("time_1ms_flag = 1;", source)
        self.assertLess(
            source.index("if(t1_subtick_cnt >= 10)"),
            source.index("time_1ms_flag = 1;"),
        )

    def test_fixed_voltage_uses_mature_7_plus_3_control(self):
        plan = make_plan_from_path(CLASSIC_FIXED_VOLTAGE_CONFIG_PATH)
        source = render_main_c(plan)
        report = render_report(plan)

        self.assertIn("u8 Get_Fin_Val(u16 temp_val)", source)
        self.assertIn("u8 PWM_DR;", source)
        self.assertIn("u8 PWM_CNT;", source)
        self.assertIn("u8 PWM_DATA_NOW;", source)
        self.assertIn("if(PWM_DR > PWM_CNT)", source)
        self.assertIn(
            f"{plan.pwm.duty_register} = PWM_DATA_NOW + 1;", source
        )
        self.assertIn("fin_val = AD_FAN_TARGET_BASE;", source)
        self.assertIn("fin_val += AD_FAN_TARGET_STEP;", source)
        self.assertIn("adc_high_rate_flag = 1;", source)
        self.assertIn("ADCDATA_COUNT > 4", source)
        self.assertIn("(ADCDATA_COUNT & 0x07) == 4", source)
        self.assertIn("ADC_GROUP_SUM / 12", source)
        self.assertIn("AD_FAN_TARGET_MAX", source)
        self.assertNotIn("quick_slow_flag", source)
        self.assertIn("Complete 7+3 cycles per AD_FAN update: `25`", report)
        self.assertIn("- Sample period: `100us`", report)

    def test_high_rate_adc_preserves_f824_accumulation_core(self):
        golden = (ROOT / "tests/fixtures/f824_adc_accumulation.c.fragment").read_bytes().decode("utf-8")
        canonical = lambda text: re.sub(r"\s+", "", re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S))
        for config in (CLASSIC_FIXED_VOLTAGE_CONFIG_PATH,
                       F824_FIXED_VOLTAGE_CONFIG_PATH,
                       CLASSIC_COMPAT_CONFIG_PATH,
                       CLASSIC_SLIDER_CONFIG_PATH):
            with self.subTest(config=config.name):
                source = render_main_c(make_plan_from_path(config))
                start = source.index("    ADCDATA_COUNT++;", source.index("u8 ADC_Sample(void)\n{"))
                end = source.index("    ADC_GROUP_SUM = 0;", start) + len("    ADC_GROUP_SUM = 0;")
                self.assertEqual(canonical(source[start:end] + "\n    }\n"), canonical(golden))
                self.assertNotIn("ADC_GROUP_SAMPLE_COUNT", source)
                self.assertNotIn("ADC_GROUP_COUNT", source)
                self.assertNotIn("ADCDATA_SUM >>= 3;", source[source.index("u8 ADC_Sample(void)\n{"):source.index("void KEY_CHECK(void)\n{")])

    def test_physical_16v_overvoltage_limit_uses_100k_10k_and_2v(self):
        plan = make_plan_from_path(CLASSIC_FIXED_VOLTAGE_CONFIG_PATH)
        protection = plan.config.fan_protection
        source = render_main_c(plan)

        self.assertEqual(protection.overvoltage_voltage_mv, 16000)
        self.assertEqual(protection.divider_high_ohm, 100000)
        self.assertEqual(protection.divider_low_ohm, 10000)
        self.assertEqual(protection.overvoltage_adc_reference, "2v")
        self.assertEqual(protection.overvoltage_adc_threshold, 2978)
        self.assertIn("#define AD_FAN_TOO_HIGH    2978", source)
        self.assertNotIn("AD_FAN_SAFE_VALUE", source)
        self.assertNotIn("ad_fan_safe_ready_flag", source)
        self.assertIn("VREFH = 0x00;", source)
        self.assertNotIn("VREFH = 0x03;", source)

    def test_all_protected_showcases_share_one_2v_ad_fan_reference(self):
        for config_path in SHOWCASE_CONFIGS:
            with self.subTest(config=config_path.name):
                plan = make_plan_from_path(config_path)
                protection = plan.config.fan_protection
                if not protection.enabled:
                    self.assertEqual(
                        plan.config.motor.kind, "brushed_fixed_duty"
                    )
                    self.assertNotIn("AD_FAN", plan.resolved_pins)
                    continue
                self.assertEqual(protection.adc_reference, "2v")
                self.assertEqual(
                    protection.overvoltage_adc_reference, "2v"
                )
                self.assertEqual(
                    protection.overvoltage_adc_threshold, 2978
                )

    def test_mismatched_ad_fan_references_are_rejected(self):
        raw = json.loads(
            CLASSIC_FIXED_VOLTAGE_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["fan_voltage_protection"]["adc_reference"] = "vdd"
        with self.assertRaises(ConfigError):
            ProjectConfig.from_dict(
                CLASSIC_FIXED_VOLTAGE_CONFIG_PATH, raw
            )

    def test_fixed_voltage_checks_overvoltage_before_feedback_adjust(self):
        plan = make_plan_from_path(CLASSIC_FIXED_VOLTAGE_CONFIG_PATH)
        source = render_main_c(plan)
        function_start = source.index("void AD_fan_deal(void)\n{")
        function_end = source.index(
            "void clean_other_time(u8 type)\n{", function_start
        )
        function = source[function_start:function_end]

        safety_check = function.index("if(AD_FAN_VALUE > AD_FAN_TOO_HIGH)")
        feedback_adjust = function.index(
            "temp_pbp_val = AD_FAN_VALUE * AD_FAN_MEASURE_MULTIPLIER;"
        )
        self.assertLess(safety_check, feedback_adjust)
        self.assertNotIn(
            "PWM_DATA_NOW == AD_FAN_PWM_MIN_COUNT", function
        )
        protection_block = function[safety_check:feedback_adjust]
        self.assertIn(f"{plan.pwm.enable_symbol} = 0;", protection_block)
        self.assertIn("T3REN = 0;", protection_block)

    def test_fixed_voltage_rejects_nonmatching_adc_phase_period(self):
        raw = json.loads(
            CLASSIC_FIXED_VOLTAGE_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["timebase"]["interrupt_us"] = 125
        with self.assertRaises(ConfigError):
            ProjectConfig.from_dict(CLASSIC_FIXED_VOLTAGE_CONFIG_PATH, raw)

    def test_fixed_voltage_rejects_adc_conversion_not_below_100us(self):
        raw = json.loads(
            CLASSIC_FIXED_VOLTAGE_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["fan_voltage_protection"]["adc_clock"] = "fcpu_div16"
        config = ProjectConfig.from_dict(CLASSIC_FIXED_VOLTAGE_CONFIG_PATH, raw)
        with self.assertRaises(ResourceConflictError):
            build_generation_plan(config)

    def test_fixed_voltage_offset_does_not_change_overvoltage_threshold(self):
        raw = json.loads(
            CLASSIC_FIXED_VOLTAGE_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["motor"]["voltage_curve"][
            "target_calibration_offset_mv"
        ] = 0
        no_offset_config = ProjectConfig.from_dict(
            CLASSIC_FIXED_VOLTAGE_CONFIG_PATH, raw
        )
        no_offset = build_generation_plan(no_offset_config)
        with_offset = make_plan_from_path(CLASSIC_FIXED_VOLTAGE_CONFIG_PATH)
        self.assertGreater(
            with_offset.config.motor.voltage_target_base,
            no_offset.config.motor.voltage_target_base,
        )
        self.assertGreater(
            with_offset.config.motor.voltage_target_max,
            no_offset.config.motor.voltage_target_max,
        )
        self.assertEqual(
            with_offset.config.fan_protection.overvoltage_adc_threshold,
            no_offset.config.fan_protection.overvoltage_adc_threshold,
        )

    def test_fixed_voltage_requires_explicit_maximum_target(self):
        raw = json.loads(
            CLASSIC_FIXED_VOLTAGE_CONFIG_PATH.read_text(encoding="utf-8")
        )
        del raw["features"]["motor"]["voltage_curve"]["target_adc_max"]
        with self.assertRaises(ConfigError):
            ProjectConfig.from_dict(CLASSIC_FIXED_VOLTAGE_CONFIG_PATH, raw)

    def test_all_fixed_voltage_showcases_match_their_gear_range(self):
        standard_paths = (
            CLASSIC_FIXED_VOLTAGE_CONFIG_PATH,
            CLASSIC_COMPAT_CONFIG_PATH,
            CLASSIC_SLIDER_CONFIG_PATH,
        )
        for config_path in standard_paths:
            with self.subTest(config=config_path.name):
                plan = make_plan_from_path(config_path)
                self.assertEqual(plan.config.classic_product.maximum_gear, 100)
                self.assertEqual(plan.config.motor.voltage_target_step, 18)
                self.assertEqual(plan.config.motor.voltage_target_max, 3534)

        f824 = make_plan_from_path(F824_FIXED_VOLTAGE_CONFIG_PATH)
        self.assertEqual(
            f824.config.classic_product.gear_steps,
            (1, 50, 100, 150, 199),
        )
        self.assertEqual(f824.config.classic_product.maximum_gear, 199)
        self.assertEqual(f824.config.motor.voltage_target_step, 9)
        self.assertEqual(f824.config.motor.voltage_target_max, 3534)

    def test_f824_reports_real_three_channel_result_periods(self):
        plan = make_plan_from_path(F824_FIXED_VOLTAGE_CONFIG_PATH)
        resolved = plan_as_dict(plan)
        channels = {
            channel["request_roles"][0]: channel
            for channel in resolved["adc"]["channels"]
        }

        self.assertEqual(resolved["adc"]["scan_cycle_ms"], 30)
        self.assertEqual(
            channels["motor.fixed_voltage.AD_FAN"]["result_update_ms"],
            30,
        )
        self.assertEqual(
            channels["input.ad_key.AD_KEY"]["result_update_ms"],
            30,
        )
        self.assertEqual(
            channels["battery.voltage.ADC_BAT"]["result_update_ms"],
            480,
        )
        self.assertEqual(
            resolved["pwm"]["complete_7_3_cycles_per_adc_update"],
            37,
        )

    def test_fixed_voltage_standard_adc_resource_timing(self):
        plan = make_plan_from_path(CLASSIC_FIXED_VOLTAGE_CONFIG_PATH)
        resolved = plan_as_dict(plan)
        channels = {
            channel["request_roles"][0]: channel
            for channel in resolved["adc"]["channels"]
        }
        self.assertTrue(plan.adc.high_rate_enabled)
        self.assertEqual(plan.adc.sample_period_us, 100)
        self.assertEqual(plan.adc.channel_scan_cycle_us, 10000)
        self.assertEqual(plan.adc.scan_cycle_ms, 20)
        self.assertEqual(plan.adc.high_rate_valid_samples, 96)
        self.assertEqual(plan.adc.high_rate_group_size, 8)
        self.assertEqual(plan.adc.high_rate_group_count, 12)
        self.assertEqual(plan.adc.high_rate_valid_samples % 8, 0)
        self.assertEqual(plan.adc.high_rate_group_size * 4095, 32760)
        self.assertEqual(plan.adc.high_rate_group_count * 4095, 49140)
        self.assertEqual(
            channels["motor.fixed_voltage.AD_FAN"]["result_update_ms"],
            20,
        )
        self.assertEqual(
            channels["battery.voltage.ADC_BAT"]["result_update_ms"],
            320,
        )

    def test_nonfixed_profile_keeps_legacy_adc_scheduler(self):
        plan = make_classic_plan()
        source = render_main_c(plan)
        self.assertFalse(plan.adc.high_rate_enabled)
        self.assertNotIn("ADC_GROUP_SUM", source)
        self.assertNotIn("adc_high_rate_flag", source)
        self.assertIn("if(time_1ms_flag)", source)

    def test_fixed_voltage_preserves_brushless_start_stop_order(self):
        plan = make_plan_from_path(CLASSIC_FIXED_VOLTAGE_CONFIG_PATH)
        source = render_main_c(plan)
        function_start = source.index("void AD_fan_deal(void)\n{")
        function_end = source.index(
            "void clean_other_time(u8 type)\n{", function_start
        )
        function = source[function_start:function_end]

        start = function.index("FAN_ON = 1;")
        pwm_on = function.index(f"{plan.pwm.enable_symbol} = 1;")
        pwm_off = function.index(f"{plan.pwm.enable_symbol} = 0;")
        fan_off = function.index("FAN_ON = 0;")
        self.assertLess(start, pwm_on)
        self.assertLess(pwm_off, fan_off)

    def test_fixed_voltage_requires_high_rate_timebase(self):
        raw = json.loads(
            CLASSIC_FIXED_VOLTAGE_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["timebase"]["interrupt_us"] = 1000
        with self.assertRaises(ConfigError):
            ProjectConfig.from_dict(CLASSIC_FIXED_VOLTAGE_CONFIG_PATH, raw)

    def test_compatible_motor_follows_mature_detection_polarity_and_pwm(self):
        plan = make_plan_from_path(CLASSIC_COMPAT_CONFIG_PATH)
        source = render_main_c(plan)

        self.assertIsNotNone(plan.alternate_pwm)
        self.assertEqual(plan.pwm.gpio_name, "PC4")
        self.assertEqual(plan.pwm.channel, 0)
        self.assertEqual(plan.pwm.period_register, 63)
        self.assertEqual(plan.alternate_pwm.gpio_name, "PC3")
        self.assertEqual(plan.alternate_pwm.channel, 2)
        self.assertEqual(plan.alternate_pwm.period_register, 147)
        self.assertIn("bit YOUSHUA_WUSHUA;", source)
        self.assertEqual(source.count("bit YOUSHUA_WUSHUA;"), 1)
        self.assertIn("void detect_youshua_wushua(void)", source)
        self.assertIn("if(delay_cnt >= 190)", source)
        self.assertIn(
            "YOUSHUA_WUSHUA = "
            "(youshua_wushua_high_cnt >= "
            "MOTOR_DETECT_HIGH_THRESHOLD) ? 1 : 0;",
            source,
        )
        self.assertIn("if(!YOUSHUA_WUSHUA)", source)
        self.assertIn("if(YOUSHUA_WUSHUA)", source)
        self.assertIn(
            "if(!YOUSHUA_WUSHUA && T3PWM0EN && T3REN)", source
        )
        self.assertIn("T3D2L = BRUSHED_PWM_DUTY_BASE", source)
        self.assertIn("T3PWM0EN = 0;", source)
        self.assertIn("T3PWM2EN = 0;", source)
        self.assertIn(
            "&& !T3PWM0EN && !T3PWM2EN && !T3REN && !FAN_ON",
            source,
        )

    def test_compatible_motor_keeps_separate_battery_compensation(self):
        source = render_main_c(
            make_plan_from_path(CLASSIC_COMPAT_CONFIG_PATH)
        )
        battery_start = source.index("u8 v_bat_deal(void)\n{")
        battery_end = source.index(
            "\nvoid detect_youshua_wushua(void)", battery_start
        )
        battery = source[battery_start:battery_end]

        self.assertIn("#define AD_BAT_MODE_100       1024", source)
        self.assertIn("#define AD_BAT_BRUSH_MODE_100 256", source)
        self.assertIn("if(!YOUSHUA_WUSHUA)", battery)
        self.assertIn("AD_BAT_MODE_100", battery)
        self.assertIn("AD_BAT_BRUSH_MODE_100", battery)
        self.assertIn("AD_BAT_MODE_COOL", battery)
        self.assertIn("AD_BAT_BRUSH_MODE_COOL", battery)

    def test_pure_brushed_uses_fan_on_pwm_without_brushless_resources(self):
        plan = make_plan_from_path(CLASSIC_BRUSHED_CONFIG_PATH)
        source = render_main_c(plan)
        report = render_report(plan)

        self.assertEqual(plan.config.motor.kind, "brushed_fixed_duty")
        self.assertEqual(plan.pwm.role, "FAN_ON")
        self.assertEqual(plan.pwm.gpio_name, "PC3")
        self.assertEqual(plan.pwm.channel, 2)
        self.assertEqual(plan.pwm.period_register, 147)
        self.assertIsNone(plan.alternate_pwm)
        self.assertEqual(len(plan.adc.channels), 1)
        self.assertEqual(plan.adc.channels[0].result_name, "ADC_BAT_VALUE")

        self.assertIn("#define FAN_ON       PC3", source)
        self.assertNotIn("#define PWM_FAN", source)
        self.assertNotIn("#define AD_FAN", source)
        self.assertNotIn("too_big_cnt", source)
        self.assertNotIn("YOUSHUA_WUSHUA", source)
        self.assertNotIn("detect_youshua_wushua", source)
        self.assertIn("PWMSEL = 0x20;", source)
        self.assertIn("T3PL = 0x93;", source)
        self.assertIn(
            "T3D2L = FAN_PWM_DUTY_BASE\n"
            "        + fan_mode / FAN_PWM_GEAR_DIVISOR;",
            source,
        )
        self.assertIn("#define AD_BAT_MODE_100       256", source)
        self.assertIn(
            "Disabled for this pure brushed profile", report
        )
        self.assertNotIn("AD_FAN u16 accumulation overflow check", report)

    def test_pure_brushed_rejects_brushless_voltage_protection(self):
        raw = json.loads(
            CLASSIC_BRUSHED_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["fan_voltage_protection"] = copy.deepcopy(
            json.loads(
                CLASSIC_CONFIG_PATH.read_text(encoding="utf-8")
            )["features"]["fan_voltage_protection"]
        )
        with self.assertRaises(ConfigError):
            ProjectConfig.from_dict(CLASSIC_BRUSHED_CONFIG_PATH, raw)

    def test_brushless_still_requires_voltage_protection(self):
        raw = json.loads(CLASSIC_CONFIG_PATH.read_text(encoding="utf-8"))
        raw["features"]["fan_voltage_protection"] = {"enabled": False}
        with self.assertRaises(ConfigError):
            ProjectConfig.from_dict(CLASSIC_CONFIG_PATH, raw)

    def test_time_requests_share_only_matching_semantics(self):
        plan = make_plan()
        main_key = "core.scheduler.main_10ms_tick"
        fan_key = "motor.brushless_fixed_duty.fan_control_tick"
        self.assertEqual(
            plan.time_resources.role_flags[main_key],
            plan.time_resources.role_flags[fan_key],
        )
        signals_10ms = [
            signal
            for signal in plan.time_resources.signals
            if signal.period_ms == 10
        ]
        self.assertEqual(len(signals_10ms), 1)
        self.assertEqual(signals_10ms[0].flag_name, "time_10ms_flag")

    def test_time_hierarchy_and_independent_same_period_counters(self):
        base = make_plan()
        extra = (
            TimeRequest(
                owner="input.key",
                role="key_window",
                period_ms=200,
                phase="key_window",
                reset_semantics="event_reset",
            ),
            TimeRequest(
                owner="display.low",
                role="low_flash",
                period_ms=200,
                phase="low_flash",
                reset_semantics="state_reset",
            ),
            TimeRequest(
                owner="display.sequence",
                role="mode_page",
                period_ms=3000,
                phase="system",
                reset_semantics="continuous",
            ),
            TimeRequest(
                owner="battery.chase",
                role="battery_chase",
                period_ms=5000,
                phase="system",
                reset_semantics="continuous",
            ),
            TimeRequest(
                owner="safety.timeout",
                role="auto_off",
                period_ms=14_400_000,
                phase="system",
                reset_semantics="continuous",
            ),
        )
        time_plan = plan_time_resources(base.requests.time + extra)
        source = render_main_c(replace(base, time_resources=time_plan))

        self.assertIn("bit key_window_200ms_flag;", source)
        self.assertIn("u8 key_window_200ms_cnt;", source)
        self.assertIn("bit low_flash_200ms_flag;", source)
        self.assertIn("u8 low_flash_200ms_cnt;", source)
        self.assertNotEqual(
            time_plan.role_counters["input.key.key_window"],
            time_plan.role_counters["display.low.low_flash"],
        )
        self.assertNotIn("u8 time_200ms_cnt;", source)

        self.assertIn("u8 time_500ms_cnt;", source)
        self.assertNotIn("bit time_500ms_flag;", source)
        self.assertIn("if(time_500ms_cnt > 49)", source)
        self.assertIn("if(time_3s_cnt > 5)", source)
        self.assertIn("if(time_5s_cnt > 9)", source)
        self.assertIn("u8 time_1min_cnt;", source)
        self.assertNotIn("bit time_1min_flag;", source)
        self.assertIn("if(time_1min_cnt > 119)", source)
        self.assertIn("if(time_4h_cnt > 239)", source)

    def test_minimal_time_generation_omits_unused_500ms_resources(self):
        source = render_main_c(make_plan())
        self.assertIn("bit time_1ms_flag;", source)
        self.assertIn("bit time_10ms_flag;", source)
        self.assertIn("bit time_100ms_flag;", source)
        self.assertNotIn("time_500ms_flag", source)
        self.assertNotIn("time_500ms_cnt", source)

    def test_adc_mapping_and_accumulation_fit(self):
        plan = make_plan()
        channel = plan.adc.channels[0]
        self.assertEqual(channel.gpio_name, "PC1")
        self.assertEqual(channel.channel, 5)
        self.assertEqual(plan.gpio.adpcon, 0x20)
        self.assertEqual(plan.gpio.trisc, 0x02)
        self.assertLessEqual(4095 * plan.adc.average_samples, 65535)

    def test_high_adc_channel_uses_adpcon1(self):
        raw = copy.deepcopy(load_raw())
        raw["pins"]["AD_FAN"] = 3
        plan = make_plan(raw)
        channel = plan.adc.channels[0]
        self.assertEqual(channel.gpio_name, "PA6")
        self.assertEqual(channel.channel, 13)
        self.assertEqual(plan.gpio.adpcon1, 0x40)
        self.assertEqual(plan.gpio.trisa, 0x40)

    def test_multi_adc_uses_mature_battery_fan_key_scan_order(self):
        config_path = (
            ROOT / "configs" / "hs2811_brushless_adc_fan_battery_key.json"
        )
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        config = ProjectConfig.from_dict(config_path, raw)
        plan = build_generation_plan(config)
        source = render_main_c(plan)

        self.assertEqual(
            [channel.result_name for channel in plan.adc.channels],
            ["ADC_BAT_VALUE", "AD_FAN_VALUE", "AD_KEY_VALUE"],
        )
        self.assertEqual(
            [channel.channel for channel in plan.adc.channels],
            [12, 5, 13],
        )
        self.assertEqual(plan.adc.scan_cycle_ms, 30)
        self.assertEqual(plan.gpio.adpcon, 0x20)
        self.assertEqual(plan.gpio.adpcon1, 0x40)
        self.assertIn("u8 ad_channel;", source)
        self.assertIn("ad_channel = 2;", source)
        self.assertIn("ADM = 0x9C;", source)
        self.assertIn("VREFH = 0x00;", source)
        self.assertIn("u16 ADC_BAT_SUM;", source)
        self.assertIn("u8 ADC_BAT_COUNT;", source)
        self.assertIn("ADC_BAT_VALUE = ADC_BAT_SUM >> 4;", source)
        self.assertIn("else if(ad_channel == 2)", source)
        self.assertIn("wait_cnt = 50;", source)

    def test_slow_adc_clock_gets_conservative_conversion_wait(self):
        config_path = (
            ROOT / "configs" / "hs2811_brushless_pwm1_pa1_120k.json"
        )
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        config = ProjectConfig.from_dict(config_path, raw)
        plan = build_generation_plan(config)
        source = render_main_c(plan)

        self.assertEqual(plan.adc.conversion_wait_limit, 250)
        self.assertIn("wait_cnt = 250;", source)

    def test_exact_adc_source_requests_share_one_result(self):
        base = make_plan()
        request = base.requests.adc[0]
        shared = replace(
            request,
            owner="motor.brushless_fixed_duty",
            role="AD_FAN_FEEDBACK",
        )
        adc_plan = plan_adc_resources(
            load_chip_database(base.config),
            base.requests.adc + (shared,),
        )
        self.assertEqual(len(adc_plan.channels), 1)
        self.assertEqual(
            adc_plan.role_results[
                "motor.brushless_fixed_duty.AD_FAN_FEEDBACK"
            ],
            "AD_FAN_VALUE",
        )

    def test_multi_adc_rejects_different_first_stage_filters(self):
        base = make_plan()
        different_filter = AdcRequest(
            owner="input.ad_key",
            role="AD_KEY",
            source_kind="external_pin",
            physical_pin=3,
            reference="vdd",
            clock="fcpu",
            discard_samples=2,
            average_samples=4,
            secondary_average_samples=1,
            result_name="AD_KEY_VALUE",
            scan_order=30,
            reset_semantics="system_reset",
        )
        with self.assertRaises(ResourceConflictError):
            plan_adc_resources(
                load_chip_database(base.config),
                base.requests.adc + (different_filter,),
            )

    def test_adc_result_cannot_collide_with_shared_state(self):
        base = make_plan()
        invalid = replace(base.requests.adc[0], result_name="ADCDATA_SUM")
        with self.assertRaises(ResourceConflictError):
            plan_adc_resources(
                load_chip_database(base.config),
                (invalid,),
            )

    def test_pin_conflict_is_rejected(self):
        raw = copy.deepcopy(load_raw())
        raw["pins"]["FAN_ON"] = raw["pins"]["PWM_FAN"]
        with self.assertRaises(ResourceConflictError):
            make_plan(raw)

    def test_adc_gpio_sharing_requires_same_owner_and_role(self):
        config_path = (
            ROOT / "configs" / "hs2811_brushless_adc_fan_battery_key.json"
        )
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        raw["pins"]["AD_KEY"] = raw["pins"]["FAN_ON"]
        config = ProjectConfig.from_dict(config_path, raw)
        with self.assertRaises(ResourceConflictError):
            build_generation_plan(config)

    def test_generated_source_has_no_unresolved_slots(self):
        source = render_main_c(make_plan())
        self.assertNotIn("@@", source)
        self.assertIn("PWMSEL = 0xC0;", source)
        self.assertIn("T3PL = 0x3F;", source)
        self.assertIn("ADPCON = 0x20;", source)
        self.assertIn("bit fan_error_flag;", source)
        self.assertIn("OSCM = 0x00;", source)
        self.assertNotIn("fan_start_wait_flag", source)
        self.assertNotIn("fan_stop_wait_flag", source)
        self.assertNotIn("SYSTEM_SAFE_CLOSE", source)

    def test_report_requires_external_system_divider(self):
        report = render_report(make_plan())
        self.assertIn("system-divider setting: `/2`", report)
        self.assertIn("`OSCM = 0x00`", report)

    def test_generation_is_byte_deterministic(self):
        plan = make_plan()
        with tempfile.TemporaryDirectory() as temp:
            first = Path(temp) / "first"
            second = Path(temp) / "second"
            write_generation(plan, first)
            write_generation(plan, second)
            for name in (
                "main.c.in",
                "main.h.in",
                "generation_report.md",
                "acceptance_checklist.md",
                "resolved_plan.json",
            ):
                self.assertEqual(
                    (first / name).read_bytes(),
                    (second / name).read_bytes(),
                    name,
                )

    def test_acceptance_checklist_exposes_product_safety_contract(self):
        checklist = render_acceptance_checklist(make_classic_plan())

        self.assertIn("Brushless startup order", checklist)
        self.assertIn("Brushless shutdown order", checklist)
        self.assertIn("Charging interface: `chrg_stdby_active_low`", checklist)
        self.assertIn("Non-insert discharge does not chase", checklist)
        self.assertIn("Normal sleep registers", checklist)
        self.assertIn("Compile with the target HSIDE/PICC", checklist)

    def test_pure_brushed_checklist_omits_brushless_contract(self):
        checklist = render_acceptance_checklist(
            make_plan_from_path(CLASSIC_BRUSHED_CONFIG_PATH)
        )

        self.assertIn("`FAN_ON` is the brushed PWM output", checklist)
        self.assertIn("No brushless `PWM_FAN`, `AD_FAN`", checklist)
        self.assertNotIn("Brushless startup order", checklist)

    def test_classic_profile_resolves_active_sleep_and_wake_gpio(self):
        plan = make_classic_plan()
        self.assertEqual(plan.gpio.trisa, 0xF0)
        self.assertEqual(plan.gpio.trisc, 0x02)
        self.assertEqual(plan.gpio.pahcon, 0x0F)
        self.assertEqual(plan.gpio.sleep_trisa, 0xF0)
        self.assertEqual(plan.gpio.sleep_trisc, 0x00)
        self.assertEqual(plan.gpio.sleep_pahcon, 0x0F)
        self.assertEqual(plan.gpio.wake_mask_a, 0xF0)
        self.assertEqual(plan.pwm.gpio_name, "PC4")
        self.assertEqual(plan.pwm.channel, 0)

    def test_classic_profile_rejects_non_wake_capable_key_pin(self):
        raw = json.loads(CLASSIC_CONFIG_PATH.read_text(encoding="utf-8"))
        raw["pins"]["KEY1"] = 9
        with self.assertRaises(ResourceConflictError):
            make_classic_plan(raw)

    def test_classic_profile_can_disable_cooling_without_unused_pin(self):
        raw = json.loads(CLASSIC_CONFIG_PATH.read_text(encoding="utf-8"))
        raw["features"]["classic_product"]["cooling_enabled"] = False
        raw["pins"].pop("COOL_EN")

        source = render_main_c(make_classic_plan(raw))

        self.assertNotIn("#define COOL_EN", source)
        self.assertNotIn("COOL_EN =", source)

    def test_cooling_defaults_to_presence_detection_and_restores_output(self):
        source = render_main_c(make_classic_plan())

        self.assertIn("bit YOUWU_COOL;", source)
        self.assertIn("void detect_optional_features(void)", source)
        self.assertIn("YOUWU_COOL = COOL_EN ? 0 : 1;", source)
        self.assertIn("PCHCON |= 0x20;", source)
        self.assertIn("TRISC &= 0xDF;", source)
        self.assertIn("if(delay_cnt == 1)", source)
        self.assertIn("if(!YOUWU_COOL || !fan_mode)", source)

    def test_cooling_can_follow_fan_and_remain_available_while_charging(self):
        raw = json.loads(CLASSIC_CONFIG_PATH.read_text(encoding="utf-8"))
        raw["features"]["classic_product"].pop("cooling_enabled")
        raw["features"]["cooling"] = {
            "enabled": True,
            "presence_detection": False,
            "control_mode": "follow_fan",
            "allow_while_charging": True,
        }

        source = render_main_c(make_classic_plan(raw))

        self.assertIn("YOUWU_COOL = 1;", source)
        self.assertNotIn("detect_optional_features", source)
        self.assertIn("if(YOUWU_COOL && fan_mode)", source)
        self.assertNotIn("COOL_EN = !COOL_EN;", source)

    def test_insert_chrg_interface_uses_pull_down_and_mature_flags(self):
        plan = make_plan_from_path(CLASSIC_INSERT_CHRG_CONFIG_PATH)
        source = render_main_c(plan)

        self.assertEqual(
            plan.config.charging.kind,
            "insert_active_high_chrg_active_low",
        )
        self.assertEqual(plan.gpio.trisa, 0xF0)
        self.assertEqual(plan.gpio.pahcon, 0x1F)
        self.assertEqual(plan.gpio.padcon, 0xEF)
        self.assertEqual(plan.gpio.sleep_padcon, 0xEF)
        self.assertEqual(plan.gpio.wake_mask_a, 0xF0)
        self.assertIn("#define INSERT       PA4", source)
        self.assertIn("#define CHRG         PA5", source)
        self.assertNotIn("#define STDBY", source)
        self.assertIn("if(INSERT)", source)
        self.assertIn("if(!CHRG)", source)
        self.assertIn("charge_on_flag = 1;", source)
        self.assertIn("charge_max_flag = 1;", source)

    def test_static_chrg_max_interface_reuses_mature_state_table(self):
        plan = make_plan_from_path(CLASSIC_CHRG_MAX_STATIC_CONFIG_PATH)
        source = render_main_c(plan)
        requests = {
            request.role: request
            for request in plan.requests.gpio
            if request.owner.startswith("charging.")
        }

        self.assertEqual(
            plan.config.charging.kind,
            "chrg_chrg_max_active_low_static",
        )
        self.assertIn("CHRG", plan.resolved_pins)
        self.assertIn("CHRG_MAX", plan.resolved_pins)
        self.assertNotIn("STDBY", plan.resolved_pins)
        self.assertEqual(requests["CHRG"].pull, "up")
        self.assertEqual(requests["CHRG"].sleep_pull, "up")
        self.assertEqual(requests["CHRG_MAX"].pull, "up")
        self.assertEqual(requests["CHRG_MAX"].sleep_pull, "up")
        self.assertTrue(requests["CHRG"].wake)
        self.assertTrue(requests["CHRG_MAX"].wake)
        self.assertIn("#define CHRG", source)
        self.assertIn("#define CHRG_MAX", source)
        self.assertNotIn("#define STDBY", source)
        self.assertIn("if(!CHRG)", source)
        self.assertIn("else if(!CHRG_MAX)", source)
        self.assertNotIn("out_flag", source)
        self.assertNotIn("charge_wave", source)

    def test_no_charging_interface_omits_pins_flags_and_charge_timers(self):
        plan = make_plan_from_path(CLASSIC_NO_CHARGING_CONFIG_PATH)
        source = render_main_c(plan)
        time_roles = {
            (item.owner, item.role) for item in plan.requests.time
        }

        self.assertFalse(plan.config.charging.enabled)
        self.assertNotIn("CHRG", plan.resolved_pins)
        self.assertNotIn("STDBY", plan.resolved_pins)
        self.assertNotIn("INSERT", plan.resolved_pins)
        self.assertNotIn("#define CHRG", source)
        self.assertNotIn("#define STDBY", source)
        self.assertNotIn("#define INSERT", source)
        self.assertNotIn("bit charge_on_flag;", source)
        self.assertNotIn("bit charge_max_flag;", source)
        self.assertNotIn(("battery.charge", "charge_active"), time_roles)
        self.assertNotIn(("battery.charge", "charge_full"), time_roles)
        self.assertIn("if(charge_num > p_temp)", source)
        self.assertIn("if(type != 2)", source)
        self.assertIn("if(type != 3)", source)

    def test_new_and_legacy_charging_kinds_cannot_conflict(self):
        raw = json.loads(CLASSIC_CONFIG_PATH.read_text(encoding="utf-8"))
        raw["features"]["charging"] = {
            "enabled": True,
            "kind": "insert_active_high_chrg_active_low",
        }
        with self.assertRaises(ConfigError):
            make_classic_plan(raw)

    def test_legacy_charging_kind_remains_supported(self):
        plan = make_classic_plan()

        self.assertTrue(plan.config.charging.enabled)
        self.assertEqual(
            plan.config.charging.kind,
            "chrg_stdby_active_low",
        )

    def test_light_profiles_use_one_mature_output_and_detection_path(self):
        profile_expectations = (
            (
                CLASSIC_LIGHT_FAN_SYNC_CONFIG_PATH,
                "if(YOUWU_LED && fan_mode)",
                None,
            ),
            (
                CLASSIC_LIGHT_ON_OFF_CONFIG_PATH,
                "LED_ON = light_mode ? 1 : 0;",
                "light_mode = !light_mode;",
            ),
            (
                CLASSIC_LIGHT_FLASH_CONFIG_PATH,
                "LED_ON = time_flash_flag;",
                "if(light_mode < 2)",
            ),
        )
        for config_path, output_line, action_line in profile_expectations:
            with self.subTest(config=config_path.name):
                source = render_main_c(make_plan_from_path(config_path))
                self.assertIn("#define LED_ON       PC2", source)
                self.assertIn("bit YOUWU_LED;", source)
                self.assertIn("YOUWU_LED = LED_ON ? 0 : 1;", source)
                self.assertIn("LED_ON = 1;", source)
                self.assertIn("LED_ON = 0;", source)
                self.assertIn(output_line, source)
                if action_line is not None:
                    self.assertIn(action_line, source)
                    self.assertIn("&& !light_mode", source)
                else:
                    self.assertNotIn("u8 light_mode;", source)

    def test_classic_ad_key_reuses_one_pin_for_adc_and_sleep_wake(self):
        plan = make_ad_classic_plan()
        source = render_main_c(plan)
        self.assertEqual(plan.resolved_pins["AD_KEY"], "PA6")
        self.assertEqual(plan.gpio.trisa, 0x70)
        self.assertEqual(plan.gpio.pahcon, 0xCF)
        self.assertEqual(plan.gpio.sleep_trisa, 0x70)
        self.assertEqual(plan.gpio.sleep_pahcon, 0x8F)
        self.assertEqual(plan.gpio.wake_mask_a, 0x70)
        self.assertIn("#define AD_KEY       PA6", source)
        self.assertNotRegex(source, r"(?m)^#define KEY[12]\s+PA")
        self.assertIn("bit KEY1;", source)
        self.assertIn("bit KEY2;", source)
        self.assertIn("VREFH = 0x03;", source)
        self.assertIn("WUACON = 0x70;", source)

    def test_classic_ad_key_decodes_before_mature_key_check(self):
        source = render_main_c(make_ad_classic_plan())
        decode_start = source.index("if(ad_key_ready_flag)")
        key_check_call = source.index("KEY_CHECK();", decode_start)
        self.assertLess(decode_start, key_check_call)
        self.assertIn("#define AD_KEY1_MIN           0", source)
        self.assertIn("#define AD_KEY1_MAX           100", source)
        self.assertIn("#define AD_KEY2_MIN           610", source)
        self.assertIn("#define AD_KEY2_MAX           810", source)
        self.assertIn("KEY1 = 1;\n                KEY2 = 1;", source)
        self.assertIn("KEY1 = 0;", source[decode_start:key_check_call])
        self.assertIn("KEY2 = 0;", source[decode_start:key_check_call])

        digital_source = render_main_c(make_classic_plan())
        ad_key_check = source[
            source.index("\nvoid KEY_CHECK(void)\n{") :
            source.index("\nvoid Key_Clear(void)\n{")
        ]
        digital_key_check = digital_source[
            digital_source.index("\nvoid KEY_CHECK(void)\n{") :
            digital_source.index("\nvoid Key_Clear(void)\n{")
        ]
        self.assertEqual(ad_key_check, digital_key_check)
        report = render_report(make_ad_classic_plan())
        self.assertIn("- AD KEY1 range: `0..100`", report)
        self.assertNotIn(
            "- AD keys, encoders, slide resistors",
            report,
        )

    def test_classic_ad_key_rejects_overlapping_ranges(self):
        raw = json.loads(
            CLASSIC_AD_KEY_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["ad_key"]["keys"][1]["min"] = 100
        with self.assertRaises(ConfigError):
            make_ad_classic_plan(raw)

    def test_classic_ad_key_requires_two_named_ranges(self):
        raw = json.loads(
            CLASSIC_AD_KEY_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["ad_key"]["keys"][1]["name"] = "KEY3"
        with self.assertRaises(ConfigError):
            make_ad_classic_plan(raw)

    def test_legacy_ad_key_rejects_action_override(self):
        raw = json.loads(
            CLASSIC_AD_KEY_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["ad_key"]["keys"][0]["short_action"] = "fan_step_up"
        with self.assertRaises(ConfigError):
            make_ad_classic_plan(raw)

    def test_classic_ad_key_rejects_non_wake_capable_pin(self):
        raw = json.loads(
            CLASSIC_AD_KEY_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["pins"]["AD_KEY"] = 9
        with self.assertRaises(ResourceConflictError):
            make_ad_classic_plan(raw)

    def test_general_ad_key_uses_default_two_key_thresholds(self):
        plan = make_ad_classic_plan_from_path(
            CLASSIC_DEFAULT_AD_KEY_CONFIG_PATH
        )
        source = render_main_c(plan)
        report = render_report(plan)

        self.assertEqual(plan.config.ad_key.threshold_profile, "default_two_key")
        self.assertEqual(
            [
                (item.name, item.minimum_adc, item.maximum_adc)
                for item in plan.config.ad_key.key_bands
            ],
            [("KEY1", 0, 100), ("KEY2", 610, 810)],
        )
        self.assertIn("#define AD_KEY1_MIN           0", source)
        self.assertIn("#define AD_KEY2_MAX           810", source)
        self.assertIn(
            "short=`fan_cycle`; double=`none`; long=`fan_step_up`",
            report,
        )
        self.assertIn(
            "short=`cooling_toggle`; double=`none`; "
            "long=`fan_step_down`",
            report,
        )

    def test_general_ad_key_generates_four_key_complete_path(self):
        plan = make_ad_classic_plan_from_path(
            CLASSIC_FOUR_AD_KEY_CONFIG_PATH
        )
        source = render_main_c(plan)
        report = render_report(plan)

        self.assertEqual(
            [item.name for item in plan.config.ad_key.key_bands],
            ["KEY1", "KEY2", "KEY3", "KEY4"],
        )
        for index in range(1, 5):
            self.assertIn(f"bit KEY{index};", source)
            self.assertIn(f"bit key{index}_short_flag;", source)
            self.assertIn(f"u8 key{index}_delay;", source)
            self.assertIn(f"KEY{index} = 1;", source)
            self.assertIn(f"KEY{index} = 0;", source)
            self.assertIn(f"key{index}_short_flag = 0;", source)
            self.assertIn(f"key{index}_long_flag = 0;", source)
        self.assertIn("#define AD_KEY4_MIN           1810", source)
        self.assertIn("#define AD_KEY4_MAX           2010", source)
        self.assertIn("if(KEY4 && !key4_down_flag)", source)
        self.assertIn(
            "if(key4_short_flag && YOUWU_COOL && fan_mode && !insert_flag)",
            source,
        )
        self.assertIn("fan_mode = FAN_MODE_MIN;", source)
        self.assertIn("if(fan_mode > FAN_MODE_MIN)", source)
        self.assertIn(
            "&& KEY1 && KEY2 && KEY3 && KEY4", source
        )
        self.assertIn("- AD threshold profile: `custom`", report)
        self.assertIn(
            "- AD KEY4 range: `1810..2010`; "
            "short=`cooling_toggle`; double=`none`; long=`none`",
            report,
        )

    def test_ad_key_double_click_delays_single_and_blocks_sleep(self):
        plan = make_ad_classic_plan_from_path(
            CLASSIC_DOUBLE_CLICK_CONFIG_PATH
        )
        source = render_main_c(plan)
        report = render_report(plan)
        requests = {
            (item.owner, item.role): item.period_ms
            for item in plan.requests.time
        }

        self.assertEqual(
            requests[("input.key1", "double_click_window")], 350
        )
        self.assertIn("u8 key1_click_cnt;", source)
        self.assertIn(
            "if(key1_click_cnt && double_click_window_350ms_flag)",
            source,
        )
        self.assertIn("key1_click_cnt = 1;", source)
        self.assertIn("COOL_EN = !COOL_EN;", source)
        self.assertIn(
            "if(YOUWU_COOL && fan_mode && !insert_flag)", source
        )
        self.assertIn("if(fan_mode)", source)
        self.assertIn("fan_mode = FAN_MODE_MIN;", source)
        self.assertIn("&& !key1_click_cnt", source)
        self.assertIn(
            "- AD key double-click window: `350ms`.", report
        )

    def test_ad_key_double_click_window_validation(self):
        raw = json.loads(
            CLASSIC_DOUBLE_CLICK_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["ad_key"]["double_click_ms"] = 355
        with self.assertRaises(ConfigError):
            make_ad_classic_plan(raw)

    def test_multiple_double_click_keys_get_independent_timers(self):
        raw = json.loads(
            CLASSIC_DOUBLE_CLICK_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["ad_key"]["keys"][3]["double_action"] = (
            "light_cycle"
        )
        plan = make_ad_classic_plan(raw)
        source = render_main_c(plan)
        key1_flag = plan.time_resources.role_flags[
            "input.key1.double_click_window"
        ]
        key4_flag = plan.time_resources.role_flags[
            "input.key4.double_click_window"
        ]

        self.assertNotEqual(key1_flag, key4_flag)
        self.assertIn("u8 key1_click_cnt;", source)
        self.assertIn("u8 key4_click_cnt;", source)
        self.assertIn(f"key1_click_cnt && {key1_flag}", source)
        self.assertIn(f"key4_click_cnt && {key4_flag}", source)

    def test_general_ad_key_generates_one_and_three_key_paths(self):
        base = json.loads(
            CLASSIC_FOUR_AD_KEY_CONFIG_PATH.read_text(encoding="utf-8")
        )
        for key_count in (1, 3):
            raw = copy.deepcopy(base)
            raw["features"]["ad_key"]["keys"] = raw["features"]["ad_key"][
                "keys"
            ][:key_count]
            plan = make_ad_classic_plan(raw)
            source = render_main_c(plan)
            for index in range(1, key_count + 1):
                self.assertIn(f"bit KEY{index};", source)
                self.assertIn(f"if(KEY{index} && !key{index}_down_flag)", source)
            for index in range(key_count + 1, 5):
                self.assertNotIn(f"bit KEY{index};", source)
                self.assertNotIn(f"key{index}_delay", source)

    def test_general_ad_key_requires_contiguous_names_and_actions(self):
        raw = json.loads(
            CLASSIC_FOUR_AD_KEY_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["ad_key"]["keys"][2]["name"] = "KEY4"
        raw["features"]["ad_key"]["keys"].pop()
        with self.assertRaises(ConfigError):
            make_ad_classic_plan(raw)

        raw = json.loads(
            CLASSIC_FOUR_AD_KEY_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["ad_key"]["keys"][2].pop("short_action")
        raw["features"]["ad_key"]["keys"][2].pop("long_action")
        with self.assertRaises(ConfigError):
            make_ad_classic_plan(raw)

    def test_general_ad_key_rejects_unimplemented_action(self):
        raw = json.loads(
            CLASSIC_FOUR_AD_KEY_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["ad_key"]["keys"][3]["short_action"] = "mist_toggle"
        with self.assertRaises(ConfigError):
            make_ad_classic_plan(raw)

    def test_slide_switch_profile_plans_normal_and_zero_battery_sleep(self):
        plan = make_slide_switch_classic_plan()
        source = render_main_c(plan)
        self.assertEqual(plan.resolved_pins["SWI_KEY"], "PA7")
        self.assertEqual(plan.gpio.wake_mask_a, 0x98)
        self.assertEqual(plan.gpio.zero_battery_wake_mask_a, 0x18)
        self.assertEqual(plan.gpio.sleep_pahcon, 0x07)
        self.assertEqual(plan.gpio.zero_battery_sleep_pahcon, 0x87)
        self.assertTrue(plan.gpio.has_zero_battery_sleep_override)
        self.assertIn("#define SWI_KEY      PA7", source)
        self.assertIn("if(!charge_num)\n    {\n        PORTA", source)
        self.assertIn("PAHCON = 0x87;", source)
        self.assertIn("WUACON = 0x18;", source)
        self.assertIn("WUACON = 0x98;", source)

    def test_slide_switch_owns_power_and_keys_do_not_clear_fan_error(self):
        source = render_main_c(make_slide_switch_classic_plan())
        mode_start = source.index("\nvoid mode_change(void)\n{")
        mode_end = source.index("\nvoid show_mode_deal(void)\n{", mode_start)
        mode_body = source[mode_start:mode_end]
        key_start = source.index("\nvoid KEY_deal(void)\n{")
        key_end = source.index("\nvoid smg_close(void)\n{", key_start)
        key_body = source[key_start:key_end]
        self.assertIn("if(SWI_KEY)", mode_body)
        self.assertIn("fan_error_flag = 0;", mode_body)
        self.assertIn("fan_mode = FAN_MODE_MIN;", mode_body)
        self.assertTrue(key_body.startswith("\nvoid KEY_deal(void)\n{\n    if(SWI_KEY)"))
        self.assertNotIn("fan_error_flag = 0;", key_body)
        self.assertIn("fan_mode = FAN_MODE_MIN;", key_body)
        self.assertIn("&& (SWI_KEY || !charge_num)", source)

    def test_slide_switch_rejects_unreviewed_polarity(self):
        raw = json.loads(
            CLASSIC_SLIDE_SWITCH_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["slide_switch"]["active_level"] = "high"
        with self.assertRaises(ConfigError):
            make_slide_switch_classic_plan(raw)

    def test_encoder_uses_only_phase_a_runtime_port_change(self):
        plan = make_encoder_classic_plan()
        source = render_main_c(plan)

        self.assertEqual(plan.resolved_pins["ENC_A"], "PA5")
        self.assertEqual(plan.resolved_pins["ENC_B"], "PA4")
        self.assertEqual(plan.gpio.runtime_change_mask_a, 0x20)
        self.assertEqual(plan.gpio.wake_mask_a, 0xC8)
        self.assertEqual(plan.gpio.zero_battery_wake_mask_a, 0x48)
        self.assertIn("WUACON = 0x20;", source)
        self.assertIn("PORTA;\n        PAIF = 0;", source)
        self.assertNotIn("WUACON = 0x30;", source)

    def test_encoder_preserves_mature_full_cycle_validation(self):
        source = render_main_c(make_encoder_classic_plan())

        self.assertIn("if(!encoder_a_last && ENC_A)", source)
        self.assertIn("encoder_phase_b = !ENC_B;", source)
        self.assertIn("else if(encoder_a_last && !ENC_A)", source)
        self.assertIn("encoder_phase_a = ENC_B;", source)
        self.assertIn(
            "if(encoder_phase_a && encoder_phase_b)",
            source,
        )
        self.assertIn(
            "else if(!encoder_phase_a && !encoder_phase_b)",
            source,
        )
        self.assertIn(
            "if(encoder_sub_cnt)\n"
            "                        {\n"
            "                            encoder_sub_cnt--;\n"
            "                        }",
            source,
        )

    def test_encoder_has_independent_acceleration_and_no_key_state(self):
        plan = make_encoder_classic_plan()
        source = render_main_c(plan)
        report = render_report(plan)

        self.assertIn("#define ENCODER_NORMAL_STEP   1", source)
        self.assertIn("#define ENCODER_ACCEL_STEP    5", source)
        self.assertIn("#define ENCODER_ACCEL_EVENTS  3", source)
        self.assertIn(
            "encoder_quick_flag =\n"
            "            (encoder_change_cnt >= ENCODER_ACCEL_EVENTS);",
            source,
        )
        self.assertIn("fan_mode = encoder_max_mode;", source)
        self.assertIn("#define FAN_MODE_MIN          1", source)
        self.assertIn("fan_mode = FAN_MODE_MIN;", source)
        self.assertNotRegex(source, r"(?m)^bit key[12]_")
        self.assertNotRegex(source, r"(?m)^u8 key[12]_delay")
        self.assertNotIn("#define COOL_EN", source)
        self.assertIn("mature full-cycle A-edge validation", report)
        self.assertNotIn("encoders, slide resistors", report)

    def test_encoder_sleep_does_not_wait_forever_on_half_cycle(self):
        source = render_main_c(make_encoder_classic_plan())
        sleep_start = source.index(
            "if(!low_cnt && !fan_mode && !insert_flag"
        )
        sleep_end = source.index("file_sleep_mode();", sleep_start)
        sleep_condition = source[sleep_start:sleep_end]

        self.assertIn("!encoder_add_cnt && !encoder_sub_cnt", sleep_condition)
        self.assertNotIn("encoder_cycle_flag", sleep_condition)
        self.assertIn("encoder_cycle_flag = 0;", source)

    def test_encoder_requires_port_a_phase_a_and_valid_gear_range(self):
        raw = json.loads(
            CLASSIC_ENCODER_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["pins"]["ENC_A"] = 9
        with self.assertRaises(ResourceConflictError):
            make_encoder_classic_plan(raw)

        raw = json.loads(
            CLASSIC_ENCODER_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["classic_product"]["gear_range"]["minimum"] = 0
        with self.assertRaises(ConfigError):
            make_encoder_classic_plan(raw)

    def test_encoder_continuous_range_is_independent_of_gear_steps(self):
        raw = json.loads(
            CLASSIC_ENCODER_CONFIG_PATH.read_text(encoding="utf-8")
        )
        classic = raw["features"]["classic_product"]
        classic["gear_range"] = {"minimum": 20, "maximum": 120}
        classic["charge_max_gear"] = 60

        plan = make_encoder_classic_plan(raw)
        source = render_main_c(plan)

        self.assertEqual(plan.config.classic_product.gear_mode, "continuous")
        self.assertEqual(plan.config.classic_product.minimum_gear, 20)
        self.assertEqual(plan.config.classic_product.maximum_gear, 120)
        self.assertEqual(plan.config.classic_product.gear_steps, (20, 120))
        self.assertIn("#define FAN_MODE_MIN          20", source)
        self.assertIn("#define FAN_MODE_MAX          120", source)
        self.assertIn("if(fan_mode > FAN_MODE_MIN)", source)
        self.assertIn("fan_mode = FAN_MODE_MIN;", source)

    def test_legacy_encoder_gear_steps_keep_only_continuous_endpoints(self):
        raw = json.loads(
            CLASSIC_ENCODER_CONFIG_PATH.read_text(encoding="utf-8")
        )
        classic = raw["features"]["classic_product"]
        classic.pop("gear_range")
        classic["gear_steps"] = [1, 25, 50, 75, 100]

        plan = make_encoder_classic_plan(raw)

        self.assertEqual(plan.config.classic_product.gear_mode, "continuous")
        self.assertEqual(plan.config.classic_product.gear_steps, (1, 100))

    def test_encoder_charge_limit_smaller_than_accelerated_step_is_safe(self):
        raw = json.loads(
            CLASSIC_ENCODER_CONFIG_PATH.read_text(encoding="utf-8")
        )
        classic = raw["features"]["classic_product"]
        classic["gear_range"] = {"minimum": 20, "maximum": 120}
        classic["charge_max_gear"] = 40
        raw["features"]["encoder"]["accelerated_step"] = 50

        source = render_main_c(make_encoder_classic_plan(raw))

        self.assertIn(
            "if(encoder_step <= encoder_max_mode - fan_mode)", source
        )
        self.assertNotIn(
            "fan_mode <= encoder_max_mode - encoder_step", source
        )

    def test_continuous_and_discrete_gear_fields_cannot_be_mixed(self):
        raw = json.loads(
            CLASSIC_ENCODER_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["classic_product"]["gear_steps"] = [1, 100]
        with self.assertRaises(ConfigError):
            make_encoder_classic_plan(raw)

        raw = json.loads(CLASSIC_CONFIG_PATH.read_text(encoding="utf-8"))
        raw["features"]["classic_product"]["gear_range"] = {
            "minimum": 20,
            "maximum": 100,
        }
        with self.assertRaises(ConfigError):
            make_classic_plan(raw)

    def test_encoder_requires_slide_switch_and_disables_long_adjust(self):
        raw = json.loads(
            CLASSIC_ENCODER_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["slide_switch"]["enabled"] = False
        with self.assertRaises(ConfigError):
            make_encoder_classic_plan(raw)

        raw = json.loads(
            CLASSIC_ENCODER_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["classic_product"]["long_adjust"] = True
        with self.assertRaises(ConfigError):
            make_encoder_classic_plan(raw)

    def test_slider_adc_keeps_eight_sample_sum_without_changing_other_results(self):
        plan = make_slider_classic_plan()
        source = render_main_c(plan)
        channels = {item.result_name: item for item in plan.adc.channels}

        self.assertEqual(channels["ADC_BAT_VALUE"].result_mode, "average")
        self.assertEqual(channels["AD_FAN_VALUE"].result_mode, "average")
        self.assertEqual(channels["AD_SLIDER_SUM"].result_mode, "sum")
        self.assertEqual(channels["AD_SLIDER_SUM"].average_samples, 96)
        self.assertIn("ADC_GROUP_SUM / 12", source)
        self.assertIn("ADCDATA_SUM <<= 3;\n            AD_SLIDER_SUM", source)
        self.assertIn(
            "else if(ad_channel == 2)\n"
            "        {\n"
            "            ADCDATA_SUM <<= 3;",
            source,
        )

    def test_slider_preserves_mature_deadband_and_confirmation_logic(self):
        source = render_main_c(make_slider_classic_plan())

        self.assertIn(
            "#define ADC_SLIDER_MIN_GEAR    31129UL", source
        )
        self.assertIn(
            "#define ADC_SLIDER_MAX_GEAR    1638UL", source
        )
        self.assertIn("#define ADC_STEP               297", source)
        self.assertIn("#define ADC_DEADBAND           891UL", source)
        self.assertIn("#define ADC_CONFIRM_COUNT      3", source)
        self.assertIn("old_res_val = 60000;", source)
        self.assertIn("> ADC_DEADBAND)", source)
        self.assertIn(
            "if(res_change_cnt < ADC_CONFIRM_COUNT - 1)", source
        )
        self.assertIn("old_res_val = AD_SLIDER_SUM;", source)
        self.assertIn(
            "if(fan_mode != slider_target_mode)\n"
            "                    {\n"
            "                        fan_mode = slider_target_mode;\n"
            "                        show_mode_change();",
            source,
        )

    def test_slider_single_key_owns_power_and_long_press_only_controls_cooling(self):
        source = render_main_c(make_slider_classic_plan())
        key_start = source.index("\nvoid KEY_deal(void)\n{")
        key_end = source.index("\nvoid smg_close(void)\n{", key_start)
        key_body = source[key_start:key_end]

        self.assertIn("fan_start = !fan_start;", key_body)
        self.assertIn("fan_mode = FAN_MODE_MIN;", key_body)
        self.assertIn(
            "if(YOUWU_COOL && fan_start && (charge_num || insert_flag) "
            "&& !insert_flag)",
            key_body,
        )
        self.assertIn("COOL_EN = !COOL_EN;", key_body)
        self.assertNotIn("fan_mode++;", key_body)
        self.assertNotIn("fan_mode--;", key_body)
        self.assertNotRegex(source, r"(?m)^bit key[12]_")

    def test_slider_charging_ignores_slider_and_uses_configured_limit(self):
        source = render_main_c(make_slider_classic_plan())
        mode_start = source.index("\nvoid mode_change(void)\n{")
        mode_end = source.index("\nvoid show_mode_deal(void)\n{", mode_start)
        mode_body = source[mode_start:mode_end]

        self.assertIn(
            "if(insert_flag)\n"
            "    {\n"
            "        COOL_EN = 0;\n"
            "        if(fan_start)\n"
            "        {\n"
            "            fan_mode = CHARGE_MAX_GEAR;",
            mode_body,
        )
        self.assertIn(
            "if(fan_start && !insert_flag && charge_num)", source
        )
        self.assertIn(
            "else\n"
            "                {\n"
            "                    old_res_val = 60000;\n"
            "                    res_change_cnt = 0;",
            source,
        )

    def test_slider_range_and_charging_limit_are_independently_configurable(self):
        raw = json.loads(
            CLASSIC_SLIDER_CONFIG_PATH.read_text(encoding="utf-8")
        )
        classic = raw["features"]["classic_product"]
        classic["gear_range"] = {"minimum": 20, "maximum": 120}
        classic["charge_max_gear"] = 40

        plan = make_slider_classic_plan(raw)
        source = render_main_c(plan)

        self.assertEqual(plan.config.classic_product.minimum_gear, 20)
        self.assertEqual(plan.config.classic_product.maximum_gear, 120)
        self.assertIn("#define FAN_MODE_MIN          20", source)
        self.assertIn("#define FAN_MODE_MAX          120", source)
        self.assertIn("#define CHARGE_MAX_GEAR       40", source)
        self.assertIn("slider_target_mode = 20;", source)
        self.assertIn("slider_target_mode = 120;", source)
        self.assertIn("fan_mode = CHARGE_MAX_GEAR;", source)

    def test_legacy_slider_gear_steps_keep_only_continuous_endpoints(self):
        raw = json.loads(
            CLASSIC_SLIDER_CONFIG_PATH.read_text(encoding="utf-8")
        )
        classic = raw["features"]["classic_product"]
        classic.pop("gear_range")
        classic["gear_steps"] = [1, 25, 50, 75, 100]

        plan = make_slider_classic_plan(raw)

        self.assertEqual(plan.config.classic_product.gear_mode, "continuous")
        self.assertEqual(plan.config.classic_product.gear_steps, (1, 100))

    def test_continuous_charge_limit_must_stay_inside_gear_range(self):
        raw = json.loads(
            CLASSIC_SLIDER_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["classic_product"]["charge_max_gear"] = 101

        with self.assertRaises(ConfigError):
            make_slider_classic_plan(raw)

    def test_slider_supply_is_high_awake_low_asleep_and_key_gates_sleep(self):
        plan = make_slider_classic_plan()
        source = render_main_c(plan)
        sleep_start = source.index("\nvoid file_sleep_mode(void)\n{")
        sleep_end = source.index("\nvoid main(void)\n{", sleep_start)
        sleep_body = source[sleep_start:sleep_end]
        sleep_condition_start = source.index(
            "if(!low_cnt && !fan_mode && !insert_flag"
        )
        sleep_condition_end = source.index(
            "file_sleep_mode();", sleep_condition_start
        )
        sleep_condition = source[
            sleep_condition_start:sleep_condition_end
        ]

        self.assertEqual(plan.resolved_pins["SLIDER_ON"], "PA4")
        self.assertEqual(plan.gpio.porta & 0x10, 0x10)
        self.assertEqual(plan.gpio.sleep_porta & 0x10, 0)
        self.assertIn("PORTA = 0x10;", source)
        self.assertIn("PORTA = 0x00;", sleep_body)
        self.assertIn("&& KEY", sleep_condition)
        self.assertIn("&& !fan_start && !key_down_flag", sleep_condition)
        self.assertIn("&& !key_short_flag && !key_long_flag", sleep_condition)
        self.assertIn("old_res_val = 60000;", sleep_body)

    def test_slider_direction_and_endpoint_configuration_must_match(self):
        raw = json.loads(
            CLASSIC_SLIDER_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["slide_resistor"]["low_gear_at_high_adc"] = False
        with self.assertRaises(ConfigError):
            make_slider_classic_plan(raw)

        raw = json.loads(
            CLASSIC_SLIDER_CONFIG_PATH.read_text(encoding="utf-8")
        )
        slider = raw["features"]["slide_resistor"]
        slider["low_gear_adc_sum"] = 1638
        slider["high_gear_adc_sum"] = 31129
        slider["low_gear_at_high_adc"] = False
        source = render_main_c(make_slider_classic_plan(raw))
        self.assertIn(
            "if(AD_SLIDER_SUM <= ADC_SLIDER_MIN_GEAR)", source
        )
        self.assertIn("((unsigned long)old_res_val", source)
        self.assertIn(
            "- (unsigned long)ADC_SLIDER_MIN_GEAR)", source
        )

    def test_slider_requires_mature_two_discard_eight_sum_shape(self):
        raw = json.loads(
            CLASSIC_SLIDER_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["slide_resistor"]["accumulation_samples"] = 4
        with self.assertRaises(ConfigError):
            make_slider_classic_plan(raw)

        raw = json.loads(
            CLASSIC_SLIDER_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["slide_resistor"]["discard_samples"] = 1
        with self.assertRaises(ConfigError):
            make_slider_classic_plan(raw)

    def test_slider_report_describes_real_range_and_supported_profile(self):
        report = render_report(make_slider_classic_plan())

        self.assertIn("- Slider gear range: `1 -> 100`", report)
        self.assertIn(
            "- Slider accumulation/deadband/confirmation: "
            "`8` / `3` gears / `3` complete ADC results.",
            report,
        )
        self.assertNotIn("- Short-press gear sequence:", report)
        self.assertNotIn(
            "AD keys, encoders, slide resistors, mist", report
        )

    def test_existing_classic_sources_remain_byte_identical(self):
        for config_path in SHOWCASE_CONFIGS:
            if config_path == CLASSIC_SLIDER_CONFIG_PATH:
                continue
            example = ROOT / "examples" / config_path.stem / "main.c.in"
            if not example.exists():
                continue
            with self.subTest(config=config_path.name):
                self.assertEqual(
                    render_main_c(make_plan_from_path(config_path)),
                    example.read_text(encoding="utf-8"),
                )

    def test_classic_charge_limit_must_be_a_short_press_gear(self):
        raw = json.loads(CLASSIC_CONFIG_PATH.read_text(encoding="utf-8"))
        raw["features"]["classic_product"]["charge_max_gear"] = 50
        with self.assertRaises(ConfigError):
            make_classic_plan(raw)

    def test_classic_rejects_non_monotonic_battery_thresholds(self):
        raw = json.loads(CLASSIC_CONFIG_PATH.read_text(encoding="utf-8"))
        thresholds = raw["features"]["battery_monitor"]["business"]["thresholds"]
        thresholds["p50"] = thresholds["p10"]
        with self.assertRaises(ConfigError):
            make_classic_plan(raw)

    def test_classic_rejects_duty_curve_larger_than_pwm_period(self):
        raw = json.loads(CLASSIC_CONFIG_PATH.read_text(encoding="utf-8"))
        raw["features"]["motor"]["duty_curve"]["base_count"] = 63
        with self.assertRaises(ResourceConflictError):
            make_classic_plan(raw)

    def test_classic_rejects_unknown_blink_target(self):
        raw = json.loads(CLASSIC_CONFIG_PATH.read_text(encoding="utf-8"))
        raw["features"]["classic_product"]["charge_blink_target"] = "guess"
        with self.assertRaises(ConfigError):
            make_classic_plan(raw)

    def test_custom_display_generates_mapping_and_charge_icon_blink(self):
        plan = make_plan_from_path(CLASSIC_CUSTOM_DISPLAY_CONFIG_PATH)
        source = render_main_c(plan)
        self.assertEqual(plan.config.display.profile, "custom_charlieplex_188")
        self.assertEqual(plan.config.display.pin_count, 5)
        self.assertEqual(len(plan.config.display.connections), 19)
        self.assertIn(
            "if(!(Data[0] & 0x10)) { IO_IN_LED_1; }",
            source,
        )
        self.assertIn("if(insert_flag)\n    {\n        d0 |= 0x10;", source)
        self.assertIn("d0 &= 0xEF;", source)

    def test_custom_display_rejects_duplicate_directed_pair(self):
        raw = json.loads(
            CLASSIC_CUSTOM_DISPLAY_CONFIG_PATH.read_text(encoding="utf-8")
        )
        raw["features"]["display"]["connections"]["icon.charge"] = {
            "positive": 2,
            "negative": 5,
        }
        with self.assertRaises(ConfigError):
            make_classic_plan(raw)

    def test_custom_display_rejects_missing_digit_segment(self):
        raw = json.loads(
            CLASSIC_CUSTOM_DISPLAY_CONFIG_PATH.read_text(encoding="utf-8")
        )
        del raw["features"]["display"]["connections"]["ones.g"]
        with self.assertRaises(ConfigError):
            make_classic_plan(raw)

    def test_charge_icon_blink_requires_mapped_charge_icon(self):
        raw = json.loads(CLASSIC_CONFIG_PATH.read_text(encoding="utf-8"))
        raw["features"]["classic_product"]["charge_blink_target"] = (
            "charge_icon"
        )
        with self.assertRaises(ConfigError):
            make_classic_plan(raw)

    def test_custom_display_behavior_uses_separate_page_timers(self):
        plan = make_plan_from_path(
            CLASSIC_CUSTOM_DISPLAY_BEHAVIOR_CONFIG_PATH
        )
        source = render_main_c(plan)
        requests = {
            (item.owner, item.role): item.period_ms
            for item in plan.requests.time
        }
        self.assertEqual(
            requests[("display.page", "gear_event")], 3000
        )
        self.assertEqual(
            requests[("display.page", "battery_preview")], 5000
        )
        self.assertNotIn(("display.page", "page_3s"), requests)
        self.assertIn("step_cnt = insert_flag ? 1 : 2;", source)
        self.assertIn("if(show_mode)", source)
        self.assertIn(
            "if(step_cnt && battery_preview_5s_flag)", source
        )

    def test_battery_idle_behavior_skips_battery_preview_timer(self):
        raw = json.loads(
            CLASSIC_CUSTOM_DISPLAY_BEHAVIOR_CONFIG_PATH.read_text(
                encoding="utf-8"
            )
        )
        behavior = raw["features"]["display"]["behavior"]
        behavior["normal_idle_page"] = "battery"
        behavior["normal_battery_preview_ms"] = 0
        plan = make_classic_plan(raw)
        source = render_main_c(plan)
        requests = {
            (item.owner, item.role)
            for item in plan.requests.time
        }
        self.assertNotIn(
            ("display.page", "battery_preview"), requests
        )
        self.assertIn("step_cnt = 1;", source)

    def test_battery_idle_rejects_redundant_preview_period(self):
        raw = json.loads(
            CLASSIC_CUSTOM_DISPLAY_BEHAVIOR_CONFIG_PATH.read_text(
                encoding="utf-8"
            )
        )
        raw["features"]["display"]["behavior"]["normal_idle_page"] = (
            "battery"
        )
        with self.assertRaises(ConfigError):
            make_classic_plan(raw)

    def test_classic_adc_results_have_one_shot_ready_flags(self):
        plan = make_classic_plan()
        source = render_main_c(plan)
        battery = plan.adc.channels[0]
        fan = plan.adc.channels[1]
        self.assertEqual(battery.ready_flag_names, ("adc_bat_ready_flag",))
        self.assertEqual(fan.ready_flag_names, ("ad_fan_ready_flag",))
        self.assertIn("adc_bat_ready_flag = 1;", source)
        self.assertIn("ad_fan_ready_flag = 1;", source)
        self.assertIn("if(ad_fan_ready_flag)", source)
        self.assertIn("ad_fan_ready_flag = 0;", source)

    def test_classic_battery_steps_are_literal_and_monotonic(self):
        source = render_main_c(make_classic_plan())
        expected = {
            "AD_BAT_STEP_0_5": 640,
            "AD_BAT_STEP_5_10": 185,
            "AD_BAT_STEP_10_50": 14,
            "AD_BAT_STEP_50_80": 25,
            "AD_BAT_STEP_80_100": 52,
        }
        for name, value in expected.items():
            self.assertRegex(
                source,
                rf"(?m)^#define {name}\s+{value}$",
            )
        self.assertNotIn("(AD_BAT_100 - AD_BAT_80) / 20", source)
        self.assertNotIn("(AD_BAT_50 - AD_BAT_10) / 40", source)

        points = (
            (15360, 17920, 1, expected["AD_BAT_STEP_0_5"], 5),
            (17920, 18841, 5, expected["AD_BAT_STEP_5_10"], 10),
            (18841, 19384, 10, expected["AD_BAT_STEP_10_50"], 50),
            (19384, 20122, 50, expected["AD_BAT_STEP_50_80"], 80),
            (20122, 21145, 80, expected["AD_BAT_STEP_80_100"], 100),
        )
        previous = 0
        for value in range(15360, 21146):
            if value >= 21145:
                percent = 100
            else:
                percent = 0
                for low, high, base, step, ceiling in points:
                    if low <= value < high:
                        increments = (value - low + step - 1) // step
                        percent = min(base + increments, ceiling)
                        break
            self.assertGreaterEqual(percent, previous)
            previous = percent

    def test_classic_charge_cycle_can_turn_off_at_charge_limit(self):
        source = render_main_c(make_classic_plan())
        key_start = source.index("\nvoid KEY_deal(void)\n{")
        key_end = source.index("\nvoid smg_close(void)\n{", key_start)
        key_body = source[key_start:key_end]
        insert_start = key_body.index("if(insert_flag)")
        charge_branch = key_body[
            insert_start : key_body.index("\n        else\n        {", insert_start)
        ]
        self.assertIn("fan_mode < 60", charge_branch)
        self.assertNotIn("fan_mode < 80", charge_branch)
        self.assertIn("fan_mode = 0;", charge_branch)

    def test_classic_display_is_atomic_and_charge_num_drives_blink(self):
        source = render_main_c(make_classic_plan())
        show_start = source.index("\nvoid show_mode_deal(void)\n{")
        show_end = source.index("\nvoid KEY_CHECK(void)\n{", show_start)
        show_body = source[show_start:show_end]
        self.assertIn(
            "if(insert_flag && charge_num < 100 && time_flash_flag)",
            show_body,
        )
        self.assertNotIn("charge_on_flag && time_flash_flag", show_body)
        self.assertLess(show_body.index("u8 d0;"), show_body.index("GIE = 0;"))
        self.assertLess(show_body.index("GIE = 0;"), show_body.index("Data[0]"))
        self.assertLess(show_body.index("Data[2]"), show_body.index("GIE = 1;"))

    def test_classic_brushless_sequence_and_sleep_gate(self):
        source = render_main_c(make_classic_plan())
        fan_start = source.index("\nvoid AD_fan_deal(void)\n{")
        fan_end = source.index("\nvoid clean_other_time", fan_start)
        fan_body = source[fan_start:fan_end]
        self.assertLess(
            fan_body.index("FAN_ON = 1;"),
            fan_body.index("T3PWM0EN = 1;"),
        )
        off_block = fan_body[
            fan_body.index("if(!fan_mode || fan_error_flag)") :
            fan_body.index("if(!FAN_ON)")
        ]
        self.assertLess(
            off_block.index("T3PWM0EN = 0;"),
            off_block.index("FAN_ON = 0;"),
        )
        self.assertIn(
            "&& !T3PWM0EN && !T3REN && !FAN_ON",
            source,
        )
        self.assertIn("WUACON = 0xF0;", source)
        self.assertIn("wake_guard_cnt = 20;", source)

    def test_classic_non_insert_battery_has_no_upward_chase(self):
        source = render_main_c(make_classic_plan())
        battery_start = source.index("u8 v_bat_deal(void)\n{")
        battery_end = source.index(
            "\nvoid file_sleep_mode(void)\n{", battery_start
        )
        battery_body = source[battery_start:battery_end]
        self.assertIn("else if(charge_num > p_temp)", battery_body)
        self.assertNotIn("else if(charge_num < p_temp)", battery_body)

    def test_classic_report_identifies_complete_review_profile(self):
        report = render_report(make_classic_plan())
        self.assertIn("complete classic profile", report)
        self.assertIn("compiler and bench validation required", report)
        self.assertIn("`IO_LED_5`", report)
        self.assertIn("20 -> 40 -> 60 -> 80 -> 100 -> 0", report)
        self.assertIn("Duty curve: `12 + fan_mode / 4`", report)

    def test_classic_200khz_variant_keeps_its_display_policy(self):
        plan = make_plan_from_path(CLASSIC_200K_CONFIG_PATH)
        source = render_main_c(plan)
        self.assertEqual(plan.pwm.period_register, 79)
        self.assertEqual(plan.pwm.actual_frequency_hz, 200000)
        self.assertIn("#define FAN_PWM_DUTY_BASE     11", source)
        self.assertIn("#define FAN_PWM_GEAR_DIVISOR  4", source)
        self.assertIn("d0 &= 0xFB;", source)
        self.assertIn(
            "if(low_power_flag && !insert_flag && time_flash_flag)\n"
            "        {\n"
            "            d2 = 0;\n"
            "        }",
            source,
        )
        self.assertIn("#define AD_FAN_CONFIRM_COUNT  13", source)

    def test_classic_199_variant_scales_segments_and_omits_long_actions(self):
        plan = make_plan_from_path(CLASSIC_199_CONFIG_PATH)
        source = render_main_c(plan)
        for limit in (40, 80, 120, 160):
            self.assertIn(f"fan_mode < {limit}", source)
        self.assertIn("#define FAN_PWM_DUTY_BASE     8", source)
        self.assertIn("#define FAN_PWM_GEAR_DIVISOR  4", source)
        self.assertNotIn("if(key1_long_flag)", source)
        self.assertNotIn("if(key2_long_flag)", source)
        self.assertLessEqual(8 + 199 // 4, plan.pwm.period_register)


if __name__ == "__main__":
    unittest.main()
