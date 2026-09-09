"""Modern UI styles and theming for the calendar widget."""

# Color palette
COLORS = {
    "bg_primary": "rgba(18, 18, 24, 200)",
    "bg_secondary": "rgba(28, 28, 40, 220)",
    "bg_card": "rgba(38, 38, 55, 230)",
    "bg_hover": "rgba(55, 55, 80, 240)",
    "text_primary": "#EAEAEF",
    "text_secondary": "#9A9AB0",
    "text_muted": "#6B6B80",
    "accent": "#6C63FF",
    "accent_light": "#8B83FF",
    "accent_dark": "#4B44CC",
    "weekend": "#FF6B8A",
    "weekend_bg": "rgba(255, 107, 138, 40)",
    "holiday": "#FFB347",
    "holiday_bg": "rgba(255, 179, 71, 40)",
    "today": "#00D4AA",
    "today_bg": "rgba(0, 212, 170, 50)",
    "event_blue": "#4DA6FF",
    "event_green": "#4DFF88",
    "event_purple": "#B388FF",
    "event_orange": "#FFB74D",
    "border": "rgba(100, 100, 140, 80)",
    "border_light": "rgba(140, 140, 180, 60)",
    "scrollbar": "rgba(100, 100, 140, 100)",
    "scrollbar_hover": "rgba(140, 140, 180, 150)",
    "danger": "#FF5252",
    "success": "#4CAF50",
}

# Background theme presets: (bg_color, border_color, label)
BACKGROUND_THEMES = {
    "dark": {
        "bg": "rgba(18, 18, 24, 200)",
        "border": "rgba(100, 100, 140, 80)",
        "label": "Escuro (padrão)",
    },
    "light": {
        "bg": "rgba(240, 240, 245, 210)",
        "border": "rgba(180, 180, 200, 120)",
        "label": "Claro",
    },
    "blue": {
        "bg": "rgba(15, 25, 50, 200)",
        "border": "rgba(60, 100, 180, 100)",
        "label": "Azul",
    },
    "purple": {
        "bg": "rgba(30, 15, 45, 200)",
        "border": "rgba(120, 80, 180, 100)",
        "label": "Roxo",
    },
    "green": {
        "bg": "rgba(10, 30, 20, 200)",
        "border": "rgba(60, 160, 100, 100)",
        "label": "Verde",
    },
}


def get_main_widget_style(theme: str = "dark") -> str:
    """Return the main widget style for a given background theme."""
    t = BACKGROUND_THEMES.get(theme, BACKGROUND_THEMES["dark"])
    return f"""
QWidget#mainWidget {{
    background-color: {t['bg']};
    border-radius: 16px;
    border: 1px solid {t['border']};
}}
"""


MAIN_WIDGET_STYLE = get_main_widget_style("dark")

HEADER_STYLE = f"""
QLabel#headerMonth {{
    color: {COLORS['text_primary']};
    font-size: 28px;
    font-weight: bold;
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;
    padding: 8px 16px;
}}
QLabel#headerYear {{
    color: {COLORS['text_secondary']};
    font-size: 18px;
    font-weight: normal;
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;
    padding: 8px 4px;
}}
"""

NAV_BUTTON_STYLE = f"""
QPushButton {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 16px;
    font-weight: bold;
    min-width: 36px;
    min-height: 36px;
}}
QPushButton:hover {{
    background-color: {COLORS['bg_hover']};
    border-color: {COLORS['accent']};
}}
QPushButton:pressed {{
    background-color: {COLORS['accent_dark']};
}}
"""

DAY_HEADER_STYLE = f"""
QLabel {{
    color: {COLORS['text_secondary']};
    font-size: 12px;
    font-weight: bold;
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;
    padding: 4px;
    text-transform: uppercase;
    letter-spacing: 1px;
}}
"""

