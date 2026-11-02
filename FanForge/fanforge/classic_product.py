from fanforge.errors import FanForgeError
from fanforge.models import DISPLAY_SEGMENT_BITS, GenerationPlan


AD_KEY_INPUT_KINDS = (
    "two_ad_keys_active_low_ranges",
    "ad_keys_active_low_ranges",
)


def _hex8(value: int) -> str:
    return f"0x{value & 0xFF:02X}"


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


def _atomizer_pwm(plan: GenerationPlan):
    for pwm in plan.auxiliary_pwm:
        if pwm.role == "PWM_WH":
            return pwm
    return None


def _stop_pwm_timer_lines(
    plan: GenerationPlan, pwm, indent: str = ""
) -> tuple[str, ...]:
    if not plan.auxiliary_pwm:
        return (f"{indent}{_pwm_run_symbol(pwm)} = 0;",)
    others = tuple(
        item.enable_symbol
        for item in _all_pwm_plans(plan)
        if item.timer == pwm.timer and item.enable_symbol != pwm.enable_symbol
    )
    if not others:
        return (f"{indent}{_pwm_run_symbol(pwm)} = 0;",)
    return (
        f"{indent}if(" + " && ".join(f"!{name}" for name in others) + ")",
        f"{indent}" + "{",
        f"{indent}    {_pwm_run_symbol(pwm)} = 0;",
        f"{indent}" + "}",
    )


def _uses_ad_keys(plan: GenerationPlan) -> bool:
    return plan.config.classic_product.input_kind in AD_KEY_INPUT_KINDS


def _key_action_items(plan: GenerationPlan):
    if plan.config.digital_key.enabled:
        return plan.config.digital_key.keys
    if _uses_ad_keys(plan):
        return plan.config.ad_key.key_bands
    return ()


def _uses_configurable_key_actions(plan: GenerationPlan) -> bool:
    return (
        plan.config.digital_key.enabled
        or plan.config.classic_product.input_kind
        == "ad_keys_active_low_ranges"
    )


def _active_key_names(plan: GenerationPlan) -> tuple[str, ...]:
    if _uses_ad_keys(plan) or plan.config.digital_key.enabled:
        return tuple(
            item.name
            for item in sorted(
                _key_action_items(plan),
                key=lambda item: int(item.name[3:]),
            )
        )
    return ("KEY1", "KEY2")


def _double_click_bands(plan: GenerationPlan):
    return tuple(
        item
        for item in _key_action_items(plan)
        if item.double_action != "none"
    )


def _uses_advanced_key_events(plan: GenerationPlan) -> bool:
    if not _key_action_items(plan):
        return False
    return bool(_double_click_bands(plan)) or any(
        item.long_action
        not in ("none", "fan_step_up", "fan_step_down")
        for item in _key_action_items(plan)
    )


def _double_click_timer_reset_lines(
    plan: GenerationPlan, key_name: str, indent: str = ""
) -> tuple[str, ...]:
    owner = f"input.{key_name.lower()}"
    role = "double_click_window"
    return (
        f"{indent}{_time_flag(plan, owner, role)} = 0;",
        f"{indent}{_time_counter(plan, owner, role)} = 0;",
    )


def _double_click_state_reset_lines(
    plan: GenerationPlan, indent: str = ""
) -> tuple[str, ...]:
    return tuple(
        line
        for item in _double_click_bands(plan)
        for line in (
            f"{indent}{item.name.lower()}_click_cnt = 0;",
            *_double_click_timer_reset_lines(plan, item.name, indent),
        )
    )


def _time_flag(plan: GenerationPlan, owner: str, role: str) -> str:
    key = f"{owner}.{role}"
    try:
        return plan.time_resources.role_flags[key]
    except KeyError as exc:
        raise FanForgeError(f"missing classic time flag: {key}") from exc


def _time_counter(plan: GenerationPlan, owner: str, role: str) -> str:
    key = f"{owner}.{role}"
    try:
        counter = plan.time_resources.role_counters[key]
    except KeyError as exc:
        raise FanForgeError(f"missing classic time counter: {key}") from exc
    if counter is None:
        raise FanForgeError(f"classic time resource has no counter: {key}")
    return counter


def _uses_legacy_display_behavior(plan: GenerationPlan) -> bool:
    return (
        plan.config.display.behavior_profile
        == "gear_3s_battery_3s_gear"
    )


def _display_timer_roles(plan: GenerationPlan) -> tuple[str, ...]:
    if _uses_legacy_display_behavior(plan):
        return ("page_3s",)
    roles = ["gear_event"]
    if plan.config.display.normal_battery_preview_ms:
        roles.append("battery_preview")
    return tuple(roles)


def _display_timer_reset_lines(
    plan: GenerationPlan, indent: str = ""
) -> tuple[str, ...]:
    lines: list[str] = []
    for role in _display_timer_roles(plan):
        lines.append(
            f"{indent}{_time_flag(plan, 'display.page', role)} = 0;"
        )
        lines.append(
            f"{indent}{_time_counter(plan, 'display.page', role)} = 0;"
        )
    return tuple(lines)


def _display_idle_show_mode(
    plan: GenerationPlan, inserted: bool
) -> int:
    page = (
        plan.config.display.charging_idle_page
        if inserted
        else plan.config.display.normal_idle_page
    )
    return 1 if page == "gear" else 0


def _adc_ready_flag(
    plan: GenerationPlan, owner: str, role: str
) -> str:
    key = f"{owner}.{role}"
    try:
        result_name = plan.adc.role_results[key]
    except KeyError as exc:
        raise FanForgeError(f"missing classic ADC result: {key}") from exc
    for channel in plan.adc.channels:
        if channel.result_name == result_name and channel.ready_flag_names:
            return channel.ready_flag_names[0]
    raise FanForgeError(f"classic ADC result has no ready flag: {key}")


def _gpio_direction_macro(gpio_name: str, output: bool) -> str:
    port = gpio_name[1]
    bit = int(gpio_name[2:])
    register = f"TRIS{port}"
    if output:
        return f"{register} &= {_hex8(~(1 << bit))}"
    return f"{register} |= {_hex8(1 << bit)}"


def _feature_detection_function(plan: GenerationPlan) -> str:
    probes: list[tuple[str, str]] = []
    if plan.config.cooling.presence_detection:
        probes.append(("COOL_EN", "YOUWU_COOL"))
    if plan.config.light.presence_detection:
        probes.append(("LED_ON", "YOUWU_LED"))
    if not probes:
        return ""

    lines = ["void detect_optional_features(void)", "{"]
    for role, flag_name in probes:
        gpio = plan.resolved_pins[role]
        port = gpio[1]
        bit = int(gpio[2:])
        clear_mask = _hex8(~(1 << bit))
        set_mask = _hex8(1 << bit)
        lines.extend(
            (
                f"    PORT{port} &= {clear_mask};",
                f"    TRIS{port} |= {set_mask};",
                f"    P{port}HCON &= {clear_mask};",
                "    _NOP();",
                "    _NOP();",
                "    _NOP();",
                "    _NOP();",
                f"    {flag_name} = {role} ? 0 : 1;",
                f"    P{port}HCON |= {set_mask};",
                f"    TRIS{port} &= {clear_mask};",
                f"    {role} = 0;",
            )
        )
    lines.append("}")
    return "\n".join(lines)


def _charging_state_normalization(plan: GenerationPlan) -> tuple[str, ...]:
    if plan.config.charging.kind in (
        "chrg_stdby_active_low",
        "chrg_chrg_max_active_low_static",
    ):
        full_role = (
            "STDBY"
            if plan.config.charging.kind == "chrg_stdby_active_low"
            else "CHRG_MAX"
        )
        return (
            "if(!CHRG)",
            "{",
            "    charge_on_flag = 1;",
            "    insert_flag = 1;",
            "}",
            f"else if(!{full_role})",
            "{",
            "    charge_max_flag = 1;",
            "    insert_flag = 1;",
            "}",
        )
    if (
        plan.config.charging.kind
        == "insert_active_high_chrg_active_low"
    ):
        return (
            "if(INSERT)",
            "{",
            "    insert_flag = 1;",
            "    if(!CHRG)",
            "    {",
            "        charge_on_flag = 1;",
            "    }",
            "    else",
            "    {",
            "        charge_max_flag = 1;",
            "    }",
            "}",
        )
    return ()


def _cooling_normalization(plan: GenerationPlan) -> tuple[str, ...]:
    config = plan.config.cooling
    if not config.enabled:
        return ()
    charge_guard = "" if config.allow_while_charging else " && !insert_flag"
    if config.control_mode == "follow_fan":
        return (
            "",
            f"if(YOUWU_COOL && fan_mode{charge_guard})",
            "{",
            "    COOL_EN = 1;",
            "}",
            "else",
            "{",
            "    COOL_EN = 0;",
            "}",
        )
    return (
        "",
        "if(!YOUWU_COOL || !fan_mode)",
        "{",
        "    COOL_EN = 0;",
        "}",
    )


def _light_normalization(plan: GenerationPlan) -> tuple[str, ...]:
    config = plan.config.light
    if not config.enabled:
        return ()
    if config.mode_profile == "fan_sync":
        return (
            "",
            "if(YOUWU_LED && fan_mode)",
            "{",
            "    LED_ON = 1;",
            "}",
            "else",
            "{",
            "    LED_ON = 0;",
            "}",
        )
    output_lines = (
        (
            "if(light_mode == 1)",
            "{",
            "    LED_ON = 1;",
            "}",
            "else if(light_mode == 2)",
            "{",
            "    LED_ON = time_flash_flag;",
            "}",
            "else",
            "{",
            "    LED_ON = 0;",
            "}",
        )
        if config.mode_profile == "on_off_flash"
        else (
            "LED_ON = light_mode ? 1 : 0;",
        )
    )
    return (
        "",
        "if(!YOUWU_LED || (!charge_num && !insert_flag))",
        "{",
        "    light_mode = 0;",
        "}",
        *output_lines,
    )


def _atomizer_normalization(plan: GenerationPlan) -> tuple[str, ...]:
    config = plan.config.atomizer
    if not config.enabled:
        return ()
    off_conditions = ["(!charge_num && !insert_flag)"]
    if config.dependency == "fan_required":
        off_conditions.append("!fan_mode")
    if not config.allow_while_charging:
        off_conditions.append("insert_flag")
    return (
        "",
        "if(" + " || ".join(off_conditions) + ")",
        "{",
        "    wh_mode = 0;",
        "}",
    )


def _display_pin_definitions(plan: GenerationPlan) -> str:
    if plan.config.classic_product.input_kind in (
        "two_digital_keys_active_low",
        "digital_keys_active_low",
    ):
        input_roles = _active_key_names(plan)
    elif _uses_ad_keys(plan):
        input_roles = ("AD_KEY",)
    elif (
        plan.config.classic_product.input_kind
        == "rotary_encoder_active_low"
    ):
        input_roles = ("ENC_A", "ENC_B")
    else:
        input_roles = ("KEY", "SLIDER_ON", "AD_SLIDER")
    motor_roles = (
        ("FAN_ON",)
        if plan.config.motor.kind == "brushed_fixed_duty"
        else ("PWM_FAN", "FAN_ON", "AD_FAN")
    )
    roles = (
        *motor_roles,
        *input_roles,
        *(("SWI_KEY",) if plan.config.slide_switch.enabled else ()),
        *(
            ("CHRG", "STDBY")
            if plan.config.charging.kind == "chrg_stdby_active_low"
            else ("CHRG", "CHRG_MAX")
            if (
                plan.config.charging.kind
                == "chrg_chrg_max_active_low_static"
            )
            else ("INSERT", "CHRG")
            if (
                plan.config.charging.kind
                == "insert_active_high_chrg_active_low"
            )
            else ()
        ),
        *(
            ("COOL_EN",)
            if plan.config.cooling.enabled
            else ()
        ),
        *(("LED_ON",) if plan.config.light.enabled else ()),
        *(("PWM_WH",) if plan.config.atomizer.enabled else ()),
        *(
            f"IO_LED_{index}"
            for index in range(1, plan.config.display.pin_count + 1)
        ),
    )
    lines = [
        f"#define {role:<12} {plan.resolved_pins[role]}"
        for role in roles
    ]
    lines.append("")
    for index in range(1, plan.config.display.pin_count + 1):
        gpio_name = plan.resolved_pins[f"IO_LED_{index}"]
        lines.append(
            f"#define IO_OUT_LED_{index}    "
            f"{_gpio_direction_macro(gpio_name, True)}"
        )
        lines.append(
            f"#define IO_IN_LED_{index}     "
            f"{_gpio_direction_macro(gpio_name, False)}"
        )
    return "\n".join(lines)


