# FanForge

FanForge 是一个确定性的 HS16P2811 风扇项目生成器。它使用应用内部唯一、受审查的核心模板，根据产品参数和物理脚位统一规划 GPIO、Timer1、Timer3/Timer4 PWM 和 ADC，并生成保持现有风扇项目代码风格的直接寄存器代码。

远程仓库：`https://github.com/cslh073621/AUTO_FAN_CREATER.git`

## 当前能力

FanForge 当前包含两层确定性输出：

- 资源演示配置：验证 HS16P2811 SOP16 的 GPIO、Timer1、Timer3/Timer4 PWM、ADC 和时间资源规划。
- 完整经典产品配置：生成1到4路可配置短按/双击/长按动作的独立低有效数字按键、一路1到4键可配置AD_KEY、拨片开关配旋转编码器或单按键配滑动变阻器、可选CHRG/STDBY、静态CHRG/CHRG_MAX或INSERT/CHRG充电接口、可选制冷、数字LED和固定占空比雾化、5到7脚可配置段位与角标的188显示、可配置档位页/电量页时序、分段电量、充放电追赶、睡眠唤醒，以及纯有刷固定占空比、无刷固定占空比、固定电压7+3或有刷/无刷上电识别兼容控制的完整单文件框架。

两层配置都使用同一个核心模板、同一套资源规划器和成熟函数顺序。完整经典产品配置已具备产品运行链路，但仍必须经过目标 HSIDE/PICC 编译、板级功能测试和电池曲线标定，不能仅凭生成成功直接量产。

配置采用严格门禁：未知顶层字段、未知功能模块、已支持模块中的未知参数和未参与规划的脚位角色会直接报错，不会被静默忽略后生成缺功能或错误默认参数源码。

`python -m fanforge capabilities`同时公开根字段、功能模块、模块参数和嵌套参数集合，AI与后续界面可直接按机器契约构造配置，不必从示例猜允许字段。

固定电压配置使用125us硬件中断执行7+3细分，并累计8次后才生成真实1ms业务节拍。生成器会计算每次AD_FAN结果更新之间可完成的7+3轮数，低于安全下限时直接拒绝生成。

所有当前无刷示例均把100K:10K分压、2V参考和16V物理上限换算为生成期常量2978。固定电压调节和超压保护共用同一个`AD_FAN_VALUE`，不会为保护额外切换参考或增加ADC通道。

当前尚未支持RGB动作、多档PWM照明、无拨片编码器产品、通信，以及IP5402/5307类脉冲和充放电复用状态协议。AD按键已支持逐键短按、双击和长按动作，固定占空比雾化已支持独立或依赖风扇运行，自定义188已支持百分号、制冷、充电、风扇和雾化状态角标，以及“事件档位页 -> 电量预览 -> 常态页”时序；每块新灯板仍必须根据原理图或实测映射填写，生成器不会猜测。

## 使用

### Windows 桌面应用

FanForge 提供现代化中文桌面前端：左侧工作区集中提供快速生成、配置编辑、高级 JSON 和校验结果，主界面以卡片方式展示当前产品方案。选择现有产品预设、按需调整配置，经过同一套后端校验后即可生成风扇项目。桌面端保留完整配置树和高级 JSON 入口，后续新增预设与普通配置字段不需要重写界面。

从源码启动：

```powershell
python -m pip install -r requirements-desktop.txt
python -m fanforge_gui
```

在 Windows 构建单文件 `FanForge.exe`：

```powershell
powershell -ExecutionPolicy Bypass -File tools/build_windows.ps1
```

也可以在 GitHub Actions 中手动运行 **Build Windows EXE** 并下载构建产物。完整说明见[`docs/DESKTOP_APP.md`](docs/DESKTOP_APP.md)。

### 命令行

查看生成器当前真实支持的选项、依赖和必需脚位：

```powershell
python -m fanforge capabilities
python -m fanforge capabilities --out build/capabilities.json
```

检查配置和资源规划：

```powershell
python -m fanforge inspect configs/hs2811_brushless_minimal.json
```

