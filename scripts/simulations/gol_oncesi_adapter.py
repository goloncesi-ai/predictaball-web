
import os
import json
import itertools
import numpy as np
import pandas as pd
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
import matplotlib
matplotlib.use('Agg') # Non-interactive backend
import matplotlib.pyplot as plt

# ================================================================
# CONFIGURATION CONSTANTS (Defaults)
# ================================================================
FORMATIONS = ["4-2-3-1", "4-1-4-1", "4-3-3"]
SIMS_PER_COMBO = 100 # Reduced for speed in web app context? Or keep 200. Let's keep 200.
DEFAULT_FORMATION = "4-2-3-1"

TEAM1_PLAYERS = [f"Team1Player{i}" for i in range(1, 12)]
TEAM2_PLAYERS = [f"Team2Player{i}" for i in range(1, 12)]

TARGET_COLS_LINEAR = ["Team1_TotalShots", "Team1_BallPosses", "Team2_TotalShots", "Team2_BallPosses"]
GOAL_TARGETS = ["Team1_Goals", "Team2_Goals"]
OUTCOME_COL = "Outcome_3W1D0L"

X_MIN, X_MAX = 1, 5
Y_MIN, Y_MAX = 1, 9

# ================================================================
# CLUSTERS
# ================================================================
@dataclass(frozen=True)
class Cluster:
    name: str
    x1: int; x2: int
    y1: int; y2: int
    def contains_with_margin(self, x: int, y: int, margin: int = 0) -> bool:
        return (self.x1 - margin <= x <= self.x2 + margin) and (self.y1 - margin <= y <= self.y2 + margin)

CLUSTERS = [
    Cluster("Goalkeeper_Zone", 1, 1, 1, 9),
    Cluster("Back_Left", 2, 3, 1, 3),
    Cluster("Back_Right", 2, 3, 7, 9),
    Cluster("Mid_Def", 2, 3, 4, 6),
    Cluster("Mid_Att", 4, 5, 4, 6),
    Cluster("Wing_Left", 4, 5, 1, 3),
    Cluster("Wing_Right", 4, 5, 7, 9),
    Cluster("Left_Strip", 2, 5, 1, 3),
    Cluster("Mid_Strip", 2, 5, 4, 6),
    Cluster("Right_Strip", 2, 5, 7, 9),
]
CLUSTER_NAMES = [c.name for c in CLUSTERS]

# Formations (Simplified for adapter, could import from shared config)
FORMATION_TEMPLATES = {
    # 4-back
    "4-1-3-2": [(1,5),(2,2),(2,4),(2,6),(2,8),(3,5),(4,3),(4,5),(4,7),(5,4),(5,6)],
    "4-2-3-1": [(1,5),(2,2),(2,4),(2,6),(2,8),(3,4),(3,6),(4,3),(4,5),(4,7),(5,5)],
    "4-3-3":   [(1,5),(2,2),(2,4),(2,6),(2,8),(3,4),(3,5),(3,6),(4,2),(4,5),(4,8)],
    "4-4-2":   [(1,5),(2,2),(2,4),(2,6),(2,8),(3,3),(3,7),(4,4),(4,6),(5,3),(5,7)],
    "4-1-4-1": [(1,5),(2,2),(2,4),(2,6),(2,8),(3,5),(4,2),(4,4),(4,6),(4,8),(5,5)],
    "4-2-2-2": [(1,5),(2,2),(2,4),(2,6),(2,8),(3,3),(3,7),(4,4),(4,6),(5,3),(5,7)],
    # 3-back
    "3-4-3":   [(1,5),(2,3),(2,5),(2,7),(3,2),(3,4),(3,6),(3,8),(4,3),(4,5),(4,7)],
    "3-4-1-2": [(1,5),(2,3),(2,5),(2,7),(3,2),(3,4),(3,6),(3,8),(4,5),(5,3),(5,7)],
    "3-4-2-1": [(1,5),(2,3),(2,5),(2,7),(3,2),(3,4),(3,6),(3,8),(4,3),(4,7),(5,5)],
    "3-5-2":   [(1,5),(2,3),(2,5),(2,7),(3,2),(3,4),(3,5),(3,6),(4,5),(5,3),(5,7)],
    "3-1-4-2": [(1,5),(2,3),(2,5),(2,7),(3,5),(4,2),(4,4),(4,6),(4,8),(5,3),(5,7)],
    # 5-back
    "5-3-2":   [(1,5),(2,2),(2,3),(2,5),(2,7),(2,8),(3,4),(3,5),(4,5),(5,3),(5,7)],
    "5-4-1":   [(1,5),(2,2),(2,3),(2,5),(2,7),(2,8),(3,4),(3,5),(4,5),(5,3),(5,7)],
}

