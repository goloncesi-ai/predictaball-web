from __future__ import annotations
from typing import Dict, Tuple

import numpy as np
import pandas as pd

from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline as SkPipeline
from hmmlearn.hmm import GaussianHMM

from .data_io import read_team_df

CATEGORICAL_COLS = ["Team1H_A", "Team1Formation", "Team2Formation"]
TEAM1_NUMERIC_COLS = [
    "Team1_Goals", "Team1_BigChances", "Team1_TotalShots", "Team1_Corners",
    "Team1_Passes", "Team1_Tackels", "Team1_FreeKicks", "Team1_BallPosses"
]
TEAM2_NUMERIC_COLS = [
    "Team2_Goals", "Team2_BigChances", "Team2_TotalShots", "Team2_Corners",
    "Team2_Passes", "Team2_Tackels", "Team2_FreeKicks", "Team2_BallPosses"
]
TEAM1_PLAYER_RATING_COLS = [f"Team1Player{i}" for i in range(1, 12)]
TEAM2_PLAYER_RATING_COLS = [f"Team2Player{i}" for i in range(1, 12)]
TARGET_COL_MARKOV = "Win(3)_Draw(1)_Lose(0)"

def build_features_markov(df: pd.DataFrame) -> Tuple[pd.DataFrame, list, list]:
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

    numeric_features = TEAM1_NUMERIC_COLS + TEAM2_NUMERIC_COLS +         [f"Diff_{c.replace('Team1_', '')}" for c in TEAM1_NUMERIC_COLS] +         ["Team1_PlayerRating_Mean", "Team1_PlayerRating_Median", "Team1_PlayerRating_Std",
         "Team2_PlayerRating_Mean", "Team2_PlayerRating_Median", "Team2_PlayerRating_Std",
         "Diff_PlayerRating_Mean", "Diff_PlayerRating_Median", "Diff_PlayerRating_Std"]

    categorical_features = CATEGORICAL_COLS
    return data, numeric_features, categorical_features

def make_preprocessor_markov(num_feats, cat_feats):
    numeric_transformer = SkPipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler())
    ])
    categorical_transformer = SkPipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(drop="if_binary", handle_unknown="ignore"))
    ])
    return ColumnTransformer([
        ("num", numeric_transformer, num_feats),
        ("cat", categorical_transformer, cat_feats)
    ])

def fit_best_hmm(X, k_min=2, k_max=3, random_state: int = 42):
    best_bic = np.inf
    best_model, best_k = None, None
    N, D = X.shape
    for k in range(k_min, k_max + 1):
        model = GaussianHMM(
            n_components=k,
            covariance_type="diag",
            n_iter=500,
            random_state=random_state + k
        )
        model.fit(X)
        logL = model.score(X)
        p = k * (D * 2 + (k - 1))
        bic = p * np.log(N) - 2 * logL
        if bic < best_bic:
            best_bic = bic
            best_model, best_k = model, k
    return best_model, best_k

def estimate_outcomes_by_state(states, y):
    outcome_map = {}
    for s in np.unique(states):
        mask = states == s
        subset = y[mask]
        total = len(subset)
        if total == 0:
            continue
        outcome_map[int(s)] = {
            "P_win": float(np.mean(subset == 3)),
            "P_draw": float(np.mean(subset == 1)),
            "P_loss": float(np.mean(subset == 0)),
            "count": int(total)
        }
    return outcome_map

def predict_next_match_markov(model, X, outcome_map):
    _, post = model.score_samples(X)
    last_gamma = post[-1]
    next_gamma = model.transmat_.T @ last_gamma

    p_win = p_draw = p_loss = 0.0
    for s, p in enumerate(next_gamma):
        m = outcome_map.get(s, {})
        p_win += float(p) * float(m.get("P_win", 0.0))
        p_draw += float(p) * float(m.get("P_draw", 0.0))
        p_loss += float(p) * float(m.get("P_loss", 0.0))
    total = p_win + p_draw + p_loss
    if total > 0:
        p_win, p_draw, p_loss = p_win / total, p_draw / total, p_loss / total
    return {"P_win": p_win, "P_draw": p_draw, "P_loss": p_loss}

def expected_points_from_probs(probs: Dict[str, float]) -> float:
    return 3.0 * float(probs.get("P_win", 0.0)) + 1.0 * float(probs.get("P_draw", 0.0))

def run_markov_drop_recent(main_folder, team_name: str, drop_recent: int, random_state: int = 42) -> Dict[str, float]:
    df_raw = read_team_df(main_folder, team_name)
    if drop_recent > 0:
        df_raw = df_raw.iloc[drop_recent:].reset_index(drop=True)

    if len(df_raw) < 6:
        neutral = {"P_win": 1/3, "P_draw": 1/3, "P_loss": 1/3}
        return {
            "drop_recent": int(drop_recent),
            "matches_used": int(len(df_raw)),
            **neutral,
            "EP": float(expected_points_from_probs(neutral)),
        }

    if "MatchOrder" not in df_raw.columns:
        df_raw["MatchOrder"] = range(len(df_raw), 0, -1)

    df = df_raw.sort_values(by="MatchOrder").reset_index(drop=True)
    feats_df, num_feats, cat_feats = build_features_markov(df)
    y = feats_df[TARGET_COL_MARKOV].values

    preproc = make_preprocessor_markov(num_feats, cat_feats)
    X = preproc.fit_transform(feats_df)

    model, _ = fit_best_hmm(X, random_state=random_state)
    states = model.predict(X)
    outcomes = estimate_outcomes_by_state(states, y)
    next_probs = predict_next_match_markov(model, X, outcomes)
    ep = expected_points_from_probs(next_probs)

    return {
        "drop_recent": int(drop_recent),
        "matches_used": int(len(df)),
        "P_win": float(next_probs["P_win"]),
        "P_draw": float(next_probs["P_draw"]),
        "P_loss": float(next_probs["P_loss"]),
        "EP": float(ep),
    }

def compute_hmm_efficiency_change(main_folder, team_name: str, clamp_min: float = -10.0, clamp_max: float = 10.0, random_state: int = 42) -> Dict[str, float]:
    r_t3 = run_markov_drop_recent(main_folder, team_name, drop_recent=3, random_state=random_state)
    r_t2 = run_markov_drop_recent(main_folder, team_name, drop_recent=2, random_state=random_state)
    r_t1 = run_markov_drop_recent(main_folder, team_name, drop_recent=1, random_state=random_state)
    r_t  = run_markov_drop_recent(main_folder, team_name, drop_recent=0, random_state=random_state)

    ep_t3 = float(r_t3["EP"]); ep_t2 = float(r_t2["EP"]); ep_t1 = float(r_t1["EP"]); ep_t = float(r_t["EP"])
    eps = 1e-6
    c1 = 100.0 * (ep_t2 - ep_t3) / (ep_t3 + eps)
    c2 = 100.0 * (ep_t1 - ep_t2) / (ep_t2 + eps)
    c3 = 100.0 * (ep_t  - ep_t1) / (ep_t1 + eps)
    avg_change = (c1 + c2 + c3) / 3.0
    suggested = max(clamp_min, min(clamp_max, avg_change))
    return {
        "team": team_name,
        "ep_series": [ep_t3, ep_t2, ep_t1, ep_t],
        "avg_change_pct": float(avg_change),
        "suggested_adj_pct": float(suggested),
    }
