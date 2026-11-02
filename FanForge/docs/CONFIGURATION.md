# FanForge配置说明

## 1. 配置职责

JSON只描述确定的产品参数和物理脚位，不允许指定模板、函数源码或寄存器值。生成器根据芯片能力表和功能需求统一计算端口、ADC、Timer1与Timer3 PWM配置。

建议创建新项目时复制最接近的`configs/*.json`，只修改已经支持的字段。未知字段组合不能靠AI临时补代码，应先扩展生成器和测试。

配置根节点只允许`schema_version`、`project`、`mcu`、`timebase`、`pins`和`features`。`features`只允许能力目录中已经实现的模块，各模块及其电机曲线、电量曲线、按键条目、显示连接等嵌套对象只允许本文列出的参数；`pins`只允许当前功能实际申请的脚位角色。未知模块、未知参数、未知顶层入口和多余脚位都会拒绝生成，不能把拼错参数回落到默认值，也不能把未支持功能静默丢弃。

## 2. MCU与时基

```json
"mcu": {
  "model": "HS16P2811",
  "package": "SOP16",
  "oscillator_hz": 16000000,
  "system_divider": 2
},
"timebase": {
  "interrupt_us": 1000,
  "t1_prescaler": "auto"
}
```

当前只支持HS16P2811 SOP16。固定占空比配置通常直接使用1ms T1中断；固定电压7+3配置必须使用125us T1中断，并由生成器累计8次后派生真实1ms业务节拍。`system_divider`必须与HSIDE/烧录配置一致；生成代码中的`OSCM=0x00`只选择高速模式，不能代替工程分频设置。

## 3. 脚位

完整经典产品公共脚位必须绑定：

- `COOL_EN`
- `FAN_ON`
- `IO_LED_1`到`IO_LED_5`

电机附加脚位由`motor.kind`决定：

- `brushed_fixed_duty`：`FAN_ON`本身就是有刷电机PWM输出，不绑定`PWM_FAN`和`AD_FAN`。
- 其他无刷或有刷/无刷兼容类型：额外绑定`PWM_FAN`和`AD_FAN`。

充电检测脚由`features.charging.kind`决定：

- `chrg_stdby_active_low`：绑定`CHRG`和`STDBY`。
- `chrg_chrg_max_active_low_static`：绑定`CHRG`和`CHRG_MAX`，两脚都必须是稳定静态状态。
- `insert_active_high_chrg_active_low`：绑定`INSERT`和`CHRG`。
- `none`：不绑定充电检测脚。

输入脚位按`classic_product.input_kind`选择：

- `two_digital_keys_active_low`：绑定`KEY1`和`KEY2`两个数字输入脚。
- `digital_keys_active_low`：按`digital_key.keys`绑定连续的`KEY1..KEYN`，支持1到4个数字输入脚。
- `two_ad_keys_active_low_ranges`：只绑定一个`AD_KEY`模拟脚。
- `rotary_encoder_active_low`：绑定`ENC_A`和`ENC_B`，当前必须同时启用低有效拨片开关。
- `single_key_slide_resistor_active_low`：绑定低有效`KEY`、模拟量`AD_SLIDER`和高有效`SLIDER_ON`。

数值是SOP16物理脚号。生成器查能力表得到`PAx/PCx`、ADC通道、PWM通道和路由；脚位能力不符、重复占用或唤醒能力不符会拒绝生成。

## 4. 风扇PWM

```json
"motor": {
  "kind": "brushless_fixed_duty",
  "pwm_frequency_hz": 250000,
  "pwm_clock_source": "fosc",
  "pwm_prescaler": "auto",
  "run_duty_percent": 50,
  "duty_curve": {
    "base_count": 12,
    "gear_divisor": 4
  }
}
```

完整经典产品的运行占空比为：

```c
base_count + fan_mode / gear_divisor
```

生成器根据PWM脚、频率和时钟源计算通道、路由、分频和周期，并验证最大档占空比计数不超过周期。

`run_duty_percent`保留给资源演示配置；完整经典产品使用`duty_curve`。

纯有刷配置使用同一组固定占空比曲线，但PWM资源直接绑定到`FAN_ON`：

