# HS2811风扇功能扫描

- 扫描根目录：`H:\WorkSpace\HS`
- 可读HS2811 `main.c`：`86`
- 涉及项目目录：`54`
- 排除或不可读：`566`

统计用于确定扩展优先级，不代表出现次数最多的文件可以直接作为量产模板。
参考候选按项目日期和正式PROJECT路径优先，资料、临时、测试和备份路径会降权。

## 功能概览

| 功能 | 文件 | 项目 | 最新优先参考 |
| --- | ---: | ---: | --- |
| `battery_timed_chase` | 80 | 49 | `26_07_28_K827\PROJECT\main.c` |
| `charge_chrg_stdby` | 16 | 14 | `26_07_28_K827\PROJECT\main.c` |
| `charge_insert_pin` | 37 | 28 | `26_07_08_Y30\PROJECT\main.c` |
| `charge_chrg_max` | 48 | 23 | `26_05_11_WZ02\PROJECT\main.c` |
| `cooling` | 21 | 15 | `26_07_28_K827\PROJECT\main.c` |
| `display_188` | 79 | 49 | `26_07_28_K827\PROJECT\main.c` |
| `input_digital_key` | 75 | 45 | `26_07_28_K827\PROJECT\main.c` |
| `input_ad_key` | 19 | 13 | `26_07_28_K827\PROJECT\main.c` |
| `input_encoder` | 57 | 29 | `26_06_16_K75\PROJECT_MAIN_电解电容\main.c` |
| `input_slide_resistor` | 6 | 4 | `26_07_06_S056\PROJECT\main.c` |
| `input_slide_switch` | 12 | 8 | `26_07_06_S056\PROJECT\main.c` |
| `light_output` | 6 | 5 | `26_07_21_F824\project\main.c` |
| `mist_pwm` | 4 | 4 | `26_07_28_K827\PROJECT\main.c` |
| `rgb_ws2812` | 3 | 3 | `26_07_15_F22\PROJECT\main.c` |
| `motor_type_detection` | 53 | 33 | `26_07_28_K827\PROJECT\main.c` |
| `motor_fixed_voltage` | 37 | 25 | `26_07_08_Y30\PROJECT\main.c` |
| `motor_fixed_duty` | 35 | 21 | `26_07_28_K827\PROJECT\main.c` |
| `ad_fan_overvoltage` | 37 | 23 | `26_07_28_K827\PROJECT\main.c` |
| `dual_chip_communication` | 5 | 3 | `26_07_02_F5\PROJECT_MAIN\main.c` |
| `stepper_swing` | 2 | 1 | `26_06_16_K75\PROJECT_SUB\main.c` |

## 使用限制

- 标签来自源码结构和关键符号，不能代替逐函数审查。
- 同一个项目的多个版本会分别计入文件数量，但项目数量会去重。
- 加密、损坏、非C源码及非HS2811项目不会参与功能占比。
- 下一功能进入生成器前，必须重新打开候选项目核对硬件原理、标志位极性和完整调用链。
