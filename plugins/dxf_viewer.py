import os
import re
import math
import customtkinter as ctk
import ezdxf
from ezdxf import bbox
from ezdxf.math import Vec2
from PIL import Image, ImageDraw, ImageFont
from plugin_interface import BasePlugin
from tkinter import messagebox

class DxfViewerPlugin(BasePlugin):
    name = "DXF 뷰어"
    
    def __init__(self):
        self.doc_cache = None
        self.path_cache = None
        self.bbox_cache = None
        self.layers = {}
        self.app = None
        self.sidebar = None
        self.initial_scale = 1.0
        self.bg_color = "black" # Default background color
        self.obj_color_mode = "original" # "original", "black", "white"

    def on_activate(self, app, document_path, page_index=0):
        pass

    def _get_doc(self, path):
        if self.path_cache == path and self.doc_cache:
            return self.doc_cache, self.bbox_cache
        try:
            # 1. 표준 방식 시도
            try:
                doc = ezdxf.readfile(path)
            except Exception:
                # 2. 인코딩 명시적 시도 (한글 DXF 등 대응)
                try:
                    doc = ezdxf.readfile(path, encoding='cp949')
                except:
                    doc = ezdxf.readfile(path, encoding='utf-8')
            
            msp = doc.modelspace()
            extents = bbox.extents(msp)
            
            self.doc_cache, self.path_cache, self.bbox_cache = doc, path, extents
            return doc, extents
        except Exception:
            return None, None

    def handle_file(self, path):
        if not path.lower().endswith(".dxf"): return None
        doc, extents = self._get_doc(path)
        if not doc: return None
        
        msp = doc.modelspace()
        if not extents or not extents.has_data: return None
        
        min_xyz, max_xyz = None, None
        for attr_min, attr_max in [('extmin', 'extmax'), ('min', 'max')]:
            if hasattr(extents, attr_min):
                min_xyz, max_xyz = getattr(extents, attr_min), getattr(extents, attr_max)
                break
        if not min_xyz: min_xyz, max_xyz = extents[0], extents[1]
        
        d_w, d_h = max_xyz[0] - min_xyz[0], max_xyz[1] - min_xyz[1]
        # 메모리 절약을 위해 초기 해상도를 4000 -> 2048로 하향
        self.initial_scale = 2048.0 / max(d_w, d_h) if max(d_w, d_h) > 0 else 1.0
        
        self.layers = {layer.dxf.name: not (layer.is_off() or layer.is_frozen()) for layer in doc.layers}
        return self._render_internal(doc, extents, 0, 0, 1.0, 0, 0, is_initial=True)

    def render_viewport(self, path, width, height, zoom, off_x, off_y):
        doc, extents = self._get_doc(path)
        if not doc: return None
        return self._render_internal(doc, extents, width, height, zoom, off_x, off_y)

    def set_object_color_mode(self, mode):
        """객체 색상 모드 설정 (original, black, white)"""
        self.obj_color_mode = mode

    def _render_internal(self, doc, extents, cw, ch, zoom, off_x, off_y, is_initial=False):
        try:
            msp = doc.modelspace()
            min_xyz, max_xyz = None, None
            for attr_min, attr_max in [('extmin', 'extmax'), ('min', 'max')]:
                if hasattr(extents, attr_min):
                    min_xyz, max_xyz = getattr(extents, attr_min), getattr(extents, attr_max)
                    break
            if not min_xyz: min_xyz, max_xyz = extents[0], extents[1]
            
            d_min_x, d_max_y = float(min_xyz[0]), float(max_xyz[1])
            render_scale = self.initial_scale * zoom
            
            if is_initial:
                d_w, d_h = float(max_xyz[0] - min_xyz[0]), float(max_xyz[1] - min_xyz[1])
                img_w, img_h = int(d_w * render_scale), int(d_h * render_scale)
                img = Image.new("RGB", (max(1, img_w), max(1, img_h)), self.bg_color)
                draw = ImageDraw.Draw(img)
                def to_screen(x, y):
                    return (x - d_min_x) * render_scale, (d_max_y - y) * render_scale
            else:
                img = Image.new("RGB", (cw, ch), self.bg_color)
                draw = ImageDraw.Draw(img)
                def to_screen(x, y):
                    sx = (x - d_min_x) * render_scale + off_x
                    sy = (d_max_y - y) * render_scale + off_y
                    return sx, sy

            from ezdxf.colors import aci2rgb
            
            lt_patterns = {
                'HIDDEN': [0.25, -0.125], 'HIDDEN2': [0.125, -0.0625],
                'CENTER': [1.25, -0.25, 0.25, -0.25], 'CENTER2': [0.75, -0.125, 0.125, -0.125],
                'DASHED': [0.5, -0.25], 'DASHED2': [0.25, -0.125],
                'PHANTOM': [1.25, -0.25, 0.25, -0.25, 0.25, -0.25],
                'DOT': [0.0, -0.25], 'DOT2': [0.0, -0.125]
            }
            for lt in doc.linetypes:
                try:
                    if hasattr(lt, 'pattern'):
                        lt_patterns[lt.dxf.name.upper()] = lt.pattern
                except: continue

            def get_entity_pattern(entity):
                lt_name = getattr(entity.dxf, 'linetype', 'BYLAYER').upper()
                if lt_name == 'BYLAYER':
                    layer = doc.layers.get(entity.dxf.layer)
                    lt_name = layer.dxf.linetype.upper() if layer else 'CONTINUOUS'
                if lt_name in ('CONTINUOUS', 'BYBLOCK'): return None
                return lt_patterns.get(lt_name)

            def draw_line_custom(draw_obj, p1, p2, color, width, pattern, scale, offset=0, entity_ltscale=1.0):
                if not pattern:
                    draw_obj.line([p1, p2], fill=color, width=width)
                    return 0
                dx, dy = p2[0] - p1[0], p2[1] - p1[1]
                dist = math.hypot(dx, dy)
                if dist == 0: return offset
                vx, vy = dx / dist, dy / dist
                curr = 0
                global_ltscale = doc.header.get('$LTSCALE', 1.0)
                combined_scale = scale * global_ltscale * entity_ltscale
                pattern_sum = sum(abs(p) for p in pattern if p != 0) + (0.1 * len(pattern))
                total_px_len = pattern_sum * combined_scale
                if total_px_len > 150: combined_scale *= (150.0 / total_px_len)
                elif total_px_len < 10: combined_scale *= (15.0 / total_px_len)
                temp_offset = offset % (sum(abs(p) for p in pattern) * combined_scale)
                idx = 0
                while temp_offset > 0:
                    p_val = abs(pattern[idx % len(pattern)]) * combined_scale
                    if p_val == 0: p_val = 1
                    if temp_offset < p_val: break
                    temp_offset -= p_val
                    idx += 1
                first_segment = True
                while curr < dist:
                    p_val = abs(pattern[idx % len(pattern)]) * combined_scale
                    if p_val == 0: p_val = 1
                    if first_segment:
                        p_val -= temp_offset
                        first_segment = False
                    next_p = min(dist, curr + p_val)
                    if pattern[idx % len(pattern)] >= 0:
                        s = (p1[0] + vx * curr, p1[1] + vy * curr)
                        e = (p1[0] + vx * next_p, p1[1] + vy * next_p)
                        draw_obj.line([s, e], fill=color, width=width)
                    curr = next_p
                    idx += 1
                return (offset + dist)

            def get_line_width(entity, scale):
                if hasattr(entity.dxf, 'const_width') and entity.dxf.const_width > 0:
                    return max(1, int(entity.dxf.const_width * scale))
                lweight = getattr(entity.dxf, 'lineweight', -3)
                if lweight < 0:
                    layer = doc.layers.get(entity.dxf.layer)
                    lweight = layer.dxf.lineweight if layer else 25
                if lweight > 0:
                    return max(1, int((lweight / 100.0) * 8.0))
                return 1

            def draw_thick_segment(draw_obj, p1, p2, w1, w2, scale, color):
                s1, s2 = to_screen(p1[0], p1[1]), to_screen(p2[0], p2[1])
                dsx, dsy = s2[0] - s1[0], s2[1] - s1[1]
                dist = math.hypot(dsx, dsy)
                if dist <= 0.1: return
                vx, vy = -dsy / dist, dsx / dist
                h_w1, h_w2 = (w1 * scale) / 2.0, (w2 * scale) / 2.0
                c1 = (s1[0] + vx * h_w1, s1[1] + vy * h_w1)
                c2 = (s1[0] - vx * h_w1, s1[1] - vy * h_w1)
                c3 = (s2[0] - vx * h_w2, s2[1] - vy * h_w2)
                c4 = (s2[0] + vx * h_w2, s2[1] + vy * h_w2)
                draw_obj.polygon([c1, c2, c3, c4], fill=color)
                if h_w1 > 1.0:
                    draw_obj.ellipse([s1[0]-h_w1, s1[1]-h_w1, s1[0]+h_w1, s1[1]+h_w1], fill=color)
                if h_w2 > 1.0:
                    draw_obj.ellipse([s2[0]-h_w2, s2[1]-h_w2, s2[0]+h_w2, s2[1]+h_w2], fill=color)

            style_fonts = {}
            for style in doc.styles:
                if style.dxf.font:
                    style_fonts[style.dxf.name] = os.path.splitext(os.path.basename(style.dxf.font))[0]

            def get_font_for_entity(entity, scale):
                style_name = getattr(entity.dxf, 'style', 'Standard')
                font_base = style_fonts.get(style_name, 'malgun')
                font_file = f"C:/Windows/Fonts/{font_base}.ttf"
                if not os.path.exists(font_file):
                    for alt in ['malgun', 'arial', 'gulim', 'msgothic']:
                        if os.path.exists(f"C:/Windows/Fonts/{alt}.ttf"):
                            font_file = f"C:/Windows/Fonts/{alt}.ttf"; break
                cad_h = getattr(entity.dxf, 'height', getattr(entity.dxf, 'char_height', 2.5))
                txt_h = cad_h * scale
                if txt_h < 0.5: return None, 0
                actual_h = max(4, int(txt_h))
                try: return ImageFont.truetype(font_file, actual_h), actual_h
                except: return ImageFont.load_default(), 10

            def draw_entities(entities, draw_obj, scale):
                for entity in entities:
                    if not self.layers.get(entity.dxf.layer, True): continue
                    etype = entity.dxftype()
                    color_idx = entity.dxf.color
                    if color_idx == 256:
                        layer = doc.layers.get(entity.dxf.layer)
                        color_idx = layer.dxf.color if layer else 7
                    
                    rgb = aci2rgb(color_idx)
                    # Color inversion logic for readability
                    if self.bg_color == "white":
                        # If color is close to white, make it black
                        if rgb[0] > 220 and rgb[1] > 220 and rgb[2] > 220:
                            rgb = (0, 0, 0)
                    else: # Black background
                        # If color is close to black, make it white
                        if rgb[0] < 35 and rgb[1] < 35 and rgb[2] < 35:
                            rgb = (255, 255, 255)
                            
                    fill_color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
                    
                    # [신규] 객체 색상 강제 전환 로직
                    if self.obj_color_mode == "black":
                        fill_color = "#000000"
                    elif self.obj_color_mode == "white":
                        fill_color = "#FFFFFF"
                        
                    line_w = get_line_width(entity, scale)
                    pattern = get_entity_pattern(entity)
                    elt_scale = getattr(entity.dxf, 'ltscale', 1.0)

                    try:
                        if etype == 'LINE':
                            p1, p2 = to_screen(entity.dxf.start.x, entity.dxf.start.y), to_screen(entity.dxf.end.x, entity.dxf.end.y)
                            draw_line_custom(draw_obj, p1, p2, fill_color, line_w, pattern, scale, entity_ltscale=elt_scale)
                        
                        elif etype in ('LWPOLYLINE', 'POLYLINE'):
                            if etype == 'LWPOLYLINE':
                                points = list(entity.get_points(format='xyseb'))
                                const_w = getattr(entity.dxf, 'const_width', 0)
                            else:
                                verts = list(entity.vertices)
                                points = [(v.dxf.location.x, v.dxf.location.y, getattr(v.dxf, 'start_width', 0), getattr(v.dxf, 'end_width', 0), getattr(v.dxf, 'bulge', 0)) for v in verts]
                                const_w = 0
                            
                            has_width = const_w > 0 or any(p[2] > 0 or p[3] > 0 for p in points)
                            lt_offset = 0
                            
                            if has_width:
                                seg_idx = 0
                                for v_entity in entity.virtual_entities():
                                    vtype = v_entity.dxftype()
                                    if seg_idx < len(points):
                                        s_w = points[seg_idx][2] if points[seg_idx][2] > 0 else const_w
                                        e_w = points[seg_idx][3] if points[seg_idx][3] > 0 else const_w
                                    else: s_w = e_w = const_w
                                    
                                    if vtype == 'LINE':
                                        p1, p2 = (v_entity.dxf.start.x, v_entity.dxf.start.y), (v_entity.dxf.end.x, v_entity.dxf.end.y)
                                        draw_thick_segment(draw_obj, p1, p2, s_w, e_w, scale, fill_color)
                                        lt_offset += (math.hypot(p2[0]-p1[0], p2[1]-p1[1]) * scale)
                                    elif vtype == 'ARC':
                                        cx, cy, r = v_entity.dxf.center.x, v_entity.dxf.center.y, v_entity.dxf.radius
                                        s_ang, e_ang = math.radians(v_entity.dxf.start_angle), math.radians(v_entity.dxf.end_angle)
                                        delta = e_ang - s_ang
                                        if delta < 0: delta += 2 * math.pi
                                        num_f = max(8, int(abs(delta) * r * scale / 3.0))
                                        last_p = (cx + math.cos(s_ang) * r, cy + math.sin(s_ang) * r)
                                        for j in range(1, num_f + 1):
                                            curr_ang = s_ang + delta * (j / num_f)
                                            curr_p = (cx + math.cos(curr_ang) * r, cy + math.sin(curr_ang) * r)
                                            cw1 = s_w + (e_w - s_w) * ((j-1) / num_f)
                                            cw2 = s_w + (e_w - s_w) * (j / num_f)
                                            draw_thick_segment(draw_obj, last_p, curr_p, cw1, cw2, scale, fill_color)
                                            lt_offset += (math.hypot(curr_p[0]-last_p[0], curr_p[1]-last_p[1]) * scale)
                                            last_p = curr_p
                                    seg_idx += 1
                            else:
                                for v_entity in entity.virtual_entities():
                                    draw_entities([v_entity], draw_obj, scale)

                        elif etype == 'CIRCLE':
                            cx, cy = to_screen(entity.dxf.center.x, entity.dxf.center.y); r = entity.dxf.radius * scale
                            draw_obj.ellipse([cx-r, cy-r, cx+r, cy+r], outline=fill_color, width=line_w)
                        
                        elif etype == 'ARC':
                            cx, cy = to_screen(entity.dxf.center.x, entity.dxf.center.y); r = entity.dxf.radius * scale
                            s_ang, e_ang = 360 - entity.dxf.end_angle, 360 - entity.dxf.start_angle
                            if s_ang > e_ang: e_ang += 360
                            draw_obj.arc([cx-r, cy-r, cx+r, cy+r], start=s_ang, end=e_ang, fill=fill_color, width=line_w)
                        
                        elif etype in ('TEXT', 'MTEXT'):
                            if etype == 'TEXT': content = entity.dxf.text
                            else:
                                raw = entity.text if hasattr(entity, 'text') else ""
                                content = re.sub(r'[{}]', '', raw)
                                def unicode_repl(match):
                                    try: return chr(int(match.group(1), 16))
                                    except: return match.group(0)
                                content = re.sub(r'\\U\+([0-9A-Fa-f]{4})', unicode_repl, content)
                                content = re.sub(r'\\[L|l|O|o|K|k|X]', '', content)
                                content = re.sub(r'\\[A-Z0-9]+;|\\[a-z]+;?', '', content)
                                content = content.replace('\\P', ' ').replace('\\p', ' ')
                            content = content.replace('%%d', '°').replace('%%c', 'ø').replace('%%p', '±')
                            font, actual_h = get_font_for_entity(entity, scale)
                            if not font: continue

                            # Get rotation (handle MTEXT text_direction vector)
                            rotation = getattr(entity.dxf, 'rotation', 0)
                            if etype == 'MTEXT' and hasattr(entity.dxf, 'text_direction'):
                                tv = entity.dxf.text_direction
                                if tv and (tv[0] != 0 or tv[1] != 0):
                                    rotation = math.degrees(math.atan2(tv[1], tv[0]))
                            
                            if etype == 'TEXT':
                                halign, valign = getattr(entity.dxf, 'halign', 0), getattr(entity.dxf, 'valign', 0)
                                raw_pos = entity.dxf.insert if (halign == 0 and valign == 0) else entity.dxf.get('align_point', entity.dxf.insert)
                                h_code = {0:'l', 1:'m', 2:'r', 3:'m', 4:'m', 5:'m'}.get(halign, 'l')
                                v_code = {0:'s', 1:'b', 2:'m', 3:'t'}.get(valign, 's')
                                pil_anchor = h_code + v_code
                            else:
                                raw_pos = entity.dxf.insert
                                ap = getattr(entity.dxf, 'attachment_point', 1)
                                ap_map = {1:'lt', 2:'mt', 3:'rt', 4:'lm', 5:'mm', 6:'rm', 7:'ls', 8:'ms', 9:'rs'}
                                pil_anchor = ap_map.get(ap, 'ls')
                            pos = to_screen(raw_pos.x, raw_pos.y)
                            
                            if abs(rotation) < 0.1:
                                draw_obj.text(pos, content, fill=fill_color, font=font, anchor=pil_anchor)
                            else:
                                tw = draw_obj.textlength(content, font=font); th = actual_h * 1.5
                                txt_img = Image.new("RGBA", (int(tw+40), int(th+40)), (0,0,0,0))
                                ImageDraw.Draw(txt_img).text((tw/2+20, th/2+20), content, fill=fill_color, font=font, anchor="mm")
                                rotated = txt_img.rotate(rotation, expand=True, resample=Image.Resampling.BICUBIC)
                                img.paste(rotated, (int(pos[0] - rotated.width/2), int(pos[1] - rotated.height/2)), rotated)

                        elif etype in ('SOLID', 'TRACE'):
                            pts = [to_screen(entity.dxf.vtx0.x, entity.dxf.vtx0.y), to_screen(entity.dxf.vtx1.x, entity.dxf.vtx1.y), to_screen(entity.dxf.vtx2.x, entity.dxf.vtx2.y)]
                            if hasattr(entity.dxf, 'vtx3'): pts.append(to_screen(entity.dxf.vtx3.x, entity.dxf.vtx3.y))
                            draw_obj.polygon(pts, fill=fill_color)

                        elif etype in ('INSERT', 'DIMENSION'):
                            try:
                                for v_entity in entity.virtual_entities():
                                    draw_entities([v_entity], draw_obj, scale)
                            except: pass
                    except: continue

            draw_entities(msp, draw, render_scale)
            return img
        except: return None

    def on_image_change(self, app, path):
        self.app = app
        if path and path.lower().endswith('.dxf'):
            doc, _ = self._get_doc(path)
            if doc:
                self.layers = {layer.dxf.name: not (layer.is_off() or layer.is_frozen()) for layer in doc.layers}
                if self.sidebar: self.update_layer_ui()

    def on_embed(self, app, parent):
        self.app, self.sidebar = app, parent
        for child in parent.winfo_children(): child.destroy()
        
        # Header
        ctk.CTkLabel(parent, text="레이어 설정", font=("Malgun Gothic", 16, "bold"), text_color="#00d2d3").pack(pady=10)
        
        # Layer Scroll Frame
        self.scroll_frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.update_layer_ui()

    def toggle_background(self):
        self.bg_color = "white" if self.bg_color == "black" else "black"
        if self.app: self.app.render_image()

    def update_layer_ui(self):
        if not self.sidebar or not hasattr(self, 'scroll_frame'): return
        for child in self.scroll_frame.winfo_children(): child.destroy()
        for name in sorted(self.layers.keys()):
            cb = ctk.CTkCheckBox(self.scroll_frame, text=name, command=lambda n=name: self.toggle_layer(n), font=("Malgun Gothic", 12, "bold"))
            if self.layers[name]: cb.select()
            cb.pack(fill="x", padx=10, pady=2)

    def toggle_layer(self, name):
        self.layers[name] = not self.layers.get(name, True)
        if self.app: self.app.render_image()

    def register_menu(self): return {"label": "레이어 설정 (DXF)"}
