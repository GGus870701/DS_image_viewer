"""
DS Image Viewer — 네비게이터 (미니맵)
뷰포트 우측 상단에 플로팅되는 맵 위젯.
확대 시 노출되며 현재 보고 있는 영역을 빨간 사각형으로 표시.
"""
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtGui import QPainter, QColor, QPen, QPixmap
from PySide6.QtCore import Qt, QRectF, QSize


class NavigatorWidget(QWidget):
    """
    미니맵 오버레이 위젯.
    ImageViewport의 transform 시그널을 받아 실시간으로 뷰 영역 표시.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(180, 140)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)  # 클릭 관통
        self.setStyleSheet("background-color: rgba(10, 18, 32, 180); border: 1px solid #3A4A64; border-radius: 4px;")
        
        self._pixmap: QPixmap | None = None
        self._view_rect = QRectF()  # 0~1 사이의 상대 좌표 (전체 대비 현재 뷰 비율)
        
        # 아직 이미지가 없거나 줌이 100% 이하면 숨김 처리할 수 있도록 설계
        self.hide()

    def set_thumbnail(self, pixmap: QPixmap):
        """이미지 로드 시 썸네일 업데이트"""
        if pixmap.isNull():
            self._pixmap = None
            self.hide()
            return
        
        # 위젯 크기에 맞게 스케일링 (비율 유지)
        self._pixmap = pixmap.scaled(
            self.width() - 10, self.height() - 10,
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.update()

    def update_view(self, view_rect: QRectF, scene_rect: QRectF):
        """
        현재 뷰포트의 가시 영역 정보를 받아 빨간 사각형 업데이트.
        rect는 씬 좌표계 기준.
        """
        if scene_rect.width() == 0 or scene_rect.height() == 0:
            return

        # 전체 씬 대비 가시 영역의 비율 계산
        x = view_rect.left() / scene_rect.width()
        y = view_rect.top() / scene_rect.height()
        w = view_rect.width() / scene_rect.width()
        h = view_rect.height() / scene_rect.height()
        
        self._view_rect = QRectF(x, y, w, h)
        
        # 가시 영역 비율 (w, h: 0~1)
        # 전체 이미지(Scene)가 뷰포트 안에 다 들어오면 (w, h >= 1.0) 숨김
        # 미세한 오차를 고려하여 0.99 기준으로 처리
        if w >= 0.99 and h >= 0.99:
            self.hide()
        elif self._pixmap and not self._pixmap.isNull():
            self.show()
            self.update()
        else:
            self.hide()

    def paintEvent(self, event):
        if not self._pixmap:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 1. 썸네일 그리기 (중앙 배치)
        tx = (self.width() - self._pixmap.width()) / 2
        ty = (self.height() - self._pixmap.height()) / 2
        painter.drawPixmap(tx, ty, self._pixmap)
        
        # 2. 가시 영역 사각형 그리기
        if not self._view_rect.isNull():
            # 썸네일 좌표계로 변환
            rx = tx + self._view_rect.x() * self._pixmap.width()
            ry = ty + self._view_rect.y() * self._pixmap.height()
            rw = self._view_rect.width() * self._pixmap.width()
            rh = self._view_rect.height() * self._pixmap.height()
            
            # 클리핑 (썸네일 영역 밖으로 나가지 않게)
            draw_rect = QRectF(rx, ry, rw, rh).intersected(QRectF(tx, ty, self._pixmap.width(), self._pixmap.height()))
            
            painter.setPen(QPen(QColor(238, 82, 83), 2)) # #ee5253 (강조색)
            painter.drawRect(draw_rect)
            
        painter.end()
