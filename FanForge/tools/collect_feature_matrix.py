import argparse
import csv
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HS_ROOT = REPO_ROOT.parent
DEFAULT_EVIDENCE_DIR = REPO_ROOT / "evidence"

FUNCTION_PATTERN = re.compile(
    r"(?m)^\s*(?:void\s+interrupt|void|u8|u16|unsigned\s+char|"
    r"unsigned\s+int|bit)\s+([A-Za-z_]\w*)\s*"
    r"\([^;\r\n]*\)\s*\{"
)
DATE_PATTERN = re.compile(r"(?P<year>\d{2})_(?P<month>\d{2})_(?P<day>\d{2})")
FAN_FUNCTION_MARKERS = {
    "ADC_Sample",
    "ADC_Init",
    "pwm_init",
    "AD_fan_deal",
    "fan_deal",
    "mode_change",
    "mode_deal",
    "KEY_deal",
    "file_sleep_mode",
    "v_bat_deal",
    "smg_188_scan",
}

FEATURE_PATTERNS = {
    "battery_timed_chase": (
        r"\bv_bat_deal\s*\(",
        r"\bclean_other_time\s*\(",
        r"\bcharge_num\b",
    ),
    "charge_chrg_stdby": (r"\bCHRG\b", r"\bSTDBY\b"),
    "charge_insert_pin": (r"\bINSERT\b",),
    "charge_chrg_max": (r"\bCHRG_MAX\b",),
    "cooling": (r"\b(?:COOL_EN|COLD_ON)\b",),
    "display_188": (r"\bsmg_188_scan\s*\(",),
    "input_digital_key": (r"\bKEY_CHECK\s*\(", r"\bKEY_deal\s*\("),
    "input_ad_key": (r"\b(?:AD_KEY|ADC_KEY|ADKEY)\b",),
    "input_encoder": (
        r"\b(?:encoder_|GUNLUN|KEY_A|KEY_B|key2_typeA|key2_typeB)\w*",
    ),
    "input_slide_resistor": (
        r"\b(?:RES_ADC|AD_RES|ADC_RES|old_res_val|res_change_cnt)\b",
    ),
    "input_slide_switch": (r"\bSWI_KEY\b",),
    "light_output": (r"\b(?:LED_ON|LIGHT_ON|light_mode)\b",),
    "mist_pwm": (r"\b(?:PWM_WH|WH_PWM|wh_deal)\b",),
    "rgb_ws2812": (r"\b(?:RGB_SIGN|ws2812|rgb_wheel)\w*",),
    "motor_type_detection": (
        r"\b(?:YOUSHUA_WUSHUA|detect_youshua_wushua)\b",
    ),
    "motor_fixed_voltage": (
        r"\bGet_Fin_Val\s*\(",
        r"\bPWM_DATA_NOW\b",
    ),
    "motor_fixed_duty": (
        r"\btoo_big_cnt\b",
        r"\bAD_FAN\b",
        r"\bT3PWM[0-4]EN\b",
    ),
    "ad_fan_overvoltage": (
        r"\btoo_big_cnt\b",
        r"\b(?:AD_fan_deal|fan_deal)\s*\(",
    ),
    "dual_chip_communication": (
        r"\b(?:SIGN_1|SIGN_2|SHOW_sign_send|file_send_deal)\b",
    ),
    "stepper_swing": (r"\b(?:stepper_|motor_phase|swing_)\w*",),
}

EXCLUDED_REFERENCE_PARTS = (
    "资料",
    "temp",
    "test",
    "backup",
    "备份",
    "sample",
    "old",
    "history",
)


@dataclass(frozen=True)
class SourceRecord:
    path: Path
    relative_path: str
    project: str
    project_date: int
    function_count: int
    functions: tuple[str, ...]
    features: dict[str, bool]
    reference_quality: int


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    if b"\x00" in raw:
        return ""
    return raw.decode("utf-8", errors="ignore")


def _project_date(project: str) -> int:
    match = DATE_PATTERN.search(project)
    if not match:
        return 0
    year = 2000 + int(match.group("year"))
    month = int(match.group("month"))
    day = int(match.group("day"))
    if not 1 <= month <= 12 or not 1 <= day <= 31:
        return 0
    return year * 10000 + month * 100 + day


