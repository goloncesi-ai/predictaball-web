"""
TACTICAL FORMATION MATCH SIMULATOR + ONE HEATMAP (single-file script)

What this version does (per your latest requirements):
- User can choose ANY formation available in FORMATION_TEMPLATES (not limited to 3).
- Those chosen formations are assumed final:
    -> simulations run ONLY for those two formations (no formation grid sweep).
- Total simulations = 1000:
    -> 500 where Team1 is home (home perspective)
    -> 500 where Team1 is away (away perspective, i.e., swapped teams)
- Results are combined exactly like before (two perspectives -> unified output).
- Markov/HMM is still used ONLY to compute suggested mean-adjustment (efficiency change),
  but we do NOT print the full Markov model report.
- Heatmap is drawn ONCE ONLY for the "Team1 home vs Team2 away" run.
  (when home/away flips, we do not draw again)

Heatmap logic:
- Uses per-player AVERAGE ratings from all simulations (home perspective only).
- Rebuilds positional coords via formation templates.
- Color scaling uses min/max across ALL 22 players (11+11) to set the thresholds.
- Team1 colormap: yellow (low) -> red (high)
- Team2 colormap: light blue (low) -> dark blue (high)
- Pitch is drawn on grid: X=1..5, Y=1..9

NOTE:
- Output files are saved under OUTPUT_FOLDER.
- If you want the heatmap filename/path changed, edit HEATMAP_FILENAME below.
"""

from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple
import warnings

import numpy as np
import pandas as pd

from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline as SkPipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.linear_model import LogisticRegressionCV
from sklearn.base import BaseEstimator, TransformerMixin

from hmmlearn.hmm import GaussianHMM

# Optional: keep your existing image outputs
from KimKazanır import create_probability_image
from tahmini_skor import create_match_image

# Heatmap drawing
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

warnings.filterwarnings("ignore", category=FutureWarning)
np.random.seed(42)

# ================================================================
# GLOBAL PATHS
# ================================================================
MAIN_FOLDER = Path("//Users/kagancalikoglu/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi/Data/Turkish Super League")
OUTPUT_FOLDER = Path("/Users/kagancalikoglu/Documents/PredictaBall/Outputs")
LOGO_FOLDER = Path("/Users/kagancalikoglu/Documents/PredictaBall/Logos")
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

HEATMAP_FILENAME = "tactical_heatmap.png"

# ================================================================
# SIMULATION COUNTS (fixed per your request)
# ================================================================
N_SIMS_HOME_PERSPECTIVE = 500
N_SIMS_AWAY_PERSPECTIVE = 500

TEAM1_FORMATION_COL = "Team1Formation"
TEAM2_FORMATION_COL = "Team2Formation"

TEAM1_PLAYERS = [f"Team1Player{i}" for i in range(1, 12)]
TEAM2_PLAYERS = [f"Team2Player{i}" for i in range(1, 12)]

TARGET_COLS_LINEAR = ["Team1_TotalShots", "Team1_BallPosses", "Team2_TotalShots", "Team2_BallPosses"]
GOAL_TARGETS = ["Team1_Goals", "Team2_Goals"]
OUTCOME_COL = "Outcome_3W1D0L"

X_MIN, X_MAX = 1, 5
Y_MIN, Y_MAX = 1, 9

# ================================================================
# Helpers
# ================================================================
def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def read_adjustment_pct(team_name: str) -> float:
    raw = input(f"Adjustment for {team_name} (%), e.g. -10..+10 (default 0): ").strip()
    if raw == "":
        return 0.0
    try:
        val = float(raw.replace(",", "."))
    except ValueError:
        print("Invalid input -> using 0")
        return 0.0
    return _clamp(val, -50.0, 50.0)


def ask_efficiency_choice() -> int:
    """
    1) No: keep historical play learnings (0%)
    2) Yes: apply calculated performance changes
    3) Manual: user enters adjustments
    """
    print("\nAdjust team efficiencies based on HMM trend?")
    print("  1) no (0%)")
    print("  2) yes (apply suggested %)")
    print("  3) manual (I will enter %)")
    raw = input("Select (1/2/3): ").strip().lower()

    mapping = {
        "1": 1, "no": 1, "n": 1,
        "2": 2, "yes": 2, "y": 2,
        "3": 3, "manual": 3, "m": 3,
    }
    return mapping.get(raw, 1)


def make_unique_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols = list(df.columns)
    seen = {}
    new_cols = []
    for c in cols:
        if c not in seen:
            seen[c] = 0
            new_cols.append(c)
        else:
            seen[c] += 1
            new_cols.append(f"{c}__dup{seen[c]}")
    out = df.copy()
    out.columns = new_cols
    return out


