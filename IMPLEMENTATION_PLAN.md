# JZ01 固定9V实施方案（待批准）

日期：2026-11-02。阶段：只完成方案及只读资源核验，尚未生成或烧录固件。

## 本次用户确认（覆盖交接文档旧的待确认项）
- HS16P2811，实际时钟16MHz/4T，Fcpu=4MHz。
- 反馈上臂100kΩ、下臂10kΩ，升压输出固定9V，采用PWM 7+3。
- 采用FanForge无刷固定电压基础；6脚负责制冷开关，7脚负责电机升压电路导通，按成熟高有效COOL_EN/FAN_ON逻辑处理，无需再次向用户询问常规职能。
- 8脚档位通信及S1-S6映射仍按首次要求留空。

## 实施前对比表
当前JZ01为空固件工程，故以用户指定的FanForge F824固定电压配置作为比较基线。

| 项目 | 参考配置/当前状态 | JZ01拟用配置 | 理由及证据 | 引脚/复用、寄存器及逻辑 | 行为时序影响、风险与回滚 |
| --- | --- | --- | --- | --- | --- |
| 时钟 | F824预置16MHz/2分频 | 16MHz/4T，系统分频4 | 用户确认；planner按Fcpu=Fosc/divider规划 | 工程烧录配置与T1/ADC参数需匹配，不用OSCM代替系统分频 | 不照搬2T重载；回滚至本方案前提交 |
| 升压PWM | PWM_FAN在2脚，250kHz规划，7+3 | 保留2脚PA7→T3PWM3、Fosc/1、7+3 | FanForge F824配置、芯片表；P2811手册p31-36 | T3C1=0x17、PWMSEL通道3选择11、T3D3L/H、T3PWM3EN；规划T3PL=63、T3PH=0 | 不换外设/通道；250kHz为FanForge规划值，手册p34周期文字与规划器+1口径存在差异，最终频率须核验，不能当成已实测；回滚PWM初始化及ISR |
| 7+3节拍 | 100us相位推进、8相位 | 保留100us及800us完整8相位 | emitter._high_rate_motor_isr | T1内部4MHz/1，400计数，理论重载0xFE70、T1CON=0x01；10拍派生1ms | 理论值未计ISR重载开销，须波形验证；不更换ISR架构；回滚T1及ISR |
| 反馈 | AD_FAN在10脚，2V参考 | PC1/AIN5，100k:10k，2V参考 | 用户分压；FanForge芯片表、models._voltage_target_adc | ADPCON bit5、VREFH=0、ADC_Sample、AD_FAN_VALUE | 9V对应0.81818V，理想12位原始ADC约1675；转换/校准误差留待板测；回滚ADC配置 |
| 目标 | 1656+档位步进，最大3460；附200mV校准参数 | 所有运行档位比较目标3350，测量值为原始均值×2；不添加200mV补偿 | 按FanForge4095量程公式计算；用户要求档位不改变电压 | Get_Fin_Val改为固定目标，保留成熟粗调/细调与进位/借位 | 零步进被当前生成器校验拒绝，不能仅改JSON宣称完成；在JZ01成熟函数内做最小修改，不改FanForge公共架构；回滚目标比较函数 |
| ADC调度 | 固定电压高频采样，主循环转换 | 保留100us请求；每通道100次，丢4次，96次分12组平均，每新均值消费一次 | planner高频常量及emitter新值标志 | ADC在主循环，ISR只置标志/更新相位；参考含电池、反馈、按键3通道 | 规划3通道一轮30ms；主循环丢标志可拉长，不能把100us请求等同100us闭环响应；回滚ADC调度 |
| 使能/制冷 | FAN_ON和COOL_EN置1有效 | 7脚PC4=FAN_ON，6脚PC5=COOL_EN；保留约10ms启停顺序 | F824引脚配置及成熟fan_deal路径 | 启动先FAN_ON，再升压PWM；关机先停PWM，再撤FAN_ON；制冷沿用成熟函数职责 | 检查调用周期落实间隔；不新增状态机或helper；回滚fan_deal/制冷逻辑 |
| 保护 | 实际反馈、连续13个超限均值确认；参考16V阈值 | 保留真实采样/确认/清零路径；不直接采用16V产品阈值，初版提议10V超限值供板测校验 | 13次来自FanForge；10V仅为9V目标的工程初值，非硬件耐压证明 | AD_FAN_TOO_HIGH、too_big_cnt、fan_error_flag；ADC初始化/停机/非活动/异常后清零 | 满足有效运行采样才累加；无负载检测能力需电路/板测验证，不能仅凭此宣称检出所有电机缺失；回滚保护参数及相关逻辑 |
| 电机通信 | 参考没有JZ01独立通信 | 8脚PC3暂不发档位波形 | 用户要求暂时空置；手册p31的T3多路共周期 | 暂不启用PC3的T3PWM2或T4PWM，不让后续协议改变升压T3周期 | 后补协议时独立核验资源；本阶段不分配第二路PWM；回滚点为8脚未启用状态 |
| 显示与输入 | 参考2个AD键及既定188映射 | 保留3脚PA6/AIN13输入位置；S1-S6映射待补，不点亮未核对段灯 | 用户示意图；FanForge芯片表 | 4脚PA5=CHRG，5脚PA4=STDBY；S1..S6=PA0,PA1,PA2,PA3,PC0,PC2 | 不照搬参考的按键数量、档位数量和段灯表；回滚相关输入/显示配置 |