def _parameter_definitions(
    plan: GenerationPlan, base_motor_parameters: str
) -> str:
    config = plan.config
    curve = config.battery_monitor.curve
    if curve is None:
        raise FanForgeError("classic product is missing its battery curve")
    comp = curve.fan_compensation
    step_0_5 = (curve.adc_5 - curve.adc_0 + 3) // 4
    step_5_10 = (curve.adc_10 - curve.adc_5 + 4) // 5
    step_10_50 = (curve.adc_50 - curve.adc_10 + 39) // 40
    step_50_80 = (curve.adc_80 - curve.adc_50 + 29) // 30
    step_80_100 = (curve.adc_100 - curve.adc_80 + 19) // 20
    motor_lines = [base_motor_parameters]
    if config.motor.kind in (
        "brushless_fixed_duty",
        "brushed_fixed_duty",
    ):
        duty_base = config.motor.duty_base_count
        duty_divisor = config.motor.duty_gear_divisor
        if duty_base is None or duty_divisor is None:
            raise FanForgeError("classic product is missing its motor duty curve")
        motor_lines.extend(
            (
                f"#define FAN_PWM_DUTY_BASE     {duty_base}",
                f"#define FAN_PWM_GEAR_DIVISOR  {duty_divisor}",
            )
        )
    atomizer_pwm = _atomizer_pwm(plan)
    if config.atomizer.enabled:
        if atomizer_pwm is None:
            raise FanForgeError("atomizer PWM resource is missing")
        atomizer_duty = round(
            (atomizer_pwm.period_register + 1)
            * config.atomizer.duty_percent
            / 100
        )
        atomizer_duty = max(
            1, min(atomizer_pwm.period_register, atomizer_duty)
        )
        motor_lines.append(f"#define WH_DUTY              {atomizer_duty}")
    brush_comp_lines: tuple[str, ...] = ()
    if config.motor.kind == "brushed_brushless_compat_fixed_voltage_7_3":
        brush_comp = curve.brushed_fan_compensation
        brush_cooling = curve.brushed_cooling_compensation
        if brush_comp is None or brush_cooling is None:
            raise FanForgeError(
                "compatible classic product is missing brushed compensation"
            )
        brush_comp_lines = (
            f"#define AD_BAT_BRUSH_MODE_1   {brush_comp[0]}",
            f"#define AD_BAT_BRUSH_MODE_25  {brush_comp[1]}",
            f"#define AD_BAT_BRUSH_MODE_50  {brush_comp[2]}",
            f"#define AD_BAT_BRUSH_MODE_75  {brush_comp[3]}",
            f"#define AD_BAT_BRUSH_MODE_100 {brush_comp[4]}",
            *(
                (f"#define AD_BAT_BRUSH_MODE_COOL {brush_cooling}",)
                if config.cooling.enabled
                else ()
            ),
        )
    ad_key_lines: tuple[str, ...] = ()
    if config.classic_product.input_kind in AD_KEY_INPUT_KINDS:
        ad_key_lines = tuple(
            line
            for item in sorted(
                config.ad_key.key_bands,
                key=lambda band: int(band.name[3:]),
            )
            for line in (
                f"#define AD_{item.name}_MIN           {item.minimum_adc}",
                f"#define AD_{item.name}_MAX           {item.maximum_adc}",
            )
        )
    encoder_lines: tuple[str, ...] = ()
    if config.encoder.enabled:
        filter_ticks = (
            (
                config.encoder.filter_us
                + config.timebase.interrupt_us
                - 1
            )
            // config.timebase.interrupt_us
            + 1
        )
        if filter_ticks > 255:
            raise FanForgeError("encoder filter needs more than 255 T1 ticks")
        encoder_lines = (
            f"#define ENCODER_FILTER_TICKS  {filter_ticks}",
            f"#define ENCODER_NORMAL_STEP   {config.encoder.normal_step}",
            (
                "#define ENCODER_ACCEL_EVENTS  "
                f"{config.encoder.acceleration_events}"
            ),
            (
                "#define ENCODER_ACCEL_STEP    "
                f"{config.encoder.accelerated_step}"
            ),
        )
    slider_lines: tuple[str, ...] = ()
    if config.slide_resistor.enabled:
        slider_range = abs(
            config.slide_resistor.low_gear_adc_sum
            - config.slide_resistor.high_gear_adc_sum
        )
        slider_gear_count = (
            config.classic_product.maximum_gear
            - config.classic_product.minimum_gear
        )
        slider_step = slider_range // slider_gear_count
        slider_deadband = (
            slider_step * config.slide_resistor.deadband_gears
        )
        slider_lines = (
            (
                "#define ADC_SLIDER_MIN_GEAR    "
                f"{config.slide_resistor.low_gear_adc_sum}UL"
            ),
            (
                "#define ADC_SLIDER_MAX_GEAR    "
                f"{config.slide_resistor.high_gear_adc_sum}UL"
            ),
            f"#define ADC_RANGE              {slider_range}UL",
            f"#define ADC_STEP               {slider_step}",
            (
                "#define ADC_TRIGGER_GEARS      "
                f"{config.slide_resistor.deadband_gears}"
            ),
            f"#define ADC_DEADBAND           {slider_deadband}UL",
            (
                "#define ADC_CONFIRM_COUNT      "
                f"{config.slide_resistor.confirmation_count}"
            ),
        )
    return "\n".join(
        (
            *motor_lines,
            f"#define FAN_MODE_MIN          {config.classic_product.minimum_gear}",
            f"#define FAN_MODE_MAX          {config.classic_product.maximum_gear}",
            f"#define CHARGE_MAX_GEAR       {config.classic_product.charge_max_gear}",
            "",
            f"#define AD_BAT_ZERO           {curve.zero_shutdown}",
            f"#define AD_BAT_LOW            {curve.low_threshold}",
            f"#define AD_BAT_0              {curve.adc_0}",
            f"#define AD_BAT_5              {curve.adc_5}",
            f"#define AD_BAT_10             {curve.adc_10}",
            f"#define AD_BAT_50             {curve.adc_50}",
            f"#define AD_BAT_80             {curve.adc_80}",
            f"#define AD_BAT_100            {curve.adc_100}",
            f"#define AD_BAT_STEP_0_5       {step_0_5}",
            f"#define AD_BAT_STEP_5_10      {step_5_10}",
            f"#define AD_BAT_STEP_10_50     {step_10_50}",
            f"#define AD_BAT_STEP_50_80     {step_50_80}",
            f"#define AD_BAT_STEP_80_100    {step_80_100}",
            f"#define AD_BAT_MODE_1         {comp[0]}",
            f"#define AD_BAT_MODE_25        {comp[1]}",
            f"#define AD_BAT_MODE_50        {comp[2]}",
            f"#define AD_BAT_MODE_75        {comp[3]}",
            f"#define AD_BAT_MODE_100       {comp[4]}",
            *(
                (
                    "#define AD_BAT_MODE_COOL      "
                    f"{curve.cooling_compensation}",
                )
                if config.cooling.enabled
                else ()
            ),
            *brush_comp_lines,
            *ad_key_lines,
            *encoder_lines,
            *slider_lines,
        )
    )


def _native_flags(plan: GenerationPlan) -> str:
    ready_flags = tuple(
        name
        for channel in plan.adc.channels
        for name in channel.ready_flag_names
    )
    return "\n".join(
        (
            "bit fan_error_flag;",
            *(
                ("bit quick_slow_flag;",)
                if plan.config.motor.kind
                in (
                    "brushless_fixed_voltage_7_3",
                    "brushed_brushless_compat_fixed_voltage_7_3",
                )
                and plan.config.motor.voltage_slow_adjust_ms is not None
                else ()
            ),
            *(("bit adc_high_rate_flag;",) if plan.adc.high_rate_enabled else ()),
            *(
                ("bit YOUSHUA_WUSHUA;",)
                if plan.alternate_pwm is not None
                else ()
            ),
            *(
                ("bit YOUWU_COOL;",)
                if plan.config.cooling.enabled
                else ()
            ),
            *(
                ("bit YOUWU_LED;",)
                if plan.config.light.enabled
                else ()
            ),
            *(
                ("bit wh_mode;",)
                if plan.config.atomizer.enabled
                else ()
            ),
            *(
                (
                    "bit encoder_cycle_flag;",
                    "bit encoder_phase_a;",
                    "bit encoder_phase_b;",
                    "bit encoder_a_last;",
                    "bit encoder_quick_flag;",
                )
                if plan.config.encoder.enabled
                else (
                    (
                        "bit key_down_flag;",
                        "bit key_short_flag;",
                        "bit key_long_flag;",
                        "bit key_long_once_flag;",
                        "bit fan_start;",
                    )
                    if plan.config.slide_resistor.enabled
                    else tuple(
                        line
                        for key_name in _active_key_names(plan)
                        for line in (
                            f"bit {key_name.lower()}_down_flag;",
                            f"bit {key_name.lower()}_short_flag;",
                            f"bit {key_name.lower()}_long_flag;",
                            f"bit {key_name.lower()}_long_one_flag;",
                        )
                    )
                )
            ),
            *(
                tuple(
                    f"bit {key_name};"
                    for key_name in _active_key_names(plan)
                )
                if _uses_ad_keys(plan)
                else ()
            ),
            "bit insert_flag;",
            *(
                (
                    "bit charge_on_flag;",
                    "bit charge_max_flag;",
                )
                if plan.config.charging.enabled
                else ()
            ),
            "bit low_power_flag;",
            "bit show_mode;",
            "bit time_flash_flag;",
            *tuple(f"bit {name};" for name in ready_flags),
        )
    )


def _global_state(plan: GenerationPlan, base_state: str) -> str:
    return "\n".join(
        (
            base_state,
            "",
            "u8 Data[3];",
            "u8 charge_num;",
            "u8 low_cnt;",
            "u8 step_cnt;",
            "u8 wake_guard_cnt;",
            *(
                ("u8 light_mode;",)
                if (
                    plan.config.light.enabled
                    and plan.config.light.mode_profile
                    in ("on_off", "on_off_flash")
                )
                else ()
            ),
            *(
                (
                    "u8 encoder_add_cnt;",
                    "u8 encoder_sub_cnt;",
                    "u8 encoder_change_cnt;",
                    "u8 encoder_filter_cnt;",
                )
                if plan.config.encoder.enabled
                else (
                    (
                        "u8 key_delay;",
                        "u16 old_res_val;",
                        "u8 res_change_cnt;",
                        "u8 slider_target_mode;",
                    )
                    if plan.config.slide_resistor.enabled
                    else tuple(
                        f"u8 {key_name.lower()}_delay;"
                        for key_name in _active_key_names(plan)
                    )
                )
            ),
            *tuple(
                f"u8 {item.name.lower()}_click_cnt;"
                for item in _double_click_bands(plan)
            ),
            "u8 battery_time_type;",
            "",
            "const u8 app_smg[11] = {",
            "    0x3F, 0x06, 0x5B, 0x4F, 0x66,",
            "    0x6D, 0x7D, 0x07, 0x7F, 0x6F, 0x00",
            "};",
        )
    )


def _display_idle(plan: GenerationPlan) -> str:
    port_masks: dict[str, int] = {"A": 0, "C": 0}
    for index in range(1, plan.config.display.pin_count + 1):
        gpio = plan.resolved_pins[f"IO_LED_{index}"]
        port_masks[gpio[1]] |= 1 << int(gpio[2:])
    lines: list[str] = []
    for port in ("A", "C"):
        mask = port_masks[port]
        if mask:
            lines.append(f"PORT{port} |= {_hex8(mask)};")
    for port in ("A", "C"):
        mask = port_masks[port]
        if mask:
            lines.append(f"TRIS{port} &= {_hex8(~mask)};")
    return "\n".join(lines)


