# DS Image Viewer Agent Guidelines

이 파일은 AI 에이전트가 DS Image Viewer 프로젝트를 작업할 때 참고해야 할 필수 환경 정보와 지침을 담고 있습니다.

## 1. 환경 정보 (Environment)
> [!IMPORTANT]
> PySide6 기반으로 리빌딩됨. 빌드 도구는 PyInstaller를 사용하며 DS_capture의 자동화 패턴을 따름.
- **Python Path**: `C:\Users\zars8\AppData\Local\Python\pythoncore-3.14-64\python.exe`
- **Python Version**: 3.14.3
- **Build Tool**: PyInstaller 6.20.0 이상
- **GUI Framework**: PySide6 (Qt for Python)

## 2. 프로젝트 아키텍처 (Architecture)
- **Main Script**: `main.py` (PySide6 기반 고성능 이미지 뷰어)
- **Core Engine**: `QGraphicsView` 기반 하드웨어 가속 렌더링
- **Build Script**: `build.py` (자동 버전 관리 및 walkthrough 기록 기능 포함)
- **Licensing**: HWID 기반 오프라인 라이센스 시스템 (DASAN_TECHNOLOGY_SAFETY 공통 키)
- **Key Features**: 화면 분할 모드(SplitView), 네비게이터(Mini-map), EXIF/GPS 정보 패널, TIF Stack 지원

## 3. 빌드 지침 (Build Instructions)
- **빌드 도구**: PyInstaller (via `build.py`)
- **빌드 실행 규칙**: `build.py`를 사용하여 버전 정보를 자동 갱신함.
- **아이콘**: `resources/ds_viewer.ico` 사용 (인라인 SVG 아이콘은 `ui/icon_data.py` 관리)

## 4. 작업 시 주의사항 (Important Notes)
- **파일명 준수**: 파일명은 스페이스 대신 언더바(`_`)를 사용하는 `DS_image_viewer.py` 형식을 유지할 것.
- **빌드 정보 자동화**: `build.py`가 `DS_image_viewer.py` 내의 `BUILD_VERSION`, `BUILD_DATE`, `BUILD_TIME`을 관리함.
- **라이센스**: `SECRET_KEY`는 모든 앱 공통(`DASAN_TECHNOLOGY_SAFETY_SECRET_KEY_@!`)이며, `app_name`은 `"DS_IMAGE_VIEWER"` 또는 `"ALL_ACCESS"`를 허용함.

## 5. UI/UX 및 아이콘 지침 (UI/UX & Icons)
- **작업표시줄 그룹화**: `AppUserModelID`를 `'ds.imageviewer.v1'`으로 설정하여 작업표시줄에서 독립된 아이콘으로 표시되도록 함.
- **폰트 통일**: 인터페이스 및 내부의 모든 한글 폰트는 **'맑은 고딕' (Malgun Gothic)**을 기본으로 사용함.
- **윈도우 아이콘**: 
    - `iconbitmap()`을 사용하여 제목 표시줄 아이콘을 설정함.
    - 모든 서브 윈도우(Toplevel)에도 명시적으로 아이콘을 지정할 것을 권장함.

## 6. 빌드 실행 방법
```powershell
# 1. 테스트 빌드 (빠름, dist_test 폴더 생성)
& 'C:\Users\zars8\AppData\Local\Python\pythoncore-3.14-64\python.exe' build.py test

# 2. 배포 빌드 (느림, dist_production 단일 EXE 생성)
& 'C:\Users\zars8\AppData\Local\Python\pythoncore-3.14-64\python.exe' build.py
```
