#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct  7 22:44:07 2025

@author: kagancalikoglu
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.linear_model import PoissonRegressor, Ridge
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import joblib

# =========================
# Config
# =========================
EXCEL_PATH = Path("Fenerbahce_Games_Input.xlsx")  # <-- put your file next to this script
SHEET_NAME = "Team_Inputs" # change if needed (can be sheet name string or index)
TEST_SIZE = 0.6
RANDOM_STATE = 42
ALPHA_POISSON = 0.1
ALPHA_RIDGE = 1.0
MODELS_DIR = Path("models_fc")
MODELS_DIR.mkdir(exist_ok=True)

# =========================
# Helpers
# =========================
def parse_formation(formation: str):
    """
    Returns a 4-tuple: (num_def, num_def_mid, num_att_mid, num_att).
    If formation has 3 numbers, split middle into def_mid/att_mid (floor to def_mid).
    """
    if not isinstance(formation, str):
        return (np.nan, np.nan, np.nan, np.nan)
    try:
        parts = [int(x) for x in formation.strip().split("-") if x != ""]
        if len(parts) == 4:
            return parts[0], parts[1], parts[2], parts[3]
        elif len(parts) == 3:
            num_def, mid, num_att = parts
            num_def_mid = mid // 2
            num_att_mid = mid - num_def_mid
            return num_def, num_def_mid, num_att_mid, num_att
        else:
            # Unexpected formats (e.g., "4-4-1-1-0" or malformed) -> NaNs
            return (np.nan, np.nan, np.nan, np.nan)
    except Exception:
        return (np.nan, np.nan, np.nan, np.nan)

def compute_line_avgs(df: pd.DataFrame, team_prefix: str):
    """Create GK, DEF_AVG(2-5), MID_AVG(6-9), ATT_AVG(10-11) for the given team prefix."""
    df[f"{team_prefix}_GK"] = df[f"{team_prefix}Player1"]
    df[f"{team_prefix}_DEF_AVG"] = df[[f"{team_prefix}Player{i}" for i in range(2, 6)]].mean(axis=1)
    df[f"{team_prefix}_MID_AVG"] = df[[f"{team_prefix}Player{i}" for i in range(6, 10)]].mean(axis=1)
    df[f"{team_prefix}_ATT_AVG"] = df[[f"{team_prefix}Player{i}" for i in range(10, 12)]].mean(axis=1)

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    # Formation parsing -> 4-cluster encoding
    for team in ["Team1", "Team2"]:
        parsed = df[f"{team}Formation"].apply(parse_formation)
        df[[f"{team}_num_def", f"{team}_num_def_mid", f"{team}_num_att_mid", f"{team}_num_att"]] = (
            pd.DataFrame(parsed.tolist(), index=df.index)
        )

    # Player line averages
    compute_line_avgs(df, "Team1")
    compute_line_avgs(df, "Team2")

    # Reaction / differences (Team1 perspective)
    df["GK_DIFF"] = df["Team1_GK"] - df["Team2_GK"]
    df["DEF_DIFF"] = df["Team1_DEF_AVG"] - df["Team2_ATT_AVG"]
    df["MID_DIFF"] = df["Team1_MID_AVG"] - df["Team2_MID_AVG"]
    df["ATT_DIFF"] = df["Team1_ATT_AVG"] - df["Team2_DEF_AVG"]

    # Home dummy
    df["Home"] = (df["Team1H_A"].astype(str).str.lower() == "home").astype(int)

    # Feature matrix
    feature_cols = [
        "Home",
        "Team1_GK","Team1_DEF_AVG","Team1_MID_AVG","Team1_ATT_AVG",
        "Team2_GK","Team2_DEF_AVG","Team2_MID_AVG","Team2_ATT_AVG",
        "GK_DIFF","DEF_DIFF","MID_DIFF","ATT_DIFF",
        "Team1_num_def","Team1_num_def_mid","Team1_num_att_mid","Team1_num_att",
        "Team2_num_def","Team2_num_def_mid","Team2_num_att_mid","Team2_num_att",
    ]
    return df, feature_cols

def train_eval_poisson(X, y, label):
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE)
    model = PoissonRegressor(alpha=ALPHA_POISSON, max_iter=2000)
    model.fit(X_tr, y_tr)
    pred = model.predict(X_te)
    rmse = mean_squared_error(y_te, pred, squared=False)
    print(f"[Poisson] {label} RMSE: {rmse:.4f}")
    return model

