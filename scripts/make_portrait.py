import os
import numpy as np
from PIL import Image, ImageOps, ImageEnhance, ImageFilter

RAMP = ".:-~=+*#%@"

def generate_portrait(image_path, output_path, target_width=115):
    img = Image.open(image_path).convert("RGBA")
    
    aspect_ratio = img.height / img.width
    target_height = int(target_width * aspect_ratio * 0.52)
    img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
    
    r, g, b, alpha = img.split()
    alpha_arr = np.array(alpha)
    
    base_gray = Image.merge("RGB", (r, g, b)).convert("L")
    base_gray = ImageOps.autocontrast(base_gray, cutoff=(2, 2))
    enhanced = ImageEnhance.Sharpness(base_gray).enhance(2.0)
    enhanced = ImageEnhance.Contrast(enhanced).enhance(1.6)
    gray_arr = np.array(enhanced)
    
    edge_map = np.array(enhanced.filter(ImageFilter.FIND_EDGES))
    
    lines = []
    ramp_len = len(RAMP) - 1
    
    for y in range(target_height):
        line = ""
        for x in range(target_width):
            if alpha_arr[y, x] < 15 or gray_arr[y, x] < 10:
                line += " "
                continue
                
            lum = gray_arr[y, x]
            edge = edge_map[y, x]
            
            if edge > 75:
                char = "#"
            elif lum < 45:
                char = "." if y % 2 == 0 else ":"
            else:
                idx = int((lum / 255.0) * ramp_len)
                char = RAMP[idx]
                
            line += char
        lines.append(line)

    char_width = 6.2
    line_height = 9.2
    svg_width = int(target_width * char_width)
    svg_height = int(target_height * line_height + 30)

    total_duration = 3.5
    line_delay_step = total_duration / max(target_height, 1)

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_width} {svg_height}" width="100%" height="auto">',
        '  <style>',
        '    text {',
        '      font-family: "JetBrains Mono", Consolas, "Courier New", monospace;',
        '      font-size: 8.5px;',
        '      font-weight: bold;',
        '      fill: #58a6ff;',
        '      white-space: pre;',
        '      text-anchor: middle;',
        '    }',
        '  </style>',
        '  <rect width="100%" height="100%" fill="#0d1117" rx="8" />',
        '  <defs>'
    ]

    for i in range(target_height):
        delay = round(i * line_delay_step, 3)
        svg.append(
            f'    <clipPath id="wipe-{i}">'
            f'      <rect x="0" y="0" width="0" height="{svg_height}">'
            f'        <animate attributeName="width" from="0" to="{svg_width}" dur="0.45s" begin="{delay}s" fill="freeze" />'
            f'      </rect>'
            f'    </clipPath>'
        )

    svg.append('  </defs>')

    y_pos = 20
    for i, line in enumerate(lines):
        escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        svg.append(
            f'  <g clip-path="url(#wipe-{i})">'
            f'    <text x="50%" y="{y_pos}">{escaped}</text>'
            f'  </g>'
        )
        y_pos += line_height

    svg.append('</svg>')

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(svg))

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_file = os.path.join(base_dir, "headshot.png")
    output_file = os.path.join(base_dir, "assets", "ascii.svg")

    if not os.path.exists(input_file):
        print(f"❌ Cannot find: {input_file}")
    else:
        generate_portrait(input_file, output_file, target_width=115)
        print(f"✓ Generated centered: {output_file}")