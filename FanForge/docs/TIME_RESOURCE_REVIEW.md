# 时间资源模块审查

## 目标

功能模块只声明自己需要的时间资源，不能直接向模板拼接 `bit time_xxx_flag`、`u8 time_xxx_cnt` 或 `time_flag_deal()` 分支。

时间请求包含：

- 所属模块和用途。
- 周期，单位为整数毫秒。
- 相位语义。
- 复位语义。

生成器统一完成请求合并、命名、父时基选择、计数器声明、ISR 累加和 `time_flag_deal()` 分层代码。

## 合并规则

只有周期、相位和复位语义全部相同时才共享一个标志位和计数器。

当前核心请求：

```text
ADC调度：1ms / system / continuous
主循环：10ms / system / continuous
睡眠检查：100ms / system / continuous
无刷风扇处理：10ms / system / continuous
```

主循环和无刷风扇处理共享 `time_10ms_flag`，因为三项语义完全相同。

如果按键双击窗口和低电闪烁都需要 200ms，但相位或复位语义不同，生成器会分别生成：

```c
bit key_window_200ms_flag;
bit low_flash_200ms_flag;
u8 key_window_200ms_cnt;
u8 low_flash_200ms_cnt;
```

## 分层规则

当前基础中断固定为 1ms。父时基按成熟项目选择：

```text
短周期        <- 1ms
常规周期      <- 10ms
秒级周期      <- 500ms
小时级周期    <- 1min
```

每一层必须整除目标周期，且单层计数次数不得超过 255。当前审核范围为 1ms 到 4h。

例如请求 3s、5s 和 4h 时：

```c
if(time_500ms_cnt > 49)
{
    time_500ms_cnt = 0;
    time_3s_cnt++;
    time_5s_cnt++;
    time_1min_cnt++;
}

if(time_3s_cnt > 5)
{
    time_3s_cnt = 0;
    time_3s_flag = 1;
}

if(time_1min_cnt > 119)
{
    time_1min_cnt = 0;
    time_4h_cnt++;
}

if(time_4h_cnt > 239)
{
    time_4h_cnt = 0;
    time_4h_flag = 1;
}
```

`500ms` 和 `1min` 如果只用于派生子周期，只生成计数器，不生成无用途标志位。

## 当前最小项目结果

当前最小无刷项目只需要 1ms、10ms 和 100ms，因此生成：

```c
bit time_1ms_flag;
bit time_10ms_flag;
bit time_100ms_flag;

u8 time_10ms_cnt;
u8 time_100ms_cnt;
```

原模板中无实际用途的 `time_500ms_flag/time_500ms_cnt` 已去除。

## 当前边界

- T1 基础中断仍固定为直接 1ms。
- 模块负责在自身业务函数中使用生成器返回的计数器名称完成事件复位。
- 当前只实现资源规划和分层代码，不自动发明按键、显示或电量的启动/清零条件。
- 非整数毫秒、超过 4h 或无法用审核层级和 `u8` 安全派生的请求会停止生成。
- 高频数码管扫描、7+3 PWM、单线通信和步进电机需要亚毫秒时基，属于后续单独审核范围。
