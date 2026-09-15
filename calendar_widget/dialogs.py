"""Event dialogs for viewing, editing, and creating calendar events."""

import datetime
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QDateTimeEdit,
    QPushButton,
    QMessageBox,
    QFileDialog,
    QComboBox,
    QCheckBox,
    QScrollArea,
    QWidget,
    QFrame,
    QStackedWidget,
)
from PyQt6.QtCore import Qt, QDateTime, pyqtSignal, QThread
from PyQt6.QtGui import QFont

from calendar_widget.styles import DIALOG_STYLE, SETUP_DIALOG_STYLE, COLORS
from calendar_widget import calendar_api
from calendar_widget.calendar_api import RECURRENCE_OPTIONS, REMINDER_OPTIONS


def _make_remove_btn_style() -> str:
    """Style for the small remove button next to each reminder row."""
    return (
        f"QPushButton {{ background: transparent; color: {COLORS['text_muted']}; "
        f"border: none; font-size: 14px; padding: 2px 6px; border-radius: 4px; }} "
        f"QPushButton:hover {{ background: {COLORS['bg_hover']}; "
        f"color: {COLORS['text_primary']}; }}"
    )


class EventDialog(QDialog):
    """Dialog for creating or editing a calendar event."""

    event_saved = pyqtSignal()

    def __init__(
        self,
        parent=None,
        event: Optional[dict] = None,
        default_date: Optional[datetime.date] = None,
        calendars: Optional[list[dict]] = None,
    ):
        super().__init__(parent)
        self.event = event
        self.is_edit = event is not None
        self.calendars = calendars or []
        self.setWindowTitle(
            "Editar Compromisso" if self.is_edit else "Novo Compromisso"
        )
        self.setMinimumSize(420, 500)
        self.setMaximumSize(520, 720)
        self.setStyleSheet(DIALOG_STYLE)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint
        )
        self._setup_ui(default_date)

    def _setup_ui(self, default_date: Optional[datetime.date] = None) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setSpacing(8)
        outer_layout.setContentsMargins(24, 20, 24, 20)

        # Title header
        title_label = QLabel(
            "Editar Compromisso" if self.is_edit else "Novo Compromisso"
        )
        title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {COLORS['accent']}; border: none;")
        outer_layout.addWidget(title_label)

        # Scrollable form area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
        )
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setSpacing(10)
        form_layout.setContentsMargins(0, 0, 4, 0)

        # Summary
        form_layout.addWidget(self._make_field_label("T\u00edtulo"))
        self.summary_edit = QLineEdit()
        self.summary_edit.setPlaceholderText("Nome do compromisso...")
        form_layout.addWidget(self.summary_edit)

        # Start / End in one row (compact)
        time_row = QHBoxLayout()
        time_row.setSpacing(8)

        start_col = QVBoxLayout()
        start_col.setSpacing(2)
        start_col.addWidget(self._make_field_label("In\u00edcio"))
        self.start_edit = QDateTimeEdit()
        self.start_edit.setDisplayFormat("dd/MM/yy HH:mm")
        self.start_edit.setCalendarPopup(True)
        self.start_edit.setFixedHeight(32)
        start_col.addWidget(self.start_edit)
        time_row.addLayout(start_col)

        end_col = QVBoxLayout()
        end_col.setSpacing(2)
        end_col.addWidget(self._make_field_label("Fim"))
        self.end_edit = QDateTimeEdit()
        self.end_edit.setDisplayFormat("dd/MM/yy HH:mm")
        self.end_edit.setCalendarPopup(True)
        self.end_edit.setFixedHeight(32)
        end_col.addWidget(self.end_edit)
        time_row.addLayout(end_col)

        form_layout.addLayout(time_row)

        # Recurrence + Location in one row
        extra_row = QHBoxLayout()
        extra_row.setSpacing(8)

        recur_col = QVBoxLayout()
        recur_col.setSpacing(2)
        recur_col.addWidget(self._make_field_label("Repetir"))
        self.recurrence_combo = QComboBox()
        self.recurrence_combo.setFixedHeight(32)
        for label in RECURRENCE_OPTIONS:
            self.recurrence_combo.addItem(label)
        recur_col.addWidget(self.recurrence_combo)
        extra_row.addLayout(recur_col)

        loc_col = QVBoxLayout()
        loc_col.setSpacing(2)
        loc_col.addWidget(self._make_field_label("Local"))
        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("Local (opcional)")
        self.location_edit.setFixedHeight(32)
        loc_col.addWidget(self.location_edit)
        extra_row.addLayout(loc_col)

        form_layout.addLayout(extra_row)

        # Reminders (multiple)
        form_layout.addWidget(self._make_field_label("Alertas"))

        self.reminders_widget = QWidget()
        self.reminders_layout = QVBoxLayout(self.reminders_widget)
        self.reminders_layout.setSpacing(6)
        self.reminders_layout.setContentsMargins(0, 0, 0, 0)
        self.reminder_rows: list[tuple[QWidget, QComboBox, QPushButton]] = []
        form_layout.addWidget(self.reminders_widget)

        add_reminder_btn = QPushButton("+ Adicionar alerta")
        add_reminder_btn.setFixedHeight(32)
        add_reminder_btn.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['bg_card']}; "
            f"color: {COLORS['accent']}; "
            f"border: 1px dashed {COLORS['accent']}; "
            f"border-radius: 8px; "
            f"font-size: 13px; font-weight: bold; "
            f"font-family: 'Segoe UI', sans-serif; "
            f"padding: 4px 12px; min-width: 0; }} "
            f"QPushButton:hover {{ background-color: {COLORS['bg_hover']}; "
            f"border-style: solid; }}"
        )
        add_reminder_btn.clicked.connect(self._add_reminder_row)
        form_layout.addWidget(add_reminder_btn)

        # Calendar selection
        if self.calendars:
            writable = [
                c for c in self.calendars
                if c.get("accessRole") in ("owner", "writer")
            ]
            if writable:
                form_layout.addWidget(self._make_field_label("Calend\u00e1rio"))
                self.calendar_combo = QComboBox()
                self.calendar_combo.setFixedHeight(32)
                for cal in writable:
                    display = cal["summary"]
                    if cal.get("primary"):
                        display += " (principal)"
                    self.calendar_combo.addItem(display, cal["id"])
                form_layout.addWidget(self.calendar_combo)
            else:
                self.calendar_combo = None
        else:
            self.calendar_combo = None

        # Description (compact)
        form_layout.addWidget(self._make_field_label("Descri\u00e7\u00e3o"))
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Detalhes (opcional)...")
        self.description_edit.setMaximumHeight(60)
        form_layout.addWidget(self.description_edit)

        form_layout.addStretch()

        # Set default values
        if self.is_edit and self.event:
            self._populate_from_event()
        else:
            self._set_defaults(default_date)

        scroll.setWidget(form_widget)
        outer_layout.addWidget(scroll, 1)

        # Buttons (fixed at bottom, outside scroll)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        if self.is_edit:
            delete_btn = QPushButton("Excluir")
            delete_btn.setObjectName("deleteBtn")
            delete_btn.clicked.connect(self._delete_event)
            btn_layout.addWidget(delete_btn)

        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Salvar")
        save_btn.clicked.connect(self._save_event)
        btn_layout.addWidget(save_btn)

        outer_layout.addLayout(btn_layout)

    def _make_field_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; border: none; padding: 0;"
        )
        return label

    def _populate_from_event(self) -> None:
        if not self.event:
            return
        self.summary_edit.setText(self.event.get("summary", ""))
        self.location_edit.setText(self.event.get("location", ""))
        self.description_edit.setPlainText(self.event.get("description", ""))

        start_dt, end_dt = calendar_api.parse_event_datetime(self.event)
        self.start_edit.setDateTime(
            QDateTime(
                start_dt.year, start_dt.month, start_dt.day,
                start_dt.hour, start_dt.minute,
            )
        )
        self.end_edit.setDateTime(
            QDateTime(
                end_dt.year, end_dt.month, end_dt.day,
                end_dt.hour, end_dt.minute,
            )
        )

        # Set recurrence
        recur_label = calendar_api.get_event_recurrence_label(self.event)
        idx = self.recurrence_combo.findText(recur_label)
        if idx >= 0:
            self.recurrence_combo.setCurrentIndex(idx)

        # Set reminders
        existing_minutes = calendar_api.get_event_reminder_minutes(self.event)
        if existing_minutes is not None:
            for mins in existing_minutes:
                label = calendar_api._minutes_to_label(mins)
                self._add_reminder_row(preset_label=label)

        # Set calendar
        if self.calendar_combo and self.event.get("_calendarId"):
            cal_idx = self.calendar_combo.findData(self.event["_calendarId"])
            if cal_idx >= 0:
                self.calendar_combo.setCurrentIndex(cal_idx)

    def _add_reminder_row(
        self, preset_label: Optional[str] = None,
    ) -> None:
        """Add a new reminder row with a combo and remove button."""
        row_widget = QWidget()
        row_widget.setFixedHeight(40)
        row_layout = QHBoxLayout(row_widget)
        row_layout.setSpacing(6)
        row_layout.setContentsMargins(0, 0, 0, 0)

        combo = QComboBox()
        combo.setFixedHeight(32)
        for label in REMINDER_OPTIONS:
            combo.addItem(label)
        if preset_label:
            idx = combo.findText(preset_label)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        row_layout.addWidget(combo, 1)

        remove_btn = QPushButton("\u2715")
        remove_btn.setFixedSize(32, 32)
        remove_btn.setStyleSheet(_make_remove_btn_style())
        remove_btn.setToolTip("Remover alerta")
        row_layout.addWidget(remove_btn)

        self.reminders_layout.addWidget(row_widget)
        entry = (row_widget, combo, remove_btn)
        self.reminder_rows.append(entry)

        remove_btn.clicked.connect(lambda: self._remove_reminder_row(entry))

    def _remove_reminder_row(
        self, entry: tuple[QWidget, QComboBox, QPushButton],
    ) -> None:
        """Remove a reminder row from the form."""
        row_widget, _combo, _remove_btn = entry
        if entry in self.reminder_rows:
            self.reminder_rows.remove(entry)
        row_widget.deleteLater()

    def _set_defaults(self, default_date: Optional[datetime.date] = None) -> None:
        now = datetime.datetime.now()
        if default_date:
            start = QDateTime(
                default_date.year, default_date.month, default_date.day,
                now.hour + 1, 0,
            )
        else:
            start = QDateTime(now.year, now.month, now.day, now.hour + 1, 0)

        self.start_edit.setDateTime(start)
        self.end_edit.setDateTime(start.addSecs(3600))

    def _save_event(self) -> None:
        summary = self.summary_edit.text().strip()
        if not summary:
            QMessageBox.warning(self, "Aviso", "O t\u00edtulo \u00e9 obrigat\u00f3rio.")
            return

        start_qdt = self.start_edit.dateTime()
        end_qdt = self.end_edit.dateTime()

        start_dt = datetime.datetime(
            start_qdt.date().year(), start_qdt.date().month(),
            start_qdt.date().day(), start_qdt.time().hour(),
            start_qdt.time().minute(),
        )
        end_dt = datetime.datetime(
            end_qdt.date().year(), end_qdt.date().month(),
            end_qdt.date().day(), end_qdt.time().hour(),
            end_qdt.time().minute(),
        )

        description = self.description_edit.toPlainText().strip()
        location = self.location_edit.text().strip()

        # Recurrence
        recur_text = self.recurrence_combo.currentText()
        recurrence = RECURRENCE_OPTIONS.get(recur_text)

        # Reminders
        reminder_minutes_list: list[int] | None = None
        if self.reminder_rows:
            reminder_minutes_list = []
            for _widget, combo, _btn in self.reminder_rows:
                mins = REMINDER_OPTIONS.get(combo.currentText())
                if mins is not None:
                    reminder_minutes_list.append(mins)

        # Calendar
        cal_id = "primary"
        if self.calendar_combo:
            cal_id = self.calendar_combo.currentData() or "primary"

        if self.is_edit and self.event:
            result = calendar_api.update_event(
                event_id=self.event["id"],
                summary=summary,
                start_datetime=start_dt,
                end_datetime=end_dt,
                description=description,
                location=location,
                recurrence=recurrence,
                reminder_minutes_list=reminder_minutes_list,
                calendar_id=cal_id,
            )
        else:
            result = calendar_api.create_event(
                summary=summary,
                start_datetime=start_dt,
                end_datetime=end_dt,
                description=description,
                location=location,
                recurrence=recurrence,
                reminder_minutes_list=reminder_minutes_list,
                calendar_id=cal_id,
            )

        if result:
            self.event_saved.emit()
            self.accept()
        else:
            QMessageBox.critical(
                self, "Erro",
                "N\u00e3o foi poss\u00edvel salvar o compromisso. Verifique sua conex\u00e3o.",
            )

    def _delete_event(self) -> None:
        if not self.event:
            return
        reply = QMessageBox.question(
            self, "Confirmar Exclus\u00e3o",
            "Tem certeza que deseja excluir este compromisso?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            cal_id = self.event.get("_calendarId", "primary")
            if calendar_api.delete_event(self.event["id"], calendar_id=cal_id):
                self.event_saved.emit()
                self.accept()
            else:
                QMessageBox.critical(
                    self, "Erro",
                    "N\u00e3o foi poss\u00edvel excluir o compromisso.",
                )


class EventViewDialog(QDialog):
    """Dialog for viewing event details."""

    edit_requested = pyqtSignal(dict)

    def __init__(self, parent=None, event: Optional[dict] = None):
        super().__init__(parent)
        self.event = event
        self.setWindowTitle("Detalhes do Compromisso")
        self.setMinimumSize(380, 300)
        self.setMaximumSize(500, 420)
        self.setStyleSheet(DIALOG_STYLE)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint
        )
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(24, 20, 24, 20)

        if not self.event:
            layout.addWidget(QLabel("Evento não encontrado."))
            return

        title = QLabel(self.event.get("summary", "Sem título"))
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['accent']}; border: none;")
        title.setWordWrap(True)
        layout.addWidget(title)

        time_str = calendar_api.get_event_time_str(self.event)
        start_dt, end_dt = calendar_api.parse_event_datetime(self.event)
        date_str = start_dt.strftime("%d/%m/%Y")
        end_time = end_dt.strftime("%H:%M") if time_str != "Dia inteiro" else ""
        time_display = f"{date_str}  •  {time_str}"
        if end_time:
            time_display += f" - {end_time}"

        time_label = QLabel(time_display)
        time_label.setFont(QFont("Segoe UI", 12))
        time_label.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
        layout.addWidget(time_label)

        recur_label = calendar_api.get_event_recurrence_label(self.event)
        if recur_label != "Não repetir":
            recur = QLabel(f"🔁 {recur_label}")
            recur.setFont(QFont("Segoe UI", 11))
            recur.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
            layout.addWidget(recur)

        reminder_labels = calendar_api.get_event_reminder_labels(self.event)
        for rlabel in reminder_labels:
            reminder = QLabel(f"🔔 {rlabel}")
            reminder.setFont(QFont("Segoe UI", 11))
            reminder.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
            layout.addWidget(reminder)

        location = self.event.get("location", "")
        if location:
            loc_label = QLabel(f"📍 {location}")
            loc_label.setFont(QFont("Segoe UI", 11))
            loc_label.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
            loc_label.setWordWrap(True)
            layout.addWidget(loc_label)

        description = self.event.get("description", "")
        if description:
            sep = QLabel("")
            sep.setFixedHeight(1)
            sep.setStyleSheet(f"background-color: {COLORS['border']}; border: none;")
            layout.addWidget(sep)
            desc_label = QLabel(description)
            desc_label.setFont(QFont("Segoe UI", 11))
            desc_label.setStyleSheet(f"color: {COLORS['text_primary']}; border: none;")
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()
        close_btn = QPushButton("Fechar")
        close_btn.setObjectName("cancelBtn")
        close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(close_btn)
        edit_btn = QPushButton("Editar")
        edit_btn.clicked.connect(self._on_edit)
        btn_layout.addWidget(edit_btn)
        layout.addLayout(btn_layout)

    def _on_edit(self) -> None:
        if self.event:
            self.edit_requested.emit(self.event)
            self.accept()


