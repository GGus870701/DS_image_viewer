"""
DS Image Viewer — 메인 윈도우
Phase 2: 파일 열기 + ImageViewport + 기본 툴바/상태바 연결
Phase 3~5에서 분할 뷰, 네비게이터, INFO 패널 추가 예정
"""
import os
import subprocess
import webbrowser

from PySide6.QtWidgets import (QMainWindow, QFileDialog, QToolBar, QStatusBar,
                                QLabel, QWidget, QSizePolicy, QMenu, QMessageBox,
                                QToolButton, QStackedWidget, QComboBox, QHBoxLayout)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtCore import Qt, QSize, QTimer, QRectF

from core.version import BUILD_VERSION
from core.settings import settings
from core.image_model import ImageModel, SUPPORTED_EXTS
from ui.image_viewport import ImageViewport
from ui.split_view import SplitView
from ui.navigator import NavigatorWidget
from ui.info_panel import InfoPanel
from ui.style import get_stylesheet
from ui.icon_data import get_qicon
from ui.fonts import UI_FONT_NAME
from ui.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    def __init__(self, license_data: dict, initial_file: str = None):
        super().__init__()
        self.license_data = license_data
        self._model = ImageModel(self)

        user = license_data.get('user_name', 'User')
        ver = '.'.join(BUILD_VERSION.split('.')[:2])
        self.setWindowTitle(f"DS Image Viewer v{ver} - [{user}]")
        self.resize(1280, 800)
        self.setStyleSheet(get_stylesheet())
        self.setAcceptDrops(True)

        # 윈도우 아이콘 설정 (Taskbar 및 Window Title)
        ico_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "ds_viewer.ico")
        if os.path.exists(ico_path):
            self.setWindowIcon(QIcon(ico_path))

        self._init_ui()
        self._connect_signals()

        if initial_file:
            QTimer.singleShot(100, lambda: self._load_file(initial_file))

    # ──────────────────────────────────────────────
    # UI 초기화
    # ──────────────────────────────────────────────
    def _init_ui(self):
        # 중앙 스택 위젯 (단일 뷰 <-> 분할 뷰)
        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._viewport = ImageViewport(self)
        self._stack.addWidget(self._viewport)

        self._split_view = SplitView(self)
        self._stack.addWidget(self._split_view)

        # 네비게이터 오버레이
        self._nav = NavigatorWidget(self)

        # 정보 패널 (Dock)
        self._info_panel = InfoPanel(self)
        self._info_panel.setMinimumWidth(330)  # 너비 330px로 조정
        self._info_panel.file_renamed.connect(self._on_file_renamed)
        self._info_panel.gps_detected.connect(self._on_gps_detected)
        self.addDockWidget(Qt.RightDockWidgetArea, self._info_panel)
        self._info_panel.hide() # 기본 숨김

        # 툴바
        self._create_toolbar()

        # 상태바
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.setSizeGripEnabled(False)
        self._status.setStyleSheet(f"font-family: '{UI_FONT_NAME}'; font-size: 12px; color: #A0B0C5; border-top: 1px solid #1A2A44;")

        # 상태바 위젯 구성
        # 1. 좌측: 파일 정보 (아이콘 + 텍스트)
        self._file_container = QWidget()
        file_layout = QHBoxLayout(self._file_container)
        file_layout.setContentsMargins(5, 0, 5, 0)
        file_layout.setSpacing(5)
        
        self._icon_file = QLabel()
        self._icon_file.setPixmap(get_qicon("open").pixmap(16, 16))
        self._lbl_file = QLabel(" 대기 중... ")
        self._lbl_file.setStyleSheet("border: none; background: transparent;")
        
        file_layout.addWidget(self._icon_file)
        file_layout.addWidget(self._lbl_file)
        file_layout.addStretch() # 오른쪽으로 밀어내기
        
        # 2. 중앙: 해상도 및 용량 (아이콘 + 텍스트)
        self._size_container = QWidget()
        size_layout = QHBoxLayout(self._size_container)
        size_layout.setContentsMargins(5, 0, 5, 0)
        size_layout.setSpacing(5)
        
        self._icon_size = QLabel()
        self._icon_size.setPixmap(get_qicon("fit").pixmap(16, 16))
        self._lbl_size = QLabel("")
        self._lbl_size.setStyleSheet("border: none; background: transparent;")
        
        size_layout.addWidget(self._icon_size)
        size_layout.addWidget(self._lbl_size)
        size_layout.addStretch() # 오른쪽으로 밀어내기
        
        # 3. 우측: 줌 배율 (드롭다운)
        self._zoom_combo = QComboBox()
        self._zoom_combo.setEditable(True)
        self._zoom_combo.addItems(["10%", "25%", "50%", "75%", "100%", "125%", "150%", "200%", "300%", "400%", "500%"])
        self._zoom_combo.setCurrentText("100%")
        self._zoom_combo.setFixedWidth(90)
        self._zoom_combo.setFixedHeight(26) # 상태바 높이에 맞춰 축소
        self._zoom_combo.currentTextChanged.connect(self._on_zoom_combo_changed)
        
        self._status.addWidget(self._file_container, 2)
        self._status.addWidget(self._size_container, 1)
        self._status.addPermanentWidget(self._zoom_combo)

    def _create_toolbar(self):
        tb = QToolBar("Main Toolbar")
        tb.setMovable(False)
        tb.setIconSize(QSize(28, 28))
        tb.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.addToolBar(tb)
        self._toolbar = tb

        # ── 파일 열기 (최근 파일 메뉴 포함) ──
        self._open_btn = QToolButton()
        self._open_btn.setIcon(get_qicon("open"))
        self._open_btn.setToolTip("파일 열기 (최근 파일)")
        self._open_btn.setPopupMode(QToolButton.MenuButtonPopup)
        self._open_btn.clicked.connect(self._open_file_dialog)
        self._open_menu = QMenu(self)
        self._open_btn.setMenu(self._open_menu)
        self._update_recent_menu()
        tb.addWidget(self._open_btn)
        tb.addSeparator()

        # ── 보기 ──
        self._fit_act = QAction(get_qicon("fit"), "화면 맞춤 (F)", self)
        self._fit_act.setStatusTip("이미지를 화면에 맞춥니다.")
        self._fit_act.setShortcut(Qt.Key_F)
        self._fit_act.triggered.connect(self._on_fit_clicked)
        tb.addAction(self._fit_act)

        self._zoom_in_act = QAction(get_qicon("zoom_in"), "확대", self)
        self._zoom_in_act.setStatusTip("이미지를 확대합니다.")
        self._zoom_in_act.setShortcut(QKeySequence(Qt.Key_Equal))
        self._zoom_in_act.triggered.connect(lambda: self._zoom_step(1))
        tb.addAction(self._zoom_in_act)

        self._zoom_out_act = QAction(get_qicon("zoom_out"), "축소", self)
        self._zoom_out_act.setStatusTip("이미지를 축소합니다.")
        self._zoom_out_act.setShortcut(Qt.Key_Minus)
        self._zoom_out_act.triggered.connect(lambda: self._zoom_step(-1))
        tb.addAction(self._zoom_out_act)
        tb.addSeparator()

        # ── 화면 분할 ──
        self._split_act = QAction(get_qicon("split_view"), "화면 분할 (S)", self)
        self._split_act.setCheckable(True)
        self._split_act.setShortcut(Qt.Key_S)
        self._split_act.triggered.connect(self._toggle_split_view)
        tb.addAction(self._split_act)
        tb.addSeparator()

        # ── 변환 ──
        self._rotate_ccw_act = QAction(get_qicon("rotate_ccw"), "반시계 회전 (E)", self)
        self._rotate_ccw_act.setStatusTip("이미지를 반시계 방향으로 90° 회전합니다.")
        self._rotate_ccw_act.setShortcut(Qt.Key_E)
        self._rotate_ccw_act.triggered.connect(self._on_rotate_ccw_clicked)
        tb.addAction(self._rotate_ccw_act)

        self._rotate_act = QAction(get_qicon("rotate"), "시계 회전 (R)", self)
        self._rotate_act.setStatusTip("이미지를 시계 방향으로 90° 회전합니다.")
        self._rotate_act.setShortcut(Qt.Key_R)
        self._rotate_act.triggered.connect(self._on_rotate_cw_clicked)
        tb.addAction(self._rotate_act)

        self._flip_act = QAction(get_qicon("flip_h"), "좌우 반전 (H)", self)
        self._flip_act.setStatusTip("이미지를 좌우로 반전합니다.")
        self._flip_act.setShortcut(Qt.Key_H)
        self._flip_act.triggered.connect(self._on_flip_clicked)
        tb.addAction(self._flip_act)
        tb.addSeparator()

        # ── 이미지 작업 도구 (크기 변환 + 편집기) ──
        self._batch_convert_act = QAction(get_qicon("batch_convert"), "이미지 크기 변환 (B)", self)
        self._batch_convert_act.setStatusTip("이미지 일괄 변환기(리사이즈 등)를 실행합니다.")
        self._batch_convert_act.setShortcut(Qt.Key_B)
        self._batch_convert_act.triggered.connect(self._launch_batch_converter)
        tb.addAction(self._batch_convert_act)

        self._editor_act = QAction(get_qicon("image_editor"), "이미지 편집기 (E)", self)
        self._editor_act.setStatusTip("이미지 편집기를 실행합니다. (추후 업데이트 예정)")
        self._editor_act.setShortcut(Qt.Key_E)
        # self._editor_act.triggered.connect(...)
        tb.addAction(self._editor_act)
        
        tb.addSeparator()

        # ── 환경설정 ──
        self._settings_act = QAction(get_qicon("settings"), "환경설정", self)
        self._settings_act.setStatusTip("프로그램 환경설정을 엽니다.")
        self._settings_act.triggered.connect(self._open_settings)
        tb.addAction(self._settings_act)
        
        # Spacer
        self._info_act = QAction(get_qicon("info_circle"), "정보 패널 (I)", self)
        self._info_act.setCheckable(True)
        self._info_act.setShortcut(Qt.Key_I)
        self._info_act.triggered.connect(self._toggle_info_panel)
        tb.addAction(self._info_act)

        # ── 지도 연동 (GPS 감지 시 노출) ──
        self._btn_naver = self._create_map_toolbar_btn("Naver", "#2DB400")
        self._btn_kakao = self._create_map_toolbar_btn("Kakao", "#FEE500", "#3C1E1E")
        self._btn_google = self._create_map_toolbar_btn("Google", "#4285F4")
        
        # addWidget은 QAction을 반환하므로 이를 저장하여 제어
        self._act_naver = tb.addWidget(self._btn_naver)
        self._act_kakao = tb.addWidget(self._btn_kakao)
        self._act_google = tb.addWidget(self._btn_google)
        
        # 초기 숨김
        self._act_naver.setVisible(False)
        self._act_kakao.setVisible(False)
        self._act_google.setVisible(False)

        # 스페이서
        spacer = QWidget()
        spacer.setStyleSheet("background: transparent;")
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)

        # ── 이전 / 다음 (우측) ──
        self._prev_act = QAction(get_qicon("nav_prev"), "이전 이미지 (←)", self)
        self._prev_act.setShortcut(Qt.Key_Left)
        self._prev_act.triggered.connect(self._prev_image)
        tb.addAction(self._prev_act)

        self._next_act = QAction(get_qicon("nav_next"), "다음 이미지 (→)", self)
        self._next_act.setShortcut(Qt.Key_Right)
        self._next_act.triggered.connect(self._next_image)
        tb.addAction(self._next_act)

    # ──────────────────────────────────────────────
    # 시그널 연결
    # ──────────────────────────────────────────────
    def _connect_signals(self):
        # 메인 뷰포트
        self._viewport.zoom_changed.connect(self._on_zoom_changed)
        self._viewport.image_loaded.connect(self._on_image_loaded)
        self._viewport.view_changed.connect(self._nav.update_view)
        self._viewport.load_failed.connect(self._on_load_failed)
        
        # 분할 뷰포트들
        self._split_view.left_viewport.zoom_changed.connect(self._on_zoom_changed)
        self._split_view.right_viewport.zoom_changed.connect(self._on_zoom_changed)
        self._split_view.left_viewport.view_changed.connect(self._on_viewport_view_changed)
        self._split_view.right_viewport.view_changed.connect(self._on_viewport_view_changed)
        self._split_view.active_changed.connect(self._on_split_active_changed)

        self._model.index_changed.connect(self._on_model_index_changed)

    # ──────────────────────────────────────────────
    # 파일 로드
    # ──────────────────────────────────────────────
    def _load_file(self, path: str):
        if not os.path.isfile(path):
            return
        self._model.scan_folder(path)
        vp = self._get_active_viewport()
        vp.load_image(path)

    def _get_active_viewport(self) -> ImageViewport:
        """현재 활성화된 뷰포트 반환 (단일/분할 상태 고려)"""
        if self._stack.currentIndex() == 0:
            return self._viewport
        return self._split_view.get_active_viewport()

    def _toggle_split_view(self, checked: bool):
        """단일 뷰 <-> 분할 뷰 전환"""
        if checked:
            # 1. 단일 뷰의 이미지를 왼쪽 분할 뷰로 복사
            curr = self._viewport.current_path
            if curr:
                self._split_view.left_viewport.load_image(curr)
                
                # 2. 다음 이미지를 오른쪽 분할 뷰로 로드
                next_path = self._model.next()
                if next_path:
                    self._split_view.right_viewport.load_image(next_path)
                    
            self._stack.setCurrentIndex(1)
            self._on_split_active_changed("left")
        else:
            # 왼쪽 분할 뷰의 이미지를 단일 뷰로 복원
            curr = self._split_view.left_viewport.current_path
            if curr:
                self._viewport.load_image(curr)
            self._stack.setCurrentIndex(0)
        
        # 네비게이터 갱신
        self._on_split_active_changed("left" if checked else "")

    def _toggle_info_panel(self, checked: bool):
        """정보 패널 보이기/숨기기"""
        self._info_panel.setVisible(checked)
        if checked:
            self._info_panel.set_image(self._get_active_viewport().current_path)

    def _on_split_active_changed(self, side: str):
        """분할 뷰 포커스 변경 시 네비게이터 및 정보 패널 동기화"""
        vp = self._get_active_viewport()
        self._nav.set_thumbnail(vp.get_thumbnail())
        # 위치 정보도 즉시 갱신 (가시 영역, 전체 영역 전달)
        self._nav.update_view(vp.get_view_rect(), vp.get_scene_rect())
        
        # 줌 콤보박스 업데이트
        self._on_zoom_changed(vp.get_zoom_percent() / 100.0)
        self._info_panel.set_image(vp.current_path)

    def _on_viewport_view_changed(self, view_rect, scene_rect):
        """뷰포트 이동 시 활성 뷰포트인 경우에만 네비게이터 갱신"""
        if self.sender() == self._get_active_viewport():
            self._nav.update_view(view_rect, scene_rect)

    def _on_gps_detected(self, coords):
        """이미지에서 GPS 정보가 감지된 경우 처리"""
        self._current_coords = coords
        visible = coords is not None
        self._act_naver.setVisible(visible)
        self._act_kakao.setVisible(visible)
        self._act_google.setVisible(visible)

    def _launch_batch_converter(self):
        import sys
        import subprocess
        # 배포된 exe인지 스크립트인지 판별
        if getattr(sys, 'frozen', False):
            cmd = [sys.executable, "--convert"]
        else:
            cmd = [sys.executable, sys.argv[0], "--convert"]
            
        # 현재 열려있는 파일이나 분할 뷰의 파일들을 넘길 수 있음
        # 기본적으로는 현재 활성화된 이미지만 먼저 넘김
        current_path = self._model.current()
        if current_path:
            cmd.append(current_path)
            
        # 뷰어를 블로킹하지 않도록 subprocess.Popen 사용
        subprocess.Popen(cmd)

    def _open_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()

    def _create_map_toolbar_btn(self, text, bg, fg="white"):
        btn = QToolButton()
        btn.setText(text)
        btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QToolButton {{
                background-color: {bg};
                color: {fg};
                border-radius: 4px;
                font-weight: bold;
                padding: 7px 0;
                min-height: 24px;
                min-width: 50px;
                font-size: 12px;
            }}
            QToolButton:hover {{ background-color: white; color: {bg}; }}
        """)
        btn.clicked.connect(lambda: self._open_map(text.lower()))
        return btn

    def _open_map(self, engine):
        if not self._current_coords:
            return
        lat, lon = self._current_coords
        urls = {
            "naver": f"https://map.naver.com/v5/search/{lat}%2C{lon}",
            "kakao": f"https://map.kakao.com/link/search/{lat},{lon}",
            "google": f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
        }
        webbrowser.open(urls.get(engine))

    def _open_file_dialog(self):
        ext_filter = "이미지 파일 (" + " ".join(f"*{e}" for e in SUPPORTED_EXTS) + ");;모든 파일 (*)"
        last_dir = settings.get("last_open_dir", "")
        path, _ = QFileDialog.getOpenFileName(self, "파일 열기", last_dir, ext_filter)
        if path:
            settings.set("last_open_dir", os.path.dirname(path))
            self._load_file(path)

    def _update_recent_menu(self):
        self._open_menu.clear()
        direct = QAction("직접 파일 열기...", self)
        direct.triggered.connect(self._open_file_dialog)
        self._open_menu.addAction(direct)

        recent = settings.get("recent_files", [])
        if recent:
            self._open_menu.addSeparator()
            for p in recent:
                if not os.path.exists(p):
                    continue
                act = QAction(os.path.basename(p), self)
                act.setToolTip(p)
                act.triggered.connect(lambda checked=False, fp=p: self._load_file(fp))
                self._open_menu.addAction(act)

    # ──────────────────────────────────────────────
    # 이미지 탐색
    # ──────────────────────────────────────────────
    def _next_image(self):
        path = self._model.next()
        if path:
            self._get_active_viewport().load_image(path)

    def _prev_image(self):
        path = self._model.prev()
        if path:
            self._get_active_viewport().load_image(path)

    def _on_fit_clicked(self):
        """현재 화면에 맞게 확대/축소 (활성 뷰포트 기준)"""
        self._get_active_viewport().fit_in_view()

    def _on_rotate_cw_clicked(self):
        """시계 방향 회전 (활성 뷰포트 기준)"""
        self._get_active_viewport().rotate_cw()

    def _on_rotate_ccw_clicked(self):
        """반시계 방향 회전 (활성 뷰포트 기준)"""
        self._get_active_viewport().rotate_ccw()

    def _on_flip_clicked(self):
        """좌우 반전 (활성 뷰포트 기준)"""
        self._get_active_viewport().flip_horizontal()

    # ──────────────────────────────────────────────
    # 줌 컨트롤
    # ──────────────────────────────────────────────
    def _zoom_step(self, direction: int):
        """툴바 줌 버튼 (±15%)"""
        vp = self._get_active_viewport()
        factor = ImageViewport.ZOOM_FACTOR if direction > 0 else 1.0 / ImageViewport.ZOOM_FACTOR
        current = vp._get_zoom_scale()
        vp.set_zoom(current * factor)

    def _show_zoom_menu(self, event=None):
        """줌 레이블 클릭 → 프리셋 메뉴"""
        menu = QMenu(self)
        presets = [10, 25, 50, 75, 100, 125, 150, 200, 300, 400, 500]
        vp = self._get_active_viewport()
        for p in presets:
            act = QAction(f"{p}%", self)
            act.triggered.connect(lambda checked=False, v=p: vp.set_zoom(v / 100))
            menu.addAction(act)
        menu.addSeparator()
        fit_act = QAction("화면 맞춤", self)
        fit_act.triggered.connect(vp.fit_in_view)
        menu.addAction(fit_act)
        menu.exec(self._lbl_zoom.mapToGlobal(self._lbl_zoom.rect().bottomLeft()))

    # ──────────────────────────────────────────────
    # 이미지 편집기 (추후 연동)
    # ──────────────────────────────────────────────
    def _launch_editor(self):
        QMessageBox.information(self, "준비 중",
                                "이미지 편집기는 추후 업데이트에서 제공됩니다.")

    # ──────────────────────────────────────────────
    # 슬롯
    # ──────────────────────────────────────────────
    def _on_zoom_changed(self, scale: float):
        # 콤보박스 텍스트 업데이트 (시그널 루프 방지 위해 blockSignals 사용)
        self._zoom_combo.blockSignals(True)
        self._zoom_combo.setCurrentText(f"{int(scale * 100)}%")
        self._zoom_combo.blockSignals(False)

    def _on_zoom_combo_changed(self, text: str):
        vp = self._get_active_viewport()
        try:
            val = int(text.replace("%", ""))
            vp.set_zoom(val / 100.0)
        except:
            pass

    def _on_file_renamed(self, old_path: str, new_path: str):
        """정보 패널에서 파일명이 변경된 경우 처리"""
        if self._model.update_image_path(old_path, new_path):
            self.setWindowTitle(f"DS Image Viewer - {os.path.basename(new_path)}")
            self._update_status_bar()
            self._update_recent_menu()

    def _on_image_loaded(self, path: str):
        settings.add_recent_file(path)
        self._update_recent_menu()
        
        # 네비게이터 및 정보 패널 업데이트
        vp = self._get_active_viewport()
        self._nav.set_thumbnail(vp.get_thumbnail())
        self._info_panel.set_image(path)

        filename = os.path.basename(path)
        idx = self._model.index
        cnt = self._model.count  # total에서 count로 수정
        self._lbl_file.setText(f"  {filename}  ({idx + 1} / {cnt})")

        try:
            sz = os.path.getsize(path)
            vp = self._get_active_viewport()
            w, h = vp._pil_img.size if vp._pil_img else (0, 0)
            self._lbl_size.setText(f"{w} × {h}  |  {self._fmt_size(sz)}")
        except Exception:
            self._lbl_size.setText("")

        ver = '.'.join(BUILD_VERSION.split('.')[:2])
        user = self.license_data.get('user_name', 'User')
        self.setWindowTitle(f"DS Image Viewer v{ver} — {filename}")

    def _on_load_failed(self, msg: str):
        self._status.showMessage(f"로드 실패: {msg}", 4000)

    def _on_model_index_changed(self, idx: int):
        # 모델에서 인덱스가 바뀌면 상태바 갱신 (탐색 키로 변경 시)
        pass

    # ──────────────────────────────────────────────
    # 드래그 앤 드롭
    # ──────────────────────────────────────────────
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].toLocalFile().lower().endswith(SUPPORTED_EXTS):
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.isfile(path):
                self._load_file(path)
                event.acceptProposedAction()

    # ──────────────────────────────────────────────
    # 키보드
    # ──────────────────────────────────────────────
    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Escape:
            pass  # 종료 방지
        elif key == Qt.Key_Z and event.modifiers() == Qt.ControlModifier:
            self._model.undo_rename()
        else:
            super().keyPressEvent(event)

    def resizeEvent(self, event):
        """네비게이터 오버레이 위치 조정 (우측 상단)"""
        if hasattr(self, "_nav"):
            self._nav.move(self.width() - self._nav.width() - 20, 60)
        super().resizeEvent(event)

    # ──────────────────────────────────────────────
    # 유틸
    # ──────────────────────────────────────────────
    @staticmethod
    def _fmt_size(b: int) -> str:
        for unit in ('B', 'KB', 'MB', 'GB'):
            if b < 1024:
                return f"{b:.1f} {unit}"
            b /= 1024
        return f"{b:.1f} TB"
