"""Prevent single-result overvoltage shutdown from re-entering configurations."""
import json
from pathlib import Path
import unittest

from fanforge.errors import ConfigError
from fanforge.models import ProjectConfig

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/hs2811_classic_fixed_voltage_7_3.json"


class ProtectionConfirmationTests(unittest.TestCase):
    def test_single_result_and_out_of_range_counts_rejected(self):
        for count in (0, 1, 256):
            raw = json.loads(CONFIG.read_bytes())
            raw["features"]["fan_voltage_protection"]["consecutive_confirmations"] = count
            with self.subTest(count=count), self.assertRaisesRegex(ConfigError, "between 2 and 255"):
                ProjectConfig.from_dict(CONFIG, raw)

    def test_multiple_result_boundary_counts_accepted(self):
        for count in (2, 13, 255):
            raw = json.loads(CONFIG.read_bytes())
            raw["features"]["fan_voltage_protection"]["consecutive_confirmations"] = count
            config = ProjectConfig.from_dict(CONFIG, raw)
            self.assertEqual(config.fan_protection.consecutive_confirmations, count)

    def test_all_enabled_examples_use_f824_thirteen_result_rule(self):
        for path in (ROOT / "configs").glob("*.json"):
            raw = json.loads(path.read_bytes())
            protection = raw["features"].get("fan_voltage_protection", {})
            if protection.get("enabled"):
                with self.subTest(config=path.name):
                    self.assertEqual(protection["consecutive_confirmations"], 13)


if __name__ == "__main__":
    unittest.main()
