import json
from itertools import product
from pathlib import Path
from typing import Any

from fanforge.errors import ConfigError, ResourceConflictError
from fanforge.models import (
    AdcChannelPlan,
    AdcRequest,
    AdcResourcePlan,
    GenerationPlan,
    GpioPlan,
    ProjectConfig,
    PwmPlan,
    PwmRequest,
    ResourceRequests,
    TimeRequest,
    TimeResourcePlan,
    TimeSignalPlan,
    TimerPlan,
)
from fanforge.modules import collect_resource_requests


PWM_DIVIDER_CODES = {
    1: 0b111,
    2: 0b110,
    4: 0b101,
    8: 0b100,
    16: 0b011,
    32: 0b010,
    64: 0b001,
    128: 0b000,
}
T1_DIVIDER_CODES = {1: 0b00, 2: 0b01, 4: 0b10, 8: 0b11}
ADC_CLOCK_VALUES = {
    "fcpu_div16": 0x00,
    "fcpu_div8": 0x10,
    "fcpu": 0x40,
    "fcpu_div2": 0x50,
}
ADC_WAIT_LIMITS = {
    "fcpu": 50,
    "fcpu_div2": 50,
    "fcpu_div8": 128,
    "fcpu_div16": 250,
}
ADC_REFERENCE_VALUES = {
    "2v": 0x00,
    "3v": 0x01,
    "4v": 0x02,
    "vdd": 0x03,
}
TIME_PARENT_CANDIDATES_MS = (60000, 500, 10, 1)
MAX_TIME_PERIOD_MS = 4 * 60 * 60 * 1000
MIN_7_3_CYCLES_PER_AD_UPDATE = 8
HIGH_RATE_ADC_PERIOD_US = 100
HIGH_RATE_ADC_SAMPLES_PER_CHANNEL = 100
HIGH_RATE_ADC_DISCARD_SAMPLES = 4
HIGH_RATE_ADC_GROUP_SIZE = 8
HIGH_RATE_ADC_GROUP_COUNT = 12


def load_chip_database(config: ProjectConfig) -> dict[str, Any]:
    if config.mcu.model != "HS16P2811" or config.mcu.package != "SOP16":
        raise ConfigError("version 0.4 supports only HS16P2811 SOP16")
    path = Path(__file__).parent / "chips" / "hs2811_sop16.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _pin(chip: dict[str, Any], physical_pin: int) -> dict[str, Any]:
    try:
        pin = chip["pins"][str(physical_pin)]
    except KeyError as exc:
        raise ConfigError(f"physical pin {physical_pin} does not exist") from exc
    if pin["kind"] != "gpio":
        raise ConfigError(
            f"physical pin {physical_pin} is {pin['name']}, not a GPIO pin"
        )
    return pin


def _check_pin_conflicts(
    chip: dict[str, Any], requests: ResourceRequests
) -> dict[str, str]:
    owners_by_pin: dict[int, tuple[str, str]] = {}
    resolved: dict[str, str] = {}
    all_requests = (*requests.gpio, *requests.pwm)
    for request in all_requests:
        pin = _pin(chip, request.physical_pin)
        prior = owners_by_pin.get(request.physical_pin)
        if prior is not None:
            raise ResourceConflictError(
                f"pin {request.physical_pin} ({pin['name']}) is requested by "
                f"{prior[0]}.{prior[1]} and {request.owner}.{request.role}"
            )
        owners_by_pin[request.physical_pin] = (request.owner, request.role)
        resolved[request.role] = pin["name"]

    for request in requests.adc:
        if request.source_kind != "external_pin":
            continue
        if request.physical_pin is None:
            raise ResourceConflictError(
                f"{request.owner}.{request.role} requires an external ADC pin"
            )
        pin = _pin(chip, request.physical_pin)
        prior = owners_by_pin.get(request.physical_pin)
        if (
            prior is not None
            and prior[0] != "__adc__"
            and prior != (request.owner, request.role)
        ):
            raise ResourceConflictError(
                f"pin {request.physical_pin} ({pin['name']}) is requested by "
                f"{prior[0]}.{prior[1]} and {request.owner}.{request.role}"
            )
        if prior is None:
            owners_by_pin[request.physical_pin] = ("__adc__", request.role)
        resolved[request.role] = pin["name"]
    return resolved


def _plan_timer(config: ProjectConfig) -> TimerPlan:
    source_hz = config.mcu.fcpu_hz
    candidates = (
        (config.timebase.t1_prescaler,)
        if config.timebase.t1_prescaler is not None
        else (1, 2, 4, 8)
    )
    valid: list[tuple[float, int, int, float]] = []
    for prescaler in candidates:
        exact_count = (
            source_hz * config.timebase.interrupt_us / 1_000_000 / prescaler
        )
        count = round(exact_count)
        if not 1 <= count <= 65535:
            continue
        actual_us = count * prescaler * 1_000_000 / source_hz
        error_us = abs(actual_us - config.timebase.interrupt_us)
        valid.append((error_us, prescaler, count, actual_us))
    if not valid:
        raise ResourceConflictError(
            "T1 cannot produce the requested interrupt period with the selected clock"
        )

    _, prescaler, count, actual_us = min(valid, key=lambda item: (item[0], item[1]))
    reload_value = 65536 - count
    t1con = (T1_DIVIDER_CODES[prescaler] << 4) | 0x01
    if 1000 % config.timebase.interrupt_us:
        raise ResourceConflictError(
            "T1 interrupt period must divide the reviewed 1ms scheduler root"
        )
    return TimerPlan(
        source_hz=source_hz,
        prescaler=prescaler,
        timer_hz=source_hz // prescaler,
        target_us=config.timebase.interrupt_us,
        count=count,
        reload_value=reload_value,
        actual_us=actual_us,
        t1con=t1con,
        subticks_per_ms=1000 // config.timebase.interrupt_us,
    )


