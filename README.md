# JZ01 本地基线

- FanForge/：本地FanForge全部Git跟踪文件的逐字节副本；不复制.git、未跟踪构建输出和缓存。
- PROJECT/：从上述副本中的examples/hs2811_f824_fixed_voltage_7_3_regression复制的固件基线；后续只在此修改产品源码。
- PROJECT/main.c.in、main.h.in及生成报告/资源计划：完整保留原样，用于对照来源。
- PROJECT/main.c、main.h：可编辑源码，仅统一为CRLF并收拢连续多空行；非空白内容与原始示例一致，未改函数、寄存器或业务逻辑。
- BASELINE_MANIFEST.json：源提交、逐文件SHA256及源码行数核验记录。

本次只复制基线。参考中的2T配置、随档位变化的电压、旧板200mV补偿、按键/显示定义和16V保护值仍是参考值；尚未适配JZ01的16MHz/4T及固定9V，不可将此副本作为JZ01成品烧录。
PROJECT中的报告也是源示例报告，并非JZ01构建或板测结果。本阶段未创建HSIDE工程、未编译或板测。下一步从PROJECT/main.c、main.h做最小修改，保留成熟函数顺序与布局，不重写框架。