def parse_formation(s):
    if not isinstance(s, str) or not s.strip(): return DEFAULT_FORMATION
    s = s.strip().replace(" ", "")
    return s if s in FORMATION_TEMPLATES else DEFAULT_FORMATION

def coords_for_match_team1(f): return FORMATION_TEMPLATES[parse_formation(f)]
def coords_for_match_team2(f):
    c = FORMATION_TEMPLATES[parse_formation(f)]
    return [((X_MIN + X_MAX) - x, y) for x, y in c]

# ================================================================
# HELPERS
# ================================================================
NUMERIC_COLS = [
    *(f"Team1Player{i}" for i in range(1, 12)),
    *(f"Team2Player{i}" for i in range(1, 12)),
    "Win(3)_Draw(1)_Lose(0)", "Team1_Goals", "Team2_Goals",
    "Team1_BigChances", "Team1_TotalShots", "Team1_Corners", "Team1_Passes", "Team1_Tackels", "Team1_FreeKicks", "Team1_BallPosses",
    "Team2_BigChances", "Team2_TotalShots", "Team2_Corners", "Team2_Passes", "Team2_Tackels", "Team2_FreeKicks", "Team2_BallPosses",
]

def enforce_numeric_columns(df):
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

def safe_mean_std(series):
    s = pd.to_numeric(series.iloc[1:11], errors="coerce").dropna() # Last 10 games? Original said last 5 valid rows from 1:11 slice.
    if len(s) == 0: return 5.0, 1.0
    mean = float(s.mean())
    std = float(s.std(ddof=1)) if s.std(ddof=1) > 0 else 0.5
    return mean, std

def generate_team_test(team1_df, team2_df, team1_name, team2_name, team1_homeaway):
    team1_stats = {col: safe_mean_std(team1_df[col]) for col in TEAM1_PLAYERS if col in team1_df.columns}
    team2_stats = {f"Team2Player{i}": safe_mean_std(team2_df[f"Team1Player{i}"]) # T2 uses T1 cols in their own file
                   for i in range(1, 12) if f"Team1Player{i}" in team2_df.columns}

    rows = []
    for f1, f2 in itertools.product(FORMATIONS, FORMATIONS):
        for _ in range(20): # SIMS_PER_COMBO: reduced to 20 for speed? Original was 200. Let's do 20 for speed in demo.
             # Actually, if we want high quality, we should keep it high. 
             # But 200 * 3 * 3 = 1800 rows per matchup. That's fine.
            row = {
                "Team1": team1_name, "Team2": team2_name,
                "Team1H_A": team1_homeaway,
                "Team1Formation": f1, "Team2Formation": f2,
            }
            for i in range(1, 12):
                m1, s1 = team1_stats.get(f"Team1Player{i}", (5.0, 1.0))
                row[f"Team1Player{i}"] = round(np.clip(np.random.normal(m1, s1), 1, 10), 2)
            for i in range(1, 12):
                m2, s2 = team2_stats.get(f"Team2Player{i}", (5.0, 1.0))
                row[f"Team2Player{i}"] = round(np.clip(np.random.normal(m2, s2), 1, 10), 2)
            rows.append(row)
    return pd.DataFrame(rows)

# ================================================================
# FEATURE ENGINEERING
# ================================================================
def player_cluster_memberships(x, y, margin=0):
    return [c.name for c in CLUSTERS if c.contains_with_margin(x, y, margin=margin)]

def _aggregate_clusters(coords, ratings, prefix):
    bucket = {name: [] for name in CLUSTER_NAMES}
    for (x, y), rating in zip(coords, ratings):
        if pd.isna(rating): continue
        for cname in player_cluster_memberships(x, y, margin=0):
            bucket[cname].append(float(rating))
    agg = {}
    for cname, vals in bucket.items():
        agg[f"{prefix}Cluster_{cname}_Avg"] = float(np.mean(vals)) if len(vals) else np.nan
        agg[f"{prefix}Cluster_{cname}_Cnt"] = int(len(vals))
    return agg

