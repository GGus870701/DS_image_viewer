import os
import time
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor, as_completed
from PIL import Image, ImageOps

from PySide6.QtCore import QObject, Signal, QThread

@dataclass
class ConvertSettings:
    rotation_mode: int # 0: None, 1: Left 90, 2: Right 90, 3: 180, 4: EXIF Auto
    resize_mode: int # 0: None, 1: Keep Aspect, 2: Fit Width, 3: Fit Height, 4: Pad, 5: Crop, 6: Stretch
    target_width: int
    target_height: int
    unit_is_percent: bool
    format_idx: int # 0: Original, 1: JPG, 2: PNG, 3: WEBP
    quality: int
    preserve_exif: bool
    
    loc_mode: int # 0: Same, 1: Specific, 2: Subfolder
    specific_dir: str
    subfolder_name: str
    
    conflict_mode: int # 0: Rename, 1: Overwrite
    use_prefix: bool
    prefix_str: str

def get_unique_filename(path):
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    counter = 2
    while os.path.exists(f"{base}({counter}){ext}"):
        counter += 1
    return f"{base}({counter}){ext}"

def process_single_image(args, preview_only=False):
    if len(args) == 2:
        file_path, settings = args
    else:
        file_path, settings, preview_only = args
        
    try:
        with Image.open(file_path) as img:
            original_format = img.format
            exif_data = img.info.get('exif') if settings.preserve_exif else None
            
            # 1. 회전 처리
            if settings.rotation_mode == 4: # EXIF Auto
                img = ImageOps.exif_transpose(img)
            elif settings.rotation_mode == 1: # Left 90
                img = img.transpose(Image.ROTATE_90)
            elif settings.rotation_mode == 2: # Right 90
                img = img.transpose(Image.ROTATE_270)
            elif settings.rotation_mode == 3: # 180
                img = img.transpose(Image.ROTATE_180)
                
            orig_w, orig_h = img.size
            
            # 2. 크기 조절
            if settings.resize_mode != 0: # Not None
                if settings.unit_is_percent:
                    tw = int(orig_w * (settings.target_width / 100.0))
                    th = int(orig_h * (settings.target_height / 100.0))
                else:
                    tw = settings.target_width
                    th = settings.target_height
                    
                target_size = (tw, th)
                
                if settings.resize_mode == 1: # 비율 유지 (Contain/Thumbnail)
                    img.thumbnail(target_size, Image.Resampling.LANCZOS)
                elif settings.resize_mode == 2: # 폭 맞춤
                    ratio = tw / float(orig_w)
                    new_h = int(float(orig_h) * float(ratio))
                    img = img.resize((tw, new_h), Image.Resampling.LANCZOS)
                elif settings.resize_mode == 3: # 높이 맞춤
                    ratio = th / float(orig_h)
                    new_w = int(float(orig_w) * float(ratio))
                    img = img.resize((new_w, th), Image.Resampling.LANCZOS)
                elif settings.resize_mode == 4: # 여백 붙이기 (Pad)
                    img = ImageOps.pad(img, target_size, method=Image.Resampling.LANCZOS, color=(0, 0, 0))
                elif settings.resize_mode == 5: # 여백 자르기 (Crop)
                    img = ImageOps.fit(img, target_size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
                elif settings.resize_mode == 6: # 꽉차게 늘리기 (Stretch)
                    img = img.resize(target_size, Image.Resampling.LANCZOS)

            # 포맷 변경 로직을 위해 RGB 변환 (JPG 등은 RGBA를 지원하지 않음)
            target_ext_mapping = {0: None, 1: '.jpg', 2: '.png', 3: '.webp'}
            target_ext = target_ext_mapping.get(settings.format_idx)
            
            if target_ext in ['.jpg', '.jpeg'] or (target_ext is None and original_format in ['JPEG', 'JPG']):
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')

            # 미리보기 모드일 경우 여기서 바로 이미지 리턴
            if preview_only:
                # 미리보기를 위해 복사본 반환 (with 블록 밖에서도 쓰기 위함)
                preview_img = img.copy()
                exif_info_str = "EXIF 정보가 없습니다."
                if exif_data:
                    try:
                        from PIL import ExifTags
                        exif = img.getexif()
                        if exif:
                            exif_lines = []
                            for k, v in exif.items():
                                tag = ExifTags.TAGS.get(k, k)
                                val_str = str(v)
                                if len(val_str) > 100:
                                    val_str = val_str[:100] + "..."
                                exif_lines.append(f"{tag}: {val_str}")
                            
                            # 추가적인 Exif IFD 데이터 (GPS 등) 추출 시도
                            try:
                                for ifd_id in [ExifTags.IFD.Exif, ExifTags.IFD.GPSInfo]:
                                    ifd_data = exif.get_ifd(ifd_id)
                                    for k, v in ifd_data.items():
                                        tag = ExifTags.TAGS.get(k, k)
                                        if ifd_id == ExifTags.IFD.GPSInfo:
                                            tag = ExifTags.GPSTAGS.get(k, k)
                                        val_str = str(v)
                                        if len(val_str) > 100:
                                            val_str = val_str[:100] + "..."
                                        exif_lines.append(f"[{ifd_id.name}] {tag}: {val_str}")
                            except Exception:
                                pass
                                
                            exif_info_str = "\n".join(exif_lines) if exif_lines else "파싱 가능한 EXIF 데이터가 없습니다."
                        else:
                            exif_info_str = "파싱 가능한 EXIF 데이터가 없습니다."
                    except Exception as e:
                        exif_info_str = f"EXIF 데이터 파싱 오류: {e}"
                        
                return True, preview_img, exif_info_str

            # 3. 저장 위치 결정
            orig_dir, orig_name = os.path.split(file_path)
            orig_base, orig_ext = os.path.splitext(orig_name)
            
            if target_ext is None:
                target_ext = orig_ext
            
            # 접두어 붙이기
            if settings.use_prefix and settings.prefix_str:
                new_base = f"{settings.prefix_str}{orig_base}"
            else:
                new_base = orig_base
                
            new_name = f"{new_base}{target_ext}"
            
            out_dir = orig_dir
            if settings.loc_mode == 1: # 특정 폴더
                out_dir = settings.specific_dir
            elif settings.loc_mode == 2: # 서브 폴더
                out_dir = os.path.join(orig_dir, settings.subfolder_name)
                
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, new_name)
            
            # 4. 이름 중복 처리
            if settings.conflict_mode == 0: # 이름 바꾸기
                out_path = get_unique_filename(out_path)
                
            # 5. 최종 저장
            save_kwargs = {}
            if target_ext.lower() in ['.jpg', '.jpeg', '.webp']:
                save_kwargs['quality'] = settings.quality
            if exif_data:
                save_kwargs['exif'] = exif_data
                
            img.save(out_path, **save_kwargs)
            return file_path, True, out_path, None
            
    except Exception as e:
        return file_path, False, None, str(e)


class BatchConverterWorker(QThread):
    progress = Signal(int, int, str) # current, total, last_file_path
    finished = Signal(int, int) # success_count, fail_count
    
    def __init__(self, file_paths, settings: ConvertSettings, max_workers=None):
        super().__init__()
        self.file_paths = file_paths
        self.settings = settings
        self.max_workers = max_workers
        self.is_cancelled = False

    def run(self):
        total = len(self.file_paths)
        success_count = 0
        fail_count = 0
        
        # 워커 데이터 준비
        tasks = [(path, self.settings) for path in self.file_paths]
        
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # map 대신 as_completed를 사용하여 진행률 실시간 보고
            futures = [executor.submit(process_single_image, task) for task in tasks]
            
            for i, future in enumerate(as_completed(futures), 1):
                if self.is_cancelled:
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                    
                path, success, out_path, error = future.result()
                if success:
                    success_count += 1
                else:
                    fail_count += 1
                    
                self.progress.emit(i, total, path)
                
        self.finished.emit(success_count, fail_count)

    def cancel(self):
        self.is_cancelled = True
