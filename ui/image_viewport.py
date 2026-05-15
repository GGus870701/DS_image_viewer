"""
DS Image Viewer — QGraphicsView 기반 고성능 이미지 뷰어 위젯

핵심 설계:
  - QGraphicsView + QGraphicsScene + QGraphicsPixmapItem
  - 마우스 앵커 줌 (Ctrl + 휠)
  - 드래그 팬 (Qt 내장 ScrollHandDrag)
  - QTransform 기반 회전/반전 (회전 후 자동 Fit)
  - 로드 시 초기 줌: 이미지 <= 뷰포트 → 1:1, 그 외 → Fit
  - TIF Stack: 다중 프레임 탐색 (PageUp/Down, 슬라이더)
"""
import os
from PIL import Image

from PySide6.QtWidgets import (QGraphicsView, QGraphicsScene,
                                QGraphicsPixmapItem, QSizePolicy)
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QTransform, QWheelEvent, QBrush
from PySide6.QtCore import Qt, Signal, QTimer, QPointF


def _pil_to_qpixmap(img: Image.Image) -> QPixmap:
    """PIL Image → QPixmap 변환 (RGBA 안전 처리)"""
    if img.mode not in ('RGB', 'RGBA'):
        img = img.convert('RGBA')
    data = img.tobytes('raw', img.mode)
    fmt = QImage.Format.Format_RGBA8888 if img.mode == 'RGBA' else QImage.Format.Format_RGB888
    qimg = QImage(data, img.width, img.height, fmt)
    return QPixmap.fromImage(qimg)


