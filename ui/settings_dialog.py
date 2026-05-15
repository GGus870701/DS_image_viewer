from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                QPushButton, QGroupBox, QMessageBox)
from PySide6.QtCore import Qt
from core.registry_mgr import register_context_menu, unregister_context_menu, is_context_menu_registered

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("환경설정 (Settings)")
        self.resize(400, 200)
        self._init_ui()
        self._update_ui_state()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Windows 탐색기 연동 그룹
        group_explorer = QGroupBox("Windows 탐색기 연동")
        layout_explorer = QVBoxLayout(group_explorer)
        
        lbl_desc = QLabel("Windows 탐색기 우클릭 메뉴에 'DS Image Viewer' 상위 메뉴와\n'이미지 크기 변환', '이미지 편집기' 하위 메뉴를 추가합니다.")
        lbl_desc.setStyleSheet("color: #AAAAAA;")
        layout_explorer.addWidget(lbl_desc)
        
        h_layout = QHBoxLayout()
        self.lbl_status = QLabel("현재 상태: 확인 중...")
        self.btn_toggle_registry = QPushButton("메뉴 등록 / 해제")
        self.btn_toggle_registry.clicked.connect(self._on_toggle_registry)
        
        h_layout.addWidget(self.lbl_status)
        h_layout.addStretch()
        h_layout.addWidget(self.btn_toggle_registry)
        layout_explorer.addLayout(h_layout)
        
        main_layout.addWidget(group_explorer)
        main_layout.addStretch()
        
        # 하단 닫기 버튼
        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.close)
        
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        bottom_layout.addWidget(btn_close)
        main_layout.addLayout(bottom_layout)

    def _update_ui_state(self):
        is_reg = is_context_menu_registered()
        
        red_btn_style = """
            QPushButton {
                background-color: #c0392b;
                color: #ffffff;
                border: 1px solid #a93226;
                border-radius: 4px;
                padding: 5px 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #e74c3c; }
            QPushButton:pressed { background-color: #922b21; }
        """
        
        blue_btn_style = """
            QPushButton {
                background-color: #0984e3;
                color: #ffffff;
                border: 1px solid #074b83;
                border-radius: 4px;
                padding: 5px 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #0fbcf9; }
            QPushButton:pressed { background-color: #0652dd; }
        """

        if is_reg:
            self.lbl_status.setText("현재 상태: <b><font color='#4CAF50'>등록됨 (사용 중)</font></b>")
            self.btn_toggle_registry.setText("우클릭 메뉴 해제하기")
            self.btn_toggle_registry.setStyleSheet(red_btn_style)
        else:
            self.lbl_status.setText("현재 상태: <b><font color='#F44336'>해제됨 (미사용)</font></b>")
            self.btn_toggle_registry.setText("우클릭 메뉴 등록하기")
            self.btn_toggle_registry.setStyleSheet(blue_btn_style)
            
        self.is_registered = is_reg

    def _on_toggle_registry(self):
        if self.is_registered:
            ok, msg = unregister_context_menu()
            if ok:
                QMessageBox.information(self, "성공", "Windows 탐색기 우클릭 메뉴에서 성공적으로 제거되었습니다.")
            else:
                QMessageBox.warning(self, "오류", msg)
        else:
            ok, msg = register_context_menu()
            if ok:
                QMessageBox.information(self, "성공", "Windows 탐색기 우클릭 메뉴에 성공적으로 추가되었습니다.\n이제 이미지 파일 우클릭 시 'DS뷰어로 변환' 메뉴를 사용할 수 있습니다.")
            else:
                QMessageBox.warning(self, "오류", msg)
                
        self._update_ui_state()
