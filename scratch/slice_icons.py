from PIL import Image, ImageOps
import os

def slice_icons(sprite_path, output_dir):
    img = Image.open(sprite_path).convert("RGBA")
    w, h = img.size
    
    # 4x2 grid
    cols = 4
    rows = 2
    cell_w = w // cols
    cell_h = h // rows
    
    names = [
        "open", "split", "fit", "rotate",
        "flip", "gps", "info", "layer"
    ]
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    for i in range(rows):
        for j in range(cols):
            idx = i * cols + j
            if idx >= len(names):
                break
                
            left = j * cell_w
            top = i * cell_h
            right = left + cell_w
            bottom = top + cell_h
            
            icon = img.crop((left, top, right, bottom))
            
            # Convert black to transparent
            # Since icons are white on black, we can use the max of R,G,B as Alpha
            datas = icon.getdata()
            newData = []
            for item in datas:
                # item is (R, G, B, A)
                # Alpha based on brightness (assuming white icon on black)
                brightness = max(item[0], item[1], item[2])
                newData.append((255, 255, 255, brightness))
            
            icon.putdata(newData)
            
            # Trim empty space
            bbox = icon.getbbox()
            if bbox:
                icon = icon.crop(bbox)
                
            # Resize to a standard size (e.g., 64x64) for better quality when scaled down
            icon.thumbnail((64, 64), Image.Resampling.LANCZOS)
            
            save_path = os.path.join(output_dir, f"{names[idx]}.png")
            icon.save(save_path)
            print(f"Saved {save_path}")

if __name__ == "__main__":
    # Use the generated image path
    sprite_file = r"C:\Users\zars8\.gemini\antigravity\brain\3221606f-a5c5-442c-bbba-3b6fc102ba69\ds_viewer_icons_sprite_1778844159860.png"
    output_folder = r"c:\ai_project\DS_image_viewer\assets\icons"
    slice_icons(sprite_file, output_folder)