def _time_label(period_ms: int) -> str:
    if period_ms % 3_600_000 == 0:
        return f"{period_ms // 3_600_000}h"
    if period_ms % 60_000 == 0:
        return f"{period_ms // 60_000}min"
    if period_ms % 1_000 == 0:
        return f"{period_ms // 1_000}s"
    return f"{period_ms}ms"


def _c_identifier(value: str) -> str:
    result = "".join(
        char.lower() if char.isascii() and char.isalnum() else "_"
        for char in value
    )
    result = "_".join(part for part in result.split("_") if part)
    if not result:
        raise ResourceConflictError("time resource name cannot be empty")
    if result[0].isdigit():
        result = "t_" + result
    return result


def _time_parent(period_ms: int) -> int:
    for candidate in TIME_PARENT_CANDIDATES_MS:
        if candidate >= period_ms:
            continue
        if period_ms % candidate:
            continue
        ticks = period_ms // candidate
        if ticks <= 255:
            return candidate
    raise ResourceConflictError(
        f"{period_ms}ms cannot be derived with the reviewed u8 time hierarchy"
    )


def plan_time_resources(requests: tuple[TimeRequest, ...]) -> TimeResourcePlan:
    if not requests:
        raise ResourceConflictError("at least one time resource is required")

    grouped: dict[tuple[int, str, str], list[TimeRequest]] = {}
    for request in requests:
        if request.period_ms < 1 or request.period_ms > MAX_TIME_PERIOD_MS:
            raise ResourceConflictError(
                f"time request {request.owner}.{request.role} must be 1ms..4h"
            )
        if (
            request.period_ms == 1
            and (
                request.phase != "system"
                or request.reset_semantics != "continuous"
            )
        ):
            raise ResourceConflictError(
                "the reviewed 1ms root must use system/continuous semantics"
            )
        key = (request.period_ms, request.phase, request.reset_semantics)
        grouped.setdefault(key, []).append(request)

    known_periods = {key[0] for key in grouped}
    parent_periods: set[int] = set()
    pending = list(known_periods)
    while pending:
        period_ms = pending.pop()
        if period_ms == 1:
            continue
        parent_ms = _time_parent(period_ms)
        parent_periods.add(parent_ms)
        if parent_ms not in known_periods:
            known_periods.add(parent_ms)
            pending.append(parent_ms)

    for period_ms in parent_periods:
        key = (period_ms, "system", "continuous")
        grouped.setdefault(key, [])

    plans: list[TimeSignalPlan] = []
    role_flags: dict[str, str] = {}
    role_counters: dict[str, str | None] = {}
    used_names: set[str] = set()
    noncanonical_stem_counts: dict[str, int] = {}

    for key, group_requests in grouped.items():
        period_ms, phase, reset_semantics = key
        if not group_requests:
            continue
        if phase == "system" and reset_semantics == "continuous":
            continue
        first = sorted(
            group_requests, key=lambda item: (item.owner, item.role)
        )[0]
        base_stem = f"{_c_identifier(first.role)}_{_time_label(period_ms)}"
        noncanonical_stem_counts[base_stem] = (
            noncanonical_stem_counts.get(base_stem, 0) + 1
        )

    for key in sorted(grouped, key=lambda item: (item[0], item[1], item[2])):
        period_ms, phase, reset_semantics = key
        group_requests = sorted(
            grouped[key], key=lambda item: (item.owner, item.role)
        )
        internal = not group_requests
        canonical = phase == "system" and reset_semantics == "continuous"
        label = _time_label(period_ms)

        if canonical:
            stem = f"time_{label}"
        else:
            first = group_requests[0]
            base_stem = f"{_c_identifier(first.role)}_{label}"
            if noncanonical_stem_counts[base_stem] > 1:
                stem = (
                    f"{_c_identifier(first.owner)}_"
                    f"{_c_identifier(first.role)}_{label}"
                )
            else:
                stem = base_stem

        flag_name = None if internal else f"{stem}_flag"
        counter_name = None if period_ms == 1 else f"{stem}_cnt"
        for name in (flag_name, counter_name):
            if name is None:
                continue
            if name in used_names:
                raise ResourceConflictError(f"duplicate generated time name: {name}")
            used_names.add(name)

        parent_ms = None if period_ms == 1 else _time_parent(period_ms)
        ticks = 1 if parent_ms is None else period_ms // parent_ms
        roles = tuple(f"{item.owner}.{item.role}" for item in group_requests)

        for request, role_key in zip(group_requests, roles):
            if flag_name is None:
                raise ResourceConflictError(
                    f"internal time signal cannot own request {role_key}"
                )
            role_flags[role_key] = flag_name
            role_counters[role_key] = counter_name

        plans.append(
            TimeSignalPlan(
                period_ms=period_ms,
                parent_period_ms=parent_ms,
                ticks_per_period=ticks,
                phase=phase,
                reset_semantics=reset_semantics,
                flag_name=flag_name,
                counter_name=counter_name,
                request_roles=roles,
                internal=internal,
            )
        )

    return TimeResourcePlan(
        base_period_ms=1,
        signals=tuple(plans),
        role_flags=role_flags,
        role_counters=role_counters,
    )


