# 当前支持选项对照版本

这组配置用于观察生成器已经能够确定性处理哪些硬件资源和产品参数。全部版本都不是已经完成电气标定的量产项目。

| 配置 | PWM脚/通道 | PWM时钟 | 目标频率 | 系统分频 | T1分频 | AD_FAN | ADC时钟 | 平均 |
| --- | --- | --- | ---: | ---: | ---: | --- | --- | ---: |
| `hs2811_brushless_minimal` | PA7/T3PWM3 | Fosc | 250kHz | /2 | auto | PC1/AIN5 | Fcpu | 8 |
| `hs2811_brushless_adc_fan_battery_key` | PA7/T3PWM3 | Fosc | 250kHz | /2 | auto | AIN12(VDD/4) + PC1/AIN5 + PA6/AIN13 | Fcpu | 8 + 电量二级16组 |
| `hs2811_brushless_pwm0_pa0_fcpu_125k` | PA0/T3PWM0 | Fcpu/2 | 125kHz | /2 | /8 | PC1/AIN5 | Fcpu/2 | 2 |
| `hs2811_brushless_pwm0_pc4_zero_route_250k` | PC4/T3PWM0 | Fosc | 250kHz | /2 | /1 | PC1/AIN5 | Fcpu/8 | 8 |
| `hs2811_brushless_pwm1_pa1_120k` | PA1/T3PWM1 | Fosc | 120kHz | /1 | /4 | PC0/AIN4 | Fcpu/16 | 16 |
| `hs2811_brushless_pwm2_pc3_250k` | PC3/T3PWM2 | Fosc | 250kHz | /8 | auto | PA7/AIN14 | Fcpu | 1 |
| `hs2811_brushless_pwm4_pc5_200k` | PC5/T3PWM4 | Fosc | 200kHz | /4 | /2 | PA6/AIN13 | Fcpu/8 | 4 |
| `hs2811_classic_two_key_cooling_188` | PC4/T3PWM0 | Fosc | 250kHz | /2 | auto | AIN12(VDD/4) + PC1/AIN5 | Fcpu | 8 + 电量二级16组 |
| `hs2811_classic_two_ad_key_cooling_188` | PC4/T3PWM0 | Fosc | 250kHz | /2 | auto | AIN12(VDD/4) + PC1/AIN5 + PA6/AIN13 | Fcpu | 8 + 电量二级16组 |
| `hs2811_classic_default_two_ad_key_cooling_188` | PC4/T3PWM0 | Fosc | 250kHz | /2 | auto | AIN12(VDD/4) + PC1/AIN5 + PA6/AIN13 | Fcpu | 8 + 电量二级16组 |
| `hs2811_classic_four_ad_key_cooling_188` | PC4/T3PWM0 | Fosc | 250kHz | /2 | auto | AIN12(VDD/4) + PC1/AIN5 + PA6/AIN13 | Fcpu | 8 + 电量二级16组 |
| `hs2811_classic_two_key_cooling_light_fan_sync_188` | PC4/T3PWM0 | Fosc | 250kHz | /2 | auto | AIN12(VDD/4) + PC1/AIN5 | Fcpu | 8 + 电量二级16组 |
| `hs2811_classic_four_ad_key_cooling_light_on_off_188` | PC4/T3PWM0 | Fosc | 250kHz | /2 | auto | AIN12(VDD/4) + PC1/AIN5 + PA6/AIN13 | Fcpu | 8 + 电量二级16组 |
| `hs2811_classic_four_ad_key_cooling_light_on_off_flash_188` | PC4/T3PWM0 | Fosc | 250kHz | /2 | auto | AIN12(VDD/4) + PC1/AIN5 + PA6/AIN13 | Fcpu | 8 + 电量二级16组 |
| `hs2811_classic_two_key_insert_chrg_cooling_188` | PC4/T3PWM0 | Fosc | 250kHz | /2 | auto | AIN12(VDD/4) + PC1/AIN5 | Fcpu | 8 + 电量二级16组 |
| `hs2811_classic_two_key_chrg_chrg_max_static_cooling_188` | PC4/T3PWM0 | Fosc | 250kHz | /2 | auto | AIN12(VDD/4) + PC1/AIN5 | Fcpu | 8 + 电量二级16组 |
| `hs2811_classic_two_key_no_charging_188` | PC4/T3PWM0 | Fosc | 250kHz | /2 | auto | AIN12(VDD/4) + PC1/AIN5 | Fcpu | 8 + 电量二级16组 |
| `hs2811_classic_slide_switch_two_key_cooling_188` | PC4/T3PWM0 | Fosc | 250kHz | /2 | auto | AIN12(VDD/4) + PC1/AIN5 | Fcpu | 8 + 电量二级16组 |
| `hs2811_classic_slide_switch_encoder_188` | PC4/T3PWM0 | Fosc | 250kHz | /2 | auto | AIN12(VDD/4) + PC1/AIN5 | Fcpu | 8 + 电量二级16组 |
| `hs2811_classic_single_key_slide_resistor_cooling_188` | 无刷PC4/T3PWM0；有刷PC3/T3PWM2 | Fosc | 250kHz/约108kHz | /2 | auto | AIN12(VDD/4) + PC1/AIN5 + PC2/AIN6滑阻 | Fcpu | 电池/AD_FAN平均8次；滑阻累积8次 |
| `hs2811_classic_two_key_cooling_188_199_no_long` | PC4/T3PWM0 | Fosc | 250kHz | /2 | auto | AIN12(VDD/4) + PC1/AIN5 | Fcpu | 8 + 电量二级16组 |
| `hs2811_classic_two_key_cooling_188_icon_blink_200k` | PC4/T3PWM0 | Fosc | 200kHz | /2 | auto | AIN12(VDD/4) + PC1/AIN5 | Fcpu | 8 + 电量二级16组 |
| `hs2811_classic_fixed_voltage_7_3` | PC4/T3PWM0 | Fosc | 250kHz | /2 | auto | AIN12(VDD/4) + PC1/AIN5，2V参考 | Fcpu | 8 + 电量二级16组 |
| `hs2811_classic_brushed_brushless_compat` | 无刷PC4/T3PWM0；有刷PC3/T3PWM2 | Fosc | 250kHz/约108kHz | /2 | auto | AIN12(VDD/4) + PC1/AIN5，2V参考 | Fcpu | 8 + 电量二级16组 |
| `hs2811_classic_brushed_fixed_duty_188` | PC3/T3PWM2（FAN_ON） | Fosc | 约108kHz | /2 | auto | 仅AIN12(VDD/4)，无AD_FAN | Fcpu | 电量平均8次、二级16组 |
| `hs2811_classic_two_ad_key_atomizer_188` | 风扇PA7/T4PWM；雾化PC5/T3PWM4 | Fosc | 250kHz/约108kHz | /2 | auto | AIN12(VDD/4) + PC1/AIN5 + PA6/AIN13 | Fcpu | 8 + 电量二级16组 |
| `hs2811_classic_two_ad_key_atomizer_fan_mist_icons_188` | 风扇PA7/T4PWM；雾化PC5/T3PWM4 | Fosc | 250kHz/约108kHz | /2 | auto | AIN12(VDD/4) + PC1/AIN5 + PA6/AIN13 | Fcpu | 8 + 电量二级16组 |
| `hs2811_classic_two_digital_key_atomizer_cooling_188` | 风扇PA7/T4PWM；雾化PC5/T3PWM4 | Fosc | 250kHz/约108kHz | /2 | auto | AIN12(VDD/4) + PC1/AIN5 | Fcpu | 8 + 电量二级16组 |
| `hs2811_classic_four_digital_key_188` | PA1/T3PWM1 | Fosc | 250kHz | /2 | auto | AIN12(VDD/4) + PA0/AIN0 | Fcpu | 8 + 电量二级16组 |
| `hs2811_classic_max_supported_single_chip_188` | 风扇PA7/T4PWM；雾化PC5/T3PWM4 | Fosc | 250kHz/约108kHz | /2 | auto | AIN12(VDD/4) + PC3/AIN7 + PA6/AIN13 | Fcpu | 8 + 电量二级16组 |

