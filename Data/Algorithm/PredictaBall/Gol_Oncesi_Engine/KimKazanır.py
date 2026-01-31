from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

LOGO_FOLDER = Path("/Users/kagancalikoglu/Documents/PredictaBall/Logos")
OUTPUT_FOLDER = Path("/Users/kagancalikoglu/Documents/PredictaBall/Posts")
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

TEMPLATE_PATH = LOGO_FOLDER / "kim_kazanır.png"

def get_text_size(draw, text, font):
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    return right - left, bottom - top

def draw_centered_text(draw, text, box, font, fill="white"):
    x1, y1, x2, y2 = box
    tw, th = get_text_size(draw, text, font)
    x = x1 + (x2 - x1 - tw) / 2
    y = y1 + (y2 - y1 - th) / 2
    draw.text((x, y), text, font=font, fill=fill)

def paste_logo_overlap_bottom(base_img, logo_path, center_x, center_y, target_size):
    """
    Paste logo so that its center is at (center_x, center_y).
    If center_y == panel bottom, the panel line visually cuts the logo.
    """
    logo = Image.open(logo_path).convert("RGBA")
    logo = logo.resize((target_size, target_size), Image.LANCZOS)
    w, h = logo.size
    paste_x = int(center_x - w / 2)
    paste_y = int(center_y - h / 2)
    base_img.paste(logo, (paste_x, paste_y), logo)

def create_probability_image(
    home_team: str,
    away_team: str,
    home_logo: str,
    away_logo: str,
    home_prob: int,
    draw_prob: int,
    away_prob: int,
    conclusion_text: str,
):
    base = Image.open(TEMPLATE_PATH).convert("RGBA")
    width, height = base.size
    draw = ImageDraw.Draw(base)

    try:
        font_path = "/System/Library/Fonts/Helvetica.ttc"
        font_percent    = ImageFont.truetype(font_path, 140)  # smaller than before
        font_conclusion = ImageFont.truetype(font_path, 54)
    except Exception:
        font_percent = font_conclusion = ImageFont.load_default()

    # Panel coordinates from template
    PANEL_Y1, PANEL_Y2 = 557, 890
    LEFT_BOX  = (46,  PANEL_Y1, 371, PANEL_Y2)
    MID_BOX   = (399, PANEL_Y1, 679, PANEL_Y2)
    RIGHT_BOX = (708, PANEL_Y1, 1033, PANEL_Y2)

    # Upper area for percentages
    def percent_box(box, top_margin=40, side_margin=30, frac_height=0.55):
        x1, y1, x2, y2 = box
        h = y2 - y1
        return (
            x1 + side_margin,
            y1 + top_margin,
            x2 - side_margin,
            y1 + int(h * frac_height),
        )

    LEFT_PERCENT_BOX  = percent_box(LEFT_BOX)
    MID_PERCENT_BOX   = percent_box(MID_BOX)
    RIGHT_PERCENT_BOX = percent_box(RIGHT_BOX)

    draw_centered_text(draw, f"{home_prob}%", LEFT_PERCENT_BOX,  font_percent, fill="white")
    draw_centered_text(draw, f"{draw_prob}%", MID_PERCENT_BOX,   font_percent, fill="white")
    draw_centered_text(draw, f"{away_prob}%", RIGHT_PERCENT_BOX, font_percent, fill="white")

    # Bigger logos overlapping bottom edge of left/right boxes
    center_y = PANEL_Y2  # so the rectangle's bottom line cuts through the logo
    left_center_x  = (LEFT_BOX[0]  + LEFT_BOX[2])  // 2
    right_center_x = (RIGHT_BOX[0] + RIGHT_BOX[2]) // 2

    paste_logo_overlap_bottom(base, home_logo, left_center_x,  center_y, target_size=260)
    paste_logo_overlap_bottom(base, away_logo, right_center_x, center_y, target_size=260)

    # ANA TAHMİN explanation (only the meaningful line)
    lines = [ln.strip() for ln in conclusion_text.splitlines() if ln.strip()]
    if lines:
        main_line = lines[-1]  # e.g. "Fenerbahçe en az 1 puan alır."
        y_header_bottom = 392  # around bottom of "ANA TAHMİN" heading in template
        text_box = (80, y_header_bottom + 22, width - 80, y_header_bottom + 22 + 60)
        draw_centered_text(draw, main_line, text_box, font_conclusion, fill="white")

    # No footer text anymore

    out_name = f"KimKazanir_{home_team}vs{away_team}.png"
    out_path = OUTPUT_FOLDER / out_name
    base.convert("RGB").save(out_path, format="PNG", quality=95)
    print("KimKazanır image created:", out_path)