class CalendarFilterDialog(QDialog):
    """Dialog for selecting which calendars to display."""

    calendars_changed = pyqtSignal(list)

    def __init__(
        self,
        parent=None,
        calendars: Optional[list[dict]] = None,
        selected_ids: Optional[list[str]] = None,
    ):
        super().__init__(parent)
        self.calendars = calendars or []
        self.selected_ids = set(selected_ids or [])
        self.setWindowTitle("Calendários")
        self.setMinimumSize(340, 300)
        self.setMaximumSize(440, 500)
        self.setStyleSheet(DIALOG_STYLE)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint
        )
        self.checkboxes: list[tuple[QCheckBox, str]] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(24, 20, 24, 20)

        title = QLabel("Selecionar Calendários")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['accent']}; border: none;")
        layout.addWidget(title)

        subtitle = QLabel("Escolha quais calendários exibir no widget:")
        subtitle.setFont(QFont("Segoe UI", 11))
        subtitle.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
        layout.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        list_layout = QVBoxLayout(container)
        list_layout.setSpacing(6)
        list_layout.setContentsMargins(4, 4, 4, 4)

        for cal in self.calendars:
            cb = QCheckBox(cal["summary"])
            cb.setChecked(cal["id"] in self.selected_ids)
            color = cal.get("backgroundColor", "#6C63FF")
            cb.setStyleSheet(
                f"QCheckBox {{ color: {COLORS['text_primary']}; font-size: 13px; "
                f"font-family: 'Segoe UI', sans-serif; padding: 6px 8px; "
                f"border-radius: 6px; border: none; background: transparent; }} "
                f"QCheckBox:hover {{ background: {COLORS['bg_hover']}; }} "
                f"QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px; "
                f"border: 2px solid {color}; }} "
                f"QCheckBox::indicator:checked {{ background-color: {color}; }}"
            )
            if cal.get("primary"):
                cb.setText(cal["summary"] + " (principal)")
            self.checkboxes.append((cb, cal["id"]))
            list_layout.addWidget(cb)

        list_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        sel_row = QHBoxLayout()
        sel_row.setSpacing(8)
        all_btn = QPushButton("Todos")
        all_btn.setObjectName("cancelBtn")
        all_btn.clicked.connect(self._select_all)
        sel_row.addWidget(all_btn)
        none_btn = QPushButton("Nenhum")
        none_btn.setObjectName("cancelBtn")
        none_btn.clicked.connect(self._select_none)
        sel_row.addWidget(none_btn)
        sel_row.addStretch()
        layout.addLayout(sel_row)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        save_btn = QPushButton("Aplicar")
        save_btn.clicked.connect(self._apply)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _select_all(self) -> None:
        for cb, _ in self.checkboxes:
            cb.setChecked(True)

    def _select_none(self) -> None:
        for cb, _ in self.checkboxes:
            cb.setChecked(False)

    def _apply(self) -> None:
        selected = [cal_id for cb, cal_id in self.checkboxes if cb.isChecked()]
        if not selected:
            QMessageBox.warning(self, "Aviso", "Selecione pelo menos um calendário.")
            return
        self.calendars_changed.emit(selected)
        self.accept()


