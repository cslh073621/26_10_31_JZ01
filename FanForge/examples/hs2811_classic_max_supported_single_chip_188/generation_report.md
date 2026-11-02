# FanForge generation report: HS2811_CLASSIC_MAX_SUPPORTED_SINGLE_CHIP_188

## Scope

- Generator version: `0.31.2`
- Status: complete classic profile; compiler and bench validation required
- Production-ready: no
- Core template: fixed internal `hs2811_fan_core.c.in`
- Source previews: `main.c.in` and `main.h.in`

## Resolved pins

- `AD_FAN`: physical pin 8 -> `PC3`
- `AD_KEY`: physical pin 3 -> `PA6`
- `CHRG`: physical pin 4 -> `PA5`
- `COOL_EN`: physical pin 10 -> `PC1`
- `FAN_ON`: physical pin 7 -> `PC4`
- `IO_LED_1`: physical pin 15 -> `PA0`
- `IO_LED_2`: physical pin 14 -> `PA1`
- `IO_LED_3`: physical pin 13 -> `PA2`
- `IO_LED_4`: physical pin 12 -> `PA3`
- `IO_LED_5`: physical pin 11 -> `PC0`
- `LED_ON`: physical pin 9 -> `PC2`
- `PWM_FAN`: physical pin 2 -> `PA7`
- `PWM_WH`: physical pin 6 -> `PC5`
- `STDBY`: physical pin 5 -> `PA4`

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
- `350ms`: flag=`double_click_window_350ms_flag`, counter=`double_click_window_350ms_cnt`, parent=`10ms`, ticks=`35`, internal=`false`
- `500ms`: flag=`time_500ms_flag`, counter=`time_500ms_cnt`, parent=`10ms`, ticks=`50`, internal=`false`
- `3000ms`: flag=`battery_preview_3s_flag`, counter=`battery_preview_3s_cnt`, parent=`500ms`, ticks=`6`, internal=`false`
- `3000ms`: flag=`gear_event_3s_flag`, counter=`gear_event_3s_cnt`, parent=`500ms`, ticks=`6`, internal=`false`
- `5000ms`: flag=`low_discharge_5s_flag`, counter=`low_discharge_5s_cnt`, parent=`500ms`, ticks=`10`, internal=`false`
- `20000ms`: flag=`discharge_20s_flag`, counter=`discharge_20s_cnt`, parent=`500ms`, ticks=`40`, internal=`false`
- `25000ms`: flag=`charge_full_25s_flag`, counter=`charge_full_25s_cnt`, parent=`500ms`, ticks=`50`, internal=`false`
- `90000ms`: flag=`charge_active_90s_flag`, counter=`charge_active_90s_cnt`, parent=`500ms`, ticks=`180`, internal=`false`

## Fan PWM

- Route: `PA7` -> `T4PWM`
- Route register: `PWMSEL1 = 0x08`
- T4 clock source: `fosc`
- T4 prescaler: `1`
- Period register: `63`
- Target: `250000 Hz`
- Actual: `250000.000000 Hz`
- Error: `0.000000%`
- Duty curve: `12 + fan_mode / 4` counts
- Auxiliary PWM: `PWM_WH` on `PC5` -> `T3PWM4`, target `108000 Hz`, actual `108108.108108 Hz`.

## AD_FAN overvoltage protection

- Physical limit: `16000mV`, divider `100000:10000`.
- Single AD_FAN reference: `2v`, generated threshold: `2978`, confirmations: `13`.
- Fixed-voltage regulation and the 16V guard reuse this same completed AD_FAN average.
- The software check is supplemental; boost hardware must still provide fast overvoltage protection.

## ADC

- Channel count: `3`
- Sample period: `1000us`
- Per-channel scan cycle: `30000us`
- One complete first-stage scan: `30 ms`
- Discard samples: `2`
- Average samples: `8`
- Fixed-voltage high-rate pipeline: disabled.
- Conversion wait limit: `50` loops
- Maximum first-stage u16 accumulation: `32760`
- `ADC_BAT_VALUE`: `AIN12_VDD_DIV4 / AIN12`, ADM=`0x9C`, VREFH=`0x00`, ADR=`0x40`, second average=`16`, result mode=`average`, result update=`480ms`, ready flags=`adc_bat_ready_flag`
- `AD_FAN_VALUE`: `PC3 / AIN7`, ADM=`0x97`, VREFH=`0x00`, ADR=`0x40`, second average=`1`, result mode=`average`, result update=`30ms`, ready flags=`ad_fan_ready_flag`
- `AD_KEY_VALUE`: `PA6 / AIN13`, ADM=`0x9D`, VREFH=`0x03`, ADR=`0x40`, second average=`1`, result mode=`average`, result update=`30ms`, ready flags=`ad_key_ready_flag`

## Classic product behavior

- Input kind: `ad_keys_active_low_ranges`
- AD threshold profile: `custom`
- AD KEY1 range: `0..100`; short=`fan_cycle`; double=`none`; long=`fan_power_toggle`
- AD KEY2 range: `610..810`; short=`atomizer_toggle`; double=`cooling_toggle`; long=`none`
- AD KEY3 range: `1210..1410`; short=`light_cycle`; double=`none`; long=`none`
- AD KEY4 range: `1810..2010`; short=`fan_step_up`; double=`none`; long=`fan_step_up`
- AD key double-click window: `350ms`.
- Short-press gear sequence: `20 -> 40 -> 60 -> 80 -> 100 -> 0`
- Long continuous adjustment: `true`
- Charging maximum gear: `60`
- Charging interface enabled/kind: `true` / `chrg_stdby_active_low`
- Display hardware/pins/drive: `standard_188_cooling_percent_style_a` / `5` / `output_high_input_off`
- Display mapped signals: `18`
- Display policy: `gear_event_battery_preview_idle`
- Display behavior profile: `gear_event_battery_preview_idle`
- Gear event/battery preview periods: `3000ms` / `3000ms`
- Normal/charging idle pages: `gear` / `battery`
- Low/charge blink targets: `both_digits` / `last_digit`
- Cooling/sleep enabled: `true` / `true`
- Cooling detection/control/charging policy: `true` / `toggle_while_fan_on` / `false`
- Light enabled/detection/mode: `true` / `true` / `on_off_flash`
- Atomizer enabled/frequency/duty/dependency/charging: `true` / `108000Hz` / `10%` / `independent` / `true`

## Deliberate limits

- This profile generates complete classic product behavior, but it is not declared production-ready without the target compiler and bench validation.
- Brushed/brushless auto-detection is not part of this fixed-motor profile.
- Atomizer PWM is generated from the configured frequency, duty and dependency policy.
- RGB, PWM light and communication modules are not part of this profile.
- Active-low slide-switch power control is not part of this profile.
- Battery thresholds, load compensation and chase periods are explicit product calibration parameters and still require the selected cell/load discharge curve.
