#!/usr/bin/env python3
"""
Hidden Markov Model (HMM) Football Match Sequence Analyzer
----------------------------------------------------------

This script models the underlying "form states" of a single football team based on
match-level data (Team1 always refers to the same team, e.g. Fenerbahçe).

It automatically creates a chronological `MatchOrder` column when no date is given,
assuming the first row is the most recent game.

Pipeline:
  1. Ask user for team name.
  2. Build input path: main_folder / team_name / "mixed-seasons" / f"{team_name}_Games_Input.xlsx"
  3. Create MatchOrder = len(df) - index.
  4. Engineer features, fit Gaussian HMM, infer hidden states.
  5. Estimate P(win/draw/loss | state) and predict next match.
  6. Save artifacts in main_folder / team_name / "HMM_Results".

Requirements:
    pip install pandas numpy scikit-learn hmmlearn matplotlib
"""

import os
import json
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
import matplotlib.pyplot as plt

try:
    from hmmlearn.hmm import GaussianHMM
except Exception:
    GaussianHMM = None

warnings.filterwarnings("ignore", category=FutureWarning)
np.random.seed(42)


# ---------------------------------------------------------------------
# USER INPUT AND PATH SETUP
# ---------------------------------------------------------------------
team1_name = input("Enter Team 1 name: ").strip()
main_folder = Path("//Users/kagancalikoglu/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi/Data/Turkish Super League")

team1_file = main_folder / team1_name / "mixed-seasons" / f"{team1_name}_Games_Input.xlsx"
save_dir = Path("/Users/kagancalikoglu/Documents/PredictaBall/Outputs")
save_dir.mkdir(parents=True, exist_ok=True)

print(f"\nLoading data from: {team1_file}")
print(f"Saving results to: {save_dir}\n")

if GaussianHMM is None:
    raise ImportError("Please install hmmlearn with: pip install hmmlearn")

df = pd.read_excel(team1_file)
print(f"Loaded {df.shape[0]} matches.")

# Automatically create and use MatchOrder
if "MatchOrder" not in df.columns:
    df["MatchOrder"] = range(len(df), 0, -1)
    print("Created MatchOrder column (descending, most recent first).")

df = df.sort_values(by="MatchOrder").reset_index(drop=True)
print("Sorted matches chronologically (oldest first).")


# ---------------------------------------------------------------------
# FEATURE ENGINEERING
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


def build_features(df: pd.DataFrame) -> tuple:
    """Engineer numeric and categorical features for modeling."""
    data = df.copy()

    # Aggregate player ratings
    for prefix, cols in [("Team1", TEAM1_PLAYER_RATING_COLS), ("Team2", TEAM2_PLAYER_RATING_COLS)]:
        data[f"{prefix}_PlayerRating_Mean"] = data[cols].mean(axis=1)
        data[f"{prefix}_PlayerRating_Median"] = data[cols].median(axis=1)
        data[f"{prefix}_PlayerRating_Std"] = data[cols].std(axis=1, ddof=0)

    # Stat differentials
    for c1, c2 in zip(TEAM1_NUMERIC_COLS, TEAM2_NUMERIC_COLS):
        base = c1.replace("Team1_", "")
        data[f"Diff_{base}"] = data[c1] - data[c2]

    # Rating differentials
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


def make_preprocessor(num_feats, cat_feats):
    numeric_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler())
    ])
    categorical_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(drop="if_binary", handle_unknown="ignore"))
    ])
    return ColumnTransformer([
        ("num", numeric_transformer, num_feats),
        ("cat", categorical_transformer, cat_feats)
    ])


# ---------------------------------------------------------------------
# MODELING FUNCTIONS
# ---------------------------------------------------------------------
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
        p = k * (D * 2 + (k - 1))  # approximate params
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


def predict_next_match(model, X, outcome_map):
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


# ---------------------------------------------------------------------
# TRAIN AND SAVE
# ---------------------------------------------------------------------
feats_df, num_feats, cat_feats = build_features(df)
y = feats_df["Win(3)_Draw(1)_Lose(0)"].values

preproc = make_preprocessor(num_feats, cat_feats)
X = preproc.fit_transform(feats_df)
print(f"Feature matrix: {X.shape}")

model, best_k, scores = fit_best_hmm(X)
print("BIC scores:", scores)
print(f"Selected {best_k} hidden states.\n")

states = model.predict(X)
outcomes = estimate_outcomes_by_state(states, y)
print("Outcome probabilities by hidden state:")
print(json.dumps(outcomes, indent=2))

next_probs = predict_next_match(model, X, outcomes)
print("\nPredicted next-match probabilities:")
print(json.dumps(next_probs, indent=2))

# Save results
df["HMM_State"] = states
df.to_csv(save_dir / "match_states.csv", index=False)

summary = {
    "best_k": best_k,
    "bic_scores": scores,
    "transition_matrix": model.transmat_.tolist(),
    "means": model.means_.tolist(),
    "covars": model.covars_.tolist(),
    "state_outcomes": outcomes,
    "next_match_probs": next_probs
}
with open(save_dir / "hmm_summary.json", "w") as f:
    json.dump(summary, f, indent=2)

print(f"\nArtifacts saved in: {save_dir}")