```json
"motor": {
  "kind": "brushed_fixed_duty",
  "pwm_frequency_hz": 108000,
  "pwm_clock_source": "fosc",
  "pwm_prescaler": "auto",
  "run_duty_percent": 75,
  "duty_curve": {
    "base_count": 98,
    "gear_divisor": 4
  }
}
```

生成器仍根据实际`FAN_ON`物理脚选择PWM通道、路由和周期。运行代码沿用成熟有刷分支，在`AD_fan_deal()`内直接写该PWM占空比；不会生成第二套运行时电机抽象。

当产品同时启用风扇和雾化等多个PWM资源时，生成器会在Timer3和Timer4可用路由中统一分配通道。Timer3的多个PWM通道共用时钟和周期，因此只有频率、时钟源、分频和周期完全兼容时才允许共存；Timer4具有独立周期，可用于隔离250kHz无刷风扇和约108kHz雾化。任何脚位、通道或共享周期冲突都会在生成期拒绝，不会静默改变目标频率。

## 5. AD_FAN保护

```json
"fan_voltage_protection": {
  "enabled": true,
  "adc_reference": "2v",
  "adc_clock": "fcpu",
  "discard_samples": 2,
  "average_samples": 8,
  "overvoltage_limit": {
    "voltage_mv": 16000,
    "divider_high_ohm": 100000,
    "divider_low_ohm": 10000,
    "adc_reference": "2v"
  },
  "consecutive_confirmations": 13
}
```

当前标准无刷配置使用100K:10K分压和2V参考。生成器在PC端把16V物理上限计算为ADC常量2978，MCU运行时不执行乘除法。外层`adc_reference`与`overvoltage_limit.adc_reference`必须一致，否则拒绝生成。

固定占空比保护和固定电压7+3调节都只使用一个`AD_FAN`通道。固定电压版本每得到一个新的`AD_FAN_VALUE`，先检查16V保护，再进入快调或200ms慢调判断，不会额外生成`AD_FAN_SAFE`通道。

`average_samples`必须是2的幂且累加结果不能超过`u16`。连续确认只按完成的新平均值计数，不按主循环次数计数。软件保护只能作为补充，升压电路仍必须具备硬件过压保护。

纯有刷电机不经过无刷升压链路，必须配置：

```json
"fan_voltage_protection": {
  "enabled": false
}
```

该组合不会申请`AD_FAN`、不会生成`too_big_cnt`和16V保护判断。除纯有刷外的所有电机类型仍强制要求启用保护，防止配置失误绕开无刷升压安全检查。

## 6. 有刷/无刷兼容

兼容配置的`motor.kind`为：

```json
"kind": "brushed_brushless_compat_fixed_voltage_7_3"
```

- 上电全亮自检前段把`PWM_FAN`配置为输入上拉，多次采样后判定电机类型。
- 极性固定为`YOUSHUA_WUSHUA=0`无刷、`1`有刷。
- 无刷：`FAN_ON`持续导通电机负极，`PWM_FAN`输出250kHz固定电压7+3升压控制。
- 有刷：关闭`PWM_FAN`升压通道，由`FAN_ON`对应Timer3 PWM直接控制电机负极。
- 两种电机分别使用各自的电量压降补偿参数，不能共用一套补偿。

纯有刷`brushed_fixed_duty`不执行上电类型检测，不生成`YOUSHUA_WUSHUA`，并直接使用`battery_monitor.business.compensation.fan_segments`和`cooling`作为有刷负载补偿。示例值来自现有兼容方案的成熟有刷分支，但新产品仍需按实际电池与负载标定。

## 7. 电量

```json
"battery_monitor": {
  "enabled": true,
  "business": {
    "enabled": true,
    "thresholds": {
      "zero_shutdown": 15000,
      "low": 18000,
      "p0": 15360,
      "p5": 17920,
      "p10": 18841,
      "p50": 19384,
      "p80": 20122,
      "p100": 21145
    },
    "compensation": {
      "fan_segments": [272, 312, 462, 571, 680],
      "cooling": 571
    },
    "timing_ms": {
      "charge_active": 90000,
      "charge_full": 25000,
      "discharge": 20000,
      "low_discharge": 5000
    }
  }
}
```

