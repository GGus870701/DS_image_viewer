"""
DS Image Viewer — 라이센스 오류 다이얼로그
DS_cad_viewer license/license_dialog.py 패턴 채택
"""
import sys
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton,
                               QApplication, QMessageBox)
from PySide6.QtCore import Qt

from ui.fonts import UI_FONT_TITLE, UI_FONT_SMALL, UI_FONT_NAV_S, UI_FONT_BOLD


class LicenseDialog(QDialog):
    def __init__(self, hwid: str, message: str):
        super().__init__()
        self.hwid = hwid
        self.message = message
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("라이센스 인증 필요")
        self.setFixedSize(460, 290)
        self.setStyleSheet("background-color: #1e272e; color: white;")

        layout = QVBoxLayout()
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(8)

        # 타이틀
        title = QLabel("라이센스 인증이 필요합니다.")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(UI_FONT_TITLE)
        title.setStyleSheet("color: #ff4757;")
        layout.addWidget(title)

        # 안내 메시지
        msg = QLabel(self.message)
        msg.setAlignment(Qt.AlignCenter)
        msg.setFont(UI_FONT_SMALL)
        msg.setWordWrap(True)
        msg.setStyleSheet("color: #A0B0C5; margin-top: 6px;")
        layout.addWidget(msg)

        layout.addStretch()

        # HWID 표시
        hwid_lbl = QLabel("기기 고유 ID:")
        hwid_lbl.setAlignment(Qt.AlignCenter)
        hwid_lbl.setFont(UI_FONT_SMALL)
        hwid_lbl.setStyleSheet("color: #a4b0be;")
        layout.addWidget(hwid_lbl)

        self.hwid_value = QLabel(self.hwid)
        self.hwid_value.setAlignment(Qt.AlignCenter)
        self.hwid_value.setFont(UI_FONT_NAV_S)
        self.hwid_value.setStyleSheet("color: #00d2d3; letter-spacing: 2px;")
        layout.addWidget(self.hwid_value)

        layout.addStretch()

        # 복사 버튼
        copy_btn = QPushButton("기기 ID 복사하기")
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.setFont(UI_FONT_BOLD)
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #4b6584;
                border: none;
                border-radius: 4px;
                padding: 10px;
                color: white;
            }
            QPushButton:hover { background-color: #778ca3; }
            QPushButton:pressed { background-color: #3a5068; }
        """)
        copy_btn.clicked.connect(self._copy_id)
        layout.addWidget(copy_btn)

        # 안내 문구
        footer = QLabel("관리자에게 문의하여 라이센스를 발급받으세요.")
        footer.setAlignment(Qt.AlignCenter)
        footer.setFont(UI_FONT_SMALL)
        footer.setStyleSheet("color: #57606f; margin-top: 6px;")
        layout.addWidget(footer)

        self.setLayout(layout)

    def _copy_id(self):
        QApplication.clipboard().setText(self.hwid)
        QMessageBox.information(self, "복사 완료",
                                "기기 ID가 클립보드에 복사되었습니다.\n관리자에게 전달해 주세요.")


def show_license_error(hwid: str, message: str):
    """라이센스 오류 다이얼로그를 표시하고 프로그램 종료"""
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    dlg = LicenseDialog(hwid, message)
    dlg.exec()
    sys.exit(0)
