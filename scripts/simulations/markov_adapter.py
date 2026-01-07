
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
try:
    from hmmlearn.hmm import GaussianHMM
except ImportError:
    GaussianHMM = None

warnings.filterwarnings("ignore", category=FutureWarning)
np.random.seed(42)

# ================================================================
# SHARED CONFIG
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
TARGET_COL = "Win(3)_Draw(1)_Lose(0)"

# ================================================================
# FEATURE BUILDING
# ================================================================
def build_features(df):
    df = df.copy()
    # Player Stats
    for prefix, cols in [("Team1", TEAM1_PLAYER_RATING_COLS), ("Team2", TEAM2_PLAYER_RATING_COLS)]:
        df[f"{prefix}_PlayerRating_Mean"] = df[cols].mean(axis=1)
        df[f"{prefix}_PlayerRating_Median"] = df[cols].median(axis=1)
        df[f"{prefix}_PlayerRating_Std"] = df[cols].std(axis=1, ddof=0)
    
    # Stat Diffs
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

# ================================================================
# HMM LOGIC
# ================================================================
def fit_best_hmm(X, k_min=2, k_max=5):
    if GaussianHMM is None: return None, 0
    best_bic = np.inf; best_model = None; best_k = None
    N, D = X.shape
    for k in range(k_min, k_max+1):
        try:
            model = GaussianHMM(n_components=k, covariance_type="diag", n_iter=100, tol=1e-2, random_state=42)
            model.fit(X)
            logL = model.score(X)
            p = k*(D*2 + (k-1))
            bic = p*np.log(N) - 2*logL
            if bic < best_bic:
                best_bic, best_model, best_k = bic, model, k
        except: continue
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
    if model is None: return {"P_win":0.33, "P_draw":0.33, "P_loss":0.33}
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
    r_home = p_home["P_win"] * p_away["P_loss"] * 1.1
    r_draw = p_home["P_draw"] * p_away["P_draw"]
    r_away = p_away["P_win"] * p_home["P_loss"] * 0.90
    total = r_home + r_draw + r_away
    if total == 0: return {"Home_win": 0.33, "Draw": 0.33, "Away_win": 0.33}
    return {
        "Home_win": r_home / total,
        "Draw": r_draw / total,
        "Away_win": r_away / total
    }

# ================================================================
# PIPELINE
# ================================================================
def team_pipeline(team_name, base_dir):
    f_xlsx = Path(base_dir) / team_name / "mixed-seasons" / f"{team_name}_Games_Input.xlsx"
    f_csv = Path(base_dir) / team_name / "mixed-seasons" / f"{team_name}_Games_Input.csv"
    
    if f_xlsx.exists(): df = pd.read_excel(f_xlsx)
    elif f_csv.exists(): df = pd.read_csv(f_csv)
    else: return None

    # Enforce Numeric for features
    for c in TEAM1_NUMERIC_COLS + TEAM2_NUMERIC_COLS + TEAM1_PLAYER_RATING_COLS + TEAM2_PLAYER_RATING_COLS:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')

    if "MatchOrder" not in df.columns:
        df["MatchOrder"] = range(len(df),0,-1)
    df = df.sort_values("MatchOrder").reset_index(drop=True)

    feats, numf, catf = build_features(df)
    if TARGET_COL not in feats: return None
    
    # HMM requires sequential clean data, dropna
    feats = feats.dropna(subset=numf + [TARGET_COL])
    if len(feats) < 5: return None

    y = feats[TARGET_COL].values
    preproc = make_preprocessor(numf, catf)
    X = preproc.fit_transform(feats)
    
    model, k = fit_best_hmm(X)
    if model is None: return None
    
    states = model.predict(X)
    omap = estimate_outcomes_by_state(states, y)
    nextp = predict_next(model, X, omap)
    return nextp

# ================================================================
# MAIN ENTRY POINT
# ================================================================
def simulate_match(team1, team2, data_path, version="v3"):
    if GaussianHMM is None:
        return {"error": "hmmlearn not installed"}

    p_t1 = team_pipeline(team1, data_path)
    p_t2 = team_pipeline(team2, data_path)

    if not p_t1 or not p_t2:
        return {"error": "Insufficient data/HMM failure"}

    # V3 Logic: Fusion of two separate HMMs
    # V2 Logic: Single HMM (Team1 perspective) - but the user's v2 script was similar structure.
    # For now, we use the fusion for both as it's more robust, or just return single if v2.
    # Let's adhere to v3 fusion for now as default high quality.
    
    combined = fuse_simple_product(p_t1, p_t2)
    
    return {
        "win_prob": combined["Home_win"] * 100,
        "draw_prob": combined["Draw"] * 100,
        "lose_prob": combined["Away_win"] * 100,
        "predicted_score": "?-?" # Markov doesn't predict exact score easily
    }
