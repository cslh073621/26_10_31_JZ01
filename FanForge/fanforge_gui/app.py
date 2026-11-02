"""Tkinter desktop frontend for FanForge."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from fanforge import __version__
from fanforge.errors import FanForgeError
from fanforge_gui.adapter import (
    FanForgeAdapter,
    OutputExistsError,
    Preset,
    discover_presets,
    load_config_dict,
    save_config_dict,
)
from fanforge_gui.core import (
    ConfigDocument,
    JsonPathPart,
    choices_for_path,
    output_directory_value,
    project_name,
    safe_directory_name,
    summarize_config,
)


FIELD_LABELS = {
    "schema_version": "配置版本",
    "project": "项目",
    "name": "名称",
    "self_test_ms": "上电自检时间（ms）",
    "mcu": "芯片",
    "model": "型号",
    "package": "封装",
    "oscillator_hz": "振荡频率（Hz）",
    "system_divider": "系统分频",
    "timebase": "时基",
    "interrupt_us": "中断周期（μs）",
    "t1_prescaler": "Timer1 预分频",
    "pins": "物理脚位",
    "features": "功能模块",
    "motor": "电机",
    "kind": "类型",
    "pwm_frequency_hz": "PWM 频率（Hz）",
    "pwm_clock_source": "PWM 时钟源",
    "pwm_prescaler": "PWM 预分频",
    "run_duty_percent": "运行占空比（%）",
    "fan_voltage_protection": "风扇电压保护",
    "battery_monitor": "电量监测",
    "classic_product": "经典产品逻辑",
    "input_kind": "输入方案",
    "charging": "充电接口",
    "charging_kind": "充电接口类型",
    "cooling": "制冷",
    "cooling_enabled": "启用制冷",
    "light": "照明",
    "atomizer": "雾化",
    "display": "显示",
    "enabled": "启用",
    "control_mode": "控制模式",
    "mode_profile": "模式方案",
    "dependency": "运行依赖",
    "profile": "硬件方案",
    "drive_mode": "驱动方式",
    "behavior": "显示行为",
    "connections": "显示连接",
    "pin_count": "脚位数量",
    "gear_steps": "档位",
    "gear_range": "档位范围",
    "sleep_enabled": "启用休眠",
    "long_adjust": "启用长按调档",
    "charge_max_gear": "充电最大档位",
    "ad_key": "AD 按键",
    "digital_key": "数字按键",
    "slide_switch": "拨片开关",
    "encoder": "旋转编码器",
    "slide_resistor": "滑动变阻器",
    "keys": "按键列表",
    "short_action": "短按动作",
    "double_action": "双击动作",
    "long_action": "长按动作",
}


VALUE_LABELS = {
    "brushless_fixed_duty": "无刷固定占空比",
    "brushed_fixed_duty": "有刷固定占空比",
    "brushless_fixed_voltage_7_3": "无刷固定电压 7+3",
    "brushed_brushless_compat_fixed_voltage_7_3": "有刷/无刷兼容 7+3",
    "two_digital_keys_active_low": "双数字按键（低有效）",
    "digital_keys_active_low": "可配置数字按键（低有效）",
    "two_ad_keys_active_low_ranges": "双 AD 按键",
    "ad_keys_active_low_ranges": "可配置 AD 按键",
    "rotary_encoder_active_low": "拨片开关＋旋转编码器",
    "single_key_slide_resistor_active_low": "单按键＋滑动变阻器",
    "none": "无",
    "chrg_stdby_active_low": "CHRG/STDBY 低有效",
    "chrg_chrg_max_active_low_static": "CHRG/CHRG_MAX 静态低有效",
    "insert_active_high_chrg_active_low": "INSERT 高有效＋CHRG 低有效",
    "toggle_while_fan_on": "风扇运行时独立切换",
    "follow_fan": "跟随风扇",
    "fan_sync": "跟随风扇",
    "on_off": "开/关",
    "on_off_flash": "关/常亮/闪烁",
    "fan_required": "依赖风扇运行",
    "independent": "独立运行",
    "standard_188_cooling_percent_style_a": "标准 188 制冷百分比灯板",
    "custom_charlieplex_188": "自定义 Charlieplex 188 灯板",
    "auto": "自动",
}


NO_RESULT = object()


FONT_FAMILY = "Microsoft YaHei UI"
MONO_FONT_FAMILY = "Cascadia Mono"

COLORS = {
    "background": "#F4F6FA",
    "panel": "#FFFFFF",
    "panel_subtle": "#F8FAFC",
    "sidebar": "#111827",
    "sidebar_active": "#263244",
    "sidebar_hover": "#1E293B",
    "accent": "#5B5FEF",
    "accent_hover": "#4B4FD8",
    "accent_soft": "#EEF0FF",
    "text": "#111827",
    "muted": "#64748B",
    "border": "#E2E8F0",
    "success": "#0F9F6E",
    "success_soft": "#E9F8F2",
    "danger": "#DC4C64",
    "danger_soft": "#FDECEF",
    "warning": "#D97706",
    "editor": "#0F172A",
    "editor_text": "#E2E8F0",
}

PAGE_META = {
    "start": (
        "快速生成",
        "从产品预设出发，校验配置并生成完整的风扇固件工程。",
    ),
    "config": (
        "配置编辑",
        "按真实 JSON 结构浏览和调整参数，新增字段会自动出现在这里。",
    ),
    "json": (
        "高级 JSON",
        "直接编辑完整配置；适合批量复制、复杂结构和新接口字段。",
    ),
    "result": (
        "校验与结果",
        "查看后端资源规划、冲突校验和最终生成记录。",
    ),
}


def friendly_value(value: Any) -> str:
    if isinstance(value, bool):
        return "是" if value else "否"
    if value is None:
        return "空"
    text = str(value)
    label = VALUE_LABELS.get(text)
    return f"{label}（{text}）" if label else text


def value_kind(value: Any) -> str:
    if isinstance(value, bool):
        return "布尔"
    if isinstance(value, dict):
        return "对象"
    if isinstance(value, list):
        return "列表"
    if isinstance(value, int):
        return "整数"
    if isinstance(value, float):
        return "小数"
    if value is None:
        return "空"
    return "文本"


def compact_value(value: Any) -> str:
    if isinstance(value, dict):
        return f"{len(value)} 项"
    if isinstance(value, list):
        return f"{len(value)} 项"
    rendered = friendly_value(value)
    return rendered if len(rendered) <= 80 else rendered[:77] + "…"


def display_path(path: Sequence[JsonPathPart]) -> str:
    result = "$"
    for part in path:
        if isinstance(part, int):
            result += f"[{part}]"
        else:
            result += f".{part}"
    return result


class EditValueDialog:
    def __init__(
        self,
        parent: tk.Misc,
        *,
        path: Sequence[JsonPathPart],
        value: Any,
        choices: Sequence[Any],
    ) -> None:
        self.parent = parent
        self.path = tuple(path)
        self.value = value
        self.choices = tuple(choices)
        self.result: Any = NO_RESULT
        self.choice_by_display: dict[str, Any] = {}

        self.window = ctk.CTkToplevel(parent)
        self.window.title("编辑配置项")
        self.window.transient(parent.winfo_toplevel())
        self.window.resizable(True, isinstance(value, (dict, list)))
        self.window.configure(fg_color=COLORS["background"])
        self.window.protocol("WM_DELETE_WINDOW", self.window.destroy)

        body = ctk.CTkFrame(
            self.window,
            fg_color=COLORS["panel"],
            corner_radius=18,
            border_width=1,
            border_color=COLORS["border"],
        )
        body.grid(row=0, column=0, sticky="nsew", padx=18, pady=18)
        self.window.rowconfigure(0, weight=1)
        self.window.columnconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            body,
            text="编辑配置项",
            text_color=COLORS["text"],
            font=(FONT_FAMILY, 20, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(22, 4))
        ctk.CTkLabel(
            body,
            text="修改将保留原始 JSON 类型，并在生成前交由后端重新校验。",
            text_color=COLORS["muted"],
            font=(FONT_FAMILY, 12),
        ).grid(row=1, column=0, sticky="w", padx=22)

        meta = ctk.CTkFrame(
            body,
            fg_color=COLORS["accent_soft"],
            corner_radius=10,
        )
        meta.grid(row=2, column=0, sticky="ew", padx=22, pady=(18, 14))
        meta.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            meta,
            text=display_path(path),
            text_color=COLORS["accent"],
            font=(MONO_FONT_FAMILY, 12, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=14, pady=10)
        ctk.CTkLabel(
            meta,
            text=value_kind(value),
            text_color=COLORS["muted"],
            fg_color=COLORS["panel"],
            corner_radius=7,
            font=(FONT_FAMILY, 11),
        ).grid(row=0, column=1, padx=(0, 10), pady=7, ipadx=7, ipady=2)

        editor_host = ctk.CTkFrame(body, fg_color="transparent")
        editor_host.grid(row=3, column=0, sticky="nsew", padx=22)
        editor_host.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(3, weight=1)

        self.editor: tk.Widget | ctk.CTkBaseClass
        if isinstance(value, bool):
            self.bool_var = tk.BooleanVar(value=value)
            self.editor = ctk.CTkCheckBox(
                editor_host,
                text="启用此配置项",
                variable=self.bool_var,
                text_color=COLORS["text"],
                fg_color=COLORS["accent"],
                hover_color=COLORS["accent_hover"],
                border_color=COLORS["border"],
                font=(FONT_FAMILY, 13),
            )
            self.editor.grid(row=0, column=0, sticky="w", pady=10)
        elif self.choices:
            displays: list[str] = []
            for choice in self.choices:
                shown = friendly_value(choice)
                displays.append(shown)
                self.choice_by_display[shown] = choice
            current = friendly_value(value)
            if current not in self.choice_by_display:
                displays.insert(0, current)
                self.choice_by_display[current] = value
            self.scalar_var = tk.StringVar(value=current)
            self.editor = ctk.CTkComboBox(
                editor_host,
                variable=self.scalar_var,
                values=displays,
                state="readonly",
                height=42,
                corner_radius=10,
                border_color=COLORS["border"],
                button_color=COLORS["accent"],
                button_hover_color=COLORS["accent_hover"],
                dropdown_font=(FONT_FAMILY, 12),
                font=(FONT_FAMILY, 12),
            )
            self.editor.grid(row=0, column=0, sticky="ew", pady=4)
        elif isinstance(value, (dict, list)) or value is None:
            editor_host.grid_rowconfigure(0, weight=1)
            self.text = ctk.CTkTextbox(
                editor_host,
                width=700,
                height=340,
                wrap="none",
                font=(MONO_FONT_FAMILY, 12),
                fg_color=COLORS["editor"],
                text_color=COLORS["editor_text"],
                corner_radius=12,
                border_width=1,
                border_color="#263449",
                undo=True,
            )
            self.text.grid(row=0, column=0, sticky="nsew")
            self.text.insert(
                "1.0", json.dumps(value, ensure_ascii=False, indent=2)
            )
            self.editor = self.text
        else:
            self.scalar_var = tk.StringVar(value=str(value))
            self.editor = ctk.CTkEntry(
                editor_host,
                textvariable=self.scalar_var,
                height=42,
                corner_radius=10,
                border_color=COLORS["border"],
                fg_color=COLORS["panel_subtle"],
                text_color=COLORS["text"],
                font=(FONT_FAMILY, 13),
            )
            self.editor.grid(row=0, column=0, sticky="ew", pady=4)

        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.grid(row=4, column=0, sticky="e", padx=22, pady=22)
        ctk.CTkButton(
            buttons,
            text="取消",
            command=self.window.destroy,
            width=92,
            height=38,
            fg_color=COLORS["panel_subtle"],
            hover_color=COLORS["border"],
            text_color=COLORS["text"],
            border_width=1,
            border_color=COLORS["border"],
            font=(FONT_FAMILY, 12),
        ).pack(side="right")
        ctk.CTkButton(
            buttons,
            text="应用修改",
            command=self._apply,
            width=112,
            height=38,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            font=(FONT_FAMILY, 12, "bold"),
        ).pack(side="right", padx=(0, 10))

        self.window.bind("<Escape>", lambda _event: self.window.destroy())
        if not isinstance(value, (dict, list)):
            self.window.bind("<Return>", lambda _event: self._apply())

    def _apply(self) -> None:
        try:
            if isinstance(self.value, bool):
                result: Any = self.bool_var.get()
            elif self.choices:
                result = self.choice_by_display[self.scalar_var.get()]
            elif isinstance(self.value, (dict, list)) or self.value is None:
                result = json.loads(self.text.get("1.0", "end-1c"))
                if isinstance(self.value, dict) and not isinstance(result, dict):
                    raise ValueError("该配置项必须保持为 JSON 对象")
                if isinstance(self.value, list) and not isinstance(result, list):
                    raise ValueError("该配置项必须保持为 JSON 列表")
            elif isinstance(self.value, int):
                result = int(self.scalar_var.get().strip())
            elif isinstance(self.value, float):
                result = float(self.scalar_var.get().strip())
            else:
                result = self.scalar_var.get()
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            messagebox.showerror("无法应用", str(exc), parent=self.window)
            return
        self.result = result
        self.window.destroy()

    def show(self) -> Any:
        self.window.grab_set()
        self.window.update_idletasks()
        x = self.parent.winfo_rootx() + 80
        y = self.parent.winfo_rooty() + 70
        self.window.geometry(f"+{x}+{y}")
        self.editor.focus_set()
        self.parent.wait_window(self.window)
        return self.result


class FanForgeApplication:
    def __init__(self, root: ctk.CTk) -> None:
        self.root = root
        self.adapter = FanForgeAdapter()
        self.capabilities = self.adapter.capability_catalog()
        self.presets = discover_presets()
        self.document: ConfigDocument | None = None
        self.current_preset: Preset | None = None
        self.document_dirty = False
        self.json_dirty = False
        self._updating_json = False
        self._setting_preset = False
        self.item_paths: dict[str, tuple[JsonPathPart, ...]] = {}
        self.last_output: Path | None = None
        self.status_var = tk.StringVar(value="准备就绪")
        self.page_title_var = tk.StringVar()
        self.page_subtitle_var = tk.StringVar()
        self.active_page = "start"

        self.root.title(f"FanForge 风扇项目生成器 {__version__}")
        self.root.geometry("1280x820")
        self.root.minsize(1060, 700)
        self.root.configure(fg_color=COLORS["background"])
        self._configure_style()
        self._build_ui()
        self._load_initial_preset()

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.layout(
            "Modern.Treeview",
            [("Modern.Treeview.treearea", {"sticky": "nswe"})],
        )
        style.configure(
            "Modern.Treeview",
            background=COLORS["panel"],
            fieldbackground=COLORS["panel"],
            foreground=COLORS["text"],
            borderwidth=0,
            relief="flat",
            rowheight=34,
            font=(FONT_FAMILY, 11),
        )
        style.configure(
            "Modern.Treeview.Heading",
            background=COLORS["panel_subtle"],
            foreground="#475569",
            borderwidth=0,
            relief="flat",
            padding=(12, 10),
            font=(FONT_FAMILY, 11, "bold"),
        )
        style.map(
            "Modern.Treeview",
            background=[("selected", COLORS["accent_soft"])],
            foreground=[("selected", "#3730A3")],
        )
        style.map(
            "Modern.Treeview.Heading",
            background=[("active", "#F1F5F9")],
        )

    def _build_ui(self) -> None:
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        sidebar = ctk.CTkFrame(
            self.root,
            width=238,
            corner_radius=0,
            fg_color=COLORS["sidebar"],
        )
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(8, weight=1)

        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=24, pady=(26, 30))
        ctk.CTkLabel(
            brand,
            text="F",
            width=38,
            height=38,
            corner_radius=11,
            fg_color=COLORS["accent"],
            text_color="#FFFFFF",
            font=(FONT_FAMILY, 20, "bold"),
        ).pack(side="left")
        brand_text = ctk.CTkFrame(brand, fg_color="transparent")
        brand_text.pack(side="left", padx=(11, 0))
        ctk.CTkLabel(
            brand_text,
            text="FanForge",
            text_color="#FFFFFF",
            font=(FONT_FAMILY, 18, "bold"),
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            brand_text,
            text="DESKTOP STUDIO",
            text_color="#8290A8",
            font=(FONT_FAMILY, 9, "bold"),
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            sidebar,
            text="工作区",
            text_color="#6F7D94",
            font=(FONT_FAMILY, 10, "bold"),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=25, pady=(0, 8))

        nav_items = (
            ("start", "◈", "快速生成"),
            ("config", "⚙", "配置编辑"),
            ("json", "{ }", "高级 JSON"),
            ("result", "✓", "校验结果"),
        )
        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        for offset, (key, icon, label) in enumerate(nav_items, start=2):
            button = ctk.CTkButton(
                sidebar,
                text=f"{icon}   {label}",
                command=lambda page=key: self._show_page(page),
                height=44,
                corner_radius=10,
                fg_color="transparent",
                hover_color=COLORS["sidebar_hover"],
                text_color="#C8D1DF",
                anchor="w",
                font=(FONT_FAMILY, 12, "bold"),
            )
            button.grid(
                row=offset,
                column=0,
                sticky="ew",
                padx=14,
                pady=3,
            )
            self.nav_buttons[key] = button

        capability_button = ctk.CTkButton(
            sidebar,
            text="查看后端能力  ↗",
            command=self._show_capabilities,
            height=40,
            corner_radius=10,
            fg_color="#182234",
            hover_color=COLORS["sidebar_hover"],
            text_color="#D8E0EB",
            border_width=1,
            border_color="#2B374B",
            font=(FONT_FAMILY, 11),
        )
        capability_button.grid(
            row=9,
            column=0,
            sticky="ew",
            padx=18,
            pady=(0, 12),
        )
        ctk.CTkLabel(
            sidebar,
            text=f"FanForge {__version__}\n后端规则保持唯一权威",
            text_color="#6F7D94",
            justify="left",
            anchor="w",
            font=(FONT_FAMILY, 9),
        ).grid(row=10, column=0, sticky="ew", padx=23, pady=(0, 22))

        workspace = ctk.CTkFrame(
            self.root,
            corner_radius=0,
            fg_color=COLORS["background"],
        )
        workspace.grid(row=0, column=1, sticky="nsew")
        workspace.grid_rowconfigure(1, weight=1)
        workspace.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(workspace, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=30, pady=(24, 16))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            textvariable=self.page_title_var,
            text_color=COLORS["text"],
            font=(FONT_FAMILY, 25, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            header,
            textvariable=self.page_subtitle_var,
            text_color=COLORS["muted"],
            font=(FONT_FAMILY, 11),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", pady=(3, 0))
        ctk.CTkLabel(
            header,
            text="LOCAL · PRIVATE",
            fg_color=COLORS["success_soft"],
            text_color=COLORS["success"],
            corner_radius=9,
            font=(FONT_FAMILY, 10, "bold"),
        ).grid(row=0, column=1, rowspan=2, padx=(16, 0), ipadx=10, ipady=5)

        page_host = ctk.CTkFrame(workspace, fg_color="transparent")
        page_host.grid(row=1, column=0, sticky="nsew", padx=30)
        page_host.grid_rowconfigure(0, weight=1)
        page_host.grid_columnconfigure(0, weight=1)

        self.start_tab = ctk.CTkFrame(page_host, fg_color="transparent")
        self.config_tab = ctk.CTkFrame(page_host, fg_color="transparent")
        self.json_tab = ctk.CTkFrame(page_host, fg_color="transparent")
        self.result_tab = ctk.CTkFrame(page_host, fg_color="transparent")
        self.pages = {
            "start": self.start_tab,
            "config": self.config_tab,
            "json": self.json_tab,
            "result": self.result_tab,
        }
        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")

        self._build_start_tab()
        self._build_config_tab()
        self._build_json_tab()
        self._build_result_tab()

        status_bar = ctk.CTkFrame(
            workspace,
            height=42,
            fg_color=COLORS["panel"],
            corner_radius=0,
            border_width=1,
            border_color=COLORS["border"],
        )
        status_bar.grid(row=2, column=0, sticky="ew", pady=(16, 0))
        status_bar.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            status_bar,
            text="●",
            text_color=COLORS["accent"],
            font=(FONT_FAMILY, 10),
        ).grid(row=0, column=0, padx=(30, 8), pady=11)
        ctk.CTkLabel(
            status_bar,
            textvariable=self.status_var,
            text_color=COLORS["muted"],
            anchor="w",
            font=(FONT_FAMILY, 10),
        ).grid(row=0, column=1, sticky="ew", pady=11)
        ctk.CTkLabel(
            status_bar,
            text="所有生成规则均来自 FanForge 后端",
            text_color="#94A3B8",
            font=(FONT_FAMILY, 9),
        ).grid(row=0, column=2, padx=(12, 30), pady=11)

        self._show_page("start")

    def _show_page(self, page: str) -> None:
        if page not in self.pages:
            return
        self.active_page = page
        self.pages[page].tkraise()
        title, subtitle = PAGE_META[page]
        self.page_title_var.set(title)
        self.page_subtitle_var.set(subtitle)
        for key, button in self.nav_buttons.items():
            selected = key == page
            button.configure(
                fg_color=(
                    COLORS["sidebar_active"] if selected else "transparent"
                ),
                text_color="#FFFFFF" if selected else "#C8D1DF",
            )

    def _build_start_tab(self) -> None:
        tab = self.start_tab
        tab.grid_columnconfigure(0, weight=3)
        tab.grid_columnconfigure(1, weight=2)
        tab.grid_rowconfigure(1, weight=1)

        hero = ctk.CTkFrame(
            tab,
            height=128,
            fg_color=COLORS["accent"],
            corner_radius=18,
        )
        hero.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(0, 16),
        )
        hero.grid_propagate(False)
        hero.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            hero,
            text="从产品方案到可交付工程",
            text_color="#FFFFFF",
            font=(FONT_FAMILY, 22, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=26, pady=(22, 3))
        ctk.CTkLabel(
            hero,
            text="选择预设，必要时调整参数；校验、资源规划和源码生成由同一套后端完成。",
            text_color="#DDE0FF",
            font=(FONT_FAMILY, 11),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=26)
        badge_row = ctk.CTkFrame(hero, fg_color="transparent")
        badge_row.grid(row=2, column=0, sticky="w", padx=26, pady=(14, 0))
        for text in ("后端校验", "资源冲突检查", "完整工程生成"):
            ctk.CTkLabel(
                badge_row,
                text=f"✓  {text}",
                fg_color="#7074F4",
                text_color="#FFFFFF",
                corner_radius=8,
                font=(FONT_FAMILY, 9, "bold"),
            ).pack(side="left", padx=(0, 8), ipadx=8, ipady=3)
        ctk.CTkLabel(
            hero,
            text="FF",
            width=76,
            height=76,
            fg_color="#6B6FF2",
            text_color="#BFC2FF",
            corner_radius=22,
            font=(FONT_FAMILY, 28, "bold"),
        ).grid(row=0, column=1, rowspan=3, padx=26)

        workflow = ctk.CTkFrame(
            tab,
            fg_color=COLORS["panel"],
            corner_radius=18,
            border_width=1,
            border_color=COLORS["border"],
        )
        workflow.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        workflow.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            workflow,
            text="01",
            text_color=COLORS["accent"],
            font=(FONT_FAMILY, 10, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(20, 2))
        ctk.CTkLabel(
            workflow,
            text="选择产品预设",
            text_color=COLORS["text"],
            font=(FONT_FAMILY, 16, "bold"),
        ).grid(row=1, column=0, sticky="w", padx=22)
        ctk.CTkLabel(
            workflow,
            text="从最接近目标产品的配置开始，后续仍可修改任意字段。",
            text_color=COLORS["muted"],
            font=(FONT_FAMILY, 10),
        ).grid(row=2, column=0, sticky="w", padx=22, pady=(3, 10))

        self.preset_var = tk.StringVar()
        self.preset_combo = ctk.CTkComboBox(
            workflow,
            variable=self.preset_var,
            values=[preset.label for preset in self.presets],
            command=lambda _choice: self._on_preset_selected(),
            state="readonly",
            height=42,
            corner_radius=10,
            border_color=COLORS["border"],
            fg_color=COLORS["panel_subtle"],
            button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"],
            text_color=COLORS["text"],
            dropdown_font=(FONT_FAMILY, 11),
            font=(FONT_FAMILY, 11),
        )
        self.preset_combo.grid(row=3, column=0, sticky="ew", padx=22)

        preset_actions = ctk.CTkFrame(workflow, fg_color="transparent")
        preset_actions.grid(row=4, column=0, sticky="ew", padx=22, pady=(10, 0))
        ctk.CTkButton(
            preset_actions,
            text="导入配置",
            command=self._import_config,
            width=104,
            height=34,
            fg_color=COLORS["panel_subtle"],
            hover_color=COLORS["border"],
            text_color=COLORS["text"],
            border_width=1,
            border_color=COLORS["border"],
            font=(FONT_FAMILY, 10),
        ).pack(side="left")
        ctk.CTkButton(
            preset_actions,
            text="保存配置副本",
            command=self._save_config,
            width=126,
            height=34,
            fg_color=COLORS["panel_subtle"],
            hover_color=COLORS["border"],
            text_color=COLORS["text"],
            border_width=1,
            border_color=COLORS["border"],
            font=(FONT_FAMILY, 10),
        ).pack(side="left", padx=(8, 0))

        ctk.CTkFrame(
            workflow,
            height=1,
            fg_color=COLORS["border"],
        ).grid(row=5, column=0, sticky="ew", padx=22, pady=18)

        ctk.CTkLabel(
            workflow,
            text="02",
            text_color=COLORS["accent"],
            font=(FONT_FAMILY, 10, "bold"),
        ).grid(row=6, column=0, sticky="w", padx=22)
        ctk.CTkLabel(
            workflow,
            text="选择输出位置",
            text_color=COLORS["text"],
            font=(FONT_FAMILY, 16, "bold"),
        ).grid(row=7, column=0, sticky="w", padx=22, pady=(2, 10))

        output_row = ctk.CTkFrame(workflow, fg_color="transparent")
        output_row.grid(row=8, column=0, sticky="ew", padx=22)
        output_row.grid_columnconfigure(0, weight=1)
        self.output_var = tk.StringVar()
        ctk.CTkEntry(
            output_row,
            textvariable=self.output_var,
            height=42,
            corner_radius=10,
            border_color=COLORS["border"],
            fg_color=COLORS["panel_subtle"],
            text_color=COLORS["text"],
            font=(FONT_FAMILY, 10),
        ).grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            output_row,
            text="浏览",
            command=self._browse_output,
            width=76,
            height=42,
            fg_color=COLORS["panel_subtle"],
            hover_color=COLORS["border"],
            text_color=COLORS["text"],
            border_width=1,
            border_color=COLORS["border"],
            font=(FONT_FAMILY, 10),
        ).grid(row=0, column=1, padx=(8, 0))
        ctk.CTkLabel(
            workflow,
            text="已有生成产物时会再次确认，不会静默覆盖。",
            text_color=COLORS["muted"],
            font=(FONT_FAMILY, 9),
        ).grid(row=9, column=0, sticky="w", padx=22, pady=(7, 12))

        action_frame = ctk.CTkFrame(workflow, fg_color="transparent")
        action_frame.grid(row=10, column=0, sticky="ew", padx=22, pady=(0, 20))
        ctk.CTkButton(
            action_frame,
            text="校验配置",
            command=self._validate,
            width=106,
            height=42,
            fg_color=COLORS["panel"],
            hover_color=COLORS["accent_soft"],
            text_color=COLORS["accent"],
            border_width=1,
            border_color="#C7CBFF",
            font=(FONT_FAMILY, 11, "bold"),
        ).pack(side="left")
        ctk.CTkButton(
            action_frame,
            text="生成风扇项目  →",
            command=self._generate,
            width=154,
            height=42,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            font=(FONT_FAMILY, 11, "bold"),
        ).pack(side="left", padx=(8, 0))
        self.open_output_button = ctk.CTkButton(
            action_frame,
            text="打开目录",
            command=self._open_output,
            state="disabled",
            width=96,
            height=42,
            fg_color=COLORS["panel_subtle"],
            hover_color=COLORS["border"],
            text_color=COLORS["text"],
            border_width=1,
            border_color=COLORS["border"],
            font=(FONT_FAMILY, 10),
        )
        self.open_output_button.pack(side="left", padx=(8, 0))

        summary_frame = ctk.CTkFrame(
            tab,
            fg_color=COLORS["panel"],
            corner_radius=18,
            border_width=1,
            border_color=COLORS["border"],
        )
        summary_frame.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        summary_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            summary_frame,
            text="当前方案",
            text_color=COLORS["text"],
            font=(FONT_FAMILY, 16, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=22, pady=(20, 2))
        ctk.CTkLabel(
            summary_frame,
            text="根据当前配置自动提取的关键参数",
            text_color=COLORS["muted"],
            font=(FONT_FAMILY, 10),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 12))

        self.summary_vars: dict[str, tk.StringVar] = {}
        labels = (
            "项目名称",
            "芯片",
            "电机方案",
            "输入方案",
            "充电接口",
            "已启用功能",
        )
        for row, label in enumerate(labels, start=2):
            item = ctk.CTkFrame(
                summary_frame,
                fg_color=(
                    COLORS["accent_soft"]
                    if label == "项目名称"
                    else COLORS["panel_subtle"]
                ),
                corner_radius=10,
            )
            item.grid(
                row=row,
                column=0,
                sticky="ew",
                padx=18,
                pady=(0, 8),
            )
            item.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(
                item,
                text=label,
                text_color=COLORS["muted"],
                font=(FONT_FAMILY, 9),
                anchor="w",
            ).grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 0))
            variable = tk.StringVar(value="—")
            self.summary_vars[label] = variable
            ctk.CTkLabel(
                item,
                textvariable=variable,
                text_color=COLORS["text"],
                font=(FONT_FAMILY, 11, "bold"),
                anchor="w",
                justify="left",
                wraplength=320,
            ).grid(row=1, column=0, sticky="ew", padx=12, pady=(1, 8))

    def _build_config_tab(self) -> None:
        tab = self.config_tab
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        toolbar = ctk.CTkFrame(
            tab,
            fg_color=COLORS["panel"],
            corner_radius=16,
            border_width=1,
            border_color=COLORS["border"],
        )
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        toolbar.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            toolbar,
            text="动态配置树",
            text_color=COLORS["text"],
            font=(FONT_FAMILY, 15, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 1))
        ctk.CTkLabel(
            toolbar,
            text="双击配置项即可编辑；对象和列表会保持原始结构。",
            text_color=COLORS["muted"],
            font=(FONT_FAMILY, 9),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 14))

        tools = ctk.CTkFrame(toolbar, fg_color="transparent")
        tools.grid(row=0, column=1, rowspan=2, padx=16)
        for text, command in (
            ("折叠全部", lambda: self._set_tree_open(False)),
            ("展开全部", lambda: self._set_tree_open(True)),
        ):
            ctk.CTkButton(
                tools,
                text=text,
                command=command,
                width=86,
                height=34,
                fg_color=COLORS["panel_subtle"],
                hover_color=COLORS["border"],
                text_color=COLORS["text"],
                border_width=1,
                border_color=COLORS["border"],
                font=(FONT_FAMILY, 9),
            ).pack(side="left", padx=(0, 7))
        ctk.CTkButton(
            tools,
            text="编辑选中项",
            command=self._edit_selected,
            width=108,
            height=34,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            font=(FONT_FAMILY, 9, "bold"),
        ).pack(side="left")

        tree_frame = ctk.CTkFrame(
            tab,
            fg_color=COLORS["panel"],
            corner_radius=16,
            border_width=1,
            border_color=COLORS["border"],
        )
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        self.config_tree = ttk.Treeview(
            tree_frame,
            columns=("value", "type"),
            show="tree headings",
            selectmode="browse",
            style="Modern.Treeview",
        )
        self.config_tree.heading("#0", text="配置项")
        self.config_tree.heading("value", text="当前值")
        self.config_tree.heading("type", text="类型")
        self.config_tree.column("#0", width=390, minwidth=240)
        self.config_tree.column("value", width=470, minwidth=260)
        self.config_tree.column("type", width=86, minwidth=72, anchor="center")
        yscroll = ctk.CTkScrollbar(
            tree_frame,
            orientation="vertical",
            command=self.config_tree.yview,
            fg_color=COLORS["panel"],
            button_color="#CBD5E1",
            button_hover_color="#94A3B8",
        )
        xscroll = ctk.CTkScrollbar(
            tree_frame,
            orientation="horizontal",
            command=self.config_tree.xview,
            fg_color=COLORS["panel"],
            button_color="#CBD5E1",
            button_hover_color="#94A3B8",
        )
        self.config_tree.configure(
            yscrollcommand=yscroll.set,
            xscrollcommand=xscroll.set,
        )
        self.config_tree.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=(10, 0))
        yscroll.grid(row=0, column=1, sticky="ns", padx=(5, 6), pady=10)
        xscroll.grid(row=1, column=0, sticky="ew", padx=10, pady=(5, 6))
        self.config_tree.bind("<Double-1>", lambda _event: self._edit_selected())

    def _build_json_tab(self) -> None:
        tab = self.json_tab
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        toolbar = ctk.CTkFrame(
            tab,
            fg_color=COLORS["panel"],
            corner_radius=16,
            border_width=1,
            border_color=COLORS["border"],
        )
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        toolbar.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            toolbar,
            text="高级编辑模式",
            text_color=COLORS["text"],
            font=(FONT_FAMILY, 15, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 1))
        ctk.CTkLabel(
            toolbar,
            text="适用于复杂结构和暂未提供专用控件的新字段；应用后仍需通过后端校验。",
            text_color=COLORS["muted"],
            font=(FONT_FAMILY, 9),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 14))

        json_actions = ctk.CTkFrame(toolbar, fg_color="transparent")
        json_actions.grid(row=0, column=1, rowspan=2, padx=16)
        ctk.CTkButton(
            json_actions,
            text="格式化",
            command=self._format_json,
            width=88,
            height=34,
            fg_color=COLORS["panel_subtle"],
            hover_color=COLORS["border"],
            text_color=COLORS["text"],
            border_width=1,
            border_color=COLORS["border"],
            font=(FONT_FAMILY, 9),
        ).pack(side="left", padx=(0, 7))
        ctk.CTkButton(
            json_actions,
            text="应用 JSON",
            command=self._apply_json,
            width=102,
            height=34,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            font=(FONT_FAMILY, 9, "bold"),
        ).pack(side="left")

        editor_frame = ctk.CTkFrame(
            tab,
            fg_color=COLORS["editor"],
            corner_radius=16,
            border_width=1,
            border_color="#263449",
        )
        editor_frame.grid(row=1, column=0, sticky="nsew")
        editor_frame.grid_rowconfigure(1, weight=1)
        editor_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            editor_frame,
            text="CONFIG.JSON",
            text_color="#7C8AA1",
            font=(MONO_FONT_FAMILY, 9, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=18, pady=(12, 8))
        self.json_text = tk.Text(
            editor_frame,
            wrap="none",
            font=(MONO_FONT_FAMILY, 11),
            undo=True,
            padx=16,
            pady=12,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            background=COLORS["editor"],
            foreground=COLORS["editor_text"],
            insertbackground="#FFFFFF",
            selectbackground="#334155",
        )
        yscroll = ctk.CTkScrollbar(
            editor_frame,
            orientation="vertical",
            command=self.json_text.yview,
            fg_color=COLORS["editor"],
            button_color="#475569",
            button_hover_color="#64748B",
        )
        xscroll = ctk.CTkScrollbar(
            editor_frame,
            orientation="horizontal",
            command=self.json_text.xview,
            fg_color=COLORS["editor"],
            button_color="#475569",
            button_hover_color="#64748B",
        )
        self.json_text.configure(
            yscrollcommand=yscroll.set,
            xscrollcommand=xscroll.set,
        )
        self.json_text.grid(row=1, column=0, sticky="nsew", padx=(8, 0))
        yscroll.grid(row=1, column=1, sticky="ns", padx=(5, 7), pady=6)
        xscroll.grid(row=2, column=0, sticky="ew", padx=8, pady=(5, 7))
        self.json_text.bind("<<Modified>>", self._on_json_modified)

    def _build_result_tab(self) -> None:
        tab = self.result_tab
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        self.result_banner = ctk.CTkFrame(
            tab,
            fg_color=COLORS["accent_soft"],
            corner_radius=16,
            border_width=1,
            border_color="#D9DCFF",
        )
        self.result_banner.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        self.result_banner.grid_columnconfigure(1, weight=1)
        self.result_icon = ctk.CTkLabel(
            self.result_banner,
            text="i",
            width=42,
            height=42,
            corner_radius=12,
            fg_color=COLORS["accent"],
            text_color="#FFFFFF",
            font=(FONT_FAMILY, 17, "bold"),
        )
        self.result_icon.grid(row=0, column=0, rowspan=2, padx=18, pady=16)
        self.result_title_var = tk.StringVar(value="等待校验")
        self.result_detail_var = tk.StringVar(
            value="选择一个配置并运行校验，这里会显示资源规划和生成结果。"
        )
        ctk.CTkLabel(
            self.result_banner,
            textvariable=self.result_title_var,
            text_color=COLORS["text"],
            font=(FONT_FAMILY, 15, "bold"),
            anchor="w",
        ).grid(row=0, column=1, sticky="sew", pady=(14, 0))
        ctk.CTkLabel(
            self.result_banner,
            textvariable=self.result_detail_var,
            text_color=COLORS["muted"],
            font=(FONT_FAMILY, 9),
            anchor="w",
        ).grid(row=1, column=1, sticky="new", pady=(1, 14))
        ctk.CTkButton(
            self.result_banner,
            text="返回配置",
            command=lambda: self._show_page("config"),
            width=92,
            height=34,
            fg_color=COLORS["panel"],
            hover_color="#E8EAFF",
            text_color=COLORS["accent"],
            border_width=1,
            border_color="#C7CBFF",
            font=(FONT_FAMILY, 9, "bold"),
        ).grid(row=0, column=2, rowspan=2, padx=18)

        result_frame = ctk.CTkFrame(
            tab,
            fg_color=COLORS["editor"],
            corner_radius=16,
            border_width=1,
            border_color="#263449",
        )
        result_frame.grid(row=1, column=0, sticky="nsew")
        result_frame.grid_rowconfigure(1, weight=1)
        result_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            result_frame,
            text="FANFORGE OUTPUT",
            text_color="#7C8AA1",
            font=(MONO_FONT_FAMILY, 9, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=18, pady=(12, 6))
        self.result_text = ctk.CTkTextbox(
            result_frame,
            wrap="word",
            font=(MONO_FONT_FAMILY, 11),
            fg_color=COLORS["editor"],
            text_color=COLORS["editor_text"],
            corner_radius=0,
            border_width=0,
            state="disabled",
        )
        self.result_text.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=8,
            pady=(0, 8),
        )

    def _load_initial_preset(self) -> None:
        if not self.presets:
            messagebox.showerror(
                "没有可用预设",
                "未找到 configs/*.json。请重新构建应用并包含预设资源。",
                parent=self.root,
            )
            return
        preferred_name = "hs2811_classic_two_key_cooling_188"
        selected = next(
            (preset for preset in self.presets if preset.name == preferred_name),
            self.presets[0],
        )
        self._load_preset(selected)

    def _on_preset_selected(self, _event: tk.Event | None = None) -> None:
        if self._setting_preset:
            return
        label = self.preset_var.get()
        selected = next(
            (preset for preset in self.presets if preset.label == label),
            None,
        )
        if selected is None or selected == self.current_preset:
            return
        if self.document_dirty and not messagebox.askyesno(
            "放弃当前修改？",
            "切换预设会放弃尚未保存的配置修改，是否继续？",
            parent=self.root,
        ):
            self._set_preset_label(
                self.current_preset.label if self.current_preset else ""
            )
            return
        self._load_preset(selected)

    def _set_preset_label(self, value: str) -> None:
        self._setting_preset = True
        try:
            self.preset_var.set(value)
        finally:
            self._setting_preset = False

    def _load_preset(self, preset: Preset) -> None:
        try:
            raw = load_config_dict(preset.path)
        except FanForgeError as exc:
            messagebox.showerror("无法载入预设", str(exc), parent=self.root)
            return
        self.current_preset = preset
        self.document = ConfigDocument(raw, source_path=preset.path)
        self.document_dirty = False
        self._set_preset_label(preset.label)
        self._refresh_document_views(reset_output=True)
        self.status_var.set(f"已载入预设：{preset.name}")

    def _import_config(self) -> None:
        chosen = filedialog.askopenfilename(
            parent=self.root,
            title="导入 FanForge 配置",
            filetypes=(("JSON 配置", "*.json"), ("所有文件", "*.*")),
        )
        if not chosen:
            return
        path = Path(chosen)
        try:
            self.document = ConfigDocument.from_path(path)
        except (OSError, ValueError) as exc:
            messagebox.showerror("无法导入配置", str(exc), parent=self.root)
            return
        self.current_preset = None
        self.document_dirty = False
        self._set_preset_label(f"[外部] {path.name}")
        self._refresh_document_views(reset_output=True)
        self.status_var.set(f"已导入配置：{path}")

    def _save_config(self) -> None:
        if not self._commit_json_editor():
            return
        if self.document is None:
            return
        default_name = safe_directory_name(
            project_name(self.document.to_dict())
        ) + ".json"
        chosen = filedialog.asksaveasfilename(
            parent=self.root,
            title="保存配置副本",
            defaultextension=".json",
            initialfile=default_name,
            filetypes=(("JSON 配置", "*.json"),),
        )
        if not chosen:
            return
        path = Path(chosen)
        try:
            save_config_dict(self.document.to_dict(), path)
        except OSError as exc:
            messagebox.showerror("保存失败", str(exc), parent=self.root)
            return
        self.document.source_path = path
        self.document_dirty = False
        self.status_var.set(f"配置已保存：{path}")

    def _refresh_document_views(self, *, reset_output: bool = False) -> None:
        if self.document is None:
            return
        self._populate_tree()
        self._set_json_text(self.document.to_json())
        self._update_summary()
        if reset_output:
            self.output_var.set(
                output_directory_value(
                    self.output_var.get(),
                    self.document.to_dict(),
                )
            )
        self._set_result("尚未校验。\n\n选择“校验配置”查看资源规划结果。")
        self.last_output = None
        self.open_output_button.configure(state="disabled")

    def _update_summary(self) -> None:
        if self.document is None:
            return
        for label, value in summarize_config(self.document.to_dict()):
            self.summary_vars[label].set(friendly_value(value))

    def _populate_tree(self) -> None:
        self.config_tree.delete(*self.config_tree.get_children())
        self.item_paths.clear()
        if self.document is None:
            return
        raw = self.document.to_dict()
        for key, value in raw.items():
            self._insert_tree_node("", key, value, (key,))

    def _insert_tree_node(
        self,
        parent: str,
        key: str | int,
        value: Any,
        path: tuple[JsonPathPart, ...],
    ) -> None:
        if isinstance(key, int):
            label = f"[{key}]"
        else:
            translated = FIELD_LABELS.get(key)
            label = f"{translated}  ·  {key}" if translated else key
        item = self.config_tree.insert(
            parent,
            "end",
            text=label,
            values=(compact_value(value), value_kind(value)),
            open=len(path) <= 2,
        )
        self.item_paths[item] = path
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                self._insert_tree_node(
                    item,
                    child_key,
                    child_value,
                    (*path, child_key),
                )
        elif isinstance(value, list):
            for index, child_value in enumerate(value):
                self._insert_tree_node(
                    item,
                    index,
                    child_value,
                    (*path, index),
                )

    def _edit_selected(self) -> None:
        if not self._commit_json_editor():
            return
        if self.document is None:
            return
        selection = self.config_tree.selection()
        if not selection:
            messagebox.showinfo(
                "选择配置项",
                "请先在配置树中选择一项。",
                parent=self.root,
            )
            return
        path = self.item_paths[selection[0]]
        value = self.document.get(path)
        dialog = EditValueDialog(
            self.root,
            path=path,
            value=value,
            choices=choices_for_path(path, self.capabilities),
        )
        result = dialog.show()
        if result is NO_RESULT:
            return
        self.document.set(path, result)
        self.document_dirty = True
        self._refresh_document_views(reset_output=False)
        self.status_var.set(f"已修改 {display_path(path)}，尚未校验")

    def _set_tree_open(self, opened: bool) -> None:
        def walk(item: str) -> None:
            self.config_tree.item(item, open=opened)
            for child in self.config_tree.get_children(item):
                walk(child)

        for root_item in self.config_tree.get_children():
            walk(root_item)

    def _set_json_text(self, rendered: str) -> None:
        self._updating_json = True
        try:
            self.json_text.delete("1.0", "end")
            self.json_text.insert("1.0", rendered)
            self.json_text.edit_modified(False)
            self.json_dirty = False
        finally:
            self._updating_json = False

    def _on_json_modified(self, _event: tk.Event | None = None) -> None:
        if self._updating_json:
            return
        if self.json_text.edit_modified():
            self.json_dirty = True
            self.document_dirty = True
            self.json_text.edit_modified(False)
            self.status_var.set("JSON 已修改，尚未应用和校验")

    def _parse_json_editor(self) -> dict[str, Any]:
        raw = json.loads(self.json_text.get("1.0", "end-1c"))
        if not isinstance(raw, dict):
            raise ValueError("配置根必须是 JSON 对象")
        return raw

    def _commit_json_editor(self) -> bool:
        if not self.json_dirty:
            return True
        try:
            raw = self._parse_json_editor()
        except (ValueError, json.JSONDecodeError) as exc:
            messagebox.showerror("JSON 无效", str(exc), parent=self.root)
            self._show_page("json")
            return False
        source = self.document.source_path if self.document else None
        self.document = ConfigDocument(raw, source_path=source)
        self.document_dirty = True
        self._populate_tree()
        self._update_summary()
        self._set_json_text(self.document.to_json())
        return True

    def _apply_json(self) -> None:
        if self._commit_json_editor():
            self.status_var.set("JSON 已应用，尚未校验")

    def _format_json(self) -> None:
        try:
            raw = self._parse_json_editor()
        except (ValueError, json.JSONDecodeError) as exc:
            messagebox.showerror("JSON 无效", str(exc), parent=self.root)
            return
        self._set_json_text(
            json.dumps(raw, ensure_ascii=False, indent=2) + "\n"
        )
        self.json_dirty = True
        self.document_dirty = True
        self.status_var.set("JSON 已格式化，点击“应用 JSON”写入配置")

    def _browse_output(self) -> None:
        initial = Path(self.output_var.get()).expanduser()
        if not initial.exists():
            initial = initial.parent
        chosen = filedialog.askdirectory(
            parent=self.root,
            title="选择项目输出目录",
            initialdir=str(initial),
            mustexist=False,
        )
        if chosen:
            self.output_var.set(chosen)

    def _validate(self) -> None:
        if not self._commit_json_editor() or self.document is None:
            return
        self.status_var.set("正在调用后端校验…")
        self.root.update_idletasks()
        try:
            _, plan = self.adapter.validate(
                self.document.to_dict(),
                source_path=self.document.source_path,
            )
            summary = self.adapter.summarize(plan)
        except (FanForgeError, ValueError, OSError) as exc:
            self._show_validation_error(exc)
            return
        self._show_validation_success(summary)
        self._show_page("result")
        self.status_var.set("配置校验通过，可以生成项目")

    def _generate(self) -> None:
        if not self._commit_json_editor() or self.document is None:
            return
        output_text = self.output_var.get().strip()
        if not output_text:
            messagebox.showerror(
                "缺少输出目录",
                "请先选择项目输出目录。",
                parent=self.root,
            )
            return
        output = Path(output_text).expanduser()
        self.status_var.set("正在校验并生成项目…")
        self.root.update_idletasks()
        try:
            result = self.adapter.generate(
                self.document.to_dict(),
                output,
                source_path=self.document.source_path,
            )
        except OutputExistsError as exc:
            confirmed = messagebox.askyesno(
                "确认覆盖生成文件",
                f"{exc}\n\n只会覆盖 FanForge 的五个标准生成文件，是否继续？",
                parent=self.root,
                icon="warning",
            )
            if not confirmed:
                self.status_var.set("已取消生成，现有文件未改动")
                return
            try:
                result = self.adapter.generate(
                    self.document.to_dict(),
                    output,
                    source_path=self.document.source_path,
                    force=True,
                )
            except (FanForgeError, ValueError, OSError) as retry_exc:
                self._show_validation_error(retry_exc)
                return
        except (FanForgeError, ValueError, OSError) as exc:
            self._show_validation_error(exc)
            return

        self.last_output = result.output_dir
        self.open_output_button.configure(state="normal")
        self._show_generation_success(result)
        self._show_page("result")
        self.status_var.set(f"项目已生成：{result.output_dir}")
        messagebox.showinfo(
            "生成完成",
            f"风扇项目已生成到：\n{result.output_dir}",
            parent=self.root,
        )

    def _show_validation_error(self, error: Exception) -> None:
        rendered = f"配置未通过后端校验\n\n{error}\n"
        self._set_result(rendered, tone="danger")
        self._show_page("result")
        self.status_var.set("配置校验失败，请根据结果修改")
        messagebox.showerror("配置校验失败", str(error), parent=self.root)

    def _show_validation_success(self, summary: Any) -> None:
        pins = "\n".join(
            f"  {role:<20} -> {gpio}"
            for role, gpio in sorted(summary.resolved_pins.items())
        )
        rendered = (
            "配置校验通过\n"
            "=" * 60
            + f"\n项目：{summary.project}\n"
            + f"生成器版本：{summary.generator_version}\n"
            + f"电机方案：{friendly_value(summary.motor_kind)}\n"
            + f"Timer1：{summary.timer_actual_us:.3f} μs，"
            + f"reload={summary.timer_reload_hex}\n"
            + f"PWM：{summary.pwm_gpio} / {summary.pwm_timer}，"
            + f"{summary.pwm_actual_hz:.3f} Hz，"
            + f"误差 {summary.pwm_error_percent:.4f}%\n\n"
            + "已解析脚位：\n"
            + (pins or "  无")
            + "\n\n校验与资源冲突判断均由 FanForge 后端完成。\n"
        )
        self._set_result(rendered, tone="success")

    def _show_generation_success(self, result: Any) -> None:
        files = "\n".join(f"  - {name}" for name in result.written_files)
        rendered = (
            "项目生成完成\n"
            "=" * 60
            + f"\n项目：{result.summary.project}\n"
            + f"输出目录：{result.output_dir}\n\n"
            + "生成文件：\n"
            + files
            + "\n\n请继续按 generation_report.md 和 "
            + "acceptance_checklist.md 完成编译、板级测试与标定。\n"
        )
        self._set_result(rendered, tone="success", generated=True)

    def _set_result(
        self,
        rendered: str,
        *,
        tone: str = "neutral",
        generated: bool = False,
    ) -> None:
        if tone == "success":
            color = COLORS["success"]
            soft = COLORS["success_soft"]
            border = "#BDEBD9"
            icon = "✓"
            title = "项目生成完成" if generated else "配置校验通过"
            detail = (
                "生成产物已写入目标目录，可以继续编译和板级验收。"
                if generated
                else "后端已完成参数、脚位和资源冲突检查。"
            )
        elif tone == "danger":
            color = COLORS["danger"]
            soft = COLORS["danger_soft"]
            border = "#F7C7D0"
            icon = "!"
            title = "配置校验失败"
            detail = "请根据下方后端错误信息修改配置后重新校验。"
        else:
            color = COLORS["accent"]
            soft = COLORS["accent_soft"]
            border = "#D9DCFF"
            icon = "i"
            title = "等待校验"
            detail = "选择一个配置并运行校验，这里会显示资源规划和生成结果。"
        self.result_banner.configure(fg_color=soft, border_color=border)
        self.result_icon.configure(text=icon, fg_color=color)
        self.result_title_var.set(title)
        self.result_detail_var.set(detail)
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", rendered)
        self.result_text.configure(state="disabled")

    def _open_output(self) -> None:
        path = self.last_output
        if path is None or not path.exists():
            messagebox.showerror(
                "目录不存在",
                "尚未生成项目，或输出目录已被移动。",
                parent=self.root,
            )
            return
        try:
            if sys.platform == "win32":
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except OSError as exc:
            messagebox.showerror("无法打开目录", str(exc), parent=self.root)

    def _show_capabilities(self) -> None:
        window = ctk.CTkToplevel(self.root)
        window.title("FanForge 后端支持能力")
        window.geometry("900x680")
        window.minsize(720, 520)
        window.configure(fg_color=COLORS["background"])
        window.transient(self.root)
        frame = ctk.CTkFrame(
            window,
            fg_color=COLORS["panel"],
            corner_radius=18,
            border_width=1,
            border_color=COLORS["border"],
        )
        frame.pack(fill="both", expand=True, padx=18, pady=18)
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            frame,
            text="后端支持能力",
            text_color=COLORS["text"],
            font=(FONT_FAMILY, 20, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=22, pady=(20, 2))
        ctk.CTkLabel(
            frame,
            text="此目录由后端实时生成，用于描述枚举、功能模块和硬件能力。",
            text_color=COLORS["muted"],
            font=(FONT_FAMILY, 10),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 12))
        text = ctk.CTkTextbox(
            frame,
            wrap="none",
            font=(MONO_FONT_FAMILY, 11),
            fg_color=COLORS["editor"],
            text_color=COLORS["editor_text"],
            corner_radius=12,
            border_width=1,
            border_color="#263449",
        )
        text.grid(row=2, column=0, sticky="nsew", padx=22)
        text.insert(
            "1.0",
            json.dumps(self.capabilities, ensure_ascii=False, indent=2),
        )
        text.configure(state="disabled")
        ctk.CTkButton(
            frame,
            text="关闭",
            command=window.destroy,
            width=96,
            height=38,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            font=(FONT_FAMILY, 11, "bold"),
        ).grid(row=3, column=0, sticky="e", padx=22, pady=20)


def main() -> int:
    try:
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        root = ctk.CTk()
    except tk.TclError as exc:
        print(f"FanForge GUI could not start: {exc}", file=sys.stderr)
        return 1
    FanForgeApplication(root)
    root.mainloop()
    return 0