def _build_pwm_candidate(
    config: ProjectConfig,
    chip: dict[str, Any],
    request: PwmRequest,
    timer: str,
    route: dict[str, int],
    validate_motor_curve: bool = True,
) -> PwmPlan:
    pin = _pin(chip, request.physical_pin)

    source_hz = (
        config.mcu.oscillator_hz
        if request.clock_source == "fosc"
        else config.mcu.fcpu_hz // 2
    )
    dividers = (
        (request.prescaler,)
        if request.prescaler is not None
        else tuple(PWM_DIVIDER_CODES)
    )
    valid: list[tuple[float, int, int, float]] = []
    for prescaler in dividers:
        exact_period_count = source_hz / prescaler / request.target_frequency_hz
        period_count = round(exact_period_count)
        if not 1 <= period_count <= 1024:
            continue
        actual_hz = source_hz / prescaler / period_count
        error_percent = (
            abs(actual_hz - request.target_frequency_hz)
            * 100
            / request.target_frequency_hz
        )
        valid.append((error_percent, prescaler, period_count, actual_hz))
    if not valid:
        raise ResourceConflictError(
            f"{timer} cannot generate {request.target_frequency_hz}Hz "
            f"on {pin['name']}"
        )

    error_percent, prescaler, period_count, actual_hz = min(
        valid, key=lambda item: (item[0], item[1])
    )
    if (
        validate_motor_curve
        and config.classic_product.enabled
        and config.motor.kind
        in ("brushless_fixed_duty", "brushed_fixed_duty")
    ):
        if (
            config.motor.duty_base_count is None
            or config.motor.duty_gear_divisor is None
        ):
            raise ResourceConflictError("classic motor duty curve is incomplete")
        maximum_duty = (
            config.motor.duty_base_count
            + config.classic_product.maximum_gear
            // config.motor.duty_gear_divisor
        )
        if maximum_duty > period_count - 1:
            raise ResourceConflictError(
                "classic motor duty curve exceeds the selected PWM period"
            )
    if (
        validate_motor_curve
        and config.motor.kind in (
            "brushless_fixed_voltage_7_3",
            "brushed_brushless_compat_fixed_voltage_7_3",
        )
    ):
        if config.motor.voltage_pwm_max_count is None:
            raise ResourceConflictError(
                "fixed-voltage motor PWM range is incomplete"
            )
        if config.motor.voltage_pwm_max_count + 1 > period_count - 1:
            raise ResourceConflictError(
                "fixed-voltage 7+3 maximum duty exceeds the selected PWM period"
            )
    channel = route["channel"]
    route_code = route["route_code"]
    if timer == "T4":
        route_register = "PWMSEL1"
        route_value = route_code << 2
        duty_register = "T4DL"
        duty_high_register = "T4DH"
        enable_symbol = "T4PWMEN"
    elif channel == 4:
        route_register = "PWMSEL1"
        route_value = route_code
        duty_register = f"T3D{channel}L"
        duty_high_register = f"T3D{channel}H"
        enable_symbol = f"T3PWM{channel}EN"
    else:
        route_register = "PWMSEL"
        route_value = route_code << (channel * 2)
        duty_register = f"T3D{channel}L"
        duty_high_register = f"T3D{channel}H"
        enable_symbol = f"T3PWM{channel}EN"

    t3c1 = PWM_DIVIDER_CODES[prescaler]
    if request.clock_source == "fosc":
        t3c1 |= 0x10

    return PwmPlan(
        owner=request.owner,
        role=request.role,
        timer=timer,
        physical_pin=request.physical_pin,
        gpio_name=pin["name"],
        channel=channel,
        route_code=route_code,
        route_register=route_register,
        route_mask=route_value,
        source_hz=source_hz,
        clock_source=request.clock_source,
        prescaler=prescaler,
        period_register=period_count - 1,
        actual_frequency_hz=actual_hz,
        error_percent=error_percent,
        t3c1=t3c1,
        duty_register=duty_register,
        duty_high_register=duty_high_register,
        enable_symbol=enable_symbol,
    )


def _pwm_candidates(
    config: ProjectConfig,
    chip: dict[str, Any],
    request: PwmRequest,
    validate_motor_curve: bool,
) -> tuple[PwmPlan, ...]:
    pin = _pin(chip, request.physical_pin)
    candidates: list[PwmPlan] = []
    for timer, capability in (
        ("T3", "t3_pwm"),
        ("T4", "t4_pwm"),
    ):
        for route in pin.get(capability, []):
            candidates.append(
                _build_pwm_candidate(
                    config,
                    chip,
                    request,
                    timer,
                    route,
                    validate_motor_curve,
                )
            )
    if not candidates:
        raise ResourceConflictError(
            f"pin {request.physical_pin} ({pin['name']}) has no PWM output"
        )
    return tuple(candidates)


def _plan_pwm(
    config: ProjectConfig,
    chip: dict[str, Any],
    requests: ResourceRequests,
    request_override: PwmRequest | None = None,
    validate_motor_curve: bool = True,
) -> PwmPlan:
    if request_override is None and len(requests.pwm) != 1:
        raise ResourceConflictError(
            "single-PWM planner received multiple PWM requests"
        )
    request = request_override or requests.pwm[0]
    pin = _pin(chip, request.physical_pin)
    routes = pin.get("t3_pwm", [])
    if not routes:
        raise ResourceConflictError(
            f"pin {request.physical_pin} ({pin['name']}) cannot output T3 PWM"
        )
    route = min(routes, key=lambda item: item["channel"])
    return _build_pwm_candidate(
        config,
        chip,
        request,
        "T3",
        route,
        validate_motor_curve,
    )


