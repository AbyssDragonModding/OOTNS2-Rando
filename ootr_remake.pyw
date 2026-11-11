#!/usr/bin/env python3
"""OoT Remake Randomizer - double-click this file to open the generator.

First-time setup: install Python 3.14+ and double-click "Install Requirements.bat" (see README.md).
A .pyw file runs without a console window, so problems are shown in a message box instead.
"""
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _show_error(text):
    """Message box on Windows (no console with pythonw); stderr everywhere else."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, text, "OoT Remake Randomizer", 0x10)
            return
        except Exception:
            pass
    print(text, file=sys.stderr)


def main():
    if sys.version_info < (3, 14):
        _show_error("Python 3.14 or newer is required (this is Python %d.%d).\n\n"
                    "Install it from python.org, then double-click this file again." % sys.version_info[:2])
        return 1
    try:
        import raven  # noqa: F401
    except ImportError:
        _show_error("The GUI library isn't installed yet.\n\n"
                    "Double-click \"Install Requirements.bat\" in this folder, then open the randomizer again.")
        return 1
    try:
        from rando.gui_glass import run
        run()
    except Exception:
        log = os.path.join(HERE, "error_log.txt")
        with open(log, "w", encoding="utf-8") as fh:
            fh.write(traceback.format_exc())
        _show_error("The randomizer crashed. The details were saved to:\n%s\n\n"
                    "Please attach that file when you report the problem." % log)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