## 核验来源
- H:/WorkSpace/HS/FanForge/configs/hs2811_f824_fixed_voltage_7_3_regression.json
- H:/WorkSpace/HS/FanForge/fanforge/chips/hs2811_sop16.json
- H:/WorkSpace/HS/FanForge/fanforge/emitter.py：_high_rate_motor_isr、_fixed_voltage_compare、_fan_deal_fixed_voltage。
- H:/WorkSpace/HS/FanForge/fanforge/planner.py：_plan_timer、build_generation_plan与高频ADC常量。
- H:/WorkSpace/HS/FanForge/fanforge/models.py：_voltage_target_adc、from_dict的零步进限制。
- H:/WorkSpace/HS/资料/HS16P2811系列用户手册V2.02.pdf：已读取p29-36，验证T1源/分频、T3共享周期、PWM通道3的PA7路由。

## 本阶段验证结果与后续交付
- 只读运行FanForge规划器：保持参考电压曲线，仅将system_divider置4，资源规划通过；得到T1=400计数、PA7/T3PWM3、PC1/AIN5和PA6/AIN13。该检查不等于固定9V固件已生成。
- 单独计算9V目标比较单位=3350；零步进配置试探被模型拒绝，已据此制定最小函数改动方案。
- 当前无JZ01源码、构建或HEX，ROM/RAM/SHA256及0E0W不适用。
- 本方案批准后才能写入硬件/寄存器实现；编译通过后仍需板测9V误差、纹波、各负载瞬态及故障保护。
- 本阶段Commit：见包含本记录的提交。


## 执行顺序补充（2026-11-02）
用户要求先复制FanForge，再修改。现已落地FanForge/完整跟踪文件快照及PROJECT/固定电压源码副本。后续方案修改以PROJECT/main.c、main.h为基础，保留原函数结构和风格；本次复制不表示已完成JZ01硬件适配。


## 复制范围纠正（2026-11-02）
仅保留PROJECT/main.c、main.h作为FanForge无刷固定电压固件基线；已移除整个生成器副本及多余生成报告。来源见BASELINE_MANIFEST.json，后续直接修改这两个源码文件。


## 2026-11-02 实施结果
用户要求项目开始后已建立HSIDE工程并落实上述固定9V/4T方案。随后用户明确按键只完成驱动、不绑定具体动作，已据此实现三键事件及空KEY_deal。原生构建0E0W、ROM1732/2048、RAM67/128；8脚和S1-S6映射仍占位，实际板测尚未完成。实际函数差异、保护边界及SHA256以DEV_LOG和build_result.json为准。
