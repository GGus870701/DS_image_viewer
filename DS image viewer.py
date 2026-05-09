import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk, ImageOps
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

# --- [초기 설정] ---
def get_base_dir():
    """실행 파일(EXE)이 위치한 실제 폴더 경로를 반환 (Nuitka 최신 버전 대응)"""
    for env_var in ['NUITKA_ONEFILE_DIRECTORY', 'NUITKA_PACKAGE_HOME']:
        val = os.environ.get(env_var)
        if val:
            path = os.path.abspath(val)
            if os.path.isfile(path): path = os.path.dirname(path)
            return path

    if getattr(sys, 'frozen', False):
        exe_path = os.path.abspath(sys.executable)
        if 'Temp' not in exe_path: return os.path.dirname(exe_path)
        argv_path = os.path.abspath(sys.argv[0])
        if 'Temp' not in argv_path: return os.path.dirname(argv_path)
        return os.path.dirname(exe_path)
    else:
        return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()
CONFIG_FILE = os.path.join(BASE_DIR, "settings.json")
LICENSE_CENTRAL_DIR = r"C:\license"

# DPI 인식 설정
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# --- [라이센스 시스템] ---
SECRET_KEY = "DS_CAPTURE_SECRET_KEY_2026_@!" # DS 계열 공통 키 사용

def get_hwid():
    """기기 고유 정보를 조합하여 해싱된 HWID 생성"""
    try:
        cmd_mb = 'powershell "Get-CimInstance -ClassName Win32_BaseBoard | Select-Object -ExpandProperty SerialNumber"'
        mb_serial = subprocess.check_output(cmd_mb, shell=True).decode('cp949').strip()
        cmd_disk = 'powershell "Get-CimInstance -ClassName Win32_DiskDrive | Select-Object -ExpandProperty SerialNumber"'
        disk_serial = subprocess.check_output(cmd_disk, shell=True).decode('cp949').strip()
        raw_id = f"DS_{mb_serial}_{disk_serial}"
        hash_id = hashlib.sha256(raw_id.encode()).hexdigest().upper()
        return f"{hash_id[:4]}-{hash_id[4:8]}-{hash_id[8:12]}"
    except:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography")
            guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            hash_id = hashlib.sha256(guid.encode()).hexdigest().upper()
            return f"G-{hash_id[:4]}-{hash_id[4:8]}"
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
                    data = json.load(f)
                
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
    error_root.geometry("450x300")
    ctk.set_appearance_mode("dark")
    
    ctk.CTkLabel(error_root, text="라이센스 인증이 필요합니다.", text_color="#ff4757", font=("Malgun Gothic", 16, "bold")).pack(pady=(30, 10))
    ctk.CTkLabel(error_root, text=message, font=("Malgun Gothic", 10), wraplength=400).pack(pady=5)
    ctk.CTkLabel(error_root, text=f"기기 고유 ID: {hwid}", text_color="#00d2d3", font=("Consolas", 12, "bold")).pack(pady=15)
    
    def copy_id():
        error_root.clipboard_clear()
        error_root.clipboard_append(hwid)
        from tkinter import messagebox
        messagebox.showinfo("복사 완료", "기기 ID가 복사되었습니다.")
        
    ctk.CTkButton(error_root, text="기기 ID 복사하기", command=copy_id, fg_color="#4b6584").pack(pady=10)
    ctk.CTkButton(error_root, text="종료", command=sys.exit, fg_color="transparent", border_width=1).pack(pady=5)
    
    error_root.mainloop()