阈值必须按`p0 < p5 < p10 < p50 < p80 < p100`严格递增。五个风扇补偿值对应按最大档等分后的五个档位区间。

这些值属于产品电池和负载标定，不是通用默认真值。优先修正映射连续性和负载补偿，最后才调整追赶时间。

## 8. AD按键

```json
"ad_key": {
  "enabled": true,
  "adc_reference": "vdd",
  "adc_clock": "fcpu",
  "discard_samples": 2,
  "average_samples": 8
}
```

`classic_product.input_kind="ad_keys_active_low_ranges"`且省略`keys`时，使用默认双键阈值`KEY1=0..100`、`KEY2=610..810`，并保持原有KEY1档位循环/加档和KEY2制冷/减档动作。

自定义1到4键时填写：

```json
"ad_key": {
  "enabled": true,
  "adc_reference": "vdd",
  "adc_clock": "fcpu",
  "discard_samples": 2,
  "average_samples": 8,
  "double_click_ms": 350,
  "keys": [
    {"name": "KEY1", "min": 0, "max": 100,
     "short_action": "fan_cycle",
     "double_action": "cooling_toggle",
     "long_action": "fan_power_toggle"},
    {"name": "KEY2", "min": 610, "max": 810,
     "short_action": "fan_step_up", "long_action": "fan_step_up"},
    {"name": "KEY3", "min": 1210, "max": 1410,
     "short_action": "fan_step_down", "long_action": "fan_step_down"},
    {"name": "KEY4", "min": 1810, "max": 2010,
     "short_action": "cooling_toggle", "long_action": "none"}
  ]
}
```

同一个`AD_KEY`脚可解码连续命名的`KEY1`到`KEY4`。阈值使用完成废样和平均后的12位ADC结果，范围必须在0到4095之间且不能重叠。旧`two_ad_keys_active_low_ranges`仍严格要求KEY1/KEY2，用于保持已有配置兼容。

运行时，ADC模块只产生`AD_KEY_VALUE`和一次性`ad_key_ready_flag`；10ms输入处理先把新结果解码为低有效原生`bit KEY1..KEY4`，再按实际键数生成成熟`KEY_CHECK()`、动作消费、事件清理和睡眠条件。阈值均在生成期写成整数常量，MCU不执行除法。

短按、双击和长按当前允许`fan_cycle`、`fan_power_toggle`、`fan_step_up`、`fan_step_down`、`cooling_toggle`、`light_cycle`、`atomizer_toggle`及`none`。长按加减档使用原有重复节奏，其他长按动作只触发一次；`fan_step_up/down`长按仍要求`long_adjust=true`。

只有配置了非`none`的`double_action`才生成双击资源。第一次短按松手只启动`double_click_ms`窗口，窗口内第二次短按松手执行双击，超时后才执行单击；长按会取消同一按键尚未执行的单击。每个双击按键使用独立计数器和时间资源，窗口未结束时阻止睡眠。RGB和PWM调光动作尚未接入时仍会拒绝配置。

当启用睡眠时，同一物理脚在正常状态由ADC接管并关闭内部上下拉，睡眠状态恢复为输入上拉和Port A唤醒口。该复用只允许同一个`input.ad_key.AD_KEY`资源同时声明ADC和GPIO；不同功能占用同一脚仍会拒绝生成。

### 普通数字按键动作

旧`two_digital_keys_active_low`配置不写`features.digital_key`时，继续保持KEY1档位循环/连续加档、KEY2制冷/连续减档的原有固定行为。需要自定义时显式填写：

```json
"digital_key": {
  "enabled": true,
  "double_click_ms": 350,
  "keys": [
    {
      "name": "KEY1",
      "short_action": "fan_cycle",
      "double_action": "none",
      "long_action": "fan_power_toggle"
    },
    {
      "name": "KEY2",
      "short_action": "atomizer_toggle",
      "double_action": "cooling_toggle",
      "long_action": "none"
    }
  ]
}
```

