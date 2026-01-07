#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct  7 22:57:17 2025

@author: kagancalikoglu
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import PoissonRegressor, Ridge
from sklearn.metrics import r2_score, mean_squared_error
from pathlib import Path
import joblib

# ======================================================
# CONFIG
# ======================================================
EXCEL_PATH = Path("/Users/kagancalikoglu/Documents/PredictaBall/Inputs/Galatasaray_Games_Input.xlsx")
INPUT_SHEET = "Team_Inputs"
TEST_SHEET = "Team_Test"
MODELS_DIR = Path("models_fc")
MODELS_DIR.mkdir(exist_ok=True)

# ======================================================
# Helper Functions
# ======================================================
def parse_formation(formation: str):
    """Return (num_def, num_def_mid, num_att_mid, num_att) always 4 values."""
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
            return (np.nan, np.nan, np.nan, np.nan)
    except Exception:
        return (np.nan, np.nan, np.nan, np.nan)

def compute_line_avgs(df: pd.DataFrame, team_prefix: str):
    """Add GK, DEF_AVG(2-5), MID_AVG(6-9), ATT_AVG(10-11)."""
    df[f"{team_prefix}_GK"] = df[f"{team_prefix}Player1"]
    df[f"{team_prefix}_DEF_AVG"] = df[[f"{team_prefix}Player{i}" for i in range(2, 6)]].mean(axis=1)
    df[f"{team_prefix}_MID_AVG"] = df[[f"{team_prefix}Player{i}" for i in range(6, 10)]].mean(axis=1)
    df[f"{team_prefix}_ATT_AVG"] = df[[f"{team_prefix}Player{i}" for i in range(10, 12)]].mean(axis=1)

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute formation encoding, averages, diffs, and Home dummy."""
    for team in ["Team1", "Team2"]:
        parsed = df[f"{team}Formation"].apply(parse_formation)
        df[[f"{team}_num_def", f"{team}_num_def_mid", f"{team}_num_att_mid", f"{team}_num_att"]] = (
            pd.DataFrame(parsed.tolist(), index=df.index)
        )
        compute_line_avgs(df, team)

    # Reaction ratios (your choice — use division)
    df["GK_DIFF"]  = df["Team1_GK"] / df["Team2_GK"]
    df["DEF_DIFF"] = df["Team1_DEF_AVG"] / df["Team2_ATT_AVG"]
    df["MID_DIFF"] = df["Team1_MID_AVG"] / df["Team2_MID_AVG"]
    df["ATT_DIFF"] = df["Team1_ATT_AVG"] / df["Team2_DEF_AVG"]

    # Home dummy
    df["Home"] = (df["Team1H_A"].astype(str).str.lower() == "home").astype(int)
    
    #Adding the Opponent's Tier
    if "Opponent_Tier" in df.columns:
        df["Opponent_Tier"] = pd.to_numeric(df["Opponent_Tier"], errors="coerce").fillna(df["Opponent_Tier"].median())
    else:
        df["Opponent_Tier"] = 3  # default mid-tier if missing

    feature_cols = [
        "Home",
        "Opponent_Tier",
        "Team1_GK","Team1_DEF_AVG","Team1_MID_AVG","Team1_ATT_AVG",
        "Team2_GK","Team2_DEF_AVG","Team2_MID_AVG","Team2_ATT_AVG",
        "GK_DIFF","DEF_DIFF","MID_DIFF","ATT_DIFF",
        "Team1_num_def","Team1_num_def_mid","Team1_num_att_mid","Team1_num_att",
        "Team2_num_def","Team2_num_def_mid","Team2_num_att_mid","Team2_num_att",
    ]
    return df, feature_cols

def adjusted_r2_score(y_true, y_pred, n_features):
    r2 = r2_score(y_true, y_pred)
    n = len(y_true)
    adj_r2 = 1 - (1 - r2) * (n - 1) / (n - n_features - 1)
    return r2, adj_r2

def poisson_pseudo_r2(y_true, y_pred):
    eps = 1e-9
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    ll_model = np.sum(y_true * np.log(y_pred + eps) - y_pred)
    ll_null = np.sum(y_true * np.log(np.mean(y_true) + eps) - np.mean(y_true))
    return 1 - ll_model / ll_null

def train_poisson(X, y):
    model = PoissonRegressor(alpha=0.05, max_iter=2000)
    model.fit(X, y)
    return model

def train_ridge(X, y):
    model = Ridge(alpha=0.3, solver="sparse_cg", random_state=42)
    model.fit(X, y)
    return model

# ======================================================
# Load data
# ======================================================
print("Loading Excel data...")
train_df = pd.read_excel(EXCEL_PATH, sheet_name=INPUT_SHEET)
test_df  = pd.read_excel(EXCEL_PATH, sheet_name=TEST_SHEET)
train_df.columns = [c.strip() for c in train_df.columns]
test_df.columns  = [c.strip() for c in test_df.columns]

# ======================================================
# Build features
# ======================================================
train_df, feature_cols = build_features(train_df)
test_df, _             = build_features(test_df)
X_train, X_test = train_df[feature_cols], test_df[feature_cols]

# ======================================================
# Targets
# ======================================================
primary_targets = [("Team1_Goals", "Team2_Goals")]
secondary_targets = [
    ("Team1_BigChances", "Team2_BigChances"),
    ("Team1_TotalShots", "Team2_TotalShots"),
    ("Team1_Corners", "Team2_Corners"),
    ("Team1_Passes", "Team2_Passes"),
    ("Team1_Tackels", "Team2_Tackels"),
    ("Team1_FreeKicks", "Team2_FreeKicks"),
    ("Team1_BallPosses", "Team2_BallPosses"),
]

# ======================================================
# Train, evaluate, and forecast
# ======================================================
models = {}
summary_records = []

print("\n=== Training models and computing fit ===")
for model_type, pairs, trainer in [
    ("Poisson", primary_targets, train_poisson),
    ("Ridge", secondary_targets, train_ridge),
]:
    for t1, t2 in pairs:
        for target in [t1, t2]:
            if target not in train_df.columns:
                continue
            y = train_df[target]
            model = trainer(X_train, y)
            models[target] = model
            joblib.dump(model, MODELS_DIR / f"{model_type.lower()}_{target}.joblib")

            preds = model.predict(X_train)
            mse = mean_squared_error(y, preds)
            rmse = np.sqrt(mse)

            if model_type == "Poisson":
                pseudo_r2 = poisson_pseudo_r2(y, preds)
                summary_records.append({
                    "Target": target, "Model": model_type,
                    "RMSE": rmse, "Pseudo_R2": pseudo_r2,
                    "Intercept": model.intercept_,
                    **{f"coef_{f}": c for f, c in zip(feature_cols, model.coef_)}
                })
                print(f"[Poisson] {target}: RMSE={rmse:.3f}, Pseudo-R²={pseudo_r2:.3f}")
            else:
                r2, adj_r2 = adjusted_r2_score(y, preds, X_train.shape[1])
                summary_records.append({
                    "Target": target, "Model": model_type,
                    "RMSE": rmse, "R2": r2, "Adj_R2": adj_r2,
                    "Intercept": model.intercept_,
                    **{f"coef_{f}": c for f, c in zip(feature_cols, model.coef_)}
                })
                print(f"[Ridge]   {target}: RMSE={rmse:.3f}, R²={r2:.3f}, AdjR²={adj_r2:.3f}")

# ======================================================
# Forecast on Team_Test
# ======================================================
forecast_df = test_df.copy()
for t1, t2 in primary_targets + secondary_targets:
    if t1 in models:
        forecast_df[f"Pred_{t1}"] = models[t1].predict(X_test)
    if t2 in models:
        forecast_df[f"Pred_{t2}"] = models[t2].predict(X_test)

# ======================================================
# Save outputs
# ======================================================
cols_to_show = ["Team1", "Team2", "Team1H_A"] + [c for c in forecast_df.columns if c.startswith("Pred_")]
forecasts_df = forecast_df[cols_to_show]
forecasts_df.to_excel("/Users/kagancalikoglu/Documents/PredictaBall/Outputs/Forecasted_Team_Test.xlsx", index=False)
pd.DataFrame(summary_records).to_excel("/Users/kagancalikoglu/Documents/PredictaBall/Outputs/Model_Weights_and_Fit.xlsx", index=False)

print("\n=== Forecast sample ===")
print(forecasts_df.head())
print("\nSaved:")
print(" • Forecasted_Team_Test.xlsx  → match forecasts")
print(" • Model_Weights_and_Fit.xlsx → model weights & fit metrics")
