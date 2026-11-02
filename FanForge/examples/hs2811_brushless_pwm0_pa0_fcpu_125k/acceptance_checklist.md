# FanForge product acceptance checklist: HS2811_BRUSHLESS_PWM0_PA0_FCPU_125K

This file is generated from the resolved configuration. Checked resource items are generator-verified; unchecked items require compiler or bench confirmation.

## Generated configuration

- [x] MCU/package: `HS16P2811` / `SOP16`.
- [x] Oscillator/system divider/Fcpu: `16000000Hz` / `/2` / `8000000Hz`.
- [x] Timer1: `1000.000us`, `T1CON=0x31`, reload=`0xFC18`.
- [x] Product profile: `resource-demo`.

## Pin contract

- [x] `AD_FAN`: physical pin `10` -> `PC1`.
- [x] `FAN_ON`: physical pin `7` -> `PC4`.
- [x] `PWM_FAN`: physical pin `15` -> `PA0`.

## PWM contract

- [x] `PWM_FAN`: `PA0` -> `T3PWM0`, period=`31`, actual=`125000.000Hz`.

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

- [x] Input kind: `none`.
- [ ] Verify every short, double and long action on the target key resistor/GPIO hardware.
- [ ] Verify release, double-click timeout and sleep blocking.

## Charging and battery contract

- [x] Charging interface: `none`.
- [x] Charging maximum fan gear: `0`.
- [ ] Verify charge, full, unplug and any supported discharge state truth table on the actual power IC.
- [ ] Run the selected cell/load discharge curve before production.

## Display and optional outputs

- [x] Display profile/pins/drive: `none` / `0` / `none`.
- [x] Display behavior: `none`, gear event=`0ms`, battery preview=`0ms`, idle=`gear`, charging idle=`battery`.
- [x] Cooling: enabled=`false`, detection=`false`, charging allowed=`false`.
- [x] LED: enabled=`false`, mode=`fan_sync`.
- [x] Atomizer: enabled=`false`, duty=`10%`, dependency=`fan_required`.
- [ ] Verify all 188 segments/icons, full-light self-test, dark-frame ghosting and blink synchronization.
- [ ] Verify cooling, LED and atomizer dependencies and charging restrictions.

## Sleep and wake contract

- [x] Sleep enabled: `false`.
- [x] Normal sleep registers: `TRISA=0x00`, `TRISC=0x00`, `PAHCON=0xFF`, `PADCON=0xFF`, `WUACON=0x00`.
- [ ] Measure sleep current in normal-off and zero-battery states.
- [ ] Verify every intended wake source and confirm unintended keys cannot wake the product.

## Release gate

- [ ] Compile with the target HSIDE/PICC toolchain without errors or unexpected warnings.
- [ ] Record program/data-space usage and checksum.
- [ ] Complete cold boot, repeated on/off, charger insert/remove and low-battery tests.
- [ ] Confirm generated pin roles against schematic, PCB and package orientation.
- [ ] Update project HANDOFF with calibrated values and bench results before production.
