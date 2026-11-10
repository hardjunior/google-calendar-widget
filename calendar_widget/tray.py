"""System tray icon module."""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QAction
from PyQt6.QtCore import pyqtSignal, QObject

from calendar_widget import settings
from calendar_widget.styles import BACKGROUND_THEMES



def create_tray_icon_pixmap() -> QPixmap:
    """Create a calendar-style tray icon programmatically."""
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Background
    painter.setBrush(QColor(108, 99, 255))
    painter.setPen(QColor(0, 0, 0, 0))
    painter.drawRoundedRect(4, 4, 56, 56, 12, 12)

    # Top bar
    painter.setBrush(QColor(75, 68, 204))
    painter.drawRoundedRect(4, 4, 56, 18, 12, 12)
    painter.drawRect(4, 14, 56, 8)

    # Calendar icon text
    painter.setPen(QColor(255, 255, 255))
    font = QFont("Segoe UI", 24, QFont.Weight.Bold)
    painter.setFont(font)

    import datetime
    day = str(datetime.date.today().day)
    painter.drawText(4, 20, 56, 40, 0x0084, day)  # AlignCenter | AlignVCenter

    painter.end()
    return pixmap


class TrayIcon(QObject):
    """System tray icon with context menu."""

    show_widget = pyqtSignal()
    hide_widget = pyqtSignal()
    refresh = pyqtSignal()
    create_event = pyqtSignal()
    open_tasks = pyqtSignal()
    toggle_always_on_top = pyqtSignal(bool)
    change_background = pyqtSignal(str)
    quit_app = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._visible = True

        self.tray = QSystemTrayIcon()
        self.tray.setIcon(QIcon(create_tray_icon_pixmap()))
        self.tray.setToolTip("Google Calendar Widget")
        self.tray.activated.connect(self._on_activated)

        self._setup_menu()
        self.tray.show()

    def _setup_menu(self) -> None:
        """Create the context menu for the tray icon."""
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #1C1C28;
                color: #EAEAEF;
                border: 1px solid rgba(100, 100, 140, 80);
                border-radius: 8px;
                padding: 4px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 8px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: rgba(108, 99, 255, 120);
            }
            QMenu::separator {
                height: 1px;
                background: rgba(100, 100, 140, 80);
                margin: 4px 8px;
            }
        """)

        self.toggle_action = QAction("Ocultar Widget", menu)
        self.toggle_action.triggered.connect(self._toggle_visibility)
        menu.addAction(self.toggle_action)

        menu.addSeparator()

        refresh_action = QAction("Atualizar", menu)
        refresh_action.triggered.connect(self.refresh.emit)
        menu.addAction(refresh_action)

        new_event_action = QAction("Novo Compromisso", menu)
        new_event_action.triggered.connect(self.create_event.emit)
        menu.addAction(new_event_action)

        tasks_action = QAction("📋 Gerenciar Tarefas...", menu)
        tasks_action.triggered.connect(self.open_tasks.emit)
        menu.addAction(tasks_action)

        menu.addSeparator()

        self.always_on_top_action = QAction("Sempre no topo", menu)
        self.always_on_top_action.setCheckable(True)
        self.always_on_top_action.setChecked(settings.get_always_on_top())
        self.always_on_top_action.triggered.connect(self._toggle_always_on_top)
        menu.addAction(self.always_on_top_action)

        # Background theme submenu
        bg_menu = QMenu("Cor de fundo", menu)
        bg_menu.setStyleSheet(menu.styleSheet())
        current_theme = settings.get_background_theme()
        self._bg_actions: dict[str, QAction] = {}
        for theme_key, theme_info in BACKGROUND_THEMES.items():
            action = QAction(theme_info["label"], bg_menu)
            action.setCheckable(True)
            action.setChecked(theme_key == current_theme)
            action.setData(theme_key)
            action.triggered.connect(
                lambda checked, key=theme_key: self._on_background_selected(key)
            )
            bg_menu.addAction(action)
            self._bg_actions[theme_key] = action
        menu.addMenu(bg_menu)

        menu.addSeparator()

        self.autostart_action = QAction("Iniciar com o sistema", menu)
        self.autostart_action.setCheckable(True)
        self.autostart_action.setChecked(settings.get_autostart())
        self.autostart_action.triggered.connect(self._toggle_autostart)
        menu.addAction(self.autostart_action)

        menu.addSeparator()

        quit_action = QAction("Sair", menu)
        quit_action.triggered.connect(self.quit_app.emit)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation (single/double click)."""
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._toggle_visibility()

    def _toggle_visibility(self) -> None:
        """Toggle widget visibility."""
        if self._visible:
            self.hide_widget.emit()
            self.toggle_action.setText("Mostrar Widget")
            self._visible = False
        else:
            self.show_widget.emit()
            self.toggle_action.setText("Ocultar Widget")
            self._visible = True

    def update_icon(self) -> None:
        """Update the tray icon (e.g., when day changes)."""
        self.tray.setIcon(QIcon(create_tray_icon_pixmap()))

    def show_notification(
        self, title: str, message: str, duration_ms: int = 8000
    ) -> None:
        """Show a system tray notification/balloon message."""
        if self.tray.supportsMessages():
            self.tray.showMessage(
                title,
                message,
                QSystemTrayIcon.MessageIcon.Information,
                duration_ms,
            )

    def _toggle_always_on_top(self, checked: bool) -> None:
        """Toggle always-on-top and persist."""
        settings.set_always_on_top(checked)
        self.toggle_always_on_top.emit(checked)

    def set_always_on_top_checked(self, checked: bool) -> None:
        """Update tray menu action checkmark without re-emitting."""
        if hasattr(self, "always_on_top_action"):
            self.always_on_top_action.blockSignals(True)
            self.always_on_top_action.setChecked(checked)
            self.always_on_top_action.blockSignals(False)

    def _on_background_selected(self, theme_key: str) -> None:
        """Handle background theme selection."""
        settings.set_background_theme(theme_key)
        # Update checkmarks
        for key, action in self._bg_actions.items():
            action.setChecked(key == theme_key)
        self.change_background.emit(theme_key)

    def _toggle_autostart(self, checked: bool) -> None:
        """Toggle autostart with system."""
        settings.set_autostart(checked)

    def hide(self) -> None:
        """Hide the tray icon."""
        self.tray.hide()
