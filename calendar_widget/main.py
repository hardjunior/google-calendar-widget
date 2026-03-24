"""Main entry point for the Google Calendar Desktop Widget."""

import datetime
import sys

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from calendar_widget.auth import is_authenticated, has_client_secret
from calendar_widget.widget import CalendarWidget
from calendar_widget.tray import TrayIcon
from calendar_widget.dialogs import SetupDialog, EventDialog
from calendar_widget import calendar_api


class CalendarApp:
    """Main application controller."""

    # Alert thresholds in minutes
    ALERT_MINUTES = [15, 5, 0]

    def __init__(self) -> None:
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("Google Calendar Widget")
        self.app.setQuitOnLastWindowClosed(False)

        self.widget: CalendarWidget | None = None
        self.tray: TrayIcon | None = None
        self._notified_events: set[str] = set()  # event_id:minutes_before

    def run(self) -> int:
        """Run the application."""
        if not has_client_secret() or not is_authenticated():
            self._show_setup()
        else:
            self._start_widget()

        return self.app.exec()

    def _show_setup(self) -> None:
        """Show the setup/authentication dialog."""
        dialog = SetupDialog()
        dialog.auth_completed.connect(self._start_widget)
        result = dialog.exec()
        if result == 0 and not is_authenticated():
            # User closed dialog without authenticating
            sys.exit(0)

    def _start_widget(self) -> None:
        """Initialize and show the calendar widget and tray icon."""
        # Create widget
        self.widget = CalendarWidget()
        self.widget.show_on_all_screens()

        # Create tray icon
        self.tray = TrayIcon()
        self.tray.show_widget.connect(self.widget.show)
        self.tray.hide_widget.connect(self.widget.hide)
        self.tray.refresh.connect(self.widget.refresh_events)
        self.tray.create_event.connect(self._create_event_from_tray)
        self.tray.quit_app.connect(self._quit)

        # Check day changes and event alerts every minute
        self.minute_timer = QTimer()
        self.minute_timer.timeout.connect(self._on_minute_tick)
        self.minute_timer.start(60_000)

        self._last_day = datetime.date.today().day

    def _create_event_from_tray(self) -> None:
        """Open event creation dialog from tray."""
        if self.widget:
            dialog = EventDialog(
                self.widget, calendars=self.widget.calendars
            )
            dialog.event_saved.connect(self.widget.refresh_events)
            dialog.exec()

    def _on_minute_tick(self) -> None:
        """Called every minute to check day changes and event alerts."""
        self._check_day_change()
        self._check_event_alerts()

    def _check_day_change(self) -> None:
        """Check if day has changed and update accordingly."""
        current_day = datetime.date.today().day
        if current_day != self._last_day:
            self._last_day = current_day
            # Clear old notifications on day change
            self._notified_events.clear()
            if self.tray:
                self.tray.update_icon()
            if self.widget:
                today = datetime.date.today()
                if (
                    self.widget.current_year == today.year
                    and self.widget.current_month == today.month
                ):
                    self.widget.refresh_events()

    def _check_event_alerts(self) -> None:
        """Check upcoming events and show tray notifications."""
        if not self.tray or not self.widget:
            return

        now = datetime.datetime.now()
        today = now.date()

        # Get today's events from the widget cache
        day_events = self.widget.events_by_day.get(today.day, [])

        for event in day_events:
            event_id = event.get("id", "")
            if not event_id:
                continue

            # Skip all-day events
            start_info = event.get("start", {})
            if "date" in start_info and "dateTime" not in start_info:
                continue

            try:
                start_dt, _ = calendar_api.parse_event_datetime(event)
                # Make start_dt offset-naive for comparison
                if start_dt.tzinfo is not None:
                    start_dt = start_dt.replace(tzinfo=None)
            except Exception:
                continue

            diff_minutes = (start_dt - now).total_seconds() / 60.0
            summary = event.get("summary", "Sem título")

            for threshold in self.ALERT_MINUTES:
                notify_key = f"{event_id}:{threshold}"
                if notify_key in self._notified_events:
                    continue

                # Trigger if we're within the window
                # (threshold - 1 min) < diff <= threshold
                if -1 < diff_minutes <= threshold + 1:
                    if threshold == 0:
                        msg = f"Agora: {summary}"
                        title = "Compromisso agora!"
                    elif threshold == 1:
                        msg = f"Em 1 minuto: {summary}"
                        title = "Compromisso em breve"
                    else:
                        msg = f"Em {threshold} minutos: {summary}"
                        title = "Compromisso em breve"

                    time_str = start_dt.strftime("%H:%M")
                    location = event.get("location", "")
                    body = f"{time_str} - {msg}"
                    if location:
                        body += f"\n📍 {location}"

                    self.tray.show_notification(title, body)
                    self._notified_events.add(notify_key)
                    break  # Only one alert per event per tick

    def _quit(self) -> None:
        """Clean up and quit the application."""
        if self.tray:
            self.tray.hide()
        if self.widget:
            self.widget.close()
        self.app.quit()


def main() -> None:
    """Entry point."""
    app = CalendarApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
