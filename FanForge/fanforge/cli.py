import argparse
import json
import sys
from pathlib import Path

from fanforge.capabilities import build_capability_catalog
from fanforge.emitter import plan_as_dict, write_generation
from fanforge.errors import FanForgeError
from fanforge.models import ProjectConfig
from fanforge.planner import build_generation_plan


GENERATED_ARTIFACTS = (
    "main.c.in",
    "main.h.in",
    "generation_report.md",
    "acceptance_checklist.md",
    "resolved_plan.json",
)


def _load_config(path: Path) -> ProjectConfig:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FanForgeError(f"configuration file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise FanForgeError(
            f"invalid JSON in {path}:{exc.lineno}:{exc.colno}: {exc.msg}"
        ) from exc
    if not isinstance(raw, dict):
        raise FanForgeError("configuration root must be an object")
    return ProjectConfig.from_dict(path, raw)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fanforge",
        description="Deterministic HS2811 fan firmware generator",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser(
        "generate", help="validate, plan, and write generated files"
    )
    generate.add_argument("config", type=Path)
    generate.add_argument("--out", required=True, type=Path)
    generate.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing FanForge-generated artifacts",
    )

    inspect = subparsers.add_parser(
        "inspect", help="validate and print the resolved hardware plan"
    )
    inspect.add_argument("config", type=Path)

    capabilities = subparsers.add_parser(
        "capabilities",
        help="print the machine-readable supported feature contract",
    )
    capabilities.add_argument("--out", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "capabilities":
            rendered = (
                json.dumps(
                    build_capability_catalog(),
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            )
            if args.out is None:
                print(rendered, end="")
            else:
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_text(rendered, encoding="utf-8")
                print(f"capabilities: {args.out.resolve()}")
            return 0

        config = _load_config(args.config)
        plan = build_generation_plan(config)
        if args.command == "inspect":
            print(json.dumps(plan_as_dict(plan), indent=2, sort_keys=True))
        else:
            existing = tuple(
                name
                for name in GENERATED_ARTIFACTS
                if (args.out / name).exists()
            )
            if existing and not args.force:
                raise FanForgeError(
                    "output already contains generated artifacts: "
                    f"{', '.join(existing)}; use --force only after "
                    "reviewing or backing up local edits"
                )
            write_generation(plan, args.out)
            print(f"generated: {args.out.resolve()}")
            print(
                "PWM: "
                f"{plan.pwm.gpio_name}/{plan.pwm.timer}PWM"
                f"{plan.pwm.channel if plan.pwm.timer == 'T3' else ''}, "
                f"{plan.pwm.actual_frequency_hz:.3f}Hz"
            )
            print(
                "T1: "
                f"{plan.timer.actual_us:.3f}us, "
                f"reload=0x{plan.timer.reload_value:04X}"
            )
        return 0
    except FanForgeError as exc:
        print(f"FanForge error: {exc}", file=sys.stderr)
        return 2