def train_eval_ridge(X, y, label):
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE)
    # safer solver to avoid scipy.sym_pos issue
    model = Ridge(alpha=ALPHA_RIDGE, solver="sparse_cg", random_state=RANDOM_STATE)
    model.fit(X_tr, y_tr)
    pred = model.predict(X_te)
    rmse = mean_squared_error(y_te, pred, squared=False)
    print(f"[Ridge]   {label} RMSE: {rmse:.4f}")
    return model

# =========================
# Load data
# =========================
if not EXCEL_PATH.exists():
    raise FileNotFoundError(f"Could not find {EXCEL_PATH.resolve()}")

df_raw = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)
df = df_raw.copy()

# Safety: strip column names (Excel often carries spaces)
df.columns = [c.strip() for c in df.columns]

# =========================
# Build features
# =========================
df, FEATURE_COLS = build_features(df)
X = df[FEATURE_COLS].copy()

# =========================
# Targets
# =========================
# Primary
y_T1_goals = df["Team1_Goals"]
y_T2_goals = df["Team2_Goals"]

# Secondary (Team1 & Team2) — ensure these columns exist in your Excel
secondary_pairs = [
    ("Team1_BigChances", "Team2_BigChances"),
    ("Team1_TotalShots", "Team2_TotalShots"),
    ("Team1_Corners", "Team2_Corners"),
    ("Team1_Passes", "Team2_Passes"),
    ("Team1_Tackels", "Team2_Tackels"),
    ("Team1_FreeKicks", "Team2_FreeKicks"),
    ("Team1_BallPosses", "Team2_BallPosses"),
]

# =========================
# Train primary models (Poisson for counts)
# =========================
print("\n=== Primary targets (Goals) ===")
model_T1_goals = train_eval_poisson(X, y_T1_goals, "Team1_Goals")
model_T2_goals = train_eval_poisson(X, y_T2_goals, "Team2_Goals")

joblib.dump(model_T1_goals, MODELS_DIR / "poisson_team1_goals.joblib")
joblib.dump(model_T2_goals, MODELS_DIR / "poisson_team2_goals.joblib")

# =========================
# Train secondary models (Ridge for continuous)
# =========================
secondary_models = {}
print("\n=== Secondary targets ===")
for t1, t2 in secondary_pairs:
    missing = [col for col in (t1, t2) if col not in df.columns]
    if missing:
        print(f"Skipping pair ({t1}, {t2}) — missing columns: {missing}")
        continue

    model_t1 = train_eval_ridge(X, df[t1], t1)
    model_t2 = train_eval_ridge(X, df[t2], t2)
    secondary_models[t1] = model_t1
    secondary_models[t2] = model_t2

    joblib.dump(model_t1, MODELS_DIR / f"ridge_{t1}.joblib")
    joblib.dump(model_t2, MODELS_DIR / f"ridge_{t2}.joblib")

# =========================
# Example prediction (Team1 perspective for a single row)
# =========================
print("\n=== Example prediction on a random row ===")
if len(X) > 0:
    sample = X.sample(1, random_state=RANDOM_STATE)
    idx = sample.index[0]

    out = {
        "Pred_Team1_Goals": float(model_T1_goals.predict(sample)[0]),
        "Pred_Team2_Goals": float(model_T2_goals.predict(sample)[0]),
    }
    for t1, t2 in secondary_pairs:
        if t1 in secondary_models and t2 in secondary_models:
            out[f"Pred_{t1}"] = float(secondary_models[t1].predict(sample)[0])
            out[f"Pred_{t2}"] = float(secondary_models[t2].predict(sample)[0])

    print(f"Row index: {idx}")
    for k, v in out.items():
        print(f"{k}: {v:.3f}")
else:
    print("No rows found in feature matrix.")

# =========================
# Notes / Tips
# =========================
# • The PoissonRegressor expects non-negative integer-like targets (counts). If your goals are integers (0,1,2,...), you’re good.
# • For secondary stats that are also counts (shots, corners), Poisson/NegativeBinomial GLMs could be used instead of Ridge.
# • If BallPosses is in [0,1], Ridge is a simple baseline; a Beta regression would be more principled.
# • Consider time-based splits (rolling origin) instead of random splits for production use.