# --- [메인 애플리케이션] ---
class ImageViewer(ctk.CTk):
    def __init__(self, license_data):
        super().__init__()
        self.license_data = license_data
        
        # UI 설정
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        user_info = self.license_data.get('user_name', 'Free User')
        self.title(f"DS Image Viewer v1.00 - [{user_info}]")
        
        # 해상도 기반 최대화 설정
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        self.geometry(f"{int(screen_w*0.8)}x{int(screen_h*0.8)}")
        self.after(0, lambda: self.state('zoomed')) # 시작 시 최대화
        
        # 상태 변수
        self.current_image_path = None
        self.current_img = None
        self.zoom_level = 1.0
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
        
        # [신규] 이미지 조작용 상태 변수 (단일 모드용)
        self.zoom_level = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
        # [신규] 분할 모드 전용 독립 조작 변수 (좌/우)
        self.l_zoom = 1.0; self.l_off_x = 0; self.l_off_y = 0; self.l_mode = "fit"
        self.r_zoom = 1.0; self.r_off_x = 0; self.r_off_y = 0; self.r_mode = "fit"
        
        # [신규] 성능 최적화용 캐시
        self.nav_thumb_cache = {} # {path: (photo, nw, nh)}
        
        self.is_panning = False
        self.pan_start_x = 0
        self.pan_start_y = 0
        
        # [신규] 성능 최적화용 상태 변수
        self.render_timer = None # 고화질 전환 예약용
        self.main_img_id = None  # 메인 캔버스 이미지 아이템 ID
        self.l_img_id = None     # 왼쪽 캔버스 이미지 아이템 ID
        self.r_img_id = None     # 오른쪽 캔버스 이미지 아이템 ID
        self.nav_img_id = None   # 미니맵 이미지 아이템 ID
        self.nav_rect_id = None  # 미니맵 사각형 아이템 ID
        
        self.setup_ui()
        
        # 인자로 파일이 넘어온 경우 (연결 프로그램 실행)
        if len(sys.argv) > 1:
            self.load_image(sys.argv[1])

    def setup_ui(self):
        # 상단 메뉴 영역 (프레임)
        self.menu_frame = ctk.CTkFrame(self, height=40, corner_radius=0)
        self.menu_frame.pack(side="top", fill="x")
        
        self.btn_open = ctk.CTkButton(self.menu_frame, text="파일 열기", width=100, command=self.open_file)
        self.btn_open.pack(side="left", padx=10, pady=5)

        self.btn_split = ctk.CTkButton(self.menu_frame, text="화면 분할", width=100, command=self.toggle_split_mode)
        self.btn_split.pack(side="left", padx=5, pady=5)

        self.btn_rotate = ctk.CTkButton(self.menu_frame, text="↻ 회전", width=80, fg_color="#576574", command=self.rotate_image)
        self.btn_rotate.pack(side="left", padx=5, pady=5)

        self.btn_flip = ctk.CTkButton(self.menu_frame, text="⇄ 대칭", width=80, fg_color="#576574", command=self.flip_image)
        self.btn_flip.pack(side="left", padx=5, pady=5)
        
        # 상단 라벨 제거됨
        
        # 중앙 메인 컨테이너 (이미지 + 정보패널)
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(side="top", fill="both", expand=True, padx=2, pady=2)

        # 이미지 영역
        self.canvas_frame = ctk.CTkFrame(self.main_container, fg_color="black")
        self.canvas_frame.grid(row=0, column=0, sticky="nsew")
        
        # 단일 캔버스
        self.canvas = ctk.CTkCanvas(self.canvas_frame, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # [신규] 미니맵 (내비게이터) - 캔버스 위에 플로팅
        self.nav_size = 180 # 미니맵 최대 크기
        self.nav_canvas = tk.Canvas(self.canvas, bg="#2d3436", highlightthickness=1, highlightbackground="#636e72", width=self.nav_size, height=self.nav_size)
        # 초기에는 숨김 (확대 시 표시)

        # 분할 캔버스용 프레임 (초기에는 숨김)
        self.split_container = ctk.CTkFrame(self.canvas_frame, fg_color="black")
        
        self.canvas_left = ctk.CTkCanvas(self.split_container, bg="black", highlightthickness=3, highlightbackground="black")
        self.canvas_left.pack(side="left", fill="both", expand=True, padx=1)
        
        self.canvas_right = ctk.CTkCanvas(self.split_container, bg="black", highlightthickness=3, highlightbackground="black")
        self.canvas_right.pack(side="left", fill="both", expand=True, padx=1)

        # [신규] 분할 모드용 내비게이션 버튼들
        btn_style_s = {"width": 20, "height": 60, "fg_color": "#333333", "hover_color": "#444444", "text_color": "#E0E0E0", "font": ("Arial", 18), "corner_radius": 10}
        
        self.btn_l_prev = ctk.CTkButton(self.split_container, text="◀", command=lambda: self.nav_split("left", -1), **btn_style_s)
        self.btn_l_next = ctk.CTkButton(self.split_container, text="▶", command=lambda: self.nav_split("left", 1), **btn_style_s)
        self.btn_r_prev = ctk.CTkButton(self.split_container, text="◀", command=lambda: self.nav_split("right", -1), **btn_style_s)
        self.btn_r_next = ctk.CTkButton(self.split_container, text="▶", command=lambda: self.nav_split("right", 1), **btn_style_s)

        # [신규] 정보 패널 (우측)
        self.info_panel = ctk.CTkFrame(self.main_container, corner_radius=0, fg_color="#1e272e")
        # 초기에는 grid 하지 않음
        
        # 메인 컨테이너 가중치 설정 (이미지 영역이 기본적으로 꽉 차게)
        self.main_container.grid_columnconfigure(0, weight=7)
        self.main_container.grid_rowconfigure(0, weight=1)
        
        self.info_title = ctk.CTkLabel(self.info_panel, text="이미지 정보", font=("Malgun Gothic", 20, "bold"), text_color="#00d2d3")
        self.info_title.pack(pady=20)
        
        # [수정] 표 형식의 정보 레이아웃
        self.info_scroll = ctk.CTkScrollableFrame(self.info_panel, fg_color="transparent")
        self.info_scroll.pack(fill="both", expand=True, padx=10, pady=5)
        self.info_scroll.columnconfigure(1, weight=1) # 값 컬럼 확장
        
        self.info_labels = {} # 라벨 객체 저장용
        items = ["파일명", "위치", "해상도", "파일크기", "촬영일시", "카메라", "위도", "경도", "고도", "생성일시", "수정일시"]
        
        for i, item in enumerate(items):
            # 항목명 (왼쪽)
            lbl_key = ctk.CTkLabel(self.info_scroll, text=item, font=("Malgun Gothic", 14, "bold"), text_color="#a4b0be", width=100, anchor="w")
            lbl_key.grid(row=i, column=0, padx=5, pady=8, sticky="nw")
            
            # 값 (오른쪽) - 클릭 가능
            lbl_val = ctk.CTkLabel(self.info_scroll, text="-", font=("Malgun Gothic", 16), text_color="white", anchor="w", justify="left", cursor="hand2", wraplength=300)
            lbl_val.grid(row=i, column=1, padx=5, pady=8, sticky="nw")
            
            # 파일명/위치인 경우 특수 기능, 그 외는 복사 기능
            if item == "파일명":
                lbl_val.bind("<Button-1>", lambda e: self.rename_file())
                lbl_val.configure(text_color="#00d2d3") # 클릭 가능 강조
            elif item == "위치":
                lbl_val.bind("<Button-1>", lambda e: self.open_in_explorer())
                lbl_val.configure(text_color="#00d2d3") # 클릭 가능 강조
            else:
                lbl_val.bind("<Button-1>", lambda e, val=lbl_val: self.copy_info(val))
            
            self.info_labels[item] = lbl_val
        
        # [수정] 내비게이션 버튼 (둥근 스타일)
        btn_style = {"width": 20, "height": 100, "fg_color": "#333333", "hover_color": "#444444", "text_color": "#E0E0E0", "font": ("Arial", 28), "corner_radius": 15}
        
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
        
        self.btn_info = ctk.CTkButton(self.status_frame, text="ⓘ INFO", width=100, height=30, font=("Malgun Gothic", 12, "bold"), 
                                      fg_color="#4b6584", hover_color="#576574", command=self.toggle_info_panel)
        self.btn_info.pack(side="left", padx=15, pady=5)

        self.btn_gps = ctk.CTkButton(self.status_frame, text="📍 GPS", width=100, height=30, font=("Malgun Gothic", 12, "bold"), 
                                     fg_color="#eb4d4b", hover_color="#ff7979", command=self.show_gps_menu)
        self.btn_gps.pack(side="left", padx=5, pady=5)

        self.lbl_size_info = ctk.CTkLabel(self.status_frame, text="", font=("Malgun Gothic", 13, "bold"), text_color="#a4b0be")
        self.lbl_size_info.pack(side="left", padx=15)

        self.lbl_zoom = ctk.CTkLabel(self.status_frame, text="Zoom: 100%", font=("Malgun Gothic", 13, "bold"), text_color="#f1c40f", cursor="hand2")
        self.lbl_zoom.pack(side="right", padx=15)
        self.lbl_zoom.bind("<Button-1>", self.show_zoom_menu)

        self.btn_fit = ctk.CTkButton(self.status_frame, text="FIT", width=100, height=30, font=("Arial", 12, "bold"), 
                                     fg_color="#34495e", hover_color="#2c3e50", command=self.set_fit_mode)
        self.btn_fit.pack(side="right", padx=10, pady=5)

        # 바인딩
        self.canvas.bind("<Configure>", self.on_canvas_resize)
        self.canvas_frame.bind("<Motion>", self.check_nav_visibility)
        self.canvas.bind("<Motion>", self.check_nav_visibility)
        self.canvas_left.bind("<Motion>", self.check_nav_visibility_split)
        self.canvas_right.bind("<Motion>", self.check_nav_visibility_split)
        # [수정] 좌우 창 선택은 더블 클릭으로 변경
        self.canvas_left.bind("<Double-Button-1>", lambda e: self.set_active_split("left"))
        self.canvas_right.bind("<Double-Button-1>", lambda e: self.set_active_split("right"))
        
        # [신규] 마우스 조작 바인딩 (줌은 Ctrl + 휠로 변경)
        self.canvas.bind("<Control-MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<ButtonPress-1>", self.on_pan_start)
        self.canvas.bind("<B1-Motion>", self.on_pan_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_pan_end)
        
        # 분할 모드 캔버스에도 동일하게 바인딩
        for c in [self.canvas_left, self.canvas_right]:
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
            ("Image files", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff"),
            ("All files", "*.*")
        ])
        if path:
            self.load_image(path)

    def load_image(self, path):
        try:
            path = os.path.abspath(path)
            self.current_image_path = path
            self.current_img = Image.open(path)
            
            # 모니터 해상도와 비교하여 초기 모드 결정
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()
            img_w, img_h = self.current_img.size
            
            if img_w > screen_w or img_h > screen_h:
                self.zoom_mode = "fit"
                self.zoom_level = 1.0 # fit 모드에서 계산됨
            else:
                self.zoom_mode = "1:1"
                self.zoom_level = 1.0
            
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
            
            # 정보 패널 업데이트
            self.update_info_panel()
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("오류", f"이미지를 불러올 수 없습니다:\n{str(e)}")

    def format_size(self, bytes):
        """파일 용량을 보기 좋은 단위로 변환"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024
        return f"{bytes:.1f} TB"

    def toggle_info_panel(self):
        """정보 패널 토글 (grid 가중치 이용)"""
        self.show_info_panel = not self.show_info_panel
        if self.show_info_panel:
            self.info_panel.grid(row=0, column=1, sticky="nsew")
            # 이미지(7) : 정보패널(2) 비율 설정 (전체의 약 22%)
            self.main_container.grid_columnconfigure(1, weight=2)
            self.update_info_panel()
        else:
            self.info_panel.grid_forget()
            self.main_container.grid_columnconfigure(1, weight=0)
        
        # 레이아웃 변경 후 이미지 재렌더링
        self.after(100, self.render_image)

    def toggle_split_mode(self):
        """화면 분할 모드 토글"""
        self.split_mode = not self.split_mode
        if self.split_mode:
            self.canvas.pack_forget()
            self.split_container.pack(fill="both", expand=True)
            self.btn_split.configure(text="단일 보기", fg_color="#ee5253", hover_color="#ff7675")
            
            # 분할 모드 초기화
            self.l_mode = "fit"; self.r_mode = "fit"
            self.left_index = self.current_index
            if self.image_list and len(self.image_list) > 1:
                self.right_index = (self.current_index + 1) % len(self.image_list)
                self.second_img = Image.open(self.image_list[self.right_index])
            else:
                self.right_index = self.current_index
                self.second_img = self.current_img
            
            self.set_active_split("left")
        else:
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
            self.current_index = self.left_index 
            self.current_img = Image.open(self.image_list[self.left_index])
            self.current_image_path = self.image_list[self.left_index]
            self.set_active_split("left") # 넘기면 해당 창 활성화
        else:
            self.r_mode = "fit" # 새로운 사진은 다시 맞춤
            self.right_index = (self.right_index + delta) % len(self.image_list)
            self.second_img = Image.open(self.image_list[self.right_index])
            self.set_active_split("right") # 넘기면 해당 창 활성화
            
        self.render_image()

    def set_active_split(self, side):
        """활성 분할 화면 설정 및 테두리 강조"""
        if not self.split_mode: return
        self.active_split = side
        
        # 테두리 설정 강제 적용 (색상과 두께)
        if side == "left":
            self.canvas_left.configure(highlightbackground="#ff4d4d", highlightthickness=3) # 선명한 빨간색
            self.canvas_right.configure(highlightbackground="black", highlightthickness=3)
        else:
            self.canvas_left.configure(highlightbackground="black", highlightthickness=3)
            self.canvas_right.configure(highlightbackground="#ff4d4d", highlightthickness=3) # 선명한 빨간색
            
        self.update_info_panel()
        self.render_image() # 줌 라벨 업데이트 등을 위해 다시 그림

    def update_info_panel(self):
        """정보 패널 내용 업데이트 (표 형식 + 분할 모드 대응)"""
        if not self.show_info_panel: return
        
        # 분할 모드인 경우 활성화된 창의 경로와 이미지 사용
        if self.split_mode:
            if self.active_split == "left":
                path = self.image_list[self.left_index] if self.left_index >= 0 else self.current_image_path
                img_obj = self.current_img
            else:
                path = self.image_list[self.right_index] if self.right_index >= 0 else None
                img_obj = self.second_img
        else:
            path = self.current_image_path
            img_obj = self.current_img
            
        if not path or not img_obj: return
        
        stats = os.stat(path)
        ctime = time.ctime(stats.st_ctime)
        mtime = time.ctime(stats.st_mtime)
        w, h = img_obj.size
        size_str = self.format_size(stats.st_size)
        exif_info = self.get_exif_data_for_obj(img_obj)
        
        # 데이터 매핑
        data = {
            "파일명": os.path.basename(path),
            "위치": path,
            "해상도": f"{w} x {h}",
            "파일크기": size_str,
            "촬영일시": exif_info.get('DateTime', '정보 없음'),
            "카메라": exif_info.get('Model', '정보 없음'),
            "위도": exif_info.get('Lat', '정보 없음'),
            "경도": exif_info.get('Lon', '정보 없음'),
            "고도": exif_info.get('Alt', '정보 없음'),
            "생성일시": ctime,
            "수정일시": mtime
        }
        
        for key, val in data.items():
            if key in self.info_labels:
                self.info_labels[key].configure(text=val)

    def copy_info(self, label_obj):
        """클릭한 라벨의 내용을 클립보드에 복사"""
        text = label_obj.cget("text")
        if text and text != "정보 없음" and text != "-":
            self.clipboard_clear()
            self.clipboard_append(text)
            
            # 피드백 표시 (색상 잠시 변경)
            original_color = label_obj.cget("text_color")
            label_obj.configure(text_color="#00d2d3")
            self.after(200, lambda: label_obj.configure(text_color=original_color))

    def rename_file(self):
        """현재 파일 이름 변경"""
        if not self.current_image_path: return
        
        current_name = os.path.basename(self.current_image_path)
        base_name, ext = os.path.splitext(current_name)
        
        dialog = ctk.CTkInputDialog(text="새 파일명을 입력하세요:", title="파일명 수정")
        dialog.bind("<Escape>", lambda e: dialog.destroy()) # ESC 누르면 취소
        new_base = dialog.get_input()
        
        if new_base and new_base != base_name:
            try:
                new_name = new_base + ext
                folder = os.path.dirname(self.current_image_path)
                new_path = os.path.join(folder, new_name)
                
                # 파일 이동(이름 변경)
                os.rename(self.current_image_path, new_path)
                
                # 히스토리 저장 (Undo용)
                self.rename_history.append((self.current_image_path, new_path))
                
                # 경로 업데이트 및 UI 갱신
                self.current_image_path = new_path
                self.update_image_list(new_path)
                self.load_image(new_path)
                
                from tkinter import messagebox
                messagebox.showinfo("성공", f"파일명이 '{new_name}'으로 변경되었습니다.")
            except Exception as e:
                from tkinter import messagebox
                messagebox.showerror("오류", f"파일명을 변경할 수 없습니다:\n{str(e)}")

    def open_in_explorer(self):
        """현재 파일의 위치를 탐색기에서 열기 (파일 선택 상태)"""
        if not self.current_image_path: return
        try:
            path = os.path.normpath(self.current_image_path)
            # 공백 대응을 위해 /select, 와 경로를 명확히 구분하여 호출
            subprocess.Popen(f'explorer /select,"{path}"')
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("오류", f"탐색기를 열 수 없습니다:\n{str(e)}")

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

    def get_exif_data(self):
        """이미지에서 EXIF 메타데이터 추출 (기본 객체용)"""
        return self.get_exif_data_for_obj(self.current_img)

    def get_exif_data_for_obj(self, img_obj):
        """특정 이미지 객체에서 EXIF 메타데이터 추출"""
        if not img_obj: return {}
        from PIL.ExifTags import TAGS, GPSTAGS
        info = {}
        try:
            exif = img_obj._getexif()
            if exif:
                for tag, value in exif.items():
                    decoded = TAGS.get(tag, tag)
                    if decoded == "GPSInfo":
                        gps_info = value
                        if gps_info:
                            # 위도(2), 위도참조(1), 경도(4), 경도참조(3)
                            lat_val, lat_dms = self.get_decimal_from_dms(gps_info.get(2), gps_info.get(1))
                            lon_val, lon_dms = self.get_decimal_from_dms(gps_info.get(4), gps_info.get(3))
                            
                            info['Lat_Val'] = lat_val
                            info['Lon_Val'] = lon_val
                            info['Lat'] = f"{lat_dms} ({lat_val:.6f}°)" if lat_val is not None else "정보 없음"
                            info['Lon'] = f"{lon_dms} ({lon_val:.6f}°)" if lon_val is not None else "정보 없음"
                            
                            # 고도(6)
                            alt = gps_info.get(6)
                            if alt is not None:
                                if hasattr(alt, 'numerator'): alt = float(alt.numerator) / alt.denominator
                                info['Alt'] = f"{float(alt):.2f} m"
                    else:
                        if decoded in ["DateTimeOriginal", "DateTime", "Model"]:
                            info[decoded if decoded != "DateTimeOriginal" else "DateTime"] = value
        except:
            pass
        return info

    def get_decimal_from_dms(self, dms, ref):
        """DMS 형식을 도(Decimal) 단위 및 문자열로 변환"""
        if not dms or not ref: return None, ""
        try:
            # dms는 보통 (degree, minute, second) 튜플/리스트
            deg = float(dms[0])
            min = float(dms[1])
            sec = float(dms[2])
            
            decimal = deg + min / 60.0 + sec / 3600.0
            if ref in ['S', 'W']:
                decimal = -decimal
            
            # 도/분/초 형식 문자열 생성
            dms_str = f"{int(deg)}° {int(min)}' {sec:.2f}\""
            return decimal, dms_str
        except:
            return None, ""

    def update_image_list(self, current_path):
        folder = os.path.dirname(current_path)
        exts = ('.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff')
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
        """이미지를 시계 방향으로 90도 회전"""
        if not self.current_img: return
        self.current_img = self.current_img.rotate(-90, expand=True)
        self.set_fit_mode() # 회전 후에는 화면에 맞춤

    def flip_image(self):
        """이미지 좌우 반전"""
        if not self.current_img: return
        self.current_img = self.current_img.transpose(Image.FLIP_LEFT_RIGHT)
        self.render_image()

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
        """드래그 이동 시작"""
        self.is_panning = True
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        event.widget.configure(cursor="fleur")

    def on_pan_drag(self, event):
        """드래그 이동 중 (분할 모드 대응)"""
        if not self.is_panning: return
        dx = event.x - self.pan_start_x
        dy = event.y - self.pan_start_y
        
        widget = event.widget
        if self.split_mode:
            if widget == self.canvas_left or "canvas_left" in str(widget):
                self.l_off_x += dx; self.l_off_y += dy; self.l_mode = "manual"
            else:
                self.r_off_x += dx; self.r_off_y += dy; self.r_mode = "manual"
        else:
            self.offset_x += dx; self.offset_y += dy; self.zoom_mode = "manual"
        
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.render_image(fast=True) # 조작 중에는 저화질(빠름)
        
        # 조작 종료 후 고화질 전환 예약
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

    def show_gps_menu(self):
        """GPS 지도 선택 메뉴 표시"""
        menu = tk.Menu(self, tearoff=0, bg="#2f3640", fg="white", activebackground="#eb4d4b", font=("Malgun Gothic", 13))
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
            messagebox.showwarning("정보 없음", "유효한 GPS 좌표 정보가 포함되어 있지 않습니다.")

    def show_zoom_menu(self, event):
        """줌 배율 선택 메뉴 표시"""
        menu = tk.Menu(self, tearoff=0, bg="#2f3640", fg="white", activebackground="#00d2d3", font=("Malgun Gothic", 13))
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
            self._render_to_canvas(self.canvas, self.current_img, fast=fast)
        else:
            # 분할 모드 렌더링
            self._render_to_canvas(self.canvas_left, self.current_img, fast=fast)
            if self.second_img:
                self._render_to_canvas(self.canvas_right, self.second_img, fast=fast)

    def _render_to_canvas(self, canvas, img_obj, fast=False):
        """특정 캔버스에 배율과 오프셋을 적용하여 이미지 렌더링"""
        if not img_obj: return
        
        canvas_w = canvas.winfo_width()
        canvas_h = canvas.winfo_height()
        if canvas_w < 10 or canvas_h < 10: return
        
        img_w, img_h = img_obj.size
        
        # [상태 변수 결정] 캔버스에 따른 독립 변수 선택
        if self.split_mode:
            if canvas == self.canvas_left:
                if self.l_mode == "fit":
                    ratio = min(canvas_w / img_w, canvas_h / img_h)
                    self.l_zoom = ratio
                    self.l_off_x = (canvas_w - img_w * ratio) / 2
                    self.l_off_y = (canvas_h - img_h * ratio) / 2
                    self.l_mode = "fit_done"
                cur_zoom, cur_off_x, cur_off_y = self.l_zoom, self.l_off_x, self.l_off_y
            else:
                if self.r_mode == "fit":
                    ratio = min(canvas_w / img_w, canvas_h / img_h)
                    self.r_zoom = ratio
                    self.r_off_x = (canvas_w - img_w * ratio) / 2
                    self.r_off_y = (canvas_h - img_h * ratio) / 2
                    self.r_mode = "fit_done"
                cur_zoom, cur_off_x, cur_off_y = self.r_zoom, self.r_off_x, self.r_off_y
        else:
            if self.zoom_mode == "fit":
                ratio = min(canvas_w / img_w, canvas_h / img_h)
                self.zoom_level = ratio
                self.offset_x = (canvas_w - img_w * ratio) / 2
                self.offset_y = (canvas_h - img_h * ratio) / 2
                self.zoom_mode = "fit_done"
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
            # [최적화] 조작 중(fast=True)이면 NEAREST, 아니면 BILINEAR
            resample = Image.Resampling.NEAREST if fast else Image.Resampling.BILINEAR
            
            cropped = img_obj.crop((src_left, src_top, src_right, src_bottom))
            resized_img = cropped.resize((out_w, out_h), resample)
            photo = ImageTk.PhotoImage(resized_img)
            
            # [최적화] 캔버스 아이템 재사용 (delete "all" 지양)
            img_id_attr = "main_img_id"
            if canvas == self.canvas_left: img_id_attr = "l_img_id"
            elif canvas == self.canvas_right: img_id_attr = "r_img_id"
            
            item_id = getattr(self, img_id_attr)
            if item_id and canvas.find_withtag(item_id):
                canvas.itemconfig(item_id, image=photo)
                canvas.coords(item_id, dst_left, dst_top)
            else:
                # 초기 생성 시에는 기존 것을 지우고 새로 생성
                canvas.delete("all")
                new_id = canvas.create_image(dst_left, dst_top, anchor="nw", image=photo)
                setattr(self, img_id_attr, new_id)
            
            # 이미지 참조 유지 (GC 방지)
            if canvas == self.canvas: self.tk_img = photo
            elif canvas == self.canvas_left: self.tk_img_left = photo
            elif canvas == self.canvas_right: self.tk_img_right = photo
        
        if not self.split_mode:
            self.update_zoom_label()
            self.update_navigator(img_obj, cur_zoom, cur_off_x, cur_off_y, canvas_w, canvas_h, fast=fast)
        elif canvas == (self.canvas_left if self.active_split == "left" else self.canvas_right):
            # 분할 모드에서 활성 창의 줌 레벨 표시
            if hasattr(self, 'lbl_zoom'):
                self.lbl_zoom.configure(text=f"Zoom: {int(cur_zoom * 100)}%")

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
            photo = ImageTk.PhotoImage(thumb)
            self.nav_thumb_cache[cache_key] = (photo, nw, nh)
            self.nav_img_id = None # 이미지가 바뀌었으므로 초기화
            
        # 캔버스 크기 조정
        if int(self.nav_canvas.cget("width")) != nw or int(self.nav_canvas.cget("height")) != nh:
            self.nav_canvas.config(width=nw, height=nh)
        
        # [최적화] 네비게이터 아이템 재사용
        if not self.nav_img_id or not self.nav_canvas.find_withtag(self.nav_img_id):
            self.nav_canvas.delete("all")
            self.nav_img_id = self.nav_canvas.create_image(0, 0, anchor="nw", image=photo)
            self.nav_rect_id = self.nav_canvas.create_rectangle(0, 0, 0, 0, outline="#ff4d4d", width=2)
        else:
            self.nav_canvas.itemconfig(self.nav_img_id, image=photo)
        
        self.nav_canvas.image = photo 
        
        # 뷰포트 비율 계산용 ratio
        nav_ratio = nw / img_w
        
        # 현재 뷰포트 영역 계산
        img_left = -off_x / zoom
        img_top = -off_y / zoom
        img_right = (cw - off_x) / zoom
        img_bottom = (ch - off_y) / zoom
        
        # 미니맵 좌표로 변환
        rect_l = max(0, img_left * nav_ratio)
        rect_t = max(0, img_top * nav_ratio)
        rect_r = min(nw, img_right * nav_ratio)
        rect_b = min(nh, img_bottom * nav_ratio)
        
        # [최적화] 사각형 위치만 업데이트
        self.nav_canvas.coords(self.nav_rect_id, rect_l, rect_t, rect_r, rect_b)

    def on_canvas_resize(self, event):
        if self.current_img:
            self.render_image()

if __name__ == "__main__":
    app_name = "DS_IMAGE_VIEWER"
    success, data = check_license(app_name)
    if success:
        app = ImageViewer(data)
        app.mainloop()
    else:
        show_license_error(get_hwid(), data or "유효한 라이센스를 찾을 수 없습니다.")
