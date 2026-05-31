"""
DS Image Viewer — 이미지 파일 목록 관리 및 탐색
TIF Stack 다중 프레임 지원 포함
"""
import os
import re

from PySide6.QtCore import QObject, Signal

# 지원 확장자
SUPPORTED_EXTS = ('.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp')


def _natural_sort_key(s: str):
    """파일명 자연 정렬 키 (숫자 포함 파일명 올바르게 정렬)"""
    return [int(c) if c.isdigit() else c.lower()
            for c in re.split(r'(\d+)', os.path.basename(s))]


class ImageModel(QObject):
    """
    현재 폴더의 이미지 목록 관리, 탐색, TIF Stack 처리.

    Signals:
        list_changed(list)  : 이미지 목록 변경 시
        index_changed(int)  : 현재 인덱스 변경 시
        rename_done(str, str): 이름 변경 완료 시 (old_path, new_path)
    """
    list_changed  = Signal(list)
    index_changed = Signal(int)
    rename_done   = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._files: list[str] = []
        self._index: int = -1
        self._rename_history: list[tuple[str, str]] = []  # (before, after)

    # ──────────────────────────────────────────────
    # 목록 관리
    # ──────────────────────────────────────────────
    def scan_folder(self, path: str):
        """주어진 파일/폴더 기준으로 동일 폴더 내 이미지 목록 스캔"""
        if os.path.isfile(path):
            folder = os.path.dirname(path)
            target = path
        else:
            folder = path
            target = None

        try:
            files = [
                os.path.join(folder, f)
                for f in os.listdir(folder)
                if f.lower().endswith(SUPPORTED_EXTS)
            ]
            self._files = sorted(files, key=_natural_sort_key)
        except Exception:
            self._files = [target] if target else []

        if target and target in self._files:
            self._index = self._files.index(target)
        elif self._files:
            self._index = 0
        else:
            self._index = -1

        self.list_changed.emit(self._files)
        if self._index >= 0:
            self.index_changed.emit(self._index)

    @property
    def files(self) -> list[str]:
        return self._files

    @property
    def index(self) -> int:
        return self._index

    @property
    def count(self) -> int:
        return len(self._files)

    # ──────────────────────────────────────────────
    # 탐색
    # ──────────────────────────────────────────────
    def current(self) -> str | None:
        if 0 <= self._index < len(self._files):
            return self._files[self._index]
        return None

    def go_to(self, index: int) -> str | None:
        if not self._files:
            return None
        self._index = index % len(self._files)
        self.index_changed.emit(self._index)
        return self.current()

    def next(self) -> str | None:
        return self.go_to(self._index + 1)

    def prev(self) -> str | None:
        return self.go_to(self._index - 1)

    # ──────────────────────────────────────────────
    # 파일 이름 변경 (Undo 스택)
    # ──────────────────────────────────────────────
    def rename_current(self, new_name: str) -> bool:
        """현재 파일의 이름을 변경. 성공 시 True 반환."""
        old_path = self.current()
        if not old_path:
            return False
        folder = os.path.dirname(old_path)
        new_path = os.path.join(folder, new_name)
        try:
            os.rename(old_path, new_path)
            self._rename_history.append((old_path, new_path))
            self._files[self._index] = new_path
            self.rename_done.emit(old_path, new_path)
            return True
        except Exception as e:
            print(f"[ImageModel] 이름 변경 실패: {e}")
            return False

    def undo_rename(self) -> bool:
        """마지막 이름 변경 취소. 성공 시 True 반환."""
        if not self._rename_history:
            return False
        old_path, new_path = self._rename_history.pop()
        try:
            os.rename(new_path, old_path)
            if new_path in self._files:
                idx = self._files.index(new_path)
                self._files[idx] = old_path
                if self._index == idx:
                    self.rename_done.emit(new_path, old_path)
            return True
        except Exception as e:
            print(f"[ImageModel] 이름 변경 취소 실패: {e}")
            return False

    def update_image_path(self, old_path: str, new_path: str) -> bool:
        """외부(예: 정보 패널)에서 파일명이 변경된 경우 목록을 동기화"""
        if old_path in self._files:
            idx = self._files.index(old_path)
            self._files[idx] = new_path
            self._rename_history.append((old_path, new_path))
            if self._index == idx:
                self.rename_done.emit(old_path, new_path)
            return True
        return False

    # ──────────────────────────────────────────────
    # TIF Stack 헬퍼
    # ──────────────────────────────────────────────
    @staticmethod
    def get_frame_count(path: str) -> int:
        """TIF 파일의 총 프레임 수 반환 (TIF가 아니거나 단일 프레임이면 1)"""
        if not path or not path.lower().endswith(('.tif', '.tiff')):
            return 1
        try:
            from PIL import Image
            with Image.open(path) as img:
                return getattr(img, 'n_frames', 1)
        except Exception:
            return 1
