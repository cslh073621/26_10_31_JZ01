# 188显示硬件映射审查

## 目标

显示硬件模块只负责把`Data[0..2]`中的逻辑段和角标连接到灯板的有向灯脚组合。它不修改页面切换、电量计算、按键动作或充电状态判断。

## 当前结构

- `Data[0]`的bit0、bit1用于百位数字`1`的两段。
- `Data[1]`用于十位七段码，bit0到bit6对应`a..g`。
- `Data[2]`用于个位七段码，bit0到bit6对应`a..g`。
- `Data[0]`的bit2到bit7依次保留给`percent`、`cooling`、`charge`、`fan`、`mist`和`aux`角标。
- 当前运行代码已经消费`percent`、`cooling`、`charge`、`fan`和`mist`。`aux`可以先完成硬件映射，但在对应功能模块加入前不会自行点亮。

## 有向灯脚

每个LED由一个正极灯脚和一个负极灯脚确定。例如：

```json
"icon.charge": {
  "positive": 1,
  "negative": 5
}
```

表示扫描`IO_LED_5`负极时，`IO_LED_1`保持输出高即可点亮该角标。若该位不应点亮，生成代码把`IO_LED_1`改成输入，避免同电平输出造成微亮。

生成器会拒绝：

- 正负极使用同一个灯脚。
- 灯脚序号超出`pin_count`。
- 同一个有向灯脚组合重复分配。
- 缺少百位、十位或个位的必要数字段。
- 配置未定义的逻辑信号。

反向组合是另一颗合法LED。例如`LED1+ / LED5-`和`LED5+ / LED1-`可以同时存在。

## 预置与自定义

`standard_188_cooling_percent_style_a`保持既有五线188映射和生成源码不变，兼容旧`classic_product.display_hardware`字段。

`custom_charlieplex_188`允许配置5到7个灯脚和完整段位关系。配置只写灯脚序号，物理芯片脚继续由顶层`pins.IO_LED_n`绑定，因此更换封装或脚位时不需要重写段位表。

## 角标行为

- `icon.percent`在显示电量时点亮。
- `icon.cooling`在确认存在制冷功能且`COOL_EN=1`时点亮。
- `icon.charge`配合`charge_blink_target=charge_icon`时，插入后点亮；`charge_num<100`时随500ms节拍闪烁，达到100后常亮。
- `icon.fan`在`fan_mode`非零时点亮，风扇关闭时熄灭。
- `icon.mist`在启用雾化模块且`wh_mode`非零时点亮，雾化关闭时熄灭。
- 充电闪烁仍由`insert_flag + charge_num`决定，不直接信任`charge_on_flag`或`charge_max_flag`。

## 保持不变

- `smg_close()`、`smg_188_scan()`和`show_mode_deal()`函数边界不变。
- 显示扫描仍在原有1ms调用位置执行。
- `Data[0..2]`继续采用局部变量计算后短暂关中断原子更新。
- 页面切换仍使用原有`mode_change_show()`、`show_mode_change()`和生成期规划的页面时间资源；硬件映射不参与页面时序判断。
- 电量映射、充放电追赶、无刷PWM、AD_FAN保护及睡眠时序不由显示硬件模块修改。

## 实板检查

新灯板首次生成后必须逐段验证：

1. 全亮自检是否覆盖所有数字段和角标。
2. `0..9`十位、个位是否缺段或串段。
3. `100..199`的百位`1`是否方向正确。
4. 每个角标是否对应正确业务状态。
5. 暗屏和闪烁灭相是否存在微亮。
6. 输入态灯脚是否影响复用按键或充电检测。