def _display_scan(plan: GenerationPlan) -> str:
    if plan.config.display.profile == "custom_charlieplex_188":
        by_negative: dict[int, list[tuple[int, int, int]]] = {
            index: []
            for index in range(1, plan.config.display.pin_count + 1)
        }
        for connection in plan.config.display.connections:
            byte_index, mask = DISPLAY_SEGMENT_BITS[connection.signal]
            by_negative[connection.negative_pin_index].append(
                (byte_index, mask, connection.positive_pin_index)
            )
        lines = [
            "static u8 cnt_display;",
            "",
            "smg_close();",
            "cnt_display++;",
            "switch(cnt_display)",
            "{",
        ]
        for negative in range(1, plan.config.display.pin_count + 1):
            lines.append(f"    case {negative}:")
            for byte_index, mask, positive in sorted(
                by_negative[negative]
            ):
                lines.append(
                    f"        if(!(Data[{byte_index}] & {_hex8(mask)})) "
                    f"{{ IO_IN_LED_{positive}; }}"
                )
            lines.append(f"        IO_LED_{negative} = 0;")
            if negative == plan.config.display.pin_count:
                lines.append("        cnt_display = 0;")
            lines.append("        break;")
            lines.append("")
        lines.extend(
            (
                "    default:",
                "        cnt_display = 0;",
                "        break;",
                "}",
            )
        )
        return "\n".join(lines)

    return "\n".join(
        (
            "static u8 cnt_display;",
            "",
            "smg_close();",
            "cnt_display++;",
            "switch(cnt_display)",
            "{",
            "    case 1:",
            "        if(!(Data[2] & 0x02)) { IO_IN_LED_2; }",
            "        if(!(Data[2] & 0x08)) { IO_IN_LED_3; }",
            "        if(!(Data[2] & 0x20)) { IO_IN_LED_4; }",
            "        if(!(Data[2] & 0x40)) { IO_IN_LED_5; }",
            "        IO_LED_1 = 0;",
            "        break;",
            "",
            "    case 2:",
            "        if(!(Data[2] & 0x01)) { IO_IN_LED_1; }",
            "        if(!(Data[1] & 0x02)) { IO_IN_LED_3; }",
            "        if(!(Data[1] & 0x08)) { IO_IN_LED_4; }",
            "        if(!(Data[1] & 0x10)) { IO_IN_LED_5; }",
            "        IO_LED_2 = 0;",
            "        break;",
            "",
            "    case 3:",
            "        if(!(Data[2] & 0x04)) { IO_IN_LED_1; }",
            "        if(!(Data[1] & 0x01)) { IO_IN_LED_2; }",
            "        if(!(Data[1] & 0x04)) { IO_IN_LED_4; }",
            "        if(!(Data[1] & 0x20)) { IO_IN_LED_5; }",
            "        IO_LED_3 = 0;",
            "        break;",
            "",
            "    case 4:",
            "        if(!(Data[2] & 0x10)) { IO_IN_LED_1; }",
            "        if(!(Data[0] & 0x02)) { IO_IN_LED_2; }",
            "        if(!(Data[0] & 0x01)) { IO_IN_LED_3; }",
            "        if(!(Data[1] & 0x40)) { IO_IN_LED_5; }",
            "        IO_LED_4 = 0;",
            "        break;",
            "",
            "    case 5:",
            "        if(!(Data[0] & 0x04)) { IO_IN_LED_2; }",
            "        if(!(Data[0] & 0x08)) { IO_IN_LED_3; }",
            "        IO_LED_5 = 0;",
            "        cnt_display = 0;",
            "        break;",
            "",
            "    default:",
            "        cnt_display = 0;",
            "        break;",
            "}",
        )
    )


def _display_state_transition(plan: GenerationPlan) -> str:
    flash_flag = _time_flag(plan, "display.flash", "flash_500ms")
    if _uses_legacy_display_behavior(plan):
        page_flag = _time_flag(plan, "display.page", "page_3s")
        return "\n".join(
            (
                f"if({flash_flag})",
                "{",
                f"    {flash_flag} = 0;",
                "    time_flash_flag = !time_flash_flag;",
                "    if(low_cnt)",
                "    {",
                "        low_cnt--;",
                "    }",
                "}",
                "",
                f"if({page_flag})",
                "{",
                f"    {page_flag} = 0;",
                "    if(step_cnt)",
                "    {",
                "        step_cnt--;",
                "        show_mode = !show_mode;",
                "    }",
                "}",
            )
        )

    gear_flag = _time_flag(plan, "display.page", "gear_event")
    gear_counter = _time_counter(
        plan, "display.page", "gear_event"
    )
    battery_role = (
        "battery_preview"
        if plan.config.display.normal_battery_preview_ms
        else None
    )
    battery_reset_lines: tuple[str, ...] = ()
    battery_transition_lines: tuple[str, ...] = ()
    if battery_role is not None:
        battery_flag = _time_flag(plan, "display.page", battery_role)
        battery_counter = _time_counter(
            plan, "display.page", battery_role
        )
        battery_reset_lines = (
            f"    {battery_flag} = 0;",
            f"    {battery_counter} = 0;",
        )
        battery_transition_lines = (
            "else",
            "{",
            f"    {gear_flag} = 0;",
            f"    {gear_counter} = 0;",
            f"    if(step_cnt && {battery_flag})",
            "    {",
            f"        {battery_flag} = 0;",
            f"        {battery_counter} = 0;",
            "        step_cnt--;",
            "        show_mode = 1;",
            "    }",
            "}",
        )
    return "\n".join(
        (
            f"if({flash_flag})",
            "{",
            f"    {flash_flag} = 0;",
            "    time_flash_flag = !time_flash_flag;",
            "    if(low_cnt)",
            "    {",
            "        low_cnt--;",
                "    }",
                "}",
                "",
            "if(show_mode)",
            "{",
            *battery_reset_lines,
            f"    if({gear_flag})",
            "    {",
            f"        {gear_flag} = 0;",
            f"        {gear_counter} = 0;",
            "        if(step_cnt)",
            "        {",
            "            step_cnt--;",
            "            show_mode = 0;",
            "        }",
            "    }",
            "}",
            *battery_transition_lines,
        )
    )


def _slider_mode_change(plan: GenerationPlan) -> str:
    inserted_idle = _display_idle_show_mode(plan, True)
    normal_idle = _display_idle_show_mode(plan, False)
    cooling_off = (
        ("    COOL_EN = 0;",)
        if plan.config.cooling.enabled
        else ()
    )
    insert_cooling_off = (
        cooling_off
        if (
            plan.config.cooling.enabled
            and not plan.config.cooling.allow_while_charging
        )
        else ()
    )
    charging_flag_reset = (
        (
            "charge_on_flag = 0;",
            "charge_max_flag = 0;",
        )
        if plan.config.charging.enabled
        else ()
    )
    charging_limit = (
        (
            "",
            "if(insert_flag)",
            "{",
            *insert_cooling_off,
            "    if(fan_start)",
            "    {",
            "        fan_mode = CHARGE_MAX_GEAR;",
            "    }",
            "}",
        )
        if plan.config.charging.enabled
        else ()
    )
    return "\n".join(
        (
            "static u8 insert_old;",
            "",
            *charging_flag_reset,
            "insert_flag = 0;",
            "",
            *_charging_state_normalization(plan),
            *charging_limit,
            "",
            "if(insert_flag != insert_old)",
            "{",
            "    insert_old = insert_flag;",
            "    old_res_val = 60000;",
            "    res_change_cnt = 0;",
            "    step_cnt = 0;",
            *_display_timer_reset_lines(plan, "    "),
            (
                f"    show_mode = insert_flag ? {inserted_idle} : "
                f"(fan_start ? {normal_idle} : 0);"
            ),
            "}",
            "",
            "if(fan_error_flag || (!charge_num && !insert_flag))",
            "{",
            "    fan_start = 0;",
            "    fan_mode = 0;",
            *cooling_off,
            "}",
            "",
            "if(!fan_start)",
            "{",
            "    fan_mode = 0;",
            "}",
            "",
            "if(!fan_mode)",
            "{",
            *cooling_off,
            "    old_res_val = 60000;",
            "    res_change_cnt = 0;",
            "    too_big_cnt = 0;",
            "    show_mode = 0;",
            "    step_cnt = 0;",
            "}",
            "else if(!step_cnt)",
            "{",
            (
                f"    show_mode = insert_flag ? {inserted_idle} : "
                f"{normal_idle};"
            ),
            "}",
            *_cooling_normalization(plan),
            *_light_normalization(plan),
            *_atomizer_normalization(plan),
        )
    )


def _mode_change(plan: GenerationPlan) -> str:
    if plan.config.slide_resistor.enabled:
        return _slider_mode_change(plan)

    inserted_idle = _display_idle_show_mode(plan, True)
    normal_idle = _display_idle_show_mode(plan, False)
    cooling_off = (
        ("    COOL_EN = 0;",)
        if plan.config.cooling.enabled
        else ()
    )
    insert_cooling_off = (
        cooling_off
        if (
            plan.config.cooling.enabled
            and not plan.config.cooling.allow_while_charging
        )
        else ()
    )
    charging_flag_reset = (
        (
            "charge_on_flag = 0;",
            "charge_max_flag = 0;",
        )
        if plan.config.charging.enabled
        else ()
    )
    charging_limit = (
        (
            "",
            "if(insert_flag)",
            "{",
            *insert_cooling_off,
            "    if(fan_mode > CHARGE_MAX_GEAR)",
            "    {",
            "        fan_mode = CHARGE_MAX_GEAR;",
            "    }",
            "}",
        )
        if plan.config.charging.enabled
        else ()
    )
    switch_lines: tuple[str, ...] = ()
    if plan.config.slide_switch.enabled:
        switch_lines = (
            "",
            "if(SWI_KEY)",
            "{",
            "    fan_mode = 0;",
            *cooling_off,
            "    fan_error_flag = 0;",
            "}",
            "else if(!fan_error_flag && !fan_mode",
            "        && (charge_num || insert_flag))",
            "{",
            "    fan_mode = FAN_MODE_MIN;",
            "}",
        )
    return "\n".join(
        (
            "static u8 fan_old;",
            "static u8 insert_old;",
            "",
            *charging_flag_reset,
            "insert_flag = 0;",
            "",
            *_charging_state_normalization(plan),
            *charging_limit,
            "",
            "if(fan_error_flag || (!charge_num && !insert_flag))",
            "{",
            "    fan_mode = 0;",
            *cooling_off,
            "}",
            *switch_lines,
            *_cooling_normalization(plan),
            *_light_normalization(plan),
            *_atomizer_normalization(plan),
            "",
            "if(insert_flag != insert_old)",
            "{",
            *_display_timer_reset_lines(plan, "    "),
            "    step_cnt = 0;",
            (
                f"    show_mode = insert_flag ? {inserted_idle} : "
                f"(fan_mode ? {normal_idle} : 0);"
            ),
            "}",
            "else if(fan_mode && fan_mode != fan_old)",
            "{",
            "    show_mode_change();",
            "}",
            "else if(!fan_mode && !insert_flag)",
            "{",
            "    show_mode = 0;",
            "    step_cnt = 0;",
            "}",
            "",
            "fan_old = fan_mode;",
            "insert_old = insert_flag;",
        )
    )