- 旧`two_digital_keys_active_low`启用动作配置时仍必须且只能配置`KEY1`和`KEY2`。
- 新`digital_keys_active_low`允许连续配置`KEY1..KEYN`，`N`为1到4；每脚继续使用输入上拉、低有效以及既有睡眠唤醒规划。
- 动作集合和AD按键相同；制冷、LED、雾化动作必须先启用对应功能。
- 只有存在非`none`双击动作时才申请双击时间资源。第一次松手延迟单击，第二次松手执行双击，长按取消待定单击。
- `fan_step_up/down`长按仍要求`classic_product.long_adjust=true`，并保持成熟重复节奏；其他长按动作只触发一次。
- 新配置只按实际键数展开现有`KEY_CHECK()`、`KEY_deal()`、`Key_Clear()`和睡眠条件，不生成第二套数字按键状态机。

## 9. 拨片开关

```json
"slide_switch": {
  "enabled": true,
  "active_level": "low",
  "pull": "up",
  "zero_battery_disable_pull_wake": true
}
```

当前只开放已经按N68Y/N68Y1成熟结构审查的低有效拨片配置：`SWI_KEY`工作态和正常睡眠态均为输入上拉，接地时开机，释放为高电平时关机。拨片负责产品开关机后，档位按键只在已有档位之间循环，不再通过档位`0`关机。

固定占空比风扇发生AD_FAN超压后，拨片保持在开启位置不能立即重启；必须先拨到关闭位置清除`fan_error_flag`，再重新拨到开启位置。该规则避免未处理电机故障时反复自动启动。

`zero_battery_disable_pull_wake=true`时，`file_sleep_mode()`在`charge_num==0`且拨片仍接地时关闭`SWI_KEY`内部上拉，并把它从`WUACON`唤醒掩码中移除，避免100K接地电阻持续耗电。配置选定的充电检测脚仍保留正常唤醒配置。非零电量睡眠仍要求拨片处于关闭位置，并保留拨片唤醒。

当前未开放高有效、内部下拉或外部偏置的拨片组合；这些电路不能通过改JSON绕过审查。

## 10. 完整经典产品行为

```json
"classic_product": {
  "enabled": true,
  "input_kind": "two_digital_keys_active_low",
  "gear_steps": [20, 40, 60, 80, 100],
  "long_adjust": true,
  "charging_kind": "chrg_stdby_active_low",
  "cooling_enabled": true,
  "charge_max_gear": 60,
  "display_hardware": "standard_188_cooling_percent_style_a",
  "display_policy": "gear_3s_battery_3s_gear",
  "low_blink_target": "both_digits",
  "charge_blink_target": "last_digit",
  "sleep_enabled": true
}
```

当前可选值：

- `input_kind`: `two_digital_keys_active_low`、`digital_keys_active_low`、`two_ad_keys_active_low_ranges`、`ad_keys_active_low_ranges`、`rotary_encoder_active_low`或`single_key_slide_resistor_active_low`
- `charging_kind`: 旧配置兼容字段，新配置改用`features.charging`
- `display_hardware`: 旧配置兼容字段，新配置改用`features.display`
- `display_policy`: `gear_3s_battery_3s_gear`
- `low_blink_target`: `last_digit`或`both_digits`
- `charge_blink_target`: `last_digit`、`percent_icon`或`charge_icon`

新的188灯板硬件配置格式：

```json
"display": {
  "enabled": true,
  "profile": "custom_charlieplex_188",
  "drive_mode": "output_high_input_off",
  "pin_count": 5,
  "behavior": {
    "profile": "gear_event_battery_preview_idle",
    "gear_event_ms": 3000,
    "normal_battery_preview_ms": 5000,
    "normal_idle_page": "gear",
    "charging_idle_page": "battery"
  },
  "connections": {
    "hundreds.0": {"positive": 3, "negative": 4},
    "hundreds.1": {"positive": 2, "negative": 4},
    "icon.percent": {"positive": 2, "negative": 5},
    "icon.cooling": {"positive": 3, "negative": 5},
    "icon.charge": {"positive": 1, "negative": 5},
    "tens.a": {"positive": 2, "negative": 3},
    "ones.a": {"positive": 1, "negative": 2}
  }
}
```

