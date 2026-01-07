#!/usr/bin/env python3
"""
Dual-Team Hidden Markov Match Simulator (Manual Fusion Version)
---------------------------------------------------------------

This version:
- Asks for both home and away team names
- Builds an HMM for each team separately
- Computes P(win/draw/loss) for each team
- Combines them via simple product fusion (your manual approach)

Fusion rule:
    Home_win = Phome(win) * Paway(loss)
    Draw     = Phome(draw) * Paway(draw)
    Away_win = Paway(win) * Phome(loss)
Then normalized to sum to 1.

Requirements:
    pip install pandas numpy scikit-learn hmmlearn matplotlib
"""

import os, json, warnings
import numpy as np, pandas as pd
from pathlib import Path
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from hmmlearn.hmm import GaussianHMM

warnings.filterwarnings("ignore", category=FutureWarning)
np.random.seed(42)

# ---------------------------------------------------------------------
# Shared feature settings
# ---------------------------------------------------------------------
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
TARGET_COL = "Win(3)_Draw(1)_Lose(0)"


# ---------------------------------------------------------------------
# Feature building and modeling helpers
# ---------------------------------------------------------------------
def build_features(df):
    df = df.copy()
    for prefix, cols in [("Team1", TEAM1_PLAYER_RATING_COLS), ("Team2", TEAM2_PLAYER_RATING_COLS)]:
        df[f"{prefix}_PlayerRating_Mean"] = df[cols].mean(axis=1)
        df[f"{prefix}_PlayerRating_Median"] = df[cols].median(axis=1)
        df[f"{prefix}_PlayerRating_Std"] = df[cols].std(axis=1, ddof=0)
    for c1, c2 in zip(TEAM1_NUMERIC_COLS, TEAM2_NUMERIC_COLS):
        base = c1.replace("Team1_", "")
        df[f"Diff_{base}"] = df[c1] - df[c2]
    df["Diff_PlayerRating_Mean"] = df["Team1_PlayerRating_Mean"] - df["Team2_PlayerRating_Mean"]
    df["Diff_PlayerRating_Median"] = df["Team1_PlayerRating_Median"] - df["Team2_PlayerRating_Median"]
    df["Diff_PlayerRating_Std"] = df["Team1_PlayerRating_Std"] - df["Team2_PlayerRating_Std"]

    num_feats = TEAM1_NUMERIC_COLS + TEAM2_NUMERIC_COLS + \
                [f"Diff_{c.replace('Team1_', '')}" for c in TEAM1_NUMERIC_COLS] + \
                ["Team1_PlayerRating_Mean","Team1_PlayerRating_Median","Team1_PlayerRating_Std",
                 "Team2_PlayerRating_Mean","Team2_PlayerRating_Median","Team2_PlayerRating_Std",
                 "Diff_PlayerRating_Mean","Diff_PlayerRating_Median","Diff_PlayerRating_Std"]
    cat_feats = CATEGORICAL_COLS
    return df, num_feats, cat_feats


def make_preprocessor(num_feats, cat_feats):
    num_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler())
    ])
    cat_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(drop="if_binary", handle_unknown="ignore"))
    ])
    return ColumnTransformer([
        ("num", num_pipe, num_feats),
        ("cat", cat_pipe, cat_feats)
    ])


def fit_best_hmm(X, k_min=2, k_max=5):
    best_bic = np.inf; best_model = None; best_k = None
    N, D = X.shape
    for k in range(k_min, k_max+1):
        model = GaussianHMM(n_components=k, covariance_type="diag", n_iter=500, tol=1e-4)
        model.fit(X)
        logL = model.score(X)
        p = k*(D*2 + (k-1))
        bic = p*np.log(N) - 2*logL
        if bic < best_bic:
            best_bic, best_model, best_k = bic, model, k
    return best_model, best_k


def estimate_outcomes_by_state(states, y):
    outcome_map = {}
    for s in np.unique(states):
        mask = states==s
        sub = y[mask]; total = len(sub)
        if total==0: continue
        outcome_map[int(s)] = {
            "P_win": np.mean(sub==3),
            "P_draw": np.mean(sub==1),
            "P_loss": np.mean(sub==0),
            "count": total
        }
    return outcome_map


def predict_next(model, X, outcome_map):
    _, post = model.score_samples(X)
    gamma_last = post[-1]
    next_gamma = model.transmat_.T @ gamma_last
    p_win=p_draw=p_loss=0
    for s, p in enumerate(next_gamma):
        m=outcome_map.get(s,{})
        p_win += p*m.get("P_win",0)
        p_draw += p*m.get("P_draw",0)
        p_loss += p*m.get("P_loss",0)
    t = p_win+p_draw+p_loss
    if t>0: p_win,p_draw,p_loss=p_win/t,p_draw/t,p_loss/t
    return {"P_win":p_win,"P_draw":p_draw,"P_loss":p_loss}


def fuse_simple_product(p_home, p_away):
    """Your manual-style fusion: pure product + normalization."""
    r_home = p_home["P_win"] * p_away["P_loss"] * 1.1
    r_draw = p_home["P_draw"] * p_away["P_draw"]
    r_away = p_away["P_win"] * p_home["P_loss"] * 0.90

    total = r_home + r_draw + r_away
    if total == 0:
        return {"Home_win": 0.33, "Draw": 0.33, "Away_win": 0.33}
    return {
        "Home_win": r_home / total,
        "Draw": r_draw / total,
        "Away_win": r_away / total
    }


def team_pipeline(team_name, base_dir):
    print(f"\n=== Building model for {team_name} ===")
    f = base_dir / team_name / "mixed-seasons" / f"{team_name}_Games_Input.xlsx"
    df = pd.read_excel(f)
    if "MatchOrder" not in df.columns:
        df["MatchOrder"] = range(len(df),0,-1)
    df = df.sort_values("MatchOrder").reset_index(drop=True)

    feats, numf, catf = build_features(df)
    y = feats[TARGET_COL].values
    preproc = make_preprocessor(numf, catf)
    X = preproc.fit_transform(feats)
    model, k = fit_best_hmm(X)
    states = model.predict(X)
    omap = estimate_outcomes_by_state(states, y)
    nextp = predict_next(model, X, omap)
    print(f"Hidden states: {k}")
    print("Next-match probabilities:")
    print(json.dumps(nextp, indent=2))
    return nextp


# ---------------------------------------------------------------------
# MAIN MATCHUP SECTION
# ---------------------------------------------------------------------
def main():
    main_folder = Path("//Users/kagancalikoglu/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi/Data/Turkish Super League")

    home_team = input("Enter HOME team name: ").strip()
    away_team = input("Enter AWAY team name: ").strip()

    p_home = team_pipeline(home_team, main_folder)
    p_away = team_pipeline(away_team, main_folder)

    combined = fuse_simple_product(p_home, p_away)
    print("\nCombined match prediction (product rule):")
    print(json.dumps(combined, indent=2))


if __name__ == "__main__":
    main()