生成初版示例：

```powershell
python -m fanforge generate configs/hs2811_brushless_minimal.json `
  --out examples/hs2811_brushless_minimal
```

如果输出目录已存在`main.c.in`、`main.h.in`、报告、验收清单或解析计划，`generate`默认拒绝覆盖。确认已经审查或备份人工修改后，才可显式追加`--force`：

```powershell
python -m fanforge generate configs/hs2811_brushless_minimal.json `
  --out examples/hs2811_brushless_minimal --force
```

生成完整经典产品示例：

```powershell
python -m fanforge generate configs/hs2811_classic_two_key_cooling_188.json `
  --out examples/hs2811_classic_two_key_cooling_188
```

生成双AD按键经典产品示例：

```powershell
python -m fanforge generate configs/hs2811_classic_two_ad_key_cooling_188.json `
  --out examples/hs2811_classic_two_ad_key_cooling_188
```

生成省略阈值的默认双AD按键示例：

```powershell
python -m fanforge generate configs/hs2811_classic_default_two_ad_key_cooling_188.json `
  --out examples/hs2811_classic_default_two_ad_key_cooling_188
```

生成四AD按键自定义阈值和动作示例：

```powershell
python -m fanforge generate configs/hs2811_classic_four_ad_key_cooling_188.json `
  --out examples/hs2811_classic_four_ad_key_cooling_188
```

生成带350ms双击窗口和长按单次动作的AD按键示例：

```powershell
python -m fanforge generate configs/hs2811_classic_four_ad_key_double_click_cooling_light_188.json `
  --out examples/hs2811_classic_four_ad_key_double_click_cooling_light_188
```

生成风扇250kHz、雾化108kHz双PWM示例：

```powershell
python -m fanforge generate configs/hs2811_classic_two_ad_key_atomizer_188.json `
  --out examples/hs2811_classic_two_ad_key_atomizer_188
```

生成可配置数字双键、雾化和制冷示例：

```powershell
python -m fanforge generate configs/hs2811_classic_two_digital_key_atomizer_cooling_188.json `
  --out examples/hs2811_classic_two_digital_key_atomizer_cooling_188
```

生成四路独立数字按键示例：

```powershell
python -m fanforge generate configs/hs2811_classic_four_digital_key_188.json `
  --out examples/hs2811_classic_four_digital_key_188
```

生成拨片开关经典产品示例：

```powershell
python -m fanforge generate configs/hs2811_classic_slide_switch_two_key_cooling_188.json `
  --out examples/hs2811_classic_slide_switch_two_key_cooling_188
```

生成拨片开关加旋转编码器示例：

```powershell
python -m fanforge generate configs/hs2811_classic_slide_switch_encoder_188.json `
  --out examples/hs2811_classic_slide_switch_encoder_188
```

生成单按键加滑动变阻器示例：

```powershell
python -m fanforge generate configs/hs2811_classic_single_key_slide_resistor_cooling_188.json `
  --out examples/hs2811_classic_single_key_slide_resistor_cooling_188
```

生成固定电压7+3经典产品示例：

```powershell
python -m fanforge generate configs/hs2811_classic_fixed_voltage_7_3.json `
  --out examples/hs2811_classic_fixed_voltage_7_3
```

生成有刷/无刷上电识别兼容示例：

```powershell
python -m fanforge generate configs/hs2811_classic_brushed_brushless_compat.json `
  --out examples/hs2811_classic_brushed_brushless_compat
```

生成纯有刷固定占空比示例：

```powershell
python -m fanforge generate configs/hs2811_classic_brushed_fixed_duty_188.json `
  --out examples/hs2811_classic_brushed_fixed_duty_188
```

生成占满SOP16全部14个可用IO的单芯片组合回归示例：

```powershell
python -m fanforge generate configs/hs2811_classic_max_supported_single_chip_188.json `
  --out examples/hs2811_classic_max_supported_single_chip_188
```

生成带风扇标、雾化标和百分号的自定义188示例：

```powershell
python -m fanforge generate configs/hs2811_classic_two_ad_key_atomizer_fan_mist_icons_188.json `
  --out examples/hs2811_classic_two_ad_key_atomizer_fan_mist_icons_188
```