完整自定义映射必须包含`hundreds.0/1`、`tens.a..g`及`ones.a..g`。`positive/negative`是`IO_LED_n`中的序号，不是芯片物理脚号；物理脚仍在顶层`pins`中绑定。相同有向灯脚组合不能分配给两个逻辑段。当前支持5到7个灯脚，驱动方式固定为常态输出高、不亮的阳极脚切输入、当前阴极脚拉低。映射了`icon.fan`时按`fan_mode`点亮，映射了`icon.mist`且启用雾化时按`wh_mode`点亮；没有对应灯珠时不生成虚假角标代码。

`display.behavior`当前支持两种确定性策略：

- `gear_3s_battery_3s_gear`：旧配置兼容策略，继续生成原有共用3s时间资源和源码。
- `gear_event_battery_preview_idle`：档位变化立即显示档位，经过`gear_event_ms`后进入电量页；非充电常态为档位时，可再显示`normal_battery_preview_ms`电量后回到档位；充电常态页由`charging_idle_page`决定。

`gear_event_ms`必须是10ms的整数倍，范围10ms到120s。`normal_battery_preview_ms`可设为0；当`normal_idle_page="battery"`时必须为0，避免生成“电量预览后仍停留电量”的无意义计时。所有时间资源仍由统一规划器生成，运行代码继续使用原有`show_mode`、`step_cnt`、`mode_change_show()`和`show_mode_change()`结构。

数字按键和AD按键使用离散`gear_steps`，必须严格递增且位于1到199；`charge_max_gear`必须是其中一个档位，保证充电限档后仍有明确的短按关机路径。

旋转编码器和滑动变阻器属于连续档位输入，不使用离散`gear_steps`，而是在`classic_product`中配置：

```json
"gear_range": {
  "minimum": 1,
  "maximum": 100
}
```

连续范围必须满足`1 <= minimum < maximum <= 199`，`charge_max_gear`可设置为范围内任意档位。为兼容0.11.0以前的配置，连续输入仍可读取旧`gear_steps`，但只取首尾值并归一化为连续范围；新项目不应继续使用这种旧写法。

`long_adjust=false`时不生成长按加减档动作，但当前按键扫描仍会识别长按并在松手后清除事件。

## 11. 旋转编码器

```json
"encoder": {
  "enabled": true,
  "pull": "up",
  "filter_us": 1000,
  "clockwise_increases": true,
  "normal_step": 1,
  "acceleration_window_ms": 500,
  "acceleration_events": 3,
  "accelerated_step": 5
}
```

当前编码器配置只开放经过1025滚轮结构审查的组合：

- A、B两相均输入上拉，但运行时只允许`ENC_A`进入Port A电平变化中断，`ENC_B`只在A相边沿中采样。
- A相下降沿保存B相，A相上升沿保存反相B；只有两个相位组成完整同向周期才产生一次档位事件。
- 新方向事件先抵消尚未处理的反向事件，避免机械抖动直接累积成反向跳档。
- `filter_us`按当前Timer1中断周期换算为整数计数，MCU不做除法。
- 加速窗口使用独立时间标志，不能复用显示闪烁的500ms事件标志。
- 当前必须启用低有效拨片开关，由拨片开关机；编码器在`gear_range.minimum`到`gear_range.maximum`之间连续调档，`long_adjust`必须关闭。
- 编码器两相不参与睡眠唤醒；正常/零电睡眠仍按拨片和配置选定的充电输入资源规划。

## 12. 滑动变阻器

```json
"slide_resistor": {
  "enabled": true,
  "adc_reference": "vdd",
  "adc_clock": "fcpu",
  "discard_samples": 2,
  "accumulation_samples": 8,
  "low_gear_adc_sum": 31129,
  "high_gear_adc_sum": 1638,
  "low_gear_at_high_adc": true,
  "deadband_gears": 3,
  "confirmation_count": 3,
  "supply_active_level": "high"
}
```

当前滑阻配置按1034与SS039成熟结构生成：