WEEKEND_DAY_HEADER_STYLE = f"""
QLabel {{
    color: {COLORS['weekend']};
    font-size: 12px;
    font-weight: bold;
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;
    padding: 4px;
    text-transform: uppercase;
    letter-spacing: 1px;
}}
"""


def get_day_cell_style(
    is_today: bool = False,
    is_weekend: bool = False,
    is_holiday: bool = False,
    is_other_month: bool = False,
) -> str:
    """Generate style for a day cell based on its properties."""
    if is_other_month:
        return """
        QFrame {
            background-color: rgba(20, 20, 30, 100);
            border-radius: 10px;
            border: 1px solid transparent;
        }
        """

    bg_color = COLORS["bg_card"]
    border_color = "transparent"
    border_width = "1px"

    if is_today:
        bg_color = COLORS["today_bg"]
        border_color = COLORS["today"]
        border_width = "2px"
    elif is_holiday:
        bg_color = COLORS["holiday_bg"]
        border_color = COLORS["holiday"]
    elif is_weekend:
        bg_color = COLORS["weekend_bg"]
        border_color = COLORS["weekend"]

    return f"""
    QFrame {{
        background-color: {bg_color};
        border-radius: 10px;
        border: {border_width} solid {border_color};
    }}
    QFrame:hover {{
        background-color: {COLORS['bg_hover']};
        border-color: {COLORS['accent']};
    }}
    """


def get_day_number_style(
    is_today: bool = False,
    is_weekend: bool = False,
    is_holiday: bool = False,
    is_other_month: bool = False,
) -> str:
    """Generate style for day number label."""
    if is_other_month:
        color = COLORS["text_muted"]
    elif is_today:
        color = COLORS["today"]
    elif is_holiday:
        color = COLORS["holiday"]
    elif is_weekend:
        color = COLORS["weekend"]
    else:
        color = COLORS["text_primary"]

    font_weight = "bold" if is_today else "600"
    font_size = "15px" if is_today else "13px"

    return f"""
    QLabel {{
        color: {color};
        font-size: {font_size};
        font-weight: {font_weight};
        font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;
        padding: 2px 6px;
        background: transparent;
        border: none;
    }}
    """


EVENT_LABEL_STYLE = f"""
QLabel {{
    color: {COLORS['text_primary']};
    font-size: 10px;
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;
    padding: 2px 6px;
    border-radius: 4px;
    background-color: rgba(108, 99, 255, 120);
    border: none;
    margin: 1px 2px;
}}
QLabel:hover {{
    background-color: rgba(108, 99, 255, 180);
}}
"""

HOLIDAY_LABEL_STYLE = f"""
QLabel {{
    color: {COLORS['holiday']};
    font-size: 9px;
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;
    padding: 1px 4px;
    background: transparent;
    border: none;
}}
"""

SCROLLBAR_STYLE = f"""
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {COLORS['scrollbar']};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLORS['scrollbar_hover']};
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: transparent;
}}
"""

DIALOG_STYLE = f"""
QDialog {{
    background-color: {COLORS['bg_secondary']};
    border-radius: 16px;
    border: 1px solid {COLORS['border']};
}}
QLabel {{
    color: {COLORS['text_primary']};
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;
}}
QLineEdit, QTextEdit, QDateTimeEdit, QComboBox {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 14px;
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;
    selection-background-color: {COLORS['accent']};
}}
QLineEdit:focus, QTextEdit:focus, QDateTimeEdit:focus, QComboBox:focus {{
    border-color: {COLORS['accent']};
}}
QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {COLORS['text_secondary']};
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    selection-background-color: {COLORS['accent']};
    padding: 4px;
}}
QPushButton {{
    background-color: {COLORS['accent']};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    font-size: 14px;
    font-weight: bold;
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;
    min-width: 100px;
}}
QPushButton:hover {{
    background-color: {COLORS['accent_light']};
}}
QPushButton:pressed {{
    background-color: {COLORS['accent_dark']};
}}
QPushButton#cancelBtn {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    color: {COLORS['text_secondary']};
}}
QPushButton#cancelBtn:hover {{
    background-color: {COLORS['bg_hover']};
    border-color: {COLORS['text_secondary']};
}}
QPushButton#deleteBtn {{
    background-color: {COLORS['danger']};
}}
QPushButton#deleteBtn:hover {{
    background-color: #FF7070;
}}
"""