# ================================================================
# Clusters / Formation templates (unchanged)
# ================================================================
@dataclass(frozen=True)
class Cluster:
    name: str
    x1: int
    x2: int
    y1: int
    y2: int

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
    "4-1-3-2": [(1, 5), (2, 2), (2, 4), (2, 6), (2, 8), (3, 5), (4, 3), (4, 5), (4, 7), (5, 4), (5, 6)],
    "4-2-3-1": [(1, 5), (2, 2), (2, 4), (2, 6), (2, 8), (3, 4), (3, 6), (4, 3), (4, 5), (4, 7), (5, 5)],
    "4-3-3": [(1, 5), (2, 2), (2, 4), (2, 6), (2, 8), (3, 4), (3, 5), (3, 6), (4, 2), (4, 5), (4, 8)],
    "4-4-2": [(1, 5), (2, 2), (2, 4), (2, 6), (2, 8), (3, 3), (3, 7), (4, 4), (4, 6), (5, 3), (5, 7)],
    "4-1-4-1": [(1, 5), (2, 2), (2, 4), (2, 6), (2, 8), (3, 5), (4, 2), (4, 4), (4, 6), (4, 8), (5, 5)],
    "4-2-2-2": [(1, 5), (2, 2), (2, 4), (2, 6), (2, 8), (3, 3), (3, 7), (4, 4), (4, 6), (5, 3), (5, 7)],
    "4-5-1": [(1, 5), (2, 2), (2, 4), (2, 6), (2, 8), (3, 3), (3, 5), (3, 7), (4, 2), (4, 8), (5, 5)],
    "4-4-1-1": [(1, 5), (2, 2), (2, 4), (2, 6), (2, 8), (3, 3), (3, 7), (4, 4), (4, 6), (4, 5), (5, 5)],
    "4-3-1-2": [(1, 5), (2, 2), (2, 4), (2, 6), (2, 8), (3, 4), (3, 5), (3, 6), (4, 5), (5, 3), (5, 7)],
    # === 3-back systems ===
    "3-4-3": [(1, 5), (2, 3), (2, 5), (2, 7), (3, 2), (3, 4), (3, 6), (3, 8), (4, 3), (4, 5), (4, 7)],
    "3-4-1-2": [(1, 5), (2, 3), (2, 5), (2, 7), (3, 2), (3, 4), (3, 6), (3, 8), (4, 5), (5, 3), (5, 7)],
    "3-4-2-1": [(1, 5), (2, 3), (2, 5), (2, 7), (3, 2), (3, 4), (3, 6), (3, 8), (4, 3), (4, 7), (5, 5)],
    "3-5-2": [(1, 5), (2, 3), (2, 5), (2, 7), (3, 2), (3, 4), (3, 5), (3, 6), (4, 5), (5, 3), (5, 7)],
    "3-1-4-2": [(1, 5), (2, 3), (2, 5), (2, 7), (3, 5), (4, 2), (4, 4), (4, 6), (4, 8), (5, 3), (5, 7)],
    "3-5-1-1": [(1, 5), (2, 3), (2, 5), (2, 7), (3, 2), (3, 4), (3, 6), (3, 8), (4, 5), (5, 5), (3, 5)],
    "3-2-4-1": [(1, 5), (2, 3), (2, 5), (2, 7), (3, 4), (3, 6), (4, 2), (4, 4), (4, 6), (4, 8), (5, 5)],
    "3-3-3-1": [(1, 5), (2, 3), (2, 5), (2, 7), (3, 3), (3, 5), (3, 7), (4, 3), (4, 5), (4, 7), (5, 5)],
    # === 5-back systems ===
    "5-3-2": [(1, 5), (2, 2), (2, 3), (2, 5), (2, 7), (2, 8), (3, 4), (3, 5), (4, 5), (5, 3), (5, 7)],
    "5-4-1": [(1, 5), (2, 2), (2, 3), (2, 5), (2, 7), (2, 8), (3, 4), (3, 5), (4, 3), (4, 7), (5, 5)],
}

DEFAULT_FORMATION = "4-2-3-1"


def parse_formation(s: str) -> str:
    if not isinstance(s, str) or not s.strip():
        return DEFAULT_FORMATION
    s = s.strip().replace(" ", "")
    return s if s in FORMATION_TEMPLATES else DEFAULT_FORMATION


def coords_for_match_team1(f: str):
    return FORMATION_TEMPLATES[parse_formation(f)]


def coords_for_match_team2(f: str):
    coords_t1 = FORMATION_TEMPLATES[parse_formation(f)]
    mirror = lambda x: (X_MIN + X_MAX) - x
    return [(mirror(x), y) for x, y in coords_t1]


# ================================================================
# Data preparation
# ================================================================
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


# ================================================================
# Simulation generator (FIXED formations, N rows)
# ================================================================
def generate_team_test(
    team1_df: pd.DataFrame,
    team2_df: pd.DataFrame,
    team1_name: str,
    team2_name: str,
    team1_homeaway: str,
    team1_formation: str,
    team2_formation: str,
    n_sims: int,
    team1_adj_pct: float = 0.0,
    team2_adj_pct: float = 0.0,
) -> pd.DataFrame:
    """
    Generates exactly n_sims rows using FIXED formations selected by the user.

    Adjustment logic preserved:
      mean_used = mean * (1 + adj/700)   (your current scale)
    """
    team1_formation = parse_formation(team1_formation)
    team2_formation = parse_formation(team2_formation)

    team1_stats = {col: safe_mean_std(team1_df[col]) for col in TEAM1_PLAYERS if col in team1_df.columns}
    team2_stats = {
        f"Team2Player{i}": safe_mean_std(team2_df[f"Team1Player{i}"])
        for i in range(1, 12)
        if f"Team1Player{i}" in team2_df.columns
    }

    mult1 = 1.0 + (team1_adj_pct / 700.0)
    mult2 = 1.0 + (team2_adj_pct / 700.0)

    rows = []
    for _ in range(int(n_sims)):
        row = {
            "Team1": team1_name,
            "Team2": team2_name,
            "Team1H_A": team1_homeaway,
            "Team1Formation": team1_formation,
            "Team2Formation": team2_formation,
        }

        for i in range(1, 12):
            m1, s1 = team1_stats.get(f"Team1Player{i}", (5.0, 1.0))
            m1_adj = m1 * mult1
            val1 = np.clip(np.random.normal(m1_adj, s1), 1, 10)
            row[f"Team1Player{i}"] = round(val1, 2)

        for i in range(1, 12):
            m2, s2 = team2_stats.get(f"Team2Player{i}", (5.0, 1.0))
            m2_adj = m2 * mult2
            val2 = np.clip(np.random.normal(m2_adj, s2), 1, 10)
            row[f"Team2Player{i}"] = round(val2, 2)

        rows.append(row)

    return pd.DataFrame(rows)


