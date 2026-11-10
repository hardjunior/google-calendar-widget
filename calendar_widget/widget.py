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
    QStackedWidget,
    QLineEdit,
)
from PyQt6.QtCore import Qt, QTimer, QPoint, QRect, pyqtSignal, QThread
from PyQt6.QtGui import QCursor, QFont

from calendar_widget.styles import (
    MAIN_WIDGET_STYLE,
    HEADER_STYLE,
    NAV_BUTTON_STYLE,
    DAY_HEADER_STYLE,
    WEEKEND_DAY_HEADER_STYLE,
    HOLIDAY_LABEL_STYLE,
    SCROLLBAR_STYLE,
    TODAY_BUTTON_STYLE,
    RESIZE_GRIP_STYLE,
    CALENDAR_FILTER_BUTTON_STYLE,
    PIN_BUTTON_STYLE,
    PIN_BUTTON_ACTIVE_STYLE,
    COLORS,
    VIEW_TOGGLE_BUTTON_STYLE,
    VIEW_TOGGLE_ACTIVE_STYLE,
    SEARCH_INPUT_STYLE,
    DAY_PANEL_STYLE,
    LOADING_LABEL_STYLE,
    get_day_cell_style,
    get_day_number_style,
    get_event_badge_style,
    get_main_widget_style,
    hex_to_rgba,
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
    TaskManagerDialog,
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
    """A frame that emits signals for single click (select/inspect) and double click (create)."""

    single_clicked = pyqtSignal(object)  # datetime.date
    double_clicked = pyqtSignal(object)  # datetime.date

    def __init__(self, date: datetime.date, parent=None):
        super().__init__(parent)
        self.date = date
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def mousePressEvent(self, ev) -> None:
        if ev.button() == Qt.MouseButton.LeftButton:
            self.single_clicked.emit(self.date)
        super().mousePressEvent(ev)

    def mouseDoubleClickEvent(self, ev) -> None:
        if ev.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.date)
        super().mouseDoubleClickEvent(ev)


