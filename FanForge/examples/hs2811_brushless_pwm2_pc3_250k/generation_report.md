# FanForge generation report: HS2811_BRUSHLESS_PWM2_PC3_250K

## Scope

- Generator version: `0.31.2`
- Status: initial reviewed hardware-resource demo
- Production-ready: no
- Core template: fixed internal `hs2811_fan_core.c.in`
- Source previews: `main.c.in` and `main.h.in`

## Resolved pins

- `AD_FAN`: physical pin 2 -> `PA7`
- `FAN_ON`: physical pin 7 -> `PC4`
- `PWM_FAN`: physical pin 8 -> `PC3`

## Timer1

- Fcpu: `2000000 Hz`
- Required HSIDE/programmer system-divider setting: `/8`
- Runtime code selects high-speed mode with `OSCM = 0x00`; the system divider is not an `OSCM` field.
- Prescaler: `1`
- Reload: `0xF830`
- `T1CON`: `0x01`
- Actual interrupt: `1000.000000 us`
- `time_1ms_flag` is produced directly by each T1 interrupt.

## Generated time resources

- `1ms`: flag=`time_1ms_flag`, counter=`-`, parent=`-`, ticks=`1`, internal=`false`
- `10ms`: flag=`time_10ms_flag`, counter=`time_10ms_cnt`, parent=`1ms`, ticks=`10`, internal=`false`
- `100ms`: flag=`time_100ms_flag`, counter=`time_100ms_cnt`, parent=`10ms`, ticks=`10`, internal=`false`

## Fan PWM

- Route: `PC3` -> `T3PWM2`
- Route register: `PWMSEL = 0x20`
- T3 clock source: `fosc`
- T3 prescaler: `1`
- Period register: `63`
- Target: `250000 Hz`
- Actual: `250000.000000 Hz`
- Error: `0.000000%`

## AD_FAN overvoltage protection

- Physical limit: `16000mV`, divider `100000:10000`.
- Single AD_FAN reference: `2v`, generated threshold: `2978`, confirmations: `13`.
- Fixed-voltage regulation and the 16V guard reuse this same completed AD_FAN average.
- The software check is supplemental; boost hardware must still provide fast overvoltage protection.

## ADC

- Channel count: `1`
- Sample period: `1000us`
- Per-channel scan cycle: `4000us`
- One complete first-stage scan: `4 ms`
- Discard samples: `3`
- Average samples: `1`
- Fixed-voltage high-rate pipeline: disabled.
- Conversion wait limit: `50` loops
- Maximum first-stage u16 accumulation: `4095`
- `AD_FAN_VALUE`: `PA7 / AIN14`, ADM=`0x9E`, VREFH=`0x00`, ADR=`0x40`, second average=`1`, result mode=`average`, result update=`4ms`, ready flags=`ad_fan_ready_flag`

## Deliberate limits

- AD-key and battery options currently generate acquisition results only; product behavior is not implemented.
- No key event, encoder, slide resistor behavior, display, charge, or cooling module.
- Sleep is disabled by the generated eligibility expression.
- The generated fan defaults off and has no product input path to turn it on.
- These limits prevent the initial generator from pretending to produce a complete product.