# ================================================================
# Cluster feature engineering (unchanged)
# ================================================================
def player_cluster_memberships(x: int, y: int, clusters: List[Cluster], margin: int = 0) -> List[str]:
    return [c.name for c in clusters if c.contains_with_margin(x, y, margin=margin)]


def _aggregate_clusters(coords: List[Tuple[int, int]], ratings: List[float], prefix: str) -> Dict[str, float]:
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


def _safe_div(
    a: float,
    b: float,
    denom_if_bad: float = 1.0,
    hi_ratio: float = 1.9,
    lo_ratio: float = 0.1,
    eq_ratio: float = 1.0,
    treat_one_as_bad: bool = True,
) -> float:
    if pd.isna(a) or pd.isna(b):
        return np.nan

    if a == 0 and b == 0:
        return eq_ratio

    bad = (a == 0) or (b == 0) or (treat_one_as_bad and ((a == 1) or (b == 1)))
    if bad:
        if a > b:
            return hi_ratio
        if a < b:
            return lo_ratio
        return eq_ratio

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


# ================================================================
# Ridge multinomial outcome model (glmnet-like)
# ================================================================
TEAM1_GK = ["Team1_Cluster_Goalkeeper_Zone_Avg"]
TEAM2_GK = ["Team2_Cluster_Goalkeeper_Zone_Avg"]

OUTCOME_XS_T1_MAIN = [
    "Comp_T1_Wing_Right_over_T2_Back_Left",
    "Comp_T1_Wing_Left_over_T2_Back_Right",
    "Comp_T1_Mid_Att_over_T2_Mid_Def",
    "Comp_T1_Mid_Def_over_T2_Mid_Att",
    "Comp_T1_Back_Left_over_T2_Wing_Right",
    "Comp_T1_Back_Right_over_T2_Wing_Left",
]

OUTCOME_INTERACTIONS = [
    ("Comp_T1_Left_Strip_over_T2_Right_Strip", "Comp_T1_Mid_Strip_over_T2_Mid_Strip"),
    ("Comp_T1_Right_Strip_over_T2_Left_Strip", "Comp_T1_Mid_Strip_over_T2_Mid_Strip"),
]

OUTCOME_INTERACTION_BASES = sorted(set([f for pair in OUTCOME_INTERACTIONS for f in pair]))
OUTCOME_BASE_FEATURES = OUTCOME_XS_T1_MAIN + OUTCOME_INTERACTION_BASES

FEATURES_ALL = OUTCOME_BASE_FEATURES
FEATURES_GOALS_T1 = OUTCOME_BASE_FEATURES + TEAM2_GK
FEATURES_GOALS_T2 = OUTCOME_BASE_FEATURES + TEAM1_GK


class AddSpecifiedInteractions(BaseEstimator, TransformerMixin):
    def __init__(self, interactions: List[Tuple[str, str]]):
        self.interactions = interactions

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        if not isinstance(X, pd.DataFrame):
            X = pd.DataFrame(X)
        X = X.copy()

        for a, b in self.interactions:
            name = f"{a}:{b}"
            if a not in X.columns or b not in X.columns:
                X[name] = np.nan
                continue

            xa = X[a]
            xb = X[b]
            if isinstance(xa, pd.DataFrame):
                xa = xa.iloc[:, 0]
            if isinstance(xb, pd.DataFrame):
                xb = xb.iloc[:, 0]

            X[name] = xa * xb

        return X


def _ensure_feature_columns(df: pd.DataFrame) -> pd.DataFrame:
    expected = set(FEATURES_ALL + FEATURES_GOALS_T1 + FEATURES_GOALS_T2)
    expected |= set(OUTCOME_BASE_FEATURES)
    for a, b in OUTCOME_INTERACTIONS:
        expected.add(f"{a}:{b}")

    for col in expected:
        if col not in df.columns:
            df[col] = np.nan
    return df


def run_models(df_engineered: pd.DataFrame):
    models = {}

    df_engineered = make_unique_columns(df_engineered)
    df_engineered = _ensure_feature_columns(df_engineered)

    X_all = df_engineered[FEATURES_ALL]
    X_t1_goal = df_engineered[FEATURES_GOALS_T1]
    X_t2_goal = df_engineered[FEATURES_GOALS_T2]

    # Multinomial ridge outcome model
    if OUTCOME_COL in df_engineered.columns:
        y_outcome = df_engineered[OUTCOME_COL]
        X_outcome = df_engineered[OUTCOME_BASE_FEATURES].copy()

        mask = y_outcome.notna() & X_outcome.notna().all(axis=1)
        X_tr = X_outcome.loc[mask]
        y_tr = y_outcome.loc[mask]

        pipe_mn = Pipeline([
            ("add_inter", AddSpecifiedInteractions(OUTCOME_INTERACTIONS)),
            ("scale", StandardScaler()),
            ("clf", LogisticRegressionCV(
                Cs=np.logspace(-3, 3, 25),
                cv=5,
                penalty="l2",
                solver="saga",
                multi_class="multinomial",
                scoring="accuracy",
                max_iter=5000,
                n_jobs=-1,
                refit=True
            ))
        ])
        pipe_mn.fit(X_tr, y_tr)
        _report_fit("Ridge Multinomial Outcome CV (0/1/3)", pipe_mn, X_tr, y_tr)
        models[OUTCOME_COL] = pipe_mn

    # RF targets
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

    # Goals RF
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

    return models


