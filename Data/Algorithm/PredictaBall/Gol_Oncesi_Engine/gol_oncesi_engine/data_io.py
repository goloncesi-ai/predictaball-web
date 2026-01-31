from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Dict

import numpy as np
import pandas as pd

TEAM1_PLAYERS = [f"Team1Player{i}" for i in range(1, 12)]
TEAM2_PLAYERS = [f"Team2Player{i}" for i in range(1, 12)]

NUMERIC_COLS = [
    *TEAM1_PLAYERS,
    *TEAM2_PLAYERS,
    "Win(3)_Draw(1)_Lose(0)",
    "Team1_Goals", "Team2_Goals",
    "Team1_BigChances", "Team1_TotalShots", "Team1_Corners",
    "Team1_Passes", "Team1_Tackels", "Team1_FreeKicks", "Team1_BallPosses",
    "Team2_BigChances", "Team2_TotalShots", "Team2_Corners",
    "Team2_Passes", "Team2_Tackels", "Team2_FreeKicks", "Team2_BallPosses",
]

def enforce_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

def safe_mean_std(series: pd.Series) -> Tuple[float, float]:
    # file is most-recent -> oldest; keep your intended "recent window":
    s = pd.to_numeric(series.iloc[1:11], errors="coerce").dropna()
    if len(s) == 0:
        return 5.0, 1.0
    mean = float(s.mean())
    std = float(s.std(ddof=1)) if s.std(ddof=1) > 0 else 0.5
    return mean, std

def team_file(main_folder: Path, team_name: str) -> Path:
    return main_folder / team_name / "mixed-seasons" / f"{team_name}_Games_Input.xlsx"

def read_team_df(main_folder: Path, team_name: str) -> pd.DataFrame:
    f = team_file(main_folder, team_name)
    if not f.exists():
        raise FileNotFoundError(f"Missing file for {team_name}: {f}")
    df = pd.read_excel(f, sheet_name="Sheet1")
    return enforce_numeric_columns(df)
