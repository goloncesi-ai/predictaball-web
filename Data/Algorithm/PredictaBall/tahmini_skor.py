#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 26 14:56:14 2025

@author: kagancalikoglu
"""

from PIL import Image, ImageDraw, ImageFont

def get_text_size(draw, text, font):
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    return right - left, bottom - top

def create_match_image(
    first_team_name,
    second_team_name,
    first_logo_path,
    second_logo_path,
    score_text,
    below_text,
    output_path=None
):

    width, height = 1080, 1350
    bg = (28, 49, 68)
    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    # ---- FORCE REAL FONTS HERE ----
    try:
        font_header = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 120)
        font_team   = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 60)
        font_score  = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 170)
        font_small  = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 55)
        font_corner = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 45)
    except:
        print("FONT LOAD FAILED — still using default")
        font_header = font_team = font_score = font_small = font_corner = ImageFont.load_default()

    # HEADER
    header_text = "TAHMİNİ SKOR"
    h_w, h_h = get_text_size(draw, header_text, font_header)
    draw.text(((width - h_w) / 2, 90), header_text, fill="white", font=font_header)

    # LOGOS
    logo_size = 420
    logo1 = Image.open(first_logo_path).convert("RGBA").resize((logo_size, logo_size))
    logo2 = Image.open(second_logo_path).convert("RGBA").resize((logo_size, logo_size))

    left_x = 90
    right_x = width - logo_size - 90
    y_logo = 270

    img.paste(logo1, (left_x, y_logo), logo1)
    img.paste(logo2, (right_x, y_logo), logo2)

    # TEAM NAMES
    t1_w, _ = get_text_size(draw, first_team_name, font_team)
    t2_w, _ = get_text_size(draw, second_team_name, font_team)

    draw.text((left_x + (logo_size - t1_w) / 2, y_logo + logo_size + 25),
              first_team_name, fill="white", font=font_team)

    draw.text((right_x + (logo_size - t2_w) / 2, y_logo + logo_size + 25),
              second_team_name, fill="white", font=font_team)

    # SCORE
    s_w, _ = get_text_size(draw, score_text, font_score)
    draw.text(((width - s_w) / 2, y_logo + logo_size + 120),
              score_text, fill="white", font=font_score)

    # BELOW TEXT
    b_w, _ = get_text_size(draw, below_text, font_small)
    draw.text(((width - b_w) / 2, y_logo + logo_size + 330),
              below_text, fill="white", font=font_small)

    # SIMULATION TEXT
    sim_text = "3600 Simulasyon Sonucuna Göre"
    sim_w, _ = get_text_size(draw, sim_text, font_small)
    draw.text(((width - sim_w) / 2, y_logo + logo_size + 420),
              sim_text, fill="white", font=font_small)

    # CORNER TAG
    corner_text = "@goloncesi"
    c_w, c_h = get_text_size(draw, corner_text, font_corner)
    draw.text((width - c_w - 40, height - c_h - 40),
              corner_text, fill="white", font=font_corner)

    # SAVE
    # SAVE
    if output_path:
        img.save(output_path)
        print("Image created:", output_path)
    else:
        post_name = f"{first_team_name}vs{second_team_name}.png"
        output_path = f"/Users/kagancalikoglu/Documents/PredictaBall/Posts/{post_name}"
        img.save(output_path)
        print("Image created:", output_path)



# ---------------------
# Example usage:
# ---------------------
if __name__ == "__main__":
    create_match_image(
        first_team_name="Brann",
        second_team_name="Fenerbahçe",
        first_logo_path="/Users/kagancalikoglu/Documents/PredictaBall/Logos/Brann.png",
        second_logo_path="/Users/kagancalikoglu/Documents/PredictaBall/Logos/Fenerbahçe.png",
        score_text="0-0",
        below_text="Avrupa Ligi Round 6"
    )
