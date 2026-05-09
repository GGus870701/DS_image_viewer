import hashlib
import subprocess
import hmac
import json
import os

SECRET_KEY = "DS_CAPTURE_SECRET_KEY_2026_@!"
APP_NAME = "DS_IMAGE_VIEWER"

def get_hwid():
    try:
        # PowerShell을 통한 메인보드 및 디스크 시리얼 추출
        cmd_mb = 'powershell "Get-CimInstance -ClassName Win32_BaseBoard | Select-Object -ExpandProperty SerialNumber"'
        mb_serial = subprocess.check_output(cmd_mb, shell=True).decode('cp949').strip()
        
        cmd_disk = 'powershell "Get-CimInstance -ClassName Win32_DiskDrive | Select-Object -ExpandProperty SerialNumber"'
        disk_serial = subprocess.check_output(cmd_disk, shell=True).decode('cp949').strip()
        
        raw_id = f"DS_{mb_serial}_{disk_serial}"
        hash_id = hashlib.sha256(raw_id.encode()).hexdigest().upper()
        return f"{hash_id[:4]}-{hash_id[4:8]}-{hash_id[8:12]}"
    except Exception as e:
        print(f"Error getting HWID: {e}")
        return None

def generate_license():
    hwid = get_hwid()
    if not hwid:
        print("Failed to get HWID.")
        return

    user_name = "Developer_Test"
    expiry_date = "PERMANENT"
    
    # 서명 생성: HWID + APP_NAME + EXPIRY + USERNAME
    msg = f"{hwid}{APP_NAME}{expiry_date}{user_name}"
    signature = hmac.new(SECRET_KEY.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256).hexdigest()
    
    license_data = {
        "hwid": hwid,
        "app_name": APP_NAME,
        "user_name": user_name,
        "expiry_date": expiry_date,
        "signature": signature
    }
    
    # 라이센스 저장 경로 설정
    target_dir = r"C:\license"
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    
    file_path = os.path.join(target_dir, "ds_image_viewer_dev.lic")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(license_data, f, ensure_ascii=False, indent=4)
    
    print(f"Success! License generated for HWID: {hwid}")
    print(f"Path: {file_path}")

if __name__ == "__main__":
    generate_license()