def _encoder_port_change_isr(plan: GenerationPlan) -> str:
    if not plan.config.encoder.enabled:
        return ""

    def event_lines(increase: bool) -> tuple[str, ...]:
        pending = "encoder_add_cnt" if increase else "encoder_sub_cnt"
        opposite = "encoder_sub_cnt" if increase else "encoder_add_cnt"
        return (
            f"                if({opposite})",
            "                {",
            f"                    {opposite}--;",
            "                }",
            "                else",
            "                {",
            "                    encoder_change_cnt++;",
            f"                    {pending}++;",
            "                }",
        )

    clockwise_is_high_pair = plan.config.encoder.clockwise_increases
    high_pair_event = event_lines(clockwise_is_high_pair)
    low_pair_event = event_lines(not clockwise_is_high_pair)
    return "\n".join(
        (
            "if(encoder_filter_cnt == 0)",
            "{",
            "    if(!encoder_a_last && ENC_A)",
            "    {",
            "        if(encoder_cycle_flag)",
            "        {",
            "            encoder_phase_b = !ENC_B;",
            "            encoder_cycle_flag = 0;",
            "            if(encoder_phase_a && encoder_phase_b)",
            "            {",
            *high_pair_event,
            "            }",
            "            else if(!encoder_phase_a && !encoder_phase_b)",
            "            {",
            *low_pair_event,
            "            }",
            "        }",
            "        encoder_filter_cnt = ENCODER_FILTER_TICKS;",
            "    }",
            "    else if(encoder_a_last && !ENC_A)",
            "    {",
            "        encoder_phase_a = ENC_B;",
            "        encoder_cycle_flag = 1;",
            "        encoder_filter_cnt = ENCODER_FILTER_TICKS;",
            "    }",
            "}",
            "encoder_a_last = ENC_A;",
        )
    )


def _encoder_high_rate_isr(plan: GenerationPlan, base_body: str) -> str:
    if not plan.config.encoder.enabled:
        return base_body
    return "\n".join(
        (
            base_body,
            "if(encoder_filter_cnt)",
            "{",
            "    encoder_filter_cnt--;",
            "}",
        )
    )


def _encoder_runtime_configuration(plan: GenerationPlan) -> str:
    if not plan.config.encoder.enabled:
        return ""
    return "\n".join(
        (
            "PAIE = 0;",
            f"WUACON = {_hex8(plan.gpio.runtime_change_mask_a)};",
            "encoder_a_last = ENC_A;",
            "PORTA;",
            "PAIF = 0;",
            "PAIE = 1;",
        )
    )


def _encoder_event_clear() -> str:
    return "\n".join(
        (
            "encoder_add_cnt = 0;",
            "encoder_sub_cnt = 0;",
            "encoder_change_cnt = 0;",
            "encoder_filter_cnt = 0;",
            "encoder_cycle_flag = 0;",
            "encoder_phase_a = 0;",
            "encoder_phase_b = 0;",
            "encoder_quick_flag = 0;",
        )
    )


def _encoder_deal(plan: GenerationPlan) -> str:
    acceleration_flag = _time_flag(
        plan, "input.encoder", "acceleration_window"
    )
    return "\n".join(
        (
            "u8 encoder_max_mode;",
            "u8 encoder_step;",
            "",
            "if(SWI_KEY)",
            "{",
            "    Key_Clear();",
            "    return;",
            "}",
            "",
            "if(!charge_num && !insert_flag)",
            "{",
            "    Key_Clear();",
            "    return;",
            "}",
            "",
            f"if({acceleration_flag})",
            "{",
            f"    {acceleration_flag} = 0;",
            "    encoder_quick_flag =",
            "        (encoder_change_cnt >= ENCODER_ACCEL_EVENTS);",
            "    encoder_change_cnt = 0;",
            "}",
            "",
            "encoder_max_mode = insert_flag",
            "    ? CHARGE_MAX_GEAR : FAN_MODE_MAX;",
            "encoder_step = encoder_quick_flag",
            "    ? ENCODER_ACCEL_STEP : ENCODER_NORMAL_STEP;",
            "",
            "if(encoder_add_cnt)",
            "{",
            "    encoder_add_cnt--;",
            "    if(fan_mode < encoder_max_mode)",
            "    {",
            "        if(encoder_step <= encoder_max_mode - fan_mode)",
            "        {",
            "            fan_mode += encoder_step;",
            "        }",
            "        else",
            "        {",
            "            fan_mode = encoder_max_mode;",
            "        }",
            "    }",
            "    show_mode_change();",
            "}",
            "",
            "if(encoder_sub_cnt)",
            "{",
            "    encoder_sub_cnt--;",
            "    if(fan_mode > FAN_MODE_MIN)",
            "    {",
            "        if(fan_mode >= FAN_MODE_MIN + encoder_step)",
            "        {",
            "            fan_mode -= encoder_step;",
            "        }",
            "        else",
            "        {",
            "            fan_mode = FAN_MODE_MIN;",
            "        }",
            "    }",
            "    show_mode_change();",
            "}",
        )
    )


def _key_check(plan: GenerationPlan) -> str:
    key_blocks: list[str] = []
    action_by_name = {
        item.name: item for item in _key_action_items(plan)
    }
    advanced_events = _uses_advanced_key_events(plan)
    for key_name in _active_key_names(plan):
        state = key_name.lower()
        long_action = (
            action_by_name[key_name].long_action
            if key_name in action_by_name
            else "fan_step_up"
        )
        if (
            advanced_events
            and long_action not in ("fan_step_up", "fan_step_down")
        ):
            long_event_lines = (
                (
                    f"        if(!{state}_long_one_flag "
                    f"&& {state}_delay > 60)"
                ),
                "        {",
                f"            {state}_long_flag = 1;",
                f"            {state}_long_one_flag = 1;",
                f"            {state}_delay = 0;",
                "        }",
            )
        else:
            long_event_lines = (
                (
                    f"        if((!{state}_long_one_flag "
                    f"&& {state}_delay > 60)"
                ),
                (
                    f"            || ({state}_long_one_flag "
                    f"&& {state}_delay > 6))"
                ),
                "        {",
                f"            {state}_long_flag = 1;",
                f"            {state}_long_one_flag = 1;",
                f"            {state}_delay = 0;",
                "        }",
            )
        key_blocks.append(
            "\n".join(
                (
                    f"if({key_name} && !{state}_down_flag)",
                    "{",
                    f"    {state}_delay = 0;",
                    "}",
                    f"if(!{state}_down_flag)",
                    "{",
                    f"    if(!{key_name} && ++{state}_delay > 2)",
                    "    {",
                    f"        {state}_down_flag = 1;",
                    f"        {state}_delay = 0;",
                    "    }",
                    "}",
                    "else",
                    "{",
                    f"    if({state}_delay < 250) {{ {state}_delay++; }}",
                    f"    if(!{key_name})",
                    "    {",
                    *long_event_lines,
                    "    }",
                    "    else",
                    "    {",
                    (
                        f"        if(!{state}_long_one_flag) "
                        f"{{ {state}_short_flag = 1; }}"
                    ),
                    f"        {state}_down_flag = 0;",
                    f"        {state}_long_one_flag = 0;",
                    f"        {state}_delay = 0;",
                    "    }",
                    "}",
                )
            )
        )
    return "\n\n".join(key_blocks)


def _slider_key_check() -> str:
    return "\n".join(
        (
            "if(!key_down_flag)",
            "{",
            "    if(!KEY)",
            "    {",
            "        if(++key_delay > 5)",
            "        {",
            "            key_down_flag = 1;",
            "            key_delay = 0;",
            "        }",
            "    }",
            "    else",
            "    {",
            "        key_delay = 0;",
            "    }",
            "}",
            "else",
            "{",
            "    if(!KEY)",
            "    {",
            "        if(key_delay < 250) { key_delay++; }",
            "        if(!key_long_once_flag && key_delay > 60)",
            "        {",
            "            key_long_flag = 1;",
            "            key_long_once_flag = 1;",
            "        }",
            "    }",
            "    else",
            "    {",
            "        if(!key_long_once_flag) { key_short_flag = 1; }",
            "        key_down_flag = 0;",
            "        key_long_once_flag = 0;",
            "        key_delay = 0;",
            "    }",
            "}",
        )
    )


def _slider_key_clear() -> str:
    return "\n".join(
        (
            "key_short_flag = 0;",
            "key_long_flag = 0;",
        )
    )


def _slider_key_deal(plan: GenerationPlan) -> str:
    cooling_condition = (
        "YOUWU_COOL && fan_start && (charge_num || insert_flag)"
        + (
            ""
            if plan.config.cooling.allow_while_charging
            else " && !insert_flag"
        )
    )
    cooling_lines = (
        (
            "",
            "if(key_long_flag)",
            "{",
            "    key_long_flag = 0;",
            f"    if({cooling_condition})",
            "    {",
            "        COOL_EN = !COOL_EN;",
            "    }",
            "}",
        )
        if (
            plan.config.cooling.enabled
            and plan.config.cooling.control_mode == "toggle_while_fan_on"
        )
        else ()
    )
    return "\n".join(
        (
            "if(!charge_num && !insert_flag",
            "   && (key_short_flag || key_long_flag))",
            "{",
            "    low_cnt = 8;",
            "    Key_Clear();",
            "    return;",
            "}",
            "",
            "if(key_short_flag)",
            "{",
            "    key_short_flag = 0;",
            "    fan_error_flag = 0;",
            "    fan_start = !fan_start;",
            "    if(fan_start)",
            "    {",
            "        fan_mode = FAN_MODE_MIN;",
            "        old_res_val = 60000;",
            "        res_change_cnt = 0;",
            "        show_mode_change();",
            "    }",
            "    else",
            "    {",
            "        fan_mode = 0;",
            "    }",
            "}",
            *cooling_lines,
            "",
            "Key_Clear();",
        )
    )