def _looks_like_hs2811(text: str) -> bool:
    register_groups = (
        bool(re.search(r"\b(?:PAHCON|PADCON|PCHCON|PCDCON)\b", text)),
        bool(re.search(r"\b(?:T3C1|T3PL|T3PWM[0-4]EN|PWMSEL1?)\b", text)),
        bool(re.search(r"\b(?:ADPCON1?|T1TH|T1TL|WUACON)\b", text)),
    )
    return sum(register_groups) >= 2


def _feature_matches(text: str, patterns: tuple[str, ...]) -> bool:
    return all(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def _reference_quality(relative_path: str) -> int:
    lowered = relative_path.lower()
    penalty = sum(
        1 for item in EXCLUDED_REFERENCE_PARTS if item.lower() in lowered
    )
    project_bonus = 2 if re.search(r"\\project(?:\\|_|$)", lowered) else 0
    main_bonus = 1 if lowered.endswith(r"\main.c") else 0
    return project_bonus + main_bonus - penalty * 3


def collect_sources(
    hs_root: Path,
) -> tuple[list[SourceRecord], list[tuple[str, str]]]:
    records: list[SourceRecord] = []
    rejected: list[tuple[str, str]] = []
    for path in sorted(hs_root.rglob("main.c"), key=lambda item: str(item).lower()):
        try:
            relative = str(path.relative_to(hs_root))
        except ValueError:
            continue
        if relative.lower().startswith("fanforge\\"):
            continue

        try:
            text = _read_text(path)
        except OSError as exc:
            rejected.append((relative, f"read_error:{exc.__class__.__name__}"))
            continue

        functions = tuple(FUNCTION_PATTERN.findall(text))
        if len(functions) < 8:
            rejected.append((relative, "unreadable_or_not_c"))
            continue
        if not _looks_like_hs2811(text):
            rejected.append((relative, "not_hs2811"))
            continue
        fan_marker_count = len(set(functions) & FAN_FUNCTION_MARKERS)
        if fan_marker_count < 5:
            rejected.append((relative, "not_fan_main_structure"))
            continue

        project = Path(relative).parts[0]
        features = {
            name: _feature_matches(text, patterns)
            for name, patterns in FEATURE_PATTERNS.items()
        }
        records.append(
            SourceRecord(
                path=path,
                relative_path=relative,
                project=project,
                project_date=_project_date(project),
                function_count=len(functions),
                functions=functions,
                features=features,
                reference_quality=_reference_quality(relative),
            )
        )
    return records, rejected


def write_inventory(records: list[SourceRecord], output_dir: Path) -> None:
    output = output_dir / "hs_fan_feature_inventory.csv"
    feature_names = tuple(FEATURE_PATTERNS)
    with output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            (
                "Path",
                "Project",
                "ProjectDate",
                "FunctionCount",
                "ReferenceQuality",
                *feature_names,
            )
        )
        for record in records:
            writer.writerow(
                (
                    record.relative_path,
                    record.project,
                    record.project_date or "",
                    record.function_count,
                    record.reference_quality,
                    *(int(record.features[name]) for name in feature_names),
                )
            )


def write_rejected(
    rejected: list[tuple[str, str]], output_dir: Path
) -> None:
    output = output_dir / "hs_fan_feature_rejected.csv"
    with output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(("Path", "Reason"))
        writer.writerows(rejected)


def _reference_sort_key(record: SourceRecord) -> tuple[int, int, str]:
    return (
        record.project_date,
        record.reference_quality,
        record.relative_path.lower(),
    )


def write_summary(records: list[SourceRecord], output_dir: Path) -> None:
    output = output_dir / "hs_fan_feature_summary.csv"
    project_count = len({record.project for record in records})
    with output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            (
                "Feature",
                "SourceFiles",
                "SourcePercent",
                "Projects",
                "ProjectPercent",
                "LatestReference",
            )
        )
        for name in FEATURE_PATTERNS:
            matches = [record for record in records if record.features[name]]
            projects = {record.project for record in matches}
            candidates = sorted(matches, key=_reference_sort_key, reverse=True)
            preferred = next(
                (item for item in candidates if item.reference_quality >= 3),
                candidates[0] if candidates else None,
            )
            writer.writerow(
                (
                    name,
                    len(matches),
                    round(len(matches) * 100 / len(records), 1),
                    len(projects),
                    round(len(projects) * 100 / project_count, 1),
                    preferred.relative_path if preferred else "",
                )
            )