批量重建全部能力对照版本：

```powershell
powershell -ExecutionPolicy Bypass -File tools/generate_showcase.ps1
```

运行测试：

```powershell
python -m unittest discover -s tests -v
powershell -ExecutionPolicy Bypass -File tools/validate_core.ps1
```

## 输出文件

- `main.c.in`：生成的 C 源码预览。
- `main.h.in`：生成的头文件预览。
- `generation_report.md`：脚位、寄存器、频率、误差和限制报告。
- `acceptance_checklist.md`：根据已解析配置生成的产品验收清单，区分生成器已验证项和必须实测项。
- `resolved_plan.json`：生成器解析后的完整资源计划。

当前命令行工具不直接写 `.c` 和 `.h`，因为本机透明加密会拦截 Python 直接创建这些后缀。这样可以避免把加密内容误提交到仓库；正式输出后缀转换需要后续结合白名单工具链单独处理。

## 确定性原则

1. 配置只描述硬件和产品需求，不能选择模板或参考项目。
2. 应用内部只有一个权威 HS2811 核心模板。
3. 功能模块只声明资源和业务约束，公共规划器统一生成初始化。
4. 相同生成器版本和相同配置必须产生字节级相同结果。
5. 不支持或发生资源冲突时必须停止，不能调用 AI 临时补代码。
6. 生成代码保持成熟项目的单文件结构、函数职责和调用顺序。
7. 功能配置必须先通过统一资源冲突和业务约束校验，再允许生成源码。

长期架构目标见`docs/DESIGN_DECISIONS.md`的“最终应用层目标”：前端最终按原子化硬件与功能选项构造配置，预设只负责快捷填参、示例和回归，不作为可选择的底层源码模板。

## 关键文件