def _alternate_pwm_request(config: ProjectConfig) -> PwmRequest | None:
    if (
        config.motor.kind
        != "brushed_brushless_compat_fixed_voltage_7_3"
    ):
        return None
    if config.motor.brushed_pwm_frequency_hz is None:
        raise ResourceConflictError("compatible motor brushed PWM is incomplete")
    return PwmRequest(
        owner="motor.brushed_compatible",
        role="FAN_ON",
        physical_pin=config.pins["FAN_ON"],
        target_frequency_hz=config.motor.brushed_pwm_frequency_hz,
        clock_source=config.motor.pwm_clock_source,
        prescaler=config.motor.pwm_prescaler,
    )


def _validate_alternate_pwm_curve(
    config: ProjectConfig, alternate: PwmPlan
) -> None:
    if (
        config.motor.brushed_duty_base_count is None
        or config.motor.brushed_duty_gear_divisor is None
    ):
        raise ResourceConflictError("compatible brushed duty curve is incomplete")
    maximum_duty = (
        config.motor.brushed_duty_base_count
        + config.classic_product.maximum_gear
        // config.motor.brushed_duty_gear_divisor
    )
    if maximum_duty > alternate.period_register:
        raise ResourceConflictError(
            "compatible brushed duty curve exceeds its PWM period"
        )


def _plan_alternate_pwm(
    config: ProjectConfig,
    chip: dict[str, Any],
    requests: ResourceRequests,
) -> PwmPlan | None:
    request = _alternate_pwm_request(config)
    if request is None:
        return None
    alternate = _plan_pwm(
        config,
        chip,
        requests,
        request_override=request,
        validate_motor_curve=False,
    )
    _validate_alternate_pwm_curve(config, alternate)
    return alternate


def _pwm_group_is_compatible(plans: tuple[PwmPlan, ...]) -> bool:
    occupied: set[tuple[str, int]] = set()
    timer_settings: dict[str, tuple[int, int, int]] = {}
    for pwm in plans:
        resource = (pwm.timer, pwm.channel)
        if resource in occupied:
            return False
        occupied.add(resource)
        settings = (
            pwm.source_hz,
            pwm.prescaler,
            pwm.period_register,
        )
        previous = timer_settings.get(pwm.timer)
        if previous is not None and previous != settings:
            return False
        timer_settings[pwm.timer] = settings
    return True


def _plan_pwm_resources(
    config: ProjectConfig,
    chip: dict[str, Any],
    requests: ResourceRequests,
) -> tuple[PwmPlan, PwmPlan | None, tuple[PwmPlan, ...]]:
    if len(requests.pwm) == 1:
        primary = _plan_pwm(config, chip, requests)
        alternate = _plan_alternate_pwm(config, chip, requests)
        return primary, alternate, ()

    primary_request = requests.pwm[0]
    auxiliary_requests = tuple(requests.pwm[1:])
    alternate_request = _alternate_pwm_request(config)
    all_requests = (
        primary_request,
        *auxiliary_requests,
        *((alternate_request,) if alternate_request is not None else ()),
    )
    candidate_sets = tuple(
        _pwm_candidates(
            config,
            chip,
            request,
            validate_motor_curve=(request is primary_request),
        )
        for request in all_requests
    )
    valid: list[tuple[tuple[int, ...], tuple[PwmPlan, ...]]] = []
    for combination in product(*candidate_sets):
        primary = combination[0]
        auxiliaries = combination[1 : 1 + len(auxiliary_requests)]
        alternate = (
            combination[-1] if alternate_request is not None else None
        )
        brushless_group = (primary, *auxiliaries)
        brushed_group = (
            ((alternate, *auxiliaries))
            if alternate is not None
            else ()
        )
        if not _pwm_group_is_compatible(brushless_group):
            continue
        if brushed_group and not _pwm_group_is_compatible(brushed_group):
            continue
        score = (
            sum(item.timer == "T4" for item in combination),
            1 if primary.timer != "T3" else 0,
            *(
                item.channel + (10 if item.timer == "T4" else 0)
                for item in combination
            ),
        )
        valid.append((score, combination))
    if not valid:
        roles = ", ".join(request.role for request in all_requests)
        raise ResourceConflictError(
            "PWM requests cannot share HS2811 Timer3/Timer4 resources "
            f"without a channel or frequency conflict: {roles}"
        )

    _, selected = min(valid, key=lambda item: item[0])
    primary = selected[0]
    auxiliaries = selected[1 : 1 + len(auxiliary_requests)]
    alternate = selected[-1] if alternate_request is not None else None
    if alternate is not None:
        _validate_alternate_pwm_curve(config, alternate)
    return primary, alternate, tuple(auxiliaries)


