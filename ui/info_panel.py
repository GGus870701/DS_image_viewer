"""
DS Image Viewer — 정보 패널 (QDockWidget)
EXIF 정보 테이블 및 GPS 정보 통합 제공
"""
import os
import webbrowser
import subprocess
from PySide6.QtWidgets import (QDockWidget, QWidget, QVBoxLayout, QTableWidget,
                                QTableWidgetItem, QHeaderView, QPushButton,
                                QLabel, QFrame, QHBoxLayout, QInputDialog, QLineEdit, QMessageBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
from core.exif import get_exif_data, get_gps_coordinates, format_exif_display
from ui.fonts import UI_FONT_NAME


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
        
        self._init_ui()

    def _init_ui(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. EXIF 테이블
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["항목", "내용"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 100)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        
        # 테이블 스타일 및 헤더 설정
        self.table.setStyleSheet(f"QTableWidget {{ background-color: #1e272e; border: none; font-family: '{UI_FONT_NAME}'; font-size: 13px; }}")
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.table.horizontalHeader().setFont(QFont(UI_FONT_NAME, 10, QFont.Bold))
        
        # 행 높이 기본값 설정
        self.table.verticalHeader().setDefaultSectionSize(35)
        self.table.itemDoubleClicked.connect(self._on_item_double_clicked)
        
        layout.addWidget(self.table)
        self.setWidget(container)
        
        # 상태 변수
        self._current_path = None

    def set_image(self, path):
        """이미지 로드 시 EXIF 추출 및 업데이트"""
        self._current_path = path # 현재 경로 저장
        if not path:
            self.table.setRowCount(0)
            return

        exif = get_exif_data(path)
        formatted = format_exif_display(exif)
        
        # GPS 정보 추출
        coords = get_gps_coordinates(exif)
        
        # 0. 파일 정보 추가 (최상단)
        file_info = [
            ("파일명", os.path.basename(path)),
            ("파일 경로", path)
        ]
        all_data = file_info + formatted
        
        # GPS 정보가 있으면 하단에 추가
        if coords:
            all_data.append(("위도", f"{coords[0]:.6f}"))
            all_data.append(("경도", f"{coords[1]:.6f}"))
        
        # 테이블 업데이트
        self.table.setRowCount(len(all_data))
        for i, (k, v) in enumerate(all_data):
            key_item = QTableWidgetItem(k)
            val_item = QTableWidgetItem(f"  {v}")
            
            # 정렬 설정
            key_item.setTextAlignment(Qt.AlignCenter)
            val_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            
            # 상호작용 가능한 항목 스타일링
            if k in ["파일명", "파일 경로"]:
                # 일반 아이템 대신 스타일링이 자유로운 QLabel 위젯 사용
                label = QLabel(f"  {v}")
                label.setObjectName("InteractiveCell")
                label.setToolTip(f"{v}\n▶ 더블 클릭하여 {'파일명 변경' if k == '파일명' else '폴더 열기'}")
                label.setStyleSheet(f"""
                    QLabel#InteractiveCell {{
                        color: #00B4D8;
                        background-color: transparent;
                        padding-left: 2px;
                        font-family: '{UI_FONT_NAME}';
                        font-size: 13px;
                    }}
                    QLabel#InteractiveCell:hover {{
                        color: #ffffff;
                        background-color: #2f3542;
                        padding-left: 10px;  /* 패딩이 늘어나는 효과 */
                    }}
                """)
                # 위젯 삽입 (클릭 이벤트를 위해 빈 아이템도 함께 생성)
                self.table.setItem(i, 0, key_item)
                self.table.setItem(i, 1, QTableWidgetItem("")) # 데이터는 비우고 위젯으로 대체
                self.table.setCellWidget(i, 1, label)
            else:
                val_item.setToolTip(v)
                self.table.setItem(i, 0, key_item)
                self.table.setItem(i, 1, val_item)

        # 메인 윈도우에 GPS 정보 유무 알림
        self.gps_detected.emit(coords)

    def _on_item_double_clicked(self, item):
        """파일명/경로 클릭 시 동작 처리"""
        row = item.row()
        key_item = self.table.item(row, 0)
        if not key_item: return
        key = key_item.text()
        
        # 위젯이 있는 경우 위젯의 텍스트를 가져옴
        widget = self.table.cellWidget(row, 1)
        if isinstance(widget, QLabel):
            val = widget.text().strip()
        else:
            val_item = self.table.item(row, 1)
            val = val_item.text().strip() if val_item else ""

        if key == "파일명":
            self._rename_file(val)
        elif key == "파일 경로":
            self._open_explorer(val)

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
                self.set_image(new_path) # UI 갱신
            except Exception as e:
                QMessageBox.critical(self, "오류", f"파일명을 변경할 수 없습니다:\n{e}")

    def _open_explorer(self, file_path):
        if os.path.exists(file_path):
            # 파일이 선택된 상태로 탐색기 열기
            subprocess.run(f'explorer /select,"{os.path.normpath(file_path)}"')
