from abc import ABC, abstractmethod

class BasePlugin(ABC):
    name: str = ""
    
    @abstractmethod
    def on_activate(self, app, document_path: str, page_index: int = 0):
        """플러그인 기능 실행 시 호출되는 메서드"""
        pass
    
    def register_menu(self) -> dict:
        """메뉴에 등록할 항목 정보를 반환 (예: {"label": "AI 요약", "command": self.on_activate})"""
        return {}

    def on_image_change(self, app, document_path: str):
        """이미지가 변경될 때 호출 (실시간 업데이트가 필요한 플러그인용)"""
        pass

    def on_embed(self, app, parent_frame):
        """메인 윈도우의 특정 프레임에 UI를 삽입할 때 호출"""
        pass

    def handle_file(self, path: str):
        """특정 파일 형식을 로드하여 PIL Image 객체로 반환. 지원하지 않으면 None 반환."""
        return None

    def render_viewport(self, path, width, height, zoom, off_x, off_y):
        """[선택 사항] 현재 뷰포트에 맞춰 고화질로 재렌더링 (벡터 포맷용)"""
        return None
