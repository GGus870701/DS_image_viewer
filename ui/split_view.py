"""
DS Image Viewer — 화면 분할 뷰 (QSplitter)
두 개의 ImageViewport를 좌우로 배치
"""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QSplitter, QFrame, QSplitterHandle
from PySide6.QtCore import Qt, Signal

from ui.image_viewport import ImageViewport


class ResettableSplitterHandle(QSplitterHandle):
    """더블 클릭 시 1:1 비율로 리셋하는 핸들"""
    def mouseDoubleClickEvent(self, event):
        splitter = self.splitter()
        total = sum(splitter.sizes())
        half = total // 2
        splitter.setSizes([half, total - half])
        super().mouseDoubleClickEvent(event)


class ResettableSplitter(QSplitter):
    """커스텀 핸들을 사용하는 스플리터"""
    def createHandle(self):
        return ResettableSplitterHandle(self.orientation(), self)


class SplitView(QWidget):
    """
    좌우 두 개의 이미지를 비교할 수 있는 분할 뷰 컨테이너.
    
    Signals:
        active_changed(str): 'left' 또는 'right' 뷰포트가 선택되었을 때
    """
    active_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_side = "left"
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.splitter = ResettableSplitter(Qt.Horizontal)
        
        # 왼쪽 컨테이너 (포커스 테두리용)
        self.left_container = QFrame()
        self.left_container.setFrameShape(QFrame.NoFrame)
        self.left_layout = QHBoxLayout(self.left_container)
        self.left_layout.setContentsMargins(2, 2, 2, 2)
        self.left_viewport = ImageViewport()
        self.left_layout.addWidget(self.left_viewport)
        
        # 오른쪽 컨테이너
        self.right_container = QFrame()
        self.right_container.setFrameShape(QFrame.NoFrame)
        self.right_layout = QHBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(2, 2, 2, 2)
        self.right_viewport = ImageViewport()
        self.right_layout.addWidget(self.right_viewport)

        self.splitter.addWidget(self.left_container)
        self.splitter.addWidget(self.right_container)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        
        layout.addWidget(self.splitter)

        # 포커스 이벤트 필터 설치
        self.left_viewport.installEventFilter(self)
        self.right_viewport.installEventFilter(self)
        
        # 초기 강조
        self._update_focus_style()

    def eventFilter(self, obj, event):
        if event.type() == event.Type.MouseButtonPress:
            if obj == self.left_viewport:
                self.set_active("left")
            elif obj == self.right_viewport:
                self.set_active("right")
        return super().eventFilter(obj, event)

    def set_active(self, side: str):
        if self._active_side != side:
            self._active_side = side
            self._update_focus_style()
            self.active_changed.emit(side)

    def get_active_viewport(self) -> ImageViewport:
        return self.left_viewport if self._active_side == "left" else self.right_viewport

    def _update_focus_style(self):
        """활성화된 뷰포트에 파란색 테두리 강조"""
        active_style = "border: 2px solid #00B4D8; border-radius: 2px;"
        inactive_style = "border: 2px solid transparent;"
        
        self.left_container.setStyleSheet(active_style if self._active_side == "left" else inactive_style)
        self.right_container.setStyleSheet(active_style if self._active_side == "right" else inactive_style)

    def sync_views(self):
        """(옵션) 좌우 뷰의 줌/팬 동기화 (추후 필요 시 구현)"""
        pass
