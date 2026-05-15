"""
DS Image Viewer — EXIF 및 GPS 정보 추출 모듈
Pillow(PIL) 기반
"""
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS


def get_exif_data(path: str) -> dict:
    """
    이미지 파일에서 EXIF 데이터를 추출하여 딕셔너리로 반환.
    GPS 정보는 별도의 'GPSInfo' 키에 파싱된 상태로 포함됨.
    """
    exif_result = {}
    try:
        with Image.open(path) as img:
            info = img._getexif()
            if not info:
                return {}

            for tag, value in info.items():
                decoded = TAGS.get(tag, tag)
                if decoded == "GPSInfo":
                    gps_data = {}
                    for t in value:
                        sub_decoded = GPSTAGS.get(t, t)
                        gps_data[sub_decoded] = value[t]
                    exif_result["GPSInfo"] = gps_data
                else:
                    exif_result[decoded] = value
    except Exception:
        pass
    return exif_result


def get_gps_coordinates(exif_data: dict) -> tuple[float, float] | None:
    """
    EXIF 데이터에서 위도, 경도 실수값(Decimal) 추출.
    반환: (lat, lon) 또는 None
    """
    gps_info = exif_data.get("GPSInfo")
    if not gps_info:
        return None

    def _to_decimal(values, ref):
        # values: (degrees, minutes, seconds)
        d = float(values[0])
        m = float(values[1])
        s = float(values[2])
        decimal = d + (m / 60.0) + (s / 3600.0)
        if ref in ['S', 'W']:
            decimal = -decimal
        return decimal

    try:
        lat_ref = gps_info.get("GPSLatitudeRef")
        lat_val = gps_info.get("GPSLatitude")
        lon_ref = gps_info.get("GPSLongitudeRef")
        lon_val = gps_info.get("GPSLongitude")

        if all([lat_ref, lat_val, lon_ref, lon_val]):
            lat = _to_decimal(lat_val, lat_ref)
            lon = _to_decimal(lon_val, lon_ref)
            return lat, lon
    except Exception:
        pass
    return None


def format_exif_display(exif_data: dict) -> list[tuple[str, str]]:
    """
    UI(InfoPanel) 표시를 위해 주요 EXIF 정보를 (Key, Value) 리스트로 정렬.
    """
    display_keys = [
        ("Make", "제조사"),
        ("Model", "모델"),
        ("DateTime", "촬영 일시"),
        ("ExposureTime", "노출 시간"),
        ("FNumber", "조리개 (F)"),
        ("ISOSpeedRatings", "ISO 감도"),
        ("FocalLength", "초점 거리"),
        ("Software", "소프트웨어"),
        ("HostComputer", "기기명"),
    ]
    
    results = []
    for key, label in display_keys:
        val = exif_data.get(key)
        if val is not None:
            # 특수 포맷 처리 (분수 등)
            if key == "FocalLength":
                val = f"{float(val):.1f} mm"
            elif key == "FNumber":
                val = f"f/{float(val):.1f}"
            elif key == "ExposureTime":
                if float(val) < 1:
                    val = f"1/{int(1/float(val))} s"
                else:
                    val = f"{val} s"
            results.append((label, str(val)))
            
    return results