def _slider_processing(plan: GenerationPlan) -> str:
    ready_flag = _adc_ready_flag(
        plan, "input.slide_resistor", "AD_SLIDER"
    )
    minimum_gear = plan.config.classic_product.minimum_gear
    maximum_gear = plan.config.classic_product.maximum_gear
    low_at_high = plan.config.slide_resistor.low_gear_at_high_adc
    confirm_before_accept = plan.config.slide_resistor.confirmation_count - 1

    if low_at_high:
        clamp_lines = (
            "    if(AD_SLIDER_SUM >= ADC_SLIDER_MIN_GEAR)",
            "    {",
            "        AD_SLIDER_SUM = (u16)ADC_SLIDER_MIN_GEAR;",
            "        old_res_val = AD_SLIDER_SUM;",
            "    }",
            "    else if(AD_SLIDER_SUM <= ADC_SLIDER_MAX_GEAR)",
            "    {",
            "        AD_SLIDER_SUM = (u16)ADC_SLIDER_MAX_GEAR;",
            "        old_res_val = AD_SLIDER_SUM;",
            "    }",
        )
        baseline_invalid = (
            "old_res_val > ADC_SLIDER_MIN_GEAR "
            "|| old_res_val < ADC_SLIDER_MAX_GEAR"
        )
        map_lines = (
            "    if(old_res_val >= ADC_SLIDER_MIN_GEAR)",
            "    {",
            f"        slider_target_mode = {minimum_gear};",
            "    }",
            "    else if(old_res_val <= ADC_SLIDER_MAX_GEAR)",
            "    {",
            f"        slider_target_mode = {maximum_gear};",
            "    }",
            "    else",
            "    {",
            "        slider_target_mode = (u8)(",
            f"            {minimum_gear} +",
            "            (u16)((((unsigned long)ADC_SLIDER_MIN_GEAR",
            "                     - (unsigned long)old_res_val)",
            f"                    * {maximum_gear - minimum_gear}UL",
            "                    + ((unsigned long)ADC_RANGE >> 1))",
            "                   / (unsigned long)ADC_RANGE));",
            "    }",
        )
    else:
        clamp_lines = (
            "    if(AD_SLIDER_SUM <= ADC_SLIDER_MIN_GEAR)",
            "    {",
            "        AD_SLIDER_SUM = (u16)ADC_SLIDER_MIN_GEAR;",
            "        old_res_val = AD_SLIDER_SUM;",
            "    }",
            "    else if(AD_SLIDER_SUM >= ADC_SLIDER_MAX_GEAR)",
            "    {",
            "        AD_SLIDER_SUM = (u16)ADC_SLIDER_MAX_GEAR;",
            "        old_res_val = AD_SLIDER_SUM;",
            "    }",
        )
        baseline_invalid = (
            "old_res_val < ADC_SLIDER_MIN_GEAR "
            "|| old_res_val > ADC_SLIDER_MAX_GEAR"
        )
        map_lines = (
            "    if(old_res_val <= ADC_SLIDER_MIN_GEAR)",
            "    {",
            f"        slider_target_mode = {minimum_gear};",
            "    }",
            "    else if(old_res_val >= ADC_SLIDER_MAX_GEAR)",
            "    {",
            f"        slider_target_mode = {maximum_gear};",
            "    }",
            "    else",
            "    {",
            "        slider_target_mode = (u8)(",
            f"            {minimum_gear} +",
            "            (u16)((((unsigned long)old_res_val",
            "                     - (unsigned long)ADC_SLIDER_MIN_GEAR)",
            f"                    * {maximum_gear - minimum_gear}UL",
            "                    + ((unsigned long)ADC_RANGE >> 1))",
            "                   / (unsigned long)ADC_RANGE));",
            "    }",
        )

    if confirm_before_accept:
        confirmation_lines = (
            "        if(res_change_cnt < ADC_CONFIRM_COUNT - 1)",
            "        {",
            "            res_change_cnt++;",
            "        }",
            "        else",
            "        {",
            "            res_change_cnt = 0;",
            "            old_res_val = AD_SLIDER_SUM;",
            "        }",
        )
    else:
        confirmation_lines = (
            "        old_res_val = AD_SLIDER_SUM;",
            "        res_change_cnt = 0;",
        )

    clamp_lines = tuple(f"    {line}" for line in clamp_lines)
    map_lines = tuple(f"    {line}" for line in map_lines)
    confirmation_lines = tuple(
        f"    {line}" for line in confirmation_lines
    )

    return "\n".join(
        (
            f"if({ready_flag})",
            "{",
            f"    {ready_flag} = 0;",
            "    if(fan_start && !insert_flag && charge_num)",
            "    {",
            "        SLIDER_ON = 1;",
            *clamp_lines,
            "",
            f"        if({baseline_invalid})",
            "        {",
            "            old_res_val = AD_SLIDER_SUM;",
            "            res_change_cnt = 0;",
            "        }",
            "        else if((AD_SLIDER_SUM > old_res_val",
            "                 ? AD_SLIDER_SUM - old_res_val",
            "                 : old_res_val - AD_SLIDER_SUM)",
            "                > ADC_DEADBAND)",
            "        {",
            *confirmation_lines,
            "        }",
            "        else",
            "        {",
            "            res_change_cnt = 0;",
            "        }",
            "",
            *map_lines,
            f"        if(slider_target_mode < {minimum_gear})",
            "        {",
            f"            slider_target_mode = {minimum_gear};",
            "        }",
            f"        if(slider_target_mode > {maximum_gear})",
            "        {",
            f"            slider_target_mode = {maximum_gear};",
            "        }",
            "        if(fan_mode != slider_target_mode)",
            "        {",
            "            fan_mode = slider_target_mode;",
            "            show_mode_change();",
            "        }",
            "    }",
            "    else",
            "    {",
            "        old_res_val = 60000;",
            "        res_change_cnt = 0;",
            "    }",
            "}",
        )
    )


def _ad_key_decode(plan: GenerationPlan) -> str:
    if not _uses_ad_keys(plan):
        return ""
    ready_flag = _adc_ready_flag(plan, "input.ad_key", "AD_KEY")
    bands = sorted(
        plan.config.ad_key.key_bands,
        key=lambda item: (item.minimum_adc, item.maximum_adc),
    )
    lines = [
        f"if({ready_flag})",
        "{",
        f"    {ready_flag} = 0;",
        *(f"    {key_name} = 1;" for key_name in _active_key_names(plan)),
    ]
    for index, item in enumerate(bands):
        prefix = "if" if index == 0 else "else if"
        if item.minimum_adc == 0:
            lines.append(
                f"    {prefix}(AD_KEY_VALUE <= AD_{item.name}_MAX)"
            )
        else:
            lines.extend(
                (
                    f"    {prefix}(AD_KEY_VALUE >= AD_{item.name}_MIN",
                    (
                        "            && AD_KEY_VALUE <= "
                        f"AD_{item.name}_MAX)"
                    ),
                )
            )
        lines.extend(
            (
                "    {",
                f"        {item.name} = 0;",
                "    }",
            )
        )
    lines.append("}")
    return "\n".join(lines)


def _key_deal(plan: GenerationPlan) -> str:
    if plan.config.encoder.enabled:
        return _encoder_deal(plan)
    if plan.config.slide_resistor.enabled:
        return _slider_key_deal(plan)

    gears = plan.config.classic_product.gear_steps
    charge_gears = tuple(
        gear
        for gear in gears
        if gear <= plan.config.classic_product.charge_max_gear
    )

    def cycle_lines_for(
        values: tuple[int, ...], off_after_max: bool
    ) -> tuple[str, ...]:
        result: list[str] = []
        for index, gear in enumerate(values):
            prefix = "if" if index == 0 else "else if"
            result.extend(
                (
                    f"        {prefix}(fan_mode < {gear})",
                    "        {",
                    f"            fan_mode = {gear};",
                    "        }",
                )
            )
        result.extend(
            (
                "        else",
                "        {",
                (
                    "            fan_mode = 0;"
                    if off_after_max
                    else f"            fan_mode = {values[0]};"
                ),
                "        }",
            )
        )
        return tuple(result)

    off_after_max = not plan.config.slide_switch.enabled
    normal_cycle = cycle_lines_for(gears, off_after_max)
    charge_cycle = cycle_lines_for(charge_gears, off_after_max)
    clear_fan_error = (
        ()
        if plan.config.slide_switch.enabled
        else ("    fan_error_flag = 0;",)
    )
    switch_guard = (
        (
            "if(SWI_KEY)",
            "{",
            "    Key_Clear();",
            "    return;",
            "}",
            "",
        )
        if plan.config.slide_switch.enabled
        else ()
    )
    if _uses_configurable_key_actions(plan):
        bands = sorted(
            _key_action_items(plan),
            key=lambda item: int(item.name[3:]),
        )
        event_condition = [
            "if(!charge_num && !insert_flag",
            (
                f"   && ({bands[0].name.lower()}_short_flag "
                f"|| {bands[0].name.lower()}_long_flag"
            ),
        ]
        for item in bands[1:]:
            state = item.name.lower()
            event_condition.append(
                f"       || {state}_short_flag || {state}_long_flag"
            )
        event_condition[-1] += "))"

        def action_lines(event_flag: str, action: str) -> tuple[str, ...]:
            if action == "none":
                return ()
            if action == "fan_power_toggle":
                return (
                    f"if({event_flag})",
                    "{",
                    *clear_fan_error,
                    "    if(fan_mode)",
                    "    {",
                    "        fan_mode = 0;",
                    "    }",
                    "    else",
                    "    {",
                    "        fan_mode = FAN_MODE_MIN;",
                    "    }",
                    "}",
                )
            if action == "fan_cycle":
                return (
                    f"if({event_flag})",
                    "{",
                    *clear_fan_error,
                    "    if(insert_flag)",
                    "    {",
                    *charge_cycle,
                    "    }",
                    "    else",
                    "    {",
                    *normal_cycle,
                    "    }",
                    "}",
                )
            if action == "fan_step_up":
                return (
                    f"if({event_flag})",
                    "{",
                    *clear_fan_error,
                    "    if(!fan_mode)",
                    "    {",
                    "        fan_mode = FAN_MODE_MIN;",
                    "    }",
                    "    else if(fan_mode < FAN_MODE_MAX)",
                    "    {",
                    "        fan_mode++;",
                    "    }",
                    "}",
                )
            if action == "fan_step_down":
                return (
                    f"if({event_flag})",
                    "{",
                    "    if(fan_mode > FAN_MODE_MIN)",
                    "    {",
                    "        fan_mode--;",
                    "    }",
                    "}",
                )
            if action == "cooling_toggle":
                charge_guard = (
                    ""
                    if plan.config.cooling.allow_while_charging
                    else " && !insert_flag"
                )
                return (
                    f"if({event_flag} && YOUWU_COOL && fan_mode"
                    f"{charge_guard})",
                    "{",
                    "    COOL_EN = !COOL_EN;",
                    "}",
                )
            if action == "light_cycle":
                if plan.config.light.mode_profile == "on_off":
                    light_change = ("    light_mode = !light_mode;",)
                else:
                    light_change = (
                        "    if(light_mode < 2)",
                        "    {",
                        "        light_mode++;",
                        "    }",
                        "    else",
                        "    {",
                        "        light_mode = 0;",
                        "    }",
                    )
                return (
                    f"if({event_flag} && YOUWU_LED)",
                    "{",
                    *light_change,
                    "}",
                )
            if action == "atomizer_toggle":
                guards = []
                if (
                    plan.config.atomizer.dependency
                    == "fan_required"
                ):
                    guards.append("fan_mode")
                if not plan.config.atomizer.allow_while_charging:
                    guards.append("!insert_flag")
                suffix = (
                    " && " + " && ".join(guards)
                    if guards
                    else ""
                )
                return (
                    f"if({event_flag}{suffix})",
                    "{",
                    "    wh_mode = !wh_mode;",
                    "}",
                )
            raise FanForgeError(f"unsupported key action: {action}")

        def action_body_lines(action: str, indent: str) -> tuple[str, ...]:
            wrapped = action_lines("1", action)
            if not wrapped:
                return ()
            if wrapped[0] != "if(1)":
                condition = wrapped[0].replace("if(1 && ", "if(", 1)
                return (
                    f"{indent}{condition}",
                    *tuple(f"{indent}{line}" for line in wrapped[1:]),
                )
            body = wrapped[2:-1]
            return tuple(
                indent + (line[4:] if line.startswith("    ") else line)
                for line in body
            )

        action_sections: list[str] = []
        if not _uses_advanced_key_events(plan):
            for item in bands:
                state = item.name.lower()
                for event_name, action in (
                    ("short", item.short_action),
                    ("long", item.long_action),
                ):
                    section = action_lines(
                        f"{state}_{event_name}_flag", action
                    )
                    if section:
                        action_sections.append("\n".join(section))
        else:
            for item in bands:
                state = item.name.lower()
                if item.double_action != "none":
                    window_flag = _time_flag(
                        plan,
                        f"input.{state}",
                        "double_click_window",
                    )
                    window_counter = _time_counter(
                        plan,
                        f"input.{state}",
                        "double_click_window",
                    )
                    short_body = action_body_lines(
                        item.short_action, "        "
                    )
                    double_body = action_body_lines(
                        item.double_action, "        "
                    )
                    section_lines = [
                        f"if({state}_short_flag)",
                        "{",
                        f"    {state}_short_flag = 0;",
                        f"    if(!{state}_click_cnt)",
                        "    {",
                        f"        {state}_click_cnt = 1;",
                        f"        {window_flag} = 0;",
                        f"        {window_counter} = 0;",
                        "    }",
                        "    else",
                        "    {",
                        f"        {state}_click_cnt = 0;",
                        f"        {window_flag} = 0;",
                        f"        {window_counter} = 0;",
                        *double_body,
                        "    }",
                        "}",
                        "",
                        f"if({state}_click_cnt && {window_flag})",
                        "{",
                        f"    {window_flag} = 0;",
                        f"    {window_counter} = 0;",
                        f"    {state}_click_cnt = 0;",
                        "    if(!charge_num && !insert_flag)",
                        "    {",
                        "        low_cnt = 8;",
                        "    }",
                        "    else",
                        "    {",
                        *short_body,
                        "    }",
                        "}",
                    ]
                    action_sections.append("\n".join(section_lines))
                else:
                    short_section = action_lines(
                        f"{state}_short_flag", item.short_action
                    )
                    if short_section:
                        action_sections.append(
                            "\n".join(short_section)
                        )

                long_section = action_lines(
                    f"{state}_long_flag", item.long_action
                )
                if long_section:
                    if item.double_action != "none":
                        long_body = action_body_lines(
                            item.long_action, "    "
                        )
                        long_section = (
                            f"if({state}_long_flag)",
                            "{",
                            f"    {state}_long_flag = 0;",
                            f"    {state}_click_cnt = 0;",
                            *_double_click_timer_reset_lines(
                                plan, item.name, "    "
                            ),
                            *long_body,
                            "}",
                        )
                    action_sections.append("\n".join(long_section))

        double_clear_lines = tuple(
            line
            for item in _double_click_bands(plan)
            for line in (
                f"    {item.name.lower()}_click_cnt = 0;",
                *_double_click_timer_reset_lines(
                    plan, item.name, "    "
                ),
            )
        )
        return "\n".join(
            (
                *switch_guard,
                *event_condition,
                "{",
                "    low_cnt = 8;",
                *double_clear_lines,
                "    Key_Clear();",
                "    return;",
                "}",
                "",
                "\n\n".join(action_sections),
                "",
                "Key_Clear();",
            )
        )
    long_section = (
        (
            "",
            "if(key1_long_flag)",
            "{",
            *clear_fan_error,
            "    if(!fan_mode)",
            "    {",
            "        fan_mode = FAN_MODE_MIN;",
            "    }",
            "    else if(fan_mode < FAN_MODE_MAX)",
            "    {",
            "        fan_mode++;",
            "    }",
            "}",
        )
        if plan.config.classic_product.long_adjust
        else ()
    )
    key2_long_section = (
        (
            "",
            "if(key2_long_flag)",
            "{",
            "    if(fan_mode > FAN_MODE_MIN)",
            "    {",
            "        fan_mode--;",
            "    }",
            "}",
        )
        if plan.config.classic_product.long_adjust
        else ()
    )
    return "\n".join(
        (
            *switch_guard,
            "if(!charge_num && !insert_flag",
            "   && (key1_short_flag || key1_long_flag",
            "       || key2_short_flag || key2_long_flag))",
            "{",
            "    low_cnt = 8;",
            "    Key_Clear();",
            "    return;",
            "}",
            "",
            "if(key1_short_flag)",
            "{",
            *clear_fan_error,
            "    if(insert_flag)",
            "    {",
            *charge_cycle,
            "    }",
            "    else",
            "    {",
            *normal_cycle,
            "    }",
            "}",
            *long_section,
            "",
            *(
                (
                    (
                        "if(key2_short_flag && YOUWU_COOL && fan_mode"
                        + (
                            ")"
                            if plan.config.cooling.allow_while_charging
                            else " && !insert_flag)"
                        )
                    ),
                    "{",
                    "    COOL_EN = !COOL_EN;",
                    "}",
                )
                if (
                    plan.config.cooling.enabled
                    and plan.config.cooling.control_mode
                    == "toggle_while_fan_on"
                )
                else ()
            ),
            *key2_long_section,
            "",
            "Key_Clear();",
        )
    )


