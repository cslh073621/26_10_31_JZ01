"""Source/configuration and arithmetic regression checks, not board simulation."""
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = (ROOT / "PROJECT/main.c").read_bytes()
text = SOURCE.decode("ascii").replace("\r\n", "\n")

def body(name):
    start = text.index(name + "\n{") + len(name) + 1
    depth = 0
    for end in range(start, len(text)):
        depth += (text[end] == "{") - (text[end] == "}")
        if depth == 0:
            return text[start:end + 1]
    raise AssertionError(name)

def constant(name):
    return int(re.search(r"^#define\s+" + name + r"\s+(\d+)", text, re.M).group(1))

assert b"\r\r\n" not in SOURCE and "\n\n\n" not in text
compare = body("u8 Get_Fin_Val(u16 temp_val)")
assert "AD_FAN_TARGET_9V" in compare and "fan_mode" not in compare
# Independent divider conversion: all gears must use this one target.
expected = round(9000 * 10000 * 4095 * 2 / (2000 * 110000))
assert constant("AD_FAN_TARGET_9V") == expected == 3350
reconstructed_mv = expected * 2000 * 11 / (4095 * 2)
assert abs(reconstructed_mv - 9000) < 2
assert constant("AD_FAN_TOO_HIGH") == round(10000 * 4095 / 22000)
# Exhaust all coarse/fine combinations, checking the actual ISR comparison.
isr = body("void interrupt myIsr(void)")
assert "if(PWM_DR > PWM_CNT)" in isr
assert "T3D3L = PWM_DATA_NOW + 1;" in isr and "T3D3L = PWM_DATA_NOW;" in isr
for coarse in range(constant("AD_FAN_PWM_MIN_COUNT"), constant("AD_FAN_PWM_MAX_COUNT") + 1):
    for fine in range(8):
        phases = [coarse + (fine > phase) for phase in range(8)]
        assert sum(phases) == 8 * coarse + fine
        assert max(phases) <= constant("FAN_PWM_PERIOD")
# ADC groups must not overflow native u16 at full-scale input.
assert 4095 * 8 <= 65535 and 4095 * 12 <= 65535
adc = body("u8 ADC_Sample(void)")
assert "ADCDATA_COUNT > 4" in adc and "ADCDATA_COUNT >= 100" in adc
assert "ADC_GROUP_SUM / 12" in adc and "ADC_Sample();" not in isr
assert "adc_timeout_cnt >= 3" in adc and "fan_error_flag = 1;" in adc
assert "too_big_cnt = 0;" in adc
fan = body("void AD_fan_deal(void)")
assert "if(!ad_fan_ready_flag)" in fan and "ad_fan_ready_flag = 0;" in fan
assert "too_big_cnt >= AD_FAN_CONFIRM_COUNT" in fan
assert constant("AD_FAN_CONFIRM_COUNT") == 13
# Each single-contact ADC voltage is identified, with release excluded.
for key, resistance in [(1, 20000), (2, 0), (3, 6800)]:
    nominal = round(4095 * resistance / (10000 + resistance))
    minimum = constant(f"AD_KEY{key}_MIN") if key != 2 else 0
    maximum = constant(f"AD_KEY{key}_MAX")
    assert minimum <= nominal <= maximum < 4095
    for other in (1, 2, 3):
        if other == key:
            continue
        lo = constant(f"AD_KEY{other}_MIN") if other != 2 else 0
        hi = constant(f"AD_KEY{other}_MAX")
        assert maximum < lo or minimum > hi
for key in (1, 2, 3):
    assert f"if(KEY{key} && !key{key}_down_flag)" in body("void KEY_CHECK(void)")
    assert f"key{key}_short_flag = 0;" in body("void Key_Clear(void)")
    assert f"!key{key}_down_flag" in body("void main(void)")
key_actions = body("void KEY_deal(void)")
assert not re.search(r"(?:fan_mode|COOL_EN)\s*=", key_actions)
assert "Key_Clear();" in key_actions
assert "smg_close();" in body("void smg_188_scan(void)")
assert "switch" not in body("void smg_188_scan(void)")
assert "TRISA |= 0x0F;" in body("void smg_close(void)")
assert "TRISC |= 0x05;" in body("void smg_close(void)")
assert "#define MOTOR_PWM    PC3" in text
assert not re.search(r"MOTOR_PWM\s*=\s*1", text)
assert text.count("T1TH = 0xFE;") == text.count("T1TL = 0x70;") == 2
config = ET.fromstring((ROOT / "PROJECT/JZ01.hsprj2").read_bytes().decode("utf-8-sig"))
assert config.findtext("chip") == "HS16P2811"
assert (int(config.findtext("config-values").split()[1], 16) >> 2) & 7 == 0
assert sorted(n.text for n in config.findall("folder/file")) == ["\\main.c", "\\main.h"]
result = json.loads((ROOT / "build_result.json").read_bytes())
assert hashlib.sha256(SOURCE).hexdigest() == result["source_sha256"]
assert hashlib.sha256((ROOT / "PROJECT/JZ01.hs.hex").read_bytes()).hexdigest() == result["hex_sha256"]
log = (ROOT / "build_report.txt").read_bytes().decode("utf-8")
assert not re.search(r"^(?:error|warnning|warning):", log, re.M | re.I)
print("PASS: fixed 9V target; 344 coarse/fine combinations; ADC bounds/fault path;")
print("three key ranges/drivers with empty actions; display/communication placeholders;")
print("4T native project; source/HEX hashes; zero reported compiler errors/warnings.")
print("Source checks and arithmetic checks only; no GUI rebuild or physical-board validation.")