## 实际生成的关键寄存器

| 配置 | T1 | Timer3 | PWM路由 | 运行占空比寄存器 | ADC |
| --- | --- | --- | --- | --- | --- |
| `minimal` | `T1CON=01 reload=E0C0` | `T3C1=17 T3PL=3F` | `PWMSEL=C0` | `T3D3L=20` | `ADM=95 ADR=40 ADPCON=20` |
| `adc_fan_battery_key` | `T1CON=01 reload=E0C0` | `T3C1=17 T3PL=3F` | `PWMSEL=C0` | `T3D3L=20` | `ADM=9C/95/9D VREFH=00/03/03 ADPCON=20 ADPCON1=40` |
| `pwm0_pa0_fcpu_125k` | `T1CON=31 reload=FC18` | `T3C1=07 T3PL=1F` | `PWMSEL=01` | `T3D0L=0D` | `ADM=95 ADR=50 ADPCON=20` |
| `pwm0_pc4_zero_route_250k` | `T1CON=01 reload=E0C0` | `T3C1=17 T3PL=3F` | `PWMSEL=00` | `T3D0L=23` | `ADM=95 ADR=10 ADPCON=20` |
| `pwm1_pa1_120k` | `T1CON=21 reload=F060` | `T3C1=17 T3PL=84` | `PWMSEL=04` | `T3D1L=58` | `ADM=94 ADR=00 ADPCON=10` |
| `pwm2_pc3_250k` | `T1CON=01 reload=F830` | `T3C1=17 T3PL=3F` | `PWMSEL=20` | `T3D2L=30` | `ADM=9E ADR=40 ADPCON1=80` |
| `pwm4_pc5_200k` | `T1CON=11 reload=F830` | `T3C1=16 T3PL=27` | `PWMSEL1=02` | `T3D4L=18` | `ADM=9D ADR=10 ADPCON1=40` |
| `classic_two_key_cooling_188` | `T1CON=01 reload=E0C0` | `T3C1=17 T3PL=3F` | `PWMSEL=00` | `12 + fan_mode/4` | `ADM=9C/95 ADPCON=20` |
| `classic_chrg_chrg_max_static` | `T1CON=01 reload=E0C0` | `T3C1=17 T3PL=3F` | `PWMSEL=00` | `12 + fan_mode/4` | `ADM=9C/95 ADPCON=20` |
| `classic_two_ad_key_cooling_188` | `T1CON=01 reload=E0C0` | `T3C1=17 T3PL=3F` | `PWMSEL=00` | `12 + fan_mode/4` | `ADM=9C/95/9D VREFH=00/00/03 ADPCON=20 ADPCON1=40` |
| `classic_default_two_ad_key_cooling_188` | `T1CON=01 reload=E0C0` | `T3C1=17 T3PL=3F` | `PWMSEL=00` | `12 + fan_mode/4` | `ADM=9C/95/9D VREFH=00/00/03 ADPCON=20 ADPCON1=40` |
| `classic_four_ad_key_cooling_188` | `T1CON=01 reload=E0C0` | `T3C1=17 T3PL=3F` | `PWMSEL=00` | `12 + fan_mode/4` | `ADM=9C/95/9D VREFH=00/00/03 ADPCON=20 ADPCON1=40` |
| `classic_light_fan_sync` | `T1CON=01 reload=E0C0` | `T3C1=17 T3PL=3F` | `PWMSEL=00` | `12 + fan_mode/4` | `ADM=9C/95 ADPCON=20` |
| `classic_light_on_off` | `T1CON=01 reload=E0C0` | `T3C1=17 T3PL=3F` | `PWMSEL=00` | `12 + fan_mode/4` | `ADM=9C/95/9D VREFH=00/00/03 ADPCON=20 ADPCON1=40` |
| `classic_light_on_off_flash` | `T1CON=01 reload=E0C0` | `T3C1=17 T3PL=3F` | `PWMSEL=00` | `12 + fan_mode/4` | `ADM=9C/95/9D VREFH=00/00/03 ADPCON=20 ADPCON1=40` |
| `classic_slide_switch_two_key_cooling_188` | `T1CON=01 reload=E0C0` | `T3C1=17 T3PL=3F` | `PWMSEL=00` | `12 + fan_mode/4` | `ADM=9C/95 ADPCON=20` |
| `classic_slide_switch_encoder_188` | `T1CON=01 reload=E0C0` | `T3C1=17 T3PL=3F` | `PWMSEL=00` | `12 + fan_mode/4` | `ADM=9C/95 ADPCON=20` |
| `classic_single_key_slide_resistor` | `T1CON=01 reload=FC18` | 无刷`T3PL=3F`；有刷`T3PL=93` | 无刷`PWMSEL=00`；有刷`PWMSEL=20` | 无刷7+3；有刷`98 + fan_mode/4` | `ADM=9C/95/96 VREFH=00/00/03 ADPCON=60` |
| `classic_199_no_long` | `T1CON=01 reload=E0C0` | `T3C1=17 T3PL=3F` | `PWMSEL=00` | `8 + fan_mode/4` | `ADM=9C/95 ADPCON=20` |
| `classic_icon_blink_200k` | `T1CON=01 reload=E0C0` | `T3C1=17 T3PL=4F` | `PWMSEL=00` | `11 + fan_mode/4` | `ADM=9C/95 ADPCON=20` |
| `classic_fixed_voltage_7_3` | `T1CON=01 reload=FC18` | `T3C1=17 T3PL=3F` | `PWMSEL=00` | `PWM_DATA_NOW + PWM_DR/8` | `ADM=9C/95 VREFH=00` |
| `classic_brushed_brushless_compat` | `T1CON=01 reload=FC18` | 无刷`T3PL=3F`；有刷`T3PL=93` | 无刷`PWMSEL=00`；有刷`PWMSEL=20` | 无刷7+3；有刷`98 + fan_mode/4` | `ADM=9C/95 VREFH=00` |
| `classic_brushed_fixed_duty_188` | `T1CON=01 reload=E0C0` | `T3C1=17 T3PL=93` | `PWMSEL=20` | `98 + fan_mode/4` | `ADM=9C VREFH=00` |
| `classic_two_ad_key_atomizer_188` | `T1CON=01 reload=E0C0` | 雾化`T3PL=93`；风扇`T4PL=3F` | `PWMSEL1=0A` | 风扇`12 + fan_mode/4`；雾化`WH_DUTY=15` | `ADM=9C/95/9D VREFH=00/00/03` |
| `classic_atomizer_fan_mist_icons_188` | `T1CON=01 reload=E0C0` | 雾化`T3PL=93`；风扇`T4PL=3F` | `PWMSEL1=0A` | 风扇`12 + fan_mode/4`；雾化`WH_DUTY=15` | `ADM=9C/95/9D VREFH=00/00/03` |
| `classic_two_digital_key_atomizer_cooling_188` | `T1CON=01 reload=E0C0` | 雾化`T3PL=93`；风扇`T4PL=3F` | `PWMSEL1=0A` | 风扇`12 + fan_mode/4`；雾化`WH_DUTY=15` | `ADM=9C/95 VREFH=00` |
| `classic_four_digital_key_188` | `T1CON=01 reload=E0C0` | `T3C1=17 T3PL=3F` | `PWMSEL=04` | `12 + fan_mode/4` | `ADM=9C/90 VREFH=00` |
| `classic_max_supported_single_chip_188` | `T1CON=01 reload=E0C0` | 风扇`T4PL=3F`；雾化`T3PL=93` | `PWMSEL1=0A` | 风扇`12 + fan_mode/4`；雾化`WH_DUTY=15` | `ADM=9C/97/9D VREFH=00/00/03` |

