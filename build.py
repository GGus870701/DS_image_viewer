import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
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
