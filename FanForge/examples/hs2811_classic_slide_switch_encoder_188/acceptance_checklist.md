# FanForge product acceptance checklist: HS2811_CLASSIC_SLIDE_SWITCH_ENCODER_188

This file is generated from the resolved configuration. Checked resource items are generator-verified; unchecked items require compiler or bench confirmation.

## Generated configuration

- [x] MCU/package: `HS16P2811` / `SOP16`.
- [x] Oscillator/system divider/Fcpu: `16000000Hz` / `/2` / `8000000Hz`.
- [x] Timer1: `1000.000us`, `T1CON=0x01`, reload=`0xE0C0`.
- [x] Product profile: `classic`.

## Pin contract

- [x] `AD_FAN`: physical pin `10` -> `PC1`.
- [x] `CHRG`: physical pin `3` -> `PA6`.
- [x] `ENC_A`: physical pin `4` -> `PA5`.
- [x] `ENC_B`: physical pin `5` -> `PA4`.
- [x] `FAN_ON`: physical pin `8` -> `PC3`.
- [x] `IO_LED_1`: physical pin `15` -> `PA0`.
- [x] `IO_LED_2`: physical pin `14` -> `PA1`.
- [x] `IO_LED_3`: physical pin `13` -> `PA2`.
- [x] `IO_LED_4`: physical pin `11` -> `PC0`.
- [x] `IO_LED_5`: physical pin `9` -> `PC2`.
- [x] `PWM_FAN`: physical pin `7` -> `PC4`.
- [x] `STDBY`: physical pin `12` -> `PA3`.
- [x] `SWI_KEY`: physical pin `2` -> `PA7`.

## PWM contract

- [x] `PWM_FAN`: `PC4` -> `T3PWM0`, period=`63`, actual=`250000.000Hz`.
- [x] Fan duty curve: `12 + fan_mode / 4` counts.

## Motor safety contract

- [x] Motor kind: `brushless_fixed_duty`.
- [x] `AD_FAN` software protection is enabled.
- [x] Overvoltage threshold/confirmations: `2978` / `13`.
- [x] Brushless startup order: `FAN_ON`, wait about 10ms, then enable `PWM_FAN`.
- [x] Brushless shutdown order: disable `PWM_FAN`, wait about 10ms, then clear `FAN_ON`.
- [ ] Confirm the physical motor type and MOS/boost role of each generated output pin.
- [ ] Measure minimum and maximum gear PWM/voltage with the real motor connected.
- [ ] Verify motor-disconnect and running-fault behavior.

## Input and action contract

- [x] Input kind: `rotary_encoder_active_low`.
- [x] Encoder normal/accelerated step and direction: `1` / `5` / `clockwise_increases=true`.
- [x] Slide switch: `low` active, pull=`up`.
- [ ] Verify every short, double and long action on the target key resistor/GPIO hardware.
- [ ] Verify release, double-click timeout and sleep blocking.

## Charging and battery contract

- [x] Charging interface: `chrg_stdby_active_low`.
- [x] Charging maximum fan gear: `50`.
- [x] Battery ADC thresholds zero/low: `15000` / `18000`.
- [x] Battery curve p0/p5/p10/p50/p80/p100: `15360` / `17920` / `18841` / `19384` / `20122` / `21145`.
- [x] Fan load compensation: `272, 312, 462, 571, 680`.
- [x] Charge/full/discharge/low chase periods: `90000ms` / `25000ms` / `20000ms` / `5000ms`.
- [x] Non-insert discharge does not chase battery percentage upward.
- [ ] Verify charge, full, unplug and any supported discharge state truth table on the actual power IC.
- [ ] Run the selected cell/load discharge curve before production.

## Display and optional outputs

- [x] Display profile/pins/drive: `standard_188_cooling_percent_style_a` / `5` / `output_high_input_off`.
- [x] Display behavior: `gear_3s_battery_3s_gear`, gear event=`3000ms`, battery preview=`3000ms`, idle=`gear`, charging idle=`battery`.
- [x] Cooling: enabled=`false`, detection=`false`, charging allowed=`false`.
- [x] LED: enabled=`false`, mode=`fan_sync`.
- [x] Atomizer: enabled=`false`, duty=`10%`, dependency=`fan_required`.
- [ ] Verify all 188 segments/icons, full-light self-test, dark-frame ghosting and blink synchronization.
- [ ] Verify cooling, LED and atomizer dependencies and charging restrictions.

## Sleep and wake contract

- [x] Sleep enabled: `true`.
- [x] Normal sleep registers: `TRISA=0xF8`, `TRISC=0x00`, `PAHCON=0x07`, `PADCON=0xFF`, `WUACON=0xC8`.
- [x] Zero-battery sleep override: `PAHCON=0x87`, `WUACON=0x48`.
- [ ] Measure sleep current in normal-off and zero-battery states.
- [ ] Verify every intended wake source and confirm unintended keys cannot wake the product.

## Release gate

- [ ] Compile with the target HSIDE/PICC toolchain without errors or unexpected warnings.
- [ ] Record program/data-space usage and checksum.
- [ ] Complete cold boot, repeated on/off, charger insert/remove and low-battery tests.
- [ ] Confirm generated pin roles against schematic, PCB and package orientation.
- [ ] Update project HANDOFF with calibrated values and bench results before production.
