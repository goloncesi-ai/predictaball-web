from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict

def percent_int(x: float) -> int:
    return int(round(100.0 * x))

def build_conclusion_text(home_team: str, away_team: str, home_prob: int, draw_prob: int, away_prob: int) -> str:
    if home_prob > 50 and home_prob >= away_prob and home_prob >= draw_prob:
        ana_satir = f"{home_team} maçı kazanır."
    elif away_prob > 50 and away_prob >= home_prob and away_prob >= draw_prob:
        ana_satir = f"{away_team} maçı kazanır."
    elif draw_prob > 50:
        ana_satir = "Maç berabere biter."
    else:
        if home_prob > away_prob:
            ana_satir = f"{home_team} en az 1 puan alır."
        elif away_prob > home_prob:
            ana_satir = f"{away_team} en az 1 puan alır."
        else:
            ana_satir = "Maç berabere biter."
    return "ANA TAHMİN:\n\n" + ana_satir + "\n"

@dataclass
class ImageGenerator:
    logo_folder: Path

    def generate(self, home_team: str, away_team: str, combined: Dict[str, float], below_text: str = "Tactical formation sim + HMM mean adjust") -> None:
        """Optional image generation (depends on your local modules).

        Requires:
          - from KimKazanır import create_probability_image
          - from tahmini_skor import create_match_image
        """
        try:
            from KimKazanır import create_probability_image
            from tahmini_skor import create_match_image
        except Exception as e:
            raise ImportError(
                "KimKazanır/tahmini_skor modules not available in this environment. "
                "Run this on your local project where those files exist."
            ) from e

        home_prob = percent_int(combined["home_win"])
        draw_prob = percent_int(combined["draw"])
        away_prob = percent_int(combined["home_loss"])

        conclusion_text = build_conclusion_text(home_team, away_team, home_prob, draw_prob, away_prob)

        home_logo = self.logo_folder / f"{home_team}.png"
        away_logo = self.logo_folder / f"{away_team}.png"

        create_probability_image(
            home_team=home_team,
            away_team=away_team,
            home_logo=str(home_logo),
            away_logo=str(away_logo),
            home_prob=home_prob,
            draw_prob=draw_prob,
            away_prob=away_prob,
            conclusion_text=conclusion_text
        )

        create_match_image(
            first_team_name=home_team,
            second_team_name=away_team,
            first_logo_path=str(home_logo),
            second_logo_path=str(away_logo),
            score_text=combined["headline_score"],
            below_text=below_text
        )
