import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT / "PROJECT"
IDE = next(Path(r"H:\WorkSpace\HS").glob("*/HSIDE_v2.1.16_2026.07.07(1)/HSIDE_v2.1.16_2026.07.07/cc1.exe")).parent
PICC = Path(r"C:\Program Files (x86)\HI-TECH Software\PICC\9.83")
project_xml = ET.fromstring((PROJECT / "JZ01.hsprj2").read_bytes().decode("utf-8-sig"))
config = project_xml.findtext("config-values").strip()
assert int(config.split()[1], 16) & (7 << 2) == 0, "HSIDE system divider must be 4T"
for name in ("main.c", "main.h"):
    raw = (PROJECT / name).read_bytes()
    assert b"\r\r\n" not in raw and b"\n\n\n" not in raw.replace(b"\r\n", b"\n")
    assert raw.isascii(), "Keep native PICC sources ASCII or explicitly use GBK"
with tempfile.TemporaryDirectory(prefix="jz01_build_") as directory:
    temp = Path(directory)
    compiler = temp / "picc"
    shutil.copytree(PICC, compiler)
    out = temp / "build"
    out.mkdir()
    for name in ("main.c", "main.h"):
        (out / name).write_bytes((PROJECT / name).read_bytes())
    command = [str(IDE / "cc1.exe"), "-chip", "HS16P2811", "-rom-size", "2048",
        "-banks", "4", "-ram-bank", "20-7f,a0-bf", "-common", "70-7f",
        "-rst-addr", "00h", "-int-addr", "04h", "-tran-exe", str(IDE / "ptran2.exe"),
        "-debug", "false", "-prj-name", "JZ01", "-work-dir", str(out),
        "-output-dir", str(out), "-picc-path", str(compiler), "-config", config,
        "-out-type", "ccs", "-I" + str(IDE / "include"), str(out / "main.c")]
    result = subprocess.run(command, cwd=out, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log = result.stdout.decode("gbk", errors="replace").replace("\r", "")
    (ROOT / "build_report.txt").write_bytes((log.rstrip() + "\n").encode("utf-8"))
    print(log)
    if result.returncode or re.search(r"^error:", log, re.M | re.I):
        raise SystemExit("Native build failed")
    assert not re.search(r"^warnning:|^warning:", log, re.M | re.I), "Unexpected compiler warning"
    image = (out / "JZ01.hs.hex").read_bytes()
    assert len(image.splitlines()) == 2048
    for name in ("JZ01.hs.hex", "JZ01.ccs", "JZ01.lst", "JZ01.map"):
        (PROJECT / name).write_bytes((out / name).read_bytes())
    record = {"source_sha256": hashlib.sha256((PROJECT / "main.c").read_bytes()).hexdigest(),
        "header_sha256": hashlib.sha256((PROJECT / "main.h").read_bytes()).hexdigest(),
        "hex_sha256": hashlib.sha256(image).hexdigest(), "config": config,
        "compiler": str(IDE / "cc1.exe"), "project": "PROJECT/JZ01.hsprj2",
        "board_tested": False}
    for label, pattern in [("rom", r"Program space\s+used\s+[0-9A-F]+h\s*\(\s*(\d+)\)"),
                           ("ram", r"Data space\s+used\s+[0-9A-F]+h\s*\(\s*(\d+)\)")]:
        record[label + "_used"] = int(re.search(pattern, log, re.I).group(1))
    record.update(errors=0, warnings=0, rom_capacity=2048, ram_capacity=128,
                  validation="native CLI build; GUI/board not tested")
    (ROOT / "build_result.json").write_bytes((json.dumps(record, indent=2) + "\n").encode("utf-8"))
    print("HEX SHA256:", record["hex_sha256"])
