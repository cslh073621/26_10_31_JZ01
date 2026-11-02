import sys


try:
    from fanforge_gui.app import main
except ModuleNotFoundError as exc:
    if exc.name not in {"tkinter", "customtkinter"}:
        raise
    missing_dependency = exc.name

    def main() -> int:
        if missing_dependency == "tkinter":
            message = (
                "FanForge GUI requires Tkinter. Use the Windows build or "
                "install the Tkinter package for this Python runtime."
            )
        else:
            message = (
                "FanForge GUI requires CustomTkinter. Install desktop "
                "dependencies with: pip install -r requirements-desktop.txt"
            )
        print(message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
