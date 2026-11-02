# FanForge Windows 桌面应用

## 使用方式

桌面端只是现有 FanForge 后端的图形入口，不复制脚位、资源冲突、参数合法性或源码生成规则。界面采用现代化的侧边导航与卡片式工作区，“校验配置”和“生成风扇项目”都会直接调用同一套 Python 后端。

普通使用流程：

1. 打开 `FanForge.exe`。
2. 选择一个最接近目标产品的内置预设。
3. 确认当前方案和输出目录。
4. 如需调整脚位或参数，在“配置项”中双击对应字段；复杂内容可以在“高级 JSON”中修改。
5. 点击“校验配置”。
6. 校验通过后点击“生成风扇项目”。

输出目录仍由后端生成以下文件：

- `main.c.in`
- `main.h.in`
- `generation_report.md`
- `acceptance_checklist.md`
- `resolved_plan.json`

界面不会静默覆盖这些文件。目录中已有生成产物时，必须再次明确确认。

## 从源码运行

Windows 官方 Python 通常自带 Tkinter。在仓库根目录运行：

```powershell
python -m pip install -r requirements-desktop.txt
python -m fanforge_gui
```

现代界面由 CustomTkinter 提供，运行依赖集中在 `requirements-desktop.txt`。Linux 服务器若没有安装 Tkinter 或没有图形桌面，仍可运行全部后端和桌面核心测试，但不能显示窗口。这不影响 Windows EXE 构建。

## 在 Windows 本地构建 EXE

仓库根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File tools/build_windows.ps1
```

脚本会在 `.venv-build` 中建立独立构建环境、运行测试并调用 PyInstaller。完成后应用位于：

```text
dist\FanForge.exe
```

只想重新打包、跳过测试时可以使用 `-SkipTests`，但正式交付建议保留测试。

## 通过 GitHub Actions 构建

在仓库的 Actions 页面手动运行 **Build Windows EXE**，完成后下载名为 `FanForge-Windows` 的构建产物。推送 `v*` 标签时也会自动构建。

当前 Linux 工作区不能原生生成和运行 Windows EXE，因此最终 Windows 可执行文件以 Windows 本地构建或上述 Actions 构建结果为准。

## 后续扩展

- 在 `configs/` 新增合法 JSON 预设后，重新构建的应用会自动列出它，不需要修改界面代码。
- 配置树按实际 JSON 递归生成；后端新增普通字段时会自动显示，也不会在保存时丢失。
- 后端能力目录会为常用枚举字段提供下拉选项；未专门映射的新字段仍可用通用编辑器或高级 JSON 编辑。
- 新的后端入口统一接入 `fanforge_gui/adapter.py`，窗口代码不直接承载生成规则。
- PyInstaller 配置已经包含 `configs/`、核心模板、芯片能力 JSON 和 CustomTkinter 主题资源。新增运行时数据文件后，需要同时补入 `FanForgeGUI.spec`。

桌面端提供的是配置和生成入口；生成代码仍必须通过目标编译器、板级功能测试、电池曲线标定和验收清单，不能仅凭 GUI 显示“生成完成”直接量产。
