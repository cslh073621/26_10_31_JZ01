import copy
import json
import tempfile
import unittest
from pathlib import Path

from fanforge_gui.adapter import FanForgeAdapter, OutputExistsError, discover_presets
from fanforge_gui.core import (
    ConfigDocument,
    choices_for_path,
    output_directory_value,
    project_name,
    safe_directory_name,
    summarize_config,
)


ROOT = Path(__file__).resolve().parent.parent
CONFIGS = ROOT / "configs"
MINIMAL = CONFIGS / "hs2811_brushless_minimal.json"


class ConfigDocumentTests(unittest.TestCase):
    def test_document_deep_copies_and_preserves_unknown_values(self):
        raw = {"project": {"name": "A"}, "future": {"option": [1, True]}}
        document = ConfigDocument(raw)
        raw["future"]["option"][0] = 99

        self.assertEqual(document.get(("future", "option", 0)), 1)
        round_trip = json.loads(document.to_json())
        self.assertEqual(round_trip["future"], {"option": [1, True]})

    def test_document_edits_nested_scalar_without_dropping_siblings(self):
        raw = json.loads(MINIMAL.read_text(encoding="utf-8"))
        original = copy.deepcopy(raw)
        document = ConfigDocument(raw, source_path=MINIMAL)

        document.set(("project", "name"), "GUI_TEST")

        result = document.to_dict()
        self.assertEqual(result["project"]["name"], "GUI_TEST")
        self.assertEqual(result["features"], original["features"])


class FanForgeServiceTests(unittest.TestCase):
    def setUp(self):
        self.adapter = FanForgeAdapter()

    def test_discovers_and_validates_bundled_presets(self):
        presets = discover_presets()

        self.assertGreaterEqual(len(presets), 20)
        raw = json.loads(presets[0].path.read_text(encoding="utf-8"))
        _, plan = self.adapter.validate(raw, source_path=presets[0].path)
        self.assertEqual(
            self.adapter.summarize(plan).project,
            raw["project"]["name"],
        )

    def test_generate_uses_backend_and_protects_existing_output(self):
        raw = json.loads(MINIMAL.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "generated"
            self.adapter.generate(raw, output, source_path=MINIMAL)

            self.assertTrue((output / "main.c.in").is_file())
            self.assertTrue((output / "resolved_plan.json").is_file())
            with self.assertRaises(OutputExistsError):
                self.adapter.generate(raw, output, source_path=MINIMAL)

            self.adapter.generate(raw, output, source_path=MINIMAL, force=True)

    def test_catalog_drives_known_choices(self):
        catalog = self.adapter.capability_catalog()

        self.assertIn(
            "brushless_fixed_duty",
            choices_for_path(("features", "motor", "kind"), catalog),
        )
        self.assertEqual(
            choices_for_path(("mcu", "system_divider"), catalog),
            (1, 2, 4, 8),
        )


class GuiDisplayHelpersTests(unittest.TestCase):
    def test_project_helpers_and_summary_are_configuration_driven(self):
        raw = json.loads(MINIMAL.read_text(encoding="utf-8"))

        self.assertEqual(project_name(raw), raw["project"]["name"])
        self.assertEqual(safe_directory_name('A:B/C*D'), "A_B_C_D")
        summary = dict(summarize_config(raw))
        self.assertEqual(summary["项目名称"], raw["project"]["name"])
        self.assertIn("brushless", summary["电机方案"])


    def test_output_directory_is_preserved_when_document_changes(self):
        raw = json.loads(MINIMAL.read_text(encoding="utf-8"))
        selected = r"H:\WorkSpace\HS\FanForge\generated\my-board"

        self.assertEqual(output_directory_value(selected, raw), selected)

    def test_output_directory_defaults_only_when_empty(self):
        raw = json.loads(MINIMAL.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            (home / "Documents").mkdir()
            expected = (
                home
                / "Documents"
                / "FanForgeOutputs"
                / safe_directory_name(project_name(raw))
            )

            self.assertEqual(
                Path(output_directory_value("", raw, home=home)),
                expected,
            )


if __name__ == "__main__":
    unittest.main()