class ImageViewport(QGraphicsView):
    """
    고성능 이미지 뷰어 위젯.

    Signals:
        zoom_changed(float)   : 줌 배율 변경 시 (0.1 = 10%)
        image_loaded(str)     : 이미지 로드 완료 시 (파일 경로)
        load_failed(str)      : 이미지 로드 실패 시 (에러 메시지)
        frame_changed(int, int): TIF 프레임 변경 시 (current, total)
    """
    zoom_changed   = Signal(float)
    image_loaded   = Signal(str)
    load_failed    = Signal(str)
    frame_changed  = Signal(int, int)
    view_changed   = Signal(object, object)  # view_rect, scene_rect

    # 줌 범위
    MIN_ZOOM = 0.01   # 1%
    MAX_ZOOM = 50.0   # 5000%
    ZOOM_FACTOR = 1.15

    def __init__(self, parent=None):
        super().__init__(parent)

        # ── 씬 설정 ──────────────────────────────
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item = QGraphicsPixmapItem()
        self._pixmap_item.setTransformationMode(Qt.SmoothTransformation)
        self._scene.addItem(self._pixmap_item)

        # ── 렌더링 품질 ──────────────────────────
        self.setRenderHints(
            QPainter.Antialiasing |
            QPainter.SmoothPixmapTransform |
            QPainter.TextAntialiasing
        )
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setBackgroundBrush(QBrush(QColor("#1e272e")))
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # ── 상태 변수 ─────────────────────────────
        self._current_path: str = ""
        self._pil_img: Image.Image | None = None
        self._rotation: int = 0        # 0, 90, 180, 270
        self._flipped: bool = False
        self._frame_index: int = 0
        self._frame_count: int = 1

        # 고화질 지연 렌더링 타이머 (팬 중 빠른 렌더 → 정지 후 고화질)
        self._hq_timer = QTimer(self)
        self._hq_timer.setSingleShot(True)
        self._hq_timer.setInterval(120)
        self._hq_timer.timeout.connect(self._apply_hq_render)

    # ──────────────────────────────────────────────────────────
    # 퍼블릭 API
    # ──────────────────────────────────────────────────────────
    def load_image(self, path: str, frame_index: int = 0) -> bool:
        """이미지 파일 로드. 성공 시 True."""
        if not path or not os.path.isfile(path):
            self.load_failed.emit(f"파일을 찾을 수 없습니다: {path}")
            return False
        try:
            img = Image.open(path)
            self._frame_count = getattr(img, 'n_frames', 1)
            self._frame_index = max(0, min(frame_index, self._frame_count - 1))

            # TIF Stack: 특정 프레임 선택
            if self._frame_count > 1:
                img.seek(self._frame_index)
                self.frame_changed.emit(self._frame_index, self._frame_count)

            # 모드 통일 (EXIF 회전 포함)
            img = self._normalize_pil(img)

            self._pil_img = img
            self._current_path = path
            self._rotation = 0
            self._flipped = False

            self._update_pixmap()
            self._apply_initial_zoom()

            self.image_loaded.emit(path)
            return True
        except Exception as e:
            self.load_failed.emit(str(e))
            return False

    def load_frame(self, frame_index: int):
        """TIF Stack 특정 프레임으로 이동"""
        if self._frame_count <= 1 or not self._current_path:
            return
        self.load_image(self._current_path, frame_index)

    def fit_in_view(self):
        """이미지를 뷰포트에 맞춤"""
        if not self._pil_img:
            return
        self.resetTransform()
        item_rect = self._pixmap_item.boundingRect()
        if item_rect.isEmpty():
            return
        super().fitInView(item_rect, Qt.KeepAspectRatio)
        self.zoom_changed.emit(self._get_zoom_scale())

    def set_zoom(self, scale: float):
        """절대 줌 배율 설정 (1.0 = 100%)"""
        scale = max(self.MIN_ZOOM, min(self.MAX_ZOOM, scale))
        self.resetTransform()
        self.scale(scale, scale)
        self.zoom_changed.emit(scale)

    def get_zoom_percent(self) -> int:
        """현재 줌 배율을 정수 퍼센트로 반환"""
        return int(self._get_zoom_scale() * 100)

    def rotate_cw(self):
        """시계 방향 90° 회전 → 자동 Fit"""
        self._rotation = (self._rotation + 90) % 360
        self._update_pixmap()
        self.fit_in_view()

    def rotate_ccw(self):
        """반시계 방향 90° 회전 → 자동 Fit"""
        self._rotation = (self._rotation - 90) % 360
        self._update_pixmap()
        self.fit_in_view()

    def flip_horizontal(self):
        """좌우 반전 토글"""
        self._flipped = not self._flipped
        self._update_pixmap()

    def reset_view(self):
        """줌/회전/반전 초기화 → Fit"""
        self._rotation = 0
        self._flipped = False
        self._update_pixmap()
        self.fit_in_view()

    @property
    def current_path(self) -> str:
        return self._current_path

    @property
    def frame_count(self) -> int:
        return self._frame_count

    @property
    def frame_index(self) -> int:
        return self._frame_index

    def get_view_rect(self):
        """현재 가시 영역(Scene 좌표계) 반환"""
        return self.mapToScene(self.viewport().rect()).boundingRect()

    def get_scene_rect(self):
        """전체 씬 영역 반환"""
        return self.sceneRect()

    # ──────────────────────────────────────────────────────────
    # 이벤트 처리
    # ──────────────────────────────────────────────────────────
    def wheelEvent(self, event: QWheelEvent):
        """Ctrl + 휠: 마우스 기준 줌 / 기본 휠: 무시(팬으로 대체)"""
        if event.modifiers() == Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta == 0:
                return
            factor = self.ZOOM_FACTOR if delta > 0 else 1.0 / self.ZOOM_FACTOR
            new_scale = self._get_zoom_scale() * factor
            if self.MIN_ZOOM <= new_scale <= self.MAX_ZOOM:
                self.scale(factor, factor)
                self.zoom_changed.emit(self._get_zoom_scale())
        else:
            # 휠 스크롤 → 이전/다음 이미지 신호 없음 (MainWindow에서 연결)
            event.ignore()

    def mouseDoubleClickEvent(self, event):
        """더블 클릭: 1:1 ↔ Fit 토글"""
        if not self._pil_img:
            return
        current = self._get_zoom_scale()
        if abs(current - 1.0) < 0.05:
            self.fit_in_view()
        else:
            self.set_zoom(1.0)
            self._center_item()
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event):
        """PageUp/Down: TIF Stack 프레임 탐색"""
        if self._frame_count > 1:
            if event.key() == Qt.Key_PageDown:
                self.load_frame(self._frame_index + 1)
                return
            elif event.key() == Qt.Key_PageUp:
                self.load_frame(self._frame_index - 1)
                return
        super().keyPressEvent(event)

    def resizeEvent(self, event):
        """창 크기 변경 시 현재 뷰 유지 (최초 로드 시 Fit 적용됨)"""
        super().resizeEvent(event)

    # ──────────────────────────────────────────────────────────
    # 내부 헬퍼
    # ──────────────────────────────────────────────────────────
    def _normalize_pil(self, img: Image.Image) -> Image.Image:
        """PIL 이미지를 RGBA/RGB로 통일"""
        if img.mode == 'P':
            img = img.convert('RGBA')
        elif img.mode not in ('RGB', 'RGBA', 'L'):
            img = img.convert('RGB')
        return img.copy()

    def get_thumbnail(self, size: int = 200) -> QPixmap:
        """현재 이미지의 썸네일 픽스맵 반환"""
        if self._pixmap_item.pixmap().isNull():
            return QPixmap()
        return self._pixmap_item.pixmap().scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def _emit_view_changed(self):
        """가시 영역 좌표 정보 계산 후 시그널 발생"""
        if not self._pil_img:
            return
        
        scene_rect = self.sceneRect()
        view_rect = self.mapToScene(self.viewport().rect()).boundingRect()
        self.view_changed.emit(view_rect, scene_rect)

    def scrollContentsBy(self, dx, dy):
        """스크롤(팬) 발생 시 가시 영역 업데이트 알림"""
        super().scrollContentsBy(dx, dy)
        self._emit_view_changed()

    def _apply_transform(self, img: Image.Image) -> Image.Image:
        """회전 및 반전을 PIL 레벨에서 적용한 새 이미지 반환"""
        if self._rotation != 0:
            img = img.rotate(-self._rotation, expand=True)
        if self._flipped:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        return img

    def _update_pixmap(self):
        """변환(회전/반전) 적용 후 QGraphicsScene 픽스맵 갱신"""
        if self._pil_img is None:
            return
        transformed = self._apply_transform(self._pil_img)
        pixmap = _pil_to_qpixmap(transformed)
        self._pixmap_item.setPixmap(pixmap)
        self._scene.setSceneRect(self._pixmap_item.boundingRect())
        self._emit_view_changed()

    def _apply_initial_zoom(self):
        """
        로드 직후 초기 줌 결정:
          이미지 크기 <= 뷰포트 크기 → 1:1 (원본)
          이미지 크기 >  뷰포트 크기 → Fit
        """
        if self._pil_img is None:
            return
        vw = self.viewport().width()
        vh = self.viewport().height()
        iw, ih = self._pil_img.size
        # 회전 상태 고려
        if self._rotation in (90, 270):
            iw, ih = ih, iw
        if iw <= vw and ih <= vh:
            self.set_zoom(1.0)
            self._center_item()
        else:
            self.fit_in_view()

    def _center_item(self):
        """픽스맵 아이템을 뷰포트 중앙에 배치"""
        self.centerOn(self._pixmap_item)

    def _get_zoom_scale(self) -> float:
        """현재 변환 행렬에서 스케일 팩터 추출"""
        t = self.transform()
        return t.m11()  # 회전 없을 때 수평 스케일 = 실제 배율

    def _apply_hq_render(self):
        """고화질 렌더 (타이머 콜백 — 현재는 Qt가 자동 처리)"""
        self.viewport().update()
