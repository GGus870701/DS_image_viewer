import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import os
import time
import subprocess
from PIL import Image
from PIL.ExifTags import TAGS

# plugin_interface에서 BasePlugin 임포트
from core.plugin_interface import BasePlugin

class ImageInfoPlugin(BasePlugin):
    name = "이미지 상세 정보"
    
    def __init__(self):
        self.info_window = None
        self.app = None
        self.info_labels = {}
        self.current_path = None
        self.embedded_frame = None
    
    def on_activate(self, app, document_path, page_index=0):
        """플러그인 활성화 (독립 창 방식)"""
        self.app = app
        self.current_path = document_path
        
        if self.info_window and self.info_window.winfo_exists():
            self.info_window.focus_force()
        else:
            self.info_window = ctk.CTkToplevel(self.app)
            self.info_window.title(self.name)
            self.info_window.geometry("400x600")
            self.info_window.attributes("-topmost", True)
            self.setup_ui(self.info_window)
        
        self.update_info(document_path)

    def on_embed(self, app, parent_frame):
        """플러그인 임베드 (사이드바 방식)"""
        self.app = app
        self.embedded_frame = parent_frame
        
        # 기존 내용물 삭제
        for widget in parent_frame.winfo_children():
            widget.destroy()
            
        self.setup_ui(parent_frame)
        self.update_info(self.app.current_image_path)

    def on_image_change(self, app, document_path):
        """이미지 변경 시 정보 업데이트"""
        self.app = app
        self.current_path = document_path
        # 독립 창이나 임베드 프레임이 있는 경우 모두 업데이트
        if (self.info_window and self.info_window.winfo_exists()) or self.embedded_frame:
            self.update_info(document_path)

    def setup_ui(self, parent):
        label_title = ctk.CTkLabel(parent, text="이미지 정보", font=("Malgun Gothic", 16, "bold"), text_color="#00d2d3")
        label_title.pack(pady=20)
        
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=5)
        scroll.columnconfigure(1, weight=1)
        
        items = ["파일명", "위치", "해상도", "파일크기", "촬영일시", "카메라", "위도", "경도", "고도", "생성일시", "수정일시"]
        self.info_labels = {}
        
        for i, item in enumerate(items):
            lbl_key = ctk.CTkLabel(scroll, text=item, font=("Malgun Gothic", 12, "bold"), text_color="#a4b0be", width=150, anchor="w")
            lbl_key.grid(row=i, column=0, padx=5, pady=8, sticky="nw")
            
            lbl_val = ctk.CTkLabel(scroll, text="-", font=("Malgun Gothic", 12), text_color="white", anchor="w", justify="left", cursor="hand2", wraplength=400)
            lbl_val.grid(row=i, column=1, padx=5, pady=8, sticky="nw")
            
            if item == "파일명":
                lbl_val.bind("<Button-1>", lambda e: self.rename_file())
                lbl_val.configure(text_color="#00d2d3")
            elif item == "위치":
                lbl_val.bind("<Button-1>", lambda e: self.open_in_explorer())
                lbl_val.configure(text_color="#00d2d3")
            else:
                lbl_val.bind("<Button-1>", lambda e, v=lbl_val: self.copy_info(v))
            
            self.info_labels[item] = lbl_val

    def update_info(self, path):
        if not path or not os.path.exists(path):
            for lbl in self.info_labels.values(): lbl.configure(text="-")
            return

        try:
            stats = os.stat(path)
            ext = os.path.splitext(path)[1].lower()
            
            # 기본 데이터 (이미지 오픈 전에도 알 수 있는 정보)
            data = {
                "파일명": os.path.basename(path),
                "위치": path,
                "해상도": "정보 없음",
                "파일크기": self.format_size(stats.st_size),
                "촬영일시": "정보 없음",
                "카메라": "정보 없음",
                "위도": "정보 없음",
                "경도": "정보 없음",
                "고도": "정보 없음",
                "생성일시": time.ctime(stats.st_ctime),
                "수정일시": time.ctime(stats.st_mtime)
            }

            # 이미지/CAD 특화 정보 추출
            try:
                if ext in ('.dxf', '.dwg'):
                    # CAD 파일의 경우 메인 앱의 플러그인 결과물에서 크기 정보 유추 시도
                    if hasattr(self.app, 'current_img') and self.app.current_img:
                        w, h = self.app.current_img.size
                        data["해상도"] = f"{w} x {h} (CAD)"
                else:
                    # 일반 이미지
                    img = Image.open(path)
                    w, h = img.size
                    data["해상도"] = f"{w} x {h}"
                    
                    exif = self.get_exif_data(img)
                    if exif:
                        data["촬영일시"] = exif.get('DateTime', '정보 없음')
                        data["카메라"] = exif.get('Model', '정보 없음')
                        data["위도"] = exif.get('Lat', '정보 없음')
                        data["경도"] = exif.get('Lon', '정보 없음')
                        data["고도"] = exif.get('Alt', '정보 없음')
            except:
                pass # 특정 포맷 로드 실패 시 기본 정보만 유지

            for key, val in data.items():
                if key in self.info_labels:
                    self.info_labels[key].configure(text=val)
        except Exception as e:
            print(f"Info update error: {e}")

    def format_size(self, bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024: return f"{bytes:.1f} {unit}"
            bytes /= 1024
        return f"{bytes:.1f} TB"

    def rename_file(self):
        # 현재 활성 경로 사용
        path = self.app.current_image_path
        if not path: return
        base_name, ext = os.path.splitext(os.path.basename(path))
        
        dialog = ctk.CTkInputDialog(text="새 파일명을 입력하세요:", title="파일명 수정")
        new_base = dialog.get_input()
        
        if new_base and new_base != base_name:
            try:
                new_path = os.path.join(os.path.dirname(path), new_base + ext)
                os.rename(path, new_path)
                
                # 히스토리 저장 (Undo용)
                self.app.rename_history.append((path, new_path))
                
                # 메인 앱 상태 업데이트
                self.app.current_image_path = new_path
                self.app.update_image_list(new_path)
                self.app.load_image(new_path)
                messagebox.showinfo("성공", f"파일명이 변경되었습니다.")
            except Exception as e:
                messagebox.showerror("오류", f"변경 실패: {e}")

    def open_in_explorer(self):
        path = self.app.current_image_path
        if not path: return
        try:
            path = os.path.normpath(path)
            subprocess.Popen(f'explorer /select,"{path}"')
        except Exception as e:
            messagebox.showerror("오류", f"탐색기 열기 실패: {e}")

    def copy_info(self, label_obj):
        text = label_obj.cget("text")
        if text and text not in ["-", "정보 없음"]:
            self.app.clipboard_clear()
            self.app.clipboard_append(text)
            orig = label_obj.cget("text_color")
            label_obj.configure(text_color="#00d2d3")
            self.app.after(200, lambda: label_obj.configure(text_color=orig))

    def get_exif_data(self, img_obj):
        info = {}
        try:
            exif = img_obj._getexif()
            if exif:
                for tag, value in exif.items():
                    decoded = TAGS.get(tag, tag)
                    if decoded == "GPSInfo":
                        lat_val, lat_dms = self.get_decimal_from_dms(value.get(2), value.get(1))
                        lon_val, lon_dms = self.get_decimal_from_dms(value.get(4), value.get(3))
                        info['Lat'] = f"{lat_dms} ({lat_val:.6f}°)" if lat_val is not None else "정보 없음"
                        info['Lon'] = f"{lon_dms} ({lon_val:.6f}°)" if lon_val is not None else "정보 없음"
                        info['Lat_Val'] = lat_val
                        info['Lon_Val'] = lon_val
                        alt = value.get(6)
                        if alt is not None:
                            if hasattr(alt, 'numerator'): alt = float(alt.numerator) / alt.denominator
                            info['Alt'] = f"{float(alt):.2f} m"
                    elif decoded in ["DateTimeOriginal", "DateTime", "Model"]:
                        info[decoded if decoded != "DateTimeOriginal" else "DateTime"] = value
        except: pass
        return info

    def get_decimal_from_dms(self, dms, ref):
        if not dms or not ref: return None, ""
        try:
            decimal = float(dms[0]) + float(dms[1]) / 60.0 + float(dms[2]) / 3600.0
            if ref in ['S', 'W']: decimal = -decimal
            return decimal, f"{int(dms[0])}° {int(dms[1])}' {float(dms[2]):.2f}\""
        except: return None, ""

    def register_menu(self):
        return {"label": "ℹ️ 이미지 상세 정보", "command": self.on_activate}
