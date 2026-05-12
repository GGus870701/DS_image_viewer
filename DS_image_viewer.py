import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk, ImageOps, ImageDraw, ImageFont
import os
import sys
import json
import hmac
import hashlib
import subprocess
import winreg
import ctypes
from ctypes import wintypes
import time
import importlib.util
import glob
import inspect
import gc
import ezdxf             # [중요] 플러그인 종속성 강제 포함
from ezdxf import bbox    # [중요] 플러그인 종속성 강제 포함
import ezdxf.math         # [추가]
import ezdxf.colors       # [추가]
import ezdxf.fonts        # [추가]
import ezdxf.path         # [추가]
import ezdxf.render       # [추가]
from plugin_interface import BasePlugin

# --- [빌드 정보] ---
BUILD_VERSION = "1.00.18"
BUILD_DATE = "2026-05-11"
BUILD_TIME = "21:32:17"

# --- [전역 스타일 설정] ---
UI_FONT_NAME = "Malgun Gothic"
UI_FONT_BOLD = (UI_FONT_NAME, 12, "bold")
UI_FONT_NORMAL = (UI_FONT_NAME, 12)
UI_FONT_SMALL = (UI_FONT_NAME, 10)
UI_FONT_NAV_S = (UI_FONT_NAME, 18, "bold")
UI_FONT_NAV_L = (UI_FONT_NAME, 28, "bold")
UI_FONT_TITLE = (UI_FONT_NAME, 16, "bold")

# 작업표시줄 아이콘 강제 설정 (AppUserModelID)
try:
    myappid = 'ds.imageviewer.v1'
    if hasattr(ctypes.windll.shell32, 'SetCurrentProcessExplicitAppUserModelID'):
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass


# --- [초기 설정] ---
def get_resource_path(relative_path):
    """ 리소스 절대 경로 반환 (PyInstaller 지원) """
    if getattr(sys, 'frozen', False):
        # PyInstaller _MEIPASS 임시 폴더 확인
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(sys.executable)))
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


import datetime # 날짜 계산용 임포트

def set_window_icon(window):
    """모든 Toplevel/Tk/CTk 창에 아이콘 일괄 적용"""
    try:
        ico_path = get_resource_path("ds_viewer_icon.ico")
        if os.path.exists(ico_path):
            window.iconbitmap(ico_path)
    except:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(sys.executable)) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "settings.json")
LICENSE_CENTRAL_DIR = r"C:\license"

# --- [라이센스 시스템] ---
SECRET_KEY = "DS_CAPTURE_SECRET_KEY_2026_@!" # DS 계열 공통 키 사용

def get_hwid():
    """기기 고유 정보를 조합하여 해싱된 HWID 생성 (첫 번째 장치 기반 동기화)"""
    try:
        cmd_mb = 'powershell "Get-CimInstance -ClassName Win32_BaseBoard | Select-Object -ExpandProperty SerialNumber"'
        mb_serial = subprocess.check_output(cmd_mb, shell=True).decode('cp949').strip().splitlines()[0].strip()
        cmd_disk = 'powershell "Get-CimInstance -ClassName Win32_DiskDrive | Select-Object -ExpandProperty SerialNumber"'
        disk_serial = subprocess.check_output(cmd_disk, shell=True).decode('cp949').strip().splitlines()[0].strip()
        raw_id = f"DS_{mb_serial}_{disk_serial}"
        hash_id = hashlib.sha256(raw_id.encode()).hexdigest().upper()
        return f"{hash_id[:4]}-{hash_id[4:8]}-{hash_id[8:12]}"
    except:
        return "ERR-UNKNOWN"

def check_license(app_name):
    from datetime import datetime
    hwid = get_hwid()
    target_folders = [LICENSE_CENTRAL_DIR, BASE_DIR]
    fail_reason = ""

    for folder in target_folders:
        if not os.path.exists(folder): continue
        try:
            files = os.listdir(folder)
            for filename in files:
                if not filename.lower().endswith(".lic"): continue
                path = os.path.join(folder, filename)
                with open(path, 'r', encoding='utf-8-sig') as f:
                    data_raw = json.load(f)
                
                # [수정] 복수 라이센스 지원 (리스트 형태 처리)
                license_list = data_raw if isinstance(data_raw, list) else [data_raw]
                
                for data in license_list:
                    if data.get('hwid') != hwid: continue
                    if data.get('app_name') != app_name:
                        fail_reason = f"해당 라이센스는 {data.get('app_name')}용입니다."
                        continue
                    
                    user_name = data.get('user_name')
                    expiry_str = data.get('expiry_date')
                    if not user_name or not expiry_str: continue
                    
                    msg = f"{str(data['hwid'])}{str(data['app_name'])}{str(expiry_str)}{str(user_name)}"
                    expected_signature = hmac.new(SECRET_KEY.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256).hexdigest()
                    
                    if data.get('signature') != expected_signature:
                        fail_reason = "라이센스 서명이 올바르지 않습니다."
                        continue
                    
                    if expiry_str != "PERMANENT":
                        expiry = datetime.strptime(expiry_str, "%Y-%m-%d")
                        if datetime.now() > expiry:
                            fail_reason = f"라이센스가 만료되었습니다. ({expiry_str})"
                            continue
                    return True, data
        except: continue
    return False, fail_reason

def show_license_error(hwid, message):
    error_root = ctk.CTk()
    error_root.title("라이센스 인증 필요")
    set_window_icon(error_root)
    error_root.geometry("450x300")
    ctk.set_appearance_mode("dark")
    
    ctk.CTkLabel(error_root, text="라이센스 인증이 필요합니다.", text_color="#ff4757", font=UI_FONT_TITLE).pack(pady=(30, 10))
    ctk.CTkLabel(error_root, text=message, font=UI_FONT_SMALL, wraplength=400).pack(pady=5)
    ctk.CTkLabel(error_root, text=f"기기 고유 ID: {hwid}", text_color="#00d2d3", font=UI_FONT_BOLD).pack(pady=15)
    
    def copy_id():
        error_root.clipboard_clear()
        error_root.clipboard_append(hwid)
        from tkinter import messagebox
        messagebox.showinfo("복사 완료", "기기 ID가 복사되었습니다.")
        
    ctk.CTkButton(error_root, text="기기 ID 복사하기", font=UI_FONT_BOLD, command=copy_id, fg_color="#4b6584").pack(pady=10)
    ctk.CTkButton(error_root, text="종료", font=UI_FONT_BOLD, command=sys.exit, fg_color="transparent", border_width=1).pack(pady=5)
    
    error_root.mainloop()

