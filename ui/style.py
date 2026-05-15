"""
DS Image Viewer — QSS 다크 테마
DS_cad_viewer 색상 팔레트 완전 채택 (그룹웨어 통일)
"""
from ui.fonts import UI_FONT_NAME


def get_stylesheet() -> str:
    return f"""
    QMainWindow {{
        background-color: #1e272e;
    }}
    QToolTip {{
        background-color: #2f3542;
        color: white;
        border: 1px solid #3d3d3d;
        font-family: '{UI_FONT_NAME}';
        font-size: 13px;
        padding: 4px;
    }}
    QToolBar {{
        background-color: #2f3640;
        border-bottom: 1px solid #3d3d3d;
        spacing: 5px;
        padding: 5px;
    }}
    QToolBar::separator {{
        background-color: #d2dae2;
        width: 1px;
        margin-top: 4px;
        margin-bottom: 4px;
        margin-left: 2px;
        margin-right: 2px;
    }}
    QToolButton {{
        background-color: transparent;
        border-radius: 4px;
        padding: 4px;
        color: #ffffff;
    }}
    QToolButton:hover {{
        background-color: #485460;
    }}
    QToolButton:checked {{
        background-color: #0fbcf9;
    }}
    QStatusBar {{
        background-color: #1e272e;
        color: #d2dae2;
        font-family: '{UI_FONT_NAME}';
        font-size: 14px;
        font-weight: bold;
        border-top: 1px solid #3d3d3d;
    }}
    QStatusBar::item {{
        border: none;
    }}
    QLabel {{
        color: #d2dae2;
        font-family: '{UI_FONT_NAME}';
        font-size: 13px;
    }}
    QComboBox QAbstractItemView {{
        background-color: #2f3542;
        color: #ffffff;
        selection-background-color: #57606f;
        outline: none;
        border: 1px solid #3d3d3d;
    }}
    
    /* EXIF 정보 패널 커스텀 */
    QDockWidget {{
        color: #ffffff;
        font-weight: bold;
        border: 1px solid #3d3d3d;
    }}
    QDockWidget::title {{
        background-color: #2f3640;
        padding: 8px;
        border-bottom: 1px solid #3d3d3d;
    }}
    QTableWidget {{
        background-color: #1e272e;
        alternate-background-color: #242c34;
        border: none;
        gridline-color: #2f3542;
        outline: none;
    }}
    QTableWidget::item {{
        color: #ced6e0;
    }}
    QTableWidget::item:selected {{
        background-color: #485460;
        color: #ffffff;
    }}
    QHeaderView::section {{
        background-color: #2f3640;
        color: #ffffff;
        border: none;
        padding: 4px;
        font-weight: bold;
    }}
    QGroupBox {{
        color: #d2dae2;
        font-family: '{UI_FONT_NAME}';
        font-size: 13px;
        font-weight: bold;
        border: 1px solid #3d3d3d;
        border-radius: 4px;
        margin-top: 12px;
        padding-top: 10px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 3px;
        color: #0fbcf9;
    }}
    QPushButton {{
        background-color: #2f3640;
        color: #d2dae2;
        border: 1px solid #3d3d3d;
        border-radius: 4px;
        padding: 5px 10px;
        font-family: '{UI_FONT_NAME}';
        font-size: 13px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background-color: #485460;
    }}
    QPushButton:pressed {{
        background-color: #0fbcf9;
        color: #ffffff;
    }}
    QPushButton:disabled {{
        background-color: #1e272e;
        color: #57606f;
        border: 1px solid #2f3542;
    }}
    QListWidget {{
        background-color: #2f3542;
        color: #d2dae2;
        border: 1px solid #3d3d3d;
        border-radius: 4px;
        outline: none;
        font-size: 13px;
    }}
    QListWidget::item:selected {{
        background-color: #0fbcf9;
        color: #ffffff;
    }}
    QComboBox, QSpinBox, QLineEdit {{
        background-color: #2f3542;
        color: #ffffff;
        border: 1px solid #3d3d3d;
        border-radius: 4px;
        padding: 0px 4px;
        min-height: 22px;
        font-family: '{UI_FONT_NAME}';
        font-size: 13px;
    }}
    QComboBox QLineEdit {{
        background: transparent;
        border: none;
        padding: 0px;
        margin: 0px;
        color: #ffffff;
    }}
    QStatusBar::item {{
        border: none;
    }}
    QToolButton::menu-indicator {{
        image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHZpZXdCb3g9JzAgMCAyNCAyNCc+PHBhdGggZmlsbD0nI0EwQjBDNScgZD0nTTcgMTBsNSA1IDUtNXonLz48L3N2Zz4=");
        subcontrol-origin: padding;
        subcontrol-position: bottom right;
        right: 2px;
        bottom: 2px;
        width: 10px;
        height: 10px;
    }}
    QCheckBox, QRadioButton {{
        color: #d2dae2;
        font-family: '{UI_FONT_NAME}';
        font-size: 13px;
        spacing: 8px;
    }}
    QCheckBox::indicator, QRadioButton::indicator {{
        width: 18px;
        height: 18px;
        border: 1px solid #57606f;
        background-color: #2f3542;
    }}
    QCheckBox::indicator {{
        border-radius: 4px;
    }}
    QRadioButton::indicator {{
        border-radius: 9px;
    }}
    QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
        border: 1px solid #0fbcf9;
    }}
    QCheckBox::indicator:checked {{
        background-color: #ffffff;
        border: 1px solid #ffffff;
        image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHZpZXdCb3g9JzAgMCAyNCAyNCc+PHBhdGggZmlsbD0nYmxhY2snIGQ9J005IDE2LjE3TDQuODMgMTJsLTEuNDIgMS40MUw5IDE5IDIxIDdsLTEuNDEtMS40MUw5IDE2LjE3eicvPjwvc3ZnPg==");
    }}
    QRadioButton::indicator:checked {{
        background-color: #ffffff;
        border: 1px solid #ffffff;
        image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHZpZXdCb3g9JzAgMCAyNCAyNCc+PGNpcmNsZSBmaWxsPSdibGFjaycgY3g9JzEyJyBjeT0nMTInIHI9JzYnLz48L3N2Zz4=");
    }}
    QScrollArea {{
        border: none;
        background-color: transparent;
    }}
    QScrollArea > QWidget > QWidget {{
        background-color: transparent;
    }}
    """