def write_function_summary(
    records: list[SourceRecord], output_dir: Path
) -> None:
    output = output_dir / "hs_fan_all_function_frequency.csv"
    file_frequency: Counter[str] = Counter()
    project_functions: defaultdict[str, set[str]] = defaultdict(set)
    for record in records:
        unique = set(record.functions)
        file_frequency.update(unique)
        project_functions[record.project].update(unique)

    project_frequency: Counter[str] = Counter()
    for names in project_functions.values():
        project_frequency.update(names)

    with output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            (
                "Function",
                "SourceFiles",
                "SourcePercent",
                "Projects",
                "ProjectPercent",
            )
        )
        for name, count in sorted(
            file_frequency.items(), key=lambda item: (-item[1], item[0])
        ):
            projects = project_frequency[name]
            writer.writerow(
                (
                    name,
                    count,
                    round(count * 100 / len(records), 1),
                    projects,
                    round(projects * 100 / len(project_functions), 1),
                )
            )


def write_reference_review(
    records: list[SourceRecord],
    rejected: list[tuple[str, str]],
    hs_root: Path,
    output_dir: Path,
) -> None:
    output = output_dir / "hs_fan_feature_references.md"
    lines = [
        "# HS2811风扇功能扫描",
        "",
        f"- 扫描根目录：`{hs_root}`",
        f"- 可读HS2811 `main.c`：`{len(records)}`",
        f"- 涉及项目目录：`{len({item.project for item in records})}`",
        f"- 排除或不可读：`{len(rejected)}`",
        "",
        "统计用于确定扩展优先级，不代表出现次数最多的文件可以直接作为量产模板。",
        "参考候选按项目日期和正式PROJECT路径优先，资料、临时、测试和备份路径会降权。",
        "",
        "## 功能概览",
        "",
        "| 功能 | 文件 | 项目 | 最新优先参考 |",
        "| --- | ---: | ---: | --- |",
    ]
    for name in FEATURE_PATTERNS:
        matches = [record for record in records if record.features[name]]
        projects = {record.project for record in matches}
        candidates = sorted(matches, key=_reference_sort_key, reverse=True)
        preferred = next(
            (item for item in candidates if item.reference_quality >= 3),
            candidates[0] if candidates else None,
        )
        reference = preferred.relative_path if preferred else "-"
        lines.append(
            f"| `{name}` | {len(matches)} | {len(projects)} | `{reference}` |"
        )

    lines.extend(
        (
            "",
            "## 使用限制",
            "",
            "- 标签来自源码结构和关键符号，不能代替逐函数审查。",
            "- 同一个项目的多个版本会分别计入文件数量，但项目数量会去重。",
            "- 加密、损坏、非C源码及非HS2811项目不会参与功能占比。",
            "- 下一功能进入生成器前，必须重新打开候选项目核对硬件原理、标志位极性和完整调用链。",
            "",
        )
    )
    output.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a read-only HS2811 fan feature inventory."
    )
    parser.add_argument(
        "--hs-root",
        type=Path,
        default=DEFAULT_HS_ROOT,
        help="HS project root to scan.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_EVIDENCE_DIR,
        help="Directory for generated evidence files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    hs_root = args.hs_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    records, rejected = collect_sources(hs_root)
    if not records:
        raise SystemExit("No readable HS2811 fan sources found")
    write_inventory(records, output_dir)
    write_rejected(rejected, output_dir)
    write_summary(records, output_dir)
    write_function_summary(records, output_dir)
    write_reference_review(records, rejected, hs_root, output_dir)
    print(f"Readable HS2811 sources: {len(records)}")
    print(f"Distinct projects: {len({item.project for item in records})}")
    print(f"Rejected/non-HS2811: {len(rejected)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
