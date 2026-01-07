#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec 10 17:30:53 2025

@author: kagancalikoglu
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Combined match preview / report script

- Uses Markov (HMM) form model per team (from markov_model_v2 logic)
- Uses gol_oncesi simulation pipeline twice (home & away perspectives)
- Aggregates probabilities to a unified "typical match" result
- Calls KimKazanır + tahmini_skor image generators with combined result

Inputs:
    Home team name  (Team A)
    Away team name  (Team B)

Assumptions:
    - Data folder and Excel filenames same as your existing scripts.
    - Logos named exactly as team names with .png extension.
"""

from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple
import itertools
import json
import warnings

import numpy as np
import pandas as pd

from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline as SkPipeline

from hmmlearn.hmm import GaussianHMM

from KimKazanır import create_probability_image
from tahmini_skor import create_match_image

warnings.filterwarnings("ignore", category=FutureWarning)
np.random.seed(42)

# ================================================================
# GLOBAL PATHS (same as originals)
# ================================================================
MAIN_FOLDER = Path("//Users/kagancalikoglu/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi/Data/Turkish Super League")
OUTPUT_FOLDER = Path("Outputs")
LOGO_FOLDER = Path("Logos")
try:
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

# ================================================================
# ----------------- GOL_ONCESI CORE (UNMODIFIED LOGIC) ----------
# ================================================================

# Formations and simulation count
FORMATIONS = [
    "4-2-3-1", "4-1-4-1", "4-3-3"
]
SIMS_PER_COMBO = 200

TEAM1_FORMATION_COL = "Team1Formation"
TEAM2_FORMATION_COL = "Team2Formation"

TEAM1_PLAYERS = [
    "Team1Player1", "Team1Player2", "Team1Player3", "Team1Player4",
    "Team1Player5", "Team1Player6", "Team1Player7", "Team1Player8",
    "Team1Player9", "Team1Player10", "Team1Player11"
]

TEAM2_PLAYERS = [
    "Team2Player1", "Team2Player2", "Team2Player3", "Team2Player4",
    "Team2Player5", "Team2Player6", "Team2Player7", "Team2Player8",
    "Team2Player9", "Team2Player10", "Team2Player11"
]

TARGET_COLS_LINEAR = ["Team1_TotalShots", "Team1_BallPosses", "Team2_TotalShots", "Team2_BallPosses"]
GOAL_TARGETS = ["Team1_Goals", "Team2_Goals"]
OUTCOME_COL = "Outcome_3W1D0L"

X_MIN, X_MAX = 1, 5
Y_MIN, Y_MAX = 1, 9

@dataclass(frozen=True)
class Cluster:
    name: str
    x1: int; x2: int
    y1: int; y2: int
    def contains_with_margin(self, x: int, y: int, margin: int = 0) -> bool:
        return (self.x1 - margin <= x <= self.x2 + margin) and (self.y1 - margin <= y <= self.y2 + margin)

def build_clusters() -> List[Cluster]:
    return [
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

CLUSTERS = build_clusters()
CLUSTER_NAMES = [c.name for c in CLUSTERS]

FORMATION_TEMPLATES = {
    # === 4-back systems ===
    "4-1-3-2": [(1,5),(2,2),(2,4),(2,6),(2,8),(3,5),(4,3),(4,5),(4,7),(5,4),(5,6)],
    "4-2-3-1": [(1,5),(2,2),(2,4),(2,6),(2,8),(3,4),(3,6),(4,3),(4,5),(4,7),(5,5)],
    "4-3-3":   [(1,5),(2,2),(2,4),(2,6),(2,8),(3,4),(3,5),(3,6),(4,2),(4,5),(4,8)],
    "4-4-2":   [(1,5),(2,2),(2,4),(2,6),(2,8),(3,3),(3,7),(4,4),(4,6),(5,3),(5,7)],
    "4-1-4-1": [(1,5),(2,2),(2,4),(2,6),(2,8),(3,5),(4,2),(4,4),(4,6),(4,8),(5,5)],
    "4-2-2-2": [(1,5),(2,2),(2,4),(2,6),(2,8),(3,3),(3,7),(4,4),(4,6),(5,3),(5,7)],
    # === 3-back systems ===
    "3-4-3":   [(1,5),(2,3),(2,5),(2,7),(3,2),(3,4),(3,6),(3,8),(4,3),(4,5),(4,7)],
    "3-4-1-2": [(1,5),(2,3),(2,5),(2,7),(3,2),(3,4),(3,6),(3,8),(4,5),(5,3),(5,7)],
    "3-4-2-1": [(1,5),(2,3),(2,5),(2,7),(3,2),(3,4),(3,6),(3,8),(4,3),(4,7),(5,5)],
    "3-5-2":   [(1,5),(2,3),(2,5),(2,7),(3,2),(3,4),(3,5),(3,6),(4,5),(5,3),(5,7)],
    "3-1-4-2": [(1,5),(2,3),(2,5),(2,7),(3,5),(4,2),(4,4),(4,6),(4,8),(5,3),(5,7)],
    # === 5-back systems ===
    "5-3-2":   [(1,5),(2,2),(2,3),(2,5),(2,7),(2,8),(3,4),(3,5),(4,5),(5,3),(5,7)],
    "5-4-1":   [(1,5),(2,2),(2,3),(2,5),(2,7),(2,8),(3,4),(3,5),(4,5),(5,3),(5,7)],
}
DEFAULT_FORMATION = "4-2-3-1"

def parse_formation(s: str) -> str:
    if not isinstance(s, str) or not s.strip():
        return DEFAULT_FORMATION
    s = s.strip().replace(" ", "")
    return s if s in FORMATION_TEMPLATES else DEFAULT_FORMATION

def coords_for_match_team1(f: str): return FORMATION_TEMPLATES[parse_formation(f)]
def coords_for_match_team2(f: str):
    coords_t1 = FORMATION_TEMPLATES[parse_formation(f)]
    mirror = lambda x: (X_MIN + X_MAX) - x
    return [(mirror(x), y) for x, y in coords_t1]

NUMERIC_COLS = [
    *(f"Team1Player{i}" for i in range(1, 12)),
    *(f"Team2Player{i}" for i in range(1, 12)),
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
    s = pd.to_numeric(series.iloc[1:11], errors="coerce").dropna()
    if len(s) == 0:
        return 5.0, 1.0
    mean = float(s.mean())
    std = float(s.std(ddof=1)) if s.std(ddof=1) > 0 else 0.5
    return mean, std

def generate_team_test(team1_df, team2_df, team1_name, team2_name, team1_homeaway) -> pd.DataFrame:
    team1_stats = {col: safe_mean_std(team1_df[col]) for col in TEAM1_PLAYERS if col in team1_df.columns}
    team2_stats = {f"Team2Player{i}": safe_mean_std(team2_df[f"Team1Player{i}"])
                   for i in range(1, 12) if f"Team1Player{i}" in team2_df.columns}

    rows = []
    for f1, f2 in itertools.product(FORMATIONS, FORMATIONS):
        for _ in range(SIMS_PER_COMBO):
            row = {
                "Team1": team1_name,
                "Team2": team2_name,
                "Team1H_A": team1_homeaway,
                "Team1Formation": f1,
                "Team2Formation": f2,
            }

            for i in range(1, 12):
                m1, s1 = team1_stats.get(f"Team1Player{i}", (5.0, 1.0))
                val1 = np.clip(np.random.normal(m1, s1), 1, 10)
                row[f"Team1Player{i}"] = round(val1, 2)

            for i in range(1, 12):
                m2, s2 = team2_stats.get(f"Team2Player{i}", (5.0, 1.0))
                val2 = np.clip(np.random.normal(m2, s2), 1, 10)
                row[f"Team2Player{i}"] = round(val2, 2)

            rows.append(row)

    df = pd.DataFrame(rows)
    return df

def player_cluster_memberships(x: int, y: int, clusters: List[Cluster], margin: int = 0) -> List[str]:
    return [c.name for c in clusters if c.contains_with_margin(x, y, margin=margin)]

def _aggregate_clusters(coords: List[Tuple[int,int]], ratings: List[float], prefix: str) -> Dict[str, float]:
    bucket: Dict[str, List[float]] = {name: [] for name in CLUSTER_NAMES}
    for (x, y), rating in zip(coords, ratings):
        if pd.isna(rating):
            continue
        for cname in player_cluster_memberships(x, y, CLUSTERS, margin=0):
            bucket[cname].append(float(rating))
    agg: Dict[str, float] = {}
    for cname, vals in bucket.items():
        agg[f"{prefix}Cluster_{cname}_Avg"] = float(np.mean(vals)) if len(vals) else np.nan
        agg[f"{prefix}Cluster_{cname}_Cnt"] = int(len(vals))
    return agg

def _safe_div(a: float, b: float) -> float:
    if pd.isna(a) or pd.isna(b) or b == 0:
        return np.nan
    return a / b

def _competition_ratios(row: pd.Series) -> Dict[str, float]:
    pairs = [
        ("Wing_Right", "Back_Left"),
        ("Wing_Left", "Back_Right"),
        ("Mid_Att", "Mid_Def"),
        ("Left_Strip", "Right_Strip"),
        ("Right_Strip", "Left_Strip"),
        ("Mid_Strip", "Mid_Strip"),
        ("Wing_Right", "Back_Right"),
        ("Wing_Left", "Back_Left"),
        ("Mid_Att", "Goalkeeper_Zone"),
        ("Back_Left", "Wing_Right"),
        ("Back_Right", "Wing_Left"),
        ("Mid_Def", "Mid_Att"),
        ("Right_Strip", "Left_Strip"),
        ("Left_Strip", "Right_Strip"),
        ("Mid_Strip", "Mid_Strip"),
        ("Back_Left", "Wing_Left"),
        ("Back_Right", "Wing_Right"),
        ("Goalkeeper_Zone", "Mid_Att"),
    ]

    out = {}
    getv = row.get
    for l, r in pairs:
        a = getv(f"Team1_Cluster_{l}_Avg")
        b = getv(f"Team2_Cluster_{r}_Avg")
        out[f"Comp_T1_{l}_over_T2_{r}"] = _safe_div(a, b)

        a2 = getv(f"Team2_Cluster_{l}_Avg")
        b2 = getv(f"Team1_Cluster_{r}_Avg")
        out[f"Comp_T2_{l}_over_T1_{r}"] = _safe_div(a2, b2)

    return out

def compute_cluster_features_for_row(row: pd.Series) -> Dict[str, float]:
    f1 = row.get(TEAM1_FORMATION_COL, DEFAULT_FORMATION)
    coords1 = coords_for_match_team1(f1)
    ratings1 = [row.get(col, np.nan) for col in TEAM1_PLAYERS]
    agg1 = _aggregate_clusters(coords1, ratings1, prefix="Team1_")

    f2 = row.get(TEAM2_FORMATION_COL, f1)
    coords2 = coords_for_match_team2(f2)
    ratings2 = [row.get(col, np.nan) for col in TEAM2_PLAYERS]
    agg2 = _aggregate_clusters(coords2, ratings2, prefix="Team2_")

    comp = _competition_ratios(pd.Series({**agg1, **agg2}))
    return {**agg1, **agg2, **comp}

def engineer_dataset(df: pd.DataFrame) -> pd.DataFrame:
    features = df.apply(compute_cluster_features_for_row, axis=1, result_type="expand")
    out = pd.concat([df.reset_index(drop=True), features.reset_index(drop=True)], axis=1)
    if {"Team1_Goals", "Team2_Goals"}.issubset(out.columns):
        g1, g2 = out["Team1_Goals"], out["Team2_Goals"]
        out[OUTCOME_COL] = np.where(g1 > g2, 3, np.where(g1 == g2, 1, 0))
    elif "Result" in out.columns:
        res = out["Result"].astype(str).str.upper().str.strip()
        out[OUTCOME_COL] = res.map({"W": 3, "D": 1, "L": 0})
    return out

def _valid_Xy(X: pd.DataFrame, y: pd.Series):
    mask = y.notna() & X.notna().all(axis=1)
    return X[mask], y[mask]

def _report_fit(label: str, model, X, y):
    if hasattr(model, "score"):
        try:
            score = model.score(X, y)
            print(f"{label} | Score: {score:.3f}")
        except Exception:
            pass

TEAM1_CLUSTER_AVG = [f"Team1_Cluster_{c}_Avg" for c in [
    "Goalkeeper_Zone", "Back_Left", "Back_Right", "Mid_Def", "Mid_Att",
    "Wing_Left", "Wing_Right", "Left_Strip", "Mid_Strip", "Right_Strip"
]]

TEAM2_CLUSTER_AVG = [f"Team2_Cluster_{c}_Avg" for c in [
    "Goalkeeper_Zone", "Back_Left", "Back_Right", "Mid_Def", "Mid_Att",
    "Wing_Left", "Wing_Right", "Left_Strip", "Mid_Strip", "Right_Strip"
]]

TEAM1_GK  = ["Team1_Cluster_Goalkeeper_Zone_Avg"]
TEAM2_GK  = ["Team2_Cluster_Goalkeeper_Zone_Avg"]

COMP_FEATURES_T1_ATTACK = [
    "Comp_T1_Wing_Right_over_T2_Back_Left",
    "Comp_T1_Wing_Left_over_T2_Back_Right",
    "Comp_T1_Mid_Att_over_T2_Mid_Def",
    "Comp_T1_Left_Strip_over_T2_Right_Strip",
    "Comp_T1_Right_Strip_over_T2_Left_Strip",
    "Comp_T1_Mid_Strip_over_T2_Mid_Strip",
]

COMP_FEATURES_T2_ATTACK = [
    "Comp_T1_Back_Left_over_T2_Wing_Right",
    "Comp_T1_Back_Right_over_T2_Wing_Left",
    "Comp_T1_Mid_Def_over_T2_Mid_Att",
    "Comp_T1_Right_Strip_over_T2_Left_Strip",
    "Comp_T1_Left_Strip_over_T2_Right_Strip",
    "Comp_T1_Mid_Strip_over_T2_Mid_Strip",
]

COMPETITION_FEATURES = COMP_FEATURES_T1_ATTACK + COMP_FEATURES_T2_ATTACK

FEATURES_ALL = COMPETITION_FEATURES + TEAM1_GK
FEATURES_GOALS_T1 = COMPETITION_FEATURES + TEAM2_GK
FEATURES_GOALS_T2 = COMPETITION_FEATURES + TEAM1_GK

def _ensure_feature_columns(df: pd.DataFrame) -> pd.DataFrame:
    expected = set(FEATURES_ALL + FEATURES_GOALS_T1 + FEATURES_GOALS_T2)
    for col in expected:
        if col not in df.columns:
            df[col] = np.nan
    return df

def run_models(df_engineered: pd.DataFrame):
    models = {}

    df_engineered = _ensure_feature_columns(df_engineered)

    X_all = df_engineered[FEATURES_ALL]
    X_t1_goal = df_engineered[FEATURES_GOALS_T1]
    X_t2_goal = df_engineered[FEATURES_GOALS_T2]

    if OUTCOME_COL in df_engineered.columns:
        y_outcome = df_engineered[OUTCOME_COL]
        X_tr, y_tr = _valid_Xy(X_all, y_outcome)
        pipe_mn = Pipeline([
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(multi_class="multinomial", max_iter=200, solver="lbfgs"))
        ])
        pipe_mn.fit(X_tr, y_tr)
        _report_fit("Multinomial Outcome (0/1/3)", pipe_mn, X_tr, y_tr)
        models[OUTCOME_COL] = pipe_mn

    for t in TARGET_COLS_LINEAR:
        if t in df_engineered.columns:
            y = df_engineered[t]
            X_tr, y_tr = _valid_Xy(X_all, y)
            rf = RandomForestRegressor(
                n_estimators=400,
                max_depth=None,
                min_samples_leaf=2,
                random_state=42
            )
            rf.fit(X_tr, y_tr)
            _report_fit(f"RF: {t}", rf, X_tr, y_tr)
            models[t] = rf

    if "Team1_Goals" in df_engineered.columns:
        y_t1 = df_engineered["Team1_Goals"]
        X_tr, y_tr = _valid_Xy(X_t1_goal, y_t1)
        rf1 = RandomForestRegressor(n_estimators=400, min_samples_leaf=2, random_state=42)
        rf1.fit(X_tr, y_tr)
        _report_fit("RF: Team1_Goals", rf1, X_tr, y_tr)
        models["Team1_Goals"] = rf1

    if "Team2_Goals" in df_engineered.columns:
        y_t2 = df_engineered["Team2_Goals"]
        X_tr, y_tr = _valid_Xy(X_t2_goal, y_t2)
        rf2 = RandomForestRegressor(n_estimators=400, min_samples_leaf=2, random_state=42)
        rf2.fit(X_tr, y_tr)
        _report_fit("RF: Team2_Goals", rf2, X_tr, y_tr)
        models["Team2_Goals"] = rf2

    coef_rows = []

    def add_coefs(label: str, model, feature_names: list):
        if isinstance(model, Pipeline):
            if 'ols' in model.named_steps:
                model_core = model.named_steps['ols']
            elif 'clf' in model.named_steps:
                model_core = model.named_steps['clf']
            else:
                return
        else:
            model_core = model

        if hasattr(model_core, "coef_"):
            coefs = model_core.coef_
            if hasattr(coefs, "ndim") and coefs.ndim == 2:
                for class_index, row in enumerate(coefs):
                    for f, val in zip(feature_names, row):
                        coef_rows.append({
                            "Model": f"{label}_Class{class_index}",
                            "Feature": f,
                            "Coefficient": float(val),
                        })
            else:
                for f, val in zip(feature_names, coefs):
                    coef_rows.append({
                        "Model": label,
                        "Feature": f,
                        "Coefficient": float(val),
                    })
            return

        if hasattr(model_core, "feature_importances_"):
            importances = model_core.feature_importances_
            for f, val in zip(feature_names, importances):
                coef_rows.append({
                    "Model": label,
                    "Feature": f,
                    "Importance": float(val),
                })
            return

    for name, mdl in models.items():
        if name in GOAL_TARGETS:
            feats = FEATURES_GOALS_T1 if "Team1" in name else FEATURES_GOALS_T2
        else:
            feats = FEATURES_ALL
        add_coefs(name, mdl, feats)

    coef_df = pd.DataFrame(coef_rows)
    return models, coef_df

def run_simulation_perspective(team1_name: str, team2_name: str) -> dict:
    """
    In-memory version of run_matchup():
      - trains on team1 historical data
      - simulates vs team2
      - returns outcome probabilities, expected score and top scorelines
    """
    team1_file = MAIN_FOLDER / team1_name / "mixed-seasons" / f"{team1_name}_Games_Input.xlsx"
    team2_file = MAIN_FOLDER / team2_name / "mixed-seasons" / f"{team2_name}_Games_Input.xlsx"

    if not team1_file.exists():
        raise FileNotFoundError(f"Missing file for {team1_name}: {team1_file}")
    if not team2_file.exists():
        raise FileNotFoundError(f"Missing file for {team2_name}: {team2_file}")

    team1_df = pd.read_excel(team1_file, sheet_name="Sheet1")
    team2_df = pd.read_excel(team2_file, sheet_name="Sheet1")

    team1_df = enforce_numeric_columns(team1_df)
    team2_df = enforce_numeric_columns(team2_df)

    test_df = generate_team_test(team1_df, team2_df, team1_name, team2_name, "Home")

    # Average simulated ratings
    avg_t1_rating = test_df[[c for c in test_df.columns if 'Team1Player' in c]].mean().mean()
    avg_t2_rating = test_df[[c for c in test_df.columns if 'Team2Player' in c]].mean().mean()

    eng_train = engineer_dataset(team1_df)
    eng_train = _ensure_feature_columns(eng_train)
    models, _ = run_models(eng_train)

    eng_test = engineer_dataset(test_df)
    eng_test = _ensure_feature_columns(eng_test)

    X_all_test = eng_test[FEATURES_ALL]
    X_t1_goal_test = eng_test[FEATURES_GOALS_T1]
    X_t2_goal_test = eng_test[FEATURES_GOALS_T2]

    if OUTCOME_COL in models:
        y_proba = models[OUTCOME_COL].predict_proba(X_all_test)
        class_labels = models[OUTCOME_COL].named_steps["clf"].classes_
        for c_idx, c_val in enumerate(class_labels):
            eng_test[f"PredP_{OUTCOME_COL}_{c_val}"] = y_proba[:, c_idx]
        eng_test[f"Pred_{OUTCOME_COL}"] = models[OUTCOME_COL].predict(X_all_test)

    for t in TARGET_COLS_LINEAR:
        if t in models:
            eng_test[f"Pred_{t}"] = models[t].predict(X_all_test)

    if "Team1_Goals" in models:
        eng_test["Pred_Team1_Goals"] = np.clip(models["Team1_Goals"].predict(X_t1_goal_test), a_min=0, a_max=None)
    if "Team2_Goals" in models:
        eng_test["Pred_Team2_Goals"] = np.clip(models["Team2_Goals"].predict(X_t2_goal_test), a_min=0, a_max=None)

    # Outcome probabilities
    total_matches = len(eng_test)
    if total_matches == 0:
        raise RuntimeError("No simulated matches produced.")

    win_prob = (eng_test["Pred_Outcome_3W1D0L"] == 3).sum() / total_matches
    draw_prob = (eng_test["Pred_Outcome_3W1D0L"] == 1).sum() / total_matches
    lose_prob = (eng_test["Pred_Outcome_3W1D0L"] == 0).sum() / total_matches

    # Expected score distribution
    if {"Pred_Team1_Goals", "Pred_Team2_Goals", "Pred_Outcome_3W1D0L"}.issubset(eng_test.columns):
        df_scores = eng_test.copy()

        def predict_final_score(row):
            g1, g2, outcome = row["Pred_Team1_Goals"], row["Pred_Team2_Goals"], row["Pred_Outcome_3W1D0L"]
            if pd.isna(g1) or pd.isna(g2) or pd.isna(outcome):
                return np.nan
            if outcome == 3:
                return f"{int(np.ceil(g1))}-{int(np.floor(g2))}"
            elif outcome == 0:
                return f"{int(np.floor(g1))}-{int(np.ceil(g2))}"
            else:
                if abs(g1 - g2) < 1:
                    return f"{int(np.floor(g1))}-{int(np.floor(g2))}"
                hi, lo = int(np.floor(max(g1, g2))), int(np.ceil(min(g1, g2)))
                return f"{hi}-{lo}"

        df_scores["Predicted_Final_Score"] = df_scores.apply(predict_final_score, axis=1)
        score_counts = df_scores["Predicted_Final_Score"].value_counts().reset_index()
        score_counts.columns = ["Score", "Count"]
    else:
        score_counts = pd.DataFrame(columns=["Score", "Count"])

    top_score = score_counts.iloc[0]["Score"] if not score_counts.empty else "0-0"
    top5 = score_counts.head(5).copy()

    # Compute training model performance numbers similar to your printouts
    model_perf = {}
    X_all_train = eng_train[FEATURES_ALL]
    X_all_train, _ = _valid_Xy(X_all_train, eng_train[OUTCOME_COL])  # mask just for X shape

    if OUTCOME_COL in models:
        y = eng_train[OUTCOME_COL]
        X_tr, y_tr = _valid_Xy(eng_train[FEATURES_ALL], y)
        model_perf["Multinomial_Outcome"] = models[OUTCOME_COL].score(X_tr, y_tr)

    for t in TARGET_COLS_LINEAR:
        if t in models and t in eng_train.columns:
            y = eng_train[t]
            X_tr, y_tr = _valid_Xy(eng_train[FEATURES_ALL], y)
            model_perf[t] = models[t].score(X_tr, y_tr)

    if "Team1_Goals" in models and "Team1_Goals" in eng_train.columns:
        y = eng_train["Team1_Goals"]
        X_tr, y_tr = _valid_Xy(eng_train[FEATURES_GOALS_T1], y)
        model_perf["Team1_Goals"] = models["Team1_Goals"].score(X_tr, y_tr)

    if "Team2_Goals" in models and "Team2_Goals" in eng_train.columns:
        y = eng_train["Team2_Goals"]
        X_tr, y_tr = _valid_Xy(eng_train[FEATURES_GOALS_T2], y)
        model_perf["Team2_Goals"] = models["Team2_Goals"].score(X_tr, y_tr)

    return {
        "team1": team1_name,
        "team2": team2_name,
        "simulated_matches": total_matches,
        "avg_ratings": {
            "team1": float(avg_t1_rating),
            "team2": float(avg_t2_rating),
        },
        "probs": {
            "team1_win": float(win_prob),
            "draw": float(draw_prob),
            "team1_loss": float(lose_prob),
        },
        "top_score": top_score,
        "top5_scores": top5,    # DataFrame with Score/Count
        "model_perf": model_perf,
    }


# ================================================================
# ------------------- MARKOV (HMM) CORE --------------------------
# ================================================================
CATEGORICAL_COLS = ["Team1H_A", "Team1Formation", "Team2Formation"]
TEAM1_NUMERIC_COLS = [
    "Team1_Goals","Team1_BigChances","Team1_TotalShots","Team1_Corners",
    "Team1_Passes","Team1_Tackels","Team1_FreeKicks","Team1_BallPosses"
]
TEAM2_NUMERIC_COLS = [
    "Team2_Goals","Team2_BigChances","Team2_TotalShots","Team2_Corners",
    "Team2_Passes","Team2_Tackels","Team2_FreeKicks","Team2_BallPosses"
]
TEAM1_PLAYER_RATING_COLS = [f"Team1Player{i}" for i in range(1,12)]
TEAM2_PLAYER_RATING_COLS = [f"Team2Player{i}" for i in range(1,12)]
TARGET_COL_MARKOV = "Win(3)_Draw(1)_Lose(0)"

def build_features_markov(df: pd.DataFrame) -> tuple:
    data = df.copy()

    for prefix, cols in [("Team1", TEAM1_PLAYER_RATING_COLS), ("Team2", TEAM2_PLAYER_RATING_COLS)]:
        data[f"{prefix}_PlayerRating_Mean"] = data[cols].mean(axis=1)
        data[f"{prefix}_PlayerRating_Median"] = data[cols].median(axis=1)
        data[f"{prefix}_PlayerRating_Std"] = data[cols].std(axis=1, ddof=0)

    for c1, c2 in zip(TEAM1_NUMERIC_COLS, TEAM2_NUMERIC_COLS):
        base = c1.replace("Team1_", "")
        data[f"Diff_{base}"] = data[c1] - data[c2]

    data["Diff_PlayerRating_Mean"] = data["Team1_PlayerRating_Mean"] - data["Team2_PlayerRating_Mean"]
    data["Diff_PlayerRating_Median"] = data["Team1_PlayerRating_Median"] - data["Team2_PlayerRating_Median"]
    data["Diff_PlayerRating_Std"] = data["Team1_PlayerRating_Std"] - data["Team2_PlayerRating_Std"]

    numeric_features = TEAM1_NUMERIC_COLS + TEAM2_NUMERIC_COLS + \
        [f"Diff_{c.replace('Team1_', '')}" for c in TEAM1_NUMERIC_COLS] + \
        ["Team1_PlayerRating_Mean","Team1_PlayerRating_Median","Team1_PlayerRating_Std",
         "Team2_PlayerRating_Mean","Team2_PlayerRating_Median","Team2_PlayerRating_Std",
         "Diff_PlayerRating_Mean","Diff_PlayerRating_Median","Diff_PlayerRating_Std"]
    categorical_features = CATEGORICAL_COLS

    return data, numeric_features, categorical_features

def make_preprocessor_markov(num_feats, cat_feats):
    numeric_transformer = SkPipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler())
    ])
    categorical_transformer = SkPipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot",  pd.get_dummies)
    ])
    # original: use OneHotEncoder
    from sklearn.preprocessing import OneHotEncoder
    categorical_transformer = SkPipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(drop="if_binary", handle_unknown="ignore"))
    ])
    return ColumnTransformer([
        ("num", numeric_transformer, num_feats),
        ("cat", categorical_transformer, cat_feats)
    ])

def fit_best_hmm(X, k_min=2, k_max=5):
    best_bic = np.inf
    best_model, best_k = None, None
    results = []
    N, D = X.shape

    for k in range(k_min, k_max + 1):
        model = GaussianHMM(n_components=k, covariance_type="diag", n_iter=500,
                            random_state=np.random.randint(0, 10000))
        model.fit(X)
        logL = model.score(X)
        p = k * (D * 2 + (k - 1))
        bic = p * np.log(N) - 2 * logL
        results.append((k, bic))
        if bic < best_bic:
            best_bic = bic
            best_model, best_k = model, k
    return best_model, best_k, results

def estimate_outcomes_by_state(states, y):
    outcome_map = {}
    for s in np.unique(states):
        mask = states == s
        subset = y[mask]
        total = len(subset)
        if total == 0:
            continue
        outcome_map[int(s)] = {
            "P_win": np.mean(subset == 3),
            "P_draw": np.mean(subset == 1),
            "P_loss": np.mean(subset == 0),
            "count": total
        }
    return outcome_map

def predict_next_match_markov(model, X, outcome_map):
    _, post = model.score_samples(X)
    last_gamma = post[-1]
    next_gamma = model.transmat_.T @ last_gamma

    p_win = p_draw = p_loss = 0.0
    for s, p in enumerate(next_gamma):
        m = outcome_map.get(s, {})
        p_win += p * m.get("P_win", 0)
        p_draw += p * m.get("P_draw", 0)
        p_loss += p * m.get("P_loss", 0)
    total = p_win + p_draw + p_loss
    if total > 0:
        p_win, p_draw, p_loss = p_win/total, p_draw/total, p_loss/total
    return {"P_win": p_win, "P_draw": p_draw, "P_loss": p_loss}

def run_markov_for_team(team_name: str) -> dict:
    """
    Run Markov (HMM) form analysis for a single team
    using the same logic as markov_model_v2, but wrapped as a function.
    """
    team1_file = MAIN_FOLDER / team_name / "mixed-seasons" / f"{team_name}_Games_Input.xlsx"
    if not team1_file.exists():
        raise FileNotFoundError(f"Missing file for {team_name}: {team1_file}")

    df = pd.read_excel(team1_file)
    if "MatchOrder" not in df.columns:
        df["MatchOrder"] = range(len(df), 0, -1)
    df = df.sort_values(by="MatchOrder").reset_index(drop=True)

    feats_df, num_feats, cat_feats = build_features_markov(df)
    y = feats_df[TARGET_COL_MARKOV].values

    preproc = make_preprocessor_markov(num_feats, cat_feats)
    X = preproc.fit_transform(feats_df)

    model, best_k, scores = fit_best_hmm(X)
    states = model.predict(X)
    outcomes = estimate_outcomes_by_state(states, y)
    next_probs = predict_next_match_markov(model, X, outcomes)

    # Build human-readable profiles
    state_profiles = []
    for s, info in sorted(outcomes.items(), key=lambda kv: kv[0]):
        state_profiles.append({
            "state": s,
            "count": int(info["count"]),
            "P_win": float(info["P_win"]),
            "P_draw": float(info["P_draw"]),
            "P_loss": float(info["P_loss"]),
        })

    return {
        "team": team_name,
        "matches_used": int(len(df)),
        "hidden_states": int(best_k),
        "state_profiles": state_profiles,
        "next_match_probs": {
            "P_win": float(next_probs["P_win"]),
            "P_draw": float(next_probs["P_draw"]),
            "P_loss": float(next_probs["P_loss"]),
        },
        "bic_scores": scores,
    }


# ================================================================
# ------------- COMBINED REPORT + IMAGE GENERATION --------------
# ================================================================
def combine_perspectives(home_sim: dict, away_sim: dict) -> dict:
    """
    home_sim: Team1 = Home, Team2 = Away
    away_sim: Team1 = Away (as Home), Team2 = Home (as Away)
    Convert away_sim to home team's perspective, then average.
    """
    p1 = home_sim["probs"]
    p2 = away_sim["probs"]

    # From home_sim perspective
    home_win_1 = p1["team1_win"]
    draw_1 = p1["draw"]
    home_loss_1 = p1["team1_loss"]

    # Transform away perspective to original home:
    home_win_2 = p2["team1_loss"]
    draw_2 = p2["draw"]
    home_loss_2 = p2["team1_win"]

    home_win = (home_win_1 + home_win_2) / 2.0
    draw = (draw_1 + draw_2) / 2.0
    home_loss = (home_loss_1 + home_loss_2) / 2.0

    # central expected goals:
    def parse_score(s: str):
        try:
            a, b = s.split("-")
            return int(a), int(b)
        except Exception:
            return 0, 0

    # From home_sim: score "h-a"
    h_g_home, h_g_away = parse_score(home_sim["top_score"])

    # From away_sim: score "A_home - A_away" in that sim
    a_home_g, a_away_g = parse_score(away_sim["top_score"])
    # In original home perspective: home goals = a_away_g, away goals = a_home_g
    rev_home_goals = a_away_g
    rev_away_goals = a_home_g

    exp_home_goals = (h_g_home + rev_home_goals) / 2.0
    exp_away_goals = (h_g_away + rev_away_goals) / 2.0

    # Integer "headline" central score
    headline_home = int(round(exp_home_goals))
    headline_away = int(round(exp_away_goals))

    return {
        "home_win": float(home_win),
        "draw": float(draw),
        "home_loss": float(home_loss),
        "exp_home_goals": float(exp_home_goals),
        "exp_away_goals": float(exp_away_goals),
        "headline_score": f"{headline_home}-{headline_away}",
    }

def percent(x: float) -> float:
    return round(100.0 * x, 2)

def percent_int(x: float) -> int:
    return int(round(100.0 * x))

def print_markov_section(markov_home: dict, markov_away: dict, home_team: str, away_team: str):
    print("🔍 Match Preview Report\n")
    print(f"Fixture: {home_team} vs {away_team}")
    print("Context: Two-sided simulation + team-specific Markov models\n")
    print("1. Markov form analysis (per team)")

    # Home team
    mh = markov_home
    print(f"1.1 {home_team} – Markov form model\n")
    print(f"Matches used: {mh['matches_used']}")
    print(f"Hidden states selected: {mh['hidden_states']}\n")
    print("State profiles:\n")
    for prof in mh["state_profiles"]:
        count = prof["count"]
        pw = percent(prof["P_win"])
        pd = percent(prof["P_draw"])
        pl = percent(prof["P_loss"])
        print(f"State {prof['state']} ({count} matches)")
        print(f"Win: {pw:.2f}%")
        print(f"Draw: {pd:.2f}%")
        print(f"Loss: {pl:.2f}%\n")

    pw = percent(mh["next_match_probs"]["P_win"])
    pd = percent(mh["next_match_probs"]["P_draw"])
    pl = percent(mh["next_match_probs"]["P_loss"])
    print(f"Predicted next-match probabilities (Markov, {home_team} vs generic opponent):\n")
    print(f"Win: {pw:.2f}%")
    print(f"Draw: {pd:.2f}%")
    print(f"Loss: {pl:.2f}%\n")

    # Away team
    ma = markov_away
    print(f"1.2 {away_team} – Markov form model\n")
    print(f"Matches used: {ma['matches_used']}")
    print(f"Hidden states selected: {ma['hidden_states']}\n")
    print("State profiles:\n")
    for prof in ma["state_profiles"]:
        count = prof["count"]
        pw = percent(prof["P_win"])
        pd = percent(prof["P_draw"])
        pl = percent(prof["P_loss"])
        print(f"State {prof['state']} ({count} matches)")
        print(f"Win: {pw:.2f}%")
        print(f"Draw: {pd:.2f}%")
        print(f"Loss: {pl:.2f}%\n")

    pw = percent(ma["next_match_probs"]["P_win"])
    pd = percent(ma["next_match_probs"]["P_draw"])
    pl = percent(ma["next_match_probs"]["P_loss"])
    print(f"Predicted next-match probabilities (Markov, {away_team} vs generic opponent):\n")
    print(f"Win: {pw:.2f}%")
    print(f"Draw: {pd:.2f}%")
    print(f"Loss: {pl:.2f}%\n")

def print_simulation_section(home_sim: dict, away_sim: dict, home_team: str, away_team: str):
    print("2. Simulation-based matchup analysis\n")
    print("Here we use the simulations from each perspective.\n")

    # 2.1 Home perspective (Team1 = home_team)
    print(f"2.1 {home_team} (Home) vs {away_team} (Away)\n")
    print(f"Simulated matches: {home_sim['simulated_matches']}\n")
    print("Average team ratings:\n")
    print(f"{home_team}: {home_sim['avg_ratings']['team1']:.2f}")
    print(f"{away_team}: {home_sim['avg_ratings']['team2']:.2f}\n")

    mp = home_sim["model_perf"]
    print(f"Model performance (from {home_team}’s perspective):\n")
    if "Multinomial_Outcome" in mp:
        print(f"Multinomial outcome (0/1/3 points) – score: {mp['Multinomial_Outcome']:.3f}")
    for k in TARGET_COLS_LINEAR:
        if k in mp:
            print(f"Random Forest {k}: {mp[k]:.3f}")
    if "Team1_Goals" in mp:
        print(f"Random Forest Team1_Goals: {mp['Team1_Goals']:.3f}")
    if "Team2_Goals" in mp:
        print(f"Random Forest Team2_Goals: {mp['Team2_Goals']:.3f}")
    print()

    ph = home_sim["probs"]
    print(f"Predicted outcome probabilities ({home_team} home):\n")
    print(f"{home_team} win: {percent(ph['team1_win']):.2f}%")
    print(f"Draw: {percent(ph['draw']):.2f}%")
    print(f"{away_team} win: {percent(ph['team1_loss']):.2f}%\n")

    print(f"Expected score ({home_team} home):")
    print(f"{home_team} {home_sim['top_score'].split('-')[0]} – {home_sim['top_score'].split('-')[1]} {away_team}\n")

    print(f"Top 5 scorelines from {home_team}’s perspective ({home_team} home)")
    for _, row in home_sim["top5_scores"].iterrows():
        print(f"{row['Score']} – ({int(row['Count'])})")
    print()

    # 2.2 Away team as home in its own simulation
    print(f"2.2 {away_team} (Home) vs {home_team} (Away)\n")
    print(f"Simulated matches: {away_sim['simulated_matches']}\n")
    print("Average team ratings:\n")
    print(f"{away_team}: {away_sim['avg_ratings']['team1']:.2f}")
    print(f"{home_team}: {away_sim['avg_ratings']['team2']:.2f}\n")

    mp2 = away_sim["model_perf"]
    print(f"Model performance (from {away_team}’s perspective):\n")
    if "Multinomial_Outcome" in mp2:
        print(f"Multinomial outcome (0/1/3 points) – score: {mp2['Multinomial_Outcome']:.3f}")
    for k in TARGET_COLS_LINEAR:
        if k in mp2:
            print(f"Random Forest {k}: {mp2[k]:.3f}")
    if "Team1_Goals" in mp2:
        print(f"Random Forest Team1_Goals: {mp2['Team1_Goals']:.3f}")
    if "Team2_Goals" in mp2:
        print(f"Random Forest Team2_Goals: {mp2['Team2_Goals']:.3f}")
    print()

    pa = away_sim["probs"]
    print(f"Predicted outcome probabilities ({away_team} home – Team1 is {away_team}):\n")
    print(f"{away_team} win: {percent(pa['team1_win']):.2f}%")
    print(f"Draw: {percent(pa['draw']):.2f}%")
    print(f"{away_team} loss: {percent(pa['team1_loss']):.2f}%\n")

    print(f"From {home_team}’s perspective in this match:")
    print(f"{home_team} win: {percent(pa['team1_loss']):.2f}%")
    print(f"Draw: {percent(pa['draw']):.2f}%")
    print(f"{home_team} loss: {percent(pa['team1_win']):.2f}%\n")

    print(f"Expected score ({away_team} home):")
    print(f"{away_team} {away_sim['top_score'].split('-')[0]} – {away_sim['top_score'].split('-')[1]} {home_team}\n")

    print(f"Top 5 scorelines from {away_team}’s perspective ({away_team} first team)")
    for _, row in away_sim["top5_scores"].iterrows():
        print(f"{row['Score']} – ({int(row['Count'])})")
    print()

# ---------- NEW: Conclusion text based on 50% rules -------------
def build_conclusion_text(
    home_team: str,
    away_team: str,
    home_prob: int,
    draw_prob: int,
    away_prob: int,
    exp_h: float,
    exp_a: float,
    headline_score: str,
) -> str:
    """
    Kurallar:
    - Eğer bir takımın ihtimali %50'yi geçiyorsa: ANA TAHMİN o takım maçı kazanır.
    - Eğer beraberlik %50'yi geçiyorsa: ANA TAHMİN maç berabere biter.
    - Eğer hiçbir değer %50'nin üstünde değilse:
        yüzdesi yüksek olan takım maçı kaybetmez (en az 1 puan alır).
    """

    # 1) Takım kazanır senaryosu
    if home_prob > 50 and home_prob >= away_prob and home_prob >= draw_prob:
        ana_satir = f"{home_team} maçı kazanmaya daha yakın."
    elif away_prob > 50 and away_prob >= home_prob and away_prob >= draw_prob:
        ana_satir = f"{away_team} maçı kazanmaya daha yakın."
    # 2) Beraberlik %50'nin üstünde ise
    elif draw_prob > 50:
        ana_satir = "Maçın berabere bitmesi en olası senaryo."
    # 3) Hiç kimse 50+'da değilse: yüzdesi yüksek olan takım kaybetmez
    else:
        if home_prob > away_prob:
            guclu_takim = home_team
        elif away_prob > home_prob:
            guclu_takim = away_team
        else:
            guclu_takim = None

        if guclu_takim is None:
            ana_satir = "Maç berabere biter."
        else:
            ana_satir = f"{guclu_takim} en az 1 puan alır."

    conclusion_text = (
        "ANA TAHMİN:\n\n"
        f"{ana_satir}\n"
    )
    return conclusion_text

def generate_images(home_team: str, away_team: str, combined: dict):
    home_prob = percent_int(combined["home_win"])
    draw_prob = percent_int(combined["draw"])
    away_prob = percent_int(combined["home_loss"])

    headline_score = combined["headline_score"]
    exp_h = combined["exp_home_goals"]
    exp_a = combined["exp_away_goals"]

    # ANA TAHMİN metnini yeni kurallara göre üret
    conclusion_text = build_conclusion_text(
        home_team=home_team,
        away_team=away_team,
        home_prob=home_prob,
        draw_prob=draw_prob,
        away_prob=away_prob,
        exp_h=exp_h,
        exp_a=exp_a,
        headline_score=headline_score,
    )

    home_logo = LOGO_FOLDER / f"{home_team}.png"
    away_logo = LOGO_FOLDER / f"{away_team}.png"

    # KimKazanır style probability image
    prob_out = OUTPUT_FOLDER / f"KimKazanır_{home_team}_{away_team}.png"
    create_probability_image(
        home_team=home_team,
        away_team=away_team,
        home_logo=str(home_logo),
        away_logo=str(away_logo),
        home_prob=home_prob,
        draw_prob=draw_prob,
        away_prob=away_prob,
        conclusion_text=conclusion_text,
        output_path=str(prob_out)
    )

    # Tahmini Skor style image
    below_text = "Birleşik simülasyon + Markov form"
    score_out = OUTPUT_FOLDER / f"TahminiSkor_{home_team}_{away_team}.png"
    create_match_image(
        first_team_name=home_team,
        second_team_name=away_team,
        first_logo_path=str(home_logo),
        second_logo_path=str(away_logo),
        score_text=headline_score,
        below_text=below_text,
        output_path=str(score_out)
    )

def main():
    home_team = input("Enter HOME team name: ").strip()
    away_team = input("Enter AWAY team name: ").strip()

    # 1) Markov models
    markov_home = run_markov_for_team(home_team)
    markov_away = run_markov_for_team(away_team)

    # 2) gol_oncesi simulations (two perspectives)
    home_sim = run_simulation_perspective(home_team, away_team)
    away_sim = run_simulation_perspective(away_team, home_team)

    # 3) Print report sections
    print_markov_section(markov_home, markov_away, home_team, away_team)
    print_simulation_section(home_sim, away_sim, home_team, away_team)

    # 4) Combine to unified probabilities & expected score
    combined = combine_perspectives(home_sim, away_sim)

    print("Main Result:")
    print(
        f"Combined win/draw/loss (Home perspective): "
        f"{percent(combined['home_win']):.2f}% – "
        f"{percent(combined['draw']):.2f}% – "
        f"{percent(combined['home_loss']):.2f}%"
    )
    print(
        f"Combined expected score: between "
        f"{home_sim['top_score']} and {away_sim['top_score']} "
        f"centered around {combined['exp_home_goals']:.1f}–{combined['exp_away_goals']:.1f}"
    )
    print(f"Headline central scoreline: {combined['headline_score']}\n")

    # 5) Generate visual outputs (KimKazanır + Tahmini Skor)
    generate_images(home_team, away_team, combined)
    print("✅ Probability and score images generated via KimKazanır & Tahmini Skor modules.")

if __name__ == "__main__":
    main()