def _validate_adc_request(request: AdcRequest) -> None:
    if request.source_kind not in ("external_pin", "internal_vdd_div4"):
        raise ResourceConflictError(
            f"unsupported ADC source for {request.owner}.{request.role}: "
            f"{request.source_kind}"
        )
    if request.reference not in ADC_REFERENCE_VALUES:
        raise ResourceConflictError(
            f"unsupported ADC reference for {request.owner}.{request.role}: "
            f"{request.reference}"
        )
    if request.clock not in ADC_CLOCK_VALUES:
        raise ResourceConflictError(
            f"unsupported ADC clock for {request.owner}.{request.role}: "
            f"{request.clock}"
        )
    if request.result_mode not in ("average", "sum"):
        raise ResourceConflictError(
            f"{request.owner}.{request.role} ADC result mode must be "
            "average or sum"
        )
    if request.discard_samples < 0:
        raise ResourceConflictError(
            f"{request.owner}.{request.role} ADC discard count cannot be negative"
        )
    if (
        request.average_samples < 1
        or request.average_samples > 16
        or request.average_samples & (request.average_samples - 1)
    ):
        raise ResourceConflictError(
            f"{request.owner}.{request.role} ADC average must be 1,2,4,8,or16"
        )
    if (
        request.secondary_average_samples < 1
        or request.secondary_average_samples > 16
        or request.secondary_average_samples
        & (request.secondary_average_samples - 1)
    ):
        raise ResourceConflictError(
            f"{request.owner}.{request.role} secondary ADC average must be "
            "1,2,4,8,or16"
        )
    if 4095 * request.average_samples > 65535:
        raise ResourceConflictError(
            f"{request.owner}.{request.role} first ADC accumulation overflows u16"
        )
    if 4095 * request.secondary_average_samples > 65535:
        raise ResourceConflictError(
            f"{request.owner}.{request.role} second ADC accumulation overflows u16"
        )
    if (
        request.result_mode == "sum"
        and request.secondary_average_samples != 1
    ):
        raise ResourceConflictError(
            f"{request.owner}.{request.role} summed ADC result cannot use "
            "secondary averaging"
        )
    result_name = request.result_name
    if (
        not result_name
        or not result_name.isascii()
        or not (result_name[0].isalpha() or result_name[0] == "_")
        or any(not (char.isalnum() or char == "_") for char in result_name)
    ):
        raise ResourceConflictError(
            f"{request.owner}.{request.role} has invalid ADC result name"
        )
    if request.scan_order < 0:
        raise ResourceConflictError(
            f"{request.owner}.{request.role} ADC scan order cannot be negative"
        )
    if not request.reset_semantics:
        raise ResourceConflictError(
            f"{request.owner}.{request.role} ADC reset semantics cannot be empty"
        )
    if request.ready_flag_name is not None:
        ready_name = request.ready_flag_name
        if (
            not ready_name
            or not ready_name.isascii()
            or not (ready_name[0].isalpha() or ready_name[0] == "_")
            or any(not (char.isalnum() or char == "_") for char in ready_name)
        ):
            raise ResourceConflictError(
                f"{request.owner}.{request.role} has invalid ADC ready flag name"
            )


