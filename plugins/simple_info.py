import tkinter as tk
from tkinter import messagebox
import os

# plugin_interface에서 BasePlugin 임포트
from plugin_interface import BasePlugin

class SimpleInfoPlugin(BasePlugin):
    name = "이미지 정보 플러그인"
    
    def on_activate(self, app, document_path, page_index=0):
        """플러그인 실행 시 현재 이미지 경로를 팝업으로 표시"""
        if not document_path:
            messagebox.showinfo("정보", "열려 있는 이미지가 없습니다.")
            return
            
        filename = os.path.basename(document_path)
        msg = f"파일명: {filename}\n경로: {document_path}\n페이지: {page_index}"
        messagebox.showinfo(self.name, msg)
    
    def register_menu(self):
        """메뉴에 등록할 정보 반환"""
        return {
            "label": "📄 현재 이미지 정보",
            "command": self.on_activate
        }