表中寄存器值省略了 `0x`，完整值以各版本的 `main.c.in` 和 `generation_report.md` 为准。

## 覆盖目的

- `T3PWM0~4` 五个 PWM 通道全部覆盖。
- `PC4 -> T3PWM0` 的合法零路由编码单独覆盖。
- `PWMSEL` 和 `PWMSEL1` 两种路由寄存器全部覆盖。
- PA、PC 两组 PWM 输出脚全部出现。
- Fosc 和 Fcpu/2 两种 Timer3 时钟源全部覆盖。
- 系统 `/1 /2 /4 /8` 全部覆盖。
- Timer1 的自动分频以及手动 `/2 /4 /8` 全部覆盖。
- ADC 的 `Fcpu`、`Fcpu/2`、`Fcpu/8`、`Fcpu/16` 全部覆盖。
- `ADPCON` 低通道和 `ADPCON1` 高通道全部覆盖。
- 1、2、4、8、16 次平均全部覆盖。
- 覆盖 AIN12 内部 `VDD/4` 电量采样、外部 AD_FAN、外部 AD_KEY 三通道轮询。
- 覆盖电量通道在 2 次废样、8 次平均后继续进行 16 组二级平均。
- 覆盖20/40/60/80/100、1/25/50/75/100和1/50/100/150/199三种档位序列。
- 覆盖100档与199档补偿区间自动缩放、关闭长按动作、200kHz/250kHz占空比曲线。
- 覆盖末位、双位和百分号三种低电/充电闪烁目标组合。
- 覆盖完整经典产品的按键、充电、制冷、显示、电量追赶、睡眠和无刷安全时序。
- 覆盖制冷/LED输入上拉有无检测、制冷按键联锁/直接随风扇、充电禁用选项，以及LED随风扇、独立开关、独立500ms闪烁三种模式。
- 覆盖CHRG/STDBY、静态CHRG/CHRG_MAX两种内部上拉双状态脚、INSERT内部下拉加CHRG内部上拉，以及无充电接口四种资源和状态归一方案。
- 覆盖PA6在运行态作为AIN13 AD_KEY、睡眠态作为输入上拉唤醒口，以及默认双键和自定义四键结果先解码再进入成熟`KEY_CHECK()`/`KEY_deal()`的完整链路。
- 覆盖AD按键350ms延迟单击、第二击执行双击、长按取消待定单击、长按单次开关动作和双击窗口阻止睡眠；多个双击按键使用独立时间资源。
- 覆盖低有效SWI_KEY在正常睡眠时输入上拉并参与唤醒、在零电睡眠时关闭上拉并移出唤醒掩码，以及拨片独占开关机和风扇故障复位。
- 覆盖ENC_A单相Port A变化中断、ENC_B方向采样、完整周期确认、独立500ms加速窗口，以及编码器不进入睡眠唤醒。
- 覆盖滑阻8次累积和、端点钳位、三档死区、连续三次确认、充电锁配置限档、单按键开关机/长按制冷，以及`SLIDER_ON`清醒高睡眠低。
- 覆盖100K:10K、2V参考、16V阈值2978的固定占空比与固定电压共用AD_FAN保护。
- 覆盖`YOUSHUA_WUSHUA=0`无刷、`1`有刷的上电检测，以及两路PWM和两套电量压降补偿。
- 覆盖纯有刷`FAN_ON`直接PWM、单套有刷电量补偿，以及不生成`PWM_FAN`、`AD_FAN`、16V升压保护和电机类型检测的资源裁剪。
- 覆盖五线188固定预置和自定义有向灯脚映射，以及百分号、制冷、充电三角标；充电角标在未满100时闪烁、100时常亮。
- 覆盖旧档位3s/电量3s页面策略，以及档位事件3s、电量预览5s、非充电常态档位、充电常态电量的独立时间资源策略。
- 覆盖Timer4独立风扇PWM、Timer3雾化PWM、共享Timer周期冲突拒绝，以及有刷PWM与雾化共用Timer3时的安全停表判断。
- 覆盖普通数字1到4键显式短按/双击/长按动作、数字键双击独立计时、长按单次开关动作和旧数字双键固定行为兼容。
- 覆盖单芯片14个可用IO全部占用时，四AD按键、双击、充电、制冷、LED、雾化、五线188、三路ADC、双Timer PWM和睡眠资源同时规划。
- 覆盖自定义188的风扇标按`fan_mode`、雾化标按`wh_mode`点亮，未映射角标不生成虚假状态代码。

## 没有表示的含义

- 不表示所有 PWM 频率都适合某一套升压电路。
- 不表示示例占空比、超压阈值和确认次数已经完成硬件标定。
- 不表示生成器已支持任意数量和用途的PWM；当前只开放风扇、有刷兼容分支和固定占空比雾化，并对全部共存组合做生成期冲突检查。
- 资源演示配置中的多 ADC 只生成采样结果，不包含电量追赶和 AD 按键业务判断。
- 完整经典产品配置虽包含按键、显示、电量、充电、制冷和睡眠业务，仍必须经过目标编译器、实板和电池曲线验证。

批量重新生成：

```powershell
powershell -ExecutionPolicy Bypass -File tools/generate_showcase.ps1
```
