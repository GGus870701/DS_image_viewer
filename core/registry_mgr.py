import sys
import os
import winreg
import ctypes

# 이미지 관련 확장자 목록
IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".tif", ".webp"]
APP_ID = "DS_Image_Viewer.v1"

def get_app_command():
    """현재 실행 경로에 따른 명령어 반환"""
    if getattr(sys, 'frozen', False):
        return f'"{sys.executable}" "%1"'
    else:
        python_exe = sys.executable
        if python_exe.lower().endswith("python.exe"):
            pythonw_exe = python_exe[:-4] + "w.exe"
            if os.path.exists(pythonw_exe):
                python_exe = pythonw_exe
        return f'"{python_exe}" "{os.path.abspath(sys.argv[0])}" "%1"'

def register_context_menu():
    """Windows 탐색기 우클릭 계층형 메뉴 등록"""
    if getattr(sys, 'frozen', False):
        exe_path = sys.executable
        icon_path = exe_path
    else:
        python_exe = sys.executable
        if python_exe.lower().endswith("python.exe"):
            pythonw_exe = python_exe[:-4] + "w.exe"
            if os.path.exists(pythonw_exe):
                python_exe = pythonw_exe
        exe_path = f'"{python_exe}" "{os.path.abspath(sys.argv[0])}"'
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "ds_viewer_icon.ico")

    try:
        base_key = r"Software\Classes\SystemFileAssociations\image\shell\DSViewer"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base_key) as key:
            winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, "DS Image Viewer")
            if os.path.exists(icon_path):
                winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, icon_path)
            winreg.SetValueEx(key, "SubCommands", 0, winreg.REG_SZ, "")
            winreg.SetValueEx(key, "MultiSelectModel", 0, winreg.REG_SZ, "Player")

        shell_key = rf"{base_key}\shell"
        convert_key = rf"{shell_key}\1_convert"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, convert_key) as key:
            winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, "이미지 크기 변환")
            winreg.SetValueEx(key, "MultiSelectModel", 0, winreg.REG_SZ, "Player")
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{convert_key}\command") as key:
            winreg.SetValue(key, "", winreg.REG_SZ, f'{exe_path} --convert "%1"')

        # 편집기는 현재 제거되었으므로 등록하지 않음 (필요 시 복구)
        return True, "메뉴 등록 성공"
    except Exception as e:
        return False, f"메뉴 등록 실패: {e}"

def unregister_context_menu():
    """Windows 탐색기 우클릭 계층형 메뉴 구조 삭제"""
    try:
        base_key = r"Software\Classes\SystemFileAssociations\image\shell\DSViewer"
        _delete_key_recursive(winreg.HKEY_CURRENT_USER, base_key)
        _delete_key_recursive(winreg.HKEY_CURRENT_USER, r"Software\Classes\SystemFileAssociations\image\shell\ds_convert")
        return True, "메뉴 해제 성공"
    except Exception as e:
        return False, f"메뉴 해제 실패: {e}"

def is_context_menu_registered():
    """현재 우클릭 메뉴가 등록되어 있는지 확인"""
    try:
        key_path = r"Software\Classes\SystemFileAssociations\image\shell\DSViewer"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path):
            pass
        return True
    except:
        return False

# --- 기본 연결 프로그램 관련 ---

def is_default_program_registered():
    """기본 연결 프로그램 후보로 등록되어 있는지 확인"""
    try:
        app_key_path = f"Software\\Classes\\Applications\\{APP_ID}\\shell\\open\\command"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, app_key_path) as key:
            value, _ = winreg.QueryValueEx(key, "")
            current_cmd = get_app_command().replace(' "%1"', '')
            return current_cmd in value
    except:
        return False

def register_default_program():
    """기본 연결 프로그램 후보로 등록"""
    try:
        cmd = get_app_command()
        
        # 1. Applications 등록
        app_key = f"Software\\Classes\\Applications\\{APP_ID}"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, app_key) as key:
            with winreg.CreateKey(key, "shell\\open\\command") as cmd_key:
                winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, cmd)
        
        # 2. 각 확장자별 OpenWithProgids 등록
        for ext in IMAGE_EXTENSIONS:
            ext_key = f"Software\\Classes\\{ext}\\OpenWithProgids"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, ext_key) as key:
                winreg.SetValueEx(key, APP_ID, 0, winreg.REG_NONE, b"")
        
        # 쉘 갱신 알림
        _notify_shell()
        return True, "기본 프로그램 후보로 등록되었습니다."
    except Exception as e:
        return False, f"등록 실패: {e}"

def unregister_default_program():
    """기본 연결 프로그램 등록 정보 삭제"""
    try:
        for ext in IMAGE_EXTENSIONS:
            try:
                ext_key = f"Software\\Classes\\{ext}\\OpenWithProgids"
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, ext_key, 0, winreg.KEY_ALL_ACCESS) as key:
                    winreg.DeleteValue(key, APP_ID)
            except: pass

        _delete_key_recursive(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\Applications\\{APP_ID}")
        
        _notify_shell()
        return True, "등록 정보가 성공적으로 삭제되었습니다."
    except Exception as e:
        return False, f"삭제 실패: {e}"

# --- 유틸리티 ---

def _delete_key_recursive(root, subkey):
    try:
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_ALL_ACCESS) as key:
            while True:
                try:
                    child = winreg.EnumKey(key, 0)
                    _delete_key_recursive(key, child)
                except OSError:
                    break
        winreg.DeleteKey(root, subkey)
    except FileNotFoundError:
        pass

def _notify_shell():
    """Windows 쉘에 변경 사항 알림"""
    try:
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
    except:
        pass

if __name__ == "__main__":
    # 테스트용
    print(f"Registered: {is_default_program_registered()}")