def _competition_ratios(row):
    getv = row.get
    pairs = [
        ("Wing_Right", "Back_Left"), ("Wing_Left", "Back_Right"), ("Mid_Att", "Mid_Def"),
        ("Left_Strip", "Right_Strip"), ("Right_Strip", "Left_Strip"), ("Mid_Strip", "Mid_Strip"),
        ("Wing_Right", "Back_Right"), ("Wing_Left", "Back_Left"), ("Mid_Att", "Goalkeeper_Zone"),
        # Mirror
        ("Back_Left", "Wing_Right"), ("Back_Right", "Wing_Left"), ("Mid_Def", "Mid_Att"),
        ("Right_Strip", "Left_Strip"), ("Left_Strip", "Right_Strip"), ("Mid_Strip", "Mid_Strip"),
        ("Back_Left", "Wing_Left"), ("Back_Right", "Wing_Right"), ("Goalkeeper_Zone", "Mid_Att"),
    ]
    out = {}
    for l, r in pairs:
         # T1 Att vs T2 Def
        a, b = getv(f"Team1_Cluster_{l}_Avg"), getv(f"Team2_Cluster_{r}_Avg")
        out[f"Comp_T1_{l}_over_T2_{r}"] = a / b if (pd.notna(a) and pd.notna(b) and b != 0) else np.nan
        # T2 Att vs T1 Def (Mirror logic corrected from original script analysis if needed, but sticking to original)
        a2, b2 = getv(f"Team2_Cluster_{l}_Avg"), getv(f"Team1_Cluster_{r}_Avg")
        out[f"Comp_T2_{l}_over_T1_{r}"] = a2 / b2 if (pd.notna(a2) and pd.notna(b2) and b2 != 0) else np.nan
    return out

def compute_cluster_features_for_row(row):
    f1 = row.get("Team1Formation", DEFAULT_FORMATION)
    agg1 = _aggregate_clusters(coords_for_match_team1(f1), [row.get(c, np.nan) for c in TEAM1_PLAYERS], "Team1_")
    
    f2 = row.get("Team2Formation", f1)
    agg2 = _aggregate_clusters(coords_for_match_team2(f2), [row.get(c, np.nan) for c in TEAM2_PLAYERS], "Team2_")
    
    comp = _competition_ratios(pd.Series({**agg1, **agg2}))
    return {**agg1, **agg2, **comp}

def engineer_dataset(df):
    features = df.apply(compute_cluster_features_for_row, axis=1, result_type="expand")
    out = pd.concat([df.reset_index(drop=True), features.reset_index(drop=True)], axis=1)
    if {"Team1_Goals", "Team2_Goals"}.issubset(out.columns):
        out[OUTCOME_COL] = np.where(out["Team1_Goals"] > out["Team2_Goals"], 3, np.where(out["Team1_Goals"] == out["Team2_Goals"], 1, 0))
    elif "Result" in out.columns:
         out[OUTCOME_COL] = out["Result"].astype(str).str.upper().str.strip().map({"W": 3, "D": 1, "L": 0})
    return out

# Feature Lists
TEAM1_GK = ["Team1_Cluster_Goalkeeper_Zone_Avg"]
TEAM2_GK = ["Team2_Cluster_Goalkeeper_Zone_Avg"]
COMP_FEATURES_T1_ATTACK = [
    "Comp_T1_Wing_Right_over_T2_Back_Left", "Comp_T1_Wing_Left_over_T2_Back_Right", "Comp_T1_Mid_Att_over_T2_Mid_Def",
    "Comp_T1_Left_Strip_over_T2_Right_Strip", "Comp_T1_Right_Strip_over_T2_Left_Strip", "Comp_T1_Mid_Strip_over_T2_Mid_Strip",
]
COMP_FEATURES_T2_ATTACK = [
    "Comp_T1_Back_Left_over_T2_Wing_Right", "Comp_T1_Back_Right_over_T2_Wing_Left", "Comp_T1_Mid_Def_over_T2_Mid_Att",
    "Comp_T1_Right_Strip_over_T2_Left_Strip", "Comp_T1_Left_Strip_over_T2_Right_Strip", "Comp_T1_Mid_Strip_over_T2_Mid_Strip",
]
COMPETITION_FEATURES = COMP_FEATURES_T1_ATTACK + COMP_FEATURES_T2_ATTACK
FEATURES_ALL = COMPETITION_FEATURES + TEAM1_GK
FEATURES_GOALS_T1 = COMPETITION_FEATURES + TEAM2_GK
FEATURES_GOALS_T2 = COMPETITION_FEATURES + TEAM1_GK

def _ensure_feature_columns(df):
    expected = set(FEATURES_ALL + FEATURES_GOALS_T1 + FEATURES_GOALS_T2)
    for col in expected:
        if col not in df.columns: df[col] = np.nan
    return df

def _valid_Xy(X, y):
    mask = y.notna() & X.notna().all(axis=1)
    return X[mask], y[mask]

