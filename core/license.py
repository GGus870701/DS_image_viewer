"""
DS Image Viewer — HWID 기반 오프라인 라이센스 시스템
DS 계열 공통 SECRET_KEY 사용 (DASAN_TECHNOLOGY_SAFETY)
"""
import os
import sys
import json
import hmac
import hashlib
import subprocess

# DS 계열 공통 시크릿 키
SECRET_KEY = "DASAN_TECHNOLOGY_SAFETY_SECRET_KEY_@!"

# 라이센스 탐색 경로
LICENSE_CENTRAL_DIR = r"C:\license"


def _get_base_dir() -> str:
    """실행 파일 기준 베이스 디렉토리 반환"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(sys.argv[0]))


BASE_DIR = _get_base_dir()


def get_hwid() -> str:
    """마더보드 + 디스크 시리얼 기반 HWID 생성"""
    try:
        cmd_mb = 'powershell "Get-CimInstance -ClassName Win32_BaseBoard | Select-Object -ExpandProperty SerialNumber"'
        mb_serial = subprocess.check_output(cmd_mb, shell=True).decode('cp949').strip().splitlines()[0].strip()

        cmd_disk = 'powershell "Get-CimInstance -ClassName Win32_DiskDrive | Select-Object -ExpandProperty SerialNumber"'
        disk_serial = subprocess.check_output(cmd_disk, shell=True).decode('cp949').strip().splitlines()[0].strip()

        raw_id = f"DS_{mb_serial}_{disk_serial}"
        hash_id = hashlib.sha256(raw_id.encode()).hexdigest().upper()
        return f"{hash_id[:4]}-{hash_id[4:8]}-{hash_id[8:12]}"
    except Exception:
        return "ERR-UNKNOWN"


def check_license(app_name: str) -> tuple[bool, dict | str]:
    """
    라이센스 파일 검증.
    반환: (True, license_data_dict) 또는 (False, 실패_이유_str)
    """
    from datetime import datetime
    hwid = get_hwid()
    search_dirs = [LICENSE_CENTRAL_DIR, BASE_DIR]
    fail_reason = "라이센스 파일을 찾을 수 없습니다."

    for folder in search_dirs:
        if not os.path.exists(folder):
            continue
        try:
            for filename in os.listdir(folder):
                if not filename.lower().endswith(".lic"):
                    continue
                path = os.path.join(folder, filename)
                with open(path, 'r', encoding='utf-8-sig') as f:
                    data_raw = json.load(f)

                # 단일/복수 라이센스 모두 지원
                license_list = data_raw if isinstance(data_raw, list) else [data_raw]

                for data in license_list:
                    if data.get('hwid') != hwid:
                        continue
                    if data.get('app_name') not in [app_name, "ALL_ACCESS"]:
                        fail_reason = f"해당 라이센스는 {data.get('app_name')}용입니다."
                        continue

                    user_name = data.get('user_name')
                    expiry_str = data.get('expiry_date')
                    if not user_name or not expiry_str:
                        continue

                    # 서명 검증
                    msg = f"{data['hwid']}{data['app_name']}{expiry_str}{user_name}"
                    expected = hmac.new(SECRET_KEY.encode(), msg.encode(), hashlib.sha256).hexdigest()
                    if data.get('signature') != expected:
                        fail_reason = "라이센스 서명이 올바르지 않습니다."
                        continue

                    # 만료일 검증
                    if expiry_str != "PERMANENT":
                        expiry = datetime.strptime(expiry_str, "%Y-%m-%d")
                        if datetime.now() > expiry:
                            fail_reason = f"라이센스가 만료되었습니다. ({expiry_str})"
                            continue

                    return True, data
        except Exception:
            continue

    return False, fail_reason
