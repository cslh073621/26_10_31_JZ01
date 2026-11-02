# FanForge generation report: HS2811_CLASSIC_TWO_KEY_NO_CHARGING_188

## Scope

- Generator version: `0.31.2`
- Status: complete classic profile; compiler and bench validation required
- Production-ready: no
- Core template: fixed internal `hs2811_fan_core.c.in`
- Source previews: `main.c.in` and `main.h.in`

## Resolved pins

- `AD_FAN`: physical pin 10 -> `PC1`
- `COOL_EN`: physical pin 6 -> `PC5`
- `FAN_ON`: physical pin 8 -> `PC3`
- `IO_LED_1`: physical pin 15 -> `PA0`
- `IO_LED_2`: physical pin 14 -> `PA1`
- `IO_LED_3`: physical pin 13 -> `PA2`
- `IO_LED_4`: physical pin 12 -> `PA3`
- `IO_LED_5`: physical pin 11 -> `PC0`
- `KEY1`: physical pin 2 -> `PA7`
- `KEY2`: physical pin 3 -> `PA6`
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
- `500ms`: flag=`time_500ms_flag`, counter=`time_500ms_cnt`, parent=`10ms`, ticks=`50`, internal=`false`
- `3000ms`: flag=`page_3s_3s_flag`, counter=`page_3s_3s_cnt`, parent=`500ms`, ticks=`6`, internal=`false`
- `5000ms`: flag=`low_discharge_5s_flag`, counter=`low_discharge_5s_cnt`, parent=`500ms`, ticks=`10`, internal=`false`
- `20000ms`: flag=`discharge_20s_flag`, counter=`discharge_20s_cnt`, parent=`500ms`, ticks=`40`, internal=`false`

## Fan PWM

- Route: `PC4` -> `T3PWM0`
- Route register: `PWMSEL = 0x00`
- T3 clock source: `fosc`
- T3 prescaler: `1`
- Period register: `63`
- Target: `250000 Hz`
- Actual: `250000.000000 Hz`
- Error: `0.000000%`
- Duty curve: `12 + fan_mode / 4` counts

## AD_FAN overvoltage protection

- Physical limit: `16000mV`, divider `100000:10000`.
- Single AD_FAN reference: `2v`, generated threshold: `2978`, confirmations: `13`.
- Fixed-voltage regulation and the 16V guard reuse this same completed AD_FAN average.
- The software check is supplemental; boost hardware must still provide fast overvoltage protection.

## ADC

- Channel count: `2`
- Sample period: `1000us`
- Per-channel scan cycle: `20000us`
- One complete first-stage scan: `20 ms`
- Discard samples: `2`
- Average samples: `8`
- Fixed-voltage high-rate pipeline: disabled.
- Conversion wait limit: `50` loops
- Maximum first-stage u16 accumulation: `32760`
- `ADC_BAT_VALUE`: `AIN12_VDD_DIV4 / AIN12`, ADM=`0x9C`, VREFH=`0x00`, ADR=`0x40`, second average=`16`, result mode=`average`, result update=`320ms`, ready flags=`adc_bat_ready_flag`
- `AD_FAN_VALUE`: `PC1 / AIN5`, ADM=`0x95`, VREFH=`0x00`, ADR=`0x40`, second average=`1`, result mode=`average`, result update=`20ms`, ready flags=`ad_fan_ready_flag`

## Classic product behavior

- Input kind: `two_digital_keys_active_low`
- Short-press gear sequence: `20 -> 40 -> 60 -> 80 -> 100 -> 0`
- Long continuous adjustment: `true`
- Charging maximum gear: `60`
- Charging interface enabled/kind: `false` / `none`
- Display hardware/pins/drive: `standard_188_cooling_percent_style_a` / `5` / `output_high_input_off`
- Display mapped signals: `18`
- Display policy: `gear_3s_battery_3s_gear`
- Display behavior profile: `gear_3s_battery_3s_gear`
- Gear event/battery preview periods: `3000ms` / `3000ms`
- Normal/charging idle pages: `gear` / `battery`
- Low/charge blink targets: `both_digits` / `last_digit`
- Cooling/sleep enabled: `true` / `true`
- Cooling detection/control/charging policy: `true` / `toggle_while_fan_on` / `false`
- Light enabled/detection/mode: `false` / `false` / `fan_sync`
- Atomizer enabled/frequency/duty/dependency/charging: `false` / `108000Hz` / `10%` / `fan_required` / `true`

## Deliberate limits

- This profile generates complete classic product behavior, but it is not declared production-ready without the target compiler and bench validation.
- Brushed/brushless auto-detection is not part of this fixed-motor profile.
- Mist/atomizer control is not part of this profile.
- RGB, PWM light and communication modules are not part of this profile.
- Active-low slide-switch power control is not part of this profile.
- Battery thresholds, load compensation and chase periods are explicit product calibration parameters and still require the selected cell/load discharge curve.
