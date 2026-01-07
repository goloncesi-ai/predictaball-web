
import os
from PIL import Image, ImageDraw, ImageFont

# ================================================================
# SHARED HELPERS
# ================================================================
def get_font(size):
    try:
        return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
    except:
        return ImageFont.load_default()

def load_logo(name, assets_path, size=200):
    possible_names = [f"{name}.png", f"{name}.jpg", f"{name}.jpeg"]
    for n in possible_names:
        p = os.path.join(assets_path, "Logos", n)
        if os.path.exists(p):
            try:
                img = Image.open(p).convert("RGBA")
                # Maintain aspect ratio resize
                img.thumbnail((size, size), Image.Resampling.LANCZOS)
                return img
            except: pass
    return None

def get_text_size(draw, text, font):
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    return right - left, bottom - top

# ================================================================
# 1. GOL ONCESI / STANDARD STYLE (Existing)
# ================================================================
def create_standard_image(team1, team2, p1, pd, p2, score, output_path, assets_path):
    width, height = 1080, 1350
    bg_color = (15, 23, 42)
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    f_header = get_font(100)
    f_num = get_font(70)
    
    draw.text((width/2, 100), "MATCH SIMULATION", font=f_header, fill="white", anchor="ma")
    
    # Simple Bars
    bar_y = 400; bar_w = 800; bar_h = 80
    start_x = (width - bar_w) // 2
    
    w1 = int(bar_w * (p1/100))
    wd = int(bar_w * (pd/100))
    w2 = bar_w - w1 - wd
    
    draw.rectangle([start_x, bar_y, start_x+w1, bar_y+bar_h], fill="#3b82f6")
    draw.rectangle([start_x+w1, bar_y, start_x+w1+wd, bar_y+bar_h], fill="#64748b")
    draw.rectangle([start_x+w1+wd, bar_y, start_x+bar_w, bar_y+bar_h], fill="#f43f5e")

    draw.text((width/2, bar_y - 60), f"{team1} vs {team2}", font=get_font(50), fill="white", anchor="ma")
    draw.text((width/2, bar_y + 120), f"Win {int(p1)}% | Draw {int(pd)}% | Win {int(p2)}%", font=get_font(40), fill="#cbd5e1", anchor="ma")

    draw.text((width/2, 800), score, font=get_font(200), fill="white", anchor="ma")
    
    img.save(output_path)
    return output_path

# ================================================================
# 2. KIM KAZANIR STYLE (Red/Green Boxes)
# ================================================================
def create_kim_kazanir_image(team1, team2, p1, pd, p2, output_path, assets_path):
    width, height = 1080, 1350
    bg = (90, 18, 18) # Dark Red/Bordo
    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    # Fonts
    f_head = get_font(110)
    f_sub = get_font(48)
    f_label = get_font(45)
    f_big = get_font(150)
    f_res = get_font(60)

    # TEXT
    draw.multiline_text((width/2, 80), "KİM KAZANMAYA\nDAHA YAKIN?", fill="white", font=f_head, anchor="ma", align="center")
    draw.multiline_text((width/2, 350), "3600 SİMÜLASYON\nSONUCUNA GÖRE:", fill="white", font=f_sub, anchor="ma", align="center")

    # BOXES
    box_top = 500
    box_h = 420
    box_w = width // 3
    box_fill = (120, 30, 30)
    box_border = (190, 50, 50)

    items = [
        (team1.split()[0], p1),
        ("BERABERLIK", pd),
        (team2.split()[0], p2)
    ]

    for i, (label, prob) in enumerate(items):
        x1 = i * box_w
        y1 = box_top
        rect = [x1, y1, x1+box_w, y1+box_h]
        draw.rectangle(rect, fill=box_fill, outline=box_border, width=5)
        
        draw.text((x1 + box_w/2, y1 + 30), label, fill="white", font=f_label, anchor="ma")
        draw.text((x1 + box_w/2, y1 + 150), f"{int(prob)}%", fill="white", font=f_big, anchor="ma")

    # Conclusion
    winner = team1 if p1 > p2 else team2
    if abs(p1-p2) < 5: text = f"MAÇ ORTADA GÖRÜNÜYOR."
    else: text = f"FAVORİ: {winner.upper()}"
    
    draw.text((width/2, 1100), text, fill="white", font=f_res, anchor="ma")
    
    img.save(output_path)
    return output_path

# ================================================================
# 3. TAHMINI SKOR STYLE (Dark Blue, Side-by-Side)
# ================================================================
def create_tahmini_skor_image(team1, team2, score, output_path, assets_path):
    width, height = 1080, 1350
    bg = (28, 49, 68) # Dark Slate Blue
    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    f_head = get_font(120)
    f_team = get_font(60)
    f_score = get_font(170)

    draw.text((width/2, 90), "TAHMİNİ SKOR", fill="white", font=f_head, anchor="ma")

    # Logos
    l1 = load_logo(team1, assets_path, 400)
    l2 = load_logo(team2, assets_path, 400)
    
    y_logo = 300
    if l1: img.paste(l1, (100, y_logo), l1)
    if l2: img.paste(l2, (width-100-400, y_logo), l2)

    # Names
    draw.text((300, y_logo + 450), team1, fill="white", font=f_team, anchor="ma")
    draw.text((width-300, y_logo + 450), team2, fill="white", font=f_team, anchor="ma")

    # Score
    draw.text((width/2, y_logo + 600), score, fill="white", font=f_score, anchor="ma")

    draw.text((width/2, 1200), "@goloncesi", fill="white", font=get_font(40), anchor="ma")

    img.save(output_path)
    return output_path

# ================================================================
# DISPATCHER
# ================================================================
def create_prediction_image(team1, team2, p1, pd, p2, score, output_path, assets_path, style="standard"):
    if style == "kim_kazanir":
        return create_kim_kazanir_image(team1, team2, p1, pd, p2, output_path, assets_path)
    elif style == "tahmini_skor":
        return create_tahmini_skor_image(team1, team2, score, output_path, assets_path)
    else:
        return create_standard_image(team1, team2, p1, pd, p2, score, output_path, assets_path)
