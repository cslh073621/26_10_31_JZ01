import json
import re
from pathlib import Path
from typing import Any

from fanforge import __version__
from fanforge.classic_product import apply_classic_slots
from fanforge.errors import FanForgeError
from fanforge.models import GenerationPlan


ROOT = Path(__file__).resolve().parent.parent
CORE_TEMPLATE = ROOT / "core" / "hs2811_fan_core.c.in"
SLOT_PATTERN = re.compile(r"@@([A-Z0-9_]+)@@")


def _hex8(value: int) -> str:
    return f"0x{value & 0xFF:02X}"


def _sleep_gpio_register_lines(
    *,
    porta: int,
    portc: int,
    trisa: int,
    trisc: int,
    pahcon: int,
    padcon: int,
    pchcon: int,
    pcdcon: int,
    indent: str = "",
) -> tuple[str, ...]:
    return (
        f"{indent}PORTA = {_hex8(porta)};",
        f"{indent}PORTC = {_hex8(portc)};",
        f"{indent}TRISA = {_hex8(trisa)};",
        f"{indent}TRISC = {_hex8(trisc)};",
        f"{indent}PAHCON = {_hex8(pahcon)};",
        f"{indent}PADCON = {_hex8(padcon)};",
        f"{indent}PCHCON = {_hex8(pchcon)};",
        f"{indent}PCDCON = {_hex8(pcdcon)};",
    )


def _sleep_gpio_configuration(plan: GenerationPlan) -> str:
    gpio = plan.gpio
    normal = _sleep_gpio_register_lines(
        porta=gpio.sleep_porta,
        portc=gpio.sleep_portc,
        trisa=gpio.sleep_trisa,
        trisc=gpio.sleep_trisc,
        pahcon=gpio.sleep_pahcon,
        padcon=gpio.sleep_padcon,
        pchcon=gpio.sleep_pchcon,
        pcdcon=gpio.sleep_pcdcon,
    )
    if not gpio.has_zero_battery_sleep_override:
        return "\n".join(normal)
    zero = _sleep_gpio_register_lines(
        porta=gpio.zero_battery_sleep_porta,
        portc=gpio.zero_battery_sleep_portc,
        trisa=gpio.zero_battery_sleep_trisa,
        trisc=gpio.zero_battery_sleep_trisc,
        pahcon=gpio.zero_battery_sleep_pahcon,
        padcon=gpio.zero_battery_sleep_padcon,
        pchcon=gpio.zero_battery_sleep_pchcon,
        pcdcon=gpio.zero_battery_sleep_pcdcon,
        indent="    ",
    )
    normal_indented = tuple(f"    {line}" for line in normal)
    return "\n".join(
        (
            "if(!charge_num)",
            "{",
            *zero,
            "}",
            "else",
            "{",
            *normal_indented,
            "}",
        )
    )


def _wake_source_configuration(plan: GenerationPlan) -> str:
    gpio = plan.gpio

    def lines(mask: int, indent: str = "") -> tuple[str, ...]:
        return (
            f"{indent}WUACON = {_hex8(mask)};",
            f"{indent}PORTA;",
            f"{indent}PAIF = 0;",
            f"{indent}PAIE = {1 if mask else 0};",
        )

    if gpio.has_zero_battery_sleep_override:
        body = (
            "if(!charge_num)",
            "{",
            *lines(gpio.zero_battery_wake_mask_a, "    "),
            "}",
            "else",
            "{",
            *lines(gpio.wake_mask_a, "    "),
            "}",
            "GIE = 1;",
        )
    else:
        body = (*lines(gpio.wake_mask_a), "GIE = 1;")
    return "\n".join(body)


def _render_template(template: str, slots: dict[str, str]) -> str:
    rendered = template
    for name, content in slots.items():
        line_pattern = re.compile(
            rf"(?m)^(?P<indent>[ \t]*)@@{re.escape(name)}@@[ \t]*$"
        )

        def replace_line(match: re.Match[str]) -> str:
            indent = match.group("indent")
            if not content:
                return ""
            return "\n".join(
                f"{indent}{line}" if line else "" for line in content.splitlines()
            )

        rendered = line_pattern.sub(replace_line, rendered)
        rendered = rendered.replace(f"@@{name}@@", content)

    unresolved = sorted(set(SLOT_PATTERN.findall(rendered)))
    if unresolved:
        raise FanForgeError(
            "internal generator error: unresolved slots: " + ", ".join(unresolved)
        )
    return rendered.rstrip() + "\n"


def _pwm_route_lines(plan: GenerationPlan) -> str:
    def legacy_route_lines(pwm) -> tuple[str, ...]:
        pwm_sel = pwm.route_mask if pwm.route_register == "PWMSEL" else 0
        pwm_sel1 = pwm.route_mask if pwm.route_register == "PWMSEL1" else 0
        return (
            "T3C0 = 0x00;",
            "T3C2 = 0x00;",
            f"T3C1 = {_hex8(pwm.t3c1)};",
            f"T3PL = {_hex8(pwm.period_register)};",
            f"T3PH = {_hex8(pwm.period_register >> 8)};",
            f"PWMSEL = {_hex8(pwm_sel)};",
            f"PWMSEL1 = {_hex8(pwm_sel1)};",
        )

    if not plan.auxiliary_pwm:
        if plan.alternate_pwm is None:
            return "\n".join(legacy_route_lines(plan.pwm))
        return "\n".join(
            (
                "if(!YOUSHUA_WUSHUA)",
                "{",
                *(
                    f"    {line}"
                    for line in legacy_route_lines(plan.pwm)
                ),
                "}",
                "else",
                "{",
                *(
                    f"    {line}"
                    for line in legacy_route_lines(plan.alternate_pwm)
                ),
                "}",
            )
        )

    def combined_route_lines(pwm_plans) -> tuple[str, ...]:
        pwm_sel = 0
        pwm_sel1 = 0
        timer_plans = {}
        for pwm in pwm_plans:
            if pwm.route_register == "PWMSEL":
                pwm_sel |= pwm.route_mask
            else:
                pwm_sel1 |= pwm.route_mask
            timer_plans.setdefault(pwm.timer, pwm)

        lines: list[str] = []
        if "T3" in timer_plans:
            pwm = timer_plans["T3"]
            lines.extend(
                (
                    "T3C0 = 0x00;",
                    "T3C2 = 0x00;",
                    f"T3C1 = {_hex8(pwm.t3c1)};",
                    f"T3PL = {_hex8(pwm.period_register)};",
                    f"T3PH = {_hex8(pwm.period_register >> 8)};",
                )
            )
        if "T4" in timer_plans:
            pwm = timer_plans["T4"]
            lines.extend(
                (
                    "T4C0 = 0x00;",
                    f"T4C1 = {_hex8(pwm.t3c1)};",
                    f"T4PL = {_hex8(pwm.period_register)};",
                    f"T4PH = {_hex8(pwm.period_register >> 8)};",
                )
            )
        lines.extend(
            (
                f"PWMSEL = {_hex8(pwm_sel)};",
                f"PWMSEL1 = {_hex8(pwm_sel1)};",
            )
        )
        return tuple(lines)

    brushless_group = (plan.pwm, *plan.auxiliary_pwm)
    if plan.alternate_pwm is None:
        return "\n".join(combined_route_lines(brushless_group))
    brushed_group = (plan.alternate_pwm, *plan.auxiliary_pwm)
    return "\n".join(
        (
            "if(!YOUSHUA_WUSHUA)",
            "{",
            *(
                f"    {line}"
                for line in combined_route_lines(brushless_group)
            ),
            "}",
            "else",
            "{",
            *(
                f"    {line}"
                for line in combined_route_lines(brushed_group)
            ),
            "}",
        )
    )


def _all_pwm_plans(plan: GenerationPlan):
    return tuple(
        dict.fromkeys(
            (
                plan.pwm,
                *((plan.alternate_pwm,) if plan.alternate_pwm else ()),
                *plan.auxiliary_pwm,
            )
        )
    )


def _pwm_run_symbol(pwm) -> str:
    return f"{pwm.timer}REN"


def _stop_pwm_timer_lines(
    plan: GenerationPlan, pwm, indent: str = ""
) -> tuple[str, ...]:
    run_symbol = _pwm_run_symbol(pwm)
    if not plan.auxiliary_pwm:
        return (f"{indent}{run_symbol} = 0;",)
    others = tuple(
        item.enable_symbol
        for item in _all_pwm_plans(plan)
        if item.timer == pwm.timer and item.enable_symbol != pwm.enable_symbol
    )
    if not others:
        return (f"{indent}{run_symbol} = 0;",)
    return (
        f"{indent}if(" + " && ".join(f"!{name}" for name in others) + ")",
        f"{indent}" + "{",
        f"{indent}    {run_symbol} = 0;",
        f"{indent}" + "}",
    )


def _pwm_zero_lines(plan: GenerationPlan) -> tuple[str, ...]:
    lines: list[str] = []
    for pwm in _all_pwm_plans(plan):
        lines.extend(
            (
                f"{pwm.duty_register} = 0;",
                f"{pwm.duty_high_register} = 0;",
                f"{pwm.enable_symbol} = 0;",
            )
        )
    for timer in ("T3", "T4"):
        if any(pwm.timer == timer for pwm in _all_pwm_plans(plan)):
            lines.append(f"{timer}REN = 0;")
    return tuple(dict.fromkeys(lines))


def _adc_role_result(plan: GenerationPlan, owner: str, role: str) -> str:
    key = f"{owner}.{role}"
    try:
        return plan.adc.role_results[key]
    except KeyError as exc:
        raise FanForgeError(
            f"internal generator error: missing ADC binding for {key}"
        ) from exc


def _adc_role_ready_flag(
    plan: GenerationPlan, owner: str, role: str
) -> str:
    key = f"{owner}.{role}"
    for channel in plan.adc.channels:
        if key in channel.request_roles and channel.ready_flag_names:
            if len(channel.ready_flag_names) == 1:
                return channel.ready_flag_names[0]
            if "ad_fan_ready_flag" in channel.ready_flag_names:
                return "ad_fan_ready_flag"
            return channel.ready_flag_names[0]
    raise FanForgeError(
        f"internal generator error: missing ADC ready flag for {key}"
    )


def _fan_adc_owner(plan: GenerationPlan) -> str:
    if plan.config.motor.kind in (
        "brushless_fixed_voltage_7_3",
        "brushed_brushless_compat_fixed_voltage_7_3",
    ):
        return "motor.fixed_voltage"
    return "fan_voltage_protection.fixed_duty"


def _adc_channel_configuration(channel) -> list[str]:
    return (
        f"ADM = {_hex8(channel.adm_value)};",
        f"VREFH = {_hex8(channel.vrefh_value)};",
        f"ADR = {_hex8(channel.adr_value)};",
    )


def _adc_channel_switch(plan: GenerationPlan) -> str:
    channels = plan.adc.channels
    if len(channels) == 1:
        lines = ["if(!ADCDATA_COUNT)", "{"]
        lines.extend(f"    {line}" for line in _adc_channel_configuration(channels[0]))
        lines.append("}")
        return "\n".join(lines)

    blocks: list[str] = ["if(!ADCDATA_COUNT)", "{"]
    last_index = len(channels) - 1
    for index, channel in enumerate(channels):
        previous_index = last_index if index == 0 else index - 1
        prefix = "if" if index == 0 else "else if"
        blocks.append(f"    {prefix}(ad_channel == {previous_index})")
        blocks.append("    {")
        blocks.extend(
            f"        {line}" for line in _adc_channel_configuration(channel)
        )
        blocks.append(f"        ad_channel = {index};")
        blocks.append("    }")
    blocks.append("}")
    return "\n".join(blocks)


def _adc_ready_lines(channel) -> tuple[str, ...]:
    return tuple(f"{name} = 1;" for name in channel.ready_flag_names)


def _adc_result_update(channel) -> list[str]:
    if channel.secondary_average_samples == 1:
        return (
            f"{channel.result_name} = ADCDATA_SUM;",
            *_adc_ready_lines(channel),
        )

    shift = channel.secondary_average_samples.bit_length() - 1
    return (
        f"{channel.secondary_count_name}++;",
        f"{channel.secondary_sum_name} += ADCDATA_SUM;",
        (
            f"if({channel.secondary_count_name} >= "
            f"{channel.secondary_average_samples})"
        ),
        "{",
        f"    {channel.secondary_count_name} = 0;",
        f"    {channel.result_name} = {channel.secondary_sum_name} >> {shift};",
        f"    {channel.secondary_sum_name} = 0;",
        *(f"    {line}" for line in _adc_ready_lines(channel)),
        "}",
    )


