import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = ROOT / "tools" / "collect_feature_matrix.py"
SPEC = importlib.util.spec_from_file_location("collect_feature_matrix", SCRIPT_PATH)
MATRIX = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MATRIX)


FAN_SOURCE = """
void ADC_Init(void) {}
void ADC_Sample(void) {}
void pwm_init(void) {}
void AD_fan_deal(void) {}
void mode_change(void) {}
void KEY_deal(void) {}
void file_sleep_mode(void) {}
void smg_188_scan(void) {}
void main(void) {}
void extra(void) {
    PAHCON = 0xFF;
    T3C1 = 0x17;
    ADPCON = 0x01;
}
"""


class FeatureMatrixTests(unittest.TestCase):
    def test_scan_accepts_fan_and_rejects_sdk_demo(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fan = root / "26_07_29_TEST" / "PROJECT" / "main.c"
            fan.parent.mkdir(parents=True)
            fan.write_text(FAN_SOURCE, encoding="ascii")

            demo = root / "SDK" / "main.c"
            demo.parent.mkdir(parents=True)
            demo.write_text(
                "void main(void) { PAHCON=0; T3C1=0; ADPCON=0; }\n",
                encoding="ascii",
            )

            records, rejected = MATRIX.collect_sources(root)

            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].project, "26_07_29_TEST")
            self.assertIn(("SDK\\main.c", "unreadable_or_not_c"), rejected)

    def test_reference_report_is_utf8(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fan = root / "26_07_29_TEST" / "PROJECT" / "main.c"
            fan.parent.mkdir(parents=True)
            fan.write_text(FAN_SOURCE, encoding="ascii")
            output = root / "evidence"
            output.mkdir()

            records, rejected = MATRIX.collect_sources(root)
            MATRIX.write_reference_review(records, rejected, root, output)
            report = (output / "hs_fan_feature_references.md").read_text(
                encoding="utf-8"
            )

            self.assertIn("# HS2811风扇功能扫描", report)
            self.assertIn("使用限制", report)


if __name__ == "__main__":
    unittest.main()
