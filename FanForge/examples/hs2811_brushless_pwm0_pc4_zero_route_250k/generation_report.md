# FanForge generation report: HS2811_BRUSHLESS_PWM0_PC4_ZERO_ROUTE_250K

## Scope

- Generator version: `0.31.2`
- Status: initial reviewed hardware-resource demo
- Production-ready: no
- Core template: fixed internal `hs2811_fan_core.c.in`
- Source previews: `main.c.in` and `main.h.in`

## Resolved pins

- `AD_FAN`: physical pin 10 -> `PC1`
- `FAN_ON`: physical pin 13 -> `PA2`
- `PWM_FAN`: physical pin 7 -> `PC4`

## Timer1

- Fcpu: `8000000 Hz`
- Required HSIDE/programmer system-divider setting: `/2`
- Runtime code selects high-speed mode with `OSCM = 0x00`; the system divider is not an `OSCM` field.
- Prescaler: `1`
- Reload: `0xE0C0`
- `T1CON`: `0x01`
- Actual interrupt: `1000.000000 us`
- `time_1ms_flag` is produced directly by each T1 interrupt.

## Generated time resources

- `1ms`: flag=`time_1ms_flag`, counter=`-`, parent=`-`, ticks=`1`, internal=`false`
- `10ms`: flag=`time_10ms_flag`, counter=`time_10ms_cnt`, parent=`1ms`, ticks=`10`, internal=`false`
- `100ms`: flag=`time_100ms_flag`, counter=`time_100ms_cnt`, parent=`10ms`, ticks=`10`, internal=`false`

## Fan PWM

- Route: `PC4` -> `T3PWM0`
- Route register: `PWMSEL = 0x00`
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
- Per-channel scan cycle: `10000us`
- One complete first-stage scan: `10 ms`
- Discard samples: `2`
- Average samples: `8`
- Fixed-voltage high-rate pipeline: disabled.
- Conversion wait limit: `128` loops
- Maximum first-stage u16 accumulation: `32760`
- `AD_FAN_VALUE`: `PC1 / AIN5`, ADM=`0x95`, VREFH=`0x00`, ADR=`0x10`, second average=`1`, result mode=`average`, result update=`10ms`, ready flags=`ad_fan_ready_flag`

## Deliberate limits

- AD-key and battery options currently generate acquisition results only; product behavior is not implemented.
- No key event, encoder, slide resistor behavior, display, charge, or cooling module.
- Sleep is disabled by the generated eligibility expression.
- The generated fan defaults off and has no product input path to turn it on.
- These limits prevent the initial generator from pretending to produce a complete product.