def _high_rate_adc_accumulation(plan: GenerationPlan) -> str:
    """Emit the fixed-voltage 100us ADC pipeline.

    Preserve the F824 arithmetic verbatim: one sample counter determines group
    boundaries, and the sum is never shifted in place before publication.
    The first-stage accumulator is deliberately kept at eight samples so it
    remains u16-safe.  Twelve averaged groups then form one channel result.
    """
    adc = plan.adc
    lines = [
        "ADCDATA_COUNT++;",
        f"if(ADCDATA_COUNT > {adc.high_rate_discard_samples})",
        "{",
        "    ADCDATA_SUM += ad_temp;",
        f"    if((ADCDATA_COUNT & 0x{adc.high_rate_group_size - 1:02X}) == "
        f"{adc.high_rate_discard_samples % adc.high_rate_group_size})",
        "    {",
        "        ADC_GROUP_SUM += ADCDATA_SUM >> "
        f"{adc.high_rate_group_size.bit_length() - 1};",
        "        ADCDATA_SUM = 0;",
        "    }",
        "}",
        f"if(ADCDATA_COUNT >= {adc.high_rate_samples_per_channel})",
        "{",
        "    ADCDATA_COUNT = 0;",
        "    ADCDATA_SUM = ADC_GROUP_SUM / "
        f"{adc.high_rate_group_count};",
        "    ADC_GROUP_SUM = 0;",
    ]

    def result_update(channel, indent: str) -> list[str]:
        result_lines: list[str] = []
        if channel.result_mode == "sum":
            # Preserve the mature eight-sample sum scale for slider results.
            result_lines.append(f"{indent}ADCDATA_SUM <<= 3;")
        result_lines.extend(f"{indent}{line}" for line in _adc_result_update(channel))
        return result_lines

    if len(adc.channels) == 1:
        lines.extend(result_update(adc.channels[0], "    "))
    else:
        for index, channel in enumerate(adc.channels):
            prefix = "if" if index == 0 else "else if"
            lines.extend(
                (
                    f"    {prefix}(ad_channel == {index})",
                    "    {",
                    *result_update(channel, "        "),
                    "    }",
                )
            )
    lines.extend(
        (
            "    ADCDATA_SUM = 0;",
            "}",
            "",
            "/* Fixed-voltage high-rate limits checked by FanForge:",
            f" * 4095 * {adc.high_rate_group_size} = "
            f"{4095 * adc.high_rate_group_size} <= 65535.",
            f" * 4095 * {adc.high_rate_group_count} = "
            f"{4095 * adc.high_rate_group_count} <= 65535.",
            " */",
        )
    )
    return "\n".join(lines)


def _adc_accumulation(plan: GenerationPlan) -> str:
    adc = plan.adc
    if adc.high_rate_enabled:
        return _high_rate_adc_accumulation(plan)
    protection = plan.config.fan_protection
    total_samples = adc.discard_samples + adc.average_samples
    shift = adc.average_samples.bit_length() - 1
    has_sum_result = any(
        channel.result_mode == "sum" for channel in adc.channels
    )
    lines = [
        "ADCDATA_COUNT++;",
        f"if(ADCDATA_COUNT > {adc.discard_samples})",
        "{",
        "    ADCDATA_SUM += ad_temp;",
        "}",
        f"if(ADCDATA_COUNT >= {total_samples})",
        "{",
        "    ADCDATA_COUNT = 0;",
    ]
    if not has_sum_result:
        lines.append(f"    ADCDATA_SUM >>= {shift};")

    if len(adc.channels) == 1:
        if adc.channels[0].result_mode == "average" and has_sum_result:
            lines.append(f"    ADCDATA_SUM >>= {shift};")
        lines.extend(f"    {line}" for line in _adc_result_update(adc.channels[0]))
    else:
        for index, channel in enumerate(adc.channels):
            prefix = "if" if index == 0 else "else if"
            lines.append(f"    {prefix}(ad_channel == {index})")
            lines.append("    {")
            if channel.result_mode == "average" and has_sum_result:
                lines.append(f"        ADCDATA_SUM >>= {shift};")
            lines.extend(
                f"        {line}" for line in _adc_result_update(channel)
            )
            lines.append("    }")

    lines.extend(
        (
            "    ADCDATA_SUM = 0;",
            "}",
            "",
            "/* u16 accumulation limits checked by FanForge:",
            f" * 4095 * {adc.average_samples} = "
            f"{4095 * adc.average_samples} <= 65535.",
            f" * Overvoltage confirmation count: "
            f"{protection.consecutive_confirmations}.",
            " */",
        )
    )
    return "\n".join(lines)


def _adc_global_state(plan: GenerationPlan) -> str:
    lines = ["u16 ADCDATA_SUM;"]
    if plan.adc.high_rate_enabled:
        lines.extend(
            (
                "u16 ADC_GROUP_SUM;",
            )
        )
    for channel in plan.adc.channels:
        lines.append(f"u16 {channel.result_name};")
        if channel.secondary_sum_name is not None:
            lines.append(f"u16 {channel.secondary_sum_name};")
    lines.append("u8 ADCDATA_COUNT;")
    if len(plan.adc.channels) > 1:
        lines.append("u8 ad_channel;")
    for channel in plan.adc.channels:
        if channel.secondary_count_name is not None:
            lines.append(f"u8 {channel.secondary_count_name};")
    if plan.config.fan_protection.enabled:
        lines.append("u8 too_big_cnt;")
    if plan.config.motor.kind in (
        "brushless_fixed_voltage_7_3",
        "brushed_brushless_compat_fixed_voltage_7_3",
    ):
        lines.extend(
            (
                "u8 PWM_DR;",
                "u8 PWM_CNT;",
                "u8 PWM_DATA_NOW;",
            )
        )
    if plan.alternate_pwm is not None:
        lines.append("u8 youshua_wushua_high_cnt;")
    if plan.timer.subticks_per_ms > 1:
        lines.append("u8 t1_subtick_cnt;")
    return "\n".join(lines)


def _adc_reset(plan: GenerationPlan) -> str:
    lines = ["ADCDATA_SUM = 0;", "ADCDATA_COUNT = 0;"]
    if plan.adc.high_rate_enabled:
        lines.extend(
            (
                "adc_high_rate_flag = 0;",
                "ADC_GROUP_SUM = 0;",
            )
        )
    if len(plan.adc.channels) > 1:
        lines.append(f"ad_channel = {len(plan.adc.channels) - 1};")
    for channel in plan.adc.channels:
        lines.append(f"{channel.result_name} = 0;")
        if channel.secondary_sum_name is not None:
            lines.append(f"{channel.secondary_sum_name} = 0;")
        if channel.secondary_count_name is not None:
            lines.append(f"{channel.secondary_count_name} = 0;")
        lines.extend(f"{name} = 0;" for name in channel.ready_flag_names)
    if plan.config.fan_protection.enabled:
        lines.append("too_big_cnt = 0;")
    if plan.config.motor.kind in (
        "brushless_fixed_voltage_7_3",
        "brushed_brushless_compat_fixed_voltage_7_3",
    ):
        lines.extend(
            (
                "PWM_DR = 0;",
                "PWM_CNT = 0;",
                "PWM_DATA_NOW = 0;",
            )
        )
    if plan.timer.subticks_per_ms > 1:
        lines.append("t1_subtick_cnt = 0;")
    return "\n".join(lines)


def _time_flag_declarations(plan: GenerationPlan) -> str:
    return "\n".join(
        f"bit {signal.flag_name};"
        for signal in plan.time_resources.signals
        if signal.flag_name is not None
    )


def _time_counter_declarations(plan: GenerationPlan) -> str:
    return "\n".join(
        f"u8 {signal.counter_name};"
        for signal in plan.time_resources.signals
        if signal.counter_name is not None
    )


def _time_children(plan: GenerationPlan, period_ms: int):
    return tuple(
        signal
        for signal in plan.time_resources.signals
        if signal.parent_period_ms == period_ms
    )


def _time_parent_body(plan: GenerationPlan, signal) -> list[str]:
    lines: list[str] = []
    if signal.flag_name is not None:
        lines.append(f"{signal.flag_name} = 1;")
    if signal.phase == "system" and signal.reset_semantics == "continuous":
        for child in _time_children(plan, signal.period_ms):
            if child.counter_name is None:
                raise FanForgeError(
                    f"internal generator error: {child.period_ms}ms child has no counter"
                )
            lines.append(f"{child.counter_name}++;")
    return lines


def _base_time_isr(plan: GenerationPlan) -> str:
    roots = tuple(
        signal
        for signal in plan.time_resources.signals
        if signal.parent_period_ms is None
    )
    if len(roots) != 1 or roots[0].period_ms != 1:
        raise FanForgeError("internal generator error: expected one 1ms time root")
    return "\n".join(_time_parent_body(plan, roots[0]))


def _base_time_prefix(plan: GenerationPlan) -> str:
    if plan.timer.subticks_per_ms == 1:
        return ""
    return "\n".join(
        (
            "t1_subtick_cnt++;",
            f"if(t1_subtick_cnt >= {plan.timer.subticks_per_ms})",
            "{",
            "    t1_subtick_cnt = 0;",
        )
    )


def _base_time_suffix(plan: GenerationPlan) -> str:
    return "}" if plan.timer.subticks_per_ms > 1 else ""


def _high_rate_motor_isr(plan: GenerationPlan) -> str:
    if plan.config.motor.kind not in (
        "brushless_fixed_voltage_7_3",
        "brushed_brushless_compat_fixed_voltage_7_3",
    ):
        return ""
    pwm = plan.pwm
    enabled_condition = (
        f"{pwm.enable_symbol} && {_pwm_run_symbol(pwm)}"
    )
    if plan.alternate_pwm is not None:
        enabled_condition = f"!YOUSHUA_WUSHUA && {enabled_condition}"
    return "\n".join(
        (
            "adc_high_rate_flag = 1;",
            f"if({enabled_condition})",
            "{",
            "    if(PWM_CNT < 7)",
            "    {",
            "        PWM_CNT++;",
            "    }",
            "    else",
            "    {",
            "        PWM_CNT = 0;",
            "    }",
            "",
            "    if(PWM_DR > PWM_CNT)",
            "    {",
            f"        {pwm.duty_register} = PWM_DATA_NOW + 1;",
            "    }",
            "    else",
            "    {",
            f"        {pwm.duty_register} = PWM_DATA_NOW;",
            "    }",
            "}",
        )
    )


