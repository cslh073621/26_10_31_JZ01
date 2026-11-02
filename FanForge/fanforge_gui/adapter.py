"""FanForge 后端适配器。

本模块是 GUI 与 fanforge 后端之间唯一的桥梁，只调用现有后端公开 API：

- :func:`fanforge.models.ProjectConfig.from_dict`
- :func:`fanforge.planner.build_generation_plan`
- :func:`fanforge.emitter.write_generation`
- :func:`fanforge.emitter.plan_as_dict`
- :func:`fanforge.capabilities.build_capability_catalog`

不复制校验或生成算法；覆盖保护逻辑与 CLI 完全一致。本模块不依赖 tkinter，
可在无图形环境中单独导入和测试。
"""

from __future__ import annotations

import json
import sys
import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fanforge.capabilities import build_capability_catalog
from fanforge.cli import GENERATED_ARTIFACTS
from fanforge.emitter import plan_as_dict, write_generation
from fanforge.errors import FanForgeError
from fanforge.models import ProjectConfig
from fanforge.planner import build_generation_plan


def resource_root() -> Path:
    """返回资源根目录，同时支持源码运行和 PyInstaller frozen 运行。

    - frozen（PyInstaller）：使用 ``sys._MEIPASS`` 解压目录。
    - 源码运行：包上层目录（仓库根），即 ``fanforge_gui`` 的父目录。

    后端自身通过模块 ``__file__`` 定位 ``core/`` 模板与 ``fanforge/chips/``，
    frozen 时这些数据文件同样被解压到 ``_MEIPASS``，故后端路径解析不受影响。
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass is not None:
        return Path(meipass)
    # adapter.py 位于 fanforge_gui/ 下，父目录的父目录即仓库根。
    return Path(__file__).resolve().parent.parent


def configs_dir() -> Path:
    """返回内置预设目录 ``configs/``。"""
    return resource_root() / "configs"


@dataclass(frozen=True)
class Preset:
    """一个可选择的预设配置。"""

    name: str  # 显示名（不含扩展名）
    path: Path
    source: str  # "bundled" 或 "external"

    @property
    def label(self) -> str:
        tag = "内置" if self.source == "bundled" else "外部"
        return f"[{tag}] {self.name}"


def discover_presets(extra_dirs: list[Path] | None = None) -> list[Preset]:
    """自动发现并加载预设配置。

    优先扫描内置 ``configs/*.json``，再扫描调用方提供的外部目录。结果按
    (source, name) 排序：内置在前，外部在后；同源按名称排序。
    """
    presets: list[Preset] = []

    bundled = configs_dir()
    if bundled.is_dir():
        for path in sorted(bundled.glob("*.json")):
            presets.append(
                Preset(
                    name=path.stem,
                    path=path,
                    source="bundled",
                )
            )

    for extra in extra_dirs or []:
        if not extra.is_dir():
            continue
        for path in sorted(extra.glob("*.json")):
            presets.append(
                Preset(
                    name=path.stem,
                    path=path,
                    source="external",
                )
            )

    presets.sort(key=lambda p: (0 if p.source == "bundled" else 1, p.name))
    return presets


def load_config_dict(path: Path) -> dict[str, Any]:
    """读取并解析一个 JSON 配置文件为原始字典。

    不做后端校验，仅做 JSON 解析与基本结构检查，供表单加载使用。
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FanForgeError(f"找不到配置文件：{path}") from exc
    except json.JSONDecodeError as exc:
        raise FanForgeError(
            f"配置文件 JSON 无效：{path}:{exc.lineno}:{exc.colno}：{exc.msg}"
        ) from exc
    if not isinstance(raw, dict):
        raise FanForgeError("配置根必须是对象")
    return raw


def save_config_dict(data: dict[str, Any], path: Path) -> None:
    """将配置字典写入 JSON 文件（保存副本）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


@dataclass
class PlanSummary:
    """生成计划的关键摘要，供界面展示。"""

    project: str
    generator_version: str
    resolved_pins: dict[str, str]
    timer_actual_us: float
    timer_reload_hex: str
    pwm_gpio: str
    pwm_timer: str
    pwm_actual_hz: float
    pwm_error_percent: float
    motor_kind: str
    full_plan: dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationResult:
    """一次生成的结果。"""

    output_dir: Path
    written_files: list[str]
    summary: PlanSummary


class OutputExistsError(FanForgeError):
    """输出目录已包含后端生成产物，需要用户明确确认后才能覆盖。

    本异常由 :meth:`FanForgeAdapter.generate` 在未显式 ``force`` 时抛出，
    GUI 据此弹出确认对话框；用户确认后以 ``force=True`` 重试。这与后端 CLI
    的覆盖保护语义一致，不会绕过任何检查。
    """

    def __init__(self, output_dir: Path, existing: tuple[str, ...]):
        self.output_dir = output_dir
        self.existing = existing
        super().__init__(
            f"输出目录 {output_dir} 已包含生成产物："
            f"{', '.join(existing)}；确认已审查或备份后再覆盖。"
        )


class FanForgeAdapter:
    """封装后端校验、规划与生成的适配器。"""

    def __init__(self) -> None:
        self._catalog: dict[str, Any] | None = None

    # -- 能力契约 ---------------------------------------------------------

    def capability_catalog(self) -> dict[str, Any]:
        """返回后端能力契约（带缓存）。"""
        if self._catalog is None:
            self._catalog = build_capability_catalog()
        return self._catalog

    # -- 校验与规划 -------------------------------------------------------

    def validate(
        self,
        data: dict[str, Any],
        source_path: Path | None = None,
    ) -> tuple[ProjectConfig, Any]:
        """用后端 ``ProjectConfig.from_dict`` + ``build_generation_plan`` 校验。

        返回 ``(config, plan)``。任何后端错误原样向上抛出，GUI 负责翻译展示。
        """
        path = source_path or Path("<memory>")
        config = ProjectConfig.from_dict(path, copy.deepcopy(data))
        plan = build_generation_plan(config)
        return config, plan

    def summarize(self, plan: Any) -> PlanSummary:
        """从生成计划中提取关键摘要。"""
        full = plan_as_dict(plan)
        timer = full.get("timer1", {})
        pwm = full.get("pwm", {})
        return PlanSummary(
            project=full.get("project", ""),
            generator_version=full.get("generator_version", ""),
            resolved_pins=full.get("resolved_pins", {}),
            timer_actual_us=float(timer.get("actual_us", 0.0)),
            timer_reload_hex=f"0x{int(timer.get('reload_value', 0)):04X}",
            pwm_gpio=str(pwm.get("gpio", "")),
            pwm_timer=str(pwm.get("timer", "")),
            pwm_actual_hz=float(pwm.get("actual_frequency_hz", 0.0)),
            pwm_error_percent=float(pwm.get("error_percent", 0.0)),
            motor_kind=str(pwm.get("motor_kind", "")),
            full_plan=full,
        )

    # -- 生成 -------------------------------------------------------------

    def existing_artifacts(self, output_dir: Path) -> tuple[str, ...]:
        """返回输出目录中已存在的后端生成产物名。"""
        if not output_dir.exists():
            return ()
        return tuple(
            name for name in GENERATED_ARTIFACTS if (output_dir / name).exists()
        )

    def generate(
        self,
        data: dict[str, Any],
        output_dir: Path,
        source_path: Path | None = None,
        force: bool = False,
    ) -> GenerationResult:
        """校验、规划并写入生成产物。

        - 生成前自动执行与 :meth:`validate` 相同的后端校验。
        - 若输出目录已含生成产物且未 ``force``，抛出 :class:`OutputExistsError`，
          不绕过覆盖保护。
        - 用户在 GUI 明确确认后，以 ``force=True`` 重试即可覆盖。
        """
        config, plan = self.validate(data, source_path=source_path)

        existing = self.existing_artifacts(output_dir)
        if existing and not force:
            raise OutputExistsError(output_dir, existing)

        write_generation(plan, output_dir)
        written = sorted(
            name
            for name in GENERATED_ARTIFACTS
            if (output_dir / name).exists()
        )
        return GenerationResult(
            output_dir=output_dir,
            written_files=written,
            summary=self.summarize(plan),
        )
