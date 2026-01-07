#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 26 17:02:42 2025

@author: kagancalikoglu
"""

from PIL import Image, ImageDraw, ImageFont

def get_size(draw, text, font):
    l, t, r, b = draw.textbbox((0,0), text, font=font)
    return r-l, b-t

def create_match_list_image(
    title,
    subtitle,
    matches,
    output_path="/Users/kagancalikoglu/Documents/PredictaBall/Posts/match_list.png"
):

    # --- CONSTANTS ---
    width = 1080
    box_height = 260
    box_spacing = 45
    top_space = 380
    bottom_space = 150

    # --- DYNAMIC HEIGHT ---
    total_box_area = len(matches) * (box_height + box_spacing)
    height = top_space + total_box_area + bottom_space

    # --- CANVAS ---
    bg = (235, 237, 239)
    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    # --- FONTS ---
    font_title   = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 45)
    font_sub     = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 55)
    font_team    = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 60)
    font_predict = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 52)  # bold görünecek
    font_score   = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 90)
    font_date    = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 40)
    font_score_italic = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 80)

    # --- HEADER (center aligned) ---
    draw.text((width/2, 120), title, fill="black", font=font_title, anchor="mm")
    draw.text((width/2, 230), subtitle, fill="black", font=font_sub, anchor="mm")

    # --- LOOP ---
    box_top = top_space
    left_margin = 30
    right_margin = 30

    for match in matches:
        home = match["home"]
        away = match["away"]
        score = match["score"]
        prediction = match["prediction"]
        date = match["date"]
        home_logo = match["home_logo"]
        away_logo = match["away_logo"]

        # FULL BOX
        draw.rectangle(
            [left_margin, box_top, width - right_margin, box_top + box_height],
            fill=(13, 35, 64)
        )

        # LOGOS
        logo_size = 95
        hl = Image.open(home_logo).convert("RGBA").resize((logo_size, logo_size))
        al = Image.open(away_logo).convert("RGBA").resize((logo_size, logo_size))

        img.paste(hl, (left_margin + 20, box_top + 18), hl)
        img.paste(al, (left_margin + 135, box_top + 18), al)

        # MATCH NAME (center vertically)
        match_text = f"{home} vs {away}"
        draw.text((left_margin + 20, box_top + 130), match_text, fill="white", font=font_team)

        # SCORE (RIGHT SIDE, italic + grey)
        score_w, _ = get_size(draw, score, font_score_italic)
        draw.text(
            (width - right_margin - score_w - 20, box_top + 75),
            score,
            fill="#D3D7E0",
            font=font_score_italic
        )

        # PREDICTION (BOLD EFFECT)
        draw.text(
            (left_margin + 20, box_top + 210),
            prediction,
            fill="#E8EEFF",
            font=font_predict
        )

        # DATE (RIGHT BOTTOM)
        draw.text(
            (width - right_margin - 260, box_top + 210),
            f"Tahmin {date}",
            fill="#C7D3EA",
            font=font_date
        )

        box_top += box_height + box_spacing

    img.save(output_path)
    print("Created polished version:", output_path)



matches = [
    {
        "home": "Alanyaspor",
        "away": "Antalyaspor",
        "score": "2-0",
        "prediction": "Alanya puan alır",
        "date": "",
        "home_logo": "/Users/kagancalikoglu/Documents/PredictaBall/Logos/Alanyaspor.png",
        "away_logo": "/Users/kagancalikoglu/Documents/PredictaBall/Logos/Antalyaspor.png"
    },
    {
        "home": "Beşiktaş",
        "away": "Gaziantep",
        "score": "1-1",
        "prediction": "Maç berabere biter",
        "date": "",
        "home_logo": "/Users/kagancalikoglu/Documents/PredictaBall/Logos/Beşiktaş.png",
        "away_logo": "/Users/kagancalikoglu/Documents/PredictaBall/Logos/Gaziantep.png"
    }
]

create_match_list_image(
    title="Trendyol SüperLig 08.12.2025 Maçları",
    subtitle="@goloncesi Tahminleri",
    matches=matches
)