- `AD_SLIDER`每轮先废弃2次，再累积8次；结果保留为约0到32760的累积和，不右移成12位平均值。
- `low_gear_adc_sum`和`high_gear_adc_sum`是实板标定端点；`low_gear_at_high_adc`必须与两端大小关系一致。
- 开风扇后的首个完整滑阻结果只抓取当前位置为基准，不使用历史睡眠值。
- 运行中只有新结果相对基准超过`deadband_gears`对应的ADC差值，并连续达到`confirmation_count`次，才接受新基准并换算档位。
- 充电时关闭制冷、锁定`charge_max_gear`并忽略滑阻；拔出充电器后重新抓取当前基准。
- `SLIDER_ON`清醒时输出高，睡眠时输出低；`KEY`和配置选定的充电输入按实际Port A能力参与唤醒。
- 单按键短按开关风扇，长按只在风扇开启、未充电且有电量时切换制冷。

当前完整滑阻产品固定使用2次废样和8次累积，其他值会在生成期拒绝。端点、阈值和确认次数同样在生成期检查；档位换算保留成熟项目的整数`unsigned long`比例公式，在每个完整滑阻结果到达后用当前已确认基准计算，不进入单次ADC转换过程。

## 13. 输出与验证

每次生成后至少检查：

1. `generation_report.md`中的脚位、PWM频率、系统分频、ADC更新周期和产品行为。
2. `resolved_plan.json`中的正常/睡眠GPIO、唤醒掩码、占空比曲线和资源来源。
3. `main.c.in`中的灯板映射、充电极性、档位、压降补偿和实板阈值。
4. HSIDE/PICC编译的程序空间、数据空间、警告和校验码。
5. 实板上电自检、按键、插拔、低电、风扇空载保护、启停时序、睡眠功耗和电池曲线。

生成器通过不等于产品验证通过。

## 14. 制冷与LED可选功能

推荐新配置使用独立功能对象：

```json
"cooling": {
  "enabled": true,
  "presence_detection": true,
  "control_mode": "toggle_while_fan_on",
  "allow_while_charging": false
},
"light": {
  "enabled": true,
  "presence_detection": true,
  "mode_profile": "on_off_flash"
}
```

- 功能未启用时不会申请`COOL_EN`或`LED_ON`，也不会生成有无检测。
- 功能启用且省略`presence_detection`时默认开启上电检测。自检末段把控制脚配置成输入上拉，等待4个NOP后读取；低电平表示板上存在MOS下拉和对应功能，高电平表示未装功能。检测结束必须关闭上拉、恢复输出并拉低。
- `cooling.control_mode="toggle_while_fan_on"`保留成熟按键开关制冷结构；风扇关闭时`mode_change()`强制关闭制冷。
- `cooling.control_mode="follow_fan"`直接由`mode_change()`根据风扇状态驱动制冷，不接受`cooling_toggle`按键动作。
- `cooling.allow_while_charging`决定插入充电器后是否允许制冷；默认`false`。
- `light.mode_profile="fan_sync"`时LED随风扇开关，不占用独立状态变量。
- `light.mode_profile="on_off"`时，配置一个AD按键`short_action="light_cycle"`独立开关LED。
- `light.mode_profile="on_off_flash"`时，同一动作按`关 -> 常亮 -> 500ms闪烁 -> 关`循环。
- 独立LED模式会把`light_mode`加入睡眠条件；关闭LED后才允许睡眠。睡眠入口始终把`LED_ON`拉低。
- 旧`classic_product.cooling_enabled`仍可读取；新项目应改用`features.cooling`，若两处同时填写且值冲突会拒绝生成。

## 15. 充电接口

新配置使用独立充电模块：

```json
"charging": {
  "enabled": true,
  "kind": "chrg_stdby_active_low"
}
```

或：

```json
"charging": {
  "enabled": true,
  "kind": "chrg_chrg_max_active_low_static"
}
```

或：

```json
"charging": {
  "enabled": true,
  "kind": "insert_active_high_chrg_active_low"
}
```

不带充电接口时：

```json
"charging": {
  "enabled": false,
  "kind": "none"
}
```