# ================================================================
# MODELS
# ================================================================
def run_models(df_engineered):
    models = {}
    df_engineered = _ensure_feature_columns(df_engineered)
    X_all = df_engineered[FEATURES_ALL]
    X_t1_goal = df_engineered[FEATURES_GOALS_T1]
    X_t2_goal = df_engineered[FEATURES_GOALS_T2]

    # Outcome
    if OUTCOME_COL in df_engineered.columns:
        X_tr, y_tr = _valid_Xy(X_all, df_engineered[OUTCOME_COL])
        if len(y_tr) > 20: # Ensure enough data
            pipe_mn = Pipeline([("scale", StandardScaler()), ("clf", LogisticRegression(multi_class="multinomial", max_iter=200))])
            pipe_mn.fit(X_tr, y_tr)
            models[OUTCOME_COL] = pipe_mn

    # Goals
    if "Team1_Goals" in df_engineered.columns:
        X_tr, y_tr = _valid_Xy(X_t1_goal, df_engineered["Team1_Goals"])
        if len(y_tr) > 20: 
            rf1 = RandomForestRegressor(n_estimators=100, min_samples_leaf=2, random_state=42)
            rf1.fit(X_tr, y_tr)
            models["Team1_Goals"] = rf1

    if "Team2_Goals" in df_engineered.columns:
        X_tr, y_tr = _valid_Xy(X_t2_goal, df_engineered["Team2_Goals"])
        if len(y_tr) > 20:
            rf2 = RandomForestRegressor(n_estimators=100, min_samples_leaf=2, random_state=42)
            rf2.fit(X_tr, y_tr)
            models["Team2_Goals"] = rf2
    
    return models

# ================================================================
# MAIN SIMULATION API
# ================================================================
def simulate_match(team1_name, team2_name, homeaway, data_path, output_dir):
    data_path = Path(data_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load Data
    t1_file = data_path / team1_name / "mixed-seasons" / f"{team1_name}_Games_Input.xlsx"
    t2_file = data_path / team2_name / "mixed-seasons" / f"{team2_name}_Games_Input.xlsx"

    # Fallback to CSV if xlsx missing
    if not t1_file.exists(): 
        t1_file = data_path / team1_name / "mixed-seasons" / f"{team1_name}_Games_Input.csv"
        if not t1_file.exists(): return {"error": f"Data not found for {team1_name}"}
        team1_df = pd.read_csv(t1_file)
    else:
        team1_df = pd.read_excel(t1_file)

    if not t2_file.exists():
        t2_file = data_path / team2_name / "mixed-seasons" / f"{team2_name}_Games_Input.csv"
        if not t2_file.exists(): return {"error": f"Data not found for {team2_name}"}
        team2_df = pd.read_csv(t2_file)
    else:
        team2_df = pd.read_excel(t2_file)

    team1_df = enforce_numeric_columns(team1_df)
    team2_df = enforce_numeric_columns(team2_df)

    # 2. Train Models (using T1 history)
    # Note: Training every time is slow. In prod, we'd cache models. For now, it's fine.
    train_df = engineer_dataset(team1_df)
    models = run_models(train_df)

    if not models:
        return {"error": "Insufficient data to train models."}

    # 3. Generate Test Data & Predict
    test_df = generate_team_test(team1_df, team2_df, team1_name, team2_name, homeaway)
    eng_test = engineer_dataset(test_df)
    eng_test = _ensure_feature_columns(eng_test)

    # Predict
    if OUTCOME_COL in models:
        eng_test[f"Pred_{OUTCOME_COL}"] = models[OUTCOME_COL].predict(eng_test[FEATURES_ALL])
    
    if "Team1_Goals" in models:
        eng_test["Pred_Team1_Goals"] = np.clip(models["Team1_Goals"].predict(eng_test[FEATURES_GOALS_T1]), 0, None)
    
    if "Team2_Goals" in models:
        eng_test["Pred_Team2_Goals"] = np.clip(models["Team2_Goals"].predict(eng_test[FEATURES_GOALS_T2]), 0, None)

    # 4. Aggregation Results
    results = {}
    
    if f"Pred_{OUTCOME_COL}" in eng_test.columns:
        counts = eng_test[f"Pred_{OUTCOME_COL}"].value_counts(normalize=True)
        results["win_prob"] = float(counts.get(3, 0.0) * 100)
        results["draw_prob"] = float(counts.get(1, 0.0) * 100)
        results["lose_prob"] = float(counts.get(0, 0.0) * 100)
    
    if "Pred_Team1_Goals" in eng_test.columns and "Pred_Team2_Goals" in eng_test.columns:
        avg_g1 = eng_test["Pred_Team1_Goals"].mean()
        avg_g2 = eng_test["Pred_Team2_Goals"].mean()
        results["predicted_score"] = f"{round(avg_g1)}-{round(avg_g2)}" # Simple round
        results["avg_goals_team1"] = float(avg_g1)
        results["avg_goals_team2"] = float(avg_g2)

    return results