def plan_adc_resources(
    chip: dict[str, Any],
    requests: tuple[AdcRequest, ...],
    *,
    high_rate: bool = False,
    sample_period_us: int = 1000,
    source_hz: int | None = None,
) -> AdcResourcePlan:
    if not requests:
        raise ResourceConflictError("at least one ADC request is required")

    for request in requests:
        _validate_adc_request(request)

    if high_rate:
        if sample_period_us != HIGH_RATE_ADC_PERIOD_US:
            raise ResourceConflictError(
                "fixed-voltage high-rate ADC must sample every 100us"
            )
        discard_samples = HIGH_RATE_ADC_DISCARD_SAMPLES
        average_samples = (
            HIGH_RATE_ADC_SAMPLES_PER_CHANNEL
            - HIGH_RATE_ADC_DISCARD_SAMPLES
        )
        if average_samples % HIGH_RATE_ADC_GROUP_SIZE:
            raise ResourceConflictError(
                "high-rate ADC valid samples must be a multiple of the "
                "8-phase 7+3 period"
            )
        if source_hz is None or source_hz <= 0:
            raise ResourceConflictError(
                "high-rate ADC planning requires the MCU instruction clock"
            )
        adc_clock_divider = {
            "fcpu": 1,
            "fcpu_div2": 2,
            "fcpu_div8": 8,
            "fcpu_div16": 16,
        }
        conversion_times = tuple(
            (
                64 * adc_clock_divider[request.clock] * 1_000_000
                + source_hz
                - 1
            )
            // source_hz
            for request in requests
        )
        worst_conversion_us = max(conversion_times)
        if worst_conversion_us >= sample_period_us:
            raise ResourceConflictError(
                "ADC conversion worst-case time is not below the high-rate "
                f"sample period: {worst_conversion_us}us >= "
                f"{sample_period_us}us"
            )
        if 4095 * HIGH_RATE_ADC_GROUP_SIZE > 65535:
            raise ResourceConflictError(
                "high-rate ADC group accumulation overflows u16"
            )
        if 4095 * HIGH_RATE_ADC_GROUP_COUNT > 65535:
            raise ResourceConflictError(
                "high-rate ADC group-sum accumulation overflows u16"
            )
    else:
        first_stage_filters = {
            (request.discard_samples, request.average_samples)
            for request in requests
        }
        if len(first_stage_filters) != 1:
            raise ResourceConflictError(
                "initial multi-ADC planner requires one shared discard/average "
                "group"
            )
        discard_samples, average_samples = next(iter(first_stage_filters))

    grouped: dict[tuple[Any, ...], list[AdcRequest]] = {}
    for request in requests:
        source_id = (
            request.physical_pin
            if request.source_kind == "external_pin"
            else request.source_kind
        )
        request_discard = discard_samples if high_rate else request.discard_samples
        request_average = average_samples if high_rate else request.average_samples
        key = (
            request.source_kind,
            source_id,
            request.reference,
            request.clock,
            request_discard,
            request_average,
            request.secondary_average_samples,
            request.result_mode,
            request.reset_semantics,
        )
        grouped.setdefault(key, []).append(request)

    channels: list[AdcChannelPlan] = []
    role_results: dict[str, str] = {}
    used_result_names: set[str] = set()

    for key, group in grouped.items():
        group_requests = sorted(group, key=lambda item: (item.owner, item.role))
        result_names = {request.result_name for request in group_requests}
        scan_orders = {request.scan_order for request in group_requests}
        ready_flag_names = tuple(
            sorted(
                {
                    item.ready_flag_name
                    for item in group_requests
                    if item.ready_flag_name is not None
                }
            )
        )
        if len(result_names) != 1:
            roles = ", ".join(
                f"{request.owner}.{request.role}" for request in group_requests
            )
            raise ResourceConflictError(
                f"shared ADC source must use one result name: {roles}"
            )
        if len(scan_orders) != 1:
            raise ResourceConflictError("shared ADC source must use one scan order")

        request = group_requests[0]
        result_name = request.result_name
        if result_name in used_result_names:
            raise ResourceConflictError(
                f"duplicate ADC result variable: {result_name}"
            )
        used_result_names.add(result_name)

        if request.source_kind == "external_pin":
            if request.physical_pin is None:
                raise ResourceConflictError(
                    f"{request.owner}.{request.role} requires an external ADC pin"
                )
            pin = _pin(chip, request.physical_pin)
            if "adc_channel" not in pin:
                raise ResourceConflictError(
                    f"pin {request.physical_pin} ({pin['name']}) has no ADC channel"
                )
            source_name = pin["name"]
            gpio_name = pin["name"]
            channel = pin["adc_channel"]
            adpcon_register = pin["adc_register"]
            adpcon_mask = 1 << pin["adc_bit"]
        else:
            if request.physical_pin is not None:
                raise ResourceConflictError(
                    f"{request.owner}.{request.role} internal ADC source has a pin"
                )
            source_name = "AIN12_VDD_DIV4"
            gpio_name = None
            channel = 12
            adpcon_register = None
            adpcon_mask = 0

        secondary_count_name = None
        secondary_sum_name = None
        if request.secondary_average_samples > 1:
            secondary_count_name = result_name.replace("_VALUE", "_COUNT")
            secondary_sum_name = result_name.replace("_VALUE", "_SUM")
            if secondary_count_name == result_name:
                secondary_count_name = f"{result_name}_COUNT"
            if secondary_sum_name == result_name:
                secondary_sum_name = f"{result_name}_SUM"

        roles = tuple(
            f"{item.owner}.{item.role}" for item in group_requests
        )
        for role in roles:
            role_results[role] = result_name

        channels.append(
            AdcChannelPlan(
                source_kind=request.source_kind,
                source_name=source_name,
                physical_pin=request.physical_pin,
                gpio_name=gpio_name,
                channel=channel,
                adpcon_register=adpcon_register,
                adpcon_mask=adpcon_mask,
                adm_value=0x90 | channel,
                vrefh_value=ADC_REFERENCE_VALUES[request.reference],
                adr_value=ADC_CLOCK_VALUES[request.clock],
                discard_samples=request_discard,
                average_samples=request_average,
                secondary_average_samples=request.secondary_average_samples,
                result_name=result_name,
                result_mode=request.result_mode,
                secondary_sum_name=secondary_sum_name,
                secondary_count_name=secondary_count_name,
                ready_flag_names=ready_flag_names,
                request_roles=roles,
                scan_order=request.scan_order,
                reset_semantics=request.reset_semantics,
            )
        )

    channels.sort(
        key=lambda item: (
            item.scan_order,
            item.channel,
            item.source_name,
            item.result_name,
        )
    )

    generated_names = {
        "ADCDATA_SUM": "shared ADC accumulator",
        "ADCDATA_COUNT": "shared ADC counter",
        "too_big_cnt": "fan protection counter",
    }
    if len(channels) > 1:
        generated_names["ad_channel"] = "ADC channel selector"
    for channel in channels:
        for name, purpose in (
            (channel.result_name, f"{channel.source_name} result"),
            (channel.secondary_sum_name, f"{channel.source_name} second sum"),
            (channel.secondary_count_name, f"{channel.source_name} second count"),
            *(
                (name, f"{channel.source_name} ready flag")
                for name in channel.ready_flag_names
            ),
        ):
            if name is None:
                continue
            prior = generated_names.get(name)
            if prior is not None:
                raise ResourceConflictError(
                    f"ADC state name '{name}' is used by {prior} and {purpose}"
                )
            generated_names[name] = purpose

    channel_samples = (
        HIGH_RATE_ADC_SAMPLES_PER_CHANNEL
        if high_rate
        else sum(
            channel.discard_samples + channel.average_samples
            for channel in channels
        )
    )
    channel_scan_cycle_us = (
        sample_period_us * HIGH_RATE_ADC_SAMPLES_PER_CHANNEL
        if high_rate
        else sample_period_us * channel_samples
    )
    scan_cycle_us = (
        channel_scan_cycle_us * len(channels)
        if high_rate
        else channel_scan_cycle_us
    )
    scan_cycle_ms = (scan_cycle_us + 999) // 1000
    return AdcResourcePlan(
        channels=tuple(channels),
        discard_samples=discard_samples,
        average_samples=average_samples,
        conversion_wait_limit=max(
            ADC_WAIT_LIMITS[request.clock] for request in requests
        ),
        role_results=role_results,
        scan_cycle_ms=scan_cycle_ms,
        sample_period_us=sample_period_us,
        channel_scan_cycle_us=channel_scan_cycle_us,
        high_rate_enabled=high_rate,
        high_rate_samples_per_channel=(
            HIGH_RATE_ADC_SAMPLES_PER_CHANNEL if high_rate else 0
        ),
        high_rate_discard_samples=(
            HIGH_RATE_ADC_DISCARD_SAMPLES if high_rate else 0
        ),
        high_rate_group_size=(HIGH_RATE_ADC_GROUP_SIZE if high_rate else 0),
        high_rate_group_count=(HIGH_RATE_ADC_GROUP_COUNT if high_rate else 0),
        high_rate_valid_samples=(
            average_samples if high_rate else 0
        ),
    )


