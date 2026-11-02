from fanforge.models import (
    AdcRequest,
    GpioRequest,
    ProjectConfig,
    PwmRequest,
    ResourceRequests,
    TimeRequest,
)


def collect_resource_requests(config: ProjectConfig) -> ResourceRequests:
    """Collect fixed resource declarations from reviewed feature modules."""
    motor_owner = f"motor.{config.motor.kind}"
    gpio = (
        ()
        if config.motor.kind == "brushed_fixed_duty"
        else (
            GpioRequest(
                owner=motor_owner,
                role="FAN_ON",
                physical_pin=config.pins["FAN_ON"],
                mode="output",
                initial_level=0,
                pull="none",
                sleep_mode="output",
                sleep_level=0,
                sleep_pull="none",
            ),
        )
    )
    if config.classic_product.enabled:
        key_wake = (
            config.classic_product.sleep_enabled
            and not config.slide_switch.enabled
        )
        if config.classic_product.input_kind in (
            "two_digital_keys_active_low",
            "digital_keys_active_low",
        ):
            key_names = (
                tuple(item.name for item in config.digital_key.keys)
                if config.digital_key.enabled
                else ("KEY1", "KEY2")
            )
            gpio += tuple(
                GpioRequest(
                    owner=f"input.{key_name.lower()}",
                    role=key_name,
                    physical_pin=config.pins[key_name],
                    mode="input",
                    initial_level=None,
                    pull="up",
                    wake=key_wake,
                    sleep_mode="input",
                    sleep_level=None,
                    sleep_pull="up",
                )
                for key_name in key_names
            )
        elif (
            config.classic_product.input_kind
            in (
                "two_ad_keys_active_low_ranges",
                "ad_keys_active_low_ranges",
            )
        ):
            gpio += (
                GpioRequest(
                    owner="input.ad_key",
                    role="AD_KEY",
                    physical_pin=config.pins["AD_KEY"],
                    mode="input",
                    initial_level=None,
                    pull="none",
                    wake=key_wake,
                    sleep_mode="input",
                    sleep_level=None,
                    sleep_pull="up",
                ),
            )
        elif config.classic_product.input_kind == "rotary_encoder_active_low":
            gpio += (
                GpioRequest(
                    owner="input.encoder",
                    role="ENC_A",
                    physical_pin=config.pins["ENC_A"],
                    mode="input",
                    initial_level=None,
                    pull=config.encoder.pull,
                    runtime_change=True,
                    wake=False,
                    sleep_mode="input",
                    sleep_level=None,
                    sleep_pull=config.encoder.pull,
                ),
                GpioRequest(
                    owner="input.encoder",
                    role="ENC_B",
                    physical_pin=config.pins["ENC_B"],
                    mode="input",
                    initial_level=None,
                    pull=config.encoder.pull,
                    runtime_change=False,
                    wake=False,
                    sleep_mode="input",
                    sleep_level=None,
                    sleep_pull=config.encoder.pull,
                ),
            )
        else:
            gpio += (
                GpioRequest(
                    owner="input.slide_resistor",
                    role="KEY",
                    physical_pin=config.pins["KEY"],
                    mode="input",
                    initial_level=None,
                    pull="up",
                    wake=key_wake,
                    sleep_mode="input",
                    sleep_level=None,
                    sleep_pull="up",
                ),
                GpioRequest(
                    owner="input.slide_resistor",
                    role="SLIDER_ON",
                    physical_pin=config.pins["SLIDER_ON"],
                    mode="output",
                    initial_level=1,
                    pull="none",
                    sleep_mode="output",
                    sleep_level=0,
                    sleep_pull="none",
                ),
            )
        if config.slide_switch.enabled:
            gpio += (
                GpioRequest(
                    owner="input.slide_switch",
                    role="SWI_KEY",
                    physical_pin=config.pins["SWI_KEY"],
                    mode="input",
                    initial_level=None,
                    pull="up",
                    wake=config.classic_product.sleep_enabled,
                    sleep_mode="input",
                    sleep_level=None,
                    sleep_pull="up",
                    zero_battery_sleep_mode="input",
                    zero_battery_sleep_level=None,
                    zero_battery_sleep_pull=(
                        "none"
                        if config.slide_switch.zero_battery_disable_pull_wake
                        else "up"
                    ),
                    zero_battery_wake=(
                        False
                        if config.slide_switch.zero_battery_disable_pull_wake
                        else config.classic_product.sleep_enabled
                    ),
                ),
            )
        if config.charging.kind in (
            "chrg_stdby_active_low",
            "chrg_chrg_max_active_low_static",
        ):
            full_role = (
                "STDBY"
                if config.charging.kind == "chrg_stdby_active_low"
                else "CHRG_MAX"
            )
            gpio += (
                GpioRequest(
                    owner="charging.chrg",
                    role="CHRG",
                    physical_pin=config.pins["CHRG"],
                    mode="input",
                    initial_level=None,
                    pull="up",
                    wake=config.classic_product.sleep_enabled,
                    sleep_mode="input",
                    sleep_level=None,
                    sleep_pull="up",
                ),
                GpioRequest(
                    owner=f"charging.{full_role.lower()}",
                    role=full_role,
                    physical_pin=config.pins[full_role],
                    mode="input",
                    initial_level=None,
                    pull="up",
                    wake=config.classic_product.sleep_enabled,
                    sleep_mode="input",
                    sleep_level=None,
                    sleep_pull="up",
                ),
            )
        elif (
            config.charging.kind
            == "insert_active_high_chrg_active_low"
        ):
            gpio += (
                GpioRequest(
                    owner="charging.insert",
                    role="INSERT",
                    physical_pin=config.pins["INSERT"],
                    mode="input",
                    initial_level=None,
                    pull="down",
                    wake=config.classic_product.sleep_enabled,
                    sleep_mode="input",
                    sleep_level=None,
                    sleep_pull="down",
                ),
                GpioRequest(
                    owner="charging.chrg",
                    role="CHRG",
                    physical_pin=config.pins["CHRG"],
                    mode="input",
                    initial_level=None,
                    pull="up",
                    wake=config.classic_product.sleep_enabled,
                    sleep_mode="input",
                    sleep_level=None,
                    sleep_pull="up",
                ),
            )
        if config.cooling.enabled:
            gpio += (
                GpioRequest(
                    owner="cooling.output",
                    role="COOL_EN",
                    physical_pin=config.pins["COOL_EN"],
                    mode="output",
                    initial_level=0,
                    pull="none",
                    sleep_mode="output",
                    sleep_level=0,
                    sleep_pull="none",
                ),
            )
        if config.light.enabled:
            gpio += (
                GpioRequest(
                    owner="light.output",
                    role="LED_ON",
                    physical_pin=config.pins["LED_ON"],
                    mode="output",
                    initial_level=0,
                    pull="none",
                    sleep_mode="output",
                    sleep_level=0,
                    sleep_pull="none",
                ),
            )
        gpio += tuple(
            GpioRequest(
                owner=f"display.{config.display.profile}",
                role=f"IO_LED_{index}",
                physical_pin=config.pins[f"IO_LED_{index}"],
                mode="output",
                initial_level=0,
                pull="none",
                sleep_mode="output",
                sleep_level=0,
                sleep_pull="none",
            )
            for index in range(1, config.display.pin_count + 1)
        )

    motor_pwm_role = (
        "FAN_ON"
        if config.motor.kind == "brushed_fixed_duty"
        else "PWM_FAN"
    )
    pwm = (
        PwmRequest(
            owner=motor_owner,
            role=motor_pwm_role,
            physical_pin=config.pins[motor_pwm_role],
            target_frequency_hz=config.motor.pwm_frequency_hz,
            clock_source=config.motor.pwm_clock_source,
            prescaler=config.motor.pwm_prescaler,
        ),
    )
    if config.atomizer.enabled:
        pwm += (
            PwmRequest(
                owner="atomizer.output",
                role="PWM_WH",
                physical_pin=config.pins["PWM_WH"],
                target_frequency_hz=config.atomizer.pwm_frequency_hz,
                clock_source=config.atomizer.pwm_clock_source,
                prescaler=config.atomizer.pwm_prescaler,
            ),
        )

    if config.motor.kind == "brushed_fixed_duty":
        adc = ()
    elif config.motor.kind == "brushless_fixed_duty":
        adc = (
            AdcRequest(
                owner="fan_voltage_protection.fixed_duty",
                role="AD_FAN",
                source_kind="external_pin",
                physical_pin=config.pins["AD_FAN"],
                reference=config.fan_protection.overvoltage_adc_reference,
                clock=config.fan_protection.adc_clock,
                discard_samples=config.fan_protection.discard_samples,
                average_samples=config.fan_protection.average_samples,
                secondary_average_samples=1,
                result_name="AD_FAN_VALUE",
                scan_order=20,
                reset_semantics="system_reset",
                ready_flag_name="ad_fan_ready_flag",
            ),
        )
    else:
        adc = (
            AdcRequest(
                owner="motor.fixed_voltage",
                role="AD_FAN",
                source_kind="external_pin",
                physical_pin=config.pins["AD_FAN"],
                reference=config.fan_protection.adc_reference,
                clock=config.fan_protection.adc_clock,
                discard_samples=config.fan_protection.discard_samples,
                average_samples=config.fan_protection.average_samples,
                secondary_average_samples=1,
                result_name="AD_FAN_VALUE",
                scan_order=20,
                reset_semantics="system_reset",
                ready_flag_name="ad_fan_ready_flag",
            ),
        )
    if config.battery_monitor.enabled:
        adc += (
            AdcRequest(
                owner="battery.voltage",
                role="ADC_BAT",
                source_kind="internal_vdd_div4",
                physical_pin=None,
                reference="2v",
                clock="fcpu",
                discard_samples=2,
                average_samples=8,
                secondary_average_samples=16,
                result_name="ADC_BAT_VALUE",
                scan_order=10,
                reset_semantics="system_reset",
                ready_flag_name="adc_bat_ready_flag",
            ),
        )
    if config.ad_key.enabled:
        adc += (
            AdcRequest(
                owner="input.ad_key",
                role="AD_KEY",
                source_kind="external_pin",
                physical_pin=config.pins["AD_KEY"],
                reference=config.ad_key.adc_reference,
                clock=config.ad_key.adc_clock,
                discard_samples=config.ad_key.discard_samples,
                average_samples=config.ad_key.average_samples,
                secondary_average_samples=1,
                result_name="AD_KEY_VALUE",
                scan_order=30,
                reset_semantics="system_reset",
                ready_flag_name="ad_key_ready_flag",
            ),
        )
    if config.slide_resistor.enabled:
        adc += (
            AdcRequest(
                owner="input.slide_resistor",
                role="AD_SLIDER",
                source_kind="external_pin",
                physical_pin=config.pins["AD_SLIDER"],
                reference=config.slide_resistor.adc_reference,
                clock=config.slide_resistor.adc_clock,
                discard_samples=config.slide_resistor.discard_samples,
                average_samples=config.slide_resistor.accumulation_samples,
                secondary_average_samples=1,
                result_name="AD_SLIDER_SUM",
                scan_order=30,
                reset_semantics="system_reset",
                ready_flag_name="ad_slider_ready_flag",
                result_mode="sum",
            ),
        )

    time = (
        TimeRequest(
            owner="core.scheduler",
            role="adc_1ms_tick",
            period_ms=1,
            phase="system",
            reset_semantics="continuous",
        ),
        TimeRequest(
            owner="core.scheduler",
            role="main_10ms_tick",
            period_ms=10,
            phase="system",
            reset_semantics="continuous",
        ),
        TimeRequest(
            owner="core.scheduler",
            role="sleep_100ms_tick",
            period_ms=100,
            phase="system",
            reset_semantics="continuous",
        ),
        TimeRequest(
            owner=motor_owner,
            role="fan_control_tick",
            period_ms=10,
            phase="system",
            reset_semantics="continuous",
        ),
    )
    if config.motor.kind in (
        "brushless_fixed_voltage_7_3",
        "brushed_brushless_compat_fixed_voltage_7_3",
    ):
        if config.motor.voltage_slow_adjust_ms is not None:
            time += (
                TimeRequest(
                    owner=motor_owner,
                    role="slow_adjust",
                    period_ms=config.motor.voltage_slow_adjust_ms,
                    phase="motor_voltage_slow_adjust",
                    reset_semantics="state_reset",
                ),
            )
    if config.classic_product.enabled:
        curve = config.battery_monitor.curve
        if curve is None:
            raise ValueError("classic product requires a battery curve")
        display_page_requests = (
            (
                TimeRequest(
                    owner="display.page",
                    role="page_3s",
                    period_ms=3000,
                    phase="display_page",
                    reset_semantics="event_reset",
                ),
            )
            if config.display.behavior_profile
            == "gear_3s_battery_3s_gear"
            else (
                TimeRequest(
                    owner="display.page",
                    role="gear_event",
                    period_ms=config.display.gear_event_ms,
                    phase="display_gear_event",
                    reset_semantics="event_reset",
                ),
                *(
                    (
                        TimeRequest(
                            owner="display.page",
                            role="battery_preview",
                            period_ms=(
                                config.display.normal_battery_preview_ms
                            ),
                            phase="display_battery_preview",
                            reset_semantics="event_reset",
                        ),
                    )
                    if config.display.normal_battery_preview_ms
                    else ()
                ),
            )
        )
        time += (
            *display_page_requests,
            TimeRequest(
                owner="display.flash",
                role="flash_500ms",
                period_ms=500,
                phase="system",
                reset_semantics="continuous",
            ),
            *(
                (
                    TimeRequest(
                        owner="battery.charge",
                        role="charge_active",
                        period_ms=curve.charge_active_period_ms,
                        phase="battery_charge_active",
                        reset_semantics="state_reset",
                    ),
                    TimeRequest(
                        owner="battery.charge",
                        role="charge_full",
                        period_ms=curve.charge_full_period_ms,
                        phase="battery_charge_full",
                        reset_semantics="state_reset",
                    ),
                )
                if config.charging.enabled
                else ()
            ),
            TimeRequest(
                owner="battery.discharge",
                role="discharge",
                period_ms=curve.discharge_period_ms,
                phase="battery_discharge",
                reset_semantics="state_reset",
            ),
            TimeRequest(
                owner="battery.discharge",
                role="low_discharge",
                period_ms=curve.low_discharge_period_ms,
                phase="battery_low_discharge",
                reset_semantics="state_reset",
            ),
        )
        if config.encoder.enabled:
            time += (
                TimeRequest(
                    owner="input.encoder",
                    role="acceleration_window",
                    period_ms=config.encoder.acceleration_window_ms,
                    phase="encoder_acceleration",
                    reset_semantics="continuous",
                ),
            )
        for key in config.ad_key.key_bands:
            if key.double_action != "none":
                time += (
                    TimeRequest(
                        owner=f"input.{key.name.lower()}",
                        role="double_click_window",
                        period_ms=config.ad_key.double_click_ms,
                        phase=f"{key.name.lower()}_double_click",
                        reset_semantics="event_reset",
                    ),
                )
        for key in config.digital_key.keys:
            if key.double_action != "none":
                time += (
                    TimeRequest(
                        owner=f"input.{key.name.lower()}",
                        role="double_click_window",
                        period_ms=config.digital_key.double_click_ms,
                        phase=f"{key.name.lower()}_double_click",
                        reset_semantics="event_reset",
                    ),
                )

    return ResourceRequests(gpio=gpio, pwm=pwm, adc=adc, time=time)