def _show_mode_change(plan: GenerationPlan) -> str:
    if _uses_legacy_display_behavior(plan):
        page_flag = _time_flag(plan, "display.page", "page_3s")
        page_counter = _time_counter(plan, "display.page", "page_3s")
        return "\n".join(
            (
                "show_mode = 1;",
                "step_cnt = insert_flag ? 1 : 2;",
                f"{page_flag} = 0;",
                f"{page_counter} = 0;",
            )
        )

    inserted_steps = (
        1
        if plan.config.display.charging_idle_page == "battery"
        else 0
    )
    if plan.config.display.normal_idle_page == "battery":
        normal_steps = 1
    elif plan.config.display.normal_battery_preview_ms:
        normal_steps = 2
    else:
        normal_steps = 0
    step_value = (
        str(normal_steps)
        if inserted_steps == normal_steps
        else f"insert_flag ? {inserted_steps} : {normal_steps}"
    )
    return "\n".join(
        (
            "show_mode = 1;",
            f"step_cnt = {step_value};",
            *_display_timer_reset_lines(plan),
        )
    )


def _display_mask(plan: GenerationPlan, signal: str) -> int | None:
    if any(
        connection.signal == signal
        for connection in plan.config.display.connections
    ):
        return DISPLAY_SEGMENT_BITS[signal][1]
    return None


def _show_mode_deal(plan: GenerationPlan) -> str:
    low_target = plan.config.classic_product.low_blink_target
    charge_target = plan.config.classic_product.charge_blink_target
    percent_mask = _display_mask(plan, "icon.percent")
    cooling_mask = _display_mask(plan, "icon.cooling")
    charge_mask = _display_mask(plan, "icon.charge")
    fan_mask = _display_mask(plan, "icon.fan")
    mist_mask = _display_mask(plan, "icon.mist")
    hundreds_mask = (
        DISPLAY_SEGMENT_BITS["hundreds.0"][1]
        | DISPLAY_SEGMENT_BITS["hundreds.1"][1]
    )
    low_lines = (
        ("        d2 = 0;",)
        if low_target == "last_digit"
        else ("        d1 = 0;", "        d2 = 0;")
    )
    if charge_target == "last_digit":
        charge_lines = ("        d2 = 0;",)
    elif charge_target == "percent_icon":
        if percent_mask is None:
            raise FanForgeError(
                "percent-icon charging blink requires a mapped percent icon"
            )
        charge_lines = (
            f"        d0 &= {_hex8(~percent_mask)};",
        )
    else:
        if charge_mask is None:
            raise FanForgeError(
                "charge-icon blink requires a mapped charge icon"
            )
        charge_lines = (
            f"        d0 &= {_hex8(~charge_mask)};",
        )
    cooling_icon_lines = (
        (
            "if(YOUWU_COOL && COOL_EN)",
            "{",
            f"    d0 |= {_hex8(cooling_mask)};",
            "}",
            "",
        )
        if plan.config.cooling.enabled and cooling_mask is not None
        else ()
    )
    charge_icon_lines = (
        (
            "if(insert_flag)",
            "{",
            f"    d0 |= {_hex8(charge_mask)};",
            "}",
            "",
        )
        if charge_target == "charge_icon" and charge_mask is not None
        else ()
    )
    fan_icon_lines = (
        (
            "if(fan_mode)",
            "{",
            f"    d0 |= {_hex8(fan_mask)};",
            "}",
            "",
        )
        if fan_mask is not None
        else ()
    )
    mist_icon_lines = (
        (
            "if(wh_mode)",
            "{",
            f"    d0 |= {_hex8(mist_mask)};",
            "}",
            "",
        )
        if plan.config.atomizer.enabled and mist_mask is not None
        else ()
    )
    return "\n".join(
        (
            "u8 temp_val;",
            "u8 d0;",
            "u8 d1;",
            "u8 d2;",
            "",
            "if(show_mode)",
            "{",
            "    temp_val = fan_mode;",
            "    d0 = 0;",
            "}",
            "else",
            "{",
            "    temp_val = charge_num;",
            f"    d0 = {_hex8(percent_mask or 0)};",
            "}",
            "",
            *cooling_icon_lines,
            *charge_icon_lines,
            *fan_icon_lines,
            *mist_icon_lines,
            "if(temp_val > 99)",
            "{",
            f"    d0 |= {_hex8(hundreds_mask)};",
            "    temp_val -= 100;",
            "}",
            "",
            "d1 = app_smg[temp_val / 10];",
            "d2 = app_smg[temp_val % 10];",
            "",
            "if(!show_mode)",
            "{",
            "    if(low_power_flag && !insert_flag && time_flash_flag)",
            "    {",
            *low_lines,
            "    }",
            "    if(insert_flag && charge_num < 100 && time_flash_flag)",
            "    {",
            *charge_lines,
            "    }",
            "}",
            "",
            "GIE = 0;",
            "Data[0] = d0;",
            "Data[1] = d1;",
            "Data[2] = d2;",
            "GIE = 1;",
        )
    )


def _fan_deal(plan: GenerationPlan) -> str:
    pwm = plan.pwm
    run_symbol = _pwm_run_symbol(pwm)
    if plan.config.motor.kind == "brushed_fixed_duty":
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
    ready = _adc_ready_flag(
        plan, "fan_voltage_protection.fixed_duty", "AD_FAN"
    )
    ad_value = plan.adc.role_results[
        "fan_voltage_protection.fixed_duty.AD_FAN"
    ]
    protection_cooling_off = (
        ("            COOL_EN = 0;",)
        if plan.config.cooling.enabled
        else ()
    )
    return "\n".join(
        (
            "if(!fan_mode || fan_error_flag)",
            "{",
            "    too_big_cnt = 0;",
            f"    {ready} = 0;",
            f"    if({pwm.enable_symbol} || {run_symbol})",
            "    {",
            f"        {pwm.enable_symbol} = 0;",
            *_stop_pwm_timer_lines(plan, pwm, "        "),
            f"        {pwm.duty_register} = 0;",
            f"        {pwm.duty_high_register} = 0;",
            "        return;",
            "    }",
            "    FAN_ON = 0;",
            "    return;",
            "}",
            "",
            "if(!FAN_ON)",
            "{",
            "    too_big_cnt = 0;",
            f"    {ready} = 0;",
            "    FAN_ON = 1;",
            "    return;",
            "}",
            "",
            f"if(!{pwm.enable_symbol} || !{run_symbol})",
            "{",
            f"    {pwm.duty_register} = FAN_PWM_DUTY_BASE",
            "        + fan_mode / FAN_PWM_GEAR_DIVISOR;",
            f"    {pwm.duty_high_register} = 0;",
            f"    {pwm.enable_symbol} = 1;",
            f"    {run_symbol} = 1;",
            "    return;",
            "}",
            "",
            f"if({ready})",
            "{",
            f"    {ready} = 0;",
            f"    if({ad_value} > AD_FAN_TOO_HIGH)",
            "    {",
            "        if(too_big_cnt < 255) { too_big_cnt++; }",
            "        if(too_big_cnt >= AD_FAN_CONFIRM_COUNT)",
            "        {",
            "            fan_error_flag = 1;",
            "            fan_mode = 0;",
            *protection_cooling_off,
            f"            {pwm.enable_symbol} = 0;",
            *_stop_pwm_timer_lines(plan, pwm, "            "),
            f"            {pwm.duty_register} = 0;",
            f"            {pwm.duty_high_register} = 0;",
            "            return;",
            "        }",
            "    }",
            "    else",
            "    {",
            "        too_big_cnt = 0;",
            "    }",
            "}",
            "",
            f"{pwm.duty_register} = FAN_PWM_DUTY_BASE",
            "    + fan_mode / FAN_PWM_GEAR_DIVISOR;",
        )
    )


def _atomizer_deal(plan: GenerationPlan) -> str:
    pwm = _atomizer_pwm(plan)
    if pwm is None:
        return ""
    run_symbol = _pwm_run_symbol(pwm)
    return "\n".join(
        (
            "void wh_deal(void)",
            "{",
            "    if(!wh_mode)",
            "    {",
            f"        {pwm.enable_symbol} = 0;",
            f"        {pwm.duty_register} = 0;",
            f"        {pwm.duty_high_register} = 0;",
            "        PWM_WH = 0;",
            *_stop_pwm_timer_lines(plan, pwm, "        "),
            "        return;",
            "    }",
            "",
            f"    {run_symbol} = 1;",
            f"    {pwm.enable_symbol} = 1;",
            f"    {pwm.duty_register} = WH_DUTY;",
            f"    {pwm.duty_high_register} = 0;",
            "}",
        )
    )


def _clean_battery_timers(plan: GenerationPlan) -> str:
    resources = (
        *(
            (
                (0, "battery.charge", "charge_active"),
                (1, "battery.charge", "charge_full"),
            )
            if plan.config.charging.enabled
            else ()
        ),
        (2, "battery.discharge", "discharge"),
        (3, "battery.discharge", "low_discharge"),
    )
    timers = tuple(
        (
            type_id,
            _time_flag(plan, owner, role),
            _time_counter(plan, owner, role),
        )
        for type_id, owner, role in resources
    )
    lines = [
        "if(battery_time_type != type)",
        "{",
    ]
    for _, flag, counter in timers:
        lines.extend((f"    {flag} = 0;", f"    {counter} = 0;"))
    lines.extend(("    battery_time_type = type;", "}", ""))
    for type_id, flag, counter in timers:
        lines.extend(
            (
                f"if(type != {type_id})",
                "{",
                f"    {flag} = 0;",
                f"    {counter} = 0;",
                "}",
            )
        )
    return "\n".join(lines)


