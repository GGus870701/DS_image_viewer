"""
DS Image Viewer — SVG 인라인 아이콘 데이터
DS_cad_viewer ui/icon_data.py 패턴 완전 채택.

- DS_cad_viewer 공유 아이콘: open, rotate, zoom_extents(→fit), zoom_window, layers, bg_toggle, settings
- DS Image Viewer 전용 추가 아이콘 (동일 톤앤매너 24×24):
  split_view, flip_h, gps_pin, info_circle, nav_prev, nav_next, zoom_in, zoom_out, image_editor
"""
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QByteArray, QSize, Qt

# stroke 색상: #A0B0C5 (DS 그룹웨어 공통)
SVG_ICONS = {
    # ──────────────────────────────────────────────
    # DS_cad_viewer 공유 아이콘 (그대로 차용)
    # ──────────────────────────────────────────────
    "open": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M3 7V17C3 18.1046 3.89543 19 5 19H19C20.1046 19 21 18.1046 21 17V9C21 7.89543 20.1046 7 19 7H13L11 5H5C3.89543 5 3 5.89543 3 7Z" stroke="#A0B0C5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>""",

    "rotate": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C14.7614 3 17.2101 4.24841 18.8418 6.21638" stroke="#A0B0C5" stroke-width="2" stroke-linecap="round"/>
<path d="M19 2V6H15" stroke="#A0B0C5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>""",

    "rotate_ccw": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M3 12C3 16.9706 7.02944 21 12 21C16.9706 21 21 16.9706 21 12C21 7.02944 16.9706 3 12 3C9.23858 3 6.78992 4.24841 5.15822 6.21638" stroke="#A0B0C5" stroke-width="2" stroke-linecap="round"/>
<path d="M5 2V6H9" stroke="#A0B0C5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>""",

    "fit": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M15 3H19C20.1046 3 21 3.89543 21 5V9" stroke="#A0B0C5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M9 3H5C3.89543 3 3 3.89543 3 5V9" stroke="#A0B0C5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M15 21H19C20.1046 21 21 20.1046 21 19V15" stroke="#A0B0C5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M9 21H5C3.89543 21 3 20.1046 3 19V15" stroke="#A0B0C5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>""",

    "zoom_in": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<circle cx="11" cy="11" r="8" stroke="#A0B0C5" stroke-width="2"/>
<path d="M21 21L16.65 16.65" stroke="#A0B0C5" stroke-width="2" stroke-linecap="round"/>
<path d="M11 8V14M8 11H14" stroke="#A0B0C5" stroke-width="2" stroke-linecap="round"/>
</svg>""",

    "zoom_out": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<circle cx="11" cy="11" r="8" stroke="#A0B0C5" stroke-width="2"/>
<path d="M21 21L16.65 16.65" stroke="#A0B0C5" stroke-width="2" stroke-linecap="round"/>
<path d="M8 11H14" stroke="#A0B0C5" stroke-width="2" stroke-linecap="round"/>
</svg>""",

    "settings": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<circle cx="12" cy="12" r="3" stroke="#A0B0C5" stroke-width="2"/>
<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" stroke="#A0B0C5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>""",

    # ──────────────────────────────────────────────
    # DS Image Viewer 전용 아이콘
    # ──────────────────────────────────────────────
    "split_view": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<rect x="2" y="3" width="20" height="18" rx="2" stroke="#A0B0C5" stroke-width="2"/>
<path d="M12 3V21" stroke="#A0B0C5" stroke-width="2" stroke-linecap="round"/>
</svg>""",

    "flip_h": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M2 5L11 12L2 19Z" stroke="#A0B0C5" stroke-width="1.8" stroke-linejoin="round"/>
<path d="M22 5L13 12L22 19Z" stroke="#A0B0C5" stroke-width="1.8" stroke-linejoin="round"/>
<path d="M12 4V20" stroke="#A0B0C5" stroke-width="1.5" stroke-linecap="round" stroke-dasharray="2 2"/>
</svg>""",

    "gps_pin": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M12 2C8.13401 2 5 5.13401 5 9C5 14.25 12 22 12 22C12 22 19 14.25 19 9C19 5.13401 15.866 2 12 2Z" stroke="#A0B0C5" stroke-width="2" stroke-linejoin="round"/>
<circle cx="12" cy="9" r="2.5" stroke="#A0B0C5" stroke-width="2"/>
</svg>""",

    "info_circle": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<circle cx="12" cy="12" r="9" stroke="#A0B0C5" stroke-width="2"/>
<path d="M12 8V8.5" stroke="#A0B0C5" stroke-width="2.5" stroke-linecap="round"/>
<path d="M12 11.5V16" stroke="#A0B0C5" stroke-width="2" stroke-linecap="round"/>
</svg>""",

    "nav_prev": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M15 18L9 12L15 6" stroke="#A0B0C5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>""",

    "nav_next": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M9 18L15 12L9 6" stroke="#A0B0C5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>""",

    "image_editor": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M12 20H21" stroke="#A0B0C5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" stroke="#A0B0C5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>""",

    "close_file": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M18 6L6 18M6 6L18 18" stroke="#A0B0C5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>""",

    "folder_open": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M20 20H4C2.89543 20 2 19.1046 2 18V6C2 4.89543 2.89543 4 4 4H9L11 6H20C21.1046 6 22 6.89543 22 8V18C22 19.1046 21.1046 20 20 20Z" stroke="#A0B0C5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M12 10L16 14M16 14L12 18M16 14H8" stroke="#A0B0C5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>""",

    "batch_convert": """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M4 14V6C4 4.89543 4.89543 4 6 4H14" stroke="#A0B0C5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
<rect x="8" y="8" width="12" height="12" rx="2" stroke="#A0B0C5" stroke-width="2"/>
<path d="M12 14L14 16L16 14" stroke="#A0B0C5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M14 10V16" stroke="#A0B0C5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>""",
}


def get_qicon(name: str, size: int = 32) -> QIcon:
    """SVG 데이터를 QIcon으로 변환 (파일 경로 의존성 없음)"""
    svg_data = SVG_ICONS.get(name)
    if not svg_data:
        return QIcon()

    renderer = QSvgRenderer(QByteArray(svg_data.encode('utf-8')))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    return QIcon(pixmap)
