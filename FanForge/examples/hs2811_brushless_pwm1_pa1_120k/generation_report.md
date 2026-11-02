# FanForge generation report: HS2811_BRUSHLESS_PWM1_PA1_120K

## Scope

- Generator version: `0.31.2`
- Status: initial reviewed hardware-resource demo
- Production-ready: no
- Core template: fixed internal `hs2811_fan_core.c.in`
- Source previews: `main.c.in` and `main.h.in`

## Resolved pins

- `AD_FAN`: physical pin 11 -> `PC0`
- `FAN_ON`: physical pin 7 -> `PC4`
- `PWM_FAN`: physical pin 14 -> `PA1`

## Timer1

- Fcpu: `16000000 Hz`
- Required HSIDE/programmer system-divider setting: `/1`
- Runtime code selects high-speed mode with `OSCM = 0x00`; the system divider is not an `OSCM` field.
- Prescaler: `4`
- Reload: `0xF060`
- `T1CON`: `0x21`
- Actual interrupt: `1000.000000 us`
- `time_1ms_flag` is produced directly by each T1 interrupt.

## Generated time resources

- `1ms`: flag=`time_1ms_flag`, counter=`-`, parent=`-`, ticks=`1`, internal=`false`
- `10ms`: flag=`time_10ms_flag`, counter=`time_10ms_cnt`, parent=`1ms`, ticks=`10`, internal=`false`
- `100ms`: flag=`time_100ms_flag`, counter=`time_100ms_cnt`, parent=`10ms`, ticks=`10`, internal=`false`

## Fan PWM

- Route: `PA1` -> `T3PWM1`
- Route register: `PWMSEL = 0x04`
- T3 clock source: `fosc`
- T3 prescaler: `1`
- Period register: `132`
- Target: `120000 Hz`
- Actual: `120300.751880 Hz`
- Error: `0.250627%`

## AD_FAN overvoltage protection

- Physical limit: `16000mV`, divider `100000:10000`.
- Single AD_FAN reference: `2v`, generated threshold: `2978`, confirmations: `13`.
- Fixed-voltage regulation and the 16V guard reuse this same completed AD_FAN average.
- The software check is supplemental; boost hardware must still provide fast overvoltage protection.

## ADC

- Channel count: `1`
- Sample period: `1000us`
- Per-channel scan cycle: `18000us`
- One complete first-stage scan: `18 ms`
- Discard samples: `2`
- Average samples: `16`
- Fixed-voltage high-rate pipeline: disabled.
- Conversion wait limit: `250` loops
- Maximum first-stage u16 accumulation: `65520`
- `AD_FAN_VALUE`: `PC0 / AIN4`, ADM=`0x94`, VREFH=`0x00`, ADR=`0x00`, second average=`1`, result mode=`average`, result update=`18ms`, ready flags=`ad_fan_ready_flag`

## Deliberate limits

- AD-key and battery options currently generate acquisition results only; product behavior is not implemented.
- No key event, encoder, slide resistor behavior, display, charge, or cooling module.
- Sleep is disabled by the generated eligibility expression.
- The generated fan defaults off and has no product input path to turn it on.
- These limits prevent the initial generator from pretending to produce a complete product.
