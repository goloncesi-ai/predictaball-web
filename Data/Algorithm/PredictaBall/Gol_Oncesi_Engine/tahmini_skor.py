from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

LOGO_FOLDER = Path("/Users/erdilsen/Documents/PredictaBall/Logos")
OUTPUT_FOLDER = Path("/Users/erdilsen/Documents/PredictaBall/Posts")
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

TEMPLATE_PATH = LOGO_FOLDER / "tahmini_skor.png"

def get_text_size(draw, text, font):
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    return right - left, bottom - top

def draw_centered_text(draw, text, box, font, fill="white"):
    x1, y1, x2, y2 = box
    tw, th = get_text_size(draw, text, font)
    x = x1 + (x2 - x1 - tw) / 2
    y = y1 + (y2 - y1 - th) / 2
    draw.text((x, y), text, font=font, fill=fill)

def paste_logo_in_box(base_img, logo_path, box, max_scale=0.9):
    x1, y1, x2, y2 = box
    box_w, box_h = x2 - x1, y2 - y1

    logo = Image.open(logo_path).convert("RGBA")
    lw, lh = logo.size

    max_w = int(box_w * max_scale)
    max_h = int(box_h * max_scale)
    scale = min(max_w / lw, max_h / lh)
    new_size = (int(lw * scale), int(lh * scale))
    logo = logo.resize(new_size, Image.LANCZOS)

    lw, lh = logo.size
    paste_x = int(x1 + (box_w - lw) / 2)
    paste_y = int(y1 + (box_h - lh) / 2)

    base_img.paste(logo, (paste_x, paste_y), logo)

def create_match_image(
    first_team_name,
    second_team_name,
    first_logo_path,
    second_logo_path,
    score_text,
    below_text=None,   # kept for compatibility, not used
):
    base = Image.open(TEMPLATE_PATH).convert("RGBA")
    width, height = base.size
    draw = ImageDraw.Draw(base)

    try:
        font_path = "/System/Library/Fonts/Helvetica.ttc"
        font_score = ImageFont.truetype(font_path, 190)
        font_sim   = ImageFont.truetype(font_path, 48)
    except Exception:
        font_score = font_sim = ImageFont.load_default()

    # Grey panel vertical bounds (from template)
    PANEL_Y1, PANEL_Y2 = 509, 841
    LEFT_BOX  = (46,  PANEL_Y1, 371, PANEL_Y2)
    MID_BOX   = (399, PANEL_Y1, 679, PANEL_Y2)
    RIGHT_BOX = (708, PANEL_Y1, 1033, PANEL_Y2)

    # Logos
    paste_logo_in_box(base, first_logo_path, LEFT_BOX)
    paste_logo_in_box(base, second_logo_path, RIGHT_BOX)

    # Score in middle box
    SCORE_BOX = (
        MID_BOX[0] + 20,
        MID_BOX[1] + 40,
        MID_BOX[2] - 20,
        MID_BOX[3] - 40,
    )
    draw_centered_text(draw, score_text, SCORE_BOX, font_score, fill="white")

    # "3600 Simulasyon Sonucuna Göre" BELOW the boxes
    sim_text = "3600 Simulasyon Sonucuna Göre"
    sim_box = (80, PANEL_Y2 + 65, width - 80, PANEL_Y2 + 65 + 60)
    draw_centered_text(draw, sim_text, sim_box, font_sim, fill="white")

    # Save
    post_name = f"{first_team_name}vs{second_team_name}_tahmini_skor.png"
    output_path = OUTPUT_FOLDER / post_name
    base.convert("RGB").save(output_path, format="PNG", quality=95)
    print("Tahmini Skor image created:", output_path)
