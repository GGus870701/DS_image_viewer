"""
DS Image Viewer v2 — 진입점
PySide6 기반 고성능 이미지 뷰어
"""
import sys
import os
import ctypes

# 작업표시줄 아이콘 그룹화 및 타이틀바 다크 모드 설정 (Agents.md 지침)
try:
    myappid = 'ds.imageviewer.v2'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    
    # Windows 10 (1809+) 및 Windows 11 다크 모드 타이틀바 지원 함수
    def set_dark_title_bar(window):
        if sys.platform == "win32":
            from ctypes import windll, byref, sizeof, c_int
            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            # 일부 구형 Win10 버전은 19를 사용하기도 함
            attr = 20
            dark_mode = c_int(1)
            hwnd = window.winId()
            windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, byref(dark_mode), sizeof(dark_mode))
except Exception:
    pass

from core.version import BUILD_VERSION
from core.license import check_license, get_hwid
from core.settings import settings


def main():
    # 1. 초기 파일 및 실행 모드 인수 확인 (무거운 임포트 전 가장 먼저 수행)
    is_convert_mode = False
    target_files = []
    initial_file = None
    
    if len(sys.argv) > 1:
        if "--convert" in sys.argv:
            is_convert_mode = True
            idx = sys.argv.index("--convert")
            for arg in sys.argv[idx+1:]:
                if os.path.exists(arg):
                    target_files.append(os.path.abspath(arg))
        else:
            arg = sys.argv[1]
            if os.path.isfile(arg):
                initial_file = arg

    # 2. 다중 파일 처리 최적화 (Fast-path for client instances)
    SERVER_NAME = "ds_convert_server_v1"
    global _app_mutex
    
    if is_convert_mode:
        from PySide6.QtNetwork import QLocalSocket
        import time
        
        # Windows 커널 수준의 완벽한 락(Mutex)을 사용하여 누가 첫 번째 창인지 결정
        ERROR_ALREADY_EXISTS = 183
        _app_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "DS_Convert_Mutex_V1")
        is_first_instance = (ctypes.windll.kernel32.GetLastError() != ERROR_ALREADY_EXISTS)
        
        if not is_first_instance:
            # 나는 클라이언트다 (첫 번째 창이 아님)
            # UI가 필요 없으므로 가장 가볍고 빠른 QCoreApplication만 로드하여 속도 극대화
            from PySide6.QtCore import QCoreApplication
            app_core = QCoreApplication.instance()
            if not app_core:
                app_core = QCoreApplication(sys.argv)
                
            socket = QLocalSocket()
            # 서버가 파이프를 열 때까지 최대 5초간 재시도하며 대기
            for _ in range(50):
                socket.connectToServer(SERVER_NAME)
                if socket.waitForConnected(100):
                    break
                time.sleep(0.1)
                
            if socket.state() == QLocalSocket.ConnectedState:
                if target_files:
                    data = "|".join(target_files).encode('utf-8')
                    socket.write(data)
                    socket.waitForBytesWritten(2000)
            sys.exit(0)

    # 3. 여기부터는 실제 창을 띄워야 하는 메인 인스턴스 (무거운 모듈 임포트 시작)
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QIcon
    from PySide6.QtNetwork import QLocalServer
    from ui.fonts import UI_FONT_NORMAL, UI_FONT_NAME
    from ui.license_dialog import show_license_error

    # Windows 작업 표시줄에 독립된 아이콘으로 표시되도록 설정
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('ds.imageviewer.v1')
    except Exception:
        pass

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
        
    app.setStyle("Fusion")  # DS Capture와 동일하게 Fusion 스타일 고정
    app.setApplicationName("DS Image Viewer")
    app.setApplicationVersion(BUILD_VERSION)
    app.setFont(UI_FONT_NORMAL)

    # 앱 아이콘 설정
    ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "ds_viewer.ico")
    if os.path.exists(ico_path):
        app.setWindowIcon(QIcon(ico_path))

    # 4. 라이센스 체크
    is_valid, lic_data = check_license("DS_IMAGE_VIEWER")
    if not is_valid:
        hwid = get_hwid()
        msg = (
            "유효한 라이센스를 찾을 수 없습니다.\n"
            "프로그램을 사용하려면 전용 라이센스 파일(*.lic)이 필요합니다."
        )
        show_license_error(hwid, msg if isinstance(lic_data, str) and not lic_data else lic_data or msg)
        return

    # 5. 변환기 모드 실행 (서버 인스턴스)
    if is_convert_mode:
        # 이전에 남아있던 비정상 파이프 쓰레기 청소
        QLocalServer.removeServer(SERVER_NAME)
        server = QLocalServer()
        server.listen(SERVER_NAME)
        
        from ui.convert_window import ConvertWindow
        window = ConvertWindow(initial_files=target_files)
        
        # 다른 인스턴스에서 데이터가 넘어오면 처리하는 콜백
        def _on_new_connection():
            client_socket = server.nextPendingConnection()
            if client_socket.waitForReadyRead(1000):
                data = client_socket.readAll().data().decode('utf-8')
                if data:
                    new_files = data.split("|")
                    window.add_files(new_files)
                    window.raise_()
                    window.activateWindow()
            client_socket.disconnectFromServer()
            
        server.newConnection.connect(_on_new_connection)
        
        try:
            set_dark_title_bar(window)
        except:
            pass
        window.show()
        sys.exit(app.exec())

    # 6. 일반 메인 윈도우 실행 (뷰어 모드)
    from ui.main_window import MainWindow
    window = MainWindow(lic_data, initial_file=initial_file)
    try:
        set_dark_title_bar(window)
    except:
        pass
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
