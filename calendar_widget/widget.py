"""Main calendar widget UI module."""

import calendar
import datetime
import sys
from collections import defaultdict
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QFrame,
    QPushButton,
    QScrollArea,
    QSizeGrip,
    QSizePolicy,
    QApplication,
)
from PyQt6.QtCore import Qt, QTimer, QPoint, QRect, pyqtSignal
from PyQt6.QtGui import QCursor

from calendar_widget.styles import (
    MAIN_WIDGET_STYLE,
    HEADER_STYLE,
    NAV_BUTTON_STYLE,
    DAY_HEADER_STYLE,
    WEEKEND_DAY_HEADER_STYLE,
    EVENT_LABEL_STYLE,
    HOLIDAY_LABEL_STYLE,
    SCROLLBAR_STYLE,
    TODAY_BUTTON_STYLE,
    RESIZE_GRIP_STYLE,
    CALENDAR_FILTER_BUTTON_STYLE,
    PIN_BUTTON_STYLE,
    PIN_BUTTON_ACTIVE_STYLE,
    COLORS,
    get_day_cell_style,
    get_day_number_style,
    get_main_widget_style,
)
from calendar_widget.holidays_br import (
    get_brazilian_holidays,
    is_holiday,
    is_weekend,
    get_holiday_name,
)
from calendar_widget import calendar_api
from calendar_widget import settings
from calendar_widget.dialogs import (
    EventDialog,
    EventViewDialog,
    CalendarFilterDialog,
)

# Portuguese month names
MONTH_NAMES = [
    "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

# Portuguese day abbreviations (Monday first)
DAY_NAMES = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


class ClickableEventLabel(QLabel):
    """A label that emits clicked signal when pressed."""

    clicked = pyqtSignal(dict)

    def __init__(self, text: str, event_data: dict, parent=None):
        super().__init__(text, parent)
        self.event_data = event_data
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def mousePressEvent(self, ev) -> None:
        if ev.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.event_data)
        super().mousePressEvent(ev)


class ClickableDayFrame(QFrame):
    """A frame that emits clicked signal for creating events on that day."""

    clicked = pyqtSignal(object)  # datetime.date

    def __init__(self, date: datetime.date, parent=None):
        super().__init__(parent)
        self.date = date
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def mouseDoubleClickEvent(self, ev) -> None:
        if ev.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.date)
        super().mouseDoubleClickEvent(ev)


