"""GUI-independent configuration document and presentation helpers."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any, Iterable, Sequence


JsonValue = dict[str, Any] | list[Any] | str | int | float | bool | None
JsonPathPart = str | int
JsonPath = tuple[JsonPathPart, ...]


class ConfigDocument:
    """Mutable JSON document that preserves all keys and value types."""

    def __init__(
        self,
        raw: dict[str, Any],
        *,
        source_path: Path | None = None,
    ) -> None:
        self.source_path = source_path
        self._raw: dict[str, Any] = {}
        self.replace(raw, source_path=source_path)

    @classmethod
    def from_path(cls, path: Path) -> "ConfigDocument":
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"JSON 无效（第 {exc.lineno} 行，第 {exc.colno} 列）：{exc.msg}"
            ) from exc
        if not isinstance(raw, dict):
            raise ValueError("配置根必须是 JSON 对象")
        return cls(raw, source_path=path)

    def replace(
        self,
        raw: dict[str, Any],
        *,
        source_path: Path | None = None,
    ) -> None:
        if not isinstance(raw, dict):
            raise ValueError("配置根必须是 JSON 对象")
        self._raw = copy.deepcopy(raw)
        if source_path is not None:
            self.source_path = source_path

    def to_dict(self) -> dict[str, Any]:
        return copy.deepcopy(self._raw)

    def to_json(self) -> str:
        return json.dumps(self._raw, ensure_ascii=False, indent=2) + "\n"

    def get(self, path: Sequence[JsonPathPart]) -> JsonValue:
        node: Any = self._raw
        for part in path:
            node = node[part]
        return copy.deepcopy(node)

    def set(self, path: Sequence[JsonPathPart], value: JsonValue) -> None:
        if not path:
            if not isinstance(value, dict):
                raise ValueError("配置根必须是 JSON 对象")
            self.replace(value)
            return
        node: Any = self._raw
        for part in path[:-1]:
            node = node[part]
        node[path[-1]] = copy.deepcopy(value)


def choices_for_path(
    path: Sequence[JsonPathPart],
    capabilities: dict[str, Any],
) -> tuple[Any, ...]:
    """Return catalog-backed choices for common scalar fields."""
    key = tuple(path)
    target = capabilities.get("target", {})
    display = capabilities.get("display", {})
    optional = capabilities.get("optional_features", {})
    exact: dict[JsonPath, Iterable[Any]] = {
        ("mcu", "model"): target.get("mcu_models", ()),
        ("mcu", "package"): target.get("packages", ()),
        ("mcu", "system_divider"): target.get("system_dividers", ()),
        ("timebase", "interrupt_us"): target.get(
            "timebase_interrupt_us", ()
        ),
        ("timebase", "t1_prescaler"): ("auto", 1, 2, 4, 8),
        ("features", "motor", "kind"): capabilities.get(
            "motor_kinds", {}
        ).keys(),
        ("features", "classic_product", "input_kind"): capabilities.get(
            "input_kinds", {}
        ).keys(),
        ("features", "classic_product", "charging_kind"): capabilities.get(
            "charging_kinds", {}
        ).keys(),
        ("features", "charging", "kind"): capabilities.get(
            "charging_kinds", {}
        ).keys(),
        ("features", "cooling", "control_mode"): optional.get(
            "cooling", {}
        ).get("control_modes", ()),
        ("features", "light", "mode_profile"): optional.get(
            "light", {}
        ).get("mode_profiles", ()),
        ("features", "atomizer", "dependency"): optional.get(
            "atomizer", {}
        ).get("dependencies", ()),
        ("features", "display", "profile"): display.get(
            "profiles", {}
        ).keys(),
        ("features", "display", "drive_mode"): display.get(
            "drive_modes", ()
        ),
        ("features", "display", "behavior", "profile"): display.get(
            "behavior_profiles", ()
        ),
        ("features", "display", "behavior", "idle_page"): display.get(
            "idle_pages", ()
        ),
        ("features", "classic_product", "low_blink_target"): display.get(
            "low_blink_targets", ()
        ),
        ("features", "classic_product", "charge_blink_target"): display.get(
            "charge_blink_targets", ()
        ),
    }
    if key in exact:
        return tuple(exact[key])
    last = key[-1] if key else None
    if last == "pwm_prescaler":
        return ("auto", 1, 2, 4, 8, 16, 32, 64, 128)
    if last == "pwm_clock_source":
        return ("fosc", "fcpu_div2")
    if last == "adc_reference":
        return ("2v", "3v", "4v", "vdd")
    if last == "adc_clock":
        return ("fcpu", "fcpu_div2", "fcpu_div8", "fcpu_div16")
    if isinstance(last, str) and last.endswith("_action"):
        return tuple(capabilities.get("key_actions", ()))
    return ()


def project_name(raw: dict[str, Any], fallback: str = "fanforge-project") -> str:
    project = raw.get("project")
    if isinstance(project, dict):
        value = project.get("name")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return fallback


def safe_directory_name(value: str) -> str:
    cleaned = re.sub(r"[<>:\"/\\|?*\x00-\x1f]+", "_", value).strip(" .")
    return cleaned or "fanforge-project"


def output_directory_value(
    current: str,
    raw: dict[str, Any],
    *,
    home: Path | None = None,
) -> str:
    """Keep a selected output directory, or initialize the default once."""
    current = current.strip()
    if current:
        return current

    home_dir = home or Path.home()
    documents = home_dir / "Documents"
    parent = documents if documents.exists() else home_dir
    return str(
        parent
        / "FanForgeOutputs"
        / safe_directory_name(project_name(raw))
    )


def summarize_config(raw: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    """Build a compact summary without interpreting backend validity."""
    mcu = raw.get("mcu", {})
    features = raw.get("features", {})
    motor = features.get("motor", {}) if isinstance(features, dict) else {}
    classic = (
        features.get("classic_product", {})
        if isinstance(features, dict)
        else {}
    )
    charging = (
        features.get("charging", {}) if isinstance(features, dict) else {}
    )

    enabled: list[str] = []
    feature_labels = {
        "cooling": "制冷",
        "light": "照明",
        "atomizer": "雾化",
        "display": "188 显示",
        "battery_monitor": "电量监测",
        "fan_voltage_protection": "风扇电压保护",
        "ad_key": "AD 按键",
        "digital_key": "数字按键",
        "slide_switch": "拨片开关",
        "encoder": "旋转编码器",
        "slide_resistor": "滑动变阻器",
    }
    if isinstance(features, dict):
        for key, label in feature_labels.items():
            section = features.get(key)
            if isinstance(section, dict) and section.get("enabled") is True:
                enabled.append(label)

    return (
        ("项目名称", project_name(raw)),
        (
            "芯片",
            f"{mcu.get('model', '—')} / {mcu.get('package', '—')}"
            if isinstance(mcu, dict)
            else "—",
        ),
        (
            "电机方案",
            str(motor.get("kind", "—")) if isinstance(motor, dict) else "—",
        ),
        (
            "输入方案",
            str(classic.get("input_kind", "—"))
            if isinstance(classic, dict)
            else "—",
        ),
        (
            "充电接口",
            str(
                charging.get(
                    "kind",
                    classic.get("charging_kind", "none")
                    if isinstance(classic, dict)
                    else "none",
                )
            )
            if isinstance(charging, dict)
            else "none",
        ),
        ("已启用功能", "、".join(enabled) if enabled else "基础功能"),
    )