def _set_tris_bit(value: int, port_bit: int, is_input: bool) -> int:
    if is_input:
        return value | (1 << port_bit)
    return value & ~(1 << port_bit)


def _set_port_bit(value: int, port_bit: int, level: int) -> int:
    if level:
        return value | (1 << port_bit)
    return value & ~(1 << port_bit)


def _set_pull_bit(value: int, port_bit: int, enabled: bool) -> int:
    # HS2811 HCON/DCON bits use 0 to enable the corresponding resistor.
    if enabled:
        return value & ~(1 << port_bit)
    return value | (1 << port_bit)


def _apply_gpio_state(
    pin: dict[str, Any],
    mode: str,
    level: int | None,
    pull: str,
    registers: dict[str, int],
) -> None:
    if mode not in ("input", "output"):
        raise ResourceConflictError(f"unsupported GPIO mode '{mode}'")
    if pull not in ("none", "up", "down"):
        raise ResourceConflictError(f"unsupported GPIO pull '{pull}'")
    if mode == "output" and level not in (0, 1):
        raise ResourceConflictError("GPIO output requires level 0 or 1")
    if mode == "input" and level is not None:
        raise ResourceConflictError("GPIO input cannot define an output level")
    if mode == "output" and pull != "none":
        raise ResourceConflictError("GPIO output cannot enable an input pull")

    port = pin["port"]
    bit = pin["bit"]
    tris_name = f"tris{port.lower()}"
    port_name = f"port{port.lower()}"
    hcon_name = f"p{port.lower()}hcon"
    dcon_name = f"p{port.lower()}dcon"
    registers[tris_name] = _set_tris_bit(
        registers[tris_name], bit, mode == "input"
    )
    if mode == "output":
        registers[port_name] = _set_port_bit(registers[port_name], bit, level)
    registers[hcon_name] = _set_pull_bit(
        registers[hcon_name], bit, pull == "up"
    )
    registers[dcon_name] = _set_pull_bit(
        registers[dcon_name], bit, pull == "down"
    )


