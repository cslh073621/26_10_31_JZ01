# AD按键模块审查

## 当前范围

FanForge当前完整经典产品支持一个物理`AD_KEY`脚解码1到4个互斥按键：

- 旧`two_ad_keys_active_low_ranges`保持严格双键兼容，生成结果不因本次扩展改变。
- 新`ad_keys_active_low_ranges`按实际配置生成`KEY1`到`KEY4`的状态、消抖、事件、动作、清理和睡眠门槛。
- 未填写`ad_key.keys`时使用默认双键阈值：`KEY1=0..100`、`KEY2=610..810`。
- 自定义版本逐键填写阈值和短按、双击、长按动作，生成器不会根据ADC大小猜测按键功能。

## 成熟结构来源

阈值采样和输入职责边界参考：

- `HS/26_02_09_FC8/PROJECT_v1.1_YOUWUSHUA_9.5V/main.c`
- `HS/26_03_12_HSF368/PROJECT/main.c`

保留的成熟原则：

1. `ADC_Sample()`只完成通道切换、废样、8次平均和结果就绪。
2. 新`AD_KEY_VALUE`先解码成低有效按键状态。
3. `KEY_CHECK()`只消抖、计时并生成短按/长按事件。
4. `KEY_deal()`只消费事件并执行产品动作。
5. 睡眠必须等待按键释放、事件清空和唤醒稳定窗口结束。

## 生成时配置

默认双键可以省略`keys`。自定义按键声明：

```json
{"name": "KEY3", "min": 1210, "max": 1410,
 "short_action": "fan_cycle",
 "double_action": "cooling_toggle",
 "long_action": "fan_power_toggle"}
```

当前三类事件允许`fan_cycle`、`fan_power_toggle`、`fan_step_up`、`fan_step_down`、`cooling_toggle`、`light_cycle`和`none`。生成器会拒绝：

- ADC范围低于0或高于4095。
- `min > max`。
- 两个按键范围相交或共用边界。
- 重复按键名。
- 通用版本不是连续的`KEY1..KEY4`，或数量不在1到4之间。
- 新增`KEY3/KEY4`却没有配置任何动作。
- 在关闭制冷时配置制冷动作，或在关闭长按调节时配置连续长按加减档。
- 尚未实现的喷雾、RGB、PWM调光等动作名称；数字LED循环使用已审核的`light_cycle`。
- `AD_KEY`物理脚不支持ADC或Port A变化唤醒。
- 其他功能与`AD_KEY`占用同一物理脚。

## 运行时结构

每个新的平均值只消费一次：

```c
if(ad_key_ready_flag)
{
    ad_key_ready_flag = 0;
    KEY1 = 1;
    KEY2 = 1;
    KEY3 = 1;
    KEY4 = 1;
    if(AD_KEY_VALUE <= AD_KEY1_MAX)
    {
        KEY1 = 0;
    }
    else if(AD_KEY_VALUE >= AD_KEY2_MIN
            && AD_KEY_VALUE <= AD_KEY2_MAX)
    {
        KEY2 = 0;
    }
    else if(AD_KEY_VALUE >= AD_KEY3_MIN
            && AD_KEY_VALUE <= AD_KEY3_MAX)
    {
        KEY3 = 0;
    }
    else if(AD_KEY_VALUE >= AD_KEY4_MIN
            && AD_KEY_VALUE <= AD_KEY4_MAX)
    {
        KEY4 = 0;
    }
}
KEY_CHECK();
KEY_deal();
```

所有按键状态均使用HS2811原生`bit`。阈值是生成期整数常量，运行时没有除法；`KEY_CHECK()`仍沿用成熟的10ms低有效消抖。连续加减档长按保持首次约600ms、之后约60ms重复的节奏，开关类长按只触发一次。

启用双击时，第一次短按松手只置点击计数并清零独立窗口；第二次短按松手执行双击，窗口超时才执行单击。长按会取消同一按键待执行的单击，窗口未完成时睡眠资格为假。没有双击动作的旧配置不生成这些变量和语句。

## 工作态和睡眠态复用

- 工作态：`AD_KEY`为模拟输入，关闭内部上下拉。
- 睡眠态：关闭ADC后，同一脚恢复数字输入上拉并加入`WUACON`。
- 唤醒后重新执行`Init_System()`，并保留200ms稳定窗口，让ADC至少完成多轮采样后才允许再次睡眠。

规划器只允许同一个`input.ad_key.AD_KEY`所有者和角色共享ADC/GPIO脚位。名称或所有者不同仍视为冲突。

## 仍需实板验证

- 按实际分压电阻重新测量每个按键的ADC中心值和离散范围。
- 检查VDD变化、按键接触抖动和电机干扰时是否仍落在范围内。
- 检查按下唤醒、持续按住、松手短按事件和长按重复节奏。
- 检查睡眠电流以及AD_KEY内部上拉是否符合硬件设计。
- 使用HSIDE/PICC检查程序空间、数据空间、警告和校验码。
