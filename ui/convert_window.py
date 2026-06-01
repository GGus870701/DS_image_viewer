import os
import multiprocessing
from PIL import Image
from PIL.ImageQt import ImageQt

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                                QLabel, QListWidget, QGroupBox, QRadioButton,
                                QComboBox, QSpinBox, QCheckBox, QPushButton,
                                QSplitter, QLineEdit, QFileDialog, QProgressBar,
                                QScrollArea, QAbstractItemView, QTextEdit, QMessageBox,
                                QSizePolicy, QDialog, QAbstractSpinBox, QGridLayout)
from PySide6.QtCore import Qt, QSize, Signal, QThread, QTimer
from PySide6.QtGui import QIcon, QPixmap

from core.image_converter import ConvertSettings, BatchConverterWorker, process_single_image
from ui.icon_data import get_qicon
from ui.style import get_stylesheet
from core.settings import settings
from dataclasses import asdict

class DragDropListWidget(QListWidget):
    """드래그 앤 드롭과 Delete 키 삭제를 지원하는 커스텀 파일 목록 위젯"""
    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            paths = [url.toLocalFile() for url in urls if os.path.isfile(url.toLocalFile())]
            if paths:
                self.files_dropped.emit(paths)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            for item in self.selectedItems():
                self.takeItem(self.row(item))
        else:
            super().keyPressEvent(event)

class NoWheelComboBox(QComboBox):
    """휠 이벤트로 인해 의도치 않게 설정이 바뀌는 것을 방지"""
    def wheelEvent(self, event):
        event.ignore()

class NoWheelSpinBox(QSpinBox):
    """휠 이벤트로 인해 의도치 않게 설정이 바뀌는 것을 방지"""
    def wheelEvent(self, event):
        event.ignore()

