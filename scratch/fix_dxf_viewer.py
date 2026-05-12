
import sys

input_file = r'c:\ai_project\DS_image_viewer\plugins\dxf_viewer_utf8.py'
output_file = r'c:\ai_project\DS_image_viewer\plugins\dxf_viewer.py'

with open(input_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    line_num = i + 1
    
    # Correct mangled Korean name at line 11
    if line_num == 11:
        new_lines.append('    name = "DXF 뷰어"\n')
        continue
    
    # Correct mangled Korean at line 460
    if line_num == 460:
        new_lines.append('        ctk.CTkLabel(parent, text="DXF 레이어 설정", font=("Malgun Gothic", 16, "bold"), text_color="#00d2d3").pack(pady=10)\n')
        continue

    # Correct mangled Korean at line 469
    if line_num == 469:
        new_lines.append('            ctk.CTkLabel(self.scroll_frame, text="로드된 레이어 없음", font=("Malgun Gothic", 12)).pack(pady=20)\n')
        continue

    # Correct mangled Korean at line 480
    if line_num == 480:
        new_lines.append('    def register_menu(self): return {"label": "레이어 설정 (DXF)"}\n')
        continue

    # Start of LWPOLYLINE replacement (line 252 to 336)
    if line_num == 252:
        new_lines.append("                        elif etype == 'LWPOLYLINE':\n")
        new_lines.append("                            # LWPOLYLINE의 곡선 세그먼트를 bulge_to_arc를 이용해 정밀하게 렌더링\n")
        new_lines.append("                            from ezdxf.math import bulge_to_arc, Vec2\n")
        new_lines.append("                            import math\n")
        new_lines.append("                            \n")
        new_lines.append("                            points = entity.get_points() # (x, y, s_w, e_w, bulge)\n")
        new_lines.append("                            const_w = getattr(entity.dxf, 'const_width', 0)\n")
        new_lines.append("                            lt_offset = 0\n")
        new_lines.append("                            \n")
        new_lines.append("                            num_points = len(points)\n")
        new_lines.append("                            for i in range(num_points - (0 if entity.closed else 1)):\n")
        new_lines.append("                                p1_d = points[i]\n")
        new_lines.append("                                p2_d = points[(i+1) % num_points]\n")
        new_lines.append("                                \n")
        new_lines.append("                                s_w = p1_d[2] if p1_d[2] > 0 else const_w\n")
        new_lines.append("                                e_w = p1_d[3] if p1_d[3] > 0 else const_w\n")
        new_lines.append("                                bulge = p1_d[4]\n")
        new_lines.append("                                \n")
        new_lines.append("                                if bulge == 0:\n")
        new_lines.append("                                    # 직선 세그먼트\n")
        new_lines.append("                                    if s_w > 0 or e_w > 0:\n")
        new_lines.append("                                        draw_thick_segment(draw_obj, p1_d[:2], p2_d[:2], s_w, e_w, scale, fill_color)\n")
        new_lines.append("                                        d = math.hypot(p2_d[0]-p1_d[0], p2_d[1]-p1_d[1])\n")
        new_lines.append("                                        lt_offset += (d * scale)\n")
        new_lines.append("                                    else:\n")
        new_lines.append("                                        lt_offset = draw_line_custom(draw_obj, to_screen(p1_d[0], p1_d[1]), \n")
        new_lines.append("                                                                   to_screen(p2_d[0], p2_d[1]), fill_color, line_w, pattern, scale, \n")
        new_lines.append("                                                                   offset=lt_offset, entity_ltscale=elt_scale)\n")
        new_lines.append("                                else:\n")
        new_lines.append("                                    # 곡선 세그먼트 (Bulge)\n")
        new_lines.append("                                    try:\n")
        new_lines.append("                                        # bulge를 원호 파라미터로 변환\n")
        new_lines.append("                                        center, start_angle, end_angle, radius = bulge_to_arc(\n")
        new_lines.append("                                            Vec2(p1_d[0], p1_d[1]), Vec2(p2_d[0], p2_d[1]), bulge\n")
        new_lines.append("                                        )\n")
        new_lines.append("                                        \n")
        new_lines.append("                                        delta_angle = end_angle - start_angle\n")
        new_lines.append("                                        if bulge < 0 and delta_angle > 0: delta_angle -= 2*math.pi\n")
        new_lines.append("                                        if bulge > 0 and delta_angle < 0: delta_angle += 2*math.pi\n")
        new_lines.append("                                        \n")
        new_lines.append("                                        # 호 길이에 따른 분할 (최소 5등분, 5픽셀당 1분할)\n")
        new_lines.append("                                        arc_len = abs(delta_angle) * radius * scale\n")
        new_lines.append("                                        num_f = max(5, int(arc_len / 5.0))\n")
        new_lines.append("                                        \n")
        new_lines.append("                                        last_p = Vec2(p1_d[0], p1_d[1])\n")
        new_lines.append("                                        for j in range(1, num_f + 1):\n")
        new_lines.append("                                            curr_ang = start_angle + delta_angle * (j / num_f)\n")
        new_lines.append("                                            curr_p = Vec2(\n")
        new_lines.append("                                                center.x + math.cos(curr_ang) * radius,\n")
        new_lines.append("                                                center.y + math.sin(curr_ang) * radius\n")
        new_lines.append("                                            )\n")
        new_lines.append("                                            \n")
        new_lines.append("                                            # 폭 보간 (Width Interpolation)\n")
        new_lines.append("                                            cw1 = s_w + (e_w - s_w) * ((j-1) / num_f)\n")
        new_lines.append("                                            cw2 = s_w + (e_w - s_w) * (j / num_f)\n")
        new_lines.append("                                            \n")
        new_lines.append("                                            if cw1 > 0 or cw2 > 0:\n")
        new_lines.append("                                                draw_thick_segment(draw_obj, (last_p.x, last_p.y), (curr_p.x, curr_p.y), cw1, cw2, scale, fill_color)\n")
        new_lines.append("                                                d = math.hypot(curr_p.x-last_p.x, curr_p.y-last_p.y)\n")
        new_lines.append("                                                lt_offset += (d * scale)\n")
        new_lines.append("                                            else:\n")
        new_lines.append("                                                lt_offset = draw_line_custom(draw_obj, to_screen(last_p.x, last_p.y), \n")
        new_lines.append("                                                                           to_screen(curr_p.x, curr_p.y), fill_color, line_w, pattern, scale, \n")
        new_lines.append("                                                                           offset=lt_offset, entity_ltscale=elt_scale)\n")
        new_lines.append("                                            last_p = curr_p\n")
        new_lines.append("                                    except:\n")
        new_lines.append("                                        # 예외 발생 시 직선으로 폴백\n")
        new_lines.append("                                        if s_w > 0 or e_w > 0:\n")
        new_lines.append("                                            draw_thick_segment(draw_obj, p1_d[:2], p2_d[:2], s_w, e_w, scale, fill_color)\n")
        new_lines.append("                                            d = math.hypot(p2_d[0]-p1_d[0], p2_d[1]-p1_d[1])\n")
        new_lines.append("                                            lt_offset += (d * scale)\n")
        new_lines.append("                                        else:\n")
        new_lines.append("                                            lt_offset = draw_line_custom(draw_obj, to_screen(p1_d[0], p1_d[1]), \n")
        new_lines.append("                                                                       to_screen(p2_d[0], p2_d[1]), fill_color, line_w, pattern, scale, \n")
        new_lines.append("                                                                       offset=lt_offset, entity_ltscale=elt_scale)\n")
        new_lines.append("                        elif etype == 'POLYLINE':\n")
        new_lines.append("                            # 일반 POLYLINE도 bulge 로직 적용\n")
        new_lines.append("                            from ezdxf.math import bulge_to_arc, Vec2\n")
        new_lines.append("                            import math\n")
        new_lines.append("                            \n")
        new_lines.append("                            vertices = list(entity.vertices)\n")
        new_lines.append("                            num_verts = len(vertices)\n")
        new_lines.append("                            if num_verts < 2: continue\n")
        new_lines.append("                            \n")
        new_lines.append("                            lt_offset = 0\n")
        new_lines.append("                            for i in range(num_verts - (0 if entity.closed else 1)):\n")
        new_lines.append("                                v1 = vertices[i]\n")
        new_lines.append("                                v2 = vertices[(i+1) % num_verts]\n")
        new_lines.append("                                \n")
        new_lines.append("                                p1 = v1.dxf.location\n")
        new_lines.append("                                p2 = v2.dxf.location\n")
        new_lines.append("                                bulge = v1.dxf.bulge\n")
        new_lines.append("                                \n")
        new_lines.append("                                s_w = getattr(v1.dxf, 'start_width', 0)\n")
        new_lines.append("                                e_w = getattr(v1.dxf, 'end_width', 0)\n")
        new_lines.append("                                \n")
        new_lines.append("                                if bulge == 0:\n")
        new_lines.append("                                    if s_w > 0 or e_w > 0:\n")
        new_lines.append("                                        draw_thick_segment(draw_obj, (p1.x, p1.y), (p2.x, p2.y), s_w, e_w, scale, fill_color)\n")
        new_lines.append("                                        d = math.hypot(p2.x-p1.x, p2.y-p1.y)\n")
        new_lines.append("                                        lt_offset += (d * scale)\n")
        new_lines.append("                                    else:\n")
        new_lines.append("                                        lt_offset = draw_line_custom(draw_obj, to_screen(p1.x, p1.y), \n")
        new_lines.append("                                                                   to_screen(p2.x, p2.y), fill_color, line_w, pattern, scale, \n")
        new_lines.append("                                                                   offset=lt_offset, entity_ltscale=elt_scale)\n")
        new_lines.append("                                else:\n")
        new_lines.append("                                    try:\n")
        new_lines.append("                                        center, start_angle, end_angle, radius = bulge_to_arc(\n")
        new_lines.append("                                            Vec2(p1.x, p1.y), Vec2(p2.x, p2.y), bulge\n")
        new_lines.append("                                        )\n")
        new_lines.append("                                        delta_angle = end_angle - start_angle\n")
        new_lines.append("                                        if bulge < 0 and delta_angle > 0: delta_angle -= 2*math.pi\n")
        new_lines.append("                                        if bulge > 0 and delta_angle < 0: delta_angle += 2*math.pi\n")
        new_lines.append("                                        \n")
        new_lines.append("                                        arc_len = abs(delta_angle) * radius * scale\n")
        new_lines.append("                                        num_f = max(5, int(arc_len / 5.0))\n")
        new_lines.append("                                        \n")
        new_lines.append("                                        last_p = Vec2(p1.x, p1.y)\n")
        new_lines.append("                                        for j in range(1, num_f + 1):\n")
        new_lines.append("                                            curr_ang = start_angle + delta_angle * (j / num_f)\n")
        new_lines.append("                                            curr_p = Vec2(\n")
        new_lines.append("                                                center.x + math.cos(curr_ang) * radius,\n")
        new_lines.append("                                                center.y + math.sin(curr_ang) * radius\n")
        new_lines.append("                                            )\n")
        new_lines.append("                                            \n")
        new_lines.append("                                            cw1 = s_w + (e_w - s_w) * ((j-1) / num_f)\n")
        new_lines.append("                                            cw2 = s_w + (e_w - s_w) * (j / num_f)\n")
        new_lines.append("                                            \n")
        new_lines.append("                                            if cw1 > 0 or cw2 > 0:\n")
        new_lines.append("                                                draw_thick_segment(draw_obj, (last_p.x, last_p.y), (curr_p.x, curr_p.y), cw1, cw2, scale, fill_color)\n")
        new_lines.append("                                                d = math.hypot(curr_p.x-last_p.x, curr_p.y-last_p.y)\n")
        new_lines.append("                                                lt_offset += (d * scale)\n")
        new_lines.append("                                            else:\n")
        new_lines.append("                                                lt_offset = draw_line_custom(draw_obj, to_screen(last_p.x, last_p.y), \n")
        new_lines.append("                                                                           to_screen(curr_p.x, curr_p.y), fill_color, line_w, pattern, scale, \n")
        new_lines.append("                                                                           offset=lt_offset, entity_ltscale=elt_scale)\n")
        new_lines.append("                                            last_p = curr_p\n")
        new_lines.append("                                    except:\n")
        new_lines.append("                                        if s_w > 0 or e_w > 0:\n")
        new_lines.append("                                            draw_thick_segment(draw_obj, (p1.x, p1.y), (p2.x, p2.y), s_w, e_w, scale, fill_color)\n")
        new_lines.append("                                            d = math.hypot(p2.x-p1.x, p2.y-p1.y)\n")
        new_lines.append("                                            lt_offset += (d * scale)\n")
        new_lines.append("                                        else:\n")
        new_lines.append("                                            lt_offset = draw_line_custom(draw_obj, to_screen(p1.x, p1.y), \n")
        new_lines.append("                                                                       to_screen(p2.x, p2.y), fill_color, line_w, pattern, scale, \n")
        new_lines.append("                                                                       offset=lt_offset, entity_ltscale=elt_scale)\n")
        skip = True
        continue
    
    if skip:
        if line_num == 336: # End of POLYLINE block in original file
            skip = False
        continue
    
    if not skip:
        new_lines.append(line)

with open(output_file, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
