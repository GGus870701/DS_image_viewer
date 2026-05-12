import os
import re

def update_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. get_image_obj 보강
    target1 = 'def get_image_obj(self, path):'
    replacement1 = '''def get_image_obj(self, path):
        """플러그인 또는 PIL을 사용하여 이미지 객체 생성"""
        write_log(f"get_image_obj: Loading {path}")
        img = None
        for plugin in self.plugins:
            try:
                write_log(f"Trying plugin: {plugin.name}")
                img = plugin.handle_file(path)
                if img: 
                    write_log(f"Plugin {plugin.name} successfully handled the file.")
                    break
            except Exception as e:
                import traceback
                write_log(f"Plugin {plugin.name} error: {str(e)}\\n{traceback.format_exc()}")
                continue
        
        if not img:
            write_log("No plugin handled the file. Falling back to PIL.")
            img = Image.open(path)
        return img
    
    def _hidden_duplicate_remover(self): # 임시 마커
        pass'''
    
    # 중복 삽입 방지 및 교체
    if 'write_log(f"get_image_obj: Loading {path}")' not in content:
        # 기존 함수 본문까지 포함해서 교체하기 위해 정규표현식 사용하거나... 
        # 여기서는 단순 문자열 교체 시도 (이미 본문이 있는 경우 주의)
        # 본문 패턴: def get_image_obj(self, path):\n(.*?)\n    def load_image
        content = re.sub(r'def get_image_obj\(self, path\):.*?def load_image', 
                         replacement1 + '\n\n    def load_image', 
                         content, flags=re.DOTALL)

    # 2. load_image 에러 핸들링 보강
    target2 = 'messagebox.showerror("오류", f"이미지를 불러올 수 없습니다:\\n{str(e)}")'
    replacement2 = '''import traceback
            error_stack = traceback.format_exc()
            write_log(f"load_image error for {path}:\\n{str(e)}\\n{error_stack}")
            from tkinter import messagebox
            messagebox.showerror("오류", f"이미지를 불러올 수 없습니다:\\n{str(e)}\\n\\n상세 내용은 debug_log.txt를 확인하세요.")'''
    
    if 'debug_log.txt를 확인하세요' not in content:
        content = content.replace(target2, replacement2)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    update_file('DS_image_viewer.py')
    print("Update successful.")