def _plan_gpio(
    chip: dict[str, Any],
    requests: ResourceRequests,
    pwm_plans: tuple[PwmPlan, ...],
    adc: AdcResourcePlan,
) -> GpioPlan:
    # Unassigned GPIO defaults to output-low in both active and sleep states.
    active = {
        "trisa": 0x00,
        "trisc": 0x00,
        "porta": 0x00,
        "portc": 0x00,
        "pahcon": 0xFF,
        "padcon": 0xFF,
        "pchcon": 0xFF,
        "pcdcon": 0xFF,
    }
    sleep = dict(active)
    zero_battery_sleep = dict(active)
    adpcon = 0x00
    adpcon1 = 0x00
    runtime_change_mask_a = 0x00
    wake_mask_a = 0x00
    zero_battery_wake_mask_a = 0x00
    has_zero_battery_sleep_override = False

    for request in requests.gpio:
        pin = _pin(chip, request.physical_pin)
        _apply_gpio_state(
            pin,
            request.mode,
            request.initial_level,
            request.pull,
            active,
        )
        if request.runtime_change:
            if pin["port"] != "A" or not pin.get("wake_on_change", False):
                raise ResourceConflictError(
                    f"{request.owner}.{request.role} cannot use Port A "
                    f"change interrupt on pin {request.physical_pin} "
                    f"({pin['name']})"
                )
            if request.mode != "input":
                raise ResourceConflictError(
                    f"{request.owner}.{request.role} runtime change pin "
                    "must be input"
                )
            runtime_change_mask_a |= 1 << pin["bit"]
        sleep_mode = request.sleep_mode or request.mode
        sleep_pull = request.sleep_pull or request.pull
        sleep_level = (
            request.sleep_level
            if request.sleep_mode is not None
            else request.initial_level
        )
        _apply_gpio_state(
            pin,
            sleep_mode,
            sleep_level,
            sleep_pull,
            sleep,
        )
        if request.zero_battery_sleep_mode is not None:
            zero_battery_sleep_mode = request.zero_battery_sleep_mode
            zero_battery_sleep_level = request.zero_battery_sleep_level
            has_zero_battery_sleep_override = True
        else:
            zero_battery_sleep_mode = sleep_mode
            zero_battery_sleep_level = sleep_level
        zero_battery_sleep_pull = (
            request.zero_battery_sleep_pull
            if request.zero_battery_sleep_pull is not None
            else sleep_pull
        )
        if request.zero_battery_sleep_pull is not None:
            has_zero_battery_sleep_override = True
        _apply_gpio_state(
            pin,
            zero_battery_sleep_mode,
            zero_battery_sleep_level,
            zero_battery_sleep_pull,
            zero_battery_sleep,
        )
        if request.wake:
            if pin["port"] != "A" or not pin.get("wake_on_change", False):
                raise ResourceConflictError(
                    f"{request.owner}.{request.role} cannot wake on "
                    f"pin {request.physical_pin} ({pin['name']})"
                )
            if sleep_mode != "input":
                raise ResourceConflictError(
                    f"{request.owner}.{request.role} wake pin must be input in sleep"
                )
            wake_mask_a |= 1 << pin["bit"]
        zero_battery_wake = (
            request.zero_battery_wake
            if request.zero_battery_wake is not None
            else request.wake
        )
        if request.zero_battery_wake is not None:
            has_zero_battery_sleep_override = True
        if zero_battery_wake:
            if pin["port"] != "A" or not pin.get("wake_on_change", False):
                raise ResourceConflictError(
                    f"{request.owner}.{request.role} cannot wake on "
                    f"pin {request.physical_pin} ({pin['name']})"
                )
            if zero_battery_sleep_mode != "input":
                raise ResourceConflictError(
                    f"{request.owner}.{request.role} zero-battery wake pin "
                    "must be input in sleep"
                )
            zero_battery_wake_mask_a |= 1 << pin["bit"]

    for pwm in pwm_plans:
        pwm_pin = _pin(chip, pwm.physical_pin)
        _apply_gpio_state(pwm_pin, "output", 0, "none", active)
        _apply_gpio_state(pwm_pin, "output", 0, "none", sleep)
        _apply_gpio_state(
            pwm_pin, "output", 0, "none", zero_battery_sleep
        )

    gpio_requests_by_pin = {
        request.physical_pin: request for request in requests.gpio
    }
    for channel in adc.channels:
        if channel.physical_pin is None:
            continue
        adc_pin = _pin(chip, channel.physical_pin)
        _apply_gpio_state(adc_pin, "input", None, "none", active)
        gpio_request = gpio_requests_by_pin.get(channel.physical_pin)
        if gpio_request is None or (
            f"{gpio_request.owner}.{gpio_request.role}"
            not in channel.request_roles
        ):
            _apply_gpio_state(adc_pin, "output", 0, "none", sleep)
            _apply_gpio_state(
                adc_pin, "output", 0, "none", zero_battery_sleep
            )
        if channel.adpcon_register == "ADPCON":
            adpcon |= channel.adpcon_mask
        else:
            adpcon1 |= channel.adpcon_mask

    return GpioPlan(
        trisa=active["trisa"],
        trisc=active["trisc"],
        porta=active["porta"],
        portc=active["portc"],
        pahcon=active["pahcon"],
        padcon=active["padcon"],
        pchcon=active["pchcon"],
        pcdcon=active["pcdcon"],
        runtime_change_mask_a=runtime_change_mask_a,
        adpcon=adpcon,
        adpcon1=adpcon1,
        sleep_trisa=sleep["trisa"],
        sleep_trisc=sleep["trisc"],
        sleep_porta=sleep["porta"],
        sleep_portc=sleep["portc"],
        sleep_pahcon=sleep["pahcon"],
        sleep_padcon=sleep["padcon"],
        sleep_pchcon=sleep["pchcon"],
        sleep_pcdcon=sleep["pcdcon"],
        wake_mask_a=wake_mask_a,
        zero_battery_sleep_trisa=zero_battery_sleep["trisa"],
        zero_battery_sleep_trisc=zero_battery_sleep["trisc"],
        zero_battery_sleep_porta=zero_battery_sleep["porta"],
        zero_battery_sleep_portc=zero_battery_sleep["portc"],
        zero_battery_sleep_pahcon=zero_battery_sleep["pahcon"],
        zero_battery_sleep_padcon=zero_battery_sleep["padcon"],
        zero_battery_sleep_pchcon=zero_battery_sleep["pchcon"],
        zero_battery_sleep_pcdcon=zero_battery_sleep["pcdcon"],
        zero_battery_wake_mask_a=zero_battery_wake_mask_a,
        has_zero_battery_sleep_override=(
            has_zero_battery_sleep_override
        ),
    )


def build_generation_plan(config: ProjectConfig) -> GenerationPlan:
    chip = load_chip_database(config)
    requests = collect_resource_requests(config)
    resolved_pins = _check_pin_conflicts(chip, requests)
    timer = _plan_timer(config)
    pwm, alternate_pwm, auxiliary_pwm = _plan_pwm_resources(
        config, chip, requests
    )
    fixed_voltage_kind = config.motor.kind in (
        "brushless_fixed_voltage_7_3",
        "brushed_brushless_compat_fixed_voltage_7_3",
    )
    adc = plan_adc_resources(
        chip,
        requests.adc,
        high_rate=fixed_voltage_kind,
        sample_period_us=config.timebase.interrupt_us,
        source_hz=config.mcu.fcpu_hz,
    )
    if fixed_voltage_kind:
        if adc.sample_period_us != config.timebase.interrupt_us:
            raise ResourceConflictError(
                "fixed-voltage ADC sample period must equal the T1 7+3 "
                "phase period"
            )
        if adc.high_rate_valid_samples < 8:
            raise ResourceConflictError(
                "fixed-voltage ADC valid samples must cover at least one "
                "complete 7+3 phase cycle"
            )
        if adc.high_rate_valid_samples % 8:
            raise ResourceConflictError(
                "fixed-voltage ADC valid samples must be a multiple of 8"
            )
    gpio = _plan_gpio(
        chip,
        requests,
        tuple(
            dict.fromkeys(
                (
                    pwm,
                    *((alternate_pwm,) if alternate_pwm else ()),
                    *auxiliary_pwm,
                )
            )
        ),
        adc,
    )
    time_resources = plan_time_resources(requests.time)
    return GenerationPlan(
        config=config,
        requests=requests,
        timer=timer,
        pwm=pwm,
        alternate_pwm=alternate_pwm,
        auxiliary_pwm=auxiliary_pwm,
        adc=adc,
        gpio=gpio,
        time_resources=time_resources,
        resolved_pins=resolved_pins,
    )
