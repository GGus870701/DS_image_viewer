"""
DS Image Viewer — 정보 패널 (QDockWidget)
EXIF 정보 테이블 및 GPS 정보 통합 제공
"""
import os
import sys
import webbrowser
import subprocess
import time
from PySide6.QtWidgets import (QDockWidget, QWidget, QVBoxLayout, QScrollArea,
                                QLabel, QFrame, QHBoxLayout, QInputDialog, QLineEdit, QMessageBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
from PySide6.QtSvgWidgets import QSvgWidget
from core.exif import get_exif_data, get_gps_coordinates, format_exif_display
from ui.fonts import UI_FONT_NAME


class ClickableLabel(QLabel):
    clicked = Signal()
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class InfoPanel(QDockWidget):
    file_renamed = Signal(str, str)  # (old_path, new_path)
    gps_detected = Signal(object)    # (coords or None)

    def __init__(self, parent=None):
        super().__init__("이미지 정보", parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        # 제목 가운데 정렬을 위한 커스텀 레이블 설정
        title_label = QLabel("이미지 정보")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(f"""
            QLabel {{
                background-color: #2f3640;
                color: #FFFFFF;
                padding: 10px;
                font-family: '{UI_FONT_NAME}';
                font-weight: bold;
                border-bottom: 1px solid #3d3d3d;
                font-size: 14px;
            }}
        """)
        self.setTitleBarWidget(title_label)
        
        self.labels = {}
        self._current_path = None
        self._init_ui()

    def _init_ui(self):
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        self.container = QWidget()
        self.container.setStyleSheet("background-color: #2f3640;")
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(12)
        
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        icon_dir = os.path.join(base_path, "assets", "icons")
        
        self._create_card("파일 정보", os.path.join(icon_dir, "info_file.svg"), ["파일명", "촬영 일시", "수정 일시"])
        self._add_separator()
        self._create_card("파일 경로", os.path.join(icon_dir, "info_folder.svg"), ["파일 위치"])
        self._add_separator()
        self._create_card("크기 정보", os.path.join(icon_dir, "info_size.svg"), ["해상도", "파일 용량"])
        self._add_separator()
        self._create_card("위치 정보", os.path.join(icon_dir, "info_location.svg"), ["위도", "경도"])
        self._add_separator()
        self._create_card("장치 정보", os.path.join(icon_dir, "info_device.svg"), ["제조사", "모델", "조리개", "노출 시간", "ISO 감도", "초점 거리", "소프트웨어"])
        
        self.layout.addStretch()
        
        self.scroll_area.setWidget(self.container)
        self.setWidget(self.scroll_area)

    def _add_separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #3d3d3d; max-height: 1px; margin: 5px 15px;")
        self.layout.addWidget(line)

    def _create_card(self, title, icon_path, items):
        card = QFrame()
        card.setObjectName("InfoCard")
        card.setStyleSheet("""
            QFrame#InfoCard {
                background-color: transparent;
                border: none;
            }
        """)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(6)
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 8)
        
        icon_lbl = QSvgWidget(icon_path)
        icon_lbl.setFixedSize(16, 16)
        icon_lbl.setStyleSheet("background: transparent;")
        
        title_lbl = QLabel(title)
        title_lbl.setFont(QFont(UI_FONT_NAME, 11, QFont.Bold))
        title_lbl.setStyleSheet("color: #ffffff; background: transparent;")
        
        header_layout.addWidget(icon_lbl)
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        card_layout.addLayout(header_layout)
        
        # Items
        for key in items:
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(5, 0, 0, 0)
            
            key_lbl = QLabel(key)
            key_lbl.setFixedWidth(75)
            key_lbl.setFont(QFont(UI_FONT_NAME, 10))
            key_lbl.setStyleSheet("color: #a4b0be; background: transparent;")
            
            # Interactive items (파일명, 파일 위치)
            if key in ["파일명", "파일 위치"]:
                val_lbl = ClickableLabel("-")
                val_lbl.setWordWrap(True)
                val_lbl.setCursor(Qt.PointingHandCursor)
                val_lbl.setFont(QFont(UI_FONT_NAME, 11, QFont.Bold if key == "파일명" else QFont.Normal))
                val_lbl.setStyleSheet(f"""
                    QLabel {{
                        color: #00d2d3;
                        background: transparent;
                    }}
                    QLabel:hover {{
                        color: #ffffff;
                        text-decoration: underline;
                    }}
                """)
                if key == "파일명":
                    val_lbl.clicked.connect(self._on_filename_clicked)
                else:
                    val_lbl.clicked.connect(self._on_filepath_clicked)
            else:
                val_lbl = QLabel("-")
                val_lbl.setWordWrap(True)
                val_lbl.setFont(QFont(UI_FONT_NAME, 10))
                val_lbl.setStyleSheet("color: #ffffff; background: transparent;")
                
            row_layout.addWidget(key_lbl)
            row_layout.addWidget(val_lbl, 1)
            
            self.labels[key] = val_lbl
            card_layout.addLayout(row_layout)
            
        self.layout.addWidget(card)

    def set_image(self, path):
        self._current_path = path
        if not path:
            for lbl in self.labels.values(): lbl.setText("-")
            return

        exif = get_exif_data(path)
        formatted = format_exif_display(exif)
        coords = get_gps_coordinates(exif)

        # File stats
        try:
            stats = os.stat(path)
            mtime = time.ctime(stats.st_mtime)
            size_bytes = stats.st_size
            size_str = ""
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size_bytes < 1024:
                    size_str = f"{size_bytes:.1f} {unit}"
                    break
                size_bytes /= 1024
            else: size_str = f"{size_bytes:.1f} TB"
        except:
            mtime, size_str = "-", "-"

        # Resolution
        from PIL import Image
        res = "-"
        try:
            with Image.open(path) as img:
                res = f"{img.size[0]} x {img.size[1]}"
        except: pass
        
        exif_dict = {k: v for k, v in formatted}
        
        data = {
            "파일명": os.path.basename(path),
            "수정 일시": mtime,
            "해상도": res,
            "파일 용량": size_str,
            "제조사": exif_dict.get("제조사", "-"),
            "모델": exif_dict.get("모델", "-"),
            "촬영 일시": exif_dict.get("촬영 일시", "-"),
            "노출 시간": exif_dict.get("노출 시간", "-"),
            "조리개": exif_dict.get("조리개 (F)", "-"),
            "ISO 감도": exif_dict.get("ISO 감도", "-"),
            "초점 거리": exif_dict.get("초점 거리", "-"),
            "소프트웨어": exif_dict.get("소프트웨어", "-"),
            "위도": f"{coords[0]:.6f}" if coords else "-",
            "경도": f"{coords[1]:.6f}" if coords else "-",
            "파일 위치": path
        }
        
        for k, v in data.items():
            if k in self.labels:
                self.labels[k].setText(v)
                
        self.gps_detected.emit(coords)

    def _on_filename_clicked(self):
        if self._current_path:
            self._rename_file(os.path.basename(self._current_path))
            
    def _on_filepath_clicked(self):
        if self._current_path:
            self._open_explorer(self._current_path)

    def _rename_file(self, current_name):
        if not self._current_path: return
        
        dir_path = os.path.dirname(self._current_path)
        base_name, ext = os.path.splitext(current_name)
        
        new_name, ok = QInputDialog.getText(self, "파일명 변경", "새 파일명:", QLineEdit.Normal, base_name)
        if ok and new_name and new_name != base_name:
            new_path = os.path.join(dir_path, new_name + ext)
            try:
                os.rename(self._current_path, new_path)
                old_path = self._current_path
                self._current_path = new_path
                self.file_renamed.emit(old_path, new_path)
                self.set_image(new_path)
            except Exception as e:
                QMessageBox.critical(self, "오류", f"파일명을 변경할 수 없습니다:\n{e}")

    def _open_explorer(self, file_path):
        if os.path.exists(file_path):
            subprocess.run(f'explorer /select,"{os.path.normpath(file_path)}"')
