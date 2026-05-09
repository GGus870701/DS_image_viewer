import os
import re
import subprocess
import sys
import shutil

def main():
    py_file = 'DS image viewer.py'
    app_name = "DS_Image_Viewer"
    
    if not os.path.exists(py_file):
        print(f"Error: {py_file} 파일을 찾을 수 없습니다.")
        return

    # 1. 버전 정보 찾기 및 업데이트 (v1.XX 포맷)
    with open(py_file, 'r', encoding='utf-8') as f:
        content = f.read()

    match = re.search(r'self\.title\(f"DS Image Viewer v1\.(\d+)', content)
    
    if not match:
        print("버전 정보를 찾을 수 없어 1.00으로 시작합니다.")
        new_version_str = "1.00"
    else:
        current_minor = int(match.group(1))
        new_minor = current_minor + 1
        new_version_str = f"1.{new_minor:02d}"
        
        old_title_part = f'DS Image Viewer v1.{current_minor:02d}'
        new_title_part = f'DS Image Viewer v{new_version_str}'
        content = content.replace(old_title_part, new_title_part)
        
        with open(py_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
    print(f">>> 빌드 대상 버전: v{new_version_str}")
    
    # 2. Nuitka로 패키징 실행
    print(f"[{app_name}] Nuitka 컴파일을 시작합니다...")
    
    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--onefile",
        "--windows-console-mode=disable",
        "--enable-plugin=tk-inter",
        "--windows-icon-from-ico=ds viewer icon.ico",
        "--include-data-files=ds viewer icon.ico=ds viewer icon.ico",
        "--include-package=customtkinter",
        "--assume-yes-for-downloads",
        "--output-dir=dist",
        "--output-filename=" + app_name + ".exe",
        py_file
    ]
    
    # 명령어 실행
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\n[SUCCESS] 빌드가 성공적으로 완료되었습니다!")
        print(f"결과물: dist/{app_name}.exe")
        
        # 3. 임시 빌드 파일 정리
        print("\n임시 빌드 파일을 정리하는 중...")
        base_path = "dist"
        dummy_folders = [
            os.path.join(base_path, app_name + ".build"),
            os.path.join(base_path, app_name + ".onefile-build"),
            os.path.join(base_path, app_name + ".dist")
        ]
        
        # 파일명에 띄어쓰기가 있는 경우 Nuitka가 생성하는 기본 폴더명 대응
        safe_py_name = py_file.replace(".py", "")
        dummy_folders.extend([
            os.path.join(base_path, safe_py_name + ".build"),
            os.path.join(base_path, safe_py_name + ".onefile-build"),
            os.path.join(base_path, safe_py_name + ".dist")
        ])
        
        for folder in dummy_folders:
            if os.path.exists(folder):
                try:
                    shutil.rmtree(folder)
                    print(f"삭제 완료: {folder}")
                except Exception as e:
                    print(f"삭제 실패: {folder} ({e})")
        
        print("빌드 정리 완료.")
    else:
        print("\n[ERROR] 패키징 중 오류가 발생했습니다.")

if __name__ == "__main__":
    main()