class CalendarWidget(QWidget):
    """Main calendar widget that displays on the desktop."""

    refresh_requested = pyqtSignal()
    always_on_top_changed = pyqtSignal(bool)

    # Edge resize constants
    EDGE_MARGIN = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_year = datetime.date.today().year
        self.current_month = datetime.date.today().month
        self.events: list[dict] = []
        self.events_by_day: dict[int, list[dict]] = defaultdict(list)
        self.holidays: dict[datetime.date, str] = {}
        self._drag_pos: Optional[QPoint] = None

        # Calendar list state
        self.calendars: list[dict] = []
        self.selected_calendar_ids: list[str] = []

        # Edge resize state
        self._resize_edge: Optional[str] = None
        self._resize_start_rect: Optional[QRect] = None
        self._resize_start_pos: Optional[QPoint] = None

        self._setup_window()
        self._setup_ui()
        self._apply_saved_background()
        self._load_holidays()
        self._load_calendar_list()

        # Auto-refresh every 5 minutes
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_events)
        self.refresh_timer.start(300_000)
        self.setMouseTracking(True)

    def _setup_window(self) -> None:
        """Configure the window to be frameless, transparent and styled."""
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if settings.get_always_on_top():
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(700, 500)

        # Restore saved geometry or use default
        saved = settings.get_window_geometry()
        if saved and saved["width"] > 0 and saved["height"] > 0:
            self.setGeometry(
                saved["x"], saved["y"], saved["width"], saved["height"]
            )
        else:
            screen = QApplication.primaryScreen()
            if screen:
                geom = screen.availableGeometry()
                width = int(geom.width() * 0.75)
                height = int(geom.height() * 0.80)
                x = geom.x() + (geom.width() - width) // 2
                y = geom.y() + (geom.height() - height) // 2
                self.setGeometry(x, y, width, height)

    def _setup_ui(self) -> None:
        """Build the complete UI."""
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        # Main container with background
        self.main_frame = QWidget()
        self.main_frame.setObjectName("mainWidget")
        self.main_frame.setStyleSheet(MAIN_WIDGET_STYLE)

        main_layout = QVBoxLayout(self.main_frame)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(20, 16, 20, 12)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        # Nav buttons
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setStyleSheet(NAV_BUTTON_STYLE)
        self.prev_btn.clicked.connect(self._prev_month)
        header_layout.addWidget(self.prev_btn)

        # Month and Year labels
        self.month_label = QLabel()
        self.month_label.setObjectName("headerMonth")
        self.month_label.setStyleSheet(HEADER_STYLE)
        header_layout.addWidget(self.month_label)

        self.year_label = QLabel()
        self.year_label.setObjectName("headerYear")
        self.year_label.setStyleSheet(HEADER_STYLE)
        header_layout.addWidget(self.year_label)

        header_layout.addStretch()

        # Today button
        self.today_btn = QPushButton("Hoje")
        self.today_btn.setStyleSheet(TODAY_BUTTON_STYLE)
        self.today_btn.clicked.connect(self._go_today)
        header_layout.addWidget(self.today_btn)

        # Next button
        self.next_btn = QPushButton("▶")
        self.next_btn.setStyleSheet(NAV_BUTTON_STYLE)
        self.next_btn.clicked.connect(self._next_month)
        header_layout.addWidget(self.next_btn)

        # Pin (Always on top) button
        self.pin_btn = QPushButton("📌")
        self.pin_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.pin_btn.clicked.connect(self._toggle_pin)
        self._update_pin_button_style(settings.get_always_on_top())
        header_layout.addWidget(self.pin_btn)

        # Calendar filter button
        self.filter_btn = QPushButton("\u2630")
        self.filter_btn.setStyleSheet(CALENDAR_FILTER_BUTTON_STYLE)
        self.filter_btn.setToolTip("Selecionar calendários")
        self.filter_btn.clicked.connect(self._open_calendar_filter)
        header_layout.addWidget(self.filter_btn)

        # Add new event button
        self.add_btn = QPushButton("+")
        self.add_btn.setStyleSheet(NAV_BUTTON_STYLE)
        self.add_btn.setToolTip("Criar novo compromisso")
        self.add_btn.clicked.connect(self._create_event)
        header_layout.addWidget(self.add_btn)

        main_layout.addLayout(header_layout)

        # Day of week headers
        self.dow_layout = QHBoxLayout()
        self.dow_layout.setSpacing(4)
        for i, name in enumerate(DAY_NAMES):
            lbl = QLabel(name)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if i >= 5:  # Weekend
                lbl.setStyleSheet(WEEKEND_DAY_HEADER_STYLE)
            else:
                lbl.setStyleSheet(DAY_HEADER_STYLE)
            self.dow_layout.addWidget(lbl)
        main_layout.addLayout(self.dow_layout)

        # Calendar grid in a scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(SCROLLBAR_STYLE)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(4)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area.setWidget(self.grid_container)
        main_layout.addWidget(self.scroll_area, 1)

        # Bottom bar with resize grip
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        # Legend
        legend_layout = QHBoxLayout()
        legend_layout.setSpacing(16)
        legend_layout.addWidget(self._make_legend_item(COLORS["today"], "Hoje"))
        legend_layout.addWidget(self._make_legend_item(COLORS["weekend"], "Fim de semana"))
        legend_layout.addWidget(self._make_legend_item(COLORS["holiday"], "Feriado"))
        legend_layout.addStretch()
        bottom_layout.addLayout(legend_layout)

        grip = QSizeGrip(self)
        grip.setStyleSheet(RESIZE_GRIP_STYLE)
        bottom_layout.addWidget(grip, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)

        main_layout.addLayout(bottom_layout)

        outer_layout.addWidget(self.main_frame)

        self._update_header()

    def _make_legend_item(self, color: str, text: str) -> QWidget:
        """Create a legend item with color dot and label."""
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        dot = QLabel()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(
            f"background-color: {color}; border-radius: 4px; border: none;"
        )
        layout.addWidget(dot)

        label = QLabel(text)
        label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 10px; "
            f"font-family: 'Segoe UI', sans-serif; border: none;"
        )
        layout.addWidget(label)

        return container

    def _update_header(self) -> None:
        """Update month/year labels."""
        self.month_label.setText(MONTH_NAMES[self.current_month])
        self.year_label.setText(str(self.current_year))

    def _load_holidays(self) -> None:
        """Load holidays for the current year."""
        self.holidays = get_brazilian_holidays(self.current_year)

    def _prev_month(self) -> None:
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
            self._load_holidays()
        else:
            self.current_month -= 1
        self._update_header()
        self.refresh_events()

    def _next_month(self) -> None:
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
            self._load_holidays()
        else:
            self.current_month += 1
        self._update_header()
        self.refresh_events()

    def _go_today(self) -> None:
        today = datetime.date.today()
        self.current_year = today.year
        self.current_month = today.month
        self._load_holidays()
        self._update_header()
        self.refresh_events()

    def _load_calendar_list(self) -> None:
        """Fetch list of calendars from Google."""
        self.calendars = calendar_api.get_calendar_list()
        # Restore saved selection, fallback to API defaults
        saved_ids = settings.get_selected_calendar_ids()
        if saved_ids is not None:
            self.selected_calendar_ids = saved_ids
        elif not self.selected_calendar_ids and self.calendars:
            self.selected_calendar_ids = [
                c["id"] for c in self.calendars if c.get("selected", True)
            ]

    def _open_calendar_filter(self) -> None:
        """Open the calendar filter dialog."""
        if not self.calendars:
            self._load_calendar_list()
        dialog = CalendarFilterDialog(
            self,
            calendars=self.calendars,
            selected_ids=self.selected_calendar_ids,
        )
        dialog.calendars_changed.connect(self._on_calendars_changed)
        dialog.exec()

    def _on_calendars_changed(self, selected_ids: list[str]) -> None:
        """Handle calendar selection changes."""
        self.selected_calendar_ids = selected_ids
        settings.set_selected_calendar_ids(selected_ids)
        self.refresh_events()

    def refresh_events(self) -> None:
        """Fetch events from Google Calendar and rebuild the grid."""
        cal_ids = self.selected_calendar_ids or None
        self.events = calendar_api.get_events_for_month(
            self.current_year, self.current_month, calendar_ids=cal_ids
        )
        self.events_by_day = defaultdict(list)
        for event in self.events:
            try:
                days = calendar_api.get_event_days(
                    event, self.current_year, self.current_month
                )
                for day in days:
                    self.events_by_day[day].append(event)
            except Exception:
                pass
        self._rebuild_grid()

    def _rebuild_grid(self) -> None:
        """Clear and rebuild the calendar grid."""
        # Clear existing grid
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        today = datetime.date.today()
        cal = calendar.Calendar(firstweekday=0)  # Monday first
        month_days = cal.monthdayscalendar(self.current_year, self.current_month)

        for row, week in enumerate(month_days):
            for col, day in enumerate(week):
                if day == 0:
                    # Empty cell (other month)
                    frame = QFrame()
                    frame.setStyleSheet(get_day_cell_style(is_other_month=True))
                    frame.setMinimumHeight(80)
                    frame.setSizePolicy(
                        QSizePolicy.Policy.Expanding,
                        QSizePolicy.Policy.Expanding,
                    )
                    self.grid_layout.addWidget(frame, row, col)
                    continue

                date = datetime.date(self.current_year, self.current_month, day)
                is_today = date == today
                weekend = is_weekend(date)
                holiday = is_holiday(date)
                holiday_name = get_holiday_name(date)

                # Day cell frame
                frame = ClickableDayFrame(date)
                frame.setStyleSheet(
                    get_day_cell_style(
                        is_today=is_today,
                        is_weekend=weekend,
                        is_holiday=holiday,
                    )
                )
                frame.setMinimumHeight(80)
                frame.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Expanding,
                )
                frame.clicked.connect(self._on_day_double_click)

                cell_layout = QVBoxLayout(frame)
                cell_layout.setSpacing(2)
                cell_layout.setContentsMargins(4, 4, 4, 4)

                # Day number
                day_label = QLabel(str(day))
                day_label.setStyleSheet(
                    get_day_number_style(
                        is_today=is_today,
                        is_weekend=weekend,
                        is_holiday=holiday,
                    )
                )
                day_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
                cell_layout.addWidget(day_label)

                # Holiday name
                if holiday_name:
                    h_label = QLabel(holiday_name)
                    h_label.setStyleSheet(HOLIDAY_LABEL_STYLE)
                    h_label.setWordWrap(True)
                    cell_layout.addWidget(h_label)

                # Events for this day
                day_events = self.events_by_day.get(day, [])
                max_visible = 3
                for i, event in enumerate(day_events[:max_visible]):
                    time_str = calendar_api.get_event_time_str(event)
                    summary = event.get("summary", "Sem título")
                    display_text = f"{time_str} {summary}"
                    if len(display_text) > 30:
                        display_text = display_text[:28] + "…"

                    event_label = ClickableEventLabel(display_text, event)
                    event_label.setStyleSheet(EVENT_LABEL_STYLE)
                    event_label.clicked.connect(self._on_event_click)
                    cell_layout.addWidget(event_label)

                if len(day_events) > max_visible:
                    more_label = QLabel(f"+{len(day_events) - max_visible} mais")
                    more_label.setStyleSheet(
                        f"color: {COLORS['text_muted']}; font-size: 9px; "
                        f"padding: 1px 4px; background: transparent; border: none;"
                    )
                    cell_layout.addWidget(more_label)

                cell_layout.addStretch()
                self.grid_layout.addWidget(frame, row, col)

        # Make all columns equal width
        for col in range(7):
            self.grid_layout.setColumnStretch(col, 1)
        # Make all rows equal height
        for row in range(len(month_days)):
            self.grid_layout.setRowStretch(row, 1)

    def _on_event_click(self, event: dict) -> None:
        """Handle clicking on an event."""
        dialog = EventViewDialog(self, event)
        dialog.edit_requested.connect(self._on_edit_event)
        dialog.exec()

    def _on_edit_event(self, event: dict) -> None:
        """Open the edit dialog for an event."""
        dialog = EventDialog(
            self, event=event, calendars=self.calendars
        )
        dialog.event_saved.connect(self.refresh_events)
        dialog.exec()

    def _on_day_double_click(self, date: datetime.date) -> None:
        """Handle double-clicking on a day to create a new event."""
        dialog = EventDialog(
            self, default_date=date, calendars=self.calendars
        )
        dialog.event_saved.connect(self.refresh_events)
        dialog.exec()

    def _create_event(self) -> None:
        """Open dialog to create a new event."""
        dialog = EventDialog(self, calendars=self.calendars)
        dialog.event_saved.connect(self.refresh_events)
        dialog.exec()

    # -- Edge resize & dragging support --

    def _get_edge(self, pos: QPoint) -> Optional[str]:
        """Determine which edge/corner the position is on."""
        rect = self.rect()
        m = self.EDGE_MARGIN
        x, y = pos.x(), pos.y()
        on_left = x < m
        on_right = x > rect.width() - m
        on_top = y < m
        on_bottom = y > rect.height() - m

        if on_top and on_left:
            return "top-left"
        if on_top and on_right:
            return "top-right"
        if on_bottom and on_left:
            return "bottom-left"
        if on_bottom and on_right:
            return "bottom-right"
        if on_left:
            return "left"
        if on_right:
            return "right"
        if on_top:
            return "top"
        if on_bottom:
            return "bottom"
        return None

    def _update_cursor_for_edge(self, edge: Optional[str]) -> None:
        """Update the cursor shape based on which edge is hovered."""
        cursor_map = {
            "left": Qt.CursorShape.SizeHorCursor,
            "right": Qt.CursorShape.SizeHorCursor,
            "top": Qt.CursorShape.SizeVerCursor,
            "bottom": Qt.CursorShape.SizeVerCursor,
            "top-left": Qt.CursorShape.SizeFDiagCursor,
            "bottom-right": Qt.CursorShape.SizeFDiagCursor,
            "top-right": Qt.CursorShape.SizeBDiagCursor,
            "bottom-left": Qt.CursorShape.SizeBDiagCursor,
        }
        if edge and edge in cursor_map:
            self.setCursor(cursor_map[edge])
        else:
            self.unsetCursor()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self._get_edge(event.position().toPoint())
            if edge:
                self._resize_edge = edge
                self._resize_start_rect = self.geometry()
                self._resize_start_pos = event.globalPosition().toPoint()
            else:
                self._drag_pos = (
                    event.globalPosition().toPoint()
                    - self.frameGeometry().topLeft()
                )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._resize_edge and self._resize_start_rect and self._resize_start_pos:
            delta = event.globalPosition().toPoint() - self._resize_start_pos
            r = QRect(self._resize_start_rect)
            min_w = self.minimumWidth()
            min_h = self.minimumHeight()
            edge = self._resize_edge

            if "right" in edge:
                r.setRight(r.right() + delta.x())
            if "bottom" in edge:
                r.setBottom(r.bottom() + delta.y())
            if "left" in edge:
                new_left = r.left() + delta.x()
                if r.right() - new_left >= min_w:
                    r.setLeft(new_left)
            if "top" in edge:
                new_top = r.top() + delta.y()
                if r.bottom() - new_top >= min_h:
                    r.setTop(new_top)

            if r.width() >= min_w and r.height() >= min_h:
                self.setGeometry(r)
        elif self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        else:
            edge = self._get_edge(event.position().toPoint())
            self._update_cursor_for_edge(edge)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._drag_pos is not None or self._resize_edge is not None:
            # Save geometry after drag/resize
            g = self.geometry()
            settings.set_window_geometry(g.x(), g.y(), g.width(), g.height())
        self._drag_pos = None
        self._resize_edge = None
        self._resize_start_rect = None
        self._resize_start_pos = None
        self.unsetCursor()
        super().mouseReleaseEvent(event)

    def _toggle_pin(self) -> None:
        """Toggle always-on-top state when header pin button is clicked."""
        new_state = not settings.get_always_on_top()
        self.set_always_on_top(new_state)
        self.always_on_top_changed.emit(new_state)

    def _update_pin_button_style(self, enabled: bool) -> None:
        """Update appearance and tooltip of the pin button based on state."""
        if not hasattr(self, "pin_btn"):
            return
        if enabled:
            self.pin_btn.setStyleSheet(PIN_BUTTON_ACTIVE_STYLE)
            self.pin_btn.setToolTip("Sempre no topo: Ativado (clique para desafixar)")
        else:
            self.pin_btn.setStyleSheet(PIN_BUTTON_STYLE)
            self.pin_btn.setToolTip("Sempre no topo: Desativado (clique para fixar no topo)")

    def set_always_on_top(self, enabled: bool) -> None:
        """Toggle the always-on-top window flag and enforce via Win32 API."""
        settings.set_always_on_top(enabled)
        self._update_pin_button_style(enabled)

        # Update Qt window flags
        flags = self.windowFlags()
        if enabled:
            flags = (flags | Qt.WindowType.WindowStaysOnTopHint) & ~Qt.WindowType.WindowStaysOnBottomHint
        else:
            flags = flags & ~Qt.WindowType.WindowStaysOnTopHint

        was_visible = self.isVisible()
        self.setWindowFlags(flags)
        if was_visible:
            self.show()

        # Enforce on Windows via Win32 SetWindowPos
        if sys.platform == "win32":
            self._apply_win32_topmost(enabled)

    def _apply_win32_topmost(self, enabled: bool) -> None:
        """Directly enforce HWND_TOPMOST or HWND_NOTOPMOST on Windows."""
        try:
            import ctypes
            from ctypes import wintypes
            u32 = ctypes.windll.user32
            u32.SetWindowPos.argtypes = [
                wintypes.HWND, wintypes.HWND,
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                wintypes.UINT
            ]
            u32.SetWindowPos.restype = wintypes.BOOL

            HWND_TOPMOST = -1
            HWND_NOTOPMOST = -2
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOACTIVATE = 0x0010
            SWP_SHOWWINDOW = 0x0040

            target = HWND_TOPMOST if enabled else HWND_NOTOPMOST
            hwnd = int(self.winId())
            u32.SetWindowPos(
                hwnd, target, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
            )
        except Exception as e:
            print(f"[TopMost Error] {e}")

    def set_background_theme(self, theme: str) -> None:
        """Apply a background theme to the widget."""
        self.main_frame.setStyleSheet(get_main_widget_style(theme))

    def _apply_saved_background(self) -> None:
        """Apply the saved background theme on startup."""
        theme = settings.get_background_theme()
        if theme != "dark":
            self.main_frame.setStyleSheet(get_main_widget_style(theme))

    def show_on_all_screens(self) -> None:
        """Show the widget, centered on primary screen."""
        self.show()
        if settings.get_always_on_top() and sys.platform == "win32":
            self._apply_win32_topmost(True)
        self.refresh_events()
