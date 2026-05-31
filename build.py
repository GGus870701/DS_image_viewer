import sys
sys.path.append('..')
from build_core.builder import build

def main():
    build(
        app_name           = "DS_Image_Viewer",
        main_script        = "main.py",
        version_file       = "core/version.py",
        collect_submodules = ["core", "ui", "PySide6.QtSvg"],
        keep_modules       = ["PySide6.QtNetwork"],
    )

if __name__ == "__main__":
    main()
