"""
DS Image Viewer — 설정 관리
settings.json 로드/저장 (DS_capture 패턴 채택)
"""
import os
import json
import sys

_MAX_RECENT = 10


def _get_base_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(sys.argv[0]))


_CONFIG_FILE = os.path.join(_get_base_dir(), "settings.json")

_DEFAULTS = {
    "recent_files": [],
    "last_open_dir": "",
    "theme": "dark",
    "zoom_policy": "auto",          # "auto" = origin/fit 자동, "fit" = 항상 fit
    "navigator_enabled": True,
    "split_ratio": 0.5,
    "convert_settings": {
        "rotation_mode": 4,  # EXIF Auto
        "resize_mode": 1,    # Keep Aspect
        "target_width": 640,
        "target_height": 480,
        "format_idx": 0,     # Original
        "quality": 80,
        "preserve_exif": True,
        "loc_mode": 2,       # Subfolder
        "specific_dir": "",
        "subfolder_name": "output",
        "conflict_mode": 0,  # Rename
        "use_prefix": False,
        "prefix_str": ""
    }
}


class _Settings:
    def __init__(self):
        self._data: dict = {}
        self.load()

    def load(self):
        try:
            if os.path.exists(_CONFIG_FILE):
                with open(_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
            else:
                self._data = dict(_DEFAULTS)
        except Exception:
            self._data = dict(_DEFAULTS)

    def save(self):
        try:
            with open(_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Settings] 저장 실패: {e}")

    def get(self, key: str, default=None):
        return self._data.get(key, _DEFAULTS.get(key, default))

    def set(self, key: str, value):
        self._data[key] = value
        self.save()

    def add_recent_file(self, path: str):
        """최근 파일 목록에 추가 (중복 제거, 최대 10개)"""
        recent = self._data.get("recent_files", [])
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        self._data["recent_files"] = recent[:_MAX_RECENT]
        self.save()


# 싱글톤 인스턴스
settings = _Settings()