class AuthWorker(QThread):
    """Worker thread to run OAuth local server without blocking the GUI."""
    finished_success = pyqtSignal(object)
    finished_error = pyqtSignal(str)

    def run(self) -> None:
        try:
            from calendar_widget.auth import authenticate
            creds = authenticate()
            if creds:
                self.finished_success.emit(creds)
            else:
                self.finished_error.emit("A autenticação não foi concluída. Tente novamente.")
        except Exception as e:
            self.finished_error.emit(str(e))


class SetupDialog(QDialog):
    """Dialog to guide user through Google Calendar connection."""

    auth_completed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Conectar ao Google - Google Calendar Widget")
        self.setFixedSize(540, 500)
        self.setStyleSheet(SETUP_DIALOG_STYLE)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint
        )
        self._auth_worker: Optional[AuthWorker] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(36, 32, 36, 28)

        # Header
        title = QLabel("Google Calendar Widget")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        subtitle = QLabel(
            "Sincronize sua agenda e veja seus compromissos\n"
            "diretamente na sua área de trabalho."
        )
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(subtitle)

        # Stacked pages for Easy Mode vs Advanced Mode
        self.stack = QStackedWidget()

        # Page 0: Quick Connect (1 click)
        self.quick_page = self._create_quick_page()
        self.stack.addWidget(self.quick_page)

        # Page 1: Advanced / Manual Credentials
        self.manual_page = self._create_manual_page()
        self.stack.addWidget(self.manual_page)

        main_layout.addWidget(self.stack)

        # Determine which page to show initially
        from calendar_widget.auth import has_client_secret
        if has_client_secret():
            self.stack.setCurrentWidget(self.quick_page)
        else:
            self.stack.setCurrentWidget(self.manual_page)

    def _create_quick_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(18)
        layout.setContentsMargins(0, 8, 0, 0)

        # Info card
        info_card = QFrame()
        info_card.setObjectName("info_card")
        card_layout = QVBoxLayout(info_card)
        card_layout.setSpacing(10)
        card_layout.setContentsMargins(16, 16, 16, 16)

        item1 = QLabel("🔒  Autenticação segura via Google OAuth 2.0")
        item1.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 13px; font-weight: 500;")
        card_layout.addWidget(item1)

        item2 = QLabel("⚡  Acesso em 1 clique: autorize na sua conta Google no navegador")
        item2.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        card_layout.addWidget(item2)

        item3 = QLabel("💻  Seus dados e tokens ficam armazenados somente no seu computador")
        item3.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        card_layout.addWidget(item3)

        layout.addWidget(info_card)
        layout.addSpacing(6)

        # Connect button
        self.connect_btn = QPushButton("🌐  Conectar com o Google")
        self.connect_btn.setObjectName("connect_btn")
        self.connect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.connect_btn.clicked.connect(self._start_quick_connect)
        layout.addWidget(self.connect_btn)

        # Status label
        self.status_label = QLabel("Clique no botão acima para autorizar no seu navegador.")
        self.status_label.setObjectName("status_label")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        layout.addStretch()

        # Advanced link
        advanced_btn = QPushButton("⚙️ Configurações avançadas (trocar credenciais)")
        advanced_btn.setObjectName("link_btn")
        advanced_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        advanced_btn.clicked.connect(lambda: self.stack.setCurrentWidget(self.manual_page))
        layout.addWidget(advanced_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        return widget

    def _create_manual_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)

        info = QLabel("Configurar credenciais da API Google (client_secret.json):")
        info.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 13px; font-weight: 500;")
        layout.addWidget(info)

        btns_row = QHBoxLayout()
        btns_row.setSpacing(8)

        import_btn = QPushButton("📁 Importar Arquivo JSON")
        import_btn.setObjectName("secondary_btn")
        import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        import_btn.clicked.connect(self._import_credentials)
        btns_row.addWidget(import_btn)

        console_btn = QPushButton("🌐 Abrir Console Google")
        console_btn.setObjectName("secondary_btn")
        console_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        console_btn.clicked.connect(self._open_console)
        btns_row.addWidget(console_btn)

        layout.addLayout(btns_row)

        paste_label = QLabel("Ou cole o conteúdo do client_secret.json abaixo:")
        paste_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        layout.addWidget(paste_label)

        self.json_edit = QTextEdit()
        self.json_edit.setPlaceholderText('{"installed": {"client_id": "...", ...}}')
        self.json_edit.setMaximumHeight(85)
        layout.addWidget(self.json_edit)

        save_json_btn = QPushButton("Salvar Credenciais e Conectar")
        save_json_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_json_btn.clicked.connect(self._save_pasted_json)
        layout.addWidget(save_json_btn)

        layout.addStretch()

        # Link back to quick connect if client secret exists
        self.back_btn = QPushButton("⬅ Voltar para conexão rápida")
        self.back_btn.setObjectName("link_btn")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.clicked.connect(self._back_to_quick)
        layout.addWidget(self.back_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        return widget

    def _back_to_quick(self) -> None:
        from calendar_widget.auth import has_client_secret
        if has_client_secret():
            self.stack.setCurrentWidget(self.quick_page)
        else:
            QMessageBox.information(
                self, "Aviso",
                "É necessário importar ou colar as credenciais antes de prosseguir."
            )

    def _start_quick_connect(self) -> None:
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("Aguardando no navegador...")
        self.status_label.setText(
            "🔄 Abrindo navegador... Faça login e clique em 'Permitir' para concluir."
        )

        self._auth_worker = AuthWorker(self)
        self._auth_worker.finished_success.connect(self._on_auth_success)
        self._auth_worker.finished_error.connect(self._on_auth_error)
        self._auth_worker.start()

    def _on_auth_success(self, creds) -> None:
        self.status_label.setText("✅ Conectado com sucesso!")
        QMessageBox.information(
            self, "Sucesso",
            "Conexão com o Google Calendar estabelecida com sucesso!",
        )
        self.auth_completed.emit()
        self.accept()

    def _on_auth_error(self, err_msg: str) -> None:
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("🌐  Tentar Conectar Novamente")
        self.status_label.setText(f"❌ {err_msg}")
        QMessageBox.warning(
            self, "Aviso",
            f"Não foi possível autenticar:\n{err_msg}\n\nPor favor, tente novamente.",
        )

    def _open_console(self) -> None:
        from calendar_widget.auth import open_setup_instructions
        open_setup_instructions()

    def _import_credentials(self) -> None:
        import json
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar client_secret.json", "", "JSON Files (*.json)",
        )
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                from calendar_widget.auth import save_client_secret
                save_client_secret(data)
                self.stack.setCurrentWidget(self.quick_page)
                self._start_quick_connect()
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Arquivo inválido: {e}")

    def _save_pasted_json(self) -> None:
        import io
        import json
        text = self.json_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Aviso", "Cole o conteúdo JSON primeiro.")
            return
        try:
            data = json.load(io.StringIO(text))
            from calendar_widget.auth import save_client_secret
            save_client_secret(data)
            self.stack.setCurrentWidget(self.quick_page)
            self._start_quick_connect()
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"JSON inválido: {e}")
