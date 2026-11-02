# 纯有刷电机生成审查

## 目标

`brushed_fixed_duty`用于不带无刷升压链路的纯有刷风扇。生成器复用有刷/无刷兼容项目中已经存在的有刷PWM分支，不另创新的MCU运行时函数结构。

## 资源边界

- `FAN_ON`是实际PWM输出脚，由PWM规划器解析为Timer3或Timer4通道。
- 不绑定`PWM_FAN`，因为纯有刷没有独立无刷升压PWM。
- 不绑定`AD_FAN`，不生成风扇升压电压采样、`too_big_cnt`或16V保护判断。
- 电池监测仍使用内部`AIN12(VDD/4)`及原有二级平均。
- 无刷、固定电压和有刷/无刷兼容类型仍强制启用`AD_FAN`保护，不能借此配置关闭安全链路。

## 运行结构

生成的`AD_fan_deal()`保持成熟函数职责：

```c
if(!fan_mode)
{
    T3PWM2EN = 0;
    T3REN = 0;
    T3D2L = 0;
    T3D2H = 0;
    FAN_ON = 0;
    return;
}

T3D2L = FAN_PWM_DUTY_BASE
    + fan_mode / FAN_PWM_GEAR_DIVISOR;
T3D2H = 0;
T3PWM2EN = 1;
T3REN = 1;
```

具体寄存器由实际`FAN_ON`脚位确定，上述`T3PWM2`只是当前示例的`PC3`解析结果。

## 电量补偿

纯有刷直接使用：

- `battery_monitor.business.compensation.fan_segments`
- `battery_monitor.business.compensation.cooling`

不会生成`YOUSHUA_WUSHUA`或两套补偿运行分支。示例中的`[100, 140, 180, 218, 256]`和`218`来自成熟兼容项目的有刷分支，只用于展示，实际产品必须重新校准。

## 未改变内容

- `ADC_Sample()`到`v_bat_deal()`的电量采样、映射和追赶。
- `mode_change()`统一处理状态后果的职责。
- CHRG/STDBY、静态CHRG/CHRG_MAX或INSERT/CHRG充电状态表。
- `show_mode_deal()`、`smg_188_scan()`与页面切换。
- 按键消抖、短按/双击/长按动作。
- 睡眠GPIO、唤醒与全亮自检流程。

## 上板检查

1. 确认`FAN_ON`物理脚确实连接有刷电机PWM控制节点，而不是无刷负极常开MOS控制脚。
2. 示波器确认PWM脚、频率、周期和最小/最大档占空比。
3. 确认关闭风扇后PWM使能、Timer运行位和输出脚均为零。
4. 根据实际电池、风扇和制冷负载标定电量补偿。
5. 运行HSIDE/PICC真实编译，检查程序空间、变量空间和寄存器名称。