def _battery_deal(plan: GenerationPlan) -> str:
    charge_active_flag = (
        _time_flag(plan, "battery.charge", "charge_active")
        if plan.config.charging.enabled
        else ""
    )
    charge_full_flag = (
        _time_flag(plan, "battery.charge", "charge_full")
        if plan.config.charging.enabled
        else ""
    )
    discharge_flag = _time_flag(plan, "battery.discharge", "discharge")
    low_discharge_flag = _time_flag(
        plan, "battery.discharge", "low_discharge"
    )
    maximum_gear = plan.config.classic_product.maximum_gear
    compensation_limits = tuple(
        (maximum_gear * index + 4) // 5 for index in range(1, 5)
    )
    brushless_compensation = (
        (
            f"if(fan_mode < {compensation_limits[0]}) "
            "{ ADCDATA_BAT += AD_BAT_MODE_1; }"
        ),
        (
            f"else if(fan_mode < {compensation_limits[1]}) "
            "{ ADCDATA_BAT += AD_BAT_MODE_25; }"
        ),
        (
            f"else if(fan_mode < {compensation_limits[2]}) "
            "{ ADCDATA_BAT += AD_BAT_MODE_50; }"
        ),
        (
            f"else if(fan_mode < {compensation_limits[3]}) "
            "{ ADCDATA_BAT += AD_BAT_MODE_75; }"
        ),
        "else { ADCDATA_BAT += AD_BAT_MODE_100; }",
    )
    if plan.alternate_pwm is not None:
        compensation_lines = (
            "        if(!YOUSHUA_WUSHUA)",
            "        {",
            *(f"            {line}" for line in brushless_compensation),
            *(
                (
                    "            if(COOL_EN)",
                    "            {",
                    "                ADCDATA_BAT += AD_BAT_MODE_COOL;",
                    "            }",
                )
                if plan.config.cooling.enabled
                else ()
            ),
            "        }",
            "        else",
            "        {",
            (
                f"            if(fan_mode < {compensation_limits[0]}) "
                "{ ADCDATA_BAT += AD_BAT_BRUSH_MODE_1; }"
            ),
            (
                f"            else if(fan_mode < {compensation_limits[1]}) "
                "{ ADCDATA_BAT += AD_BAT_BRUSH_MODE_25; }"
            ),
            (
                f"            else if(fan_mode < {compensation_limits[2]}) "
                "{ ADCDATA_BAT += AD_BAT_BRUSH_MODE_50; }"
            ),
            (
                f"            else if(fan_mode < {compensation_limits[3]}) "
                "{ ADCDATA_BAT += AD_BAT_BRUSH_MODE_75; }"
            ),
            "            else { ADCDATA_BAT += AD_BAT_BRUSH_MODE_100; }",
            *(
                (
                    "            if(COOL_EN)",
                    "            {",
                    "                ADCDATA_BAT += AD_BAT_BRUSH_MODE_COOL;",
                    "            }",
                )
                if plan.config.cooling.enabled
                else ()
            ),
            "        }",
        )
        cooling_line: tuple[str, ...] = ()
    else:
        compensation_lines = tuple(
            f"        {line}" for line in brushless_compensation
        )
        cooling_line = (
            (
                "    if(COOL_EN) { ADCDATA_BAT += AD_BAT_MODE_COOL; }",
            )
            if plan.config.cooling.enabled
            else ()
        )
    low_zero_cooling_off = (
        ("        COOL_EN = 0;",)
        if plan.config.cooling.enabled
        else ()
    )
    charging_tracking = (
        (
            "if(insert_flag)",
            "{",
            "    if(charge_max_flag)",
            "    {",
            "        clean_other_time(1);",
            f"        if({charge_full_flag})",
            "        {",
            f"            {charge_full_flag} = 0;",
            "            if(charge_num < 100) { charge_num++; }",
            "        }",
            "    }",
            "    else",
            "    {",
            "        clean_other_time(0);",
            f"        if({charge_active_flag})",
            "        {",
            f"            {charge_active_flag} = 0;",
            "            if(charge_num <= p_temp && charge_num < 99)",
            "            {",
            "                charge_num++;",
            "            }",
            "        }",
            "    }",
            "}",
            "else if(charge_num > p_temp)",
        )
        if plan.config.charging.enabled
        else ("if(charge_num > p_temp)",)
    )
    return "\n".join(
        (
            "u16 v_temp;",
            "u16 ADCDATA_BAT;",
            "u16 step;",
            "u8 p_temp;",
            "",
            "v_temp = 0;",
            "ADCDATA_BAT = ADC_BAT_VALUE * 10;",
            "step = 0;",
            "p_temp = 0;",
            "",
            "if(ADCDATA_BAT)",
            "{",
            "    if(fan_mode)",
            "    {",
            *compensation_lines,
            "    }",
            *cooling_line,
            "",
            "    low_power_flag = (ADCDATA_BAT <= AD_BAT_LOW);",
            "    if(ADCDATA_BAT <= AD_BAT_ZERO)",
            "    {",
            "        fan_mode = 0;",
            *low_zero_cooling_off,
            "        charge_num = 0;",
            "    }",
            "",
            "    if(ADCDATA_BAT >= AD_BAT_100)",
            "    {",
            "        p_temp = 100;",
            "    }",
            "    else if(ADCDATA_BAT >= AD_BAT_80)",
            "    {",
            "        v_temp = AD_BAT_80;",
            "        p_temp = 80;",
            "        step = AD_BAT_STEP_80_100;",
            "    }",
            "    else if(ADCDATA_BAT >= AD_BAT_50)",
            "    {",
            "        v_temp = AD_BAT_50;",
            "        p_temp = 50;",
            "        step = AD_BAT_STEP_50_80;",
            "    }",
            "    else if(ADCDATA_BAT >= AD_BAT_10)",
            "    {",
            "        v_temp = AD_BAT_10;",
            "        p_temp = 10;",
            "        step = AD_BAT_STEP_10_50;",
            "    }",
            "    else if(ADCDATA_BAT >= AD_BAT_5)",
            "    {",
            "        v_temp = AD_BAT_5;",
            "        p_temp = 5;",
            "        step = AD_BAT_STEP_5_10;",
            "    }",
            "    else if(ADCDATA_BAT >= AD_BAT_0)",
            "    {",
            "        v_temp = AD_BAT_0;",
            "        p_temp = 1;",
            "        step = AD_BAT_STEP_0_5;",
            "    }",
            "",
            "    while(v_temp < ADCDATA_BAT && p_temp < 100 && step)",
            "    {",
            "        v_temp += step;",
            "        p_temp++;",
            "    }",
            "}",
            "",
            "if(delay_cnt)",
            "{",
            "    charge_num = p_temp;",
            "    return p_temp;",
            "}",
            "",
            *charging_tracking,
            "{",
            "    if(low_power_flag)",
            "    {",
            "        clean_other_time(3);",
            f"        if({low_discharge_flag})",
            "        {",
            f"            {low_discharge_flag} = 0;",
            "            if(charge_num) { charge_num--; }",
            "        }",
            "    }",
            "    else",
            "    {",
            "        clean_other_time(2);",
            f"        if({discharge_flag})",
            "        {",
            f"            {discharge_flag} = 0;",
            "            if(charge_num) { charge_num--; }",
            "        }",
            "    }",
            "}",
            "",
            "return p_temp;",
        )
    )


def _sleep_event_clear(plan: GenerationPlan, base_reset: str) -> str:
    if plan.config.encoder.enabled:
        input_clear = tuple(_encoder_event_clear().splitlines())
    elif plan.config.slide_resistor.enabled:
        input_clear = (
            "key_down_flag = 0;",
            "key_short_flag = 0;",
            "key_long_flag = 0;",
            "key_long_once_flag = 0;",
            "key_delay = 0;",
            "fan_start = 0;",
            "old_res_val = 60000;",
            "res_change_cnt = 0;",
            "slider_target_mode = 0;",
        )
    else:
        input_clear = (
            *tuple(
                line
                for key_name in _active_key_names(plan)
                for line in (
                    f"{key_name.lower()}_down_flag = 0;",
                    f"{key_name.lower()}_short_flag = 0;",
                    f"{key_name.lower()}_long_flag = 0;",
                    f"{key_name.lower()}_long_one_flag = 0;",
                )
            ),
            *tuple(
                f"{key_name.lower()}_delay = 0;"
                for key_name in _active_key_names(plan)
            ),
            *(
                tuple(
                    f"{key_name} = 1;"
                    for key_name in _active_key_names(plan)
                )
                if _uses_ad_keys(plan)
                else ()
            ),
        )
    input_clear = (
        *input_clear,
        *_double_click_state_reset_lines(plan),
    )
    return "\n".join(
        (
            *input_clear,
            "step_cnt = 0;",
            "Data[0] = 0;",
            "Data[1] = 0;",
            "Data[2] = 0;",
            *_display_timer_reset_lines(plan),
            base_reset,
            "battery_time_type = 0xFF;",
        )
    )