# --- [메인 애플리케이션] ---
class ImageViewer(ctk.CTk):
    def __init__(self, license_data):
        super().__init__()
        set_window_icon(self)
        self.license_data = license_data
        
        # UI 설정
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        user_info = self.license_data.get('user_name', 'Free User')
        self.title(f"DS Image Viewer {BUILD_VERSION} - [{user_info}]")
        
        # 아이콘 설정
        icon_path = get_resource_path("ds_viewer_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except:
                pass
        
        # 해상도 기반 최대화 설정
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        self.geometry(f"{int(screen_w*0.6)}x{int(screen_h*0.6)}")
        self.after(0, lambda: self.state('zoomed')) # 시작 시 최대화
        
        # 상태 변수
        self.current_image_path = None
        self.nav_thumb_cache = {} # {(path, size): photo}
        self.max_nav_cache = 5     # 캐시 최대 개수 제한
        self.nav_img_id = None
        self.last_zoom_level = 1.0 # 이전 배율 저장용
        self.zoom_mode = "1:1"    # "1:1" 또는 "fit"
        self.image_list = []      # 현재 폴더의 이미지 리스트
        self.current_index = -1   # 현재 이미지의 인덱스
        self.show_info_panel = False # 정보 패널 표시 여부
        self.rename_history = []  # 이름 변경 히스토리 (Undo용)
        self.split_mode = False   # 화면 분할 모드 여부
        self.second_img = None    # 분할 모드용 두 번째 이미지
        self.right_index = -1     # 분할 모드 오른쪽 인덱스
        self.active_split = "left" # 최근 클릭한 분할 화면 ("left" or "right")
        
        # 이미지 조작용 상태 변수 (단일 모드용)
        self.zoom_level = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
        # 분할 모드 전용 독립 조작 변수 (좌/우)
        self.l_zoom = 1.0; self.l_off_x = 0; self.l_off_y = 0; self.l_mode = "fit"
        self.r_zoom = 1.0; self.r_off_x = 0; self.r_off_y = 0; self.r_mode = "fit"
        
        # 회전 및 반전 상태 변수
        self.rotation = 0       # 단일 모드 회전 각도 (0, 90, 180, 270)
        self.flip = False       # 단일 모드 좌우 반전 여부
        self.l_rot = 0; self.r_rot = 0
        self.l_flip = False; self.r_flip = False
        self.center_on_next_render = False # 중앙 정렬 예약용
        
        # 성능 최적화용 캐시
        self.nav_thumb_cache = {} # {path: (photo, nw, nh)}
        self.processed_img_l = None # 회전/반전이 적용된 캐시 이미지 (좌)
        self.processed_img_r = None # 회전/반전이 적용된 캐시 이미지 (우)
        self.processed_img_main = None # 회전/반전이 적용된 캐시 이미지 (단일)
        self.last_rot_state = None # 마지막으로 처리된 회전 상태 저장
        
        self.is_panning = False
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.dxf_obj_color_mode = "original" # "original", "black", "white"
        
        # 성능 최적화용 상태 변수
        self.render_timer = None # 고화질 전환 예약용
        self.last_pan_render_time = 0 # 드래그 렌더링 시간 제어용
        self.main_img_id = None  # 메인 캔버스 이미지 아이템 ID
        self.l_img_id = None     # 왼쪽 캔버스 이미지 아이템 ID
        self.r_img_id = None     # 오른쪽 캔버스 이미지 아이템 ID
        self.nav_img_id = None   # 미니맵 이미지 아이템 ID
        self.nav_rect_id = None  # 미니맵 사각형 아이템 ID
        
        # 플러그인 관리
        self.plugins = []
        self.load_plugins()
        
        self.setup_ui()
        
        # 인자로 파일이 넘어온 경우 (연결 프로그램 실행)
        if len(sys.argv) > 1:
            self.load_image(sys.argv[1])

    def setup_ui(self):
        # 상단 메뉴 영역 (프레임)
        self.menu_frame = ctk.CTkFrame(self, height=40, corner_radius=0)
        self.menu_frame.pack(side="top", fill="x")
        
        self.btn_open = ctk.CTkButton(self.menu_frame, text="파일 열기", width=100, height=32, font=UI_FONT_BOLD, command=self.open_file)
        self.btn_open.pack(side="left", padx=10, pady=5)

        self.btn_split = ctk.CTkButton(self.menu_frame, text="화면 분할", width=100, height=32, font=UI_FONT_BOLD, command=self.toggle_split_mode)
        self.btn_split.pack(side="left", padx=5, pady=5)

        # 화면 맞춤 버튼을 화면 분할과 회전 사이로 배치
        self.btn_fit = ctk.CTkButton(self.menu_frame, text="화면 맞춤", width=100, height=32, font=UI_FONT_BOLD, 
                                     fg_color="#34495e", hover_color="#2c3e50", command=self.set_fit_mode)
        self.btn_fit.pack(side="left", padx=5, pady=5)

        self.btn_rotate = ctk.CTkButton(self.menu_frame, text="↻ 회전", width=80, height=32, font=UI_FONT_BOLD, fg_color="#576574", command=self.rotate_image)
        self.btn_rotate.pack(side="left", padx=5, pady=5)

        self.btn_flip = ctk.CTkButton(self.menu_frame, text="⇄ 반전", width=80, height=32, font=UI_FONT_BOLD, fg_color="#576574", command=self.flip_image)
        self.btn_flip.pack(side="left", padx=5, pady=5)

        # 레이어 버튼 (우측 상단)
        self.btn_layers = ctk.CTkButton(self.menu_frame, text="LAYER", width=100, 
                                        fg_color="#27ae60", hover_color="#2ecc71", 
                                        font=UI_FONT_BOLD,
                                        command=self.toggle_layer_panel)
        self.btn_layers.pack(side="right", padx=5, pady=5)
        self.btn_layers.pack_forget() # 기본적으로는 숨김

        # 배경색 전환 버튼 (레이어 버튼 옆)
        self.btn_bg_toggle = ctk.CTkButton(self.menu_frame, text="배경색 전환", width=120,
                                           fg_color="#000000", text_color="#FFFFFF",
                                           hover_color="#1a1a1a", border_width=1,
                                           font=UI_FONT_BOLD,
                                           command=self.toggle_dxf_background)
        self.btn_bg_toggle.pack(side="right", padx=5, pady=5)
        self.btn_bg_toggle.pack_forget() # 기본적으로는 숨김

        # 객체 색상 전환 버튼 (배경색 전환 버튼 왼쪽)
        self.btn_obj_color_toggle = ctk.CTkButton(self.menu_frame, text="객체 색상: 원본", width=120,
                                                 fg_color="#34495e", hover_color="#2c3e50",
                                                 font=UI_FONT_BOLD,
                                                 command=self.toggle_dxf_obj_color)
        self.btn_obj_color_toggle.pack(side="right", padx=5, pady=5)
        self.btn_obj_color_toggle.pack_forget() 

        # 중앙 메인 컨테이너 (이미지 + 정보패널)
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(side="top", fill="both", expand=True, padx=2, pady=2)
        
        # 이미지 영역 (좌측)
        self.canvas_frame = ctk.CTkFrame(self.main_container, fg_color="black")
        self.canvas_frame.grid(row=0, column=0, sticky="nsew")
        
        # 초기 가중치 설정 (이미지가 기본적으로 전체 차지)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(1, weight=0)

        # [신규] 플러그인용 사이드바 (우측)
        self.info_panel = ctk.CTkFrame(self.main_container, corner_radius=0, fg_color="#1e272e")
        
        # 단일 캔버스
        self.canvas = ctk.CTkCanvas(self.canvas_frame, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # [신규] 미니맵 (내비게이터) - 캔버스 위에 플로팅
        self.nav_size = 180 # 미니맵 최대 크기
        self.nav_canvas = tk.Canvas(self.canvas, bg="#2d3436", highlightthickness=1, highlightbackground="#636e72", width=self.nav_size, height=self.nav_size)
        # 초기에는 숨김 (확대 시 표시)

        # 분할 캔버스용 프레임 (초기에는 숨김)
        self.split_container = ctk.CTkFrame(self.canvas_frame, fg_color="black")
        
        # [신규] 좌우 크기 조절을 위한 PanedWindow 도입
        self.paned_window = tk.PanedWindow(self.split_container, orient="horizontal", 
                                          bg="#2d3436", sashwidth=4, sashpad=0,
                                          borderwidth=0)
        self.paned_window.pack(fill="both", expand=True)

        # 왼쪽 영역 프레임 (라벨 + 캔버스)
        self.left_pane = ctk.CTkFrame(self.paned_window, fg_color="black", corner_radius=0)
        self.paned_window.add(self.left_pane, stretch="always")
        
        self.lbl_filename_l = ctk.CTkLabel(self.left_pane, text="", font=UI_FONT_BOLD, text_color="#00d2d3")
        self.lbl_filename_l.pack(side="top", fill="x", padx=5, pady=2)
        
        self.canvas_left = ctk.CTkCanvas(self.left_pane, bg="black", highlightthickness=3, highlightbackground="black")
        self.canvas_left.pack(side="top", fill="both", expand=True)

        # 오른쪽 영역 프레임 (라벨 + 캔버스)
        self.right_pane = ctk.CTkFrame(self.paned_window, fg_color="black", corner_radius=0)
        self.paned_window.add(self.right_pane, stretch="always")

        self.lbl_filename_r = ctk.CTkLabel(self.right_pane, text="", font=UI_FONT_BOLD, text_color="#00d2d3")
        self.lbl_filename_r.pack(side="top", fill="x", padx=5, pady=2)
        
        self.canvas_right = ctk.CTkCanvas(self.right_pane, bg="black", highlightthickness=3, highlightbackground="black")
        self.canvas_right.pack(side="top", fill="both", expand=True)
        
        # [신규] 버튼들을 split_container 하단 또는 적절한 위치로 재배치할 필요가 있으나 일단 기존 binding 유지

        # [신규] 분할 모드용 내비게이션 버튼들
        btn_style_s = {"width": 20, "height": 60, "fg_color": "#333333", "hover_color": "#444444", "text_color": "#E0E0E0", "font": UI_FONT_NAV_S, "corner_radius": 10}
        
        self.btn_l_prev = ctk.CTkButton(self.split_container, text="◀", command=lambda: self.nav_split("left", -1), **btn_style_s)
        self.btn_l_next = ctk.CTkButton(self.split_container, text="▶", command=lambda: self.nav_split("left", 1), **btn_style_s)
        self.btn_r_prev = ctk.CTkButton(self.split_container, text="◀", command=lambda: self.nav_split("right", -1), **btn_style_s)
        self.btn_r_next = ctk.CTkButton(self.split_container, text="▶", command=lambda: self.nav_split("right", 1), **btn_style_s)

        # 메인 컨테이너 가중치 설정 (이미지 영역이 기본적으로 꽉 차게)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)
        
        
        # [수정] 내비게이션 버튼 (둥근 스타일)
        btn_style = {"width": 20, "height": 100, "fg_color": "#333333", "hover_color": "#444444", "text_color": "#E0E0E0", "font": UI_FONT_NAV_L, "corner_radius": 15}
        
        self.btn_prev = ctk.CTkButton(self.canvas_frame, text="◀", command=self.prev_image, **btn_style)
        self.btn_next = ctk.CTkButton(self.canvas_frame, text="▶", command=self.next_image, **btn_style)
        
        # 처음에는 숨김
        self.btn_prev.place_forget()
        self.btn_next.place_forget()
        
        # 하단 상태바
        self.status_frame = ctk.CTkFrame(self, height=40, corner_radius=0)
        self.status_frame.pack(side="bottom", fill="x")
        
        self.lbl_status = ctk.CTkLabel(self.status_frame, text="준비됨", font=("Malgun Gothic", 9))
        self.lbl_status.pack(side="left", padx=10)
        self.lbl_status.pack_forget() # 하단 파일명 표시 안 함 (상단으로 이동)
        
        self.btn_info = ctk.CTkButton(self.status_frame, text="ⓘ INFO", width=100, height=32, font=UI_FONT_BOLD, 
                                      fg_color="#4b6584", hover_color="#576574", command=self.toggle_info_panel)
        self.btn_info.pack(side="left", padx=15, pady=5)

        self.btn_gps = ctk.CTkButton(self.status_frame, text="📍 GPS", width=100, height=32, font=UI_FONT_BOLD, 
                                     fg_color="#eb4d4b", hover_color="#ff7979", command=self.show_gps_menu)
        self.btn_gps.pack(side="left", padx=5, pady=5)

        self.lbl_size_info = ctk.CTkLabel(self.status_frame, text="", font=UI_FONT_BOLD, text_color="#a4b0be")
        self.lbl_size_info.pack(side="left", padx=15)

        self.lbl_zoom = ctk.CTkLabel(self.status_frame, text="Zoom: 100%", font=UI_FONT_BOLD, text_color="#f1c40f", cursor="hand2")
        self.lbl_zoom.pack(side="right", padx=15)
        self.lbl_zoom.bind("<Button-1>", self.show_zoom_menu)


        # 바인딩
        self.canvas.bind("<Configure>", self.render_image)
        self.canvas_left.bind("<Configure>", self.render_image)
        self.canvas_right.bind("<Configure>", self.render_image)
        
        self.canvas_frame.bind("<Motion>", self.check_nav_visibility)
        self.canvas.bind("<Motion>", self.check_nav_visibility)
        self.canvas_left.bind("<Motion>", self.check_nav_visibility_split)
        self.canvas_right.bind("<Motion>", self.check_nav_visibility_split)
        # [수정] 좌우 창 선택은 더블 클릭으로 변경
        self.canvas_left.bind("<Double-Button-1>", lambda e: self.set_active_split("left"))
        self.canvas_right.bind("<Double-Button-1>", lambda e: self.set_active_split("right"))
        
        # [신규] 마우스 조작 바인딩 (줌은 Ctrl + 휠로 동작)
        self.canvas.bind("<Button-1>", lambda e: self.canvas.focus_set(), add="+")
        self.canvas.bind("<Control-MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<ButtonPress-1>", self.on_pan_start)
        self.canvas.bind("<B1-Motion>", self.on_pan_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_pan_end)
        
        # 분할 모드 캔버스에도 동일하게 바인딩
        for c in [self.canvas_left, self.canvas_right]:
            c.bind("<Button-1>", lambda e, widget=c: widget.focus_set(), add="+")
            c.bind("<Control-MouseWheel>", self.on_mouse_wheel)
            c.bind("<ButtonPress-1>", self.on_pan_start)
            c.bind("<B1-Motion>", self.on_pan_drag)
            c.bind("<ButtonRelease-1>", self.on_pan_end)
        
        self.bind("<Left>", lambda e: self.prev_image())
        self.bind("<Right>", lambda e: self.next_image())
        self.bind("<Control-z>", lambda e: self.undo_rename())

    def open_file(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(filetypes=[
            ("Image/CAD files", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.dxf"),
            ("All files", "*.*")
        ])
        if path:
            self.load_image(path)

    def get_image_obj(self, path):
        """플러그인 또는 PIL을 사용하여 이미지 객체 생성"""
        img = None
        for plugin in self.plugins:
            try:
                img = plugin.handle_file(path)
                if img: 
                    break
            except Exception as e:
                import traceback
                continue
        
        if not img:
            img = Image.open(path)
        return img
    

    def load_image(self, path):
        try:
            path = os.path.abspath(path)
            self.current_image_path = path
            
            # 기존 이미지 명시적 해제
            if hasattr(self, 'current_img') and self.current_img:
                try: self.current_img.close()
                except: pass
            
            self.current_img = self.get_image_obj(path)
            
            # 메모리 정리 강제 수행
            gc.collect()
            
            # [신규] 뷰 상태 초기화 (다른 사진에서의 이동/배율 영향 방지)
            self.zoom_mode = "fit"
            self.zoom_level = 1.0
            self.offset_x = 0
            self.offset_y = 0
            
            # [신규] 캔버스 및 캐시 초기화 (메모리 해제 및 이전 잔상 제거)
            self.canvas.delete("all")
            self.main_img_id = None
            self.processed_img_main = None
            self.processed_img_l = None
            self.processed_img_r = None
            self._last_key_processed_img_main = None
            self._last_key_processed_img_l = None
            self._last_key_processed_img_r = None
            
            # 모니터 해상도와 비교하여 초기 모드 결정
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()
            
            # 파일 확장자에 따른 버튼 노출 제어
            ext = os.path.splitext(path)[1].lower()
            if ext in ('.dxf', '.dwg'):
                self.btn_layers.pack(side="right", padx=5, pady=5)
                self.btn_bg_toggle.pack(side="right", padx=5, pady=5)
                self.btn_obj_color_toggle.pack(side="right", padx=5, pady=5)
                self.update_bg_toggle_ui() # 버튼 스타일 업데이트
            else:
                self.btn_layers.pack_forget()
                self.btn_bg_toggle.pack_forget()
                self.btn_obj_color_toggle.pack_forget()
                if self.show_info_panel and getattr(self, '_current_sidebar_type', '') == 'layer':
                    self.toggle_info_panel() # 레이어 창 열려있으면 닫기
            img_w, img_h = self.current_img.size
            
            if img_w > screen_w or img_h > screen_h:
                self.zoom_mode = "fit"
                self.zoom_level = 1.0
                self.offset_x = 0; self.offset_y = 0
            else:
                self.zoom_mode = "1:1"
                self.zoom_level = 1.0
                # 렌더링 시점에 정확히 중앙에 맞추기 위해 플래그 설정
                self.center_on_next_render = True
            
            # 폴더 내 리스트 업데이트
            self.update_image_list(path)
            
            self.render_image()
            
            # 하단 정보 업데이트
            filename = os.path.basename(path)
            w, h = self.current_img.size
            size_bytes = os.path.getsize(path)
            size_str = self.format_size(size_bytes)
            
            self.lbl_size_info.configure(text=f"{w} x {h}  ({size_str})")
            self.title(f"DS Image Viewer - {filename} ({self.current_index + 1}/{len(self.image_list)})")
            
            # [신규] 새 이미지 로드 시 조작 상태 초기화
            self.rotation = 0
            self.flip = False
            
            # 정보 패널 업데이트 대신 플러그인에 알림
            self.notify_image_change(path)
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("오류", f"이미지를 불러올 수 없습니다:\n{str(e)}")

    def toggle_dxf_background(self):
        """DXF 플러그인의 배경색을 전환함"""
        for plugin in self.plugins:
            if plugin.name == "DXF 뷰어":
                if hasattr(plugin, 'toggle_background'):
                    plugin.toggle_background()
                    self.update_bg_toggle_ui()
                    break

    def toggle_dxf_obj_color(self):
        """DXF 객체 색상 전환 (원본 -> 검정 -> 흰색 -> 원본)"""
        modes = ["original", "black", "white"]
        idx = (modes.index(self.dxf_obj_color_mode) + 1) % len(modes)
        self.dxf_obj_color_mode = modes[idx]
        
        # 버튼 텍스트 업데이트
        labels = {"original": "객체 색상: 원본", "black": "객체 색상: 검정", "white": "객체 색상: 흰색"}
        self.btn_obj_color_toggle.configure(text=labels[self.dxf_obj_color_mode])
        
        # 플러그인에 상태 전달 및 재렌더링
        for plugin in self.plugins:
            if plugin.name == "DXF 뷰어":
                if hasattr(plugin, 'set_object_color_mode'):
                    plugin.set_object_color_mode(self.dxf_obj_color_mode)
                    # 기본 이미지(썸네일) 새로고침하여 캐시 동기화
                    if self.current_image_path:
                        self.current_img = self.get_image_obj(self.current_image_path)
                    self.render_image()
                    break

    def update_bg_toggle_ui(self):
        """배경색 상태에 따라 버튼 스타일 업데이트 (대비 효과)"""
        for plugin in self.plugins:
            if plugin.name == "DXF 뷰어":
                bg = getattr(plugin, 'bg_color', 'black')
                if bg == "black":
                    # 배경이 검은색이면 버튼은 흰색으로 (대비 및 전환 암시)
                    self.btn_bg_toggle.configure(fg_color="#FFFFFF", text_color="#000000", hover_color="#f0f0f0")
                else:
                    # 배경이 흰색이면 버튼은 검은색으로
                    self.btn_bg_toggle.configure(fg_color="#000000", text_color="#FFFFFF", hover_color="#1a1a1a")
                break

    def format_size(self, bytes):
        """파일 용량을 보기 좋은 단위로 변환"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024
        return f"{bytes:.1f} TB"


    def toggle_split_mode(self):
        """화면 분할 모드 토글"""
        self.split_mode = not self.split_mode
        if self.split_mode:
            self.canvas.pack_forget()
            self.split_container.pack(fill="both", expand=True)
            self.btn_split.configure(text="단일 보기", fg_color="#ee5253", hover_color="#ff7675")
            
            # 분할 모드 초기화
            self.l_mode = "fit"; self.r_mode = "fit"
            self.l_rot = self.rotation; self.l_flip = self.flip # 단일 모드 상태 복사
            self.r_rot = 0; self.r_flip = False # 오른쪽은 초기화
            
            self.left_index = self.current_index
            if self.image_list:
                self.current_image_path = self.image_list[self.left_index]
                self.lbl_filename_l.configure(text=os.path.basename(self.current_image_path))
                
                if len(self.image_list) > 1:
                    self.right_index = (self.current_index + 1) % len(self.image_list)
                    path_r = self.image_list[self.right_index]
                    self.second_img = self.get_image_obj(path_r)
                    self.lbl_filename_r.configure(text=os.path.basename(path_r))
                else:
                    self.right_index = self.current_index
                    self.second_img = self.current_img
                    self.lbl_filename_r.configure(text=os.path.basename(self.current_image_path))
            
            self.set_active_split("left")
        else:
            # 활성 창의 상태를 단일 모드로 복사
            if self.active_split == "left":
                self.rotation = self.l_rot; self.flip = self.l_flip
            else:
                self.rotation = self.r_rot; self.flip = self.r_flip
                # 오른쪽 창이 활성이었으면 현재 사진도 오른쪽 것으로 변경
                if self.image_list:
                    self.current_index = self.right_index
                    self.current_image_path = self.image_list[self.current_index]
                    self.current_img = self.second_img

            self.split_container.pack_forget()
            self.canvas.pack(fill="both", expand=True)
            self.btn_split.configure(text="화면 분할", fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"], hover_color=ctk.ThemeManager.theme["CTkButton"]["hover_color"])
            self.second_img = None
            self.zoom_mode = "fit"
            
        # 레이아웃 갱신 강제 수행 (크기 계산 완료 대기)
        self.update_idletasks()
        self.render_image()

    def nav_split(self, side, delta):
        """분할 모드에서 개별 사진 넘기기"""
        if not self.image_list: return
        
        if side == "left":
            self.l_mode = "fit" # 새로운 사진은 다시 맞춤
            self.left_index = (self.left_index + delta) % len(self.image_list)
            self.current_image_path = self.image_list[self.left_index]
            self.current_img = self.get_image_obj(self.current_image_path)
            self.lbl_filename_l.configure(text=os.path.basename(self.current_image_path))
            self.l_rot = 0; self.l_flip = False # 상태 초기화
            self.set_active_split("left") # 넘기면 해당 창 활성화
        else:
            self.r_mode = "fit" # 새로운 사진은 다시 맞춤
            self.right_index = (self.right_index + delta) % len(self.image_list)
            path_r = self.image_list[self.right_index]
            self.second_img = self.get_image_obj(path_r)
            self.lbl_filename_r.configure(text=os.path.basename(path_r))
            self.r_rot = 0; self.r_flip = False # 상태 초기화
            self.set_active_split("right") # 넘기면 해당 창 활성화
            
        self.render_image()
        self.notify_image_change(self.current_image_path)

    def toggle_info_panel(self):
        """이미지 정보 패널 토글"""
        self._show_sidebar('info')

    def toggle_layer_panel(self):
        """레이어 설정 패널 토글"""
        self._show_sidebar('layer')

    def _show_sidebar(self, sidebar_type):
        """공통 사이드바 노출 로직 (타입별 플러그인 연동)"""
        # 현재 열려있는 타입과 같으면 닫기
        current_type = getattr(self, '_current_sidebar_type', None)
        if self.show_info_panel and current_type == sidebar_type:
            self.info_panel.grid_forget()
            # [수정] 가중치 초기화 (이미지 영역이 100% 차지)
            self.main_container.grid_columnconfigure(0, weight=1)
            self.main_container.grid_columnconfigure(1, weight=0, minsize=0)
            self.show_info_panel = False
            self._current_sidebar_type = None
            self.after(50, self.render_image)
            return

        # 패널 노출 및 레이아웃 설정
        # [수정] 프로그램 창 너비의 정확히 1/4이 되도록 가중치(3:1) 설정
        self.info_panel.grid(row=0, column=1, sticky="nsew")
        
        self.main_container.grid_columnconfigure(0, weight=3) # 이미지 영역 (3/4)
        self.main_container.grid_columnconfigure(1, weight=1) # 정보창 영역 (1/4)
        self.show_info_panel = True
        self._current_sidebar_type = sidebar_type
        
        # 타입에 맞는 플러그인 로드
        target_plugin = "DXF 뷰어" if sidebar_type == 'layer' else "이미지 상세 정보"

        for plugin in self.plugins:
            if plugin.name == target_plugin:
                if hasattr(plugin, 'on_embed'):
                    # 사이드바 내부 청소 후 플러그인 UI 삽입
                    for child in self.info_panel.winfo_children():
                        child.destroy()
                    plugin.on_embed(self, self.info_panel)
                break
        
        self.after(50, self.render_image)

    def set_active_split(self, side):
        """활성 분할 화면 설정 및 테두리 강조"""
        if not self.split_mode: return
        self.active_split = side
        
        # 테두리 설정 강제 적용 (색상과 두께)
        if side == "left":
            self.canvas_left.configure(highlightbackground="#ff4d4d", highlightthickness=3)
            self.canvas_right.configure(highlightbackground="black", highlightthickness=3)
            # 활성 경로 업데이트
            self.current_image_path = self.image_list[self.left_index] if self.left_index >= 0 else self.current_image_path
        else:
            self.canvas_left.configure(highlightbackground="black", highlightthickness=3)
            self.canvas_right.configure(highlightbackground="#ff4d4d", highlightthickness=3)
            # 활성 경로 업데이트
            self.current_image_path = self.image_list[self.right_index] if self.right_index >= 0 else self.current_image_path
            
        self.render_image()
        self.notify_image_change(self.current_image_path)


    def update_image_list(self, current_path):
        folder = os.path.dirname(current_path)
        exts = ('.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.dxf')
        try:
            files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(exts)]
            # 자연스러운 정렬 (알파벳/숫자 순)
            self.image_list = sorted(files, key=lambda x: os.path.basename(x).lower())
            if current_path in self.image_list:
                self.current_index = self.image_list.index(current_path)
            else:
                self.current_index = -1
        except:
            self.image_list = [current_path]
            self.current_index = 0

    def rotate_image(self):
        """이미지 회전 (상태값 변경)"""
        if self.split_mode:
            if self.active_split == "left":
                self.l_rot = (self.l_rot - 90) % 360
            else:
                self.r_rot = (self.r_rot - 90) % 360
        else:
            self.rotation = (self.rotation - 90) % 360
        
        self.set_fit_mode() # 상태 반영을 위해 재렌더링

    def flip_image(self):
        """이미지 반전 (상태값 변경)"""
        if self.split_mode:
            if self.active_split == "left":
                self.l_flip = not self.l_flip
            else:
                self.r_flip = not self.r_flip
        else:
            self.flip = not self.flip
        
        self.render_image() # 상태 반영을 위해 재렌더링

    def undo_rename(self):
        """마지막 파일 이름 변경 취소 (Ctrl+Z)"""
        if not self.rename_history: return
        
        old_path, current_path = self.rename_history.pop()
        
        if os.path.exists(current_path):
            try:
                os.rename(current_path, old_path)
                
                # 현재 보고 있는 파일이라면 UI 갱신
                if self.current_image_path == current_path:
                    self.current_image_path = old_path
                    self.update_image_list(old_path)
                    self.load_image(old_path)
                else:
                    # 다른 파일을 보고 있더라도 리스트는 갱신 필요
                    self.update_image_list(self.current_image_path)
                
                self.lbl_status.configure(text="이름 변경 취소됨", text_color="#f1c40f")
                self.lbl_status.pack(side="left", padx=10)
                self.after(2000, lambda: self.lbl_status.pack_forget())
            except Exception as e:
                from tkinter import messagebox
                messagebox.showerror("오류", f"실행 취소 중 오류가 발생했습니다:\n{str(e)}")

    def prev_image(self):
        """이전 이미지로 이동 (분할 모드 대응)"""
        if self.split_mode:
            self.nav_split(self.active_split, -1)
            return
            
        if not self.image_list: return
        self.current_index = (self.current_index - 1) % len(self.image_list)
        self.load_image(self.image_list[self.current_index])

    def next_image(self):
        """다음 이미지로 이동 (분할 모드 대응)"""
        if self.split_mode:
            self.nav_split(self.active_split, 1)
            return
            
        if not self.image_list: return
        self.current_index = (self.current_index + 1) % len(self.image_list)
        self.load_image(self.image_list[self.current_index])

    def update_zoom_label(self):
        """하단 상태바의 줌 배율 텍스트 업데이트"""
        if hasattr(self, 'lbl_zoom'):
            self.lbl_zoom.configure(text=f"Zoom: {int(self.zoom_level * 100)}%")

    def set_fit_mode(self):
        """화면 맞춤 모드 강제 설정 (분할 모드 대응)"""
        if self.split_mode:
            if self.active_split == "left":
                self.l_mode = "fit"
            else:
                self.r_mode = "fit"
        else:
            if not self.current_img: return
            self.zoom_mode = "fit"
            
        self.render_image()
        self.update_zoom_label()

    def on_mouse_wheel(self, event):
        """마우스 휠을 이용한 커서 기준 확대/축소 (분할 모드 대응)"""
        if self.split_mode:
            # 현재 마우스 아래의 위젯 확인
            widget = event.widget
            if widget == self.canvas_left or "canvas_left" in str(widget):
                side, zoom, ox, oy = "l", self.l_zoom, self.l_off_x, self.l_off_y
            elif widget == self.canvas_right or "canvas_right" in str(widget):
                side, zoom, ox, oy = "r", self.r_zoom, self.r_off_x, self.r_off_y
            else:
                # 캔버스 밖이면 현재 활성된 창 기준
                if self.active_split == "left":
                    side, zoom, ox, oy = "l", self.l_zoom, self.l_off_x, self.l_off_y
                else:
                    side, zoom, ox, oy = "r", self.r_zoom, self.r_off_x, self.r_off_y
        else:
            side, zoom, ox, oy = "main", self.zoom_level, self.offset_x, self.offset_y
            
        factor = 1.2 if event.delta > 0 else 0.8
        new_zoom = zoom * factor
        if new_zoom < 0.01: new_zoom = 0.01
        if new_zoom > 20.0: new_zoom = 20.0
        
        if new_zoom == zoom: return
        
        px, py = event.x, event.y
        new_ox = px - (px - ox) * (new_zoom / zoom)
        new_oy = py - (py - oy) * (new_zoom / zoom)
        
        if side == "l":
            self.l_zoom = new_zoom; self.l_off_x = new_ox; self.l_off_y = new_oy; self.l_mode = "manual"
        elif side == "r":
            self.r_zoom = new_zoom; self.r_off_x = new_ox; self.r_off_y = new_oy; self.r_mode = "manual"
        else:
            self.zoom_level = new_zoom; self.offset_x = new_ox; self.offset_y = new_oy; self.zoom_mode = "manual"
            
        self.render_image(fast=True)
        self.update_zoom_label()
        self.schedule_high_quality_render()

    def on_pan_start(self, event):
        """드래그 이동 시작 (절대 좌표 방식 도입)"""
        self.is_panning = True
        self.pan_mouse_start_x = event.x
        self.pan_mouse_start_y = event.y
        
        # 시작 시점의 오프셋 저장
        widget = event.widget
        if self.split_mode:
            if widget == self.canvas_left or "canvas_left" in str(widget):
                self.pan_orig_off_x = self.l_off_x
                self.pan_orig_off_y = self.l_off_y
            else:
                self.pan_orig_off_x = self.r_off_x
                self.pan_orig_off_y = self.r_off_y
        else:
            self.pan_orig_off_x = self.offset_x
            self.pan_orig_off_y = self.offset_y
            
        event.widget.configure(cursor="fleur")

    def on_pan_drag(self, event):
        """드래그 이동 중 (스로틀링을 적용하되 고화질 예약은 누락 방지)"""
        if not self.is_panning: return
        
        # 스로틀링: 초당 약 60프레임 제한 (약 16ms)
        import time
        now = time.time()
        should_render = (now - self.last_pan_render_time >= 0.016)
        
        dx = event.x - self.pan_mouse_start_x
        dy = event.y - self.pan_mouse_start_y
        
        widget = event.widget
        if self.split_mode:
            if widget == self.canvas_left or "canvas_left" in str(widget):
                self.l_off_x = self.pan_orig_off_x + dx
                self.l_off_y = self.pan_orig_off_y + dy
                self.l_mode = "manual"
            else:
                self.r_off_x = self.pan_orig_off_x + dx
                self.r_off_y = self.pan_orig_off_y + dy
                self.r_mode = "manual"
        else:
            self.offset_x = self.pan_orig_off_x + dx
            self.offset_y = self.pan_orig_off_y + dy
            self.zoom_mode = "manual"
        
        if should_render:
            self.last_pan_render_time = now
            self.render_image(fast=True)
            
        # 스로틀링 여부와 상관없이 고화질 전환 예약 (누락 방지)
        self.schedule_high_quality_render()

    def on_pan_end(self, event):
        """드래그 이동 종료"""
        self.is_panning = False
        event.widget.configure(cursor="")

    def check_nav_visibility(self, event):
        """마우스 위치에 따라 버튼 표시/숨김 제어"""
        w = self.canvas_frame.winfo_width()
        margin = 100 # 감지 영역 너비
        
        # 이전 버튼 제어
        if event.x < margin:
            self.btn_prev.place(relx=0.03, rely=0.5, anchor="center")
        else:
            self.btn_prev.place_forget()
            
        # 다음 버튼 제어
        if event.x > w - margin:
            self.btn_next.place(relx=0.97, rely=0.5, anchor="center")
        else:
            self.btn_next.place_forget()

    def schedule_high_quality_render(self):
        """조작이 멈추면 일정 시간 뒤 고화질로 다시 그림"""
        if self.render_timer:
            self.after_cancel(self.render_timer)
        self.render_timer = self.after(150, lambda: self.render_image(fast=False))

    def check_nav_visibility_split(self, event):
        """분할 모드에서 마우스 위치에 따른 버튼 표시 제어"""
        if not self.split_mode: return
        
        # 이벤트가 발생한 캔버스 확인
        canvas = event.widget
        w = canvas.winfo_width()
        margin = 60 # 분할 모드용 좁은 감지 영역
        
        # 버튼 숨김 초기화
        self.btn_l_prev.place_forget()
        self.btn_l_next.place_forget()
        self.btn_r_prev.place_forget()
        self.btn_r_next.place_forget()
        
        # 왼쪽 캔버스 감지
        if canvas == self.canvas_left:
            if event.x < margin:
                self.btn_l_prev.place(in_=self.canvas_left, relx=0.05, rely=0.5, anchor="center")
            elif event.x > w - margin:
                self.btn_l_next.place(in_=self.canvas_left, relx=0.95, rely=0.5, anchor="center")
        
        # 오른쪽 캔버스 감지
        elif canvas == self.canvas_right:
            if event.x < margin:
                self.btn_r_prev.place(in_=self.canvas_right, relx=0.05, rely=0.5, anchor="center")
            elif event.x > w - margin:
                self.btn_r_next.place(in_=self.canvas_right, relx=0.95, rely=0.5, anchor="center")

    def get_exif_data_for_obj(self, img_obj):
        """이미지 상세 정보 플러그인을 사용하여 EXIF 데이터 추출"""
        for plugin in self.plugins:
            if plugin.name == "이미지 상세 정보" and hasattr(plugin, 'get_exif_data'):
                return plugin.get_exif_data(img_obj)
        return {}

    def show_gps_menu(self):
        """GPS 지도 선택 메뉴 표시"""
        # 현재 활성화된 이미지 객체 선택
        img_obj = self.current_img
        if self.split_mode and self.active_split == "right":
            img_obj = self.second_img
            
        if not img_obj: return
        
        exif = self.get_exif_data_for_obj(img_obj)
        lat = exif.get('Lat_Val')
        lon = exif.get('Lon_Val')
        
        # [신규] 좌표 정보가 없으면 메뉴를 띄우지 않고 메시지 표시
        if not lat or not lon:
            from tkinter import messagebox
            messagebox.showwarning("정보 없음", "좌표 정보가 없습니다")
            return

        menu = tk.Menu(self, tearoff=0, bg="#2f3640", fg="white", activebackground="#eb4d4b", font=UI_FONT_NORMAL)
        menu.add_command(label="네이버 지도에서 보기", command=lambda: self.open_map("naver"))
        menu.add_command(label="카카오맵에서 보기", command=lambda: self.open_map("kakao"))
        menu.add_command(label="구글맵에서 보기", command=lambda: self.open_map("google"))
        
        # 버튼 위치 계산
        x = self.btn_gps.winfo_rootx()
        y = self.btn_gps.winfo_rooty() - 70 # 위로 띄움
        menu.post(x, y)

    def open_map(self, provider):
        """좌표를 사용하여 브라우저에서 지도 열기"""
        # 현재 활성화된 이미지 객체 선택
        img_obj = self.current_img
        if self.split_mode and self.active_split == "right":
            img_obj = self.second_img
            
        if not img_obj: return
        
        exif = self.get_exif_data_for_obj(img_obj)
        lat = exif.get('Lat_Val')
        lon = exif.get('Lon_Val')
        
        try:
            # 숫자로 변환 가능한 유효한 좌표인지 확인
            lat_val = float(lat)
            lon_val = float(lon)
            
            import webbrowser
            if provider == "naver":
                url = f"https://map.naver.com/v5/search/{lat_val},{lon_val}"
            elif provider == "kakao":
                url = f"https://map.kakao.com/?q={lat_val},{lon_val}"
            else:
                url = f"https://www.google.com/maps/search/?api=1&query={lat_val},{lon_val}"
            webbrowser.open(url)
        except (TypeError, ValueError):
            from tkinter import messagebox
            messagebox.showwarning("정보 없음", "좌표 정보가 없습니다")

    def show_zoom_menu(self, event):
        """줌 배율 선택 메뉴 표시"""
        menu = tk.Menu(self, tearoff=0, bg="#2f3640", fg="white", activebackground="#00d2d3", font=UI_FONT_NORMAL)
        zoom_levels = ["10%", "25%", "50%", "75%", "100%", "125%", "150%", "200%", "300%", "400%", "500%"]
        
        for level in zoom_levels:
            menu.add_command(label=level, command=lambda l=level: self.set_zoom_level_preset(l))
        
        # 라벨 위치에 맞춰 메뉴 팝업
        menu.post(event.x_root, event.y_root)

    def set_zoom_level_preset(self, level_str):
        """프리셋 배율 설정"""
        if not self.current_img: return
        try:
            percentage = int(level_str.replace("%", ""))
            self.zoom_level = percentage / 100.0
            self.zoom_mode = "manual"
            self.render_image()
        except:
            pass

    def render_image(self, fast=False):
        if not self.current_img: return
        
        if not self.split_mode:
            # 단일 모드 렌더링
            self._render_to_canvas(self.canvas, self.current_img, path=self.current_image_path, fast=fast)
        else:
            # 분할 모드 렌더링 - 각 캔버스에 해당하는 정확한 경로 전달
            path_l = self.image_list[self.left_index] if self.left_index >= 0 else self.current_image_path
            path_r = self.image_list[self.right_index] if self.right_index >= 0 else None
            
            self._render_to_canvas(self.canvas_left, self.current_img, path=path_l, fast=fast)
            if self.second_img:
                self._render_to_canvas(self.canvas_right, self.second_img, path=path_r, fast=fast)

    def _render_to_canvas(self, canvas, img_obj, path=None, fast=False):
        """특정 캔버스에 배율과 오프셋을 적용하여 이미지 렌더링"""
        if not img_obj: return
        
        canvas_w = canvas.winfo_width()
        canvas_h = canvas.winfo_height()
        if canvas_w < 10 or canvas_h < 10: return
        
        img_w, img_h = img_obj.size
        target_path = path or self.current_image_path

        # 벡터 포맷(DXF 등) 고화질 재렌더링 지원
        if not fast and hasattr(self, 'plugins') and target_path:
            for plugin in self.plugins:
                if hasattr(plugin, 'render_viewport') and target_path.lower().endswith('.dxf'):
                    if self.split_mode:
                        cur_zoom = self.l_zoom if canvas == self.canvas_left else self.r_zoom
                        cur_off_x = self.l_off_x if canvas == self.canvas_left else self.r_off_x
                        cur_off_y = self.l_off_y if canvas == self.canvas_left else self.r_off_y
                    else:
                        cur_zoom, cur_off_x, cur_off_y = self.zoom_level, self.offset_x, self.offset_y
                        
                    v_img = plugin.render_viewport(target_path, canvas_w, canvas_h, cur_zoom, cur_off_x, cur_off_y)
                    if v_img:
                        # 회전/반전 상태 적용 (고화질 렌더링 결과물 가공)
                        rot = self.l_rot if canvas == self.canvas_left else self.r_rot
                        fli = self.l_flip if canvas == self.canvas_left else self.r_flip
                        if not self.split_mode: rot, fli = self.rotation, self.flip
                        
                        if rot != 0: v_img = v_img.rotate(rot, expand=True)
                        if fli: v_img = v_img.transpose(Image.FLIP_LEFT_RIGHT)

                        photo = ImageTk.PhotoImage(v_img)
                        self._update_canvas_item(canvas, photo, 0, 0)
                        return

        # 회전/반전 상태 적용 (성능 최적화를 위한 캐싱 도입)
        rot = self.l_rot if canvas == self.canvas_left else self.r_rot
        fli = self.l_flip if canvas == self.canvas_left else self.r_flip
        if not self.split_mode: rot, fli = self.rotation, self.flip
        
        # 캐시 키 생성 (경로 + 회전 + 반전)
        cache_key = (target_path, rot, fli)
        
        # 캔버스별 캐시 변수 선택
        if canvas == self.canvas_left:
            cache_attr = "processed_img_l"
        elif canvas == self.canvas_right:
            cache_attr = "processed_img_r"
        else:
            cache_attr = "processed_img_main"

        # 캐시가 없거나 상태가 바뀌었을 때만 회전 수행
        current_cache = getattr(self, cache_attr, None)
        if current_cache is None or getattr(self, "_last_key_" + cache_attr, None) != cache_key:
            processed = img_obj
            if rot != 0:
                processed = processed.rotate(rot, expand=True)
            if fli:
                processed = processed.transpose(Image.FLIP_LEFT_RIGHT)
            setattr(self, cache_attr, processed)
            setattr(self, "_last_key_" + cache_attr, cache_key)
            img_obj = processed
        else:
            img_obj = current_cache

        img_w, img_h = img_obj.size

        # [상태 변수 결정] 캔버스에 따른 독립 변수 선택
        if self.split_mode:
            if canvas == self.canvas_left:
                if self.l_mode == "fit":
                    ratio = min(canvas_w / img_w, canvas_h / img_h)
                    self.l_zoom = ratio
                    self.l_off_x = (canvas_w - img_w * ratio) / 2
                    self.l_off_y = (canvas_h - img_h * ratio) / 2
                cur_zoom, cur_off_x, cur_off_y = self.l_zoom, self.l_off_x, self.l_off_y
            else:
                if self.r_mode == "fit":
                    ratio = min(canvas_w / img_w, canvas_h / img_h)
                    self.r_zoom = ratio
                    self.r_off_x = (canvas_w - img_w * ratio) / 2
                    self.r_off_y = (canvas_h - img_h * ratio) / 2
                cur_zoom, cur_off_x, cur_off_y = self.r_zoom, self.r_off_x, self.r_off_y
        else:
            if self.zoom_mode == "fit":
                ratio = min(canvas_w / img_w, canvas_h / img_h)
                self.zoom_level = ratio
                self.offset_x = (canvas_w - img_w * ratio) / 2
                self.offset_y = (canvas_h - img_h * ratio) / 2
            elif getattr(self, 'center_on_next_render', False):
                self.offset_x = (canvas_w - img_w * self.zoom_level) / 2
                self.offset_y = (canvas_h - img_h * self.zoom_level) / 2
                self.center_on_next_render = False
                
            cur_zoom, cur_off_x, cur_off_y = self.zoom_level, self.offset_x, self.offset_y
        
        # [최적화] Crop-Resize 렌더링 로직 (성능 핵심)
        src_left = max(0, -cur_off_x / cur_zoom)
        src_top = max(0, -cur_off_y / cur_zoom)
        src_right = min(img_w, (canvas_w - cur_off_x) / cur_zoom)
        src_bottom = min(img_h, (canvas_h - cur_off_y) / cur_zoom)
        
        dst_left = max(0, cur_off_x)
        dst_top = max(0, cur_off_y)
        dst_right = min(canvas_w, cur_off_x + img_w * cur_zoom)
        dst_bottom = min(canvas_h, cur_off_y + img_h * cur_zoom)
        
        out_w, out_h = int(dst_right - dst_left), int(dst_bottom - dst_top)
        
        if out_w > 0 and out_h > 0:
            resample = Image.Resampling.NEAREST if fast else Image.Resampling.BILINEAR
            cropped = img_obj.crop((src_left, src_top, src_right, src_bottom))
            resized_img = cropped.resize((out_w, out_h), resample)
            
            photo = ImageTk.PhotoImage(resized_img)
            self._update_canvas_item(canvas, photo, dst_left, dst_top)
        
        if not self.split_mode:
            self.update_zoom_label()
            self.update_navigator(img_obj, cur_zoom, cur_off_x, cur_off_y, canvas_w, canvas_h, fast=fast)
        elif canvas == (self.canvas_left if self.active_split == "left" else self.canvas_right):
            # 분할 모드에서 활성 창의 줌 레벨 표시
            if hasattr(self, 'lbl_zoom'):
                self.lbl_zoom.configure(text=f"Zoom: {int(cur_zoom * 100)}%")

    def _update_canvas_item(self, canvas, photo, x, y):
        """캔버스 이미지 아이템 업데이트 및 참조 유지"""
        img_id_attr = "main_img_id"
        if canvas == self.canvas_left: img_id_attr = "l_img_id"
        elif canvas == self.canvas_right: img_id_attr = "r_img_id"
        
        item_id = getattr(self, img_id_attr)
        if item_id and canvas.find_withtag(item_id):
            canvas.itemconfig(item_id, image=photo)
            canvas.coords(item_id, x, y)
        else:
            canvas.delete("all")
            new_id = canvas.create_image(x, y, anchor="nw", image=photo)
            setattr(self, img_id_attr, new_id)
        
        # 참조 유지
        if canvas == self.canvas: self.tk_img = photo
        elif canvas == self.canvas_left: self.tk_img_left = photo
        elif canvas == self.canvas_right: self.tk_img_right = photo

    def update_navigator(self, img_obj, zoom, off_x, off_y, cw, ch, fast=False):
        """미니맵 업데이트 (전체 사진 대비 현재 영역 표시)"""
        if self.split_mode or not img_obj:
            self.nav_canvas.place_forget()
            return
            
        # Fit 비율 계산 (내비게이터 표시 여부 결정용)
        img_w, img_h = img_obj.size
        fit_ratio = min(cw / img_w, ch / img_h)
        # 확대되지 않았으면 미니맵 숨김
        if zoom <= fit_ratio + 0.01:
            self.nav_canvas.place_forget()
            return
            
        # 드래그 중(fast=True)에는 사각형만 빠르게 업데이트하고 나머지는 건너뜀
        if fast and hasattr(self, 'nav_rect_id'):
            self._update_nav_rect_only(img_w, img_h, zoom, off_x, off_y, cw, ch)
            return

        # 미니맵 표시 (좌측 상단으로 이동)
        self.nav_canvas.place(relx=0.02, rely=0.02, anchor="nw")
        
        # 썸네일 캐싱 처리
        cache_key = id(img_obj)
        if cache_key in self.nav_thumb_cache:
            photo, nw, nh = self.nav_thumb_cache[cache_key]
        else:
            nav_ratio = min(self.nav_size / img_w, self.nav_size / img_h)
            nw, nh = int(img_w * nav_ratio), int(img_h * nav_ratio)
            thumb = img_obj.resize((nw, nh), Image.Resampling.NEAREST)
            
            # [신규] 회전/반전 상태 적용 (내비게이터 썸네일)
            if self.rotation != 0: thumb = thumb.rotate(self.rotation, expand=True)
            if self.flip: thumb = thumb.transpose(Image.FLIP_LEFT_RIGHT)
            
            # 썸네일 크기가 바뀌었을 수 있으므로 다시 계산
            nw, nh = thumb.size
            
            photo = ImageTk.PhotoImage(thumb)
            # 캐시 크기 관리 (LRU 방식과 유사하게 오래된 항목 제거)
            if len(self.nav_thumb_cache) > self.max_nav_cache:
                oldest_key = next(iter(self.nav_thumb_cache))
                del self.nav_thumb_cache[oldest_key]
                
            self.nav_thumb_cache[cache_key] = (photo, nw, nh)
            self.nav_img_id = None # 이미지가 바뀌었으므로 초기화
            
        # 캔버스 크기 조정
        if int(self.nav_canvas.cget("width")) != nw or int(self.nav_canvas.cget("height")) != nh:
            self.nav_canvas.config(width=nw, height=nh)
        
        # [최적화] 네비게이터 아이템 재사용
        if not getattr(self, 'nav_img_id', None) or not self.nav_canvas.find_withtag(self.nav_img_id):
            self.nav_canvas.delete("all")
            self.nav_img_id = self.nav_canvas.create_image(0, 0, anchor="nw", image=photo)
            self.nav_rect_id = self.nav_canvas.create_rectangle(0, 0, 0, 0, outline="#ff4d4d", width=2)
        else:
            self.nav_canvas.itemconfig(self.nav_img_id, image=photo)
        
        self.nav_canvas.image = photo 
        
        # 뷰포트 비율 계산용 ratio
        nav_ratio = nw / img_w
        
        # 현재 뷰포트 영역 계산 (정상 렌더링 시에도 이 로직 사용)
        self._update_nav_rect_only(img_w, img_h, zoom, off_x, off_y, cw, ch)

    def _update_nav_rect_only(self, img_w, img_h, zoom, off_x, off_y, cw, ch):
        """드래그 중 내비게이터 사각형만 초고속 업데이트"""
        rect_id = getattr(self, 'nav_rect_id', None)
        if not rect_id or not self.nav_canvas.find_withtag(rect_id):
            return
        
        # 내비게이터 캔버스의 실제 현재 크기 기반
        nw = self.nav_canvas.winfo_width()
        nh = self.nav_canvas.winfo_height()
        
        # 회전 상태에 따른 이미지 실질 크기 결정
        actual_img_w, actual_img_h = img_w, img_h
        if self.rotation in [90, 270]:
            actual_img_w, actual_img_h = img_h, img_w
            
        rw = (cw / (actual_img_w * zoom)) * nw
        rh = (ch / (actual_img_h * zoom)) * nh
        rx = (-off_x / (actual_img_w * zoom)) * nw
        ry = (-off_y / (actual_img_h * zoom)) * nh
        
        self.nav_canvas.coords(self.nav_rect_id, rx, ry, rx+rw, ry+rh)
        self.nav_canvas.tag_raise(self.nav_rect_id)

    # --- [플러그인 시스템 구현] ---
    def load_plugins(self):
        """내부 패키징된 플러그인과 외부 plugins 폴더에서 플러그인을 동적으로 로드합니다."""
        # 1. 내부 패키징된 플러그인 경로 (PyInstaller _MEIPASS)
        internal_dir = ""
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            internal_dir = os.path.join(sys._MEIPASS, "plugins")
            
        # 2. 외부 플러그인 경로 (EXE 옆)
        external_dir = os.path.join(BASE_DIR, "plugins")
        
        # 탐색 대상 경로 리스트
        search_dirs = []
        if internal_dir and os.path.exists(internal_dir): search_dirs.append(internal_dir)
        if os.path.exists(external_dir): search_dirs.append(external_dir)
        else: os.makedirs(external_dir) # 외부 폴더 없으면 생성

        # 플러그인이 메인 앱의 interface를 참조할 수 있도록 sys.path 추가
        if BASE_DIR not in sys.path:
            sys.path.insert(0, BASE_DIR)

        loaded_files = set()
        for plugin_dir in search_dirs:
            for plugin_file in glob.glob(os.path.join(plugin_dir, "*.py")):
                fname = os.path.basename(plugin_file)
                if fname == "__init__.py" or fname in loaded_files:
                    continue
                
                try:
                    module_name = fname[:-3]
                    spec = importlib.util.spec_from_file_location(module_name, plugin_file)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # 모듈 내에서 플러그인 클래스 탐색
                    for item_name in dir(module):
                        item = getattr(module, item_name)
                        if inspect.isclass(item) and item.__name__ != 'BasePlugin':
                            # handle_file 메서드가 있으면 플러그인으로 인정
                            if hasattr(item, 'handle_file'):
                                try:
                                    plugin_instance = item()
                                    self.plugins.append(plugin_instance)
                                    loaded_files.add(fname)
                                except Exception:
                                    pass
                    
                except Exception as e:
                    import traceback
                    if getattr(sys, 'frozen', False):
                        from tkinter import messagebox
                        messagebox.showerror("플러그인 로드 오류", f"{fname} 로드 실패.")

    def notify_image_change(self, path):
        """로드된 이미지가 바뀌면 모든 플러그인에 알림"""
        for plugin in self.plugins:
            try:
                plugin.on_image_change(self, path)
            except Exception as e:
                print(f"Plugin notification error: {e}")


if __name__ == "__main__":
    try:
        hwid = get_hwid()
        # [복구] 기존 라이센스 키와 일치하도록 앱 이름 원복
        is_ok, data = check_license("DS_IMAGE_VIEWER")
        if not is_ok:
            show_license_error(hwid, data)
        else:
            app = ImageViewer(data)
            app.mainloop()
    except Exception as e:
        import traceback
        if getattr(sys, 'frozen', False):
            from tkinter import messagebox
            messagebox.showerror("치명적 오류", f"프로그램 실행 중 오류가 발생했습니다.\ndebug_log.txt를 확인해 주세요.\n\n{str(e)}")
