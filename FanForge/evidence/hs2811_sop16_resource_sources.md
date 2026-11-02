# HS16P2811 SOP16 资源依据

初版芯片能力表不是从项目代码反推，而是按以下资料核对。

## 物理脚位

来源：`H:\WorkSpace\HS\资料\HS16P2811系列用户手册V2.02\HS16P2811系列用户手册V2.02_06.png`

SOP16：

```text
1 VDD   2 PA7   3 PA6   4 PA5   5 PA4
6 PC5   7 PC4   8 PC3   9 PC2  10 PC1
11 PC0 12 PA3  13 PA2  14 PA1  15 PA0  16 GND
```

## ADC

外部通道：

```text
PA0 AIN0   PA1 AIN1   PA2 AIN2   PA3 AIN3
PC0 AIN4   PC1 AIN5   PC2 AIN6   PC3 AIN7
PC4 AIN8   PC5 AIN9   PA4 AIN10  PA5 AIN11
PA6 AIN13  PA7 AIN14
```

成熟 HS2811 头文件中的 ADC 时钟宏：

```c
ADCKS_Fcpu_16 -> ADR = 0x00
ADCKS_Fcpu_8  -> ADR = 0x10
ADCKS_Fcpu    -> ADR = 0x40
ADCKS_Fcpu_2  -> ADR = 0x50
AD_VREFH_VDD  -> VREFH = 0x03
```

参考头文件之一：
`H:\WorkSpace\HS\25_12_23_1029\PROJECT_7V\main.h`

## Timer3 PWM 路由

手册中的路由关系：

```text
T3PWM0: PC4 / PA0 / PC1 / PA4
T3PWM1: none / PA1 / PC2 / PA5
T3PWM2: none / PA2 / PC3 / PA6
T3PWM3: none / PA3 / PC4 / PA7
T3PWM4: none / PC0 / PC5 / PA4
```

`T3PWM0..3` 使用 `PWMSEL`，`T3PWM4` 使用 `PWMSEL1`。

Timer3 分频编码：

```text
111 /1    110 /2    101 /4    100 /8
011 /16   010 /32   001 /64   000 /128
```

`T3CKS0=1` 选择 Fosc，16MHz、`T3PL=63` 时周期计数为 64，PWM 为 250kHz。

## Timer1

来源：`H:\WorkSpace\HS\资料\HS16P2811系列用户手册V2.02\HS16P2811系列用户手册V2.02_29.png`

Timer1 内部时钟使用 Fcpu，分频编码：

```text
00 /1
01 /2
10 /4
11 /8
```

系统分频是工程/烧录配置。`OSCM=0x00` 只负责选择高速模式，不能代替系统分频配置。