TODAY_BUTTON_STYLE = f"""
QPushButton {{
    background-color: {COLORS['today']};
    color: {COLORS['bg_primary']};
    border: none;
    border-radius: 8px;
    padding: 6px 16px;
    font-size: 12px;
    font-weight: bold;
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;
}}
QPushButton:hover {{
    background-color: #33DDBB;
}}
"""

SETUP_DIALOG_STYLE = f"""
QDialog {{
    background-color: {COLORS['bg_secondary']};
}}
QLabel {{
    color: {COLORS['text_primary']};
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;
    font-size: 14px;
}}
QLabel#title {{
    font-size: 24px;
    font-weight: bold;
    color: {COLORS['accent']};
}}
QLabel#subtitle {{
    font-size: 13px;
    color: {COLORS['text_secondary']};
    line-height: 1.4;
}}
QLabel#status_label {{
    font-size: 13px;
    color: {COLORS['text_secondary']};
}}
QFrame#info_card {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
}}
QPushButton {{
    background-color: {COLORS['accent']};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 12px 28px;
    font-size: 14px;
    font-weight: bold;
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;
}}
QPushButton:hover {{
    background-color: {COLORS['accent_light']};
}}
QPushButton#connect_btn {{
    background-color: #4285F4;
    color: white;
    border: none;
    border-radius: 10px;
    padding: 14px 24px;
    font-size: 16px;
    font-weight: bold;
}}
QPushButton#connect_btn:hover {{
    background-color: #3367D6;
}}
QPushButton#connect_btn:disabled {{
    background-color: #3A3D4A;
    color: {COLORS['text_muted']};
}}
QPushButton#link_btn {{
    background: transparent;
    color: {COLORS['text_muted']};
    border: none;
    font-size: 12px;
    padding: 4px 8px;
    text-decoration: underline;
    font-weight: normal;
}}
QPushButton#link_btn:hover {{
    color: {COLORS['text_primary']};
}}
QPushButton#secondary_btn {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    font-size: 13px;
    padding: 8px 16px;
}}
QPushButton#secondary_btn:hover {{
    background-color: {COLORS['bg_hover']};
    border-color: {COLORS['accent']};
}}
QTextEdit {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 8px;
    font-size: 12px;
    font-family: 'Consolas', 'Monaco', monospace;
}}
"""

RESIZE_GRIP_STYLE = """
QSizeGrip {
    background: transparent;
    width: 16px;
    height: 16px;
}
"""

CALENDAR_FILTER_BUTTON_STYLE = f"""
QPushButton {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text_secondary']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 12px;
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;
    min-width: 36px;
    min-height: 36px;
}}
QPushButton:hover {{
    background-color: {COLORS['bg_hover']};
    border-color: {COLORS['accent']};
    color: {COLORS['text_primary']};
}}
"""

PIN_BUTTON_STYLE = f"""
QPushButton {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text_muted']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 13px;
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;
    min-width: 36px;
    min-height: 36px;
}}
QPushButton:hover {{
    background-color: {COLORS['bg_hover']};
    border-color: {COLORS['accent']};
    color: {COLORS['text_primary']};
}}
"""

PIN_BUTTON_ACTIVE_STYLE = f"""
QPushButton {{
    background-color: {COLORS['accent']};
    color: white;
    border: 1px solid {COLORS['accent_light']};
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 13px;
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;
    min-width: 36px;
    min-height: 36px;
}}
QPushButton:hover {{
    background-color: {COLORS['accent_light']};
}}
"""
