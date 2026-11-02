# 机器可读能力目录

## 目的

`python -m fanforge capabilities`用于在新项目配置前读取FanForge当前版本真实支持的硬件和功能边界。它面向AI、自动化脚本以及后续可视化界面，不参与MCU运行。

## 输出内容

- 当前生成器版本、目标MCU、封装、主频分频和Timer1基础周期。
- 配置根字段、功能模块、模块参数、嵌套参数及严格未知字段策略。
- 四种已审核电机类型及各自必需脚位、时基和AD_FAN保护要求。
- 数字键、AD键、拨片加编码器和单按键加滑阻输入组合。
- 可配置按键动作、CHRG/STDBY、静态CHRG/CHRG_MAX、INSERT/CHRG充电接口、188硬件映射、状态角标和页面行为。
- 制冷、数字LED和固定占空比雾化的脚位与依赖。
- 无刷10ms启停、100K:10K、2V参考、16V保护和非插入不向上追赶等固定安全契约。
- 当前未实现且不能绕过验证的功能列表。

## 使用

直接输出：

```powershell
python -m fanforge capabilities
```

写入JSON：

```powershell
python -m fanforge capabilities --out build/capabilities.json
```

相同版本产生字节相同的JSON。能力目录只说明可填写什么；产品脚位和参数仍必须写入配置，再由`inspect`完成实际资源规划和冲突检查。

配置解析器会拒绝能力目录之外的功能模块、已支持模块中的未知参数，以及没有被启用功能申请的脚位角色。不能通过在JSON中自行加入`rgb`、`communication`或其他未知模块来绕过`not_implemented`边界，也不能把拼错的PWM、ADC或按键参数静默回落到默认值。

`configuration_contract`直接读取解析器使用的同一组字段常量：

- `root_fields`：配置根字段。
- `feature_modules`：当前实现的功能模块。
- `module_fields`：各模块允许的外层参数。
- `nested_fields`：电机曲线、电量曲线、按键条目和显示连接等嵌套参数。
- `pin_roles_are_feature_derived=true`：脚位角色不是自由字段，必须由启用模块提出需求。

该契约描述字段集合，具体类型、范围、依赖和脚位冲突仍以`inspect`的实际解析与规划结果为准。

## 满配回归配置

`configs/hs2811_classic_max_supported_single_chip_188.json`占用HS16P2811 SOP16的全部14个可用IO，同时启用当前单芯片常用模块。它不是默认产品参数，而是用于验证以下跨模块边界：

1. 风扇250kHz和雾化约108kHz自动分配到不同Timer。
2. AD_FAN、AD_KEY和内部电量通道统一轮询。
3. 四路AD按键、双击窗口、制冷、LED和雾化动作同时存在。
4. CHRG/STDBY唤醒、功能状态和睡眠阻塞条件完整合并。
5. 制冷和LED上电有无检测不会破坏对应输出恢复。

满配配置通过只表示当前规划器没有资源冲突，不表示其脚位和参数适合某个具体产品。
