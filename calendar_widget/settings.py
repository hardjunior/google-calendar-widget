"""Persistent settings for the calendar widget using QSettings."""

import sys
from pathlib import Path

from PyQt6.QtCore import QSettings

_ORGANIZATION = "GoogleCalendarWidget"
_APPLICATION = "GoogleCalendarWidget"

_settings = QSettings(_ORGANIZATION, _APPLICATION)


def get_selected_calendar_ids() -> list[str] | None:
    """Return saved calendar IDs, or None if never saved."""
    val = _settings.value("calendars/selected_ids")
    if val is None:
        return None
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        return [val] if val else []
    return None


def set_selected_calendar_ids(ids: list[str]) -> None:
    """Save selected calendar IDs."""
    _settings.setValue("calendars/selected_ids", ids)
    _settings.sync()


def get_window_geometry() -> dict | None:
    """Return saved window geometry dict, or None if never saved."""
    x = _settings.value("window/x")
    if x is None:
        return None
    return {
        "x": int(_settings.value("window/x", 0)),
        "y": int(_settings.value("window/y", 0)),
        "width": int(_settings.value("window/width", 0)),
        "height": int(_settings.value("window/height", 0)),
    }


def set_window_geometry(x: int, y: int, width: int, height: int) -> None:
    """Save window geometry."""
    _settings.setValue("window/x", x)
    _settings.setValue("window/y", y)
    _settings.setValue("window/width", width)
    _settings.setValue("window/height", height)
    _settings.sync()


def get_always_on_top() -> bool:
    """Return whether always-on-top is enabled."""
    return _settings.value("window/always_on_top", False, type=bool)


def set_always_on_top(enabled: bool) -> None:
    """Save always-on-top preference."""
    _settings.setValue("window/always_on_top", enabled)
    _settings.sync()


def get_background_theme() -> str:
    """Return the saved background theme name."""
    return _settings.value("appearance/background_theme", "dark", type=str)


def set_background_theme(theme: str) -> None:
    """Save background theme preference."""
    _settings.setValue("appearance/background_theme", theme)
    _settings.sync()


def get_autostart() -> bool:
    """Return whether autostart is enabled."""
    return _settings.value("general/autostart", False, type=bool)


def set_autostart(enabled: bool) -> None:
    """Save autostart preference and configure OS-level autostart."""
    _settings.setValue("general/autostart", enabled)
    _settings.sync()
    _configure_os_autostart(enabled)


def _get_app_command() -> str:
    """Get the command to launch this application."""
    python = sys.executable
    # Find the run.py script relative to this file
    run_script = Path(__file__).resolve().parent.parent / "run.py"
    return f'"{python}" "{run_script}"'


def _configure_os_autostart(enabled: bool) -> None:
    """Configure OS-level autostart."""
    if sys.platform == "win32":
        _configure_windows_autostart(enabled)
    elif sys.platform == "linux":
        _configure_linux_autostart(enabled)
    # macOS: could use LaunchAgents, skip for now


def _configure_windows_autostart(enabled: bool) -> None:
    """Add/remove from Windows registry Run key."""
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE
        )
        app_name = "GoogleCalendarWidget"
        if enabled:
            winreg.SetValueEx(
                key, app_name, 0, winreg.REG_SZ, _get_app_command()
            )
        else:
            try:
                winreg.DeleteValue(key, app_name)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception:
        pass


def _configure_linux_autostart(enabled: bool) -> None:
    """Add/remove .desktop file in ~/.config/autostart/."""
    autostart_dir = Path.home() / ".config" / "autostart"
    desktop_file = autostart_dir / "google-calendar-widget.desktop"

    if enabled:
        autostart_dir.mkdir(parents=True, exist_ok=True)
        content = (
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=Google Calendar Widget\n"
            f"Exec={_get_app_command()}\n"
            "Hidden=false\n"
            "NoDisplay=false\n"
            "X-GNOME-Autostart-enabled=true\n"
            "Comment=Desktop calendar widget for Google Calendar\n"
        )
        desktop_file.write_text(content)
    else:
        if desktop_file.exists():
            desktop_file.unlink()