def _time_flag_derivation(plan: GenerationPlan) -> str:
    blocks: list[str] = []
    for signal in plan.time_resources.signals:
        if signal.parent_period_ms is None:
            continue
        if signal.counter_name is None:
            raise FanForgeError(
                f"internal generator error: {signal.period_ms}ms signal has no counter"
            )
        threshold = signal.ticks_per_period - 1
        lines = [
            f"if({signal.counter_name} > {threshold})",
            "{",
            f"    {signal.counter_name} = 0;",
        ]
        lines.extend(f"    {line}" for line in _time_parent_body(plan, signal))
        lines.append("}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _time_role_flag(plan: GenerationPlan, owner: str, role: str) -> str:
    key = f"{owner}.{role}"
    try:
        return plan.time_resources.role_flags[key]
    except KeyError as exc:
        raise FanForgeError(
            f"internal generator error: missing time binding for {key}"
        ) from exc


def _fan_deal_fixed_duty(plan: GenerationPlan) -> str:
    pwm = plan.pwm
    run_symbol = _pwm_run_symbol(pwm)
    config = plan.config
    ad_fan_value = _adc_role_result(
        plan, "fan_voltage_protection.fixed_duty", "AD_FAN"
    )
    if config.motor.run_duty_percent is None:
        raise FanForgeError("fixed-duty motor is missing its duty percent")
    period_count = pwm.period_register + 1
    duty_count = round(period_count * config.motor.run_duty_percent / 100)
    duty_count = max(1, min(pwm.period_register, duty_count))
    ready_flags = tuple(
        name
        for channel in plan.adc.channels
        if channel.result_name == ad_fan_value
        for name in channel.ready_flag_names
    )
    ready_flag = ready_flags[0] if ready_flags else None
    protection_lines = [
        f"if({ad_fan_value} > AD_FAN_TOO_HIGH)",
        "{",
        "    if(too_big_cnt < 255)",
        "    {",
        "        too_big_cnt++;",
        "    }",
        "    if(too_big_cnt >= AD_FAN_CONFIRM_COUNT)",
        "    {",
        "        fan_error_flag = 1;",
        "        fan_mode = 0;",
        f"        {pwm.enable_symbol} = 0;",
        *_stop_pwm_timer_lines(plan, pwm, "        "),
        f"        {pwm.duty_register} = 0;",
        f"        {pwm.duty_high_register} = 0;",
        "        return;",
        "    }",
        "}",
        "else",
        "{",
        "    too_big_cnt = 0;",
        "}",
    ]
    if ready_flag is not None:
        protection_lines = [
            f"if({ready_flag})",
            "{",
            f"    {ready_flag} = 0;",
            *(f"    {line}" for line in protection_lines),
            "}",
        ]
    return "\n".join(
        (
            "if(fan_mode == 0 || fan_error_flag)",
            "{",
            "    too_big_cnt = 0;",
            f"    if({pwm.enable_symbol} || {run_symbol})",
            "    {",
            f"        {pwm.enable_symbol} = 0;",
            *_stop_pwm_timer_lines(plan, pwm, "        "),
            f"        {pwm.duty_register} = 0;",
            f"        {pwm.duty_high_register} = 0;",
            "        return;",
            "    }",
            "",
            "    FAN_ON = 0;",
            "    return;",
            "}",
            "",
            *protection_lines,
            "",
            "if(!FAN_ON)",
            "{",
            "    FAN_ON = 1;",
            "    return;",
            "}",
            "",
            "/* AD_fan_deal() runs every 10ms. Reaching this call after",
            " * FAN_ON was asserted provides the required brushless delay.",
            " */",
            f"{pwm.duty_register} = {_hex8(duty_count)};",
            f"{pwm.duty_high_register} = {_hex8(duty_count >> 8)};",
            f"{pwm.enable_symbol} = 1;",
            f"{run_symbol} = 1;",
        )
    )


def _fan_deal_brushed_fixed_duty(plan: GenerationPlan) -> str:
    pwm = plan.pwm
    run_symbol = _pwm_run_symbol(pwm)
    return "\n".join(
        (
            "if(!fan_mode)",
            "{",
            f"    {pwm.enable_symbol} = 0;",
            *_stop_pwm_timer_lines(plan, pwm, "    "),
            f"    {pwm.duty_register} = 0;",
            f"    {pwm.duty_high_register} = 0;",
            "    FAN_ON = 0;",
            "    return;",
            "}",
            "",
            f"{pwm.duty_register} = FAN_PWM_DUTY_BASE",
            "    + fan_mode / FAN_PWM_GEAR_DIVISOR;",
            f"{pwm.duty_high_register} = 0;",
            f"{pwm.enable_symbol} = 1;",
            f"{run_symbol} = 1;",
        )
    )


def _fixed_voltage_compare(plan: GenerationPlan) -> str:
    if plan.config.motor.kind not in (
        "brushless_fixed_voltage_7_3",
        "brushed_brushless_compat_fixed_voltage_7_3",
    ):
        return "return 0;"
    return "\n".join(
        (
            "u8 base_val;",
            "u16 fin_val;",
            "",
            "base_val = fan_mode - 1;",
            "fin_val = AD_FAN_TARGET_BASE;",
            "if(fan_mode >= AD_FAN_GEAR_MAX)",
            "{",
            "    fin_val = AD_FAN_TARGET_MAX;",
            "}",
            "else",
            "{",
            "    while(base_val--)",
            "    {",
            "        fin_val += AD_FAN_TARGET_STEP;",
            "    }",
            "}",
            "",
            "if(temp_val < fin_val)",
            "{",
            "    if(fin_val - temp_val > AD_FAN_ERROR_WINDOW)",
            "    {",
            "        return 2;",
            "    }",
            "    return 1;",
            "}",
            "",
            "if(temp_val - fin_val > AD_FAN_ERROR_WINDOW)",
            "{",
            "    return 0;",
            "}",
            "return 3;",
        )
    )


def _fan_deal_fixed_voltage(plan: GenerationPlan) -> str:
    pwm = plan.pwm
    run_symbol = _pwm_run_symbol(pwm)
    motor = plan.config.motor
    ready_flag = _adc_role_ready_flag(
        plan, "motor.fixed_voltage", "AD_FAN"
    )
    ad_value = _adc_role_result(plan, "motor.fixed_voltage", "AD_FAN")
    slow_adjust_enabled = motor.voltage_slow_adjust_ms is not None
    slow_flag = (
        _time_role_flag(plan, f"motor.{motor.kind}", "slow_adjust")
        if slow_adjust_enabled
        else None
    )
    slow_reset_lines = ("quick_slow_flag = 0;",) if slow_adjust_enabled else ()
    brushed_lines: tuple[str, ...] = ()
    if plan.alternate_pwm is not None:
        brushed = plan.alternate_pwm
        brushed_run_symbol = _pwm_run_symbol(brushed)
        if (
            motor.brushed_duty_base_count is None
            or motor.brushed_duty_gear_divisor is None
        ):
            raise FanForgeError("compatible brushed duty curve is incomplete")
        brushed_lines = (
            "if(YOUSHUA_WUSHUA)",
            "{",
            "    too_big_cnt = 0;",
            f"    {ready_flag} = 0;",
            *slow_reset_lines,
            "    PWM_DR = 0;",
            "    PWM_DATA_NOW = 0;",
            f"    {pwm.enable_symbol} = 0;",
            f"    {pwm.duty_register} = 0;",
            f"    {pwm.duty_high_register} = 0;",
            "    PWM_FAN = 0;",
            "    if(!fan_mode || fan_error_flag)",
            "    {",
            f"        {brushed.enable_symbol} = 0;",
            *_stop_pwm_timer_lines(plan, brushed, "        "),
            f"        {brushed.duty_register} = 0;",
            f"        {brushed.duty_high_register} = 0;",
            "        FAN_ON = 0;",
            "        return;",
            "    }",
            f"    {brushed.duty_register} = BRUSHED_PWM_DUTY_BASE",
            "        + fan_mode / BRUSHED_PWM_GEAR_DIVISOR;",
            f"    {brushed.duty_high_register} = 0;",
            f"    {brushed.enable_symbol} = 1;",
            f"    {brushed_run_symbol} = 1;",
            "    return;",
            "}",
            "",
        )
    return "\n".join(
        (
            "u8 result;",
            "u16 temp_pbp_val;",
            "",
            *brushed_lines,
            "if(!fan_mode || fan_error_flag)",
            "{",
            "    too_big_cnt = 0;",
            f"    {ready_flag} = 0;",
            *slow_reset_lines,
            "    PWM_DR = 0;",
            f"    if({pwm.enable_symbol} || {run_symbol})",
            "    {",
            f"        {pwm.enable_symbol} = 0;",
            *_stop_pwm_timer_lines(plan, pwm, "        "),
            f"        {pwm.duty_register} = 0;",
            f"        {pwm.duty_high_register} = 0;",
            "        PWM_DATA_NOW = 0;",
            "        return;",
            "    }",
            "    PWM_DATA_NOW = 0;",
            "    FAN_ON = 0;",
            "    return;",
            "}",
            "",
            "if(!FAN_ON)",
            "{",
            "    too_big_cnt = 0;",
            f"    {ready_flag} = 0;",
            *slow_reset_lines,
            "    PWM_DR = 0;",
            "    PWM_DATA_NOW = 0;",
            "    FAN_ON = 1;",
            "    return;",
            "}",
            "",
            f"if(!{pwm.enable_symbol} || !{run_symbol})",
            "{",
            "    PWM_DATA_NOW = AD_FAN_PWM_MIN_COUNT;",
            f"    {pwm.duty_register} = PWM_DATA_NOW;",
            f"    {pwm.duty_high_register} = 0;",
            f"    {pwm.enable_symbol} = 1;",
            f"    {run_symbol} = 1;",
            "    return;",
            "}",
            "",
            f"if(!{ready_flag})",
            "{",
            "    return;",
            "}",
            f"{ready_flag} = 0;",
            "",
            f"if({ad_value} > AD_FAN_TOO_HIGH)",
            "{",
            "    if(too_big_cnt < 255)",
            "    {",
            "        too_big_cnt++;",
            "    }",
            "    if(too_big_cnt >= AD_FAN_CONFIRM_COUNT)",
            "    {",
            "        fan_error_flag = 1;",
            "        fan_mode = 0;",
            *(
                ("        quick_slow_flag = 0;",)
                if slow_adjust_enabled
                else ()
            ),
            "        PWM_DR = 0;",
            "        PWM_DATA_NOW = 0;",
            f"        {pwm.enable_symbol} = 0;",
            *_stop_pwm_timer_lines(plan, pwm, "        "),
            f"        {pwm.duty_register} = 0;",
            f"        {pwm.duty_high_register} = 0;",
            "        return;",
            "    }",
            "}",
            "else",
            "{",
            "    too_big_cnt = 0;",
            "}",
            "",
            *(
                (
                    f"if(quick_slow_flag && !{slow_flag})",
                    "{",
                    "    return;",
                    "}",
                    f"{slow_flag} = 0;",
                )
                if slow_adjust_enabled
                else ()
            ),
            f"temp_pbp_val = {ad_value} * AD_FAN_MEASURE_MULTIPLIER;",
            "result = Get_Fin_Val(temp_pbp_val);",
            "",
            "if(result == 2)",
            "{",
            "    if(PWM_DATA_NOW < AD_FAN_PWM_MAX_COUNT)",
            "    {",
            "        PWM_DATA_NOW++;",
            "    }",
            *(
                ("    quick_slow_flag = 0;",)
                if slow_adjust_enabled
                else ()
            ),
            "}",
            "else if(result == 1)",
            "{",
            *(
                ("    quick_slow_flag = 1;",)
                if slow_adjust_enabled
                else ()
            ),
            "    if(PWM_DR < 7)",
            "    {",
            "        PWM_DR++;",
            "    }",
            "    else",
            "    {",
            "        PWM_DR = 0;",
            "        if(PWM_DATA_NOW < AD_FAN_PWM_MAX_COUNT)",
            "        {",
            "            PWM_DATA_NOW++;",
            "        }",
            "    }",
            "}",
            "else if(result == 0)",
            "{",
            "    if(PWM_DATA_NOW > AD_FAN_PWM_MIN_COUNT)",
            "    {",
            "        PWM_DATA_NOW--;",
            "    }",
            *(
                ("    quick_slow_flag = 0;",)
                if slow_adjust_enabled
                else ()
            ),
            "}",
            "else",
            "{",
            *(
                ("    quick_slow_flag = 1;",)
                if slow_adjust_enabled
                else ()
            ),
            "    if(PWM_DR > 0)",
            "    {",
            "        PWM_DR--;",
            "    }",
            "    else",
            "    {",
            "        PWM_DR = 7;",
            "        if(PWM_DATA_NOW > AD_FAN_PWM_MIN_COUNT)",
            "        {",
            "            PWM_DATA_NOW--;",
            "        }",
            "    }",
            "}",
            "",
            "if(PWM_DATA_NOW > AD_FAN_PWM_MAX_COUNT)",
            "{",
            "    PWM_DATA_NOW = AD_FAN_PWM_MAX_COUNT;",
            "}",
        )
    )


def _fan_deal(plan: GenerationPlan) -> str:
    if plan.config.motor.kind == "brushed_fixed_duty":
        return _fan_deal_brushed_fixed_duty(plan)
    if plan.config.motor.kind in (
        "brushless_fixed_voltage_7_3",
        "brushed_brushless_compat_fixed_voltage_7_3",
    ):
        return _fan_deal_fixed_voltage(plan)
    return _fan_deal_fixed_duty(plan)


def _motor_parameter_definitions(plan: GenerationPlan) -> str:
    config = plan.config
    pwm = plan.pwm
    lines = [
        f"#define FAN_PWM_TARGET_HZ {config.motor.pwm_frequency_hz}UL",
        f"#define FAN_PWM_PERIOD    {pwm.period_register}",
    ]
    if config.motor.kind in (
        "brushless_fixed_duty",
        "brushed_fixed_duty",
    ):
        if config.motor.run_duty_percent is None:
            raise FanForgeError("fixed-duty motor is missing its duty percent")
        lines.append(
            f"#define FAN_PWM_DUTY      {config.motor.run_duty_percent}"
        )
    else:
        values = (
            config.motor.voltage_target_base,
            config.motor.voltage_target_step,
            config.motor.voltage_target_max,
            config.motor.voltage_measurement_multiplier,
            config.motor.voltage_error_window,
            config.motor.voltage_pwm_min_count,
            config.motor.voltage_pwm_max_count,
        )
        if any(value is None for value in values):
            raise FanForgeError("fixed-voltage motor parameters are incomplete")
        lines.extend(
            (
                f"#define AD_FAN_TARGET_BASE       {values[0]}",
                f"#define AD_FAN_TARGET_STEP       {values[1]}",
                f"#define AD_FAN_TARGET_MAX        {values[2]}",
                (
                    "#define AD_FAN_GEAR_MAX         "
                    f"{config.classic_product.maximum_gear if config.classic_product.enabled else 100}"
                ),
                f"#define AD_FAN_MEASURE_MULTIPLIER {values[3]}",
                f"#define AD_FAN_ERROR_WINDOW      {values[4]}",
                f"#define AD_FAN_PWM_MIN_COUNT     {values[5]}",
                f"#define AD_FAN_PWM_MAX_COUNT     {values[6]}",
            )
        )
        if plan.alternate_pwm is not None:
            if (
                config.motor.brushed_pwm_frequency_hz is None
                or config.motor.brushed_duty_base_count is None
                or config.motor.brushed_duty_gear_divisor is None
                or config.motor.detection_samples is None
                or config.motor.detection_high_threshold is None
            ):
                raise FanForgeError(
                    "compatible motor parameters are incomplete"
                )
            lines.extend(
                (
                    (
                        "#define BRUSHED_PWM_TARGET_HZ "
                        f"{config.motor.brushed_pwm_frequency_hz}UL"
                    ),
                    (
                        "#define BRUSHED_PWM_PERIOD    "
                        f"{plan.alternate_pwm.period_register}"
                    ),
                    (
                        "#define BRUSHED_PWM_DUTY_BASE "
                        f"{config.motor.brushed_duty_base_count}"
                    ),
                    (
                        "#define BRUSHED_PWM_GEAR_DIVISOR "
                        f"{config.motor.brushed_duty_gear_divisor}"
                    ),
                    (
                        "#define MOTOR_DETECT_SAMPLES "
                        f"{config.motor.detection_samples}"
                    ),
                    (
                        "#define MOTOR_DETECT_HIGH_THRESHOLD "
                        f"{config.motor.detection_high_threshold}"
                    ),
                )
            )
    if config.fan_protection.enabled:
        lines.extend(
            (
                (
                    "#define AD_FAN_TOO_HIGH    "
                    f"{config.fan_protection.overvoltage_adc_threshold}"
                ),
                (
                    "/* Consecutive valid overvoltage means; normal resets count. Min 2; F824 baseline 13. */\n"
                    "#define AD_FAN_CONFIRM_COUNT  "
                    f"{config.fan_protection.consecutive_confirmations}"
                ),
            )
        )
    return "\n".join(lines)


def _motor_detection_function(plan: GenerationPlan) -> str:
    if plan.alternate_pwm is None:
        return ""
    gpio = plan.pwm.gpio_name
    port = gpio[1]
    bit = int(gpio[2:])
    clear_mask = _hex8(~(1 << bit))
    set_mask = _hex8(1 << bit)
    pull_register = f"P{port}HCON"
    return "\n".join(
        (
            "void detect_youshua_wushua(void)",
            "{",
            f"    {plan.pwm.enable_symbol} = 0;",
            f"    PORT{port} &= {clear_mask};",
            f"    TRIS{port} |= {set_mask};",
            f"    {pull_register} &= {clear_mask};",
            "    _NOP();",
            "    _NOP();",
            "    _NOP();",
            "    _NOP();",
            "    if(PWM_FAN)",
            "    {",
            "        youshua_wushua_high_cnt++;",
            "    }",
            "}",
        )
    )


def build_slots(plan: GenerationPlan) -> dict[str, str]:
    config = plan.config
    timer = plan.timer
    pwm = plan.pwm
    adc = plan.adc
    first_adc = adc.channels[0]
    gpio = plan.gpio

    slots = {
        "GENERATED_FILE_NOTICE": (
            f"Generated by FanForge {__version__} for {config.project_name}.\n"
            " * Initial reviewed hardware-resource demo, not a production fan project.\n"
            " * Do not hand-edit generated register assignments; change the JSON config."
        ),
        "PIN_AND_IO_DEFINITIONS": "\n".join(
            f"#define {role:<8} {plan.resolved_pins[role]}"
            for role in ("PWM_FAN", "FAN_ON", "AD_FAN", "AD_KEY")
            if role in plan.resolved_pins
        ),
        "PARAMETER_DEFINITIONS": _motor_parameter_definitions(plan),
        "TIME_FLAG_DECLARATIONS": _time_flag_declarations(plan),
        "ADDITIONAL_NATIVE_BIT_FLAGS": "\n".join(
            (
                "bit fan_error_flag;",
                *(
                    ("bit quick_slow_flag;",)
                    if config.motor.kind
                    in (
                        "brushless_fixed_voltage_7_3",
                        "brushed_brushless_compat_fixed_voltage_7_3",
                    )
                    and config.motor.voltage_slow_adjust_ms is not None
                    else ()
                ),
                *(("bit adc_high_rate_flag;",) if adc.high_rate_enabled else ()),
                *(
                    ("bit YOUSHUA_WUSHUA;",)
                    if plan.alternate_pwm is not None
                    else ()
                ),
                *(
                    f"bit {name};"
                    for channel in plan.adc.channels
                    for name in channel.ready_flag_names
                ),
            )
        ),
        "TIME_COUNTER_DECLARATIONS": _time_counter_declarations(plan),
        "ADDITIONAL_GLOBAL_STATE": _adc_global_state(plan),
        "PORT_CHANGE_ISR_BODY": "",
        "T1_RELOAD_HIGH": str((timer.reload_value >> 8) & 0xFF),
        "T1_RELOAD_LOW": str(timer.reload_value & 0xFF),
        "HIGH_RATE_ISR_BODY": _high_rate_motor_isr(plan),
        "BASE_TIME_ISR_PREFIX": _base_time_prefix(plan),
        "BASE_TIME_ISR_BODY": _base_time_isr(plan),
        "FIXED_1MS_ISR_BODY": "",
        "BASE_TIME_ISR_SUFFIX": _base_time_suffix(plan),
        "GPIO_PORT_INITIALIZATION": "\n".join(
            (
                f"PORTA = {_hex8(gpio.porta)};",
                f"PORTC = {_hex8(gpio.portc)};",
            )
        ),
        "GPIO_CONFIGURATION": "\n".join(
            (
                f"TRISA = {_hex8(gpio.trisa)};",
                f"TRISC = {_hex8(gpio.trisc)};",
                f"PAHCON = {_hex8(gpio.pahcon)};",
                f"PADCON = {_hex8(gpio.padcon)};",
                f"PCHCON = {_hex8(gpio.pchcon)};",
                f"PCDCON = {_hex8(gpio.pcdcon)};",
            )
        ),
        "SAFE_OUTPUT_INITIALIZATION": "\n".join(
            ("PWM_FAN = 0;", "FAN_ON = 0;")
        ),
        "ANALOG_PORT_CONFIGURATION": "\n".join(
            (
                f"ADPCON = {_hex8(gpio.adpcon)};",
                f"ADPCON1 = {_hex8(gpio.adpcon1)};",
            )
        ),
        "ADC_COMMON_REGISTER_CONFIGURATION": "\n".join(
            (
                f"ADM = {_hex8(first_adc.adm_value)};",
                f"VREFH = {_hex8(first_adc.vrefh_value)};",
                f"ADR = {_hex8(first_adc.adr_value)};",
            )
        ),
        "ADC_CONVERSION_WAIT_LIMIT": str(adc.conversion_wait_limit),
        "ADC_COUNTER_AND_PROTECTION_RESET": _adc_reset(plan),
        "T1CON_VALUE": _hex8(timer.t1con),
        "PWM_REGISTER_CONFIGURATION": _pwm_route_lines(plan),
        "PWM_SAFE_ZERO_DUTY": "\n".join(
            _pwm_zero_lines(plan)
        ),
        "SYSTEM_SAFE_CLOSE": "\n".join(
            (
                *_pwm_zero_lines(plan),
                "PWM_FAN = 0;",
                "FAN_ON = 0;",
            )
        ),
        "ADC_CHANNEL_SWITCH": _adc_channel_switch(plan),
        "ADC_DISCARD_ACCUMULATE_AVERAGE_AND_DISPATCH": _adc_accumulation(plan),
        "TIME_FLAG_DERIVATION": _time_flag_derivation(plan),
        "DISPLAY_STATE_TRANSITION": "",
        "INPUT_AND_POWER_STATE_NORMALIZATION": "\n".join(
            (
                "if(fan_error_flag)",
                "{",
                "    fan_mode = 0;",
                "}",
            )
        ),
        "SHARED_STATE_CONSEQUENCES": "",
        "OUTPUT_STATE_NORMALIZATION": "",
        "DISPLAY_BUFFER_BUILD": "",
        "INPUT_DEBOUNCE_AND_EVENT_GENERATION": "",
        "INPUT_EVENT_CLEAR": "",
        "DISPLAY_TIMER_RESTART": "",
        "INPUT_EVENT_CONSUMPTION": "",
        "DISPLAY_SAFE_IDLE_STATE": "",
        "DISPLAY_SCAN_BODY": "",
        "FAN_TARGET_COMPARE": _fixed_voltage_compare(plan),
        "FAN_START_RUN_STOP_AND_PROTECTION": _fan_deal(plan),
        "BATTERY_TIMER_MUTUAL_EXCLUSION": "(void)type;",
        "BATTERY_MEASUREMENT_COMPENSATION_MAPPING_AND_CHASE": "return 0;",
        "OPTIONAL_FUNCTION_DECLARATIONS": (
            "void detect_youshua_wushua(void);"
            if plan.alternate_pwm is not None
            else ""
        ),
        "OPTIONAL_FUNCTION_IMPLEMENTATIONS": _motor_detection_function(plan),
        "OUTPUT_SHUTDOWN_BEFORE_SLEEP": "\n".join(
            (
                *_pwm_zero_lines(plan),
                "PWM_FAN = 0;",
                "FAN_ON = 0;",
            )
        ),
        "SLEEP_EVENT_CLEAR": _adc_reset(plan),
        "SLEEP_GPIO_CONFIGURATION": _sleep_gpio_configuration(plan),
        "SLEEP_PERIPHERAL_SHUTDOWN": "\n".join(
            ("T1IE = 0;", "T1REN = 0;")
        ),
        "WAKE_SOURCE_CONFIGURATION": _wake_source_configuration(plan),
        "WAKE_COMMON_RESTORE": "\n".join(
            (
                "WDTE = 1;",
                "SLCON = 0;",
                "PAIE = 0;",
                "PORTA;",
                "PAIF = 0;",
            )
        ),
        "WAKE_STABILITY_GUARD": "",
        "POWER_ON_STATE_INITIALIZATION": "\n".join(
            (
                "fan_mode = 0;",
                "fan_error_flag = 0;",
            )
        ),
        "SELF_TEST_TICK_COUNT": str(config.self_test_ms // 10),
        "ADC_SCHEDULER_FLAG": (
            "adc_high_rate_flag"
            if adc.high_rate_enabled
            else _time_role_flag(plan, "core.scheduler", "adc_1ms_tick")
        ),
        "MAIN_SCHEDULER_FLAG": _time_role_flag(
            plan, "core.scheduler", "main_10ms_tick"
        ),
        "SLEEP_SCHEDULER_FLAG": _time_role_flag(
            plan, "core.scheduler", "sleep_100ms_tick"
        ),
        "SELF_TEST_OUTPUT_INITIALIZATION": "",
        "SELF_TEST_FIXED_TICK_BODY": "",
        "POST_SELF_TEST_RESTORE": "",
        "INPUT_EVENT_SCHEDULER": "",
        "INPUT_PROCESSING_CALLS": "",
        "OUTPUT_PROCESSING_CALLS": "AD_fan_deal();",
        "SLEEP_ELIGIBILITY_EXPRESSION": "0",
    }
    apply_classic_slots(plan, slots)
    return slots


def render_main_c(plan: GenerationPlan) -> str:
    template = CORE_TEMPLATE.read_text(encoding="utf-8")
    return _render_template(template, build_slots(plan))


def render_main_h(plan: GenerationPlan) -> str:
    guard = re.sub(r"[^A-Z0-9]+", "_", plan.config.project_name.upper())
    return (
        f"#ifndef {guard}_MAIN_H\n"
        f"#define {guard}_MAIN_H\n\n"
        '#include "hs16p2811.h"\n\n'
        "#endif\n"
    )


def plan_as_dict(plan: GenerationPlan) -> dict[str, Any]:
    return {
        "generator_version": __version__,
        "project": plan.config.project_name,
        "mcu": {
            "model": plan.config.mcu.model,
            "package": plan.config.mcu.package,
            "oscillator_hz": plan.config.mcu.oscillator_hz,
            "system_divider": plan.config.mcu.system_divider,
            "fcpu_hz": plan.config.mcu.fcpu_hz,
        },
        "resolved_pins": plan.resolved_pins,
        "timer1": {
            "source_hz": plan.timer.source_hz,
            "prescaler": plan.timer.prescaler,
            "timer_hz": plan.timer.timer_hz,
            "target_us": plan.timer.target_us,
            "count": plan.timer.count,
            "reload_value": plan.timer.reload_value,
            "t1con": plan.timer.t1con,
            "actual_us": plan.timer.actual_us,
            "subticks_per_ms": plan.timer.subticks_per_ms,
        },
        "time_resources": {
            "base_period_ms": plan.time_resources.base_period_ms,
            "signals": [
                {
                    "period_ms": signal.period_ms,
                    "parent_period_ms": signal.parent_period_ms,
                    "ticks_per_period": signal.ticks_per_period,
                    "phase": signal.phase,
                    "reset_semantics": signal.reset_semantics,
                    "flag_name": signal.flag_name,
                    "counter_name": signal.counter_name,
                    "request_roles": list(signal.request_roles),
                    "internal": signal.internal,
                }
                for signal in plan.time_resources.signals
            ],
            "role_flags": plan.time_resources.role_flags,
            "role_counters": plan.time_resources.role_counters,
        },
        "pwm": {
            "motor_kind": plan.config.motor.kind,
            "role": plan.pwm.role,
            "timer": plan.pwm.timer,
            "gpio": plan.pwm.gpio_name,
            "channel": plan.pwm.channel,
            "route_register": plan.pwm.route_register,
            "route_value": plan.pwm.route_mask,
            "clock_source": plan.pwm.clock_source,
            "source_hz": plan.pwm.source_hz,
            "prescaler": plan.pwm.prescaler,
            "period_register": plan.pwm.period_register,
            "target_frequency_hz": plan.config.motor.pwm_frequency_hz,
            "actual_frequency_hz": plan.pwm.actual_frequency_hz,
            "error_percent": plan.pwm.error_percent,
            "duty_base_count": plan.config.motor.duty_base_count,
            "duty_gear_divisor": plan.config.motor.duty_gear_divisor,
            "voltage_target_base": plan.config.motor.voltage_target_base,
            "voltage_target_step": plan.config.motor.voltage_target_step,
            "voltage_target_max": plan.config.motor.voltage_target_max,
            "voltage_target_mode": plan.config.motor.voltage_target_mode,
            "voltage_target_calibration_offset_mv": (
                plan.config.motor.voltage_target_calibration_offset_mv
            ),
            "voltage_target_min_mv": plan.config.motor.voltage_target_min_mv,
            "voltage_target_step_mv": plan.config.motor.voltage_target_step_mv,
            "voltage_target_max_mv": plan.config.motor.voltage_target_max_mv,
            "voltage_measurement_multiplier": (
                plan.config.motor.voltage_measurement_multiplier
            ),
            "voltage_error_window": plan.config.motor.voltage_error_window,
            "voltage_pwm_min_count": plan.config.motor.voltage_pwm_min_count,
            "voltage_pwm_max_count": plan.config.motor.voltage_pwm_max_count,
            "complete_7_3_cycles_per_adc_update": (
                plan.adc.channel_scan_cycle_us
                * len(plan.adc.channels)
                // plan.adc.sample_period_us
                // 8
                if plan.config.motor.kind
                in (
                    "brushless_fixed_voltage_7_3",
                    "brushed_brushless_compat_fixed_voltage_7_3",
                )
                else None
            ),
            "alternate": (
                {
                    "role": plan.alternate_pwm.role,
                    "timer": plan.alternate_pwm.timer,
                    "gpio": plan.alternate_pwm.gpio_name,
                    "channel": plan.alternate_pwm.channel,
                    "route_register": plan.alternate_pwm.route_register,
                    "route_value": plan.alternate_pwm.route_mask,
                    "period_register": plan.alternate_pwm.period_register,
                    "target_frequency_hz": (
                        plan.config.motor.brushed_pwm_frequency_hz
                    ),
                    "actual_frequency_hz": (
                        plan.alternate_pwm.actual_frequency_hz
                    ),
                }
                if plan.alternate_pwm is not None
                else None
            ),
            "auxiliary": [
                {
                    "owner": item.owner,
                    "role": item.role,
                    "timer": item.timer,
                    "gpio": item.gpio_name,
                    "channel": item.channel,
                    "route_register": item.route_register,
                    "route_value": item.route_mask,
                    "period_register": item.period_register,
                    "target_frequency_hz": request.target_frequency_hz,
                    "actual_frequency_hz": item.actual_frequency_hz,
                    "error_percent": item.error_percent,
                }
                for item in plan.auxiliary_pwm
                for request in plan.requests.pwm
                if request.owner == item.owner
            ],
        },
        "fan_voltage_protection": {
            "enabled": plan.config.fan_protection.enabled,
            "adc_reference": plan.config.fan_protection.adc_reference,
            "voltage_mv": (
                plan.config.fan_protection.overvoltage_voltage_mv
            ),
            "divider_high_ohm": (
                plan.config.fan_protection.divider_high_ohm
            ),
            "divider_low_ohm": (
                plan.config.fan_protection.divider_low_ohm
            ),
            "adc_threshold": (
                plan.config.fan_protection.overvoltage_adc_threshold
            ),
            "confirmations": (
                plan.config.fan_protection.consecutive_confirmations
            ),
        },
        "adc": {
            "discard_samples": plan.adc.discard_samples,
            "average_samples": plan.adc.average_samples,
            "sample_period_us": plan.adc.sample_period_us,
            "channel_scan_cycle_us": plan.adc.channel_scan_cycle_us,
            "high_rate_enabled": plan.adc.high_rate_enabled,
            "high_rate_samples_per_channel": (
                plan.adc.high_rate_samples_per_channel
            ),
            "high_rate_valid_samples": plan.adc.high_rate_valid_samples,
            "high_rate_group_size": plan.adc.high_rate_group_size,
            "high_rate_group_count": plan.adc.high_rate_group_count,
            "conversion_wait_limit": plan.adc.conversion_wait_limit,
            "maximum_first_stage_accumulation": (
                4095
                * (
                    plan.adc.high_rate_group_size
                    if plan.adc.high_rate_enabled
                    else plan.adc.average_samples
                )
            ),
            "scan_cycle_ms": plan.adc.scan_cycle_ms,
            "channels": [
                {
                    "source_kind": channel.source_kind,
                    "source_name": channel.source_name,
                    "physical_pin": channel.physical_pin,
                    "gpio": channel.gpio_name,
                    "channel": channel.channel,
                    "adpcon_register": channel.adpcon_register,
                    "adpcon_mask": channel.adpcon_mask,
                    "adm_value": channel.adm_value,
                    "vrefh_value": channel.vrefh_value,
                    "adr_value": channel.adr_value,
                    "secondary_average_samples": (
                        channel.secondary_average_samples
                    ),
                    "result_mode": channel.result_mode,
                    "ready_flag_names": list(channel.ready_flag_names),
                    "result_update_ms": (
                        plan.adc.scan_cycle_ms
                        * channel.secondary_average_samples
                    ),
                    "result_name": channel.result_name,
                    "request_roles": list(channel.request_roles),
                    "scan_order": channel.scan_order,
                    "reset_semantics": channel.reset_semantics,
                }
                for channel in plan.adc.channels
            ],
            "role_results": plan.adc.role_results,
        },
        "gpio_registers": {
            "PORTA": plan.gpio.porta,
            "PORTC": plan.gpio.portc,
            "TRISA": plan.gpio.trisa,
            "TRISC": plan.gpio.trisc,
            "PAHCON": plan.gpio.pahcon,
            "PADCON": plan.gpio.padcon,
            "PCHCON": plan.gpio.pchcon,
            "PCDCON": plan.gpio.pcdcon,
            "runtime_change_mask_a": plan.gpio.runtime_change_mask_a,
            "ADPCON": plan.gpio.adpcon,
            "ADPCON1": plan.gpio.adpcon1,
            "sleep": {
                "PORTA": plan.gpio.sleep_porta,
                "PORTC": plan.gpio.sleep_portc,
                "TRISA": plan.gpio.sleep_trisa,
                "TRISC": plan.gpio.sleep_trisc,
                "PAHCON": plan.gpio.sleep_pahcon,
                "PADCON": plan.gpio.sleep_padcon,
                "PCHCON": plan.gpio.sleep_pchcon,
                "PCDCON": plan.gpio.sleep_pcdcon,
                "WUACON": plan.gpio.wake_mask_a,
            },
            "zero_battery_sleep": {
                "enabled": plan.gpio.has_zero_battery_sleep_override,
                "PORTA": plan.gpio.zero_battery_sleep_porta,
                "PORTC": plan.gpio.zero_battery_sleep_portc,
                "TRISA": plan.gpio.zero_battery_sleep_trisa,
                "TRISC": plan.gpio.zero_battery_sleep_trisc,
                "PAHCON": plan.gpio.zero_battery_sleep_pahcon,
                "PADCON": plan.gpio.zero_battery_sleep_padcon,
                "PCHCON": plan.gpio.zero_battery_sleep_pchcon,
                "PCDCON": plan.gpio.zero_battery_sleep_pcdcon,
                "WUACON": plan.gpio.zero_battery_wake_mask_a,
            },
        },
        "resource_requests": {
            "gpio": [
                {
                    "owner": item.owner,
                    "role": item.role,
                    "physical_pin": item.physical_pin,
                    "mode": item.mode,
                    "initial_level": item.initial_level,
                    "pull": item.pull,
                    "wake": item.wake,
                    "runtime_change": item.runtime_change,
                    "sleep_mode": item.sleep_mode,
                    "sleep_level": item.sleep_level,
                    "sleep_pull": item.sleep_pull,
                    "zero_battery_sleep_mode": (
                        item.zero_battery_sleep_mode
                    ),
                    "zero_battery_sleep_level": (
                        item.zero_battery_sleep_level
                    ),
                    "zero_battery_sleep_pull": (
                        item.zero_battery_sleep_pull
                    ),
                    "zero_battery_wake": item.zero_battery_wake,
                }
                for item in plan.requests.gpio
            ],
            "pwm": [
                {
                    "owner": item.owner,
                    "role": item.role,
                    "physical_pin": item.physical_pin,
                    "target_frequency_hz": item.target_frequency_hz,
                }
                for item in plan.requests.pwm
            ],
            "adc": [
                {
                    "owner": item.owner,
                    "role": item.role,
                    "source_kind": item.source_kind,
                    "physical_pin": item.physical_pin,
                    "reference": item.reference,
                    "clock": item.clock,
                    "discard_samples": item.discard_samples,
                    "average_samples": item.average_samples,
                    "secondary_average_samples": item.secondary_average_samples,
                    "result_mode": item.result_mode,
                    "result_name": item.result_name,
                    "ready_flag_name": item.ready_flag_name,
                }
                for item in plan.requests.adc
            ],
            "time": [
                {
                    "owner": item.owner,
                    "role": item.role,
                    "period_ms": item.period_ms,
                    "phase": item.phase,
                    "reset_semantics": item.reset_semantics,
                }
                for item in plan.requests.time
            ],
        },
        "classic_product": {
            "enabled": plan.config.classic_product.enabled,
            "input_kind": plan.config.classic_product.input_kind,
            "gear_mode": plan.config.classic_product.gear_mode,
            "gear_steps": list(plan.config.classic_product.gear_steps),
            "minimum_gear": plan.config.classic_product.minimum_gear,
            "maximum_gear": plan.config.classic_product.maximum_gear,
            "long_adjust": plan.config.classic_product.long_adjust,
            "charging_kind": plan.config.classic_product.charging_kind,
            "cooling_enabled": plan.config.cooling.enabled,
            "charge_max_gear": (
                plan.config.classic_product.charge_max_gear
            ),
            "display_hardware": plan.config.classic_product.display_hardware,
            "display_policy": plan.config.classic_product.display_policy,
            "low_blink_target": plan.config.classic_product.low_blink_target,
            "charge_blink_target": (
                plan.config.classic_product.charge_blink_target
            ),
            "sleep_enabled": plan.config.classic_product.sleep_enabled,
        },
        "charging": {
            "enabled": plan.config.charging.enabled,
            "kind": plan.config.charging.kind,
        },
        "cooling": {
            "enabled": plan.config.cooling.enabled,
            "presence_detection": (
                plan.config.cooling.presence_detection
            ),
            "control_mode": plan.config.cooling.control_mode,
            "allow_while_charging": (
                plan.config.cooling.allow_while_charging
            ),
        },
        "light": {
            "enabled": plan.config.light.enabled,
            "presence_detection": plan.config.light.presence_detection,
            "mode_profile": plan.config.light.mode_profile,
        },
        "atomizer": {
            "enabled": plan.config.atomizer.enabled,
            "pwm_frequency_hz": (
                plan.config.atomizer.pwm_frequency_hz
            ),
            "duty_percent": plan.config.atomizer.duty_percent,
            "dependency": plan.config.atomizer.dependency,
            "allow_while_charging": (
                plan.config.atomizer.allow_while_charging
            ),
        },
        "display": {
            "enabled": plan.config.display.enabled,
            "profile": plan.config.display.profile,
            "drive_mode": plan.config.display.drive_mode,
            "pin_count": plan.config.display.pin_count,
            "behavior_profile": plan.config.display.behavior_profile,
            "gear_event_ms": plan.config.display.gear_event_ms,
            "normal_battery_preview_ms": (
                plan.config.display.normal_battery_preview_ms
            ),
            "normal_idle_page": plan.config.display.normal_idle_page,
            "charging_idle_page": (
                plan.config.display.charging_idle_page
            ),
            "connections": [
                {
                    "signal": item.signal,
                    "positive": item.positive_pin_index,
                    "negative": item.negative_pin_index,
                }
                for item in plan.config.display.connections
            ],
        },
        "ad_key": {
            "enabled": plan.config.ad_key.enabled,
            "adc_reference": plan.config.ad_key.adc_reference,
            "adc_clock": plan.config.ad_key.adc_clock,
            "discard_samples": plan.config.ad_key.discard_samples,
            "average_samples": plan.config.ad_key.average_samples,
            "threshold_profile": plan.config.ad_key.threshold_profile,
            "double_click_ms": plan.config.ad_key.double_click_ms,
            "keys": [
                {
                    "name": item.name,
                    "min": item.minimum_adc,
                    "max": item.maximum_adc,
                    "short_action": item.short_action,
                    "double_action": item.double_action,
                    "long_action": item.long_action,
                }
                for item in plan.config.ad_key.key_bands
            ],
        },
        "digital_key": {
            "enabled": plan.config.digital_key.enabled,
            "double_click_ms": plan.config.digital_key.double_click_ms,
            "keys": [
                {
                    "name": item.name,
                    "short_action": item.short_action,
                    "double_action": item.double_action,
                    "long_action": item.long_action,
                }
                for item in plan.config.digital_key.keys
            ],
        },
        "slide_switch": {
            "enabled": plan.config.slide_switch.enabled,
            "active_level": plan.config.slide_switch.active_level,
            "pull": plan.config.slide_switch.pull,
            "zero_battery_disable_pull_wake": (
                plan.config.slide_switch.zero_battery_disable_pull_wake
            ),
        },
        "encoder": {
            "enabled": plan.config.encoder.enabled,
            "pull": plan.config.encoder.pull,
            "filter_us": plan.config.encoder.filter_us,
            "clockwise_increases": (
                plan.config.encoder.clockwise_increases
            ),
            "normal_step": plan.config.encoder.normal_step,
            "acceleration_window_ms": (
                plan.config.encoder.acceleration_window_ms
            ),
            "acceleration_events": (
                plan.config.encoder.acceleration_events
            ),
            "accelerated_step": plan.config.encoder.accelerated_step,
        },
        "slide_resistor": {
            "enabled": plan.config.slide_resistor.enabled,
            "adc_reference": plan.config.slide_resistor.adc_reference,
            "adc_clock": plan.config.slide_resistor.adc_clock,
            "discard_samples": (
                plan.config.slide_resistor.discard_samples
            ),
            "accumulation_samples": (
                plan.config.slide_resistor.accumulation_samples
            ),
            "low_gear_adc_sum": (
                plan.config.slide_resistor.low_gear_adc_sum
            ),
            "high_gear_adc_sum": (
                plan.config.slide_resistor.high_gear_adc_sum
            ),
            "low_gear_at_high_adc": (
                plan.config.slide_resistor.low_gear_at_high_adc
            ),
            "deadband_gears": (
                plan.config.slide_resistor.deadband_gears
            ),
            "confirmation_count": (
                plan.config.slide_resistor.confirmation_count
            ),
            "supply_active_level": (
                plan.config.slide_resistor.supply_active_level
            ),
        },
        "scope": {
            "production_ready": False,
            "complete_classic_profile": plan.config.classic_product.enabled,
            "implemented": [
                "strict JSON configuration",
                "HS16P2811 SOP16 pin capability resolution",
                "GPIO/T1/T3PWM/T4PWM planning",
                "multi-channel ADC aggregation and mature grouped scan",
                "module-driven layered time-resource planning",
                "pin and capability conflict rejection",
                (
                    "mature pure brushed fixed-duty PWM branch"
                    if plan.config.motor.kind == "brushed_fixed_duty"
                    else "fixed-duty brushless startup/shutdown skeleton"
                ),
                *(
                    ["AD_FAN u16 accumulation overflow check"]
                    if plan.config.fan_protection.enabled
                    else []
                ),
                *(
                    [
                        (
                            "mature slide-resistor gear input with a "
                            "single active-low power key"
                            if plan.config.slide_resistor.enabled
                            else (
                                (
                                    f"{len(plan.config.ad_key.key_bands)} "
                                    "AD-key ranges feeding mature active-low "
                                    "key event paths"
                                )
                                if plan.config.classic_product.input_kind
                                in (
                                    "two_ad_keys_active_low_ranges",
                                    "ad_keys_active_low_ranges",
                                )
                                else (
                                    "mature full-cycle rotary encoder gear input"
                                    if plan.config.encoder.enabled
                                    else (
                                        "two configurable active-low digital "
                                        "key event paths"
                                        if plan.config.digital_key.enabled
                                        else (
                                            "two active-low digital key "
                                            "event paths"
                                        )
                                    )
                                )
                            )
                        ),
                        (
                            "charging state normalization: "
                            f"{plan.config.charging.kind}"
                        ),
                        *(
                            [
                                "cooling presence detection, fan dependency "
                                "and configurable charging policy"
                            ]
                            if plan.config.cooling.enabled
                            else []
                        ),
                        *(
                            [
                                "optional LED presence detection and "
                                f"{plan.config.light.mode_profile} light mode"
                            ]
                            if plan.config.light.enabled
                            else []
                        ),
                        *(
                            [
                                "fixed-duty atomizer PWM with deterministic "
                                "Timer3/Timer4 coexistence planning"
                            ]
                            if plan.config.atomizer.enabled
                            else []
                        ),
                        (
                            "configurable charlieplex 188 display scan: "
                            f"{plan.config.display.profile}"
                        ),
                        "atomic display-buffer updates",
                        "mature segmented battery mapping and timed chase",
                        "production-style sleep/wake resource generation",
                        *(
                            [
                                (
                                    "active-low slide-switch power control "
                                    "with zero-battery pull/wake isolation"
                                )
                            ]
                            if plan.config.slide_switch.enabled
                            else []
                        ),
                        *(
                            [
                                (
                                    "mature full-cycle rotary encoder input "
                                    "with independent acceleration window"
                                ),
                                (
                                    "encoder-A-only runtime port-change "
                                    "interrupt planning"
                                ),
                            ]
                            if plan.config.encoder.enabled
                            else []
                        ),
                        *(
                            [
                                "mature self-test brushed/brushless detection",
                                "separate brushed and brushless PWM paths",
                                "separate brushed and brushless battery compensation",
                            ]
                            if plan.alternate_pwm is not None
                            else []
                        ),
                    ]
                    if plan.config.classic_product.enabled
                    else []
                ),
            ],
            "not_implemented": (
                [
                    *(
                        []
                        if (
                            plan.alternate_pwm is not None
                            or plan.config.motor.kind
                            == "brushed_fixed_duty"
                        )
                        else ["brushed and compatibility-detection variants"]
                    ),
                    *(
                        (
                            ["AD-key and encoder product profiles"]
                            if plan.config.slide_resistor.enabled
                            else (
                                [
                                    "digital/AD-key and slide-resistor "
                                    "product profiles"
                                ]
                                if plan.config.encoder.enabled
                                else (
                                    [
                                        "encoder and slide-resistor "
                                        "product profiles"
                                    ]
                                    if plan.config.classic_product.input_kind
                                    in (
                                        "two_ad_keys_active_low_ranges",
                                        "ad_keys_active_low_ranges",
                                    )
                                    else [
                                        (
                                            "AD-key, encoder and "
                                            "slide-resistor product profiles"
                                        )
                                    ]
                                )
                            )
                        )
                    ),
                    *(
                        ["slide-switch product profile"]
                        if not plan.config.slide_switch.enabled
                        else []
                    ),
                    "other display behavior policies",
                    *(
                        ["mist module"]
                        if not plan.config.atomizer.enabled
                        else []
                    ),
                    "RGB, PWM light and communication modules",
                ]
                if plan.config.classic_product.enabled
                else [
                    "product input mapping",
                    "battery and charging business logic",
                    "display hardware and behavior modules",
                    "production sleep/wake policy",
                    "brushed and compatibility-detection variants",
                ]
            ),
        },
    }


def render_report(plan: GenerationPlan) -> str:
    data = plan_as_dict(plan)
    pwm = data["pwm"]
    timer = data["timer1"]
    time_resources = data["time_resources"]
    adc = data["adc"]
    protection = data["fan_voltage_protection"]
    pins = data["resolved_pins"]
    ad_key = data["ad_key"]
    digital_key = data["digital_key"]
    slide_switch = data["slide_switch"]
    encoder = data["encoder"]
    slide_resistor = data["slide_resistor"]
    charging = data["charging"]
    cooling = data["cooling"]
    light = data["light"]
    atomizer = data["atomizer"]
    display = data["display"]
    classic = plan.config.classic_product.enabled
    classic_config = data["classic_product"]
    status = (
        "complete classic profile; compiler and bench validation required"
        if classic
        else "initial reviewed hardware-resource demo"
    )
    pin_lines = tuple(
        (
            f"- `{role}`: physical pin "
            f"{plan.config.pins[role]} "
            f"-> `{gpio}`"
        )
        for role, gpio in sorted(pins.items())
    )
    compatible = plan.alternate_pwm is not None
    deliberate_limits = (
        (
            "- This profile generates complete classic product behavior, but it is not declared production-ready without the target compiler and bench validation.",
            *(
                (
                    "- Brushed/brushless auto-detection follows the mature self-test pull-up probe, but both hardware variants still require bench validation.",
                )
                if compatible
                else (
                    "- Brushed/brushless auto-detection is not part of this fixed-motor profile.",
                )
            ),
            *(
                (
                    "- Atomizer PWM is generated from the configured "
                    "frequency, duty and dependency policy.",
                )
                if atomizer["enabled"]
                else ("- Mist/atomizer control is not part of this profile.",)
            ),
            "- RGB, PWM light and communication modules are not part of this profile.",
            *(
                ()
                if slide_switch["enabled"]
                else (
                    "- Active-low slide-switch power control is not part of "
                    "this profile.",
                )
            ),
            "- Battery thresholds, load compensation and chase periods are explicit product calibration parameters and still require the selected cell/load discharge curve.",
        )
        if classic
        else (
            "- AD-key and battery options currently generate acquisition results only; product behavior is not implemented.",
            "- No key event, encoder, slide resistor behavior, display, charge, or cooling module.",
            "- Sleep is disabled by the generated eligibility expression.",
            "- The generated fan defaults off and has no product input path to turn it on.",
            "- These limits prevent the initial generator from pretending to produce a complete product.",
        )
    )
    return "\n".join(
        (
            f"# FanForge generation report: {plan.config.project_name}",
            "",
            "## Scope",
            "",
            f"- Generator version: `{__version__}`",
            f"- Status: {status}",
            "- Production-ready: no",
            "- Core template: fixed internal `hs2811_fan_core.c.in`",
            "- Source previews: `main.c.in` and `main.h.in`",
            "",
            "## Resolved pins",
            "",
            *pin_lines,
            "",
            "## Timer1",
            "",
            f"- Fcpu: `{plan.config.mcu.fcpu_hz} Hz`",
            (
                "- Required HSIDE/programmer system-divider setting: "
                f"`/{plan.config.mcu.system_divider}`"
            ),
            "- Runtime code selects high-speed mode with `OSCM = 0x00`; the system divider is not an `OSCM` field.",
            f"- Prescaler: `{timer['prescaler']}`",
            f"- Reload: `0x{timer['reload_value']:04X}`",
            f"- `T1CON`: `0x{timer['t1con']:02X}`",
            f"- Actual interrupt: `{timer['actual_us']:.6f} us`",
            (
                "- `time_1ms_flag` is produced directly by each T1 interrupt."
                if timer["subticks_per_ms"] == 1
                else (
                    "- `time_1ms_flag` is produced after "
                    f"`{timer['subticks_per_ms']}` T1 interrupts."
                )
            ),
            "",
            "## Generated time resources",
            "",
            *(
                (
                    f"- `{item['period_ms']}ms`: "
                    f"flag=`{item['flag_name'] or '-'}`, "
                    f"counter=`{item['counter_name'] or '-'}`, "
                    f"parent=`{str(item['parent_period_ms']) + 'ms' if item['parent_period_ms'] is not None else '-'}`, "
                    f"ticks=`{item['ticks_per_period']}`, "
                    f"internal=`{str(item['internal']).lower()}`"
                )
                for item in time_resources["signals"]
            ),
            "",
            "## Fan PWM",
            "",
            (
                f"- Route: `{pwm['gpio']}` -> "
                f"`{pwm['timer']}PWM"
                f"{pwm['channel'] if pwm['timer'] == 'T3' else ''}`"
            ),
            f"- Route register: `{pwm['route_register']} = 0x{pwm['route_value']:02X}`",
            f"- {pwm['timer']} clock source: `{pwm['clock_source']}`",
            f"- {pwm['timer']} prescaler: `{pwm['prescaler']}`",
            f"- Period register: `{pwm['period_register']}`",
            f"- Target: `{pwm['target_frequency_hz']} Hz`",
            f"- Actual: `{pwm['actual_frequency_hz']:.6f} Hz`",
            f"- Error: `{pwm['error_percent']:.6f}%`",
            *(
                (
                    f"- Duty curve: `{pwm['duty_base_count']} + fan_mode / {pwm['duty_gear_divisor']}` counts",
                )
                if classic and pwm["duty_base_count"] is not None
                else ()
            ),
            *(
                (
                    "- Fixed-voltage control: mature 7+3 fractional PWM.",
                    (
                        "- Effective AD targets: "
                        f"min=`{pwm['voltage_target_base']}`, "
                        f"step=`{pwm['voltage_target_step']}`, "
                        f"max=`{pwm['voltage_target_max']}`."
                    ),
                    (
                        "- Target mode/calibration: "
                        f"`{pwm['voltage_target_mode']}`, "
                        f"offset=`{pwm['voltage_target_calibration_offset_mv']}mV`."
                    ),
                    (
                        "- Feedback error window: "
                        f"`{pwm['voltage_error_window']}` multiplied-ADC units."
                    ),
                    (
                        "- PWM range: "
                        f"`{pwm['voltage_pwm_min_count']}.."
                        f"{pwm['voltage_pwm_max_count']}` counts."
                    ),
                    (
                        "- Complete 7+3 cycles per AD_FAN update: "
                        f"`{pwm['complete_7_3_cycles_per_adc_update']}`."
                    ),
                )
                if pwm["motor_kind"]
                in (
                    "brushless_fixed_voltage_7_3",
                    "brushed_brushless_compat_fixed_voltage_7_3",
                )
                else ()
            ),
            *(
                (
                    (
                        "- Brushed alternate route: "
                        f"`{pwm['alternate']['gpio']}` -> "
                        f"`{pwm['alternate']['timer']}PWM"
                        f"{pwm['alternate']['channel'] if pwm['alternate']['timer'] == 'T3' else ''}`, "
                        f"target `{pwm['alternate']['target_frequency_hz']} Hz`, "
                        f"actual "
                        f"`{pwm['alternate']['actual_frequency_hz']:.6f} Hz`."
                    ),
                    "- Motor-type polarity: `YOUSHUA_WUSHUA=0` brushless, `1` brushed.",
                )
                if pwm["alternate"] is not None
                else ()
            ),
            *(
                tuple(
                    (
                        "- Auxiliary PWM: "
                        f"`{item['role']}` on `{item['gpio']}` -> "
                        f"`{item['timer']}PWM"
                        f"{item['channel'] if item['timer'] == 'T3' else ''}`, "
                        f"target `{item['target_frequency_hz']} Hz`, "
                        f"actual `{item['actual_frequency_hz']:.6f} Hz`."
                    )
                    for item in pwm["auxiliary"]
                )
            ),
            "",
            *(
                (
                    "## AD_FAN overvoltage protection",
                    "",
                    (
                        f"- Physical limit: `{protection['voltage_mv']}mV`, "
                        f"divider `{protection['divider_high_ohm']}:"
                        f"{protection['divider_low_ohm']}`."
                        if protection["voltage_mv"] is not None
                        else (
                            "- Physical limit metadata: legacy raw ADC "
                            "threshold."
                        )
                    ),
                    (
                        "- Single AD_FAN reference: "
                        f"`{protection['adc_reference']}`, "
                        f"generated threshold: "
                        f"`{protection['adc_threshold']}`, "
                        f"confirmations: `{protection['confirmations']}`."
                    ),
                    (
                        "- Fixed-voltage regulation and the 16V guard reuse "
                        "this same completed AD_FAN average."
                    ),
                    (
                        "- The software check is supplemental; boost "
                        "hardware must still provide fast overvoltage "
                        "protection."
                    ),
                )
                if protection["enabled"]
                else (
                    "## AD_FAN overvoltage protection",
                    "",
                    (
                        "- Disabled for this pure brushed profile; no "
                        "`AD_FAN` pin, ADC channel or boost-overvoltage "
                        "counter is generated."
                    ),
                )
            ),
            "",
            "## ADC",
            "",
            f"- Channel count: `{len(adc['channels'])}`",
            f"- Sample period: `{adc['sample_period_us']}us`",
            f"- Per-channel scan cycle: `{adc['channel_scan_cycle_us']}us`",
            f"- One complete first-stage scan: `{adc['scan_cycle_ms']} ms`",
            f"- Discard samples: `{adc['discard_samples']}`",
            f"- Average samples: `{adc['average_samples']}`",
            (
                "- Fixed-voltage high-rate pipeline: "
                f"samples=`{adc['high_rate_samples_per_channel']}`, "
                f"valid=`{adc['high_rate_valid_samples']}`, "
                f"groups=`{adc['high_rate_group_size']}x"
                f"{adc['high_rate_group_count']}`."
                if adc["high_rate_enabled"]
                else "- Fixed-voltage high-rate pipeline: disabled."
            ),
            f"- Conversion wait limit: `{adc['conversion_wait_limit']}` loops",
            (
                "- Maximum first-stage u16 accumulation: "
                f"`{adc['maximum_first_stage_accumulation']}`"
            ),
            *(
                (
                    f"- `{item['result_name']}`: "
                    f"`{item['source_name']} / AIN{item['channel']}`, "
                    f"ADM=`0x{item['adm_value']:02X}`, "
                    f"VREFH=`0x{item['vrefh_value']:02X}`, "
                    f"ADR=`0x{item['adr_value']:02X}`, "
                    f"second average=`{item['secondary_average_samples']}`, "
                    f"result mode=`{item['result_mode']}`, "
                    f"result update=`{item['result_update_ms']}ms`, "
                    f"ready flags=`{','.join(item['ready_flag_names']) or '-'}`"
                )
                for item in adc["channels"]
            ),
            *(
                (
                    "",
                    "## Classic product behavior",
                    "",
                    (
                        "- Input kind: "
                        f"`{classic_config['input_kind']}`"
                    ),
                    *(
                        (
                            (
                                "- AD threshold profile: "
                                f"`{ad_key['threshold_profile']}`"
                            ),
                            *tuple(
                                f"- AD {item['name']} range: "
                                f"`{item['min']}..{item['max']}`; "
                                f"short=`{item['short_action']}`; "
                                f"double=`{item['double_action']}`; "
                                f"long=`{item['long_action']}`"
                                for item in ad_key["keys"]
                            ),
                        )
                        if classic_config["input_kind"]
                        in (
                            "two_ad_keys_active_low_ranges",
                            "ad_keys_active_low_ranges",
                        )
                        else ()
                    ),
                    *(
                        (
                            "- AD key double-click window: "
                            f"`{ad_key['double_click_ms']}ms`.",
                        )
                        if any(
                            item["double_action"] != "none"
                            for item in ad_key["keys"]
                        )
                        else ()
                    ),
                    *(
                        (
                            *tuple(
                                f"- Digital {item['name']} actions: "
                                f"short=`{item['short_action']}`; "
                                f"double=`{item['double_action']}`; "
                                f"long=`{item['long_action']}`"
                                for item in digital_key["keys"]
                            ),
                            *(
                                (
                                    "- Digital key double-click window: "
                                    f"`{digital_key['double_click_ms']}ms`.",
                                )
                                if any(
                                    item["double_action"] != "none"
                                    for item in digital_key["keys"]
                                )
                                else ()
                            ),
                        )
                        if digital_key["enabled"]
                        else ()
                    ),
                    *(
                        (
                            "- Slide switch: active-low with internal pull-up.",
                            (
                                "- Zero-battery sleep disables the slide-switch "
                                "pull-up and wake source."
                            ),
                        )
                        if slide_switch["enabled"]
                        else ()
                    ),
                    *(
                        (
                            "- Encoder: mature full-cycle A-edge validation; "
                            "only phase A enables the runtime Port A change "
                            "interrupt.",
                            (
                                "- Encoder filter/normal/accelerated steps: "
                                f"`{encoder['filter_us']}us` / "
                                f"`{encoder['normal_step']}` / "
                                f"`{encoder['accelerated_step']}`."
                            ),
                            (
                                "- Encoder acceleration window/events: "
                                f"`{encoder['acceleration_window_ms']}ms` / "
                                f"`{encoder['acceleration_events']}`."
                            ),
                        )
                        if encoder["enabled"]
                        else ()
                    ),
                    *(
                        (
                            (
                                "- Slider ADC endpoints (first/max gear): "
                                f"`{slide_resistor['low_gear_adc_sum']}` / "
                                f"`{slide_resistor['high_gear_adc_sum']}`."
                            ),
                            (
                                "- Slider accumulation/deadband/confirmation: "
                                f"`{slide_resistor['accumulation_samples']}` / "
                                f"`{slide_resistor['deadband_gears']}` gears / "
                                f"`{slide_resistor['confirmation_count']}` "
                                "complete ADC results."
                            ),
                            (
                                "- Slider supply: active "
                                f"`{slide_resistor['supply_active_level']}`, "
                                "forced low during sleep."
                            ),
                        )
                        if slide_resistor["enabled"]
                        else ()
                    ),
                    (
                        (
                            (
                                "- Slider gear range: `"
                                if slide_resistor["enabled"]
                                else "- Encoder gear range: `"
                            )
                            + f"{classic_config['minimum_gear']} -> "
                            + f"{classic_config['maximum_gear']}`"
                        )
                        if classic_config["gear_mode"] == "continuous"
                        else (
                            "- Short-press gear sequence: `"
                            + " -> ".join(
                                str(item)
                                for item in classic_config["gear_steps"]
                            )
                            + (
                                " -> first gear`"
                                if slide_switch["enabled"]
                                else " -> 0`"
                            )
                        )
                    ),
                    (
                        "- Long continuous adjustment: "
                        f"`{str(classic_config['long_adjust']).lower()}`"
                    ),
                    (
                        "- Charging maximum gear: "
                        f"`{classic_config['charge_max_gear']}`"
                    ),
                    (
                        "- Charging interface enabled/kind: "
                        f"`{str(charging['enabled']).lower()}` / "
                        f"`{charging['kind']}`"
                    ),
                    (
                        "- Display hardware/pins/drive: "
                        f"`{display['profile']}` / "
                        f"`{display['pin_count']}` / "
                        f"`{display['drive_mode']}`"
                    ),
                    (
                        "- Display mapped signals: "
                        f"`{len(display['connections'])}`"
                    ),
                    (
                        "- Display policy: "
                        f"`{classic_config['display_policy']}`"
                    ),
                    (
                        "- Display behavior profile: "
                        f"`{display['behavior_profile']}`"
                    ),
                    (
                        "- Gear event/battery preview periods: "
                        f"`{display['gear_event_ms']}ms` / "
                        f"`{display['normal_battery_preview_ms']}ms`"
                    ),
                    (
                        "- Normal/charging idle pages: "
                        f"`{display['normal_idle_page']}` / "
                        f"`{display['charging_idle_page']}`"
                    ),
                    (
                        "- Low/charge blink targets: "
                        f"`{classic_config['low_blink_target']}` / "
                        f"`{classic_config['charge_blink_target']}`"
                    ),
                    (
                        "- Cooling/sleep enabled: "
                        f"`{str(cooling['enabled']).lower()}` / "
                        f"`{str(classic_config['sleep_enabled']).lower()}`"
                    ),
                    (
                        "- Cooling detection/control/charging policy: "
                        f"`{str(cooling['presence_detection']).lower()}` / "
                        f"`{cooling['control_mode']}` / "
                        f"`{str(cooling['allow_while_charging']).lower()}`"
                    ),
                    (
                        "- Light enabled/detection/mode: "
                        f"`{str(light['enabled']).lower()}` / "
                        f"`{str(light['presence_detection']).lower()}` / "
                        f"`{light['mode_profile']}`"
                    ),
                    (
                        "- Atomizer enabled/frequency/duty/dependency/"
                        "charging: "
                        f"`{str(atomizer['enabled']).lower()}` / "
                        f"`{atomizer['pwm_frequency_hz']}Hz` / "
                        f"`{atomizer['duty_percent']}%` / "
                        f"`{atomizer['dependency']}` / "
                        f"`{str(atomizer['allow_while_charging']).lower()}`"
                    ),
                )
                if classic
                else ()
            ),
            "",
            "## Deliberate limits",
            "",
            *deliberate_limits,
            "",
        )
    )


def render_acceptance_checklist(plan: GenerationPlan) -> str:
    config = plan.config
    classic = config.classic_product
    curve = config.battery_monitor.curve
    pwm_plans = _all_pwm_plans(plan)
    gpio = plan.gpio

    lines = [
        f"# FanForge product acceptance checklist: {config.project_name}",
        "",
        "This file is generated from the resolved configuration. Checked "
        "resource items are generator-verified; unchecked items require "
        "compiler or bench confirmation.",
        "",
        "## Generated configuration",
        "",
        f"- [x] MCU/package: `{config.mcu.model}` / `{config.mcu.package}`.",
        (
            f"- [x] Oscillator/system divider/Fcpu: "
            f"`{config.mcu.oscillator_hz}Hz` / "
            f"`/{config.mcu.system_divider}` / "
            f"`{config.mcu.fcpu_hz}Hz`."
        ),
        (
            f"- [x] Timer1: `{plan.timer.actual_us:.3f}us`, "
            f"`T1CON=0x{plan.timer.t1con:02X}`, "
            f"reload=`0x{plan.timer.reload_value:04X}`."
        ),
        (
            f"- [x] Product profile: "
            f"`{'classic' if classic.enabled else 'resource-demo'}`."
        ),
        "",
        "## Pin contract",
        "",
    ]
    lines.extend(
        (
            f"- [x] `{role}`: physical pin `{config.pins[role]}` -> "
            f"`{gpio_name}`."
        )
        for role, gpio_name in sorted(plan.resolved_pins.items())
    )
    lines.extend(("", "## PWM contract", ""))
    lines.extend(
        (
            f"- [x] `{item.role}`: `{item.gpio_name}` -> "
            f"`{item.timer}PWM"
            f"{item.channel if item.timer == 'T3' else ''}`, "
            f"period=`{item.period_register}`, "
            f"actual=`{item.actual_frequency_hz:.3f}Hz`."
        )
        for item in pwm_plans
    )
    if (
        config.motor.duty_base_count is not None
        and config.motor.duty_gear_divisor is not None
    ):
        lines.append(
            "- [x] Fan duty curve: "
            f"`{config.motor.duty_base_count} + fan_mode / "
            f"{config.motor.duty_gear_divisor}` counts."
        )
    lines.extend(("", "## Motor safety contract", ""))
    lines.append(f"- [x] Motor kind: `{config.motor.kind}`.")
    if config.motor.kind == "brushed_fixed_duty":
        lines.extend(
            (
                "- [x] `FAN_ON` is the brushed PWM output.",
                "- [x] No brushless `PWM_FAN`, `AD_FAN`, boost startup "
                "sequence or 16V software guard is generated.",
            )
        )
    else:
        lines.extend(
            (
                "- [x] `AD_FAN` software protection is enabled.",
                (
                    "- [x] Overvoltage threshold/confirmations: "
                    f"`{config.fan_protection.overvoltage_adc_threshold}` / "
                    f"`{config.fan_protection.consecutive_confirmations}`."
                ),
                "- [x] Brushless startup order: `FAN_ON`, wait about 10ms, "
                "then enable `PWM_FAN`.",
                "- [x] Brushless shutdown order: disable `PWM_FAN`, wait "
                "about 10ms, then clear `FAN_ON`.",
            )
        )
    lines.extend(
        (
            "- [ ] Confirm the physical motor type and MOS/boost role of "
            "each generated output pin.",
            "- [ ] Measure minimum and maximum gear PWM/voltage with the "
            "real motor connected.",
            "- [ ] Verify motor-disconnect and running-fault behavior.",
            "",
            "## Input and action contract",
            "",
            f"- [x] Input kind: `{classic.input_kind}`.",
        )
    )
    if config.digital_key.enabled:
        lines.extend(
            (
                f"- [x] Digital {item.name}: "
                f"short=`{item.short_action}`, "
                f"double=`{item.double_action}`, "
                f"long=`{item.long_action}`."
            )
            for item in config.digital_key.keys
        )
    if config.ad_key.enabled:
        lines.extend(
            (
                f"- [x] AD {item.name}: range "
                f"`{item.minimum_adc}..{item.maximum_adc}`, "
                f"short=`{item.short_action}`, "
                f"double=`{item.double_action}`, "
                f"long=`{item.long_action}`."
            )
            for item in config.ad_key.key_bands
        )
    if config.encoder.enabled:
        lines.append(
            "- [x] Encoder normal/accelerated step and direction: "
            f"`{config.encoder.normal_step}` / "
            f"`{config.encoder.accelerated_step}` / "
            f"`clockwise_increases={str(config.encoder.clockwise_increases).lower()}`."
        )
    if config.slide_switch.enabled:
        lines.append(
            "- [x] Slide switch: "
            f"`{config.slide_switch.active_level}` active, "
            f"pull=`{config.slide_switch.pull}`."
        )
    if config.slide_resistor.enabled:
        lines.append(
            "- [x] Slide resistor ADC endpoints/deadband/confirmation: "
            f"`{config.slide_resistor.low_gear_adc_sum}` / "
            f"`{config.slide_resistor.high_gear_adc_sum}` / "
            f"`{config.slide_resistor.deadband_gears}` / "
            f"`{config.slide_resistor.confirmation_count}`."
        )
    lines.extend(
        (
            "- [ ] Verify every short, double and long action on the target "
            "key resistor/GPIO hardware.",
            "- [ ] Verify release, double-click timeout and sleep blocking.",
            "",
            "## Charging and battery contract",
            "",
            f"- [x] Charging interface: `{config.charging.kind}`.",
            (
                f"- [x] Charging maximum fan gear: "
                f"`{classic.charge_max_gear}`."
            ),
        )
    )
    if curve is not None:
        lines.extend(
            (
                (
                    "- [x] Battery ADC thresholds zero/low: "
                    f"`{curve.zero_shutdown}` / `{curve.low_threshold}`."
                ),
                (
                    "- [x] Battery curve p0/p5/p10/p50/p80/p100: "
                    f"`{curve.adc_0}` / `{curve.adc_5}` / "
                    f"`{curve.adc_10}` / `{curve.adc_50}` / "
                    f"`{curve.adc_80}` / `{curve.adc_100}`."
                ),
                (
                    "- [x] Fan load compensation: `"
                    + ", ".join(str(item) for item in curve.fan_compensation)
                    + "`."
                ),
                (
                    "- [x] Charge/full/discharge/low chase periods: "
                    f"`{curve.charge_active_period_ms}ms` / "
                    f"`{curve.charge_full_period_ms}ms` / "
                    f"`{curve.discharge_period_ms}ms` / "
                    f"`{curve.low_discharge_period_ms}ms`."
                ),
                "- [x] Non-insert discharge does not chase battery "
                "percentage upward.",
            )
        )
    lines.extend(
        (
            "- [ ] Verify charge, full, unplug and any supported discharge "
            "state truth table on the actual power IC.",
            "- [ ] Run the selected cell/load discharge curve before "
            "production.",
            "",
            "## Display and optional outputs",
            "",
            (
                f"- [x] Display profile/pins/drive: "
                f"`{config.display.profile}` / "
                f"`{config.display.pin_count}` / "
                f"`{config.display.drive_mode}`."
            ),
            (
                f"- [x] Display behavior: "
                f"`{config.display.behavior_profile}`, "
                f"gear event=`{config.display.gear_event_ms}ms`, "
                f"battery preview="
                f"`{config.display.normal_battery_preview_ms}ms`, "
                f"idle=`{config.display.normal_idle_page}`, "
                f"charging idle=`{config.display.charging_idle_page}`."
            ),
            (
                f"- [x] Cooling: enabled="
                f"`{str(config.cooling.enabled).lower()}`, "
                f"detection="
                f"`{str(config.cooling.presence_detection).lower()}`, "
                f"charging allowed="
                f"`{str(config.cooling.allow_while_charging).lower()}`."
            ),
            (
                f"- [x] LED: enabled="
                f"`{str(config.light.enabled).lower()}`, "
                f"mode=`{config.light.mode_profile}`."
            ),
            (
                f"- [x] Atomizer: enabled="
                f"`{str(config.atomizer.enabled).lower()}`, "
                f"duty=`{config.atomizer.duty_percent}%`, "
                f"dependency=`{config.atomizer.dependency}`."
            ),
            "- [ ] Verify all 188 segments/icons, full-light self-test, "
            "dark-frame ghosting and blink synchronization.",
            "- [ ] Verify cooling, LED and atomizer dependencies and "
            "charging restrictions.",
            "",
            "## Sleep and wake contract",
            "",
            (
                f"- [x] Sleep enabled: "
                f"`{str(classic.sleep_enabled).lower()}`."
            ),
            (
                f"- [x] Normal sleep registers: "
                f"`TRISA=0x{gpio.sleep_trisa:02X}`, "
                f"`TRISC=0x{gpio.sleep_trisc:02X}`, "
                f"`PAHCON=0x{gpio.sleep_pahcon:02X}`, "
                f"`PADCON=0x{gpio.sleep_padcon:02X}`, "
                f"`WUACON=0x{gpio.wake_mask_a:02X}`."
            ),
        )
    )
    if gpio.has_zero_battery_sleep_override:
        lines.append(
            "- [x] Zero-battery sleep override: "
            f"`PAHCON=0x{gpio.zero_battery_sleep_pahcon:02X}`, "
            f"`WUACON=0x{gpio.zero_battery_wake_mask_a:02X}`."
        )
    lines.extend(
        (
            "- [ ] Measure sleep current in normal-off and zero-battery "
            "states.",
            "- [ ] Verify every intended wake source and confirm unintended "
            "keys cannot wake the product.",
            "",
            "## Release gate",
            "",
            "- [ ] Compile with the target HSIDE/PICC toolchain without "
            "errors or unexpected warnings.",
            "- [ ] Record program/data-space usage and checksum.",
            "- [ ] Complete cold boot, repeated on/off, charger insert/remove "
            "and low-battery tests.",
            "- [ ] Confirm generated pin roles against schematic, PCB and "
            "package orientation.",
            "- [ ] Update project HANDOFF with calibrated values and bench "
            "results before production.",
            "",
        )
    )
    return "\n".join(lines)


def write_generation(plan: GenerationPlan, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    # Transparent encryption intercepts direct .c/.h writes from this CLI.
    (output_dir / "main.c.in").write_text(render_main_c(plan), encoding="utf-8")
    (output_dir / "main.h.in").write_text(render_main_h(plan), encoding="utf-8")
    (output_dir / "generation_report.md").write_text(
        render_report(plan), encoding="utf-8"
    )
    (output_dir / "acceptance_checklist.md").write_text(
        render_acceptance_checklist(plan), encoding="utf-8"
    )
    (output_dir / "resolved_plan.json").write_text(
        json.dumps(plan_as_dict(plan), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
