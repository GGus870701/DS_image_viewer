import sys
import os
import winreg

def register_context_menu():
    """Windows 탐색기 우클릭 계층형 메뉴 등록"""
    # 1. 실행 경로 및 아이콘 경로 판별
    if getattr(sys, 'frozen', False):
        # 배포된 EXE 환경
        exe_path = sys.executable
        icon_path = exe_path
    else:
        # 파이썬 개발 환경
        python_exe = sys.executable
        # 콘솔창 숨김을 위해 python.exe 대신 pythonw.exe 사용 시도
        if python_exe.lower().endswith("python.exe"):
            pythonw_exe = python_exe[:-4] + "w.exe"
            if os.path.exists(pythonw_exe):
                python_exe = pythonw_exe
                
        exe_path = f'"{python_exe}" "{os.path.abspath(sys.argv[0])}"'
        # resources 폴더의 아이콘 경로 (core/ 폴더 기준 상위의 resources/)
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "ds_viewer_icon.ico")

    try:
        # 상위 메뉴 키 경로
        base_key = r"Software\Classes\SystemFileAssociations\image\shell\DSViewer"
        
        # 2. 상위 메뉴 생성 (MUIVerb: 표시 이름, Icon: 아이콘)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base_key) as key:
            winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, "DS Image Viewer")
            if os.path.exists(icon_path):
                winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, icon_path)
            # 계층형 메뉴 지원을 위한 SubCommands 설정 (빈 문자열)
            winreg.SetValueEx(key, "SubCommands", 0, winreg.REG_SZ, "")
            # 다중 선택 지원 (Player 모드)
            winreg.SetValueEx(key, "MultiSelectModel", 0, winreg.REG_SZ, "Player")

        # 3. 하위 메뉴 구조 생성 (shell 폴더)
        shell_key = rf"{base_key}\shell"
        
        # 3-1. 이미지 크기 변환 (1_convert)
        convert_key = rf"{shell_key}\1_convert"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, convert_key) as key:
            winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, "이미지 크기 변환")
            winreg.SetValueEx(key, "MultiSelectModel", 0, winreg.REG_SZ, "Player")
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{convert_key}\command") as key:
            winreg.SetValue(key, "", winreg.REG_SZ, f'{exe_path} --convert "%1"')

        # 3-2. 이미지 편집기로 열기 (2_edit)
        edit_key = rf"{shell_key}\2_edit"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, edit_key) as key:
            winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, "이미지 편집기로 열기")
            winreg.SetValueEx(key, "MultiSelectModel", 0, winreg.REG_SZ, "Player")
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{edit_key}\command") as key:
            winreg.SetValue(key, "", winreg.REG_SZ, f'{exe_path} --edit "%1"')

        return True, "메뉴 등록 성공"
    except Exception as e:
        return False, f"메뉴 등록 실패: {e}"

def unregister_context_menu():
    """Windows 탐색기 우클릭 계층형 메뉴 구조 삭제"""
    try:
        base_key = r"Software\Classes\SystemFileAssociations\image\shell\DSViewer"
        
        # 레지스트리 키를 하위부터 재귀적으로 삭제하는 헬퍼 함수
        def delete_key_recursive(root, subkey):
            try:
                with winreg.OpenKey(root, subkey, 0, winreg.KEY_ALL_ACCESS) as key:
                    while True:
                        try:
                            child = winreg.EnumKey(key, 0)
                            delete_key_recursive(key, child)
                        except OSError:
                            break
                winreg.DeleteKey(root, subkey)
            except FileNotFoundError:
                pass

        # 새로운 계층형 키 삭제
        delete_key_recursive(winreg.HKEY_CURRENT_USER, base_key)
        
        # 구버전 단일 메뉴 키 삭제 (하위 호환성)
        delete_key_recursive(winreg.HKEY_CURRENT_USER, r"Software\Classes\SystemFileAssociations\image\shell\ds_convert")
        
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
    except FileNotFoundError:
        return False
    except Exception:
        return False

if __name__ == "__main__":
    # 테스트용 단독 실행
    if len(sys.argv) > 1 and sys.argv[1] == "remove":
        ok, msg = unregister_context_menu()
    else:
        ok, msg = register_context_menu()
    print(msg)