- `core/hs2811_fan_core.c.in`：唯一核心源码骨架。
- `fanforge/chips/hs2811_sop16.json`：SOP16 脚位和外设能力表。
- `fanforge/modules.py`：功能模块的 GPIO、PWM、ADC 和时间资源需求。
- `fanforge/planner.py`：GPIO、T1、T3 PWM、ADC 统一规划器。
- `fanforge/classic_product.py`：完整经典产品配置的成熟业务代码生成规则。
- `fanforge/emitter.py`：确定性源码、计划和报告生成器。
- `fanforge/capabilities.py`：机器可读的支持项、依赖、必需脚位和固定安全契约。
- `configs/hs2811_brushless_minimal.json`：初版示例参数。
- `configs/hs2811_classic_two_key_cooling_188.json`：完整经典产品示例参数。
- `configs/hs2811_classic_two_ad_key_cooling_188.json`：一路AD_KEY解码双按键并复用睡眠唤醒的完整示例。
- `configs/hs2811_classic_default_two_ad_key_cooling_188.json`：省略按键阈值并采用默认双键方案的完整示例。
- `configs/hs2811_classic_four_ad_key_cooling_188.json`：一路AD_KEY解码四个自定义阈值按键和动作的完整示例。
- `configs/hs2811_classic_four_ad_key_double_click_cooling_light_188.json`：AD按键延迟单击、双击、长按单次动作和独立双击窗口示例。
- `configs/hs2811_classic_four_digital_key_188.json`：四路独立GPIO按键、连续加减档和睡眠唤醒示例。
- `docs/DIGITAL_KEY_REVIEW.md`：普通数字按键数量、动作、唤醒和旧双键兼容边界审查。
- `docs/AD_KEY_REVIEW.md`：AD按键阈值、成熟函数边界和睡眠复用审查。
- `configs/hs2811_classic_slide_switch_two_key_cooling_188.json`：拨片开关独占开关机并在零电睡眠时断开上拉和唤醒的完整示例。
- `docs/SLIDE_SWITCH_REVIEW.md`：拨片开关有效电平、状态归一、风扇故障恢复和零电睡眠审查。
- `configs/hs2811_classic_slide_switch_encoder_188.json`：拨片独占开关机、可配置连续档位范围、编码器调档和独立加速窗口的完整示例。
- `docs/ENCODER_REVIEW.md`：编码器A相中断、B相采样、整周期确认、滤波和加速边界审查。
- `configs/hs2811_classic_single_key_slide_resistor_cooling_188.json`：单按键开关风扇、长按制冷、可配置连续滑阻档位范围和充电限档的完整示例。
- `docs/SLIDE_RESISTOR_REVIEW.md`：滑阻八次累积、三档死区、连续确认、供电脚和睡眠边界审查。
- `configs/hs2811_classic_brushed_fixed_duty_188.json`：`FAN_ON`直接输出有刷电机PWM、不申请无刷升压和AD_FAN资源的完整示例。
- `docs/BRUSHED_MOTOR_REVIEW.md`：纯有刷脚位、PWM、电量补偿和明确排除的无刷资源审查。
- `docs/ACCEPTANCE_CHECKLIST_REVIEW.md`：生成验收清单的确定性边界、内容和发布门禁说明。
- `docs/OUTPUT_SAFETY_REVIEW.md`：生成输出防覆盖规则和`--force`使用边界。
- `configs/hs2811_classic_max_supported_single_chip_188.json`：占用SOP16全部14个可用IO的跨模块资源回归配置。
- `configs/hs2811_classic_two_ad_key_atomizer_fan_mist_icons_188.json`：风扇标、雾化标和百分号跟随已有状态的自定义188示例。
- `docs/CAPABILITY_CATALOG.md`：能力目录命令、确定性边界和新项目使用方式。
- `configs/hs2811_classic_two_key_cooling_light_fan_sync_188.json`：制冷按键开关、LED随风扇同步和两种功能有无检测示例。
- `configs/hs2811_classic_four_ad_key_cooling_light_on_off_188.json`：制冷随风扇、LED独立开关示例。
- `configs/hs2811_classic_four_ad_key_cooling_light_on_off_flash_188.json`：制冷随风扇、LED关/常亮/闪烁循环示例。
- `docs/OPTIONAL_FEATURES_REVIEW.md`：制冷、LED有无检测、控制模式和充电约束审查。
- `configs/hs2811_classic_two_key_insert_chrg_cooling_188.json`：INSERT高有效、CHRG低有效充电接口示例。
- `configs/hs2811_classic_two_key_chrg_chrg_max_static_cooling_188.json`：CHRG与CHRG_MAX双静态低有效充电接口示例。
- `configs/hs2811_classic_two_key_no_charging_188.json`：不申请充电检测脚和充电追赶计时资源的示例。
- `docs/CHARGING_INTERFACE_REVIEW.md`：CHRG/STDBY、静态CHRG/CHRG_MAX、INSERT/CHRG和无充电接口的状态表、上下拉及唤醒审查。
- `configs/hs2811_classic_two_key_insert_chrg_cooling_three_icon_188.json`：五线188自定义段位及百分号、制冷、充电三角标示例。
- `docs/DISPLAY_HARDWARE_REVIEW.md`：188逻辑段、角标、正负灯脚和扫描生成规则。
- `docs/SHOWCASE_MATRIX.md`：当前支持选项的全部对照版本。
- `docs/CONFIGURATION.md`：当前JSON参数、允许值和生成后验证要求。
- `docs/CLASSIC_PROFILE_REVIEW.md`：完整经典产品的函数、参数、安全边界和验证说明。
- `docs/FIXED_VOLTAGE_7_3_REVIEW.md`：固定电压7+3时基、控制链路和生成限制。
- `docs/TIME_RESOURCE_REVIEW.md`：时间请求、合并和分层生成规则。
- `docs/ADC_RESOURCE_REVIEW.md`：多 ADC 请求、轮询、滤波和结果分发规则。
- `docs/INITIAL_RELEASE_REVIEW.md`：初版功能、边界和审查重点。
- `docs/DESIGN_DECISIONS.md`：讨论形成的长期设计约束。
- `HANDOFF.md`：项目进度和更改记录。
