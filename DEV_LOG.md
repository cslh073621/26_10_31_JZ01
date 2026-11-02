# JZ01 开发记录

## 2026-10-31：项目接入
- 用户提供仓库、本地路径和16脚示意图，要求2811实现JZ01。
- 需求意图：2脚升压PWM+10脚反馈，运行各档位均以9V为稳压目标；3脚AD按键；4/5脚接4056；8脚风速通信参数及S1-S6显示映射后补。
- 克隆结果：远程为空仓库。核对本地成熟项目、P/T手册、示例与IDE路径存在，尚未选定正式基线。
- 已询问P/T具体型号、实际时钟及分频/指令模式、分压电阻和6/7脚极性，当前未收到确认。
- 决策：先冻结需求与来源索引，按AGENTS.md第1、2条等待必要参数及外设方案审批后实现。未修改C函数、寄存器或硬件行为。
- 文件：新增HANDOFF.md和DEV_LOG.md。文档UTF-8、换行及路径核验；无源码，未编译/板测，无ROM/RAM/HEX数据。
- 工具问题：PowerShell初始管道编码损坏中文，提交前已以UTF-8重新写入并检查；Git所有权提示通过仅对指定仓库生效的命令级safe.directory处理。
- Commit：见包含本记录的提交；message：docs: initialize JZ01 requirements and handoff。


## 2026-11-02：用户参数确认及固定9V方案
- 用户确认HS16P2811、16MHz/4T、反馈100k:10k、PWM7+3，要求以FanForge无刷固定电压为基础；明确6脚制冷与7脚升压导通是成熟常规功能，不应重复提问。
- 决策：选择FanForge F824固定电压作为直接参考，不再使用泛化候选；沿用成熟函数布局和使能极性。
- 只读核验：读取FanForge配置、芯片表、emitter/planner/models以及P2811手册p29-36。仅将参考分频置4后规划通过，T1理论400计数/0xFE70；2脚PA7/T3PWM3；10脚PC1/AIN5。
- 目标换算：9V/(100k+10k)*10k=0.81818V；2V参考、4095量程、测量×2得到比较目标3350，不带入旧板200mV校准。
- 发现：FanForge预置仍按档位升压，零步进JSON被模型拒绝；后续应在JZ01的Get_Fin_Val内最小改为固定9V，不修改公共生成器。T3PL计数口径与手册文字有差异，规划频率未作实测证明。
- 文件：新增IMPLEMENTATION_PLAN.md完整事前对比表，尾部追加本记录与HANDOFF更新；无源码、寄存器变动，无编译或板测。
- 按AGENTS.md第2条，硬件/寄存器实现待用户批准具体表格后进行。Commit：见包含本记录的提交。


## 2026-11-02：先复制FanForge，再修改（用户明确要求）
- 用户纠正工作顺序：必须先将FanForge复制到JZ01文件夹，再在副本上修改，以保证编程风格一致。
- 已复制FanForge全部275个Git跟踪文件到FanForge/，源提交f2d2c76e370e329b295ba5b03a8f3d7d9855e490；排除.git和未跟踪构建/缓存。全部逐字节SHA256核验。
- 已从副本的examples/hs2811_f824_fixed_voltage_7_3_regression复制源码与报告到PROJECT/；保留原始.in，提供main.c/main.h可编辑源码，后者仅收拢多空行并保持标准CRLF，非空白内容不变。
- 源码格式核验：[{"file": "main.c", "source_lines": 1405, "copied_lines": 1403, "non_whitespace_identical": true}, {"file": "main.h", "source_lines": 6, "copied_lines": 6, "non_whitespace_identical": true}]。未更改函数、寄存器、引脚复用、时序或产品行为。
- 本阶段为可检索的复制基线；参考2T、随档位电压与旧板保护/显示参数尚未适配JZ01，不可作为JZ01成品烧录。未编译/板测，无新ROM/RAM或HEX结果。
- 后续修改以PROJECT/main.c、main.h为起点，禁止脱离该副本另写框架；原始对照保留在FanForge及PROJECT/*.in。
- 清单：BASELINE_MANIFEST.json；Commit：见包含本记录的提交。
