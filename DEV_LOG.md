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


## 2026-11-02：纠正复制范围
- 用户指出不应复制整个FanForge。正确意图是仅复制其中的无刷固定电压固件，作为JZ01修改基线并保持编程风格。
- 已移除误复制的FanForge/整个生成器副本以及PROJECT/中的.in对照、参考生成报告、验收清单和资源计划；仅保留PROJECT/main.c、main.h，压缩BASELINE_MANIFEST.json为简短来源与源码SHA256记录。
- PROJECT/main.c、main.h与清理前逐字节一致；无函数、寄存器、时序或行为改动。原始复制记录仍可通过c177a9a追溯。
- README及本交接/开发记录已同步。未进行编译/板测，未新增HEX或ROM/RAM结论。
- Commit：见包含本记录的提交。


## 2026-11-02：建立原生工程并开始JZ01适配
- 用户指出缺少项目工程并要求“项目开始”，本次落实先前已披露的寄存器/结构方案；随后明确“按键先写好驱动，具体功能先空置”，已取消按键风扇/制冷/调档动作。
- 工程：从成熟HSIDE项目结构建立PROJECT/JZ01.hsprj2，包含main.c/main.h，芯片HS16P2811；按IDE configuration/chips/hs16p2811.chip核对config-index=1、offset=2、width=3的系统分频值0=4'clock。该核验仅用于匹配用户已确认16MHz/4T。
- main.c：Get_Fin_Val去掉档位电压曲线，固定目标3350（9V、100k:10k、2V参考、均值×2）；保留AD_fan_deal粗细调/进借位，2脚PA7/T3PWM3及原PWM配置不换外设，T1重载改0xFE70匹配4MHz。
- ADC_Sample保留丢4次+96次/12组均值及主循环ADC位置；增加连续超时3次关升压和故障标志，超时清部分累加/旧反馈标志/too_big_cnt，成功采样复位超时计数。保护初版10V原始值1861、连续13个有效反馈均值确认，沿用关闭/非运行/初始化清零路径。
- KEY_CHECK直接复用成熟第二键逻辑扩展第三键；0Ω/6.8k/20k按VDD参考识别（理论0/1658/2730），KEY_deal只清事件。三键均纳入睡眠待处理条件；未定义同时按下组合，不编造产品动作。
- smg_close/smg_188_scan：映射未给，六显示引脚改输入占位；8脚PC3初始化低电平，不分配/输出通信PWM。GPIO及睡眠保留CHRG/STDBY上拉，AD键有外部10k，不额外加入内部上拉。
- 保留制冷可选检测、FAN_ON→PWM及PWM→FAN_ON成熟调用顺序、充电检测和电量追赶结构。充电逻辑用charge_on_flag明确活动充电分支；time_flag_deal消费已有1ms标志，清除未使用标志告警。
- 构建：首次原生编译发现副本头文件缺_NOP宏和2个未用标志告警；补成熟_NOP汇编宏并落实标志消费后，新鲜原生构建0错误/0警告。ROM=1732/2048 words，RAM=67/128 bytes。
- HEX SHA256：3021c7572f665f21455e15257cc3a48bbdbddc03e47b9bf552632e376aecab8b。源码/头文件哈希及配置见build_result.json；PROJECT/JZ01.ccs和JZ01.hs.hex已产出。
- verify.py通过：固定9V、344种粗细占空组合、ADC累加范围和故障/确认路径、三键识别区间及驱动/空动作、显示/通信占位、4T工程及源/HEX哈希。它是源码和算术回归，不是MCU运行或板测。
- 新增build.py可重复原生构建，verify.py及README同步；格式检查通过，无CRCRLF、多空行膨胀。原生工程、函数改动、产物和文档同一次提交。
- 限制：尚未GUI重建/板测；9V实际稳压、ADC/时钟误差、100us ISR实际节拍、PWM计数口径、保护响应和电量标定待验证；恒压下仅凭AD_FAN电压不能保证识别所有电机缺失，不宣称已验证此能力。
- Commit：见包含本记录的提交。
