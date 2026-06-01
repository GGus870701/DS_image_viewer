from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                QPushButton, QGroupBox, QMessageBox, QCheckBox)
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import Qt
import os
import sys
from core.registry_mgr import (register_context_menu, unregister_context_menu, is_context_menu_registered,
                               register_default_program, unregister_default_program, is_default_program_registered)
from core.settings import settings

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("환경설정 (Settings)")
        self.resize(450, 420)
        self._init_ui()
        self._update_ui_state()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        
        # 1. 이미지 탐색 단축키 설정
        group_nav = QGroupBox("이미지 탐색 단축키 설정")
        layout_nav = QVBoxLayout(group_nav)
        
        lbl_nav_desc = QLabel("이전/다음 이미지로 넘길 때 사용할 방식을 선택합니다.")
        lbl_nav_desc.setStyleSheet("color: #AAAAAA;")
        layout_nav.addWidget(lbl_nav_desc)
        
        nav_shortcuts = settings.get("nav_shortcuts", {"arrow_keys": True, "mouse_wheel": True})
        
        self.chk_arrow_keys = QCheckBox("키보드 화살표 키 (←, →)")
        self.chk_arrow_keys.setChecked(nav_shortcuts.get("arrow_keys", True))
        self.chk_arrow_keys.toggled.connect(self._on_nav_shortcut_changed)
        layout_nav.addWidget(self.chk_arrow_keys)
        
        self.chk_mouse_wheel = QCheckBox("마우스 휠 (위/아래)")
        self.chk_mouse_wheel.setChecked(nav_shortcuts.get("mouse_wheel", True))
        self.chk_mouse_wheel.toggled.connect(self._on_nav_shortcut_changed)
        layout_nav.addWidget(self.chk_mouse_wheel)
        
        main_layout.addWidget(group_nav)

        # 2. Windows 탐색기 연동 그룹
        group_explorer = QGroupBox("Windows 탐색기 연동")
        layout_explorer = QVBoxLayout(group_explorer)
        
        lbl_desc = QLabel("탐색기 우클릭 메뉴에 '이미지 크기 변환' 등의 기능을 추가합니다.")
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

        # 2. 기본 연결 프로그램 설정 그룹
        group_default = QGroupBox("기본 연결 프로그램 설정")
        layout_default = QVBoxLayout(group_default)
        
        lbl_desc_def = QLabel("JPG, PNG 등 이미지 파일을 열 때 사용할 수 있는 프로그램 목록에\nDS Image Viewer를 등록하거나 제거합니다.")
        lbl_desc_def.setStyleSheet("color: #AAAAAA;")
        layout_default.addWidget(lbl_desc_def)
        
        h_layout_def = QHBoxLayout()
        self.lbl_status_def = QLabel("현재 상태: 확인 중...")
        self.btn_toggle_default = QPushButton("프로그램 등록 / 해제")
        self.btn_toggle_default.clicked.connect(self._on_toggle_default)
        
        h_layout_def.addWidget(self.lbl_status_def)
        h_layout_def.addStretch()
        h_layout_def.addWidget(self.btn_toggle_default)
        layout_default.addLayout(h_layout_def)
        main_layout.addWidget(group_default)
        
        main_layout.addStretch()

        # 3. 로고 및 카피라이트 (하단 고정)
        copyright_layout = QHBoxLayout()
        copyright_layout.setContentsMargins(10, 10, 10, 10)
        
        # 로고
        self.lbl_logo = QLabel()
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            logo_path = os.path.join(sys._MEIPASS, "DASAN_logo.png")
        else:
            logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                     "build_core", "assets", "DASAN_logo.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            if not pix.isNull():
                self.lbl_logo.setPixmap(pix.scaled(35, 35, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        copyright_layout.addWidget(self.lbl_logo)
        
        # 텍스트
        v_text_layout = QVBoxLayout()
        lbl_copy1 = QLabel("© 2026 DASAN Technology Safety")
        lbl_copy1.setStyleSheet("color: #95a5a6; font-weight: bold; font-size: 11px;")
        lbl_copy2 = QLabel("All Rights Reserved.")
        lbl_copy2.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        v_text_layout.addWidget(lbl_copy1)
        v_text_layout.addWidget(lbl_copy2)
        v_text_layout.setSpacing(2)
        
        copyright_layout.addLayout(v_text_layout)
        copyright_layout.addStretch()
        
        # 하단 닫기 버튼
        btn_close = QPushButton("닫기")
        btn_close.setFixedWidth(80)
        btn_close.clicked.connect(self.close)
        copyright_layout.addWidget(btn_close)
        
        main_layout.addLayout(copyright_layout)

    def _update_ui_state(self):
        # 스타일 정의
        red_style = "background-color: #c0392b; color: white; border-radius: 4px; padding: 5px 12px; font-weight: bold;"
        blue_style = "background-color: #0984e3; color: white; border-radius: 4px; padding: 5px 12px; font-weight: bold;"

        # 1. 우클릭 메뉴 상태
        is_reg = is_context_menu_registered()
        if is_reg:
            self.lbl_status.setText("현재 상태: <b><font color='#4CAF50'>등록됨</font></b>")
            self.btn_toggle_registry.setText("우클릭 메뉴 해제")
            self.btn_toggle_registry.setStyleSheet(red_style)
        else:
            self.lbl_status.setText("현재 상태: <b><font color='#F44336'>해제됨</font></b>")
            self.btn_toggle_registry.setText("우클릭 메뉴 등록")
            self.btn_toggle_registry.setStyleSheet(blue_style)
        self.is_registered = is_reg

        # 2. 기본 프로그램 상태
        is_def = is_default_program_registered()
        if is_def:
            self.lbl_status_def.setText("현재 상태: <b><font color='#4CAF50'>등록됨</font></b>")
            self.btn_toggle_default.setText("등록 정보 삭제")
            self.btn_toggle_default.setStyleSheet(red_style)
        else:
            self.lbl_status_def.setText("현재 상태: <b><font color='#F44336'>해제됨</font></b>")
            self.btn_toggle_default.setText("프로그램 등록")
            self.btn_toggle_default.setStyleSheet(blue_style)
        self.is_default_reg = is_def

    def _on_toggle_registry(self):
        if self.is_registered:
            ok, msg = unregister_context_menu()
            if ok: QMessageBox.information(self, "성공", "탐색기 우클릭 메뉴에서 제거되었습니다.")
        else:
            ok, msg = register_context_menu()
            if ok: QMessageBox.information(self, "성공", "탐색기 우클릭 메뉴에 등록되었습니다.")
        self._update_ui_state()

    def _on_toggle_default(self):
        if self.is_default_reg:
            ok, msg = unregister_default_program()
            if ok: QMessageBox.information(self, "성공", msg)
        else:
            ok, msg = register_default_program()
            if ok: 
                QMessageBox.information(self, "성공", 
                    msg + "\n\n이제 윈도우 설정의 '기본 앱' 또는 파일 우클릭 > '연결 프로그램'에서\nDS Image Viewer를 선택할 수 있습니다.")
        self._update_ui_state()

    def _on_nav_shortcut_changed(self):
        nav_shortcuts = {
            "arrow_keys": self.chk_arrow_keys.isChecked(),
            "mouse_wheel": self.chk_mouse_wheel.isChecked()
        }
        settings.set("nav_shortcuts", nav_shortcuts)
