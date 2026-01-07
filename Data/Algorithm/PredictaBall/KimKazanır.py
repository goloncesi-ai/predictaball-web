#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 26 15:42:02 2025

@author: kagancalikoglu
"""

from PIL import Image, ImageDraw, ImageFont

def get_text_size(draw, text, font):
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    return right - left, bottom - top

def create_probability_image(
    home_team,
    away_team,
    home_logo,
    away_logo,
    home_prob,
    draw_prob,
    away_prob,
    conclusion_text,
    output_path=None
):

    width, height = 1080, 1350
    #bg = (79, 93, 47)
    bg = (90, 18, 18)  # Koyu bordo
    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    # Fonts
    try:
        font_header = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 110)
        font_sub    = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
        font_label  = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 45)
        font_big    = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 150)
        font_result = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 60)
        font_corner = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 40)
    except:
        font_header = font_sub = font_label = font_big = font_result = font_corner = ImageFont.load_default()

    # HEADER
    title = "KİM KAZANMAYA\nDAHA YAKIN?"
    draw.multiline_text((width/2, 80), title, fill="white", font=font_header, anchor="ma", align="center")

    # SUBHEADER
    sub = "3600 SİMÜLASYON\nSONUCUNA GÖRE:"
    draw.multiline_text((width/2, 310), sub, fill="white", font=font_sub, anchor="ma", align="center")

    # BOX PROPERTIES
    box_top = 480
    box_height = 420
    box_width = width // 3
    box_color = (120, 30, 30)
    box_border = (190, 50, 50)

    # LOGOS
    logo_size = 180
    home_img = Image.open(home_logo).convert("RGBA").resize((logo_size, logo_size))
    away_img = Image.open(away_logo).convert("RGBA").resize((logo_size, logo_size))

    items = [
        ("{}".format(home_team.split()[0]), home_prob, home_img),
        ("BERABERLİK", draw_prob, None),
        ("{}".format(away_team.split()[0]), away_prob, away_img)
    ]

    for i, (label, prob, logo) in enumerate(items):

        x1 = i * box_width
        y1 = box_top
        x2 = x1 + box_width
        y2 = y1 + box_height

        draw.rectangle([x1, y1, x2, y2], outline=box_border, width=5, fill=box_color)

        # Label
        lw, lh = get_text_size(draw, label, font_label)
        draw.text((x1 + box_width/2, y1 + 25), label, fill="white", font=font_label, anchor="ma")

        # Probability
        prob_text = f"{prob}%"
        pw, ph = get_text_size(draw, prob_text, font_big)
        draw.text((x1 + box_width/2, y1 + 130), prob_text, fill="white", font=font_big, anchor="ma")

        # Logos (left + right box only)
        if logo is not None:
            img.paste(logo, (int(x1 + (box_width - logo_size) / 2), int(y1 + 260)), logo)

    # RESULT TEXT
    draw.text((width/2, 1000), conclusion_text, fill="white", font=font_result, anchor="ma")

    # LEFT BOTTOM TAG
    draw.text((40, height - 40), "@goloncesi", fill="white", font=font_corner, anchor="ls")

    # SAVE
    # SAVE
    if output_path:
        img.save(output_path)
        print("Image created:", output_path)
    else:
        # Default fallback (original behavior)
        opath = f"/Users/kagancalikoglu/Documents/PredictaBall/Posts/KimKazanir_{home_team}vs{away_team}.png"
        img.save(opath)
        print("Image created (default):", opath)

    