def apply_classic_slots(
    plan: GenerationPlan, slots: dict[str, str]
) -> None:
    if not plan.config.classic_product.enabled:
        return

    pwm = plan.pwm
    base_motor_parameters = slots["PARAMETER_DEFINITIONS"]
    base_fan_deal = slots["FAN_START_RUN_STOP_AND_PROTECTION"]
    base_high_rate_isr = slots["HIGH_RATE_ISR_BODY"]
    bat_ready = _adc_ready_flag(plan, "battery.voltage", "ADC_BAT")
    base_adc_reset = slots["ADC_COUNTER_AND_PROTECTION_RESET"]
    pwm_plans = _all_pwm_plans(plan)
    pwm_shutdown_lines = tuple(
        dict.fromkeys(
            (
                *(
                    line
                    for item in pwm_plans
                    for line in (
                        f"{item.enable_symbol} = 0;",
                        f"{item.duty_register} = 0;",
                        f"{item.duty_high_register} = 0;",
                    )
                ),
                *(
                    f"{timer}REN = 0;"
                    for timer in ("T3", "T4")
                    if any(item.timer == timer for item in pwm_plans)
                ),
            )
        )
    )
    self_test_lines = [
        f"if({bat_ready})",
        "{",
        f"    {bat_ready} = 0;",
        "    charge_num = v_bat_deal();",
        "}",
    ]
    feature_detection = _feature_detection_function(plan)
    if feature_detection:
        self_test_lines.extend(
            (
                "if(delay_cnt == 1)",
                "{",
                "    detect_optional_features();",
                "}",
            )
        )
    post_self_test_lines: list[str] = []
    power_on_lines = [
        "fan_mode = 0;",
        "charge_num = 0;",
        "low_cnt = 0;",
        "step_cnt = 0;",
        "wake_guard_cnt = 0;",
        "fan_error_flag = 0;",
        "show_mode = 0;",
        "time_flash_flag = 0;",
    ]
    if plan.config.slide_resistor.enabled:
        power_on_lines.extend(
            (
                "fan_start = 0;",
                "old_res_val = 60000;",
                "res_change_cnt = 0;",
                "slider_target_mode = 0;",
                "Key_Clear();",
            )
        )
    if plan.config.cooling.enabled:
        power_on_lines.extend(
            (
                "COOL_EN = 0;",
                (
                    "YOUWU_COOL = 0;"
                    if plan.config.cooling.presence_detection
                    else "YOUWU_COOL = 1;"
                ),
            )
        )
    if plan.config.light.enabled:
        power_on_lines.extend(
            (
                "LED_ON = 0;",
                (
                    "YOUWU_LED = 0;"
                    if plan.config.light.presence_detection
                    else "YOUWU_LED = 1;"
                ),
            )
        )
        if plan.config.light.mode_profile in ("on_off", "on_off_flash"):
            power_on_lines.append("light_mode = 0;")
    if plan.config.atomizer.enabled:
        power_on_lines.append("wh_mode = 0;")
    if plan.config.encoder.enabled:
        power_on_lines.append("Key_Clear();")
    if _uses_ad_keys(plan):
        power_on_lines.extend(
            f"{key_name} = 1;"
            for key_name in _active_key_names(plan)
        )
    power_on_lines.extend(_double_click_state_reset_lines(plan))
    if plan.alternate_pwm is not None:
        detect_samples = plan.config.motor.detection_samples
        if detect_samples is None:
            raise FanForgeError("compatible motor detection count is missing")
        detect_start = plan.config.self_test_ms // 10 - detect_samples
        self_test_lines.extend(
            (
                f"if(delay_cnt >= {detect_start})",
                "{",
                "    detect_youshua_wushua();",
                "}",
            )
        )
        post_self_test_lines.append(
            "YOUSHUA_WUSHUA = "
            "(youshua_wushua_high_cnt >= "
            "MOTOR_DETECT_HIGH_THRESHOLD) ? 1 : 0;"
        )
        power_on_lines.extend(
            (
                "YOUSHUA_WUSHUA = 0;",
                "youshua_wushua_high_cnt = 0;",
            )
        )
    input_processing_lines = [
        *(("KEY_CHECK();",) if not plan.config.encoder.enabled else ()),
        "KEY_deal();",
        f"if({bat_ready})",
        "{",
        f"    {bat_ready} = 0;",
            "    v_bat_deal();",
            "}",
    ]
    if plan.config.slide_resistor.enabled:
        input_processing_lines.insert(0, _slider_processing(plan))
    ad_key_decode = _ad_key_decode(plan)
    if ad_key_decode:
        input_processing_lines.insert(0, ad_key_decode)
    safe_output_lines = (
        *(
            ()
            if plan.config.motor.kind == "brushed_fixed_duty"
            else ("PWM_FAN = 0;",)
        ),
        "FAN_ON = 0;",
        *(
            ("COOL_EN = 0;",)
            if plan.config.cooling.enabled
            else ()
        ),
        *(("LED_ON = 0;",) if plan.config.light.enabled else ()),
        *(("PWM_WH = 0;",) if plan.config.atomizer.enabled else ()),
    )
    if plan.config.encoder.enabled:
        input_event_clear = _encoder_event_clear()
    elif plan.config.slide_resistor.enabled:
        input_event_clear = _slider_key_clear()
    else:
        input_event_clear = "\n".join(
            tuple(
                line
                for key_name in _active_key_names(plan)
                for line in (
                    f"{key_name.lower()}_short_flag = 0;",
                    f"{key_name.lower()}_long_flag = 0;",
                )
            )
        )
    post_input_reset = (
        (
            "Key_Clear();",
            *(
                (
                    "fan_start = 0;",
                    "old_res_val = 60000;",
                    "res_change_cnt = 0;",
                    "slider_target_mode = 0;",
                )
                if plan.config.slide_resistor.enabled
                else ()
            ),
        )
        if plan.config.encoder.enabled or plan.config.slide_resistor.enabled
        else _double_click_state_reset_lines(plan)
    )
    slots.update(
        {
            "GENERATED_FILE_NOTICE": (
                f"Generated by FanForge for {plan.config.project_name}.\n"
                " * Complete reviewed HS2811 classic fan profile.\n"
                " * Change product parameters in JSON and regenerate."
            ),
            "PIN_AND_IO_DEFINITIONS": _display_pin_definitions(plan),
            "PARAMETER_DEFINITIONS": _parameter_definitions(
                plan, base_motor_parameters
            ),
            "ADDITIONAL_NATIVE_BIT_FLAGS": _native_flags(plan),
            "ADDITIONAL_GLOBAL_STATE": _global_state(
                plan, slots["ADDITIONAL_GLOBAL_STATE"]
            ),
            "PORT_CHANGE_ISR_BODY": _encoder_port_change_isr(plan),
            "HIGH_RATE_ISR_BODY": _encoder_high_rate_isr(
                plan, base_high_rate_isr
            ),
            "FIXED_1MS_ISR_BODY": "\n".join(
                (
                    "if(fan_mode"
                    + (" || wh_mode" if plan.config.atomizer.enabled else "")
                    + " || insert_flag || low_cnt || delay_cnt)",
                    "{",
                    "    smg_188_scan();",
                    "}",
                    "else",
                    "{",
                    "    smg_close();",
                    "}",
                )
            ),
            "SAFE_OUTPUT_INITIALIZATION": "\n".join(safe_output_lines),
            "ADC_COUNTER_AND_PROTECTION_RESET": "\n".join(
                (base_adc_reset, "battery_time_type = 0xFF;")
            ),
            "SYSTEM_SAFE_CLOSE": "\n".join(
                (
                    *pwm_shutdown_lines,
                    *safe_output_lines,
                    "smg_close();",
                    *(
                        (_encoder_runtime_configuration(plan),)
                        if plan.config.encoder.enabled
                        else ()
                    ),
                )
            ),
            "DISPLAY_STATE_TRANSITION": _display_state_transition(plan),
            "INPUT_AND_POWER_STATE_NORMALIZATION": _mode_change(plan),
            "SHARED_STATE_CONSEQUENCES": "",
            "OUTPUT_STATE_NORMALIZATION": "",
            "DISPLAY_BUFFER_BUILD": _show_mode_deal(plan),
            "INPUT_DEBOUNCE_AND_EVENT_GENERATION": (
                ""
                if plan.config.encoder.enabled
                else (
                    _slider_key_check()
                    if plan.config.slide_resistor.enabled
                    else _key_check(plan)
                )
            ),
            "INPUT_EVENT_CLEAR": input_event_clear,
            "DISPLAY_TIMER_RESTART": _show_mode_change(plan),
            "INPUT_EVENT_CONSUMPTION": _key_deal(plan),
            "DISPLAY_SAFE_IDLE_STATE": _display_idle(plan),
            "DISPLAY_SCAN_BODY": _display_scan(plan),
            "FAN_START_RUN_STOP_AND_PROTECTION": (
                base_fan_deal
                if plan.config.motor.kind
                in (
                    "brushless_fixed_voltage_7_3",
                    "brushed_brushless_compat_fixed_voltage_7_3",
                )
                else _fan_deal(plan)
            ),
            "BATTERY_TIMER_MUTUAL_EXCLUSION": _clean_battery_timers(plan),
            "BATTERY_MEASUREMENT_COMPENSATION_MAPPING_AND_CHASE": (
                _battery_deal(plan)
            ),
            "OPTIONAL_FUNCTION_DECLARATIONS": "\n".join(
                part
                for part in (
                    slots["OPTIONAL_FUNCTION_DECLARATIONS"],
                    (
                        "void detect_optional_features(void);"
                        if feature_detection
                        else ""
                    ),
                    (
                        "void wh_deal(void);"
                        if plan.config.atomizer.enabled
                        else ""
                    ),
                )
                if part
            ),
            "OPTIONAL_FUNCTION_IMPLEMENTATIONS": "\n\n".join(
                part
                for part in (
                    slots["OPTIONAL_FUNCTION_IMPLEMENTATIONS"],
                    feature_detection,
                    _atomizer_deal(plan),
                )
                if part
            ),
            "OUTPUT_SHUTDOWN_BEFORE_SLEEP": "\n".join(
                (
                    *pwm_shutdown_lines,
                    *safe_output_lines,
                )
            ),
            "SLEEP_EVENT_CLEAR": _sleep_event_clear(
                plan, slots["SLEEP_EVENT_CLEAR"]
            ),
            "WAKE_COMMON_RESTORE": "\n".join(
                (
                    "WDTE = 1;",
                    "SLCON = 0;",
                    "PAIE = 0;",
                    "WUACON = 0;",
                    "PORTA;",
                    "PAIF = 0;",
                )
            ),
            "WAKE_STABILITY_GUARD": "wake_guard_cnt = 20;",
            "POWER_ON_STATE_INITIALIZATION": "\n".join(power_on_lines),
            "SELF_TEST_OUTPUT_INITIALIZATION": "\n".join(
                (
                    "Data[0] = 0xFF;",
                    "Data[1] = 0xFF;",
                    "Data[2] = 0xFF;",
                    *(("LED_ON = 1;",) if plan.config.light.enabled else ()),
                )
            ),
            "SELF_TEST_FIXED_TICK_BODY": "\n".join(self_test_lines),
            "POST_SELF_TEST_RESTORE": "\n".join(
                (
                    *post_self_test_lines,
                    "Init_System();",
                    *post_input_reset,
                    "Data[0] = 0;",
                    "Data[1] = 0;",
                    "Data[2] = 0;",
                    "fan_mode = 0;",
                    *(
                        ("COOL_EN = 0;",)
                        if plan.config.cooling.enabled
                        else ()
                    ),
                    *(("LED_ON = 0;",) if plan.config.light.enabled else ()),
                    *(
                        ("wh_mode = 0;",)
                        if plan.config.atomizer.enabled
                        else ()
                    ),
                    *(
                        ("light_mode = 0;",)
                        if (
                            plan.config.light.enabled
                            and plan.config.light.mode_profile
                            in ("on_off", "on_off_flash")
                        )
                        else ()
                    ),
                    "show_mode = 0;",
                    "step_cnt = 0;",
                    "wake_guard_cnt = 20;",
                    "mode_change();",
                    "show_mode_deal();",
                )
            ),
            "INPUT_EVENT_SCHEDULER": "",
            "INPUT_PROCESSING_CALLS": "\n".join(input_processing_lines),
            "OUTPUT_PROCESSING_CALLS": "\n".join(
                (
                    "if(wake_guard_cnt) { wake_guard_cnt--; }",
                    "AD_fan_deal();",
                    *(
                        ("wh_deal();",)
                        if plan.config.atomizer.enabled
                        else ()
                    ),
                )
            ),
            "SLEEP_ELIGIBILITY_EXPRESSION": "\n".join(
                (
                    "!low_cnt && !fan_mode && !insert_flag",
                    *(
                        ("&& (SWI_KEY || !charge_num)",)
                        if plan.config.slide_switch.enabled
                        else ()
                    ),
                     *(
                         (
                             "&& !encoder_add_cnt && !encoder_sub_cnt",
                         )
                         if plan.config.encoder.enabled
                         else (
                             "&& KEY",
                             "&& !fan_start && !key_down_flag",
                             "&& !key_short_flag && !key_long_flag",
                         )
                         if plan.config.slide_resistor.enabled
                        else (
                            "&& " + " && ".join(_active_key_names(plan)),
                            (
                                "&& !"
                                + " && !".join(
                                    f"{key_name.lower()}_down_flag"
                                    for key_name in _active_key_names(plan)
                                )
                            ),
                            (
                                "&& !"
                                + " && !".join(
                                    f"{key_name.lower()}_short_flag"
                                    for key_name in _active_key_names(plan)
                                )
                            ),
                            (
                                "&& !"
                                + " && !".join(
                                    f"{key_name.lower()}_long_flag"
                                    for key_name in _active_key_names(plan)
                                )
                            ),
                            *tuple(
                                f"&& !{item.name.lower()}_click_cnt"
                                for item in _double_click_bands(plan)
                            ),
                        )
                    ),
                    "&& !wake_guard_cnt",
                    *(
                        ("&& !light_mode",)
                        if (
                            plan.config.light.enabled
                            and plan.config.light.mode_profile
                            in ("on_off", "on_off_flash")
                        )
                        else ()
                    ),
                    *(
                        ("&& !wh_mode",)
                        if plan.config.atomizer.enabled
                        else ()
                    ),
                    *(
                        (
                            "&& !"
                            + " && !".join(
                                item.enable_symbol for item in pwm_plans
                            )
                            + " "
                            + " ".join(
                                f"&& !{timer}REN"
                                for timer in ("T3", "T4")
                                if any(
                                    item.timer == timer
                                    for item in pwm_plans
                                )
                            )
                            + " && !FAN_ON",
                        )
                    ),
                )
            ),
        }
    )