class FetchEventsWorker(QThread):
    """Background worker to fetch events asynchronously without freezing the UI."""

    events_loaded = pyqtSignal(list, int, int)  # events, year, month
    fetch_error = pyqtSignal(str)

    def __init__(
        self,
        year: int,
        month: int,
        calendar_ids: Optional[list[str]] = None,
        calendar_colors: Optional[dict[str, str]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.year = year
        self.month = month
        self.calendar_ids = calendar_ids
        self.calendar_colors = calendar_colors
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            events = calendar_api.get_events_for_month(
                self.year,
                self.month,
                calendar_ids=self.calendar_ids,
                calendar_colors=self.calendar_colors,
            )
            if not self._cancelled:
                self.events_loaded.emit(events, self.year, self.month)
        except Exception as e:
            if not self._cancelled:
                self.fetch_error.emit(str(e))


class CalendarWidget(QWidget):
    """Main calendar widget that displays on the desktop."""

    refresh_requested = pyqtSignal()
    always_on_top_changed = pyqtSignal(bool)

    EDGE_MARGIN = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_year = datetime.date.today().year
        self.current_month = datetime.date.today().month
        self.events: list[dict] = []
        self.events_by_day: dict[int, list[dict]] = defaultdict(list)
        self.holidays: dict[datetime.date, str] = {}
        self._drag_pos: Optional[QPoint] = None

        # Asynchronous worker and caching
        self._worker: Optional[FetchEventsWorker] = None
        self._month_cache: dict[tuple[int, int], list[dict]] = {}

        # View state
        self.current_view_mode: str = "month"  # "month" or "agenda"
        self.selected_day: Optional[datetime.date] = None
        self.search_query: str = ""

        # Calendar list state
        self.calendars: list[dict] = []
        self.selected_calendar_ids: list[str] = []
        self.calendar_colors: dict[str, str] = {}

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
        self.setMinimumSize(740, 520)

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
        """Build the complete UI with view switcher, search, and day inspector panel."""
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        # Main container with background
        self.main_frame = QWidget()
        self.main_frame.setObjectName("mainWidget")
        self.main_frame.setStyleSheet(MAIN_WIDGET_STYLE)

        main_layout = QVBoxLayout(self.main_frame)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(18, 14, 18, 12)

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

        # Loading / sync indicator
        self.loading_label = QLabel("")
        self.loading_label.setStyleSheet(LOADING_LABEL_STYLE)
        self.loading_label.setVisible(False)
        header_layout.addWidget(self.loading_label)

        header_layout.addStretch()

        # Search bar
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 Buscar...")
        self.search_edit.setStyleSheet(SEARCH_INPUT_STYLE)
        self.search_edit.setFixedWidth(135)
        self.search_edit.textChanged.connect(self._on_search_changed)
        header_layout.addWidget(self.search_edit)

        # View mode toggles
        self.btn_month_view = QPushButton("⊞ Mês")
        self.btn_month_view.setStyleSheet(VIEW_TOGGLE_ACTIVE_STYLE)
        self.btn_month_view.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_month_view.clicked.connect(lambda: self._set_view_mode("month"))
        header_layout.addWidget(self.btn_month_view)

        self.btn_agenda_view = QPushButton("☰ Agenda")
        self.btn_agenda_view.setStyleSheet(VIEW_TOGGLE_BUTTON_STYLE)
        self.btn_agenda_view.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_agenda_view.clicked.connect(lambda: self._set_view_mode("agenda"))
        header_layout.addWidget(self.btn_agenda_view)

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

        # Task manager CRUD button
        self.tasks_btn = QPushButton("📋 Tarefas")
        self.tasks_btn.setStyleSheet(NAV_BUTTON_STYLE)
        self.tasks_btn.setToolTip("Gerenciador de Tarefas e Compromissos (CRUD)")
        self.tasks_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.tasks_btn.clicked.connect(self.open_task_manager)
        header_layout.addWidget(self.tasks_btn)

        # Add new event button
        self.add_btn = QPushButton("+")
        self.add_btn.setStyleSheet(NAV_BUTTON_STYLE)
        self.add_btn.setToolTip("Criar novo compromisso")
        self.add_btn.clicked.connect(self._create_event)
        header_layout.addWidget(self.add_btn)

        main_layout.addLayout(header_layout)

        # Central content area: (Views stack on left, collapsible Day Panel on right)
        central_container = QWidget()
        central_container.setStyleSheet("background: transparent;")
        central_layout = QHBoxLayout(central_container)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(10)

        # Views Stack
        self.views_stack = QStackedWidget()

        # --- View 1: Month Grid ---
        self.month_page = QWidget()
        self.month_page.setStyleSheet("background: transparent;")
        month_page_layout = QVBoxLayout(self.month_page)
        month_page_layout.setContentsMargins(0, 0, 0, 0)
        month_page_layout.setSpacing(4)

        # Day of week headers
        self.dow_container = QWidget()
        self.dow_layout = QHBoxLayout(self.dow_container)
        self.dow_layout.setContentsMargins(0, 0, 0, 0)
        self.dow_layout.setSpacing(4)
        for i, name in enumerate(DAY_NAMES):
            lbl = QLabel(name)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if i >= 5:
                lbl.setStyleSheet(WEEKEND_DAY_HEADER_STYLE)
            else:
                lbl.setStyleSheet(DAY_HEADER_STYLE)
            self.dow_layout.addWidget(lbl)
        month_page_layout.addWidget(self.dow_container)

        # Calendar grid in scroll area
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
        month_page_layout.addWidget(self.scroll_area, 1)

        self.views_stack.addWidget(self.month_page)

        # --- View 2: Agenda Timeline ---
        self.agenda_page = QWidget()
        self.agenda_page.setStyleSheet("background: transparent;")
        agenda_page_layout = QVBoxLayout(self.agenda_page)
        agenda_page_layout.setContentsMargins(0, 0, 0, 0)
        agenda_page_layout.setSpacing(6)

        self.agenda_scroll = QScrollArea()
        self.agenda_scroll.setWidgetResizable(True)
        self.agenda_scroll.setStyleSheet(SCROLLBAR_STYLE)
        self.agenda_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.agenda_container = QWidget()
        self.agenda_container.setStyleSheet("background: transparent;")
        self.agenda_layout = QVBoxLayout(self.agenda_container)
        self.agenda_layout.setContentsMargins(4, 4, 4, 4)
        self.agenda_layout.setSpacing(8)

        self.agenda_scroll.setWidget(self.agenda_container)
        agenda_page_layout.addWidget(self.agenda_scroll, 1)

        self.views_stack.addWidget(self.agenda_page)

        central_layout.addWidget(self.views_stack, 1)

        # --- Right Panel: Day Inspector ---
        self.day_panel = QWidget()
        self.day_panel.setObjectName("dayPanel")
        self.day_panel.setStyleSheet(DAY_PANEL_STYLE)
        self.day_panel.setFixedWidth(280)
        self.day_panel.setVisible(False)

        day_panel_layout = QVBoxLayout(self.day_panel)
        day_panel_layout.setContentsMargins(14, 12, 14, 12)
        day_panel_layout.setSpacing(8)

        # Day panel header
        dp_header = QHBoxLayout()
        self.dp_title_label = QLabel("")
        self.dp_title_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.dp_title_label.setStyleSheet(f"color: {COLORS['text_primary']}; border: none;")
        dp_header.addWidget(self.dp_title_label)
        dp_header.addStretch()

        self.dp_close_btn = QPushButton("✕")
        self.dp_close_btn.setFixedSize(24, 24)
        self.dp_close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.dp_close_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {COLORS['text_muted']}; "
            f"border: none; font-size: 14px; border-radius: 4px; }} "
            f"QPushButton:hover {{ background: {COLORS['bg_hover']}; color: {COLORS['text_primary']}; }}"
        )
        self.dp_close_btn.clicked.connect(self._close_day_panel)
        dp_header.addWidget(self.dp_close_btn)
        day_panel_layout.addLayout(dp_header)

        # Holiday label in day panel
        self.dp_holiday_label = QLabel("")
        self.dp_holiday_label.setStyleSheet(HOLIDAY_LABEL_STYLE)
        self.dp_holiday_label.setWordWrap(True)
        self.dp_holiday_label.setVisible(False)
        day_panel_layout.addWidget(self.dp_holiday_label)

        # Add event on this day button
        self.dp_add_btn = QPushButton("+ Novo compromisso")
        self.dp_add_btn.setStyleSheet(NAV_BUTTON_STYLE)
        self.dp_add_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.dp_add_btn.clicked.connect(self._on_day_panel_add_event)
        day_panel_layout.addWidget(self.dp_add_btn)

        # Scroll area for events of selected day
        self.dp_scroll = QScrollArea()
        self.dp_scroll.setWidgetResizable(True)
        self.dp_scroll.setStyleSheet(SCROLLBAR_STYLE)
        self.dp_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.dp_events_container = QWidget()
        self.dp_events_container.setStyleSheet("background: transparent;")
        self.dp_events_layout = QVBoxLayout(self.dp_events_container)
        self.dp_events_layout.setContentsMargins(0, 4, 0, 4)
        self.dp_events_layout.setSpacing(6)

        self.dp_scroll.setWidget(self.dp_events_container)
        day_panel_layout.addWidget(self.dp_scroll, 1)

        central_layout.addWidget(self.day_panel)

        main_layout.addWidget(central_container, 1)

        # Bottom bar with legend and resize grip
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        self.legend_layout = QHBoxLayout()
        self.legend_layout.setSpacing(14)
        bottom_layout.addLayout(self.legend_layout)
        self._update_legend()

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

    def _update_legend(self) -> None:
        """Update bottom legend with base items and active calendar colors."""
        while self.legend_layout.count():
            item = self.legend_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.legend_layout.addWidget(self._make_legend_item(COLORS["today"], "Hoje"))
        self.legend_layout.addWidget(self._make_legend_item(COLORS["weekend"], "Fim de semana"))
        self.legend_layout.addWidget(self._make_legend_item(COLORS["holiday"], "Feriado"))

        # Add active calendar indicators (up to 3 for compact layout)
        shown = 0
        for cal in self.calendars:
            if cal.get("id") in self.selected_calendar_ids:
                color = cal.get("backgroundColor", COLORS["accent"])
                name = cal.get("summary", "")
                if len(name) > 12:
                    name = name[:10] + "…"
                self.legend_layout.addWidget(self._make_legend_item(color, name))
                shown += 1
                if shown >= 3:
                    break

        self.legend_layout.addStretch()

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
        self.calendar_colors = {
            c["id"]: c.get("backgroundColor", COLORS["accent"])
            for c in self.calendars
        }
        # Restore saved selection, fallback to API defaults
        saved_ids = settings.get_selected_calendar_ids()
        if saved_ids is not None:
            self.selected_calendar_ids = saved_ids
        elif not self.selected_calendar_ids and self.calendars:
            self.selected_calendar_ids = [
                c["id"] for c in self.calendars if c.get("selected", True)
            ]
        self._update_legend()

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
        self._month_cache.clear()
        self._update_legend()
        self.refresh_events()

    def refresh_events(self) -> None:
        """Fetch events asynchronously in background without UI freezing."""
        # Check cache first for instant display
        cache_key = (self.current_year, self.current_month)
        if cache_key in self._month_cache:
            self.events = self._month_cache[cache_key]
            self._organize_events_by_day()
            self._rebuild_current_view()

        # Cancel any running background worker
        if self._worker and self._worker.isRunning():
            self._worker.cancel()

        self.loading_label.setText("↻ Sincronizando...")
        self.loading_label.setVisible(True)

        cal_ids = self.selected_calendar_ids or None
        self._worker = FetchEventsWorker(
            self.current_year,
            self.current_month,
            calendar_ids=cal_ids,
            calendar_colors=self.calendar_colors,
            parent=self,
        )
        self._worker.events_loaded.connect(self._on_events_loaded)
        self._worker.fetch_error.connect(self._on_fetch_error)
        self._worker.start()

    def _on_events_loaded(self, events: list[dict], year: int, month: int) -> None:
        """Handle background fetch completion."""
        self.loading_label.setText("")
        self.loading_label.setVisible(False)

        if year != self.current_year or month != self.current_month:
            return

        self.events = events
        self._month_cache[(year, month)] = events
        self._organize_events_by_day()
        self._rebuild_current_view()

    def _on_fetch_error(self, err_msg: str) -> None:
        """Handle background fetch error."""
        self.loading_label.setText("⚠️ Erro de conexão")
        self.loading_label.setVisible(True)

    def _organize_events_by_day(self) -> None:
        """Map events to day of the current month."""
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

    def _rebuild_current_view(self) -> None:
        """Rebuild whatever view mode is active."""
        if self.current_view_mode == "month":
            self._rebuild_grid()
            if self.selected_day and self.day_panel.isVisible():
                self._populate_day_panel(self.selected_day)
        else:
            self._rebuild_agenda_view()

    def _set_view_mode(self, mode: str) -> None:
        """Switch between Month view and Agenda view."""
        self.current_view_mode = mode
        if mode == "month":
            self.btn_month_view.setStyleSheet(VIEW_TOGGLE_ACTIVE_STYLE)
            self.btn_agenda_view.setStyleSheet(VIEW_TOGGLE_BUTTON_STYLE)
            self.views_stack.setCurrentIndex(0)
            self.dow_container.setVisible(True)
            self._rebuild_grid()
        else:
            self.btn_month_view.setStyleSheet(VIEW_TOGGLE_BUTTON_STYLE)
            self.btn_agenda_view.setStyleSheet(VIEW_TOGGLE_ACTIVE_STYLE)
            self.views_stack.setCurrentIndex(1)
            self.dow_container.setVisible(False)
            self._close_day_panel()
            self._rebuild_agenda_view()

    def _on_search_changed(self, text: str) -> None:
        """Filter events when search input changes."""
        self.search_query = text.strip()
        self._rebuild_current_view()

    def _rebuild_grid(self) -> None:
        """Clear and rebuild the monthly calendar grid."""
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        today = datetime.date.today()
        cal = calendar.Calendar(firstweekday=0)
        month_days = cal.monthdayscalendar(self.current_year, self.current_month)

        for row, week in enumerate(month_days):
            for col, day in enumerate(week):
                if day == 0:
                    frame = QFrame()
                    frame.setStyleSheet(get_day_cell_style(is_other_month=True))
                    frame.setMinimumHeight(76)
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
                is_selected = (self.selected_day == date)

                frame = ClickableDayFrame(date)
                frame.setStyleSheet(
                    get_day_cell_style(
                        is_today=is_today,
                        is_weekend=weekend,
                        is_holiday=holiday,
                        is_selected=is_selected,
                    )
                )
                frame.setMinimumHeight(76)
                frame.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Expanding,
                )
                frame.single_clicked.connect(self._on_day_single_click)
                frame.double_clicked.connect(self._on_day_double_click)

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

                # Holiday name if any
                if holiday_name:
                    h_label = QLabel(holiday_name)
                    h_label.setStyleSheet(HOLIDAY_LABEL_STYLE)
                    h_label.setWordWrap(True)
                    cell_layout.addWidget(h_label)

                # Events for this day
                all_day_events = self.events_by_day.get(day, [])

                # Filter by search query if active
                if self.search_query:
                    q = self.search_query.lower()
                    day_events = [
                        e for e in all_day_events
                        if q in e.get("summary", "").lower()
                        or q in e.get("description", "").lower()
                        or q in e.get("location", "").lower()
                    ]
                else:
                    day_events = all_day_events

                max_visible = 3
                for event in day_events[:max_visible]:
                    time_str = calendar_api.get_event_time_str(event)
                    summary = event.get("summary", "Sem título")
                    display_text = f"{time_str} {summary}"
                    if len(display_text) > 28:
                        display_text = display_text[:26] + "…"

                    event_color = event.get("_color", COLORS["accent"])
                    event_label = ClickableEventLabel(display_text, event)
                    event_label.setStyleSheet(get_event_badge_style(event_color))
                    event_label.clicked.connect(self._on_event_click)
                    cell_layout.addWidget(event_label)

                if len(day_events) > max_visible:
                    more_label = QLabel(f"+{len(day_events) - max_visible} mais")
                    more_label.setStyleSheet(
                        f"color: {COLORS['accent_light']}; font-size: 9px; font-weight: bold; "
                        f"padding: 1px 4px; background: transparent; border: none;"
                    )
                    more_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                    more_label.mousePressEvent = lambda ev, d=date: self._on_day_single_click(d)
                    cell_layout.addWidget(more_label)

                cell_layout.addStretch()
                self.grid_layout.addWidget(frame, row, col)

        for col in range(7):
            self.grid_layout.setColumnStretch(col, 1)
        for row in range(len(month_days)):
            self.grid_layout.setRowStretch(row, 1)

    def _rebuild_agenda_view(self) -> None:
        """Clear and rebuild the chronological agenda list."""
        try:
            while self.agenda_layout.count():
                item = self.agenda_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            events_to_show = self.events
            if self.search_query:
                q = self.search_query.lower()
                events_to_show = [
                    e for e in self.events
                    if q in e.get("summary", "").lower()
                    or q in e.get("description", "").lower()
                    or q in e.get("location", "").lower()
                ]

            if not events_to_show:
                no_events_label = QLabel("Nenhum compromisso encontrado.")
                no_events_label.setStyleSheet(
                    f"color: {COLORS['text_muted']}; font-size: 13px; padding: 30px; font-style: italic;"
                )
                no_events_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.agenda_layout.addWidget(no_events_label)
                self.agenda_layout.addStretch()
                return

            events_by_date = defaultdict(list)
            for ev in events_to_show:
                try:
                    start_dt, _ = calendar_api.parse_event_datetime(ev)
                    ev_date = start_dt.date()
                    events_by_date[ev_date].append(ev)
                except Exception:
                    continue

            today = datetime.date.today()
            sorted_dates = sorted(events_by_date.keys())

            for dt in sorted_dates:
                group_widget = QWidget()
                group_layout = QVBoxLayout(group_widget)
                group_layout.setContentsMargins(0, 4, 0, 4)
                group_layout.setSpacing(4)

                day_name = DAY_NAMES[dt.weekday()]
                if dt == today:
                    date_str = f"Hoje • {dt.day} de {MONTH_NAMES[dt.month]} ({day_name})"
                    header_color = COLORS["today"]
                elif dt == today + datetime.timedelta(days=1):
                    date_str = f"Amanhã • {dt.day} de {MONTH_NAMES[dt.month]} ({day_name})"
                    header_color = COLORS["accent_light"]
                else:
                    date_str = f"{day_name}, {dt.day} de {MONTH_NAMES[dt.month]}"
                    header_color = COLORS["text_primary"]

                h_lbl = QLabel(date_str)
                h_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
                h_lbl.setStyleSheet(f"color: {header_color}; border: none; padding-top: 4px;")
                group_layout.addWidget(h_lbl)

                if is_holiday(dt):
                    h_name = get_holiday_name(dt)
                    hol_lbl = QLabel(f"🎉 {h_name}")
                    hol_lbl.setStyleSheet(HOLIDAY_LABEL_STYLE)
                    group_layout.addWidget(hol_lbl)

                try:
                    day_list = sorted(
                        events_by_date[dt],
                        key=lambda e: calendar_api.parse_event_datetime(e)[0]
                    )
                except Exception:
                    day_list = events_by_date[dt]

                for event in day_list:
                    card = self._create_agenda_card(event)
                    group_layout.addWidget(card)

                self.agenda_layout.addWidget(group_widget)

            self.agenda_layout.addStretch()
        except Exception as e:
            print(f"[Agenda View Error] {e}")

    def _create_agenda_card(self, event: dict) -> QFrame:
        """Create a sleek clickable card for the agenda list."""
        card = QFrame()
        card.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        event_color = event.get("_color", COLORS["accent"])
        bg_card = COLORS["bg_card"]
        bg_hover = COLORS["bg_hover"]
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_card};
                border-left: 4px solid {event_color};
                border-radius: 8px;
                border-top: 1px solid {COLORS['border']};
                border-right: 1px solid {COLORS['border']};
                border-bottom: 1px solid {COLORS['border']};
            }}
            QFrame:hover {{
                background-color: {bg_hover};
                border-color: {COLORS['border_light']};
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 8, 12, 8)
        card_layout.setSpacing(4)

        top_row = QHBoxLayout()
        time_str = calendar_api.get_event_time_range_str(event)
        time_lbl = QLabel(time_str)
        time_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        time_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
        top_row.addWidget(time_lbl)
        top_row.addStretch()

        cal_dot = QLabel("●")
        cal_dot.setStyleSheet(f"color: {event_color}; font-size: 11px; border: none;")
        top_row.addWidget(cal_dot)
        card_layout.addLayout(top_row)

        summary_lbl = QLabel(event.get("summary", "Sem título"))
        summary_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        summary_lbl.setStyleSheet(f"color: {COLORS['text_primary']}; border: none;")
        summary_lbl.setWordWrap(True)
        card_layout.addWidget(summary_lbl)

        loc = event.get("location", "")
        if loc:
            loc_lbl = QLabel(f"📍 {loc}")
            loc_lbl.setFont(QFont("Segoe UI", 10))
            loc_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; border: none;")
            loc_lbl.setWordWrap(True)
            card_layout.addWidget(loc_lbl)

        card.mousePressEvent = lambda ev, e=event: self._on_event_click(e)
        return card

    def _on_day_single_click(self, date: datetime.date) -> None:
        """Handle single-clicking on a day to inspect in the Day Panel."""
        if self.selected_day == date and self.day_panel.isVisible():
            self._close_day_panel()
            return

        self.selected_day = date
        self._populate_day_panel(date)
        self.day_panel.setVisible(True)
        self._rebuild_grid()

    def _close_day_panel(self) -> None:
        """Close the day inspector panel and clear selected day."""
        self.selected_day = None
        self.day_panel.setVisible(False)
        self._rebuild_grid()

    def _on_day_panel_add_event(self) -> None:
        """Create new event for the currently inspected day."""
        if self.selected_day:
            dialog = EventDialog(
                self, default_date=self.selected_day, calendars=self.calendars
            )
            dialog.event_saved.connect(self.refresh_events)
            dialog.exec()

    def _populate_day_panel(self, date: datetime.date) -> None:
        """Populate the side panel with events for the selected date."""
        while self.dp_events_layout.count():
            item = self.dp_events_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        weekday_str = DAY_NAMES[date.weekday()]
        self.dp_title_label.setText(f"{date.day} de {MONTH_NAMES[date.month]} ({weekday_str})")

        if is_holiday(date):
            h_name = get_holiday_name(date)
            self.dp_holiday_label.setText(f"🎉 {h_name}")
            self.dp_holiday_label.setVisible(True)
        else:
            self.dp_holiday_label.setVisible(False)

        day_events = sorted(
            self.events_by_day.get(date.day, []),
            key=lambda e: calendar_api.parse_event_datetime(e)[0]
        )

        if not day_events:
            empty_lbl = QLabel("Nenhum compromisso neste dia.")
            empty_lbl.setStyleSheet(
                f"color: {COLORS['text_muted']}; font-size: 11px; padding: 16px 0; font-style: italic;"
            )
            self.dp_events_layout.addWidget(empty_lbl)
        else:
            for event in day_events:
                event_color = event.get("_color", COLORS["accent"])
                card = QFrame()
                card.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                card.setStyleSheet(f"""
                    QFrame {{
                        background-color: {COLORS['bg_card']};
                        border-left: 4px solid {event_color};
                        border-radius: 8px;
                        border-top: 1px solid {COLORS['border']};
                        border-right: 1px solid {COLORS['border']};
                        border-bottom: 1px solid {COLORS['border']};
                    }}
                    QFrame:hover {{
                        background-color: {COLORS['bg_hover']};
                    }}
                """)
                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(10, 6, 10, 6)
                card_layout.setSpacing(2)

                time_str = calendar_api.get_event_time_range_str(event)
                time_lbl = QLabel(time_str)
                time_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
                time_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
                card_layout.addWidget(time_lbl)

                title_lbl = QLabel(event.get("summary", "Sem título"))
                title_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
                title_lbl.setStyleSheet(f"color: {COLORS['text_primary']}; border: none;")
                title_lbl.setWordWrap(True)
                card_layout.addWidget(title_lbl)

                loc = event.get("location", "")
                if loc:
                    loc_lbl = QLabel(f"📍 {loc}")
                    loc_lbl.setFont(QFont("Segoe UI", 9))
                    loc_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; border: none;")
                    loc_lbl.setWordWrap(True)
                    card_layout.addWidget(loc_lbl)

                card.mousePressEvent = lambda ev, e=event: self._on_event_click(e)
                self.dp_events_layout.addWidget(card)

        self.dp_events_layout.addStretch()

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
        default_date = self.selected_day or datetime.date.today()
        dialog = EventDialog(self, default_date=default_date, calendars=self.calendars)
        dialog.event_saved.connect(self.refresh_events)
        dialog.exec()

    def open_task_manager(self) -> None:
        """Open the Task Manager modal for viewing and managing current/upcoming tasks."""
        dialog = TaskManagerDialog(
            self,
            events=self.events,
            calendars=self.calendars,
            year=self.current_year,
            month=self.current_month,
        )
        dialog.task_changed.connect(self.refresh_events)
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

        flags = self.windowFlags()
        if enabled:
            flags = (flags | Qt.WindowType.WindowStaysOnTopHint) & ~Qt.WindowType.WindowStaysOnBottomHint
        else:
            flags = flags & ~Qt.WindowType.WindowStaysOnTopHint

        was_visible = self.isVisible()
        self.setWindowFlags(flags)
        if was_visible:
            self.show()

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