# ================================================================
# Simulation perspective runner (fixed formations, per-player avgs)
# ================================================================
def run_simulation_perspective(
    team1_name: str,
    team2_name: str,
    team1_formation: str,
    team2_formation: str,
    n_sims: int,
    team1_homeaway: str,  # "Home" label for Team1 in this perspective
    team1_adj_pct: float = 0.0,
    team2_adj_pct: float = 0.0,
) -> dict:
    """
    - Trains on team1 historical data
    - Simulates vs team2 using FIXED formations (user selected)
    - Returns outcome probabilities, expected score and top scorelines
    - Also returns per-player avg ratings across all simulations (for heatmap)
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

    test_df = generate_team_test(
        team1_df, team2_df,
        team1_name, team2_name,
        team1_homeaway=team1_homeaway,
        team1_formation=team1_formation,
        team2_formation=team2_formation,
        n_sims=n_sims,
        team1_adj_pct=team1_adj_pct,
        team2_adj_pct=team2_adj_pct,
    )

    # per-player average ratings across all simulations
    team1_player_avgs = (
        test_df[TEAM1_PLAYERS]
        .apply(pd.to_numeric, errors="coerce")
        .mean(axis=0)
        .to_dict()
    )
    team2_player_avgs = (
        test_df[TEAM2_PLAYERS]
        .apply(pd.to_numeric, errors="coerce")
        .mean(axis=0)
        .to_dict()
    )

    avg_t1_rating = test_df[TEAM1_PLAYERS].mean().mean()
    avg_t2_rating = test_df[TEAM2_PLAYERS].mean().mean()

    eng_train = engineer_dataset(team1_df)
    eng_train = _ensure_feature_columns(eng_train)
    models = run_models(eng_train)

    eng_test = engineer_dataset(test_df)
    eng_test = _ensure_feature_columns(eng_test)
    eng_test = make_unique_columns(eng_test)

    X_all_test = eng_test[FEATURES_ALL]
    X_t1_goal_test = eng_test[FEATURES_GOALS_T1]
    X_t2_goal_test = eng_test[FEATURES_GOALS_T2]

    X_outcome_test = eng_test[OUTCOME_BASE_FEATURES].copy()

    if OUTCOME_COL in models:
        y_proba = models[OUTCOME_COL].predict_proba(X_outcome_test)
        class_labels = models[OUTCOME_COL].named_steps["clf"].classes_
        for c_idx, c_val in enumerate(class_labels):
            eng_test[f"PredP_{OUTCOME_COL}_{c_val}"] = y_proba[:, c_idx]
        eng_test[f"Pred_{OUTCOME_COL}"] = models[OUTCOME_COL].predict(X_outcome_test)

    for t in TARGET_COLS_LINEAR:
        if t in models:
            eng_test[f"Pred_{t}"] = models[t].predict(X_all_test)

    if "Team1_Goals" in models:
        eng_test["Pred_Team1_Goals"] = np.clip(models["Team1_Goals"].predict(X_t1_goal_test), a_min=0, a_max=None)
    if "Team2_Goals" in models:
        eng_test["Pred_Team2_Goals"] = np.clip(models["Team2_Goals"].predict(X_t2_goal_test), a_min=0, a_max=None)

    total_matches = len(eng_test)
    if total_matches == 0:
        raise RuntimeError("No simulated matches produced.")

    win_prob = float((eng_test["Pred_Outcome_3W1D0L"] == 3).sum() / total_matches)
    draw_prob = float((eng_test["Pred_Outcome_3W1D0L"] == 1).sum() / total_matches)
    lose_prob = float((eng_test["Pred_Outcome_3W1D0L"] == 0).sum() / total_matches)

    # Score distribution
    score_counts = pd.DataFrame(columns=["Score", "Count"])
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

    top_score = score_counts.iloc[0]["Score"] if not score_counts.empty else "0-0"
    top5 = score_counts.head(5).copy()

    return {
        "team1": team1_name,
        "team2": team2_name,
        "team1_formation": parse_formation(team1_formation),
        "team2_formation": parse_formation(team2_formation),
        "team1_homeaway": team1_homeaway,
        "simulated_matches": int(total_matches),
        "avg_ratings": {"team1": float(avg_t1_rating), "team2": float(avg_t2_rating)},
        "avg_player_ratings": {
            "team1_players": {k: float(v) for k, v in team1_player_avgs.items()},
            "team2_players": {k: float(v) for k, v in team2_player_avgs.items()},
        },
        "probs": {"team1_win": win_prob, "draw": draw_prob, "team1_loss": lose_prob},
        "top_score": str(top_score),
        "top5_scores": top5,
        "adjustments": {"team1_adj_pct": float(team1_adj_pct), "team2_adj_pct": float(team2_adj_pct)},
    }


# ================================================================
# MARKOV/HMM (used only for suggested mean adjustment)
# ================================================================
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
        ["Team1_PlayerRating_Mean", "Team1_PlayerRating_Median", "Team1_PlayerRating_Std",
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


def _run_markov_for_team_drop_recent(team_name: str, drop_recent: int) -> Dict[str, float]:
    team1_file = MAIN_FOLDER / team_name / "mixed-seasons" / f"{team_name}_Games_Input.xlsx"
    if not team1_file.exists():
        raise FileNotFoundError(f"Missing file for {team_name}: {team1_file}")

    df_raw = pd.read_excel(team1_file)

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

    model, _best_k = fit_best_hmm(X)
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


def compute_hmm_efficiency_change(team_name: str) -> dict:
    """
    Compare 4 games total by dropping most recent rows:
      t   : drop_recent=0
      t-1 : drop_recent=1
      t-2 : drop_recent=2
      t-3 : drop_recent=3

    Final efficiency change = mean stepwise % changes across last 3 steps,
    clamped to [-10, +10] for suggestion.
    """
    r_t3 = _run_markov_for_team_drop_recent(team_name, drop_recent=3)
    r_t2 = _run_markov_for_team_drop_recent(team_name, drop_recent=2)
    r_t1 = _run_markov_for_team_drop_recent(team_name, drop_recent=1)
    r_t  = _run_markov_for_team_drop_recent(team_name, drop_recent=0)

    ep_t3 = float(r_t3["EP"])
    ep_t2 = float(r_t2["EP"])
    ep_t1 = float(r_t1["EP"])
    ep_t  = float(r_t["EP"])

    eps = 1e-6
    c1 = 100.0 * (ep_t2 - ep_t3) / (ep_t3 + eps)
    c2 = 100.0 * (ep_t1 - ep_t2) / (ep_t2 + eps)
    c3 = 100.0 * (ep_t  - ep_t1) / (ep_t1 + eps)
    avg_change = (c1 + c2 + c3) / 3.0

    suggested_adj_pct = _clamp(avg_change, -10.0, 10.0)

    return {
        "team": team_name,
        "ep_series": [ep_t3, ep_t2, ep_t1, ep_t],
        "avg_change_pct": float(avg_change),
        "suggested_adj_pct": float(suggested_adj_pct),
    }


# ================================================================
# Combine perspectives (unchanged)
# ================================================================
def _parse_score_str(s: str) -> tuple[int, int]:
    try:
        a, b = str(s).split("-")
        return int(a), int(b)
    except Exception:
        return 0, 0


def _weighted_goals_from_topN(score_df: pd.DataFrame) -> tuple[float, float, int]:
    if score_df is None or len(score_df) == 0:
        return 0.0, 0.0, 0

    total = 0
    sum_g1 = 0
    sum_g2 = 0

    for _, row in score_df.iterrows():
        score = row.get("Score", "0-0")
        cnt = row.get("Count", 0)
        try:
            c = int(cnt)
        except Exception:
            c = 0
        if c <= 0:
            continue

        g1, g2 = _parse_score_str(score)
        sum_g1 += g1 * c
        sum_g2 += g2 * c
        total += c

    if total == 0:
        return 0.0, 0.0, 0

    return (sum_g1 / total), (sum_g2 / total), total


def combine_perspectives(home_sim: dict, away_sim: dict) -> dict:
    """
    home_sim: Team1=Home, Team2=Away
    away_sim: Team1=Away, Team2=Home (so reverse for home view)
    """
    p1 = home_sim["probs"]
    p2 = away_sim["probs"]

    home_win_1 = p1["team1_win"]
    draw_1 = p1["draw"]
    home_loss_1 = p1["team1_loss"]

    home_win_2 = p2["team1_loss"]
    draw_2 = p2["draw"]
    home_loss_2 = p2["team1_win"]

    home_win = (home_win_1 + home_win_2) / 2.0
    draw = (draw_1 + draw_2) / 2.0
    home_loss = (home_loss_1 + home_loss_2) / 2.0

    exp_h1, exp_a1, n1 = _weighted_goals_from_topN(home_sim.get("top5_scores"))
    exp_away_as_team1, exp_home_as_team2, n2 = _weighted_goals_from_topN(away_sim.get("top5_scores"))

    exp_h2 = exp_home_as_team2
    exp_a2 = exp_away_as_team1

    if (n1 + n2) > 0:
        exp_home_goals = (exp_h1 * n1 + exp_h2 * n2) / (n1 + n2)
        exp_away_goals = (exp_a1 * n1 + exp_a2 * n2) / (n1 + n2)
    else:
        exp_home_goals = 0.0
        exp_away_goals = 0.0

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


# ================================================================
# Heatmap (draw ONCE for home perspective)
# ================================================================
# ================================================================
# Heatmaps (readable two-panel style)
#   1) Player rating heatmap (per player)
#   2) Main cluster heatmap
#   3) Strip cluster heatmap
# Draw ONCE for home perspective only.
# ================================================================
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

PLAYER_HEATMAP_FILENAME = "player_heatmap.png"
MAIN_CLUSTER_HEATMAP_FILENAME = "main_cluster_heatmap.png"
STRIP_CLUSTER_HEATMAP_FILENAME = "strip_cluster_heatmap.png"


MAIN_CLUSTERS = [
    Cluster("Goalkeeper_Zone", 1, 1, 1, 9),
    Cluster("Back_Left", 2, 3, 1, 3),
    Cluster("Back_Right", 2, 3, 7, 9),
    Cluster("Mid_Def", 2, 3, 4, 6),
    Cluster("Mid_Att", 4, 5, 4, 6),
    Cluster("Wing_Left", 4, 5, 1, 3),
    Cluster("Wing_Right", 4, 5, 7, 9),
]

STRIP_CLUSTERS = [
    Cluster("Left_Strip", 2, 5, 1, 3),
    Cluster("Mid_Strip", 2, 5, 4, 6),
    Cluster("Right_Strip", 2, 5, 7, 9),
]


def _normalize(v: float, vmin: float, vmax: float) -> float:
    if v is None or np.isnan(v):
        return 0.0
    if vmax <= vmin:
        return 0.5
    return float((v - vmin) / (vmax - vmin))


def _draw_base_grid(ax):
    ax.set_xlim(X_MIN - 0.5, X_MAX + 0.5)
    ax.set_ylim(Y_MIN - 0.5, Y_MAX + 0.5)
    ax.set_aspect("equal")

    # grid
    for x in range(X_MIN, X_MAX + 1):
        for y in range(Y_MIN, Y_MAX + 1):
            ax.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1, fill=False, linewidth=0.8))

    ax.set_xticks(range(X_MIN, X_MAX + 1))
    ax.set_yticks(range(Y_MIN, Y_MAX + 1))
    ax.set_xlabel("X (1..5)")
    ax.set_ylabel("Y (1..9)")


def _short_cluster_name(name: str) -> str:
    # keeps labels readable inside rectangles
    return name.replace("_", "\n")


def _compute_cluster_avgs_for_team(
    team_coords: List[Tuple[int, int]],
    team_player_avgs: Dict[str, float],
    team_prefix: str,  # "Team1Player" or "Team2Player"
    clusters: List[Cluster],
) -> Dict[str, float]:
    pts = []
    for i, (x, y) in enumerate(team_coords, start=1):
        key = f"{team_prefix}{i}"
        val = float(team_player_avgs.get(key, np.nan))
        pts.append((x, y, val))

    out: Dict[str, float] = {}
    for c in clusters:
        vals = []
        for x, y, v in pts:
            if np.isnan(v):
                continue
            if c.contains_with_margin(x, y, margin=0):
                vals.append(v)
        out[c.name] = float(np.mean(vals)) if len(vals) else np.nan
    return out


def create_player_rating_heatmap_two_panel(
    team1_name: str,
    team2_name: str,
    team1_formation: str,
    team2_formation: str,
    team1_player_avgs: Dict[str, float],  # Team1Player1..11
    team2_player_avgs: Dict[str, float],  # Team2Player1..11
    output_path: Path,
):
    """
    Two panels:
      Left: Team1 (yellow->red)
      Right: Team2 (light->dark blue)
    Cells are only filled where players are located. Labels show player index + rating.
    """
    team1_formation = parse_formation(team1_formation)
    team2_formation = parse_formation(team2_formation)

    coords1 = coords_for_match_team1(team1_formation)
    coords2 = coords_for_match_team2(team2_formation)

    vals1 = [float(team1_player_avgs.get(f"Team1Player{i}", np.nan)) for i in range(1, 12)]
    vals2 = [float(team2_player_avgs.get(f"Team2Player{i}", np.nan)) for i in range(1, 12)]
    all_vals = [v for v in (vals1 + vals2) if not np.isnan(v)]
    vmin, vmax = (min(all_vals), max(all_vals)) if all_vals else (1.0, 10.0)

    fig, axes = plt.subplots(1, 2, figsize=(14, 8), constrained_layout=True)
    fig.suptitle(f"Tactical Heatmap (min={vmin:.2f}, max={vmax:.2f})", fontsize=16)

    cmap_left = plt.get_cmap("YlOrRd")
    cmap_right = plt.get_cmap("Blues")

    # --- Team1 panel ---
    ax = axes[0]
    _draw_base_grid(ax)
    ax.set_title(f"{team1_name} ({team1_formation})")
    for idx, ((x, y), v) in enumerate(zip(coords1, vals1), start=1):
        t = _normalize(v, vmin, vmax)
        ax.add_patch(
            Rectangle(
                (x - 0.5, y - 0.5), 1, 1,
                facecolor=cmap_left(t), alpha=0.9,
                edgecolor="black", linewidth=1.0
            )
        )
        ax.text(x, y, f"{idx}\n{v:.2f}", ha="center", va="center", fontsize=9)

    # --- Team2 panel ---
    ax = axes[1]
    _draw_base_grid(ax)
    ax.set_title(f"{team2_name} ({team2_formation})")
    for idx, ((x, y), v) in enumerate(zip(coords2, vals2), start=1):
        t = _normalize(v, vmin, vmax)
        ax.add_patch(
            Rectangle(
                (x - 0.5, y - 0.5), 1, 1,
                facecolor=cmap_right(t), alpha=0.9,
                edgecolor="black", linewidth=1.0
            )
        )
        ax.text(x, y, f"{idx}\n{v:.2f}", ha="center", va="center", fontsize=9)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200)
    plt.close(fig)

    print(f"✅ Player heatmap saved: {output_path}")


def _mirror_x(x: int) -> int:
    return (X_MIN + X_MAX) - x


def mirror_cluster_for_team2(c: Cluster) -> Cluster:
    # Mirror rectangle in X: (x1..x2) -> (mirror(x2)..mirror(x1))
    return Cluster(
        name=c.name,
        x1=_mirror_x(c.x2),
        x2=_mirror_x(c.x1),
        y1=c.y1,
        y2=c.y2,
    )


def create_cluster_heatmap_two_panel(
    team1_name: str,
    team2_name: str,
    team1_formation: str,
    team2_formation: str,
    team1_player_avgs: Dict[str, float],  # Team1Player1..11
    team2_player_avgs: Dict[str, float],  # Team2Player1..11
    clusters: List[Cluster],
    title: str,
    output_path: Path,
):
    """
    Two panels with cluster rectangles filled by cluster avg rating.
    Cluster avg = mean(avg_player_ratings of players inside cluster).

    IMPORTANT:
      - Team1 uses clusters as-defined.
      - Team2 uses X-mirrored cluster rectangles so zones align with mirrored Team2 coordinates.
    """
    team1_formation = parse_formation(team1_formation)
    team2_formation = parse_formation(team2_formation)

    coords1 = coords_for_match_team1(team1_formation)
    coords2 = coords_for_match_team2(team2_formation)

    team1_clusters = clusters
    team2_clusters = [mirror_cluster_for_team2(c) for c in clusters]

    cavg1 = _compute_cluster_avgs_for_team(coords1, team1_player_avgs, "Team1Player", team1_clusters)
    cavg2 = _compute_cluster_avgs_for_team(coords2, team2_player_avgs, "Team2Player", team2_clusters)

    all_cluster_vals = [v for v in list(cavg1.values()) + list(cavg2.values()) if not np.isnan(v)]
    vmin, vmax = (min(all_cluster_vals), max(all_cluster_vals)) if all_cluster_vals else (1.0, 10.0)

    fig, axes = plt.subplots(1, 2, figsize=(14, 8), constrained_layout=True)
    fig.suptitle(f"{title} (min={vmin:.2f}, max={vmax:.2f})", fontsize=16)

    cmap_left = plt.get_cmap("YlOrRd")
    cmap_right = plt.get_cmap("Blues")

    # --- Team1 panel ---
    ax = axes[0]
    _draw_base_grid(ax)
    ax.set_title(f"{team1_name} ({team1_formation})")
    for c in team1_clusters:
        v = cavg1.get(c.name, np.nan)
        t = _normalize(v, vmin, vmax)
        ax.add_patch(
            Rectangle(
                (c.x1 - 0.5, c.y1 - 0.5),
                c.x2 - c.x1 + 1,
                c.y2 - c.y1 + 1,
                facecolor=cmap_left(t),
                alpha=0.55,
                edgecolor="black",
                linewidth=1.2
            )
        )
        cx = (c.x1 + c.x2) / 2.0
        cy = (c.y1 + c.y2) / 2.0
        label = f"{_short_cluster_name(c.name)}\n{v:.2f}" if not np.isnan(v) else f"{_short_cluster_name(c.name)}\nNA"
        ax.text(cx, cy, label, ha="center", va="center", fontsize=9)

    # --- Team2 panel (mirrored clusters) ---
    ax = axes[1]
    _draw_base_grid(ax)
    ax.set_title(f"{team2_name} ({team2_formation})")
    for c in team2_clusters:
        v = cavg2.get(c.name, np.nan)
        t = _normalize(v, vmin, vmax)
        ax.add_patch(
            Rectangle(
                (c.x1 - 0.5, c.y1 - 0.5),
                c.x2 - c.x1 + 1,
                c.y2 - c.y1 + 1,
                facecolor=cmap_right(t),
                alpha=0.55,
                edgecolor="black",
                linewidth=1.2
            )
        )
        cx = (c.x1 + c.x2) / 2.0
        cy = (c.y1 + c.y2) / 2.0
        label = f"{_short_cluster_name(c.name)}\n{v:.2f}" if not np.isnan(v) else f"{_short_cluster_name(c.name)}\nNA"
        ax.text(cx, cy, label, ha="center", va="center", fontsize=9)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200)
    plt.close(fig)

    print(f"✅ Cluster heatmap saved: {output_path}")


# ================================================================
# Probability/Score images (optional, unchanged)
# ================================================================
def build_conclusion_text(
    home_team: str,
    away_team: str,
    home_prob: int,
    draw_prob: int,
    away_prob: int,
) -> str:
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


def generate_images(home_team: str, away_team: str, combined: dict):
    home_prob = percent_int(combined["home_win"])
    draw_prob = percent_int(combined["draw"])
    away_prob = percent_int(combined["home_loss"])

    conclusion_text = build_conclusion_text(home_team, away_team, home_prob, draw_prob, away_prob)

    home_logo = LOGO_FOLDER / f"{home_team}.png"
    away_logo = LOGO_FOLDER / f"{away_team}.png"

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

    below_text = "Tactical formation sim + HMM mean adjust"
    create_match_image(
        first_team_name=home_team,
        second_team_name=away_team,
        first_logo_path=str(home_logo),
        second_logo_path=str(away_logo),
        score_text=combined["headline_score"],
        below_text=below_text
    )


# ================================================================
# MAIN
# ================================================================
def main():
    home_team = input("Enter HOME team name: ").strip()
    away_team = input("Enter AWAY team name: ").strip()

    # Formation input (any in FORMATION_TEMPLATES)
    print("\nAvailable formations:")
    print(", ".join(sorted(FORMATION_TEMPLATES.keys())))

    home_form = input(f"Enter formation for {home_team}: ").strip()
    away_form = input(f"Enter formation for {away_team}: ").strip()

    home_form = parse_formation(home_form)
    away_form = parse_formation(away_form)

    print(f"\nUsing formations: {home_team}={home_form} | {away_team}={away_form}")

    # HMM suggested adjustments (no full report printing)
    trend_home = compute_hmm_efficiency_change(home_team)
    trend_away = compute_hmm_efficiency_change(away_team)

    print("\nHMM suggested mean adjustments (last 3 games trend):")
    print(f"  {home_team}: {trend_home['suggested_adj_pct']:+.1f}% (avg change {trend_home['avg_change_pct']:+.1f}%)")
    print(f"  {away_team}: {trend_away['suggested_adj_pct']:+.1f}% (avg change {trend_away['avg_change_pct']:+.1f}%)")

    choice = ask_efficiency_choice()

    if choice == 1:
        home_adj, away_adj = 0.0, 0.0
        print(f"\nUsing NO efficiency adjustment: {home_team} {home_adj:+.1f}% | {away_team} {away_adj:+.1f}%")
    elif choice == 2:
        home_adj = trend_home["suggested_adj_pct"]
        away_adj = trend_away["suggested_adj_pct"]
        print(f"\nApplying HMM-derived adjustments: {home_team} {home_adj:+.1f}% | {away_team} {away_adj:+.1f}%")
    else:
        print("\nManual adjustments selected.")
        home_adj = read_adjustment_pct(home_team)
        away_adj = read_adjustment_pct(away_team)
        print(f"\nUsing manual adjustments: {home_team} {home_adj:+.1f}% | {away_team} {away_adj:+.1f}%")

    # Simulations:
    # 500 home perspective (Team1=home_team)
    home_sim = run_simulation_perspective(
        team1_name=home_team,
        team2_name=away_team,
        team1_formation=home_form,
        team2_formation=away_form,
        n_sims=N_SIMS_HOME_PERSPECTIVE,
        team1_homeaway="Home",
        team1_adj_pct=home_adj,
        team2_adj_pct=away_adj,
    )

    # --- Heatmaps ONCE (home perspective only) ---
    player_hm_path = OUTPUT_FOLDER / PLAYER_HEATMAP_FILENAME
    main_cluster_hm_path = OUTPUT_FOLDER / MAIN_CLUSTER_HEATMAP_FILENAME
    strip_cluster_hm_path = OUTPUT_FOLDER / STRIP_CLUSTER_HEATMAP_FILENAME
    
    t1_avgs = home_sim["avg_player_ratings"]["team1_players"]
    t2_avgs = home_sim["avg_player_ratings"]["team2_players"]
    
    create_player_rating_heatmap_two_panel(
        team1_name=home_team,
        team2_name=away_team,
        team1_formation=home_form,
        team2_formation=away_form,
        team1_player_avgs=t1_avgs,
        team2_player_avgs=t2_avgs,
        output_path=player_hm_path,
    )
    
    create_cluster_heatmap_two_panel(
        team1_name=home_team,
        team2_name=away_team,
        team1_formation=home_form,
        team2_formation=away_form,
        team1_player_avgs=t1_avgs,
        team2_player_avgs=t2_avgs,
        clusters=MAIN_CLUSTERS,
        title="Main Cluster Heatmap",
        output_path=main_cluster_hm_path,
    )
    
    create_cluster_heatmap_two_panel(
        team1_name=home_team,
        team2_name=away_team,
        team1_formation=home_form,
        team2_formation=away_form,
        team1_player_avgs=t1_avgs,
        team2_player_avgs=t2_avgs,
        clusters=STRIP_CLUSTERS,
        title="Strip Cluster Heatmap",
        output_path=strip_cluster_hm_path,
    )

    # 500 away perspective (swap teams to view from the other side)
    away_sim = run_simulation_perspective(
        team1_name=away_team,
        team2_name=home_team,
        team1_formation=away_form,
        team2_formation=home_form,
        n_sims=N_SIMS_AWAY_PERSPECTIVE,
        team1_homeaway="Home",
        team1_adj_pct=away_adj,
        team2_adj_pct=home_adj,
    )

    combined = combine_perspectives(home_sim, away_sim)

    # Print combined results
    print("\n========================")
    print("RESULTS (combined)")
    print("========================")
    print(
        f"Win/Draw/Loss (Home perspective): "
        f"{percent(combined['home_win']):.2f}% / "
        f"{percent(combined['draw']):.2f}% / "
        f"{percent(combined['home_loss']):.2f}%"
    )
    print(f"Expected goals: {combined['exp_home_goals']:.2f} - {combined['exp_away_goals']:.2f}")
    print(f"Headline scoreline: {combined['headline_score']}")

    # Print per-player averages (home perspective only — same one used for heatmap)
    print("\nPer-player avg ratings (HOME perspective sims):")
    print(f"{home_team} (Team1Player1..11):")
    for i in range(1, 12):
        k = f"Team1Player{i}"
        v = home_sim["avg_player_ratings"]["team1_players"].get(k, float("nan"))
        print(f"  {k}: {v:.2f}")

    print(f"\n{away_team} (Team2Player1..11):")
    for i in range(1, 12):
        k = f"Team2Player{i}"
        v = home_sim["avg_player_ratings"]["team2_players"].get(k, float("nan"))
        print(f"  {k}: {v:.2f}")
    

    # Optional: generate your probability + score images
    generate_images(home_team, away_team, combined)
    print("\n✅ Probability and score images generated.")
    print("✅ Heatmaps generated once (home perspective):")
    print(f"  - Player heatmap: {player_hm_path}")
    print(f"  - Main cluster heatmap: {main_cluster_hm_path}")
    print(f"  - Strip cluster heatmap: {strip_cluster_hm_path}")
    


if __name__ == "__main__":
    main()