class PreviewWorker(QThread):
    result_ready = Signal(QPixmap, str)
    
    def __init__(self, file_path, settings, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.settings = settings
        
    def run(self):
        # 백그라운드에서 PIL로 이미지 처리
        success, img_or_err, exif_info = process_single_image((self.file_path, self.settings), preview_only=True)
        if success:
            pil_img = img_or_err
            # QPixmap으로 변환하기 위해 ImageQt 사용
            qimg = ImageQt(pil_img)
            pixmap = QPixmap.fromImage(qimg)
            self.result_ready.emit(pixmap, exif_info)
        else:
            # 실패 시 에러 문자열이 옴
            self.result_ready.emit(QPixmap(), f"미리보기 실패: {img_or_err}")


class ConvertWindow(QMainWindow):
    def __init__(self, initial_files=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DS Image Viewer - 이미지 크기 변환")
        self.setWindowIcon(get_qicon("batch_convert"))
        self.setStyleSheet(get_stylesheet())
        self.resize(1400, 900)
        
        self.worker = None
        self.preview_worker = None
        
        # 디바운스를 위한 타이머 (사용자 입력 중에는 렌더링 딜레이)
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self._run_preview_rendering)
        
        self._center_window()
        self._init_ui()
        self.load_settings()
        
        if initial_files:
            self.add_files(initial_files)

    def _center_window(self):
        screen = self.screen().availableGeometry()
        size = self.geometry()
        x = (screen.width() - size.width()) // 2
        y = (screen.height() - size.height()) // 2
        self.move(x, y)

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(10) # 패널 사이 간격 설정
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # === 좌측 패널 ===
        left_widget = QWidget()
        left_widget.setFixedWidth(340) # 좌측 패널 크기 고정 (요구사항)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(5, 0, 5, 0)
        left_layout.setSpacing(12)
        
        # 1) 좌측 상부: 파일 목록
        file_group = QGroupBox("변환 대상 파일")
        file_group.setFixedHeight(250) # (요구사항 2) 리사이즈 시 파일목록 크기 고정
        file_layout = QVBoxLayout(file_group)
        file_layout.setContentsMargins(10, 15, 10, 10)
        file_layout.setSpacing(8)
        self.file_list = DragDropListWidget()
        self.file_list.files_dropped.connect(self.add_files)
        
        btn_layout = QHBoxLayout()
        self.btn_add_file = QPushButton("파일 추가")
        self.btn_clear_file = QPushButton("목록 비우기") # (요구사항 3) 이름 변경
        btn_layout.addWidget(self.btn_add_file)
        btn_layout.addWidget(self.btn_clear_file)
        
        file_layout.addWidget(self.file_list)
        file_layout.addLayout(btn_layout)
        left_layout.addWidget(file_group, 0) # stretch=0으로 하여 세로 고정 유지
        
        # 2) 좌측 하부: 변환 설정 (스크롤 영역)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        settings_layout.setContentsMargins(5, 5, 10, 10)
        settings_layout.setSpacing(15)
        
        self._build_rotation_settings(settings_layout)
        self._build_resize_settings(settings_layout)
        self._build_format_settings(settings_layout)
        self._build_location_settings(settings_layout)
        self._build_naming_settings(settings_layout)
        
        # 여백 채우기
        settings_layout.addStretch(1)
        scroll_area.setWidget(settings_widget)
        left_layout.addWidget(scroll_area, 2)
        
        # 3) 좌측 하단: 설정 초기화 버튼
        self.btn_reset_settings = QPushButton("설정 초기화")
        left_layout.addWidget(self.btn_reset_settings)
        
        # 강조용 붉은색 버튼 스타일
        red_btn_style = """
            QPushButton {
                background-color: #c0392b;
                color: #ffffff;
                border: 1px solid #a93226;
                border-radius: 4px;
                padding: 5px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e74c3c;
            }
            QPushButton:pressed {
                background-color: #922b21;
            }
            QPushButton:disabled {
                background-color: #1e272e;
                color: #57606f;
                border: 1px solid #2f3542;
            }
        """
        self.btn_reset_settings.setStyleSheet(red_btn_style)
        
        main_layout.addWidget(left_widget)
        
        # === 우측 패널 ===
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 1) 우측 상단: 미리보기
        preview_group = QGroupBox("미리보기 (Preview)")
        preview_layout = QVBoxLayout(preview_group)
        
        # 미리보기와 플로팅 버튼을 겹치기 위한 컨테이너
        preview_container = QWidget()
        preview_grid = QGridLayout(preview_container)
        preview_grid.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_preview = QLabel("좌측에서 파일을 선택하면 미리보기가 표시됩니다.")
        self.lbl_preview.setAlignment(Qt.AlignCenter)
        self.lbl_preview.setMinimumSize(400, 300)
        self.lbl_preview.setStyleSheet("background-color: #1e272e; border: 1px solid #3d3d3d;")
        
        # EXIF 플로팅 아이콘 버튼 (요구사항)
        self.btn_show_exif = QPushButton()
        self.btn_show_exif.setIcon(get_qicon("info_circle"))
        self.btn_show_exif.setIconSize(QSize(24, 24))
        self.btn_show_exif.setFixedSize(40, 40)
        self.btn_show_exif.setToolTip("EXIF 정보 보기")
        self.btn_show_exif.setEnabled(False)
        self.btn_show_exif.setCursor(Qt.PointingHandCursor)
        self.btn_show_exif.setStyleSheet("""
            QPushButton {
                background-color: rgba(47, 54, 64, 200);
                border: 2px solid #57606f;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: rgba(15, 188, 249, 220);
                border: 2px solid #0fbcf9;
            }
            QPushButton:pressed {
                background-color: #0984e3;
            }
            QPushButton:disabled {
                background-color: transparent;
                border: none;
            }
        """)
        self.current_exif_info = ""
        
        # 그리드에 겹쳐서 배치
        preview_grid.addWidget(self.lbl_preview, 0, 0)
        preview_grid.addWidget(self.btn_show_exif, 0, 0, Qt.AlignTop | Qt.AlignRight)
        
        preview_layout.addWidget(preview_container)
        right_layout.addWidget(preview_group, 3)
        
        # 2) 우측 하단: 실행 및 프로그레스
        run_group = QGroupBox("진행 상태")
        run_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed) # (요구사항 7) 메뉴 크기 최소화 고정
        run_layout = QVBoxLayout(run_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.lbl_status = QLabel("대기 중...")
        
        self.btn_start = QPushButton("변환 시작 (Start)")
        self.btn_start.setIcon(get_qicon("batch_convert"))
        self.btn_start.setIconSize(QSize(24, 24))
        self.btn_start.setMinimumHeight(40)
        self.btn_start.setStyleSheet(red_btn_style)
        
        self.btn_open_folder = QPushButton("결과 폴더 열기")
        self.btn_open_folder.setMinimumHeight(40)
        blue_btn_style = """
            QPushButton {
                background-color: #0984e3;
                color: #ffffff;
                border: 1px solid #076bbb;
                border-radius: 4px;
                padding: 5px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0fbcf9;
            }
            QPushButton:pressed {
                background-color: #065299;
            }
        """
        self.btn_open_folder.setStyleSheet(blue_btn_style)
        self.btn_open_folder.hide()
        
        run_layout.addWidget(self.progress_bar)
        run_layout.addWidget(self.lbl_status)
        run_layout.addWidget(self.btn_start)
        run_layout.addWidget(self.btn_open_folder)
        
        right_layout.addWidget(run_group, 1)
        
        main_layout.addWidget(right_widget)
        
        self._connect_signals()

    def _build_rotation_settings(self, layout):
        group = QGroupBox("회전 설정")
        l = QVBoxLayout(group)
        self.cb_rotation = NoWheelComboBox()
        self.cb_rotation.addItems(["회전 안함", "좌로 90도", "우로 90도", "180도", "EXIF 정보를 사용해서 자동으로"])
        l.addWidget(self.cb_rotation)
        layout.addWidget(group)

    def _build_resize_settings(self, layout):
        group = QGroupBox("크기 조절")
        l = QVBoxLayout(group)
        self.cb_resize_mode = NoWheelComboBox()
        self.cb_resize_mode.addItems(["크기 변경 안함", "비율 유지", "폭 맞춤", "높이 맞춤", "여백 붙이기", "여백 자르기", "꽉차게 늘리기"])
        l.addWidget(self.cb_resize_mode)
        
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("폭(W)"))
        self.spin_width = NoWheelSpinBox()
        self.spin_width.setRange(1, 10000)
        self.spin_width.setButtonSymbols(QAbstractSpinBox.NoButtons)
        size_layout.addWidget(self.spin_width, 1) # stretch 1
        
        size_layout.addSpacing(5)
        
        size_layout.addWidget(QLabel("높이(H)"))
        self.spin_height = NoWheelSpinBox()
        self.spin_height.setRange(1, 10000)
        self.spin_height.setButtonSymbols(QAbstractSpinBox.NoButtons)
        size_layout.addWidget(self.spin_height, 1) # stretch 1
        
        size_layout.addStretch() # 나머지 공간 채움
        size_layout.addWidget(QLabel("px"))
        
        l.addLayout(size_layout)
        layout.addWidget(group)

    def _build_format_settings(self, layout):
        group = QGroupBox("저장 이미지 포맷")
        l = QVBoxLayout(group)
        l.setSpacing(10)
        
        # 1) 포맷
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("포맷:"))
        self.cb_format = NoWheelComboBox()
        self.cb_format.addItems(["기존 형식 유지", "JPG", "PNG", "WEBP"])
        h1.addWidget(self.cb_format, 1) # stretch 1
        l.addLayout(h1)
        
        # 2) 화질
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("화질:"))
        self.spin_quality = NoWheelSpinBox()
        self.spin_quality.setRange(1, 100)
        self.spin_quality.setButtonSymbols(QAbstractSpinBox.NoButtons)
        h2.addWidget(self.spin_quality, 1) # stretch 1
        l.addLayout(h2)
        
        # 3) 멀티코어
        h3 = QHBoxLayout()
        h3.addWidget(QLabel("멀티코어:"))
        self.cb_cores = NoWheelComboBox()
        self.cb_cores.addItem("자동")
        max_cores = multiprocessing.cpu_count()
        for i in range(1, max_cores + 1):
            self.cb_cores.addItem(str(i))
        h3.addWidget(self.cb_cores, 1) # stretch 1
        l.addLayout(h3)
        
        # 4) EXIF 정보 보존
        self.chk_preserve_exif = QCheckBox("EXIF 정보 보존")
        l.addWidget(self.chk_preserve_exif)
        
        layout.addWidget(group)

    def _build_location_settings(self, layout):
        group = QGroupBox("저장 위치 설정")
        l = QVBoxLayout(group)
        
        self.radio_loc_same = QRadioButton("원본과 같은 위치에 저장")
        self.radio_loc_specific = QRadioButton("다음 폴더에 저장:")
        self.radio_loc_subfolder = QRadioButton("원본 하위 폴더에 저장 (폴더명):")
        
        l.addWidget(self.radio_loc_same)
        
        # 특정 폴더
        l.addWidget(self.radio_loc_specific)
        h_spec = QHBoxLayout()
        h_spec.addSpacing(20) # 들여쓰기
        self.txt_specific_dir = QLineEdit()
        self.txt_specific_dir.setEnabled(False)
        self.btn_browse_dir = QPushButton("...")
        self.btn_browse_dir.setFixedWidth(30)
        self.btn_browse_dir.setEnabled(False)
        h_spec.addWidget(self.txt_specific_dir)
        h_spec.addWidget(self.btn_browse_dir)
        l.addLayout(h_spec)
        
        # 하위 폴더
        l.addWidget(self.radio_loc_subfolder)
        h_sub = QHBoxLayout()
        h_sub.addSpacing(20) # 들여쓰기
        self.txt_subfolder = QLineEdit()
        h_sub.addWidget(self.txt_subfolder)
        l.addLayout(h_sub)
        
        layout.addWidget(group)

    def _build_naming_settings(self, layout):
        group = QGroupBox("파일 이름 설정")
        l = QVBoxLayout(group)
        
        l.addWidget(QLabel("중복되는 파일 이름이 있을 때"))
        self.radio_conflict_rename = QRadioButton("이름 바꾸기 (예: 파일명(2))")
        self.radio_conflict_overwrite = QRadioButton("기존 파일 덮어쓰기")
        l.addWidget(self.radio_conflict_rename)
        l.addWidget(self.radio_conflict_overwrite)
        
        # 접두어
        self.chk_prefix = QCheckBox("앞에 글자 붙이기:")
        l.addWidget(self.chk_prefix)
        h_prefix = QHBoxLayout()
        h_prefix.addSpacing(20) # 들여쓰기
        self.txt_prefix = QLineEdit()
        self.txt_prefix.setEnabled(False)
        h_prefix.addWidget(self.txt_prefix)
        l.addLayout(h_prefix)
        
        layout.addWidget(group)

    def _connect_signals(self):
        self.btn_add_file.clicked.connect(self._on_btn_add_file_clicked)
        self.btn_clear_file.clicked.connect(self._on_btn_clear_file_clicked)
        self.btn_reset_settings.clicked.connect(self.reset_settings)
        self.btn_show_exif.clicked.connect(self._show_exif_dialog)
        
        # Location Radio logic
        self.radio_loc_same.toggled.connect(self._update_location_ui)
        self.radio_loc_specific.toggled.connect(self._update_location_ui)
        self.radio_loc_subfolder.toggled.connect(self._update_location_ui)
        
        # Prefix logic
        self.chk_prefix.toggled.connect(self.txt_prefix.setEnabled)
        
        # 버튼 액션
        self.btn_browse_dir.clicked.connect(self._browse_specific_dir)
        self.btn_start.clicked.connect(self._start_conversion)
        self.btn_open_folder.clicked.connect(self._open_result_folder)
        
        # 설정 변경 시 미리보기 트리거 및 자동 저장
        widgets_to_watch = [
            self.cb_rotation, self.cb_resize_mode, self.spin_width, self.spin_height,
            self.cb_format, self.spin_quality, self.chk_preserve_exif,
            self.radio_loc_same, self.radio_loc_specific, self.radio_loc_subfolder,
            self.cb_cores, self.radio_conflict_rename, self.radio_conflict_overwrite,
            self.chk_prefix, self.txt_specific_dir, self.txt_subfolder, self.txt_prefix
        ]
        for w in widgets_to_watch:
            if isinstance(w, QComboBox) or isinstance(w, NoWheelComboBox):
                w.currentIndexChanged.connect(self._on_settings_changed)
            elif isinstance(w, QSpinBox) or isinstance(w, NoWheelSpinBox):
                w.valueChanged.connect(self._on_settings_changed)
            elif isinstance(w, QCheckBox) or isinstance(w, QRadioButton):
                w.toggled.connect(self._on_settings_changed)
            elif isinstance(w, QLineEdit):
                w.textChanged.connect(self._on_settings_changed)
                
    def _on_btn_add_file_clicked(self):
        files, _ = QFileDialog.getOpenFileNames(self, "변환할 파일 추가", "", "이미지 파일 (*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp)")
        if files:
            self.add_files(files)

    def _on_btn_clear_file_clicked(self):
        self.file_list.clear()
        self.lbl_preview.setPixmap(QPixmap())
        self.lbl_preview.setText("좌측에서 파일을 선택하면 미리보기가 표시됩니다.")
        self.btn_show_exif.setEnabled(False)
        self.current_exif_info = ""
        self.btn_open_folder.hide()
        self.btn_start.show()
        self.btn_start.setEnabled(True)
        self.btn_start.setText("변환 시작 (Start)")

    def _show_exif_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("EXIF 정보")
        dlg.resize(400, 300)
        l = QVBoxLayout(dlg)
        t = QTextEdit()
        t.setReadOnly(True)
        t.setText(self.current_exif_info if self.current_exif_info else "EXIF 정보가 없습니다.")
        l.addWidget(t)
        dlg.exec()

    def _browse_specific_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "저장할 폴더 선택")
        if dir_path:
            self.txt_specific_dir.setText(dir_path)
            self._on_settings_changed()

    def _update_location_ui(self):
        is_specific = self.radio_loc_specific.isChecked()
        self.txt_specific_dir.setEnabled(is_specific)
        self.btn_browse_dir.setEnabled(is_specific)
        
        is_sub = self.radio_loc_subfolder.isChecked()
        self.txt_subfolder.setEnabled(is_sub)
        self._on_settings_changed()

    def _on_settings_changed(self):
        self.save_settings()
        if self.file_list.count() > 0:
            self.preview_timer.start(300)

    def _run_preview_rendering(self):
        if self.file_list.count() == 0:
            self.lbl_preview.setText("파일을 추가해주세요.")
            self.btn_show_exif.setEnabled(False)
            self.current_exif_info = ""
            return
            
        first_file = self.file_list.item(0).text()
        settings = self.get_current_settings()
        
        self.lbl_preview.setText("렌더링 중...")
        self.btn_show_exif.setEnabled(False)
        
        if self.preview_worker and self.preview_worker.isRunning():
            self.preview_worker.terminate()
            self.preview_worker.wait()
            
        self.preview_worker = PreviewWorker(first_file, settings)
        self.preview_worker.result_ready.connect(self._on_preview_ready)
        self.preview_worker.start()

    def _on_preview_ready(self, pixmap, exif_info):
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(self.lbl_preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.lbl_preview.setPixmap(scaled_pixmap)
            
            self.current_exif_info = exif_info
            self.btn_show_exif.setEnabled(True)
        else:
            self.lbl_preview.setText(exif_info)
            self.current_exif_info = ""
            self.btn_show_exif.setEnabled(False)

    def get_current_settings(self) -> ConvertSettings:
        loc_mode = 0
        if self.radio_loc_specific.isChecked(): loc_mode = 1
        elif self.radio_loc_subfolder.isChecked(): loc_mode = 2
        
        return ConvertSettings(
            rotation_mode=self.cb_rotation.currentIndex(),
            resize_mode=self.cb_resize_mode.currentIndex(),
            target_width=self.spin_width.value(),
            target_height=self.spin_height.value(),
            unit_is_percent=False,
            format_idx=self.cb_format.currentIndex(),
            quality=self.spin_quality.value(),
            preserve_exif=self.chk_preserve_exif.isChecked(),
            loc_mode=loc_mode,
            specific_dir=self.txt_specific_dir.text(),
            subfolder_name=self.txt_subfolder.text(),
            conflict_mode=1 if self.radio_conflict_overwrite.isChecked() else 0,
            use_prefix=self.chk_prefix.isChecked(),
            prefix_str=self.txt_prefix.text()
        )

    def _start_conversion(self):
        if self.file_list.count() == 0:
            QMessageBox.warning(self, "경고", "변환할 파일이 없습니다.")
            return
            
        settings = self.get_current_settings()
        
        if settings.loc_mode == 1 and not settings.specific_dir:
            QMessageBox.warning(self, "경고", "저장할 특정 폴더를 선택해주세요.")
            return
            
        file_paths = [self.file_list.item(i).text() for i in range(self.file_list.count())]
        
        cores_text = self.cb_cores.currentText()
        if cores_text == "자동":
            cores = None
        else:
            cores = int(cores_text)
            
        self.btn_start.setEnabled(False)
        self.btn_start.setText("변환 중...")
        self.btn_open_folder.hide()
        self.btn_start.show()
        self.progress_bar.setValue(0)
        
        self.worker = BatchConverterWorker(file_paths, settings, max_workers=cores)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, current, total, last_file):
        pct = int((current / total) * 100)
        self.progress_bar.setValue(pct)
        fname = os.path.basename(last_file)
        self.lbl_status.setText(f"[{current}/{total}] {fname} 처리 완료")

    def _on_finished(self, success_count, fail_count):
        self.lbl_status.setText(f"완료! (성공: {success_count}, 실패: {fail_count})")
        self.progress_bar.setValue(100)
        
        if success_count > 0:
            self.btn_start.hide()
            self.btn_open_folder.show()
            self._last_saved_path = self.file_list.item(0).text()
        else:
            self.btn_start.setEnabled(True)
            self.btn_start.setText("변환 시작 (Start)")

    def _open_result_folder(self):
        settings = self.get_current_settings()
        out_dir = ""
        
        if settings.loc_mode == 0:
            out_dir = os.path.dirname(self._last_saved_path)
        elif settings.loc_mode == 1:
            out_dir = settings.specific_dir
        elif settings.loc_mode == 2:
            out_dir = os.path.join(os.path.dirname(self._last_saved_path), settings.subfolder_name)
            
        if os.path.exists(out_dir):
            os.startfile(out_dir)

    def reset_settings(self):
        from core.settings import _DEFAULTS
        default_data = _DEFAULTS.get("convert_settings", {})
        self.apply_settings_data(default_data)
        
    def load_settings(self):
        data = settings.get("convert_settings")
        if data:
            self.apply_settings_data(data)
            
    def save_settings(self):
        current_settings = self.get_current_settings()
        data = asdict(current_settings)
        data["cores_index"] = self.cb_cores.currentIndex()
        settings.set("convert_settings", data)
        
    def apply_settings_data(self, data: dict):
        self.blockSignals(True)
        try:
            self.cb_rotation.setCurrentIndex(data.get("rotation_mode", 4))
            self.cb_resize_mode.setCurrentIndex(data.get("resize_mode", 1))
            self.spin_width.setValue(data.get("target_width", 640))
            self.spin_height.setValue(data.get("target_height", 480))
            self.cb_format.setCurrentIndex(data.get("format_idx", 0))
            self.spin_quality.setValue(data.get("quality", 80))
            self.chk_preserve_exif.setChecked(data.get("preserve_exif", True))
            
            loc_mode = data.get("loc_mode", 2)
            if loc_mode == 0: self.radio_loc_same.setChecked(True)
            elif loc_mode == 1: self.radio_loc_specific.setChecked(True)
            else: self.radio_loc_subfolder.setChecked(True)
            
            self.txt_specific_dir.setText(data.get("specific_dir", ""))
            self.txt_subfolder.setText(data.get("subfolder_name", "output"))
            
            # 중복 처리 (라디오 버튼)
            if data.get("conflict_mode", 0) == 1:
                self.radio_conflict_overwrite.setChecked(True)
            else:
                self.radio_conflict_rename.setChecked(True)
            
            self.chk_prefix.setChecked(data.get("use_prefix", False))
            self.txt_prefix.setText(data.get("prefix_str", ""))
            self.cb_cores.setCurrentIndex(data.get("cores_index", 0))
        finally:
            self.blockSignals(False)
            self._update_location_ui()

    def add_files(self, file_paths):
        existing = set(self.file_list.item(i).text() for i in range(self.file_list.count()))
        for path in file_paths:
            ext = os.path.splitext(path)[1].lower()
            if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp']:
                if path not in existing:
                    self.file_list.addItem(path)
                    existing.add(path)
        self._on_settings_changed() # 새 파일이 들어오면 미리보기 갱신

    # 창 크기 조절 시 미리보기 이미지 리사이징 대응
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._on_settings_changed()