- `chrg_stdby_active_low`要求`CHRG`和`STDBY`均为内部上拉、低有效输入。`CHRG=0`归一为充电中，`CHRG=1 && STDBY=0`归一为充满，两脚均高归一为未插入。
- `chrg_chrg_max_active_low_static`要求`CHRG`和`CHRG_MAX`均为内部上拉、低有效静态输入。`CHRG=0`归一为充电中，`CHRG=1 && CHRG_MAX=0`归一为充满，两脚均高归一为未插入。
- `insert_active_high_chrg_active_low`要求`INSERT`内部下拉、高有效，`CHRG`内部上拉、低有效。`INSERT=0`时无条件归一为未插入；`INSERT=1 && CHRG=0`为充电中；`INSERT=1 && CHRG=1`为充满。
- 工作态和睡眠态的上下拉、方向和唤醒掩码由GPIO规划器统一计算。启用睡眠时，所选输入脚必须绑定到支持Port A变化唤醒的物理脚。
- `none`不生成充电检测脚、`charge_on_flag/charge_max_flag`或充电追赶计时资源，只保留成熟的电量映射和放电追赶。
- 四种模式最终都使用同一`insert_flag`状态契约；充电限档、制冷限制、显示页面、电量追赶和睡眠条件没有分别重写。
- 静态`CHRG_MAX`类型不适用于IP5402/5307等通过闪烁频率、脉冲或充放电复用状态表达业务的接口；这类协议仍未实现，不能用静态类型代替。
- 旧`classic_product.charging_kind`仍可读取；新旧字段同时存在且不一致时拒绝生成。

## 16. 固定占空比雾化

```json
"atomizer": {
  "enabled": true,
  "pwm_frequency_hz": 108000,
  "pwm_clock_source": "fosc",
  "pwm_prescaler": "auto",
  "duty_percent": 10,
  "dependency": "fan_required",
  "allow_while_charging": true
}
```

- 启用后必须绑定`PWM_WH`物理脚，并至少给一个AD按键配置`atomizer_toggle`动作，避免生成无法操作的功能。
- `dependency="fan_required"`时风扇关闭会在`mode_change()`中强制清除`wh_mode`；`independent`允许雾化单独运行。
- `allow_while_charging=false`时插入充电器会强制关闭雾化；`true`则保留当前状态。
- `duty_percent`在生成期换算为固定整数`WH_DUTY`，MCU运行时不执行乘除法。
- `wh_deal()`沿用成熟项目结构：关闭时先禁止对应PWM通道并把占空比清零；只有同一Timer没有其他PWM通道工作时才关闭Timer运行位，避免误关有刷电机PWM。
- 睡眠入口会关闭`PWM_WH`、对应PWM通道和安全可关闭的Timer；`wh_mode`开启时阻止睡眠。
- 若灯板自定义映射包含`icon.fan`或`icon.mist`，显示缓冲分别按`fan_mode`或`wh_mode`控制对应角标；未映射时不猜测灯板连接。

## 17. 生成后验收

每次生成都会输出`acceptance_checklist.md`。先核对其中标记为`[x]`的脚位、PWM、电机类型、输入动作、充电、电量、显示和睡眠契约是否与需求及原理图一致，再完成标记为`[ ]`的目标编译器、示波器、实板、功耗和电池曲线测试。

验收清单与源码使用同一个已解析资源计划，不会重新推断配置，也不会因为清单内容改变MCU源码。生成成功只代表配置和资源规划通过，不能替代HSIDE/PICC编译及实板验证。

## 18. 机器可读能力目录

`python -m fanforge capabilities`输出当前版本真实支持的MCU、封装、电机类型、输入类型、按键动作、充电接口、显示策略、可选输出、必需脚位和固定安全契约。使用`--out`可把相同内容写入UTF-8 JSON。

能力目录不是模板选择器，不会生成或修改产品源码。新项目应先读取目录确认需求处于支持范围，再填写产品JSON并执行`inspect`和`generate`；`not_implemented`中的功能必须先扩展生成器、参考审查和测试，不能通过手工塞入占位符绕过。

Overvoltage confirmation policy: see [OVERVOLTAGE_CONFIRMATION.md](OVERVOLTAGE_CONFIRMATION.md). The legal range is 2..255; shipped configurations use 13 consecutive valid means. A normal result resets the counter. Single-result shutdown is rejected.
