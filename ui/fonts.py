"""
DS Image Viewer — 전역 폰트 설정
DS_cad_viewer ui/fonts.py 패턴 완전 채택
"""
from PySide6.QtGui import QFont

# --- [전역 스타일 설정] ---
UI_FONT_NAME = "Malgun Gothic"


def get_font(size: int = 12, bold: bool = False) -> QFont:
    """지정된 크기와 굵기의 QFont 객체 반환"""
    font = QFont(UI_FONT_NAME, size)
    if bold:
        font.setBold(True)
    return font


UI_FONT_BOLD   = get_font(12, True)
UI_FONT_NORMAL = get_font(12, False)
UI_FONT_SMALL  = get_font(10, False)
UI_FONT_NAV_S  = get_font(18, True)
UI_FONT_NAV_L  = get_font(28, True)
UI_FONT_TITLE  = get_font(16, True)
